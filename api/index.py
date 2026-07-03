"""
Vercel serverless entrypoint for FastAPI.
Set environment variables in the Vercel dashboard (see VERCEL.md).
"""
import os
import sys

os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/pdf_translator.db")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app  # noqa: E402
