from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class WritingAssignment(Base):
    __tablename__ = "writing_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=False)
    word_count_min = Column(Integer, default=50, nullable=False)
    word_count_max = Column(Integer, default=500, nullable=False)
    evaluation_criteria = Column(JSONB, nullable=False, default={})
    instructions = Column(Text)
    grade_level = Column(String(50))
    subject = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    teacher = relationship("User", back_populates="writing_assignments")
    submissions = relationship("StudentWritingSubmission", back_populates="assignment", cascade="all, delete-orphan")

    # Check constraints
    __table_args__ = (
        CheckConstraint('word_count_min > 0', name='writing_assignments_word_count_min_check'),
        CheckConstraint('word_count_max > word_count_min', name='writing_assignments_word_count_max_check'),
    )


class StudentWritingSubmission(Base):
    __tablename__ = "student_writing_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("writing_assignments.id", ondelete="CASCADE"), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    submission_text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    evaluation_score = Column(JSONB)
    evaluation_feedback = Column(Text)
    evaluated_at = Column(DateTime(timezone=True))

    # Relationships
    student = relationship("User", back_populates="writing_submissions")
    assignment = relationship("WritingAssignment", back_populates="submissions")
    classroom = relationship("Classroom", back_populates="writing_submissions")

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('student_id', 'assignment_id', 'classroom_id', name='unique_student_assignment_classroom'),
    )