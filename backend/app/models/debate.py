"""
SQLAlchemy models for UMADebate module
"""
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, Numeric, Enum as SQLEnum, JSON
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
    
    # New fields for single-point structure
    statements_per_round = Column(Integer, default=5)
    coaching_enabled = Column(Boolean, default=True)
    grading_baseline = Column(Integer, default=70)
    grading_scale = Column(String(20), default='lenient')
    
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


# Student Debate Models (Phase 2)
class StudentDebate(Base):
    __tablename__ = "student_debates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("debate_assignments.id", ondelete="CASCADE"), nullable=False)
    classroom_assignment_id = Column(Integer, ForeignKey("classroom_assignments.id", ondelete="CASCADE"), nullable=False)
    
    # Progress tracking
    status = Column(String(50), nullable=False, default='not_started')
    current_debate = Column(Integer, default=1)
    current_round = Column(Integer, default=1)
    
    # Three-debate structure
    debate_1_position = Column(String(10))  # 'pro' or 'con'
    debate_2_position = Column(String(10))
    debate_3_position = Column(String(10))
    
    # Single point per round
    debate_1_point = Column(Text)
    debate_2_point = Column(Text)
    debate_3_point = Column(Text)
    
    # Fallacy tracking
    fallacy_counter = Column(Integer, default=0)
    fallacy_scheduled_debate = Column(Integer)
    fallacy_scheduled_round = Column(Integer)
    
    # Timing controls
    assignment_started_at = Column(DateTime(timezone=True))
    current_debate_started_at = Column(DateTime(timezone=True))
    current_debate_deadline = Column(DateTime(timezone=True))
    
    # Final scoring
    debate_1_percentage = Column(Numeric(5, 2))
    debate_2_percentage = Column(Numeric(5, 2))
    debate_3_percentage = Column(Numeric(5, 2))
    final_percentage = Column(Numeric(5, 2))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", back_populates="student_debates")
    assignment = relationship("DebateAssignment")
    posts = relationship("DebatePost", back_populates="student_debate", cascade="all, delete-orphan")


class DebatePost(Base):
    __tablename__ = "debate_posts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    student_debate_id = Column(UUID(as_uuid=True), ForeignKey("student_debates.id", ondelete="CASCADE"), nullable=False)
    
    # Post identification
    debate_number = Column(Integer, nullable=False)
    round_number = Column(Integer, nullable=False)
    statement_number = Column(Integer, nullable=False)  # 1-5 for the debate flow
    post_type = Column(String(20), nullable=False)  # 'student' or 'ai'
    
    # Content
    content = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False)
    
    # AI-specific fields
    ai_personality = Column(String(50))
    is_fallacy = Column(Boolean, default=False)
    fallacy_type = Column(String(50))
    
    # Student scoring
    clarity_score = Column(Numeric(2, 1))
    evidence_score = Column(Numeric(2, 1))
    logic_score = Column(Numeric(2, 1))
    persuasiveness_score = Column(Numeric(2, 1))
    rebuttal_score = Column(Numeric(2, 1))
    base_percentage = Column(Numeric(5, 2))
    bonus_points = Column(Numeric(5, 2), default=0)
    final_percentage = Column(Numeric(5, 2))
    
    # Moderation
    content_flagged = Column(Boolean, default=False)
    moderation_status = Column(String(20), default='approved')
    
    # AI feedback
    ai_feedback = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student_debate = relationship("StudentDebate", back_populates="posts")
    challenges = relationship("DebateChallenge", back_populates="post", cascade="all, delete-orphan")


class DebateChallenge(Base):
    __tablename__ = "debate_challenges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    post_id = Column(UUID(as_uuid=True), ForeignKey("debate_posts.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Challenge details
    challenge_type = Column(String(20), nullable=False)  # 'fallacy' or 'appeal'
    challenge_value = Column(String(50), nullable=False)
    explanation = Column(Text)
    
    # Evaluation
    is_correct = Column(Boolean, nullable=False)
    points_awarded = Column(Numeric(3, 1), nullable=False)
    ai_feedback = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    post = relationship("DebatePost", back_populates="challenges")
    student = relationship("User")


class AIPersonality(Base):
    __tablename__ = "ai_personalities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    prompt_template = Column(Text, nullable=False)
    difficulty_levels = Column(JSON)  # Array of difficulty levels
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FallacyTemplate(Base):
    __tablename__ = "fallacy_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    fallacy_type = Column(String(50), nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    template = Column(Text, nullable=False)
    difficulty_levels = Column(JSON)
    topic_keywords = Column(JSON)  # Array of keywords for topic matching
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DebateRoundFeedback(Base):
    __tablename__ = "debate_round_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    student_debate_id = Column(UUID(as_uuid=True), ForeignKey("student_debates.id", ondelete="CASCADE"), nullable=False)
    debate_number = Column(Integer, nullable=False)
    
    # Coaching feedback after the round
    coaching_feedback = Column(Text, nullable=False)
    strengths = Column(Text)
    improvement_areas = Column(Text)
    specific_suggestions = Column(Text)
    
    # Round completion tracking
    round_completed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student_debate = relationship("StudentDebate")


class AIDebatePoint(Base):
    __tablename__ = "ai_debate_points"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("debate_assignments.id", ondelete="CASCADE"), nullable=False)
    debate_number = Column(Integer, nullable=False)
    position = Column(String(10), nullable=False)  # 'pro' or 'con'
    
    # The single point for this round
    debate_point = Column(Text, nullable=False)
    supporting_evidence = Column(JSON)  # Array of evidence points
    
    # Metadata
    difficulty_appropriate = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    assignment = relationship("DebateAssignment")