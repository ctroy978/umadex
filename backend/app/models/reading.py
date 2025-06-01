from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, DateTime, CheckConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class ReadingAssignment(Base):
    __tablename__ = "reading_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_title = Column(String(255), nullable=False)
    work_title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)
    grade_level = Column(String(50), nullable=False)
    work_type = Column(String(20), nullable=False)
    literary_form = Column(String(20), nullable=False)
    genre = Column(String(50), nullable=False)
    subject = Column(String(100), nullable=False)
    raw_content = Column(Text, nullable=False)
    total_chunks = Column(Integer, nullable=True)
    status = Column(String(50), default="draft")
    images_processed = Column(Boolean, default=False)
    assignment_type = Column(String(50), nullable=False, default="UMARead")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(work_type.in_(['fiction', 'non-fiction'])),
        CheckConstraint(literary_form.in_(['prose', 'poetry', 'drama', 'mixed'])),
        CheckConstraint(assignment_type.in_(['UMARead', 'UMAVocab', 'UMADebate', 'UMAWrite', 'UMALecture'])),
    )

    # Relationships
    teacher = relationship("User", back_populates="reading_assignments")
    chunks = relationship("ReadingChunk", back_populates="assignment", cascade="all, delete-orphan")
    images = relationship("AssignmentImage", back_populates="assignment", cascade="all, delete-orphan")


class ReadingChunk(Base):
    __tablename__ = "reading_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id", ondelete="CASCADE"), nullable=False)
    chunk_order = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    has_important_sections = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assignment = relationship("ReadingAssignment", back_populates="chunks")


class AssignmentImage(Base):
    __tablename__ = "assignment_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id", ondelete="CASCADE"), nullable=False)
    image_tag = Column(String(50), nullable=True)  # 'image-1', 'image-2', etc.
    image_key = Column(String(100), nullable=False)  # Unique file identifier
    file_name = Column(String(255), nullable=True)  # Original filename
    original_url = Column(Text, nullable=True)  # 2000x2000 max
    display_url = Column(Text, nullable=True)   # 800x600 max (for student view)
    thumbnail_url = Column(Text, nullable=True)  # 200x150 max (for teacher sidebar)
    image_url = Column(Text, nullable=True)  # Backward compatibility (alias for display_url)
    width = Column(Integer, nullable=True, default=0)  # Original dimensions
    height = Column(Integer, nullable=True, default=0)
    file_size = Column(Integer, nullable=True)  # In bytes
    mime_type = Column(String(50), nullable=True)
    ai_description = Column(Text, nullable=True)  # AI-generated description
    description_generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime, default=datetime.utcnow)  # Backward compatibility
    # Legacy columns
    file_url = Column(Text, nullable=True)
    custom_name = Column(String(100), nullable=True)

    # Relationships
    assignment = relationship("ReadingAssignment", back_populates="images")


class QuestionCache(Base):
    __tablename__ = "question_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(Integer, nullable=False)
    difficulty_level = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False)
    question_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("difficulty_level BETWEEN 1 AND 8"),
    )