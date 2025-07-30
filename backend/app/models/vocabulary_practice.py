"""
Vocabulary practice activity models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.core.database import Base




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
    
    __table_args__ = (
        UniqueConstraint('student_id', 'vocabulary_list_id', 'classroom_assignment_id', 
                        name='unique_student_vocab_practice'),
    )




class VocabularyStoryPrompt(Base):
    """Stores story prompts for vocabulary practice"""
    __tablename__ = "vocabulary_story_prompts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    prompt_text = Column(Text, nullable=False)
    required_words = Column(JSONB, nullable=False)  # ["word1", "word2", "word3"]
    setting = Column(String(100), nullable=False)
    tone = Column(String(50), nullable=False)
    max_score = Column(Integer, nullable=False, default=100)
    prompt_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    vocabulary_list = relationship("VocabularyList")
    story_responses = relationship("VocabularyStoryResponse", back_populates="prompt")
    
    __table_args__ = (
        UniqueConstraint('vocabulary_list_id', 'prompt_order', name='unique_prompt_order'),
    )


class VocabularyStoryResponse(Base):
    """Stores student story responses"""
    __tablename__ = "vocabulary_story_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_story_prompts.id", ondelete="CASCADE"), nullable=False)
    story_attempt_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_story_attempts.id", ondelete="CASCADE"), nullable=False)
    prompt_order = Column(Integer, nullable=False)
    response_text = Column(Text, nullable=False)
    words_used = Column(JSONB, nullable=False, default=list)
    used_required_words = Column(JSONB, nullable=False, default=list)
    score = Column(Integer, nullable=False)
    word_count = Column(Integer, nullable=False)
    feedback = Column(JSONB)
    story_text = Column(Text, nullable=False)
    ai_evaluation = Column(JSONB, nullable=False)  # scores and detailed feedback
    total_score = Column(Integer, nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    prompt = relationship("VocabularyStoryPrompt", back_populates="story_responses")
    story_attempt = relationship("VocabularyStoryAttempt")
    
    __table_args__ = (
        CheckConstraint("attempt_number BETWEEN 1 AND 2", name='check_attempt_number'),
        CheckConstraint("total_score BETWEEN 0 AND 100", name='check_total_score'),
    )


class VocabularyStoryAttempt(Base):
    """Records individual story builder attempts"""
    __tablename__ = "vocabulary_story_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    
    attempt_number = Column(Integer, nullable=False)
    total_prompts = Column(Integer, nullable=False)
    prompts_completed = Column(Integer, nullable=False, default=0)
    current_score = Column(Integer, nullable=False, default=0)
    max_possible_score = Column(Integer, nullable=False)
    passing_score = Column(Integer, nullable=False)
    
    # Story responses tracking
    story_responses = Column(JSONB, nullable=False, default=list)
    
    status = Column(String(20), nullable=False, default='in_progress')
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')",
            name='check_story_attempt_status'
        ),
    )


class VocabularyConceptMap(Base):
    """Stores student concept maps for vocabulary words"""
    __tablename__ = "vocabulary_concept_maps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_words.id", ondelete="CASCADE"), nullable=False)
    
    # Student responses
    definition = Column(Text, nullable=False)
    synonyms = Column(Text, nullable=False)
    antonyms = Column(Text, nullable=False)
    context_theme = Column(Text, nullable=False)
    connotation = Column(Text, nullable=False)
    example_sentence = Column(Text, nullable=False)
    
    # Evaluation
    ai_evaluation = Column(JSONB, nullable=False)
    word_score = Column(Numeric(3, 2), nullable=False)
    
    # Tracking
    attempt_number = Column(Integer, nullable=False, default=1)
    word_order = Column(Integer, nullable=False)
    time_spent_seconds = Column(Integer)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    word = relationship("VocabularyWord")
    
    __table_args__ = (
        CheckConstraint("word_score >= 1.0 AND word_score <= 4.0", name='check_word_score'),
        UniqueConstraint('practice_progress_id', 'word_id', 'attempt_number', 
                        name='unique_concept_map_word_attempt'),
    )


class VocabularyConceptMapAttempt(Base):
    """Records concept map builder attempts"""
    __tablename__ = "vocabulary_concept_map_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    
    attempt_number = Column(Integer, nullable=False)
    total_words = Column(Integer, nullable=False)
    words_completed = Column(Integer, nullable=False, default=0)
    current_word_index = Column(Integer, nullable=False, default=0)
    
    # Scoring
    total_score = Column(Numeric(5, 2), nullable=False, default=0)
    max_possible_score = Column(Numeric(5, 2), nullable=False)
    passing_score = Column(Numeric(5, 2), nullable=False)
    average_score = Column(Numeric(3, 2))
    
    # Word scores tracking
    word_scores = Column(JSONB, nullable=False, default=dict)
    
    status = Column(String(20), nullable=False, default='in_progress')
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    concept_maps = relationship("VocabularyConceptMap", 
                               foreign_keys="VocabularyConceptMap.practice_progress_id",
                               primaryjoin="VocabularyConceptMapAttempt.practice_progress_id == VocabularyConceptMap.practice_progress_id")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')",
            name='check_concept_map_attempt_status'
        ),
    )


class VocabularyPuzzleGame(Base):
    """Stores generated puzzles for vocabulary practice"""
    __tablename__ = "vocabulary_puzzle_games"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_words.id", ondelete="CASCADE"), nullable=False)
    puzzle_type = Column(String(50), nullable=False)
    puzzle_data = Column(JSONB, nullable=False)
    correct_answer = Column(String(200), nullable=False)
    puzzle_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    vocabulary_list = relationship("VocabularyList")
    word = relationship("VocabularyWord")
    responses = relationship("VocabularyPuzzleResponse", back_populates="puzzle")
    
    __table_args__ = (
        CheckConstraint(
            "puzzle_type IN ('scrambled', 'crossword_clue', 'word_match', 'fill_blank')",
            name='check_puzzle_type'
        ),
        UniqueConstraint('vocabulary_list_id', 'puzzle_order', name='unique_puzzle_order'),
    )


class VocabularyPuzzleResponse(Base):
    """Stores student puzzle responses"""
    __tablename__ = "vocabulary_puzzle_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    puzzle_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_puzzle_games.id", ondelete="CASCADE"), nullable=False)
    student_answer = Column(Text, nullable=False)
    ai_evaluation = Column(JSONB, nullable=False)
    puzzle_score = Column(Integer, nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    time_spent_seconds = Column(Integer)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    puzzle = relationship("VocabularyPuzzleGame", back_populates="responses")
    
    __table_args__ = (
        CheckConstraint("puzzle_score BETWEEN 1 AND 4", name='check_puzzle_score'),
        UniqueConstraint('practice_progress_id', 'puzzle_id', 'attempt_number', 
                        name='unique_puzzle_response_attempt'),
    )


class VocabularyPuzzleAttempt(Base):
    """Records puzzle path attempts"""
    __tablename__ = "vocabulary_puzzle_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    
    attempt_number = Column(Integer, nullable=False)
    total_puzzles = Column(Integer, nullable=False)
    puzzles_completed = Column(Integer, nullable=False, default=0)
    current_puzzle_index = Column(Integer, nullable=False, default=0)
    
    # Scoring
    total_score = Column(Integer, nullable=False, default=0)
    max_possible_score = Column(Integer, nullable=False)
    passing_score = Column(Integer, nullable=False)
    
    # Puzzle scores tracking
    puzzle_scores = Column(JSONB, nullable=False, default=dict)
    
    status = Column(String(20), nullable=False, default='in_progress')
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')",
            name='check_puzzle_attempt_status'
        ),
    )


class VocabularyFillInBlankSentence(Base):
    """Stores generated fill-in-the-blank sentences for vocabulary practice"""
    __tablename__ = "vocabulary_fill_in_blank_sentences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_words.id", ondelete="CASCADE"), nullable=False)
    sentence_with_blank = Column(Text, nullable=False)
    correct_answer = Column(String(100), nullable=False)
    sentence_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    vocabulary_list = relationship("VocabularyList")
    word = relationship("VocabularyWord")
    responses = relationship("VocabularyFillInBlankResponse", back_populates="sentence")
    
    __table_args__ = (
        UniqueConstraint('vocabulary_list_id', 'sentence_order', name='unique_sentence_order'),
    )


class VocabularyFillInBlankResponse(Base):
    """Stores student fill-in-the-blank responses"""
    __tablename__ = "vocabulary_fill_in_blank_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    sentence_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_fill_in_blank_sentences.id", ondelete="CASCADE"), nullable=False)
    student_answer = Column(String(100), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    time_spent_seconds = Column(Integer)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    sentence = relationship("VocabularyFillInBlankSentence", back_populates="responses")
    
    __table_args__ = (
        UniqueConstraint('practice_progress_id', 'sentence_id', 'attempt_number', 
                        name='unique_fill_in_blank_response_attempt'),
    )


class VocabularyFillInBlankAttempt(Base):
    """Records fill-in-the-blank attempts"""
    __tablename__ = "vocabulary_fill_in_blank_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    practice_progress_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_practice_progress.id", ondelete="CASCADE"), nullable=False)
    
    attempt_number = Column(Integer, nullable=False)
    total_sentences = Column(Integer, nullable=False)
    sentences_completed = Column(Integer, nullable=False, default=0)
    current_sentence_index = Column(Integer, nullable=False, default=0)
    
    # Scoring
    correct_answers = Column(Integer, nullable=False, default=0)
    incorrect_answers = Column(Integer, nullable=False, default=0)
    score_percentage = Column(Numeric(5, 2))
    passing_score = Column(Integer, nullable=False, default=70)
    
    # Tracking
    sentence_order = Column(JSONB, nullable=False, default=list)  # Shuffled order of sentence IDs
    responses = Column(JSONB, nullable=False, default=dict)  # Map of sentence_id to response data
    
    status = Column(String(20), nullable=False, default='in_progress')
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    vocabulary_list = relationship("VocabularyList")
    practice_progress = relationship("VocabularyPracticeProgress")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')",
            name='check_fill_in_blank_attempt_status'
        ),
    )