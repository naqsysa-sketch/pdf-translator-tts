import os

import utils  # noqa: F401 — loads .env on import


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_registration_allowed() -> bool:
    return env_flag("ALLOW_REGISTRATION", default=True)


def get_registration_secret() -> str:
    return os.getenv("REGISTRATION_SECRET", "").strip()


def get_configured_engines() -> dict[str, bool]:
    claude_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
    return {
        "gemini": bool(os.getenv("GEMINI_API_KEY", "").strip()),
        "deepl": bool(os.getenv("DEEPL_API_KEY", "").strip()),
        "openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "claude": bool(claude_key.strip()),
        "libretranslate": bool(os.getenv("LIBRETRANSLATE_API_KEY", "").strip()),
    }


def all_server_api_keys_configured() -> bool:
    engines = get_configured_engines()
    return all(engines[key] for key in ("gemini", "deepl", "openai", "claude"))


def get_public_config() -> dict:
    registration_secret = get_registration_secret()
    return {
        "allow_registration": is_registration_allowed(),
        "requires_registration_secret": bool(registration_secret),
        "configured_engines": get_configured_engines(),
        "hide_client_api_keys": all_server_api_keys_configured(),
    }
