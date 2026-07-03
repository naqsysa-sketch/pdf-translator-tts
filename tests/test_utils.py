import json
import os

import fitz
import pytest

from utils import (
    calculate_text_hash,
    chunk_text,
    extract_chapters_from_pdf,
    get_cached_translation,
    save_translation_to_cache,
)


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr("utils.CACHE_DIR", str(cache_dir))
    yield cache_dir


def test_calculate_text_hash_is_stable():
    text = "Hello chapter"
    assert calculate_text_hash(text) == calculate_text_hash(text)
    assert calculate_text_hash(text) != calculate_text_hash("Different text")


def test_cache_roundtrip_for_gemini_engine():
    source = "Sample paragraph for translation."
    translated = "فقرة نموذجية للترجمة."
    save_translation_to_cache(source, translated, "gemini", "gemini-1.5-flash")

    cached_text, cached_method = get_cached_translation(source, "gemini", "gemini-1.5-flash")
    assert cached_text == translated
    assert cached_method == "gemini"


def test_non_google_engine_does_not_reuse_google_cache():
    source = "Another sample paragraph."
    save_translation_to_cache(source, "ترجمة جوجل", "google", "")

    cached_text, cached_method = get_cached_translation(source, "openai", "gpt-4o-mini")
    assert cached_text is None
    assert cached_method is None


def test_google_engine_accepts_any_cached_translation():
    source = "Fallback sample."
    save_translation_to_cache(source, "ترجمة بديلة", "deepl", "")

    cached_text, cached_method = get_cached_translation(source, "google")
    assert cached_text == "ترجمة بديلة"
    assert cached_method == "deepl"


def test_chunk_text_respects_max_chars():
    text = "A\n" * 20
    chunks = chunk_text(text, max_chars=10)
    assert len(chunks) >= 2
    assert all(len(chunk) <= 10 for chunk in chunks)


def test_extract_chapters_from_pdf_by_heading(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 750)
    page.insert_textbox(
        rect,
        "Chapter 1: The Beginning\nFirst chapter body text.\n\n"
        "Chapter 2: The Journey\nSecond chapter body text.",
    )
    doc.save(pdf_path)
    doc.close()

    chapters = extract_chapters_from_pdf(str(pdf_path))
    assert len(chapters) >= 2
    assert "Chapter 1" in chapters[0]["title"] or "Beginning" in chapters[0]["title"]
    assert chapters[0]["text"].strip()
    assert chapters[1]["text"].strip()
