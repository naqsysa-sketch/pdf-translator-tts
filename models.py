import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, index=True)  # UUID string
    filename = Column(String(255), nullable=False)
    status = Column(String(50), default="processing", nullable=False)  # uploading, processing, completed, failed
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    pdf_storage_ref = Column(Text, nullable=True)

    user = relationship("User", back_populates="projects")
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan")

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    chapter_num = Column(Integer, nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=True)
    
    # Statuses: pending, processing, completed, failed
    translation_status = Column(String(50), default="pending", nullable=False)
    translation_engine = Column(String(100), nullable=True)
    translation_warning = Column(Text, nullable=True)
    
    audio_url = Column(Text, nullable=True)
    vtt_url = Column(Text, nullable=True)
    tts_status = Column(String(50), default="pending", nullable=False)
    tts_voice = Column(String(100), nullable=True)
    tts_rate = Column(String(50), nullable=True)
    
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)

    project = relationship("Project", back_populates="chapters")
