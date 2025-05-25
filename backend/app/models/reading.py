from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(work_type.in_(['fiction', 'non-fiction'])),
        CheckConstraint(literary_form.in_(['prose', 'poetry', 'drama', 'mixed'])),
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
    image_key = Column(String(50), nullable=False)
    custom_name = Column(String(100), nullable=True)
    file_url = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assignment = relationship("ReadingAssignment", back_populates="images")