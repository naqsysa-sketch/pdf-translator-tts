import os
import asyncio
import concurrent.futures
import logging
from celery import Celery
from database import SessionLocal
import models
from utils import extract_chapters_from_pdf, translate_text_to_arabic, generate_tts_edge
from storage import upload_file_to_s3, is_s3_ref, is_sb_ref, get_outputs_dir, download_stored_file_to_path

logger = logging.getLogger("pdf_translator.tasks")


def run_async(coro):
    """Run async code from sync Celery tasks (safe inside FastAPI event loop on Vercel)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()

# Broker configuration: Defaults to local Redis, but can point to docker network redis service
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("pdf_translator", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
)

UPLOAD_DIR = "/tmp/uploads" if os.getenv("VERCEL") else os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@celery_app.task
def process_pdf_task(
    project_id: str,
    pdf_path: str,
    source_lang: str = "auto",
    page_from: int | None = None,
    page_to: int | None = None,
):
    """
    Extracts chapters from the PDF file in the background, stores text to database,
    and updates project status.
    """
    db = SessionLocal()
    try:
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found in database.")
            return False
            
        project.status = "processing"
        db.commit()
        
        # Extract chapters
        chapters = extract_chapters_from_pdf(
            pdf_path,
            source_lang=source_lang,
            page_from=page_from,
            page_to=page_to,
        )
        
        for ch in chapters:
            db_chapter = models.Chapter(
                chapter_num=ch["id"],
                project_id=project_id,
                title=ch["title"],
                original_text=ch["text"],
                translation_status="pending",
                tts_status="pending",
                start_page=ch["start_page"],
                end_page=ch["end_page"]
            )
            db.add(db_chapter)
            
        project.status = "completed"

        if os.path.exists(pdf_path):
            try:
                project.pdf_storage_ref = upload_file_to_s3(
                    pdf_path,
                    f"pdfs/{project_id}.pdf",
                    "application/pdf",
                )
            except Exception as exc:
                logger.warning(f"Could not archive PDF for project {project_id}: {exc}")

        db.commit()

        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
        logger.info(f"Successfully processed PDF chapters for project {project_id}")
        return True
    except Exception as e:
        logger.error(f"Error processing PDF task for project {project_id}: {e}")
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if project:
            project.status = "failed"
            db.commit()
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise e
    finally:
        db.close()


@celery_app.task
def reextract_pdf_task(
    project_id: str,
    page_from: int | None = None,
    page_to: int | None = None,
    source_lang: str = "auto",
):
    """Re-split an archived PDF using an optional page range."""
    db = SessionLocal()
    pdf_path = os.path.join(UPLOAD_DIR, f"{project_id}_reextract.pdf")
    try:
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project or not project.pdf_storage_ref:
            logger.error(f"Project {project_id} has no archived PDF.")
            return False

        if not download_stored_file_to_path(project.pdf_storage_ref, pdf_path):
            raise RuntimeError("تعذر تحميل ملف PDF المؤرشف.")

        db.query(models.Chapter).filter(models.Chapter.project_id == project_id).delete()
        db.commit()

        chapters = extract_chapters_from_pdf(
            pdf_path,
            source_lang=source_lang,
            page_from=page_from,
            page_to=page_to,
        )

        for ch in chapters:
            db.add(
                models.Chapter(
                    chapter_num=ch["id"],
                    project_id=project_id,
                    title=ch["title"],
                    original_text=ch["text"],
                    translation_status="pending",
                    tts_status="pending",
                    start_page=ch["start_page"],
                    end_page=ch["end_page"],
                )
            )

        project.status = "completed"
        db.commit()
        logger.info(f"Re-extracted {len(chapters)} chapters for project {project_id}")
        return True
    except Exception as exc:
        logger.error(f"Re-extract failed for project {project_id}: {exc}")
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if project:
            project.status = "failed"
            db.commit()
        raise exc
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        db.close()


@celery_app.task
def translate_chapter_task(chapter_id: int, engine: str, api_key: str = None, model: str = None, custom_host: str = None):
    """
    Translates a chapter text into Arabic in the background and stores it in the database.
    """
    db = SessionLocal()
    try:
        chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
        if not chapter:
            logger.error(f"Chapter {chapter_id} not found in database.")
            return False
            
        chapter.translation_status = "processing"
        db.commit()
        
        # Run async translation function inside a synchronous worker using asyncio.run
        translated_text, method, warning = run_async(
            translate_text_to_arabic(
                text=chapter.original_text,
                engine=engine,
                api_key=api_key,
                model=model,
                custom_host=custom_host
            )
        )
        
        chapter.translated_text = translated_text
        chapter.translation_engine = method
        chapter.translation_warning = warning
        chapter.translation_status = "completed"
        db.commit()
        
        logger.info(f"Successfully translated chapter {chapter_id}")
        return True
    except Exception as e:
        logger.error(f"Error translating chapter {chapter_id}: {e}")
        db.rollback()
        chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
        if chapter:
            chapter.translation_status = "failed"
            db.commit()
        raise e
    finally:
        db.close()

@celery_app.task
def generate_tts_task(chapter_id: int, voice: str, rate: str):
    """
    Generates TTS audio using Microsoft Edge TTS, uploads output to S3/MinIO,
    and updates the database.
    """
    db = SessionLocal()
    try:
        chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
        if not chapter:
            logger.error(f"Chapter {chapter_id} not found in database.")
            return False
            
        if not chapter.translated_text:
            raise ValueError("Chapter translated text is empty. Cannot generate TTS.")
            
        chapter.tts_status = "processing"
        db.commit()
        
        outputs_dir = get_outputs_dir()
        os.makedirs(outputs_dir, exist_ok=True)
        
        import hashlib
        # Calculate unique hash for caching / filename
        payload_str = f"{chapter.translated_text}|||{voice}|||{rate}"
        file_hash = hashlib.sha256(payload_str.encode('utf-8', errors='ignore')).hexdigest()
        
        local_mp3_path = os.path.join(outputs_dir, f"{file_hash}.mp3")
        local_vtt_path = os.path.join(outputs_dir, f"{file_hash}.vtt")
        
        # Generate edge-tts audio and subtitles
        run_async(
            generate_tts_edge(
                text=chapter.translated_text,
                voice=voice,
                output_path=local_mp3_path,
                rate=rate,
                vtt_path=local_vtt_path
            )
        )
        
        # Upload generated files to S3/MinIO cloud storage
        s3_audio_url = upload_file_to_s3(local_mp3_path, f"audio/{file_hash}.mp3", "audio/mpeg")
        
        s3_vtt_url = None
        if os.path.exists(local_vtt_path):
            s3_vtt_url = upload_file_to_s3(local_vtt_path, f"subtitles/{file_hash}.vtt", "text/vtt")
            
        # Update chapter fields
        chapter.audio_url = s3_audio_url
        chapter.vtt_url = s3_vtt_url
        chapter.tts_status = "completed"
        chapter.tts_voice = voice
        chapter.tts_rate = rate
        db.commit()
        
        # Clean up local temporary files if they were uploaded to cloud storage
        if is_s3_ref(s3_audio_url) or is_sb_ref(s3_audio_url):
            if os.path.exists(local_mp3_path):
                os.remove(local_mp3_path)
            if os.path.exists(local_vtt_path):
                os.remove(local_vtt_path)
                
        logger.info(f"Successfully generated TTS audio and subtitles for chapter {chapter_id}")
        return True
    except Exception as e:
        logger.error(f"Error generating TTS for chapter {chapter_id}: {e}")
        db.rollback()
        chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
        if chapter:
            chapter.tts_status = "failed"
            db.commit()
        raise e
    finally:
        db.close()
