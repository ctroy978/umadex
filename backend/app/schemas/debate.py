"""
Pydantic schemas for UMADebate module
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FallacyFrequency(str, Enum):
    EVERY_1_2 = "every_1_2"
    EVERY_2_3 = "every_2_3"
    EVERY_3_4 = "every_3_4"
    DISABLED = "disabled"


class FlagType(str, Enum):
    PROFANITY = "profanity"
    INAPPROPRIATE = "inappropriate"
    OFF_TOPIC = "off_topic"
    SPAM = "spam"


class FlagStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


# Request schemas
class DebateAssignmentCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    topic: str = Field(..., min_length=10, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    grade_level: str
    subject: str
    rounds_per_debate: int = Field(3, ge=2, le=4)
    debate_count: int = Field(3, ge=1, le=10)
    time_limit_hours: int = Field(8, ge=4, le=24)
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    fallacy_frequency: FallacyFrequency = FallacyFrequency.EVERY_2_3
    ai_personalities_enabled: bool = True
    content_moderation_enabled: bool = True
    auto_flag_off_topic: bool = True

    @validator('topic')
    def validate_topic_is_debatable(cls, v):
        if not v.strip():
            raise ValueError('Topic cannot be empty')
        # Additional validation can be added here
        return v.strip()

    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class DebateAssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    topic: Optional[str] = Field(None, min_length=10, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    rounds_per_debate: Optional[int] = Field(None, ge=2, le=4)
    debate_count: Optional[int] = Field(None, ge=1, le=10)
    time_limit_hours: Optional[int] = Field(None, ge=4, le=24)
    difficulty_level: Optional[DifficultyLevel] = None
    fallacy_frequency: Optional[FallacyFrequency] = None
    ai_personalities_enabled: Optional[bool] = None
    content_moderation_enabled: Optional[bool] = None
    auto_flag_off_topic: Optional[bool] = None


# Response schemas
class DebateAssignmentResponse(BaseModel):
    id: UUID
    teacher_id: UUID
    title: str
    topic: str
    description: Optional[str]
    grade_level: str
    subject: str
    rounds_per_debate: int
    debate_count: int
    time_limit_hours: int
    difficulty_level: DifficultyLevel
    fallacy_frequency: FallacyFrequency
    ai_personalities_enabled: bool
    content_moderation_enabled: bool
    auto_flag_off_topic: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True


class DebateAssignmentSummary(BaseModel):
    id: UUID
    title: str
    topic: str
    grade_level: str
    subject: str
    rounds_per_debate: int
    debate_count: int
    time_limit_hours: int
    created_at: datetime
    deleted_at: Optional[datetime]
    # Additional computed fields for dashboard
    student_count: int = 0
    completion_rate: float = 0.0

    class Config:
        from_attributes = True


class DebateAssignmentListResponse(BaseModel):
    assignments: List[DebateAssignmentSummary]
    total: int
    filtered: int
    page: int
    per_page: int


# Content Flag schemas
class ContentFlagCreate(BaseModel):
    post_id: Optional[UUID]  # Will be required in Phase 2
    student_id: UUID
    assignment_id: UUID
    flag_type: FlagType
    flag_reason: Optional[str] = Field(None, max_length=500)
    auto_flagged: bool = False
    confidence_score: Optional[float] = Field(None, ge=0, le=1)


class ContentFlagUpdate(BaseModel):
    status: FlagStatus
    teacher_action: Optional[str] = Field(None, max_length=50)
    teacher_notes: Optional[str] = Field(None, max_length=1000)


class ContentFlagResponse(BaseModel):
    id: UUID
    post_id: Optional[UUID]
    student_id: UUID
    teacher_id: UUID
    assignment_id: UUID
    flag_type: FlagType
    flag_reason: Optional[str]
    auto_flagged: bool
    confidence_score: Optional[float]
    status: FlagStatus
    teacher_action: Optional[str]
    teacher_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    # Additional fields for UI
    student_name: Optional[str] = None
    assignment_title: Optional[str] = None

    class Config:
        from_attributes = True


# Filter schemas
class DebateAssignmentFilters(BaseModel):
    search: Optional[str] = None
    grade_level: Optional[str] = None
    subject: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    include_archived: bool = False