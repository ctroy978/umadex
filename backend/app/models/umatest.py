"""
UMATest models for test creation and management
Phase 1: Test Creation System
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.sql import func
from uuid import uuid4

from app.core.database import Base


class HandBuiltTestQuestion(Base):
    """Questions for hand-built tests created by teachers"""
    __tablename__ = "hand_built_test_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    test_assignment_id = Column(UUID(as_uuid=True), ForeignKey("test_assignments.id", ondelete="CASCADE"), nullable=False)
    
    # Question content
    question_text = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    evaluation_rubric = Column(Text, nullable=False)
    
    # Question metadata
    difficulty_level = Column(String(20), nullable=False)
    position = Column(Integer, nullable=False)
    points = Column(Integer, default=10)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("difficulty_level IN ('basic', 'intermediate', 'advanced', 'expert')", 
                       name='check_question_difficulty_level'),
        UniqueConstraint('test_assignment_id', 'position', name='unique_question_position'),
    )


class TestAssignment(Base):
    """Main test assignments table for UMATest module"""
    __tablename__ = "test_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Test metadata
    test_title = Column(String(255), nullable=False)
    test_description = Column(Text)
    test_type = Column(String(50), default='lecture_based')  # 'lecture_based' or 'hand_built'
    
    # Selected lectures (array of UMALecture assignment IDs) - optional for hand_built tests
    selected_lecture_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    
    # Test configuration
    time_limit_minutes = Column(Integer)
    attempt_limit = Column(Integer, default=1)
    randomize_questions = Column(Boolean, default=False)
    show_feedback_immediately = Column(Boolean, default=True)
    
    # Generated test content
    test_structure = Column(JSONB, nullable=False, default={})
    
    # Status management
    status = Column(String(50), default='draft')
    
    # Timestamps and soft delete
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'published', 'archived')", name='check_test_status'),
        CheckConstraint("test_type IN ('lecture_based', 'hand_built')", name='check_test_type'),
        CheckConstraint(
            "(test_type = 'lecture_based' AND selected_lecture_ids IS NOT NULL AND array_length(selected_lecture_ids, 1) > 0) OR (test_type = 'hand_built')",
            name='check_test_type_lecture_ids'
        ),
        CheckConstraint('time_limit_minutes IS NULL OR time_limit_minutes > 0', name='check_valid_time_limit'),
        CheckConstraint('attempt_limit > 0', name='check_valid_attempt_limit'),
    )


class TestQuestionCache(Base):
    """Cache for AI-generated test questions"""
    __tablename__ = "test_question_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Cache key components
    lecture_id = Column(UUID(as_uuid=True), nullable=False)
    topic_id = Column(String(255), nullable=False)
    difficulty_level = Column(String(20), nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA256 hash
    
    # Cached questions
    questions = Column(JSONB, nullable=False, default=[])
    
    # AI generation metadata
    ai_model = Column(String(100), default='claude-3-sonnet')
    generation_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("difficulty_level IN ('basic', 'intermediate', 'advanced', 'expert')", 
                       name='check_cache_difficulty_level'),
        UniqueConstraint('lecture_id', 'topic_id', 'difficulty_level', 'content_hash',
                        name='unique_test_question_cache'),
    )


class TestGenerationLog(Base):
    """Log for tracking AI test generation process"""
    __tablename__ = "test_generation_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    test_assignment_id = Column(UUID(as_uuid=True), ForeignKey("test_assignments.id", ondelete="CASCADE"))
    
    # Processing details
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(50))
    error_message = Column(Text)
    
    # Generation statistics
    total_topics_processed = Column(Integer, default=0)
    total_questions_generated = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)
    cache_misses = Column(Integer, default=0)
    
    # AI usage tracking
    ai_tokens_used = Column(Integer, default=0)
    ai_model = Column(String(100))
    
    __table_args__ = (
        CheckConstraint("status IN ('processing', 'completed', 'failed')", 
                       name='check_generation_status'),
    )