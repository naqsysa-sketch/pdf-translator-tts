import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def _resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./pdf_translator.db")
    # Supabase/Vercel sometimes provide postgres:// — SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _resolve_database_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """
    FastAPI dependency that provides a transactional database session scope.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema_updates():
    """Lightweight migrations for columns added after initial deploy."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("projects")}
    if "pdf_storage_ref" not in columns:
        with engine.begin() as conn:
            if DATABASE_URL.startswith("sqlite"):
                conn.execute(text("ALTER TABLE projects ADD COLUMN pdf_storage_ref TEXT"))
            else:
                conn.execute(text("ALTER TABLE projects ADD COLUMN IF NOT EXISTS pdf_storage_ref TEXT"))

