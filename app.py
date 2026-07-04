import os
import shutil
import uuid
import hashlib
import time
import threading
import asyncio
import logging
import zipfile
import io
import requests
from collections import defaultdict
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# Initialize Sentry if DSN is set
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
    )

logger = logging.getLogger("pdf_translator.server")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
from database import engine, get_db, ensure_schema_updates
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_admin,
    is_admin_user,
)
from config import (
    get_max_upload_bytes,
    get_public_config,
    get_registration_secret,
    is_registration_allowed,
)
from tasks import process_pdf_task, translate_chapter_task, generate_tts_task, reextract_pdf_task
from utils import generate_tts_edge, build_arabic_translation_pdf
from storage import (
    upload_file_to_s3,
    resolve_media_url,
    read_stored_file,
    is_s3_ref,
    get_outputs_dir,
)

# Ensure database tables exist
models.Base.metadata.create_all(bind=engine)
ensure_schema_updates()

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(lambda: defaultdict(list))
        self.lock = threading.Lock()

    def check_rate_limit(self, ip: str, route_key: str, limit: int, window: int) -> bool:
        now = time.time()
        with self.lock:
            self.requests[route_key][ip] = [t for t in self.requests[route_key][ip] if now - t < window]
            if len(self.requests[route_key][ip]) >= limit:
                return False
            self.requests[route_key][ip].append(now)
            
            if len(self.requests[route_key]) > 1000:
                for key in list(self.requests[route_key].keys()):
                    if not self.requests[route_key][key]:
                        del self.requests[route_key][key]
            return True

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.limiter = RateLimiter()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        if path.startswith("/api/"):
            if path == "/api/upload":
                limit, window = 5, 60
                err_msg = "لقد تجاوزت حد رفع الملفات المسموح به (5 ملفات في الدقيقة). يرجى الانتظار دقيقة والمحاولة مجدداً."
            elif path == "/api/translate":
                limit, window = 30, 60
                err_msg = "لقد تجاوزت حد طلبات الترجمة المسموح به (30 طلب في الدقيقة). يرجى الانتظار دقيقة والمحاولة مجدداً."
            elif path == "/api/tts":
                limit, window = 30, 60
                err_msg = "لقد تجاوزت حد طلبات تحويل النص إلى صوت المسموح به (30 طلب في الدقيقة). يرجى الانتظار دقيقة والمحاولة مجدداً."
            elif path == "/api/auth/register":
                limit, window = 3, 3600
                err_msg = "لقد تجاوزت حد محاولات التسجيل المسموح بها. يرجى المحاولة لاحقاً."
            else:
                limit, window = 60, 60
                err_msg = "لقد تجاوزت حد الطلبات المسموح به. يرجى المحاولة لاحقاً."

            if not self.limiter.check_rate_limit(client_ip, path, limit, window):
                return JSONResponse(
                    status_code=429,
                    content={"detail": err_msg}
                )
        return await call_next(request)

app = FastAPI(title="PDF Splitter, Translator & TTS")

_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = get_outputs_dir()
UPLOAD_DIR = "/tmp/uploads" if os.getenv("VERCEL") else os.path.join(BASE_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.get("/api/media/{filename}")
def serve_media_file(filename: str):
    """Serve generated audio/subtitles from writable storage (required on Vercel /tmp)."""
    import re

    if not re.fullmatch(r"[\w.\-]+", filename):
        raise HTTPException(status_code=404, detail="الملف غير موجود.")
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="الملف غير موجود.")
    if filename.endswith(".mp3"):
        media_type = "audio/mpeg"
    elif filename.endswith(".vtt"):
        media_type = "text/vtt"
    else:
        media_type = "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=filename)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Pydantic Schemas
class UserRegister(BaseModel):
    username: str
    password: str
    registration_secret: Optional[str] = None

# --- Public configuration ---

@app.get("/api/config")
def get_app_config():
    return get_public_config()

# --- Authentication API ---

@app.post("/api/auth/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    if not is_registration_allowed():
        raise HTTPException(
            status_code=403,
            detail="التسجيل مغلق حالياً. يرجى التواصل مع مسؤول النظام.",
        )

    required_secret = get_registration_secret()
    if required_secret and user_data.registration_secret != required_secret:
        raise HTTPException(status_code=403, detail="رمز التسجيل غير صحيح.")

    if len(user_data.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="اسم المستخدم يجب أن يكون 3 أحرف على الأقل.")
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 6 أحرف على الأقل.")

    existing_user = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="اسم المستخدم مسجل مسبقاً.")
    hashed_pwd = get_password_hash(user_data.password)
    new_user = models.User(username=user_data.username, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    return {"success": True, "message": "تم تسجيل الحساب بنجاح!"}

class TranslateRequest(BaseModel):
    chapter_id: int
    engine: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    custom_host: Optional[str] = None

class TTSRequest(BaseModel):
    chapter_id: int
    voice: str
    rate: Optional[str] = "+0%"

class ChapterUpdateRequest(BaseModel):
    translated_text: str


class ReExtractRequest(BaseModel):
    page_from: Optional[int] = None
    page_to: Optional[int] = None


def serialize_chapter(chapter: models.Chapter) -> dict:
    return {
        "id": chapter.id,
        "chapter_num": chapter.chapter_num,
        "title": chapter.title,
        "original_text": chapter.original_text,
        "translated_text": chapter.translated_text,
        "translation_status": chapter.translation_status,
        "translation_engine": chapter.translation_engine,
        "translation_warning": chapter.translation_warning,
        "audio_url": resolve_media_url(chapter.audio_url),
        "vtt_url": resolve_media_url(chapter.vtt_url),
        "tts_status": chapter.tts_status,
        "tts_voice": chapter.tts_voice,
        "tts_rate": chapter.tts_rate,
        "start_page": chapter.start_page,
        "end_page": chapter.end_page,
    }

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    username = form_data.username.strip()
    password = form_data.password
    user = db.query(models.User).filter(func.lower(models.User.username) == username.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="اسم المستخدم أو كلمة المرور غير صحيحة.")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "username": current_user.username,
        "is_admin": is_admin_user(current_user),
    }

# --- Project Management API ---

@app.get("/api/projects")
def list_projects(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(models.Project).filter(models.Project.user_id == current_user.id).order_by(models.Project.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "filename": p.filename,
            "status": p.status,
            "created_at": p.created_at.isoformat()
        } for p in projects
    ]

@app.get("/api/projects/{project_id}")
def get_project(project_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود.")
    
    chapters = db.query(models.Chapter).filter(models.Chapter.project_id == project_id).order_by(models.Chapter.chapter_num.asc()).all()
    
    return {
        "id": project.id,
        "filename": project.filename,
        "status": project.status,
        "created_at": project.created_at.isoformat(),
        "has_stored_pdf": bool(project.pdf_storage_ref),
        "chapters": [serialize_chapter(c) for c in chapters]
    }

@app.post("/api/upload")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    source_lang: str = Form("auto"),
    page_from: Optional[int] = Form(None),
    page_to: Optional[int] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content_length = request.headers.get("content-length")
    max_file_size = get_max_upload_bytes()
    max_mb = round(max_file_size / (1024 * 1024), 1)
    size_error = f"حجم الملف كبير جداً. الحد الأقصى المسموح به هو {max_mb:g} ميجابايت."
    if content_length:
        try:
            if int(content_length) > max_file_size:
                raise HTTPException(status_code=413, detail=size_error)
        except ValueError:
            pass

    file.file.seek(0, 2)
    actual_size = file.file.tell()
    file.file.seek(0)

    if actual_size > max_file_size:
        raise HTTPException(status_code=413, detail=size_error)

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    if page_from is not None and page_from < 1:
        raise HTTPException(status_code=400, detail="رقم صفحة البداية يجب أن يكون 1 أو أكثر.")
    if page_to is not None and page_to < 1:
        raise HTTPException(status_code=400, detail="رقم صفحة النهاية يجب أن يكون 1 أو أكثر.")
    if page_from is not None and page_to is not None and page_from > page_to:
        raise HTTPException(status_code=400, detail="صفحة البداية يجب أن تكون أصغر من أو تساوي صفحة النهاية.")

    project_id = str(uuid.uuid4())
    pdf_path = os.path.join(UPLOAD_DIR, f"{project_id}.pdf")
    
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    project = models.Project(
        id=project_id,
        filename=file.filename,
        status="processing",
        user_id=current_user.id
    )
    db.add(project)
    db.commit()
    
    process_pdf_task.delay(project_id, pdf_path, source_lang, page_from, page_to)
    
    return {
        "success": True,
        "project_id": project_id,
        "filename": file.filename,
        "page_from": page_from,
        "page_to": page_to,
    }


@app.post("/api/projects/{project_id}/re-extract")
def reextract_project(
    project_id: str,
    request: ReExtractRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود.")
    if not project.pdf_storage_ref:
        raise HTTPException(
            status_code=400,
            detail="ملف PDF الأصلي غير محفوظ لهذا المشروع. ارفع الكتاب مجدداً مع تخزين سحابي مفعّل.",
        )
    if request.page_from is not None and request.page_from < 1:
        raise HTTPException(status_code=400, detail="رقم صفحة البداية غير صالح.")
    if request.page_to is not None and request.page_to < 1:
        raise HTTPException(status_code=400, detail="رقم صفحة النهاية غير صالح.")
    if (
        request.page_from is not None
        and request.page_to is not None
        and request.page_from > request.page_to
    ):
        raise HTTPException(status_code=400, detail="نطاق الصفحات غير صالح.")

    project.status = "processing"
    db.commit()
    reextract_pdf_task.delay(project_id, request.page_from, request.page_to)
    return {
        "success": True,
        "message": "بدأت إعادة تقسيم الكتاب حسب نطاق الصفحات المحدد.",
    }

@app.patch("/api/chapters/{chapter_id}")
def update_chapter_translation(
    chapter_id: int,
    request: ChapterUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chapter = db.query(models.Chapter).join(models.Project).filter(
        models.Chapter.id == chapter_id,
        models.Project.user_id == current_user.id
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود.")

    chapter.translated_text = request.translated_text.strip()
    if chapter.translated_text:
        chapter.translation_status = "completed"
        if not chapter.translation_engine:
            chapter.translation_engine = "manual"
    db.commit()
    return {"success": True, "message": "تم حفظ الترجمة المعدّلة."}

@app.post("/api/translate")
def translate_chapter(
    request: TranslateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chapter = db.query(models.Chapter).join(models.Project).filter(
        models.Chapter.id == request.chapter_id,
        models.Project.user_id == current_user.id
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود.")
        
    chapter.translation_status = "processing"
    db.commit()
    
    translate_chapter_task.delay(
        chapter_id=request.chapter_id,
        engine=request.engine,
        api_key=request.api_key,
        model=request.model,
        custom_host=request.custom_host
    )
    
    return {"success": True, "message": "بدأت عملية الترجمة في الخلفية."}

@app.post("/api/tts")
async def generate_audio(
    request: TTSRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.chapter_id == -1:
        test_text = "مرحباً بك! هذا تسجيل تجريبي للتأكد من جودة ونبرة الصوت المختار لتوليد كتابك الصوتي."
        payload_str = f"PREVIEW|||{test_text}|||{request.voice}|||{request.rate}"
        file_hash = hashlib.sha256(payload_str.encode('utf-8', errors='ignore')).hexdigest()
        
        audio_filename = f"preview_{file_hash}.mp3"
        audio_path = os.path.join(OUTPUT_DIR, audio_filename)
        
        if not os.path.exists(audio_path):
            try:
                await generate_tts_edge(test_text, request.voice, audio_path, request.rate or "+0%")
            except Exception as e:
                logger.error(f"Voice preview failed: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")
                
        s3_ref = upload_file_to_s3(audio_path, f"previews/{audio_filename}", "audio/mpeg")
        return {
            "success": True,
            "audio_url": resolve_media_url(s3_ref)
        }

    chapter = db.query(models.Chapter).join(models.Project).filter(
        models.Chapter.id == request.chapter_id,
        models.Project.user_id == current_user.id
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود.")
        
    if not chapter.translated_text:
        raise HTTPException(status_code=400, detail="يرجى ترجمة الفصل أولاً.")
        
    chapter.tts_status = "processing"
    db.commit()
    
    generate_tts_task.delay(
        chapter_id=request.chapter_id,
        voice=request.voice,
        rate=request.rate
    )
    
    return {"success": True, "message": "بدأت عملية تحويل الصوت في الخلفية."}


def _translated_sections(chapters) -> list[tuple[str, str]]:
    sections = []
    for ch in chapters:
        if ch.translated_text and ch.translated_text.strip():
            title = f"الفصل {ch.chapter_num}: {ch.title}" if ch.title else f"الفصل {ch.chapter_num}"
            sections.append((title, ch.translated_text))
    return sections


def _pdf_streaming_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/chapters/{chapter_id}/export-pdf")
def export_chapter_pdf(
    chapter_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chapter = db.query(models.Chapter).join(models.Project).filter(
        models.Chapter.id == chapter_id,
        models.Project.user_id == current_user.id,
    ).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود.")
    if not chapter.translated_text or not chapter.translated_text.strip():
        raise HTTPException(status_code=400, detail="يرجى ترجمة الفصل أولاً.")

    title = f"الفصل {chapter.chapter_num}: {chapter.title}" if chapter.title else f"الفصل {chapter.chapter_num}"
    try:
        pdf_bytes = build_arabic_translation_pdf([(title, chapter.translated_text)])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _pdf_streaming_response(pdf_bytes, f"Chapter_{chapter.chapter_num}_Arabic.pdf")


@app.get("/api/projects/{project_id}/export-pdf")
def export_project_pdf(
    project_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id,
        models.Project.user_id == current_user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود.")

    chapters = (
        db.query(models.Chapter)
        .filter(models.Chapter.project_id == project_id)
        .order_by(models.Chapter.chapter_num.asc())
        .all()
    )
    sections = _translated_sections(chapters)
    if not sections:
        raise HTTPException(status_code=400, detail="لا توجد فصول مترجمة لتصديرها كـ PDF.")

    book_title = project.filename or f"مشروع {project_id}"
    try:
        pdf_bytes = build_arabic_translation_pdf(sections, book_title=book_title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in book_title)[:80] or project_id
    return _pdf_streaming_response(pdf_bytes, f"{safe_name}_Arabic.pdf")


@app.get("/api/projects/{project_id}/export-zip")
def export_project_zip(
    project_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود.")
        
    chapters = db.query(models.Chapter).filter(models.Chapter.project_id == project_id).order_by(models.Chapter.chapter_num.asc()).all()
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for ch in chapters:
            if ch.translated_text and ch.translated_text.strip():
                txt_filename = f"Chapter_{ch.chapter_num}_Arabic.txt"
                zip_file.writestr(txt_filename, ch.translated_text)
                title = f"الفصل {ch.chapter_num}: {ch.title}" if ch.title else f"الفصل {ch.chapter_num}"
                try:
                    pdf_bytes = build_arabic_translation_pdf([(title, ch.translated_text)])
                    zip_file.writestr(f"Chapter_{ch.chapter_num}_Arabic.pdf", pdf_bytes)
                except ValueError:
                    pass
                
            if ch.audio_url:
                audio_data = read_stored_file(ch.audio_url, OUTPUT_DIR)
                if audio_data:
                    zip_file.writestr(f"Chapter_{ch.chapter_num}_Arabic.mp3", audio_data)

        sections = _translated_sections(chapters)
        if sections:
            book_title = project.filename or f"project_{project_id}"
            try:
                full_pdf = build_arabic_translation_pdf(sections, book_title=book_title)
                zip_file.writestr("Book_Arabic_Full.pdf", full_pdf)
            except ValueError:
                pass
                    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=project_{project_id}.zip"}
    )

@app.post("/api/projects/{project_id}/export-audiobook")
async def export_project_audiobook(
    project_id: str,
    pause_seconds: int = Form(2),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from pydub import AudioSegment
    
    project = db.query(models.Project).filter(models.Project.id == project_id, models.Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود.")
        
    chapters = db.query(models.Chapter).filter(models.Chapter.project_id == project_id).order_by(models.Chapter.chapter_num.asc()).all()
    
    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=(pause_seconds or 2) * 1000)
    
    valid_audios = 0
    for ch in chapters:
        if not ch.audio_url:
            continue

        raw_audio = await asyncio.to_thread(read_stored_file, ch.audio_url, OUTPUT_DIR)
        if not raw_audio:
            continue

        try:
            audio_buffer = io.BytesIO(raw_audio)
            segment = await asyncio.to_thread(AudioSegment.from_file, audio_buffer, format="mp3")
            if valid_audios > 0:
                combined += pause
            combined += segment
            valid_audios += 1
        except Exception as e:
            logger.error(f"Error loading segment: {e}")
                
    if valid_audios == 0:
        raise HTTPException(status_code=400, detail="لا توجد فصول مجهزة بملفات صوتية للدمج.")
        
    audiobook_filename = f"audiobook_{uuid.uuid4()}.mp3"
    audiobook_path = os.path.join(OUTPUT_DIR, audiobook_filename)
    
    await asyncio.to_thread(combined.export, audiobook_path, format="mp3")

    s3_ref = upload_file_to_s3(audiobook_path, f"audiobooks/{audiobook_filename}", "audio/mpeg")

    if is_s3_ref(s3_ref) and os.path.exists(audiobook_path):
        os.remove(audiobook_path)

    return {
        "success": True,
        "audiobook_url": resolve_media_url(s3_ref)
    }

# --- Admin API ---

@app.get("/api/admin/stats")
def admin_stats(
    admin_user: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return {
        "users_count": db.query(models.User).count(),
        "projects_count": db.query(models.Project).count(),
        "chapters_count": db.query(models.Chapter).count(),
        "completed_translations": db.query(models.Chapter).filter(models.Chapter.translation_status == "completed").count(),
        "completed_tts": db.query(models.Chapter).filter(models.Chapter.tts_status == "completed").count(),
    }


@app.get("/api/admin/users")
def admin_list_users(
    admin_user: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(models.User).order_by(models.User.id.asc()).all()
    result = []
    for user in users:
        project_count = db.query(models.Project).filter(models.Project.user_id == user.id).count()
        result.append({
            "id": user.id,
            "username": user.username,
            "is_admin": is_admin_user(user),
            "projects_count": project_count,
        })
    return result


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    admin_user: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="لا يمكنك حذف حسابك الحالي.")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود.")
    if is_admin_user(user):
        raise HTTPException(status_code=400, detail="لا يمكن حذف حساب مسؤول.")
    db.delete(user)
    db.commit()
    return {"success": True, "message": "تم حذف المستخدم."}


@app.get("/api/admin/projects")
def admin_list_projects(
    admin_user: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(models.Project, models.User.username)
        .join(models.User, models.Project.user_id == models.User.id)
        .order_by(models.Project.created_at.desc())
        .all()
    )
    return [
        {
            "id": project.id,
            "filename": project.filename,
            "status": project.status,
            "owner": username,
            "created_at": project.created_at.isoformat(),
        }
        for project, username in rows
    ]


@app.delete("/api/admin/projects/{project_id}")
def admin_delete_project(
    project_id: str,
    admin_user: models.User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="المشروع غير موجود.")
    db.delete(project)
    db.commit()
    return {"success": True, "message": "تم حذف المشروع."}

# --- System Health & Monitoring API ---

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    health_status = {"status": "healthy", "database": "up", "redis": "up"}
    try:
        db.execute(func.now())
    except Exception as e:
        health_status["database"] = f"down: {str(e)}"
        health_status["status"] = "unhealthy"

    if os.getenv("VERCEL"):
        health_status["redis"] = "skipped (serverless)"
        return health_status

    import redis
    try:
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
    except Exception as e:
        health_status["redis"] = f"down: {str(e)}"
        health_status["status"] = "unhealthy"
        
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=500, detail=health_status)
    return health_status

# --- Static Files Mount ---

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def redirect_to_index():
    return RedirectResponse(url="/static/index.html")

async def cleanup_old_files():
    while True:
        try:
            cleanup_hours = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))
            max_age_seconds = cleanup_hours * 3600
            now = time.time()

            if os.path.exists(UPLOAD_DIR):
                for filename in os.listdir(UPLOAD_DIR):
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    if os.path.isdir(file_path):
                        continue
                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            try:
                                os.remove(file_path)
                                logger.info(f"Cleanup: Removed old upload file {filename}")
                            except Exception as e:
                                logger.error(f"Cleanup: Failed to remove {filename}: {e}")

            if os.path.exists(OUTPUT_DIR):
                for filename in os.listdir(OUTPUT_DIR):
                    file_path = os.path.join(OUTPUT_DIR, filename)
                    if os.path.isfile(file_path) and filename.endswith(".mp3"):
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            try:
                                os.remove(file_path)
                                logger.info(f"Cleanup: Removed old audio file {filename}")
                            except Exception as e:
                                logger.error(f"Cleanup: Failed to remove {filename}: {e}")
        except Exception as e:
            logger.error(f"Error in cleanup background task: {e}")
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    if not os.getenv("VERCEL"):
        asyncio.create_task(cleanup_old_files())
