from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, DECIMAL, Boolean, Text, CheckConstraint, Numeric
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


class StudentTestAttempt(Base):
    __tablename__ = "student_test_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_test_id = Column(UUID(as_uuid=True), ForeignKey("assignment_tests.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id"), nullable=False)
    
    # Progress tracking
    current_question = Column(Integer, default=1)
    answers_data = Column(JSONB, default={})  # {question_id: answer_text}
    status = Column(String(50), default='in_progress')
    
    # Timing
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_activity_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    submitted_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer, default=0)
    
    # Results
    score = Column(Numeric(5, 2))
    passed = Column(Boolean)
    feedback = Column(JSONB)  # Detailed feedback per question
    
    # Attempt tracking
    attempt_number = Column(Integer, default=1)
    
    # Security tracking
    security_violations = Column(JSONB, default=list)
    is_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime(timezone=True))
    locked_reason = Column(String(255))
    
    # Schedule and override tracking (added in migration 033)
    started_within_schedule = Column(Boolean, default=True)
    override_code_used = Column(UUID(as_uuid=True), ForeignKey("classroom_test_overrides.id"))
    grace_period_end = Column(DateTime(timezone=True))
    schedule_violation_reason = Column(Text)
    
    # Audit
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    test = relationship("AssignmentTest")
    assignment = relationship("ReadingAssignment")
    override_usage = relationship("TestOverrideUsage", back_populates="test_attempt", uselist=False)
    
    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'completed', 'submitted', 'graded')", 
                       name='check_test_attempt_status'),
    )


class TeacherBypassCode(Base):
    __tablename__ = "teacher_bypass_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    context_type = Column(String(50), default="test")  # test, umaread, vocabulary, etc.
    context_id = Column(UUID(as_uuid=True))  # Can be test_attempt_id, assignment_id, etc.
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    bypass_code = Column(String(8), nullable=False)
    used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    teacher = relationship("User", foreign_keys=[teacher_id])
    student = relationship("User", foreign_keys=[student_id])


class TestSecurityIncident(Base):
    __tablename__ = "test_security_incidents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_attempt_id = Column(UUID(as_uuid=True), ForeignKey("student_test_attempts.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    incident_type = Column(String(50), nullable=False)
    incident_data = Column(JSONB)
    resulted_in_lock = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    test_attempt = relationship("StudentTestAttempt")
    student = relationship("User", foreign_keys=[student_id])
    
    __table_args__ = (
        CheckConstraint(
            "incident_type IN ('focus_loss', 'tab_switch', 'navigation_attempt', 'window_blur', 'app_switch', 'orientation_cheat')",
            name='check_incident_type'
        ),
    )