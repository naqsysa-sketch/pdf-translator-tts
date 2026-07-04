"""Generate a small PDF for E2E / manual testing."""

import os

import fitz

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")
DEFAULT_PATH = os.path.join(FIXTURES_DIR, "e2e_sample.pdf")


def build_test_pdf(path: str = DEFAULT_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text((72, 72), "Chapter 1: The Beginning\n\n", fontsize=14)
    page1.insert_text(
        (72, 100),
        "This is a short English paragraph for automated end-to-end testing. "
        "The application should extract this chapter and translate it to Arabic.",
        fontsize=11,
    )

    page2 = doc.new_page()
    page2.insert_text((72, 72), "Chapter 2: Continuation\n\n", fontsize=14)
    page2.insert_text(
        (72, 100),
        "A second chapter with additional text for PDF Translator pipeline validation.",
        fontsize=11,
    )

    doc.set_toc(
        [
            [1, "Chapter 1: The Beginning", 1],
            [1, "Chapter 2: Continuation", 2],
        ]
    )
    doc.save(path)
    doc.close()
    return path


if __name__ == "__main__":
    out = build_test_pdf()
    print(f"Created {out} ({os.path.getsize(out)} bytes)")
