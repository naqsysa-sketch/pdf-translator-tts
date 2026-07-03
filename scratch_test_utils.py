import asyncio
import os
import time
import sys
from utils import extract_chapters_from_pdf, translate_text_to_arabic, generate_tts_edge

async def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
        
    print("Testing extract_chapters_from_pdf...")
    chapters = extract_chapters_from_pdf("test.pdf")
    print(f"Extracted {len(chapters)} chapters:")
    for ch in chapters:
        print(f"  - Chapter {ch['id']}: {ch['title']} (Pages {ch['start_page']}-{ch['end_page']})")
        print(f"    Text snippet: {ch['text'][:100]}...")

    if not chapters:
        print("No chapters found, exiting test.")
        return

    chapter_text = chapters[0]['text']
    
    print("\nTesting translate_text_to_arabic (with Caching)...")
    # First translation (might hit cache if run previously, let's clear cache first for clean test)
    from utils import CACHE_DIR, calculate_text_hash
    text_hash = calculate_text_hash(chapter_text)
    cache_file = os.path.join(CACHE_DIR, f"{text_hash}.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print("Cleared previous cache for clean testing.")
        
    t0 = time.time()
    translated, method, warning = await translate_text_to_arabic(chapter_text, "google")
    t1 = time.time()
    print(f"First translation (Cache Miss) took {t1 - t0:.4f} seconds. Method: {method}")

    t2 = time.time()
    translated2, method2, warning2 = await translate_text_to_arabic(chapter_text, "google")
    t3 = time.time()
    print(f"Second translation (Cache Hit) took {t3 - t2:.4f} seconds. Method: {method2}")
    
    if (t3 - t2) < 0.05:
        print("SUCCESS: Cache hit confirmed (under 0.05s)!")
    else:
        print("WARNING: Caching might have failed or taken longer than expected.")

    print(f"Translated Text snippet:\n{translated[:200]}...")

    print("\nTesting generate_tts_edge...")
    os.makedirs("static/outputs", exist_ok=True)
    audio_path = "static/outputs/test_audio.mp3"
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    try:
        await generate_tts_edge(translated, "ar-SA-HamedNeural", audio_path, "+0%")
        print(f"TTS generated successfully, file size: {os.path.getsize(audio_path)} bytes")
    except Exception as e:
        print(f"TTS generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
