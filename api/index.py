"""
Vercel serverless entrypoint for FastAPI.
"""
import os
import sys
import traceback

from fastapi import FastAPI
from fastapi.responses import JSONResponse

os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/pdf_translator.db")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

app = FastAPI()

try:
    from app import app as _main_app
    app = _main_app
except Exception as import_error:
    _BOOT_ERROR = f"{type(import_error).__name__}: {import_error}"
    _BOOT_TRACE = traceback.format_exc()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def boot_error(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server failed to boot",
                "detail": _BOOT_ERROR,
                "trace": _BOOT_TRACE,
            },
        )
