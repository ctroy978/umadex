from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
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
    words: List[VocabularyWordCreate] = Field(..., min_length=5, max_length=50)
    
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