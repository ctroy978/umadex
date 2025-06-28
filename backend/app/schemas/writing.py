from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, List, Any
from uuid import UUID
from datetime import datetime


class EvaluationCriteria(BaseModel):
    tone: List[str] = Field(default_factory=list)
    style: List[str] = Field(default_factory=list)
    perspective: List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    structure: List[str] = Field(default_factory=list)

    @field_validator('*')
    def validate_non_empty_list(cls, v, field):
        if not isinstance(v, list):
            raise ValueError(f"{field.field_name} must be a list")
        return v


class WritingAssignmentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    prompt_text: str = Field(..., min_length=10, max_length=1000)
    word_count_min: int = Field(default=50, ge=10, le=1000)
    word_count_max: int = Field(default=500, ge=50, le=2000)
    instructions: Optional[str] = Field(None, max_length=1000)
    grade_level: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=100)

    @field_validator('word_count_max')
    def validate_word_count_range(cls, v, values):
        if 'word_count_min' in values.data and v <= values.data['word_count_min']:
            raise ValueError('word_count_max must be greater than word_count_min')
        return v


class WritingAssignmentCreate(WritingAssignmentBase):
    evaluation_criteria: EvaluationCriteria = Field(default_factory=EvaluationCriteria)

    @field_validator('evaluation_criteria')
    def validate_criteria(cls, v):
        # Ensure at least one criterion is selected
        if not any([v.tone, v.style, v.perspective, v.techniques, v.structure]):
            raise ValueError("At least one evaluation criterion must be selected")
        return v


class WritingAssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    prompt_text: Optional[str] = Field(None, min_length=10, max_length=1000)
    word_count_min: Optional[int] = Field(None, ge=10, le=1000)
    word_count_max: Optional[int] = Field(None, ge=50, le=2000)
    evaluation_criteria: Optional[EvaluationCriteria] = None
    instructions: Optional[str] = Field(None, max_length=1000)
    grade_level: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=100)

    @field_validator('word_count_max')
    def validate_word_count_range(cls, v, values):
        if v is not None and 'word_count_min' in values.data and values.data['word_count_min'] is not None:
            if v <= values.data['word_count_min']:
                raise ValueError('word_count_max must be greater than word_count_min')
        return v


class WritingAssignmentResponse(WritingAssignmentBase):
    id: UUID
    teacher_id: UUID
    evaluation_criteria: Dict[str, List[str]]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    classroom_count: int = 0
    is_archived: bool = False

    model_config = ConfigDict(from_attributes=True)


class WritingAssignmentListResponse(BaseModel):
    assignments: List[WritingAssignmentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class StudentWritingSubmissionBase(BaseModel):
    submission_text: str = Field(..., min_length=1, max_length=50000)


class StudentWritingSubmissionCreate(StudentWritingSubmissionBase):
    assignment_id: UUID
    classroom_id: UUID


class StudentWritingSubmissionUpdate(BaseModel):
    submission_text: Optional[str] = Field(None, min_length=1, max_length=50000)


class StudentWritingSubmissionResponse(StudentWritingSubmissionBase):
    id: UUID
    student_id: UUID
    assignment_id: UUID
    classroom_id: UUID
    word_count: int
    submitted_at: datetime
    updated_at: datetime
    evaluation_score: Optional[Dict[str, Any]] = None
    evaluation_feedback: Optional[str] = None
    evaluated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WritingAssignmentWithProgress(WritingAssignmentResponse):
    submission: Optional[StudentWritingSubmissionResponse] = None
    is_submitted: bool = False