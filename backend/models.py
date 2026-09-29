from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("DocumentModel", back_populates="user", cascade="all, delete-orphan")
    usage_logs = relationship("PromptUsageLog", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    designation = Column(String(100), nullable=True)
    department = Column(String(150), nullable=True)
    work_experience_years = Column(Float, nullable=True)
    educational_qualification = Column(String(255), nullable=True)
    current_skills = Column(Text, nullable=True) # Stored as JSON string
    completed_trainings = Column(Text, nullable=True) # Stored as JSON string
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    chunk_count = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_data = Column(Text, nullable=True) # Stored JSON list of floats for embedding

    document = relationship("DocumentModel", back_populates="chunks")

class PromptUsageLog(Base):
    __tablename__ = "prompt_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address = Column(String(50), nullable=True)
    prompt_text = Column(Text, nullable=False)
    is_cli = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="usage_logs")

class RateLimitRecord(Base):
    __tablename__ = "rate_limit_records"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(100), unique=True, index=True, nullable=False) # e.g. "user_1" or "ip_127.0.0.1"
    request_count = Column(Integer, default=0)
    window_start = Column(DateTime, default=datetime.utcnow)
