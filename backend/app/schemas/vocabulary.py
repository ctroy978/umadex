from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.models.vocabulary import VocabularyStatus, DefinitionSource, ReviewStatus


# Base schemas
class VocabularyWordBase(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    teacher_definition: Optional[str] = None
    teacher_example_1: Optional[str] = None
    teacher_example_2: Optional[str] = None


class VocabularyListBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    context_description: str = Field(..., min_length=10)
    grade_level: str = Field(..., min_length=1, max_length=50)
    subject_area: str = Field(..., min_length=1, max_length=100)


# Create schemas
class VocabularyWordCreate(VocabularyWordBase):
    pass


class VocabularyListCreate(VocabularyListBase):
    words: List[VocabularyWordCreate] = Field(..., min_length=4, max_length=8)
    
    @field_validator('words')
    def validate_unique_words(cls, v):
        word_texts = [w.word.lower() for w in v]
        if len(word_texts) != len(set(word_texts)):
            raise ValueError('Duplicate words are not allowed')
        return v


# Update schemas
class VocabularyWordUpdate(BaseModel):
    teacher_definition: Optional[str] = None
    teacher_example_1: Optional[str] = None
    teacher_example_2: Optional[str] = None


class VocabularyListUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    context_description: Optional[str] = Field(None, min_length=10)
    grade_level: Optional[str] = Field(None, min_length=1, max_length=50)
    subject_area: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[VocabularyStatus] = None


# Review schemas
class VocabularyWordReviewRequest(BaseModel):
    action: str = Field(..., pattern="^(accept|reject)$")
    rejection_feedback: Optional[str] = Field(None, min_length=10)
    
    @field_validator('rejection_feedback')
    def validate_feedback(cls, v, info):
        if info.data.get('action') == 'reject' and not v:
            raise ValueError('Rejection feedback is required when rejecting')
        return v


class VocabularyWordManualUpdate(BaseModel):
    definition: str = Field(..., min_length=10)
    example_1: str = Field(..., min_length=10)
    example_2: str = Field(..., min_length=10)


# Response schemas
class VocabularyWordReviewResponse(BaseModel):
    id: UUID
    word_id: UUID
    review_status: ReviewStatus
    rejection_feedback: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class VocabularyWordResponse(BaseModel):
    id: UUID
    list_id: UUID
    word: str
    teacher_definition: Optional[str]
    teacher_example_1: Optional[str]
    teacher_example_2: Optional[str]
    ai_definition: Optional[str]
    ai_example_1: Optional[str]
    ai_example_2: Optional[str]
    definition_source: DefinitionSource
    examples_source: DefinitionSource
    position: int
    audio_url: Optional[str]
    phonetic_text: Optional[str]
    created_at: datetime
    updated_at: datetime
    review: Optional[VocabularyWordReviewResponse]
    
    class Config:
        from_attributes = True


class VocabularyListResponse(BaseModel):
    id: UUID
    teacher_id: UUID
    title: str
    context_description: str
    grade_level: str
    subject_area: str
    status: VocabularyStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    words: Optional[List[VocabularyWordResponse]] = None
    word_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class VocabularyListSummary(BaseModel):
    id: UUID
    title: str
    grade_level: str
    subject_area: str
    status: VocabularyStatus
    word_count: int
    review_progress: int  # Percentage of words reviewed
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Pagination
class VocabularyListPagination(BaseModel):
    items: List[VocabularyListSummary]
    total: int
    page: int
    per_page: int
    pages: int


# Export schemas
class VocabularyExportFormat(BaseModel):
    format: str = Field(..., pattern="^(pdf|csv)$")


# AI Generation schemas
class VocabularyAIRequest(BaseModel):
    word: str
    context_description: str
    grade_level: str
    subject_area: str
    rejection_feedback: Optional[str] = None


class VocabularyAIResponse(BaseModel):
    definition: str
    example_1: str
    example_2: str


# Vocabulary Test Schemas
class VocabularyTestConfig(BaseModel):
    chain_enabled: bool = False
    weeks_to_include: int = Field(default=1, ge=1, le=10)
    questions_per_week: int = Field(default=3, ge=2, le=4)
    current_week_questions: int = Field(default=6, ge=4, le=8)
    max_attempts: int = Field(default=3, ge=1, le=5)
    time_limit_minutes: int = Field(default=30, ge=10, le=120)


class VocabularyTestConfigResponse(VocabularyTestConfig):
    id: UUID
    vocabulary_list_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VocabularyTestQuestion(BaseModel):
    word: str
    definition: str
    question_type: str  # "definition", "example", "riddle"
    question_text: str
    correct_answer: str
    vocabulary_list_id: UUID
    difficulty_level: Optional[str] = None


class VocabularyTestResponse(BaseModel):
    test_id: UUID
    vocabulary_list_id: UUID
    total_questions: int
    questions: List[VocabularyTestQuestion]
    time_limit_minutes: int
    max_attempts: int
    chained_lists: List[UUID] = []
    expires_at: datetime
    created_at: datetime


class VocabularyTestEligibilityResponse(BaseModel):
    eligible: bool
    reason: Optional[str] = None
    assignments_completed: int
    assignments_required: int
    progress_details: Dict[str, bool]  # flashcards_completed, practice_completed, etc.


class VocabularyTestAttemptRequest(BaseModel):
    responses: Dict[str, str]  # question_id -> student_answer


class VocabularyTestAttemptResponse(BaseModel):
    test_attempt_id: UUID
    test_id: UUID
    score_percentage: float
    questions_correct: int
    total_questions: int
    time_spent_seconds: Optional[int]
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    detailed_results: List[Dict[str, Any]]  # question-by-question results


class VocabularyProgressUpdate(BaseModel):
    assignment_type: str = Field(..., pattern="^(flashcards|practice|challenge|sentences)$")
    completed: bool = True


class TimeRestrictionConfig(BaseModel):
    allowed_days: List[str] = Field(default=["monday", "tuesday", "wednesday", "thursday", "friday"])
    allowed_times: List[Dict[str, str]] = Field(default=[{"start": "08:00", "end": "16:00"}])
    timezone: str = Field(default="America/Los_Angeles")


class ClassroomAssignmentTestConfig(BaseModel):
    test_start_date: Optional[datetime] = None
    test_end_date: Optional[datetime] = None
    test_time_restrictions: Optional[TimeRestrictionConfig] = None