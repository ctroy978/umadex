"""
UMARead progress tracking models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from uuid import uuid4

from app.core.database import Base


class UmareadStudentResponse(Base):
    """Track individual student responses to questions"""
    __tablename__ = "umaread_student_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id"), nullable=False)
    chunk_number = Column(Integer, nullable=False)
    question_type = Column(String(20), nullable=False)
    question_text = Column(String, nullable=False)
    student_answer = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    ai_feedback = Column(String)
    difficulty_level = Column(Integer)
    time_spent_seconds = Column(Integer)
    attempt_number = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint('question_type IN (\'summary\', \'comprehension\')', name='check_question_type'),
        CheckConstraint('difficulty_level BETWEEN 1 AND 8', name='check_difficulty_level'),
        UniqueConstraint('student_id', 'assignment_id', 'chunk_number', 'question_type', 'attempt_number',
                        name='umaread_responses_student_assignment_idx'),
    )


class UmareadChunkProgress(Base):
    """Track student progress through chunks"""
    __tablename__ = "umaread_chunk_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id"), nullable=False)
    chunk_number = Column(Integer, nullable=False)
    summary_completed = Column(Boolean, default=False)
    comprehension_completed = Column(Boolean, default=False)
    current_difficulty_level = Column(Integer, default=3)
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint('current_difficulty_level BETWEEN 1 AND 8', name='check_difficulty_level'),
        UniqueConstraint('student_id', 'assignment_id', 'chunk_number', name='umaread_chunk_progress_unique'),
    )


class UmareadAssignmentProgress(Base):
    """Track overall assignment progress"""
    __tablename__ = "umaread_assignment_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id"), nullable=False)
    student_assignment_id = Column(UUID(as_uuid=True), ForeignKey("student_assignments.id"))
    current_chunk = Column(Integer, default=1)
    total_chunks_completed = Column(Integer, default=0)
    current_difficulty_level = Column(Integer, default=3)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint('current_difficulty_level BETWEEN 1 AND 8', name='check_difficulty_level'),
        UniqueConstraint('student_id', 'assignment_id', name='umaread_assignment_progress_unique'),
    )