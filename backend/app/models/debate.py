"""
SQLAlchemy models for UMADebate module
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FallacyFrequency(str, enum.Enum):
    EVERY_1_2 = "every_1_2"
    EVERY_2_3 = "every_2_3"
    EVERY_3_4 = "every_3_4"
    DISABLED = "disabled"


class FlagType(str, enum.Enum):
    PROFANITY = "profanity"
    INAPPROPRIATE = "inappropriate"
    OFF_TOPIC = "off_topic"
    SPAM = "spam"


class FlagStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class DebateAssignment(Base):
    __tablename__ = "debate_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Assignment metadata
    title = Column(String(200), nullable=False)
    topic = Column(Text, nullable=False)
    description = Column(Text)
    grade_level = Column(String(50), nullable=False)
    subject = Column(String(100), nullable=False)
    
    # Debate configuration
    rounds_per_debate = Column(Integer, nullable=False, default=3)
    debate_count = Column(Integer, nullable=False, default=3)
    time_limit_hours = Column(Integer, nullable=False, default=8)
    difficulty_level = Column(String(20), nullable=False, default="intermediate")
    
    # AI configuration
    fallacy_frequency = Column(String(20), default="every_2_3")
    ai_personalities_enabled = Column(Boolean, default=True)
    
    # Content moderation
    content_moderation_enabled = Column(Boolean, default=True)
    auto_flag_off_topic = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    teacher = relationship("User", back_populates="debate_assignments")
    content_flags = relationship("ContentFlag", back_populates="assignment", cascade="all, delete-orphan")


class ContentFlag(Base):
    __tablename__ = "content_flags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    post_id = Column(UUID(as_uuid=True))  # Will reference debate_posts in Phase 2
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("debate_assignments.id", ondelete="CASCADE"), nullable=False)
    
    flag_type = Column(String(20), nullable=False)
    flag_reason = Column(Text)
    auto_flagged = Column(Boolean, default=False)
    confidence_score = Column(Numeric(3, 2))
    
    status = Column(String(20), default="pending")
    teacher_action = Column(String(50))
    teacher_notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])
    assignment = relationship("DebateAssignment", back_populates="content_flags")