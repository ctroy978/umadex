from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


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
    assignment_id: UUID
    title: str
    assignment_type: str
    assigned_at: datetime
    display_order: Optional[int] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateClassroomAssignmentsRequest(BaseModel):
    assignment_ids: List[UUID]


class UpdateClassroomAssignmentsResponse(BaseModel):
    added: List[UUID]
    removed: List[UUID]
    total: int


# Teacher's available assignments
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

    class Config:
        from_attributes = True


# Forward references update
ClassroomDetailResponse.model_rebuild()