"""
Vocabulary practice activity models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.core.database import Base


class VocabularyGameQuestion(Base):
    """Stores generated questions for vocabulary practice games"""
    __tablename__ = "vocabulary_game_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_words.id", ondelete="CASCADE"), nullable=False)
    question_type = Column(String(50), nullable=False)
    difficulty_level = Column(String(10), nullable=False)
    question_text = Column(Text, nullable=False)
    correct_answer = Column(String(200), nullable=False)
    explanation = Column(Text, nullable=False)
    question_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    vocabulary_list = relationship("VocabularyList")
    word = relationship("VocabularyWord")
    
    __table_args__ = (
        CheckConstraint(
            "question_type IN ('riddle', 'poem', 'sentence_completion', 'word_association', 'scenario')",
            name='check_question_type'
        ),
        CheckConstraint(
            "difficulty_level IN ('easy', 'medium', 'hard')",
            name='check_difficulty_level'
        ),
        UniqueConstraint('vocabulary_list_id', 'question_order', name='unique_question_order'),
    )


class VocabularyPracticeProgress(Base):
    """Tracks student progress through vocabulary practice activities"""
    __tablename__ = "vocabulary_practice_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id"), nullable=False)
    classroom_assignment_id = Column(Integer, ForeignKey("classroom_assignments.id"), nullable=False)
    
    # Practice status tracking
    practice_status = Column(JSONB, nullable=False, default=lambda: {
        "assignments": {
            "vocabulary_challenge": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": None,
                "completed_at": None
            },
            "definition_match": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": None,
                "completed_at": None
            },
            "context_clues": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": None,
                "completed_at": None
            },
            "word_builder": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": None,
                "completed_at": None
            }
        },
        "completed_assignments": [],
        "test_unlocked": False,
        "test_unlock_date": None
    })
    
    # Current game session tracking
    current_game_session = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    game_attempts = relationship("VocabularyGameAttempt", back_populates="practice_progress")
    
    __table_args__ = (
        UniqueConstraint('student_id', 'vocabulary_list_id', 'classroom_assignment_id', 
                        name='unique_student_vocab_practice'),
    )


class VocabularyGameAttempt(Base):
    """Records individual game attempts"""
    __tablename__ = "vocabulary_game_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id"), nullable=False)
    
    game_type = Column(String(50), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    
    # Game session data
    total_questions = Column(Integer, nullable=False)
    questions_answered = Column(Integer, nullable=False, default=0)
    current_score = Column(Integer, nullable=False, default=0)
    max_possible_score = Column(Integer, nullable=False)
    passing_score = Column(Integer, nullable=False)
    
    # Question responses
    question_responses = Column(JSONB, nullable=False, default=list)
    
    status = Column(String(20), nullable=False, default='in_progress')
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress", back_populates="game_attempts")
    
    __table_args__ = (
        CheckConstraint(
            "game_type IN ('vocabulary_challenge', 'definition_match', 'context_clues', 'word_builder')",
            name='check_game_type'
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned')",
            name='check_attempt_status'
        ),
    )