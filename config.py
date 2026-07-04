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


def get_max_upload_bytes() -> int:
    raw_mb = os.getenv("MAX_UPLOAD_MB", "").strip()
    if raw_mb:
        return int(float(raw_mb) * 1024 * 1024)
    # Vercel serverless rejects request bodies above ~4.5 MB before the app runs.
    if os.getenv("VERCEL"):
        return 4 * 1024 * 1024
    return 10 * 1024 * 1024


def get_public_config() -> dict:
    registration_secret = get_registration_secret()
    max_upload_bytes = get_max_upload_bytes()
    from storage import supabase_storage_configured

    storage_backend = "local"
    if supabase_storage_configured():
        storage_backend = "supabase"
    elif os.getenv("S3_ACCESS_KEY") and os.getenv("S3_SECRET_KEY"):
        storage_backend = "s3"

    return {
        "allow_registration": is_registration_allowed(),
        "requires_registration_secret": bool(registration_secret),
        "configured_engines": get_configured_engines(),
        "hide_client_api_keys": all_server_api_keys_configured(),
        "max_upload_bytes": max_upload_bytes,
        "max_upload_mb": round(max_upload_bytes / (1024 * 1024), 1),
        "storage_backend": storage_backend,
    }
