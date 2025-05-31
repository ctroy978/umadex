"""
Pydantic models for UMARead module
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID
from datetime import datetime
from enum import Enum


class WorkType(str, Enum):
    FICTION = "Fiction"
    NON_FICTION = "Non-Fiction"


class LiteraryForm(str, Enum):
    PROSE = "Prose"
    POETRY = "Poetry"
    DRAMA = "Drama"
    MIXED = "Mixed"


class QuestionType(str, Enum):
    SUMMARY = "summary"
    COMPREHENSION = "comprehension"


class DifficultyAdjustment(int, Enum):
    DECREASE = -1
    MAINTAIN = 0
    INCREASE = 1


class AssignmentMetadata(BaseModel):
    work_type: WorkType
    literary_form: LiteraryForm
    genre: str  # Science, History, Literature, etc.
    subject: str  # Biology, American History, etc.
    grade_level: str
    title: str
    author: Optional[str] = None


class ContentSpecificPrompt(BaseModel):
    prompt_template: str
    question_focus_areas: List[str]
    vocabulary_level: str
    evaluation_criteria: List[str]
    example_questions: List[str]


class ChunkContent(BaseModel):
    chunk_number: int
    text: str
    image_references: List[str] = Field(default_factory=list)
    
    @validator('image_references', pre=True)
    def extract_images(cls, v, values):
        if 'text' in values and v is None:
            import re
            images = re.findall(r'<image>(.*?)</image>', values['text'])
            return images
        return v or []


class QuestionRequest(BaseModel):
    assignment_id: UUID
    chunk_number: int
    chunk_content: str
    difficulty_level: int = Field(ge=1, le=8)
    assignment_metadata: AssignmentMetadata
    question_type: QuestionType


class GeneratedQuestion(BaseModel):
    question_text: str
    question_type: QuestionType
    difficulty_level: Optional[int] = Field(None, ge=1, le=8)
    content_focus: str
    expected_answer_elements: List[str]
    evaluation_criteria: str
    ai_model: str = "claude-3-5-sonnet-20241022"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class StudentAnswer(BaseModel):
    assignment_id: UUID
    chunk_number: int
    question_type: QuestionType
    answer_text: str
    time_spent_seconds: int
    attempt_number: int


class AnswerEvaluation(BaseModel):
    is_correct: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    feedback_text: str
    suggested_difficulty_change: DifficultyAdjustment
    content_specific_feedback: str
    key_missing_elements: List[str] = Field(default_factory=list)


class ChunkProgress(BaseModel):
    chunk_number: int
    summary_completed: bool = False
    comprehension_completed: bool = False
    summary_attempts: int = 0
    comprehension_attempts: int = 0
    time_spent_seconds: int = 0


class StudentProgress(BaseModel):
    assignment_id: UUID
    student_id: UUID
    current_chunk: int
    total_chunks: int
    difficulty_level: int = Field(ge=1, le=8)
    chunks_completed: List[int] = Field(default_factory=list)
    chunk_scores: Dict[str, ChunkProgress] = Field(default_factory=dict)
    status: str = "in_progress"
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class ChunkResponse(BaseModel):
    """Response model for chunk content with images"""
    chunk_number: int
    total_chunks: int
    content: str
    images: List[Dict[str, str]] = Field(default_factory=list)  # [{id: str, url: str, description: str}]
    has_next: bool
    has_previous: bool


class QuestionResponse(BaseModel):
    """Response model for questions"""
    question_id: Optional[UUID] = None
    question_text: str
    question_type: QuestionType
    difficulty_level: Optional[int] = None
    attempt_number: int = 1
    previous_feedback: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    """Request model for submitting answers"""
    answer_text: str = Field(min_length=10, max_length=2000)
    time_spent_seconds: int = Field(ge=0)


class SubmitAnswerResponse(BaseModel):
    """Response model for answer submission"""
    is_correct: bool
    feedback: str
    can_proceed: bool
    next_question_type: Optional[QuestionType] = None
    difficulty_changed: bool = False
    new_difficulty_level: Optional[int] = None


class AssignmentStartResponse(BaseModel):
    """Response when starting an assignment"""
    assignment_id: UUID
    title: str
    author: Optional[str]
    total_chunks: int
    current_chunk: int
    difficulty_level: int
    status: str


# Cache models
class CachedQuestion(BaseModel):
    id: UUID
    assignment_id: UUID
    chunk_number: int
    question_type: QuestionType
    difficulty_level: Optional[int]
    question_text: str
    question_metadata: Dict[str, Any]
    ai_model: str
    created_at: datetime


class QuestionCacheKey(BaseModel):
    assignment_id: UUID
    chunk_number: int
    question_type: QuestionType
    difficulty_level: Optional[int]
    content_hash: str
    
    def cache_key(self) -> str:
        diff = self.difficulty_level or "none"
        return f"umaread:question:{self.assignment_id}:{self.chunk_number}:{self.question_type}:{diff}:{self.content_hash}"