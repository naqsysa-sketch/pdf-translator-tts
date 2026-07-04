import re
import asyncio
import requests
import hashlib
import json
import os
import logging
import io
from typing import Optional
from deep_translator import GoogleTranslator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
CACHE_DIR = "/tmp/pdf_cache" if IS_SERVERLESS else os.path.join(BASE_DIR, "uploads", "cache")

# Setup logging (file logging disabled on Vercel/serverless)
_log_handlers = [logging.StreamHandler()]
if not IS_SERVERLESS:
    try:
        _log_handlers.insert(0, logging.FileHandler(os.path.join(BASE_DIR, "app.log"), encoding="utf-8"))
    except OSError:
        pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_log_handlers,
)
logger = logging.getLogger("pdf_translator")

# Initialize static-ffmpeg (skip on serverless — ffmpeg not available)
if not IS_SERVERLESS:
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except Exception as e:
        logger.error(f"Failed to load static-ffmpeg paths: {e}")

# Import AudioSegment after static_ffmpeg paths are added so pydub finds ffmpeg
try:
    from pydub import AudioSegment
except Exception as e:
    AudioSegment = None
    logger.warning(f"pydub unavailable: {e}")

# Import prompts module
from prompts import get_gemini_prompt, get_system_prompt

# OCR dependencies setup
try:
    import pytesseract
    from pdf2image import convert_from_path
    HAS_OCR = True
    
    # Check typical windows paths for tesseract binary
    possible_tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for path in possible_tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break
except ImportError:
    HAS_OCR = False

def get_tesseract_lang(lang_code: str) -> str:
    mapping = {
        "en": "eng",
        "ar": "ara",
        "fr": "fra",
        "es": "spa",
        "de": "deu",
        "it": "ita"
    }
    return mapping.get(lang_code, "eng+ara")

def perform_ocr_on_pdf(pdf_path: str, source_lang: str = "auto") -> list[str]:
    if not HAS_OCR:
        logger.error("OCR libraries (pytesseract/pdf2image) are not installed.")
        return []
    
    tess_lang = get_tesseract_lang(source_lang)
    logger.info(f"Performing Tesseract OCR on PDF using language: {tess_lang}")
    
    try:
        pages = convert_from_path(pdf_path, dpi=120)
        page_texts = []
        for i, page in enumerate(pages):
            logger.info(f"OCR: Processing page {i+1}/{len(pages)}")
            text = pytesseract.image_to_string(page, lang=tess_lang)
            page_texts.append(text)
        return page_texts
    except Exception as e:
        logger.error(f"OCR conversion failed (make sure poppler and tesseract are installed and on PATH): {e}")
        return []

def load_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    os.environ[key] = value

load_env()

def calculate_text_hash(text: str) -> str:
    """
    Calculates SHA-256 hash of text.
    """
    return hashlib.sha256(text.encode('utf-8', errors='ignore')).hexdigest()

TRANSLATION_ERROR_MARKER = "[خطأ أثناء الترجمة"


def assess_translation_completeness(source: str, translated: str) -> str | None:
    """Return a user-facing warning when translation looks truncated or failed."""
    if not source or not source.strip():
        return None
    if not translated or not translated.strip():
        return "الترجمة فارغة — قد يكون النص المصدر طويلاً جداً أو فشلت خدمة الترجمة."
    if TRANSLATION_ERROR_MARKER in translated:
        return "فشلت ترجمة جزء من النص. أعد المحاولة أو استخدم محركاً آخر."
    src_len = len(source.strip())
    tr_len = len(translated.strip())
    if src_len >= 200:
        ratio = tr_len / src_len
        if ratio < 0.2:
            return (
                f"الترجمة تبدو ناقصة ({tr_len} حرفاً مقابل {src_len} في المصدر). "
                "أعد الترجمة أو جرّب محركاً آخر."
            )
    return None


def get_cached_translation(text: str, engine: str, model: str = None) -> tuple[str | None, str | None]:
    """
    Retrieves translation from cache if hit conditions are met.
    Returns (translated_text, method) or (None, None).
    """
    if not os.path.exists(CACHE_DIR):
        return None, None
        
    text_hash = calculate_text_hash(text)
    cache_path = os.path.join(CACHE_DIR, f"{text_hash}.json")
    
    if not os.path.exists(cache_path):
        return None, None
        
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
            
        cached_method = cache_data.get("method")
        cached_model = cache_data.get("model")
        cached_text = cache_data.get("translated_text")
        
        if not cached_text:
            return None, None

        if assess_translation_completeness(text, cached_text):
            return None, None
            
        # Cache Hit Conditions:
        if cached_method == "google" and engine != "google":
            # Do not accept cached translation from google unless explicitly requested
            return None, None

        if engine == "google":
            # Any translation is acceptable for Google Translate fallback
            return cached_text, cached_method
            
        if cached_method == engine:
            # If model is specified, it must match
            if not model or cached_model == model:
                return cached_text, cached_method
                
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
        
    return None, None

def save_translation_to_cache(text: str, translated_text: str, method: str, model: str = ""):
    """
    Saves translated text to the cache directory.
    """
    if assess_translation_completeness(text, translated_text):
        return
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        text_hash = calculate_text_hash(text)
        cache_path = os.path.join(CACHE_DIR, f"{text_hash}.json")
        
        cache_data = {
            "source_hash": text_hash,
            "translated_text": translated_text,
            "method": method,
            "model": model
        }
        
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving to cache: {e}")

def _clip_pdf_to_page_range(doc, page_from: int | None, page_to: int | None):
    """Return a document limited to inclusive 1-based page range."""
    import fitz

    total = len(doc)
    if page_from is None and page_to is None:
        return doc
    start = max(1, int(page_from or 1))
    end = min(total, int(page_to or total))
    if start > end:
        doc.close()
        raise ValueError(f"نطاق الصفحات غير صالح: من {start} إلى {end} (المجموع {total}).")
    clipped = fitz.open()
    clipped.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
    doc.close()
    return clipped


def extract_chapters_from_pdf(
    pdf_path: str,
    source_lang: str = "auto",
    page_from: int | None = None,
    page_to: int | None = None,
):
    """
    Extracts text from a PDF file and splits it into chapters.
    Tries Table of Contents (TOC) first, then scans for chapter regex patterns, 
    and falls back to chunking pages if neither works.
    Integrates Tesseract OCR if the PDF contains scanned images/has no extractable text.
    """
    import fitz  # PyMuPDF — lazy import for serverless compatibility

    doc = fitz.open(pdf_path)
    page_offset = 0
    if page_from is not None or page_to is not None:
        page_offset = max(1, int(page_from or 1)) - 1
    doc = _clip_pdf_to_page_range(doc, page_from, page_to)
    toc = doc.get_toc()  # format: [[level, title, page], ...]
    chapters = []

    # Check if PDF contains actual text or if it's scanned
    total_chars = 0
    for page in doc:
        total_chars += len(page.get_text("text", sort=True).strip())
        
    ocr_page_texts = None
    if total_chars < 150:
        logger.info(f"Scanned PDF detected (total characters: {total_chars}). Running OCR fallback...")
        ocr_page_texts = perform_ocr_on_pdf(pdf_path, source_lang)
        if not ocr_page_texts:
            logger.warning("OCR returned no text or failed. Falling back to normal text extraction.")

    def get_page_text(page_idx):
        if ocr_page_texts and page_idx < len(ocr_page_texts):
            return ocr_page_texts[page_idx]
        return doc[page_idx].get_text("text", sort=True)

    # 1. Try splitting using Table of Contents (TOC)
    if toc:
        toc = [entry for entry in toc if entry[0] in (1, 2)]
        toc = sorted(toc, key=lambda x: x[2])
        
        for i in range(len(toc)):
            title = toc[i][1]
            start_page = toc[i][2] - 1  # 0-indexed
            end_page = toc[i+1][2] - 1 if i + 1 < len(toc) else len(doc)
            
            if start_page < 0 or start_page >= len(doc):
                continue
            if end_page > len(doc):
                end_page = len(doc)
                
            chapter_text = ""
            for page_num in range(start_page, end_page):
                chapter_text += get_page_text(page_num) + "\n"
            
            chapters.append({
                "id": i + 1,
                "title": title.strip(),
                "text": chapter_text.strip(),
                "start_page": start_page + 1,
                "end_page": end_page
            })

    # 2. If no TOC entries or only 1 chapter in a large document, search text for patterns
    if not chapters or (len(chapters) == 1 and len(doc) > 10):
        chapters = []
        current_chapter_title = "المقدمة / Introduction"
        current_chapter_text = ""
        chapter_count = 1
        start_page = 1
        
        # Improved Regex to match common chapter headings (English/Arabic) supporting Roman/Words
        chapter_re = re.compile(
            r'^\s*(chapter|chap|ch\.?|section|part|unit|book|الفصل|الباب|المبحث|الدرس|تمهيد|المقدمة|الجزء)[\s\-\:]+([\d\-\u0660-\u0669]+|[a-zA-Z\s\-]+|[\u0621-\u064A\s]+|[ivxlcdmIVXLCDM]+)',
            re.IGNORECASE
        )
        
        for page_num in range(len(doc)):
            page_text = get_page_text(page_num)
            lines = page_text.split('\n')
            
            for line in lines:
                cleaned_line = line.strip()
                if chapter_re.match(cleaned_line) and len(cleaned_line) < 100:
                    # We found a new chapter heading!
                    # Save current chapter if it has text or if it's not the first one
                    if current_chapter_text.strip() or chapter_count > 1:
                        chapters.append({
                            "id": chapter_count,
                            "title": current_chapter_title,
                            "text": current_chapter_text.strip(),
                            "start_page": start_page,
                            "end_page": page_num + 1
                        })
                        chapter_count += 1
                        current_chapter_title = cleaned_line
                        current_chapter_text = ""
                        start_page = page_num + 1
                    else:
                        # First page matches a chapter heading, just update the title
                        current_chapter_title = cleaned_line
                        start_page = page_num + 1
                else:
                    current_chapter_text += "\n" + line
        
        # Add the final chapter
        if current_chapter_text.strip() or (chapter_count == 1 and current_chapter_title):
            chapters.append({
                "id": chapter_count,
                "title": current_chapter_title,
                "text": current_chapter_text.strip(),
                "start_page": start_page,
                "end_page": len(doc)
            })

    # 3. Fallback: Split by fixed page intervals if no structures found
    if not chapters or (len(chapters) == 1 and len(doc) > 10):
        chapters = []
        chunk_size = 5
        for i in range(0, len(doc), chunk_size):
            end_idx = min(i + chunk_size, len(doc))
            chapter_text = ""
            for p in range(i, end_idx):
                chapter_text += get_page_text(p) + "\n"

            chapters.append({
                "id": len(chapters) + 1,
                "title": f"الجزء {len(chapters) + 1} (صفحة {i+1}-{end_idx})",
                "text": chapter_text.strip(),
                "start_page": i + 1,
                "end_page": end_idx
            })

    if page_offset:
        for ch in chapters:
            ch["start_page"] += page_offset
            ch["end_page"] += page_offset

    doc.close()
    return chapters

def translate_text_with_gemini(text: str, api_key: str, model: str = "gemini-3.5-flash") -> str:
    """
    Translates text to literary Arabic using Google Gemini API.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = get_gemini_prompt(text)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3
        }
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=90)
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_msg = response.text
        raise ValueError(f"Gemini API Error (Status {response.status_code}): {error_msg}")
        
    data = response.json()
    
    try:
        translated_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
        # Clean up any potential markdown code fences returned by Gemini
        if translated_text.startswith("```"):
            lines = translated_text.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            translated_text = '\n'.join(lines).strip()
        return translated_text
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid API response format: {e}")

def _split_long_paragraph(para: str, max_chars: int) -> list[str]:
    """Break a single paragraph that exceeds max_chars without dropping text."""
    if len(para) <= max_chars:
        return [para]

    sentences = re.split(r'(?<=[.!?؟…:])\s+', para)
    if len(sentences) <= 1:
        parts = []
        remaining = para
        while len(remaining) > max_chars:
            cut = remaining.rfind(" ", 0, max_chars)
            if cut < max_chars // 2:
                cut = max_chars
            parts.append(remaining[:cut].strip())
            remaining = remaining[cut:].strip()
        if remaining:
            parts.append(remaining)
        return parts

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current.strip():
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_paragraph(sentence, max_chars))
            continue
        sep = 1 if current else 0
        if len(current) + sep + len(sentence) <= max_chars:
            current = f"{current} {sentence}".strip() if current else sentence
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_text(text: str, max_chars: int) -> list[str]:
    """
    Splits text into chunks of maximum character length, including long paragraphs.
    """
    if max_chars < 1:
        max_chars = 3500

    paragraphs = text.split("\n")
    chunks: list[str] = []
    current_chunk = ""

    def flush() -> None:
        nonlocal current_chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        current_chunk = ""

    for para in paragraphs:
        parts = _split_long_paragraph(para, max_chars) if len(para) > max_chars else [para]
        for part in parts:
            if not part:
                continue
            sep = 1 if current_chunk else 0
            if len(current_chunk) + sep + len(part) <= max_chars:
                current_chunk = f"{current_chunk}\n{part}".strip() if current_chunk else part
            else:
                flush()
                current_chunk = part

    flush()
    if not chunks and text.strip():
        return [text.strip()]
    return chunks

def translate_text_with_deepl(text: str, api_key: str) -> str:
    """
    Translates text to Arabic using DeepL API.
    """
    is_free_key = api_key.endswith(":fx")
    base_url = "https://api-free.deepl.com" if is_free_key else "https://api.deepl.com"
    url = f"{base_url}/v2/translate"
    
    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": [text],
        "target_lang": "AR"
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=90)
    if response.status_code != 200:
        raise ValueError(f"DeepL API Error (Status {response.status_code}): {response.text}")
        
    data = response.json()
    try:
        return data["translations"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid DeepL API response format: {e}")

def translate_text_with_openai(text: str, api_key: str, model: str = "gpt-4o-mini") -> str:
    """
    Translates text to literary Arabic using OpenAI API.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = get_system_prompt()
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "temperature": 0.3
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=90)
    if response.status_code != 200:
        raise ValueError(f"OpenAI API Error (Status {response.status_code}): {response.text}")
        
    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid OpenAI API response format: {e}")

def translate_text_with_claude(text: str, api_key: str, model: str = "claude-3-5-sonnet-latest") -> str:
    """
    Translates text to literary Arabic using Anthropic Claude API.
    """
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    system_prompt = get_system_prompt()
    
    # Dynamic max_tokens based on text length (1 token roughly per 3 characters)
    estimated_input_tokens = len(text) // 3
    dynamic_max_tokens = max(1500, min(8000, estimated_input_tokens * 2 + 500))

    payload = {
        "model": model,
        "max_tokens": dynamic_max_tokens,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": text}
        ],
        "temperature": 0.3
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=90)
    if response.status_code != 200:
        raise ValueError(f"Claude API Error (Status {response.status_code}): {response.text}")
        
    data = response.json()
    try:
        return data["content"][0]["text"].strip()
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid Claude API response format: {e}")

def translate_text_with_libretranslate(text: str, host: str, api_key: str = None) -> str:
    """
    Translates text to Arabic using LibreTranslate API.
    """
    host = host.rstrip('/')
    url = f"{host}/translate"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "q": text,
        "source": "auto",
        "target": "ar",
        "format": "text"
    }
    if api_key:
        payload["api_key"] = api_key
        
    response = requests.post(url, json=payload, headers=headers, timeout=90)
    if response.status_code != 200:
        raise ValueError(f"LibreTranslate API Error (Status {response.status_code}): {response.text}")
        
    data = response.json()
    try:
        return data["translatedText"].strip()
    except KeyError as e:
        raise ValueError(f"Invalid LibreTranslate API response format: {e}")

async def translate_text_to_arabic(text: str, engine: str, api_key: str = None, model: str = None, custom_host: str = None) -> tuple[str, str, str]:
    """
    Translates text into Arabic using the specified translation engine.
    Falls back to Google Translate if any error occurs.
    """
    if not text.strip():
        return "", "none", ""

    # Fall back to server environment variables if API Key is not provided
    if not api_key or not api_key.strip():
        if engine == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
        elif engine == "deepl":
            api_key = os.getenv("DEEPL_API_KEY")
        elif engine == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif engine == "claude":
            api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        elif engine == "libretranslate":
            api_key = os.getenv("LIBRETRANSLATE_API_KEY")

    # Check cache first
    cached_text, cached_method = get_cached_translation(text, engine, model)
    if cached_text:
        logger.info(f"Cache HIT: Loaded translation from cache using {cached_method}")
        warning = assess_translation_completeness(text, cached_text) or ""
        return cached_text, cached_method, warning
        
    def finalize(translated_text: str, method: str, warning: str = "") -> tuple[str, str, str]:
        completeness = assess_translation_completeness(text, translated_text)
        if completeness:
            warning = f"{warning} {completeness}".strip() if warning else completeness
        if translated_text and not assess_translation_completeness(text, translated_text):
            save_translation_to_cache(text, translated_text, method, model or "")
        return translated_text, method, warning
        
    # Translate
    try:
        if engine == "gemini":
            if not api_key or not api_key.strip():
                raise ValueError("API Key is missing for Gemini.")
            chunks = chunk_text(text, 8000)
            tasks = [asyncio.to_thread(translate_text_with_gemini, c, api_key, model) for c in chunks]
            translated_chunks = await asyncio.gather(*tasks)
            translated_text = "\n\n".join(translated_chunks)
            return finalize(translated_text, "gemini", "")
            
        elif engine == "deepl":
            if not api_key or not api_key.strip():
                raise ValueError("API Key is missing for DeepL.")
            chunks = chunk_text(text, 8000)
            tasks = [asyncio.to_thread(translate_text_with_deepl, c, api_key) for c in chunks]
            translated_chunks = await asyncio.gather(*tasks)
            translated_text = "\n\n".join(translated_chunks)
            return finalize(translated_text, "deepl", "")
            
        elif engine == "openai":
            if not api_key or not api_key.strip():
                raise ValueError("API Key is missing for OpenAI.")
            chunks = chunk_text(text, 4000)
            tasks = [asyncio.to_thread(translate_text_with_openai, c, api_key, model) for c in chunks]
            translated_chunks = await asyncio.gather(*tasks)
            translated_text = "\n\n".join(translated_chunks)
            return finalize(translated_text, "openai", "")
            
        elif engine == "claude":
            if not api_key or not api_key.strip():
                raise ValueError("API Key is missing for Claude.")
            chunks = chunk_text(text, 4000)
            tasks = [asyncio.to_thread(translate_text_with_claude, c, api_key, model) for c in chunks]
            translated_chunks = await asyncio.gather(*tasks)
            translated_text = "\n\n".join(translated_chunks)
            return finalize(translated_text, "claude", "")
            
        elif engine == "libretranslate":
            host = custom_host if custom_host else "https://libretranslate.de"
            chunks = chunk_text(text, 3000)
            tasks = [asyncio.to_thread(translate_text_with_libretranslate, c, host, api_key) for c in chunks]
            translated_chunks = await asyncio.gather(*tasks)
            translated_text = "\n\n".join(translated_chunks)
            return finalize(translated_text, "libretranslate", "")
            
    except Exception as e:
        logger.warning(f"Translation engine {engine} failed: {e}. Falling back to Google Translate...")
        warning = f"فشلت الترجمة باستخدام {engine} بسبب: {str(e)}. تم استخدام مترجم جوجل كبديل."
        translated_text, method, google_warning = await translate_text_to_arabic_google(text)
        if google_warning:
            warning = f"{warning} {google_warning}".strip()
        return finalize(translated_text, method or "google", warning)

    # Fallback to google directly if "google" engine is selected
    translated_text, method, warning = await translate_text_to_arabic_google(text)
    return finalize(translated_text, method, warning)

async def translate_text_to_arabic_google(text: str) -> tuple[str, str, str]:
    """
    Translates text to Arabic using Google Translate (via deep-translator).
    Chunks are translated sequentially with retries to avoid rate-limit drops.
    """
    translator = GoogleTranslator(source='auto', target='ar')
    chunks = chunk_text(text, 3000)
    translated_chunks: list[str] = []

    for index, chunk in enumerate(chunks):
        last_error = None
        for attempt in range(4):
            try:
                result = await asyncio.to_thread(translator.translate, chunk)
                if result and result.strip():
                    translated_chunks.append(result.strip())
                    break
            except Exception as e:
                last_error = e
                await asyncio.sleep(0.8 * (attempt + 1))
        else:
            logger.error(f"Translation chunk {index + 1}/{len(chunks)} failed: {last_error}")
            translated_chunks.append(f"\n{TRANSLATION_ERROR_MARKER}: {last_error}]\n")

        if index + 1 < len(chunks):
            await asyncio.sleep(0.35)

    translated_text = "\n\n".join(translated_chunks)
    warning = assess_translation_completeness(text, translated_text) or ""
    return translated_text, "google", warning

def time_to_seconds(t_str: str) -> float:
    try:
        parts = t_str.split(':')
        if len(parts) == 3:
            h = int(parts[0])
            m = int(parts[1])
            s_parts = parts[2].split('.')
            s = int(s_parts[0])
            ms = int(s_parts[1])
            return h * 3600 + m * 60 + s + ms / 1000.0
        elif len(parts) == 2:
            m = int(parts[0])
            s_parts = parts[1].split('.')
            s = int(s_parts[0])
            ms = int(s_parts[1])
            return m * 60 + s + ms / 1000.0
        return 0.0
    except Exception:
        return 0.0

def seconds_to_time(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    ms = int(round((secs - int(secs)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def shift_vtt_timestamps(vtt_content: str, shift_seconds: float) -> str:
    lines = vtt_content.split('\n')
    new_lines = []
    for line in lines:
        if '-->' in line:
            parts = line.split('-->')
            start = time_to_seconds(parts[0].strip())
            end = time_to_seconds(parts[1].strip())
            new_start = start + shift_seconds
            new_end = end + shift_seconds
            new_lines.append(f"{seconds_to_time(new_start)} --> {seconds_to_time(new_end)}")
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)

async def generate_tts_edge(text: str, voice: str, output_path: str, rate: str = "+0%", vtt_path: Optional[str] = None):
    """
    Generates an MP3 file using Microsoft Edge's natural voices, with custom speech rate.
    Injects paragraph pauses (1.0s) and heading pauses (1.5s) using pydub audio stitching
    and generates matching synchronized VTT subtitles.
    """
    if AudioSegment is None:
        import edge_tts

        if not text.strip():
            raise ValueError("Text content is empty.")
        await edge_tts.Communicate(text[:3000], voice, rate=rate).save(output_path)
        logger.info(f"Generated TTS (simple mode, no ffmpeg) to {output_path}")
        return
    import edge_tts

    if not text.strip():
        raise ValueError("Text content is empty.")
    
    # Preprocess punctuation: Ensure clean punctuation spacing for natural pauses
    text = re.sub(r'\s*([،,.؛?؟!])\s*', r'\1 ', text)
    
    # Split text into paragraphs (separated by newlines)
    raw_paras = [p.strip() for p in text.split('\n') if p.strip()]
    
    # Split any paragraph that exceeds 3000 chars into sentence chunks to stay under Edge TTS limits
    paras = []
    for p in raw_paras:
        if len(p) > 3000:
            sentences = re.split(r'(?<=[.،؟?!])\s+', p)
            for s in sentences:
                if s.strip():
                    paras.append(s.strip())
        else:
            paras.append(p)
        
    combined_audio = AudioSegment.empty()
    vtt_parts = ["WEBVTT\n"]
    current_offset_ms = 0
    
    # Silence definitions
    pause_heading = AudioSegment.silent(duration=1500)
    pause_para = AudioSegment.silent(duration=1000)
    
    for idx, para in enumerate(paras):
        if not para.strip():
            continue
            
        chunk_data = io.BytesIO()
        submaker = edge_tts.SubMaker()
        communicate = edge_tts.Communicate(para, voice, rate=rate)
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunk_data.write(chunk["data"])
            elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                submaker.feed(chunk)
                
        if chunk_data.tell() > 0:
            chunk_data.seek(0)
            try:
                segment = AudioSegment.from_file(chunk_data, format="mp3")
                combined_audio += segment
                
                # Fetch VTT for this paragraph and shift timestamps
                if vtt_path:
                    vtt_text = submaker.get_vtt()
                    if vtt_text:
                        vtt_body = vtt_text.replace("WEBVTT\n\n", "").strip()
                        if vtt_body:
                            shifted_vtt = shift_vtt_timestamps(vtt_body, current_offset_ms / 1000.0)
                            vtt_parts.append(shifted_vtt)
                
                # Update offset for next segment
                current_offset_ms += len(segment)
                
                # Check if paragraph is a heading or a regular paragraph
                is_heading = (idx == 0) or (len(para) < 100 and not para.endswith('.') and not para.endswith('。') and not para.endswith('!'))
                if is_heading:
                    combined_audio += pause_heading
                    current_offset_ms += 1500
                else:
                    combined_audio += pause_para
                    current_offset_ms += 1000
            except Exception as e:
                logger.error(f"Error decoding TTS chunk or VTT: {e}")

    if len(combined_audio) == 0:
        import edge_tts

        await edge_tts.Communicate(text[:3000], voice, rate=rate).save(output_path)
        logger.info(f"Generated TTS (simple fallback) to {output_path}")
        return

    if len(combined_audio) > 0:
        # Export as single clean MP3 file
        combined_audio.export(output_path, format="mp3")
        logger.info(f"Successfully generated merged TTS audio to {output_path}")
        
        # Write VTT subtitles file
        if vtt_path and len(vtt_parts) > 1:
            with open(vtt_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(vtt_parts))
            logger.info(f"Successfully generated matched VTT subtitles to {vtt_path}")
