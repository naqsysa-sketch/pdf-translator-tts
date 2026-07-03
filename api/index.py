"""
Vercel serverless entrypoint for FastAPI.
See VERCEL.md for environment variables.
"""
import os
import sys

from fastapi import FastAPI

os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/pdf_translator.db")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

app = FastAPI()

from app import app as _main_app  # noqa: E402

app = _main_app
