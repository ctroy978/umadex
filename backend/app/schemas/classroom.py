from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.classroom import UmaType

class ClassroomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subject: Optional[str] = Field(None, max_length=255)
    grade_level: Optional[str] = Field(None, max_length=50)
    school_year: Optional[str] = Field(None, max_length=20)

class ClassroomCreate(ClassroomBase):
    pass

class ClassroomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = Field(None, max_length=255)
    grade_level: Optional[str] = Field(None, max_length=50)
    school_year: Optional[str] = Field(None, max_length=20)

class ClassroomResponse(ClassroomBase):
    id: UUID
    teacher_id: UUID
    created_at: datetime
    updated_at: datetime
    student_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class ClassroomStudentResponse(BaseModel):
    id: UUID
    student_id: UUID
    first_name: str
    last_name: str
    email: str
    enrolled_at: datetime
    status: str
    
    class Config:
        from_attributes = True

class AssignmentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    uma_type: UmaType
    classroom_id: Optional[UUID] = None
    description: Optional[str] = None
    content: Optional[dict] = None
    due_date: Optional[datetime] = None
    is_published: bool = False

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    content: Optional[dict] = None
    due_date: Optional[datetime] = None
    is_published: Optional[bool] = None

class AssignmentResponse(AssignmentBase):
    id: UUID
    teacher_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_classrooms: int
    total_students: int
    active_assignments: int
    recent_assignments: List[AssignmentResponse]

class EnrollStudentRequest(BaseModel):
    student_email: str