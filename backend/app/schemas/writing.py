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
    response_text: str = Field(..., min_length=1, max_length=50000, alias="content")
    selected_techniques: List[str] = Field(default_factory=list, max_length=5)
    word_count: int = Field(..., ge=1)


class StudentWritingSubmissionCreate(StudentWritingSubmissionBase):
    is_final: bool = Field(default=True)


class StudentWritingSubmissionUpdate(BaseModel):
    response_text: Optional[str] = Field(None, min_length=1, max_length=50000)
    selected_techniques: Optional[List[str]] = Field(None, max_length=5)


class StudentWritingSubmissionResponse(BaseModel):
    id: UUID
    student_assignment_id: UUID
    writing_assignment_id: UUID
    student_id: UUID
    response_text: str
    selected_techniques: List[str]
    word_count: int
    submission_attempt: int
    is_final_submission: bool
    submitted_at: datetime
    score: Optional[float] = None
    ai_feedback: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class StudentWritingDraft(BaseModel):
    content: str
    selected_techniques: List[str] = Field(default_factory=list, max_length=5)
    word_count: int


class StudentWritingProgress(BaseModel):
    student_assignment_id: UUID
    draft_content: str = ""
    selected_techniques: List[str] = Field(default_factory=list)
    word_count: int = 0
    last_saved_at: Optional[str] = None
    status: str
    submission_count: int = 0


class WritingAssignmentWithProgress(WritingAssignmentResponse):
    submission: Optional[StudentWritingSubmissionResponse] = None
    is_submitted: bool = False