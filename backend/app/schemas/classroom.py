from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, validator


# Base schemas
class ClassroomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ClassroomCreate(ClassroomBase):
    pass


class ClassroomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class ClassroomInDB(ClassroomBase):
    id: UUID
    teacher_id: UUID
    class_code: str
    created_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClassroomResponse(ClassroomInDB):
    student_count: int = 0
    assignment_count: int = 0


class ClassroomDetailResponse(ClassroomResponse):
    students: List["StudentInClassroom"] = []
    assignments: List["AssignmentInClassroom"] = []


# Student enrollment schemas
class StudentInClassroom(BaseModel):
    id: UUID
    email: str
    full_name: str
    joined_at: datetime
    removed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JoinClassroomRequest(BaseModel):
    class_code: str = Field(..., min_length=6, max_length=8)


class JoinClassroomResponse(BaseModel):
    classroom: ClassroomResponse
    message: str


# Assignment in classroom schemas
class AssignmentInClassroom(BaseModel):
    id: int  # classroom_assignment.id
    assignment_id: UUID
    title: str
    assignment_type: str
    assigned_at: datetime
    display_order: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssignmentSchedule(BaseModel):
    assignment_id: UUID
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class UpdateClassroomAssignmentsRequest(BaseModel):
    assignments: List[AssignmentSchedule]


class UpdateClassroomAssignmentsResponse(BaseModel):
    added: List[UUID]
    removed: List[UUID]
    total: int


# Teacher's available assignments
class CurrentSchedule(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AvailableAssignment(BaseModel):
    id: UUID
    assignment_title: str
    work_title: str
    author: str
    assignment_type: str
    grade_level: str
    work_type: str
    created_at: datetime
    is_assigned: bool = False
    is_archived: bool = False
    current_schedule: Optional[CurrentSchedule] = None

    class Config:
        from_attributes = True


# Vocabulary settings schemas
class VocabularySettings(BaseModel):
    delivery_mode: Literal["all_at_once", "in_groups", "teacher_controlled"] = "all_at_once"
    group_size: Optional[int] = Field(None, ge=5, le=8)
    release_condition: Optional[Literal["immediate", "after_test"]] = None
    allow_test_retakes: bool = True
    max_test_attempts: int = Field(2, ge=1, le=5)
    released_groups: List[int] = Field(default_factory=list)
    
    @validator('group_size')
    def validate_group_size(cls, v, values):
        if values.get('delivery_mode') in ['in_groups', 'teacher_controlled'] and v is None:
            raise ValueError('group_size is required for in_groups and teacher_controlled modes')
        return v
    
    @validator('release_condition')
    def validate_release_condition(cls, v, values):
        if values.get('delivery_mode') == 'in_groups' and v is None:
            raise ValueError('release_condition is required for in_groups mode')
        return v


class VocabularySettingsUpdate(BaseModel):
    delivery_mode: Optional[Literal["all_at_once", "in_groups", "teacher_controlled"]] = None
    group_size: Optional[int] = Field(None, ge=5, le=8)
    release_condition: Optional[Literal["immediate", "after_test"]] = None
    allow_test_retakes: Optional[bool] = None
    max_test_attempts: Optional[int] = Field(None, ge=1, le=5)


class VocabularySettingsResponse(BaseModel):
    assignment_id: int
    vocabulary_list_id: UUID
    settings: VocabularySettings
    total_words: int
    groups_count: Optional[int] = None
    
    class Config:
        from_attributes = True


# Forward references update
ClassroomDetailResponse.model_rebuild()