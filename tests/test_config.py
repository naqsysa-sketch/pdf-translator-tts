import pytest

import config


def test_public_config_shape(monkeypatch):
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    monkeypatch.setenv("REGISTRATION_SECRET", "invite-123")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)

    payload = config.get_public_config()
    assert payload["allow_registration"] is False
    assert payload["requires_registration_secret"] is True
    assert payload["configured_engines"]["gemini"] is True
    assert payload["configured_engines"]["deepl"] is False


def test_hide_client_api_keys_when_all_main_engines_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g")
    monkeypatch.setenv("DEEPL_API_KEY", "d")
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    monkeypatch.setenv("CLAUDE_API_KEY", "c")
    monkeypatch.delenv("LIBRETRANSLATE_API_KEY", raising=False)

    payload = config.get_public_config()
    assert payload["hide_client_api_keys"] is True


def test_claude_key_from_anthropic_alias(monkeypatch):
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    engines = config.get_configured_engines()
    assert engines["claude"] is True


def test_max_upload_bytes_on_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("MAX_UPLOAD_MB", raising=False)
    assert config.get_max_upload_bytes() == 4 * 1024 * 1024
    payload = config.get_public_config()
    assert payload["max_upload_mb"] == 4


def test_max_upload_bytes_override(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("MAX_UPLOAD_MB", "25")
    assert config.get_max_upload_bytes() == 25 * 1024 * 1024
