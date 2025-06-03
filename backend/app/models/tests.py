from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.core.database import Base


class AssignmentTest(Base):
    __tablename__ = "assignment_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    test_questions = Column(JSONB, nullable=False)
    teacher_notes = Column(Text)
    expires_at = Column(DateTime(timezone=True))
    max_attempts = Column(Integer, default=1)
    time_limit_minutes = Column(Integer, default=60)
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    assignment = relationship("ReadingAssignment", back_populates="tests")
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    test_results = relationship("TestResult", back_populates="test", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("assignment_tests.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    classroom_assignment_id = Column(UUID(as_uuid=True), ForeignKey("classroom_assignments.id"), nullable=False)
    
    # Student responses and AI grading
    responses = Column(JSONB, nullable=False)
    overall_score = Column(DECIMAL(5, 2), nullable=False)
    
    # Timing and completion
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    time_spent_minutes = Column(Integer)
    attempt_number = Column(Integer, default=1)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    test = relationship("AssignmentTest", back_populates="test_results")
    student = relationship("User", foreign_keys=[student_id])
    
    # Constraints
    __table_args__ = (
        {"schema": None}  # Ensure we're using the default schema
    )