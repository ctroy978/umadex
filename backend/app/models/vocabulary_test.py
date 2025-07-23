from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class VocabularyTest(Base):
    __tablename__ = "vocabulary_tests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    classroom_assignment_id = Column(UUID(as_uuid=True), ForeignKey("classroom_assignments.id", ondelete="CASCADE"), nullable=True)
    questions = Column(JSON, nullable=False)
    total_questions = Column(Integer, nullable=False)
    max_attempts = Column(Integer, nullable=False, default=3)
    time_limit_minutes = Column(Integer, default=30)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    attempts = relationship("VocabularyTestAttempt", back_populates="test", cascade="all, delete-orphan")
    vocabulary_list = relationship("VocabularyList")


class VocabularyTestAttempt(Base):
    __tablename__ = "vocabulary_test_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_tests.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    responses = Column(JSON, nullable=False)
    score_percentage = Column(Integer, nullable=False)
    questions_correct = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer)
    status = Column(String(50), nullable=False, default="in_progress")
    
    # Security fields
    security_violations = Column(JSON, default=list)
    is_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime(timezone=True))
    locked_reason = Column(Text)
    
    # Relationships
    test = relationship("VocabularyTest", back_populates="attempts")
    student = relationship("User")
    security_incidents = relationship("VocabularyTestSecurityIncident", back_populates="test_attempt", cascade="all, delete-orphan")


class VocabularyTestSecurityIncident(Base):
    __tablename__ = "vocabulary_test_security_incidents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_attempt_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_test_attempts.id", ondelete="CASCADE"), nullable=False)
    incident_type = Column(String(50), nullable=False)
    incident_data = Column(JSON)
    resulted_in_lock = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    test_attempt = relationship("VocabularyTestAttempt", back_populates="security_incidents")