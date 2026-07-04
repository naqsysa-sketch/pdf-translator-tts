"""
End-to-end API tests against a running deployment.

Requires:
  E2E_BASE_URL   (default: https://pdf-translator-tts.vercel.app)
  E2E_USERNAME   (default: owner)
  E2E_PASSWORD   (required — set in env, never commit)

Run:
  E2E_PASSWORD=... python -m pytest tests/test_e2e_api.py -v -s
"""

import os
import time

import pytest
import requests

from scripts.make_test_pdf import build_test_pdf

BASE_URL = os.getenv("E2E_BASE_URL", "https://pdf-translator-tts.vercel.app").rstrip("/")
USERNAME = os.getenv("E2E_USERNAME", "owner")
PASSWORD = os.getenv("E2E_PASSWORD", "")
POLL_INTERVAL = 3
PROCESS_TIMEOUT = 120
TRANSLATE_TIMEOUT = 180
TTS_TIMEOUT = 180


pytestmark = pytest.mark.skipif(
    not PASSWORD,
    reason="Set E2E_PASSWORD to run live E2E tests",
)


@pytest.fixture(scope="module")
def pdf_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("pdf") / "e2e_sample.pdf"
    build_test_pdf(str(path))
    assert path.stat().st_size < 4 * 1024 * 1024, "E2E PDF must stay under Vercel upload limit"
    return str(path)


@pytest.fixture(scope="module")
def auth_headers():
    res = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        timeout=60,
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _poll(predicate, timeout: int, label: str):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last is not None:
            return last
        time.sleep(POLL_INTERVAL)
    pytest.fail(f"Timeout waiting for {label} (last={last})")


def test_health():
    res = requests.get(f"{BASE_URL}/api/health", timeout=60)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert body["database"] == "up"


def test_config_upload_limit():
    res = requests.get(f"{BASE_URL}/api/config", timeout=30)
    assert res.status_code == 200
    body = res.json()
    assert body["max_upload_bytes"] <= 10 * 1024 * 1024
    assert body["max_upload_mb"] >= 1


def test_auth_me(auth_headers):
    res = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers, timeout=30)
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == USERNAME
    if USERNAME == "owner":
        assert body["is_admin"] is True


def test_upload_process_translate_tts(auth_headers, pdf_path):
    with open(pdf_path, "rb") as f:
        res = requests.post(
            f"{BASE_URL}/api/upload",
            headers=auth_headers,
            files={"file": ("e2e_sample.pdf", f, "application/pdf")},
            data={"source_lang": "en"},
            timeout=120,
        )
    assert res.status_code == 200, res.text
    upload = res.json()
    assert upload["success"] is True
    project_id = upload["project_id"]

    def project_ready():
        r = requests.get(
            f"{BASE_URL}/api/projects/{project_id}",
            headers=auth_headers,
            timeout=60,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if data["status"] == "failed":
            pytest.fail(f"Project processing failed: {data}")
        if data["status"] == "completed" and data.get("chapters"):
            return data
        return None

    project = _poll(project_ready, PROCESS_TIMEOUT, "PDF chapter extraction")
    chapters = project["chapters"]
    assert len(chapters) >= 1
    chapter = chapters[0]
    assert chapter["original_text"].strip()

    tr = requests.post(
        f"{BASE_URL}/api/translate",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"chapter_id": chapter["id"], "engine": "google"},
        timeout=TRANSLATE_TIMEOUT,
    )
    assert tr.status_code == 200, tr.text

    def translation_done():
        r = requests.get(
            f"{BASE_URL}/api/projects/{project_id}",
            headers=auth_headers,
            timeout=60,
        )
        ch = r.json()["chapters"][0]
        if ch["translation_status"] == "failed":
            pytest.fail(f"Translation failed: {ch}")
        if ch["translation_status"] == "completed" and ch.get("translated_text"):
            return ch
        return None

    translated = _poll(translation_done, TRANSLATE_TIMEOUT, "chapter translation")
    assert any("\u0600" <= c <= "\u06FF" for c in translated["translated_text"]), "Expected Arabic text"

    preview = requests.post(
        f"{BASE_URL}/api/tts",
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"chapter_id": -1, "voice": "ar-SA-HamedNeural", "rate": "+0%"},
        timeout=TTS_TIMEOUT,
    )
    assert preview.status_code == 200, preview.text
    audio = preview.json()
    assert audio.get("success") is True
    assert audio.get("audio_url")

    # Cleanup: delete project (owner is admin)
    if USERNAME == "owner":
        dr = requests.delete(
            f"{BASE_URL}/api/admin/projects/{project_id}",
            headers=auth_headers,
            timeout=30,
        )
        assert dr.status_code == 200, dr.text
