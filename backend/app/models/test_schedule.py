from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, JSON, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class ClassroomTestSchedule(Base):
    __tablename__ = "classroom_test_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_by_teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    timezone = Column(String(50), nullable=False, default="America/New_York")
    grace_period_minutes = Column(Integer, default=30)
    schedule_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP", onupdate=datetime.utcnow)
    
    # Relationships
    classroom = relationship("Classroom", back_populates="test_schedule")
    created_by = relationship("User", foreign_keys=[created_by_teacher_id])
    
    __table_args__ = (
        CheckConstraint('grace_period_minutes >= 0 AND grace_period_minutes <= 120', name='valid_grace_period'),
    )


class ClassroomTestOverride(Base):
    __tablename__ = "classroom_test_overrides"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    override_code = Column(String(8), nullable=False, unique=True)
    reason = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    max_uses = Column(Integer, default=1)
    current_uses = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")
    used_at = Column(DateTime(timezone=True))
    
    # Relationships
    classroom = relationship("Classroom", back_populates="test_overrides")
    teacher = relationship("User", foreign_keys=[teacher_id])
    usage_records = relationship("TestOverrideUsage", back_populates="override", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('max_uses > 0', name='positive_max_uses'),
        CheckConstraint('current_uses <= max_uses', name='valid_usage'),
    )


class TestOverrideUsage(Base):
    __tablename__ = "test_override_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    override_id = Column(UUID(as_uuid=True), ForeignKey("classroom_test_overrides.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    test_attempt_id = Column(UUID(as_uuid=True), ForeignKey("student_test_attempts.id"), nullable=False)
    used_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")
    
    # Relationships
    override = relationship("ClassroomTestOverride", back_populates="usage_records")
    student = relationship("User", foreign_keys=[student_id])
    test_attempt = relationship("StudentTestAttempt", back_populates="override_usage")
    
    __table_args__ = (
        UniqueConstraint('override_id', 'student_id', 'test_attempt_id', name='unique_override_usage'),
    )