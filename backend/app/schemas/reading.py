from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


class ReadingAssignmentMetadata(BaseModel):
    assignment_title: str = Field(..., min_length=1, max_length=255)
    work_title: str = Field(..., min_length=1, max_length=255)
    author: Optional[str] = Field(None, max_length=255)
    grade_level: Literal["K-2", "3-5", "6-8", "9-10", "11-12", "College", "Adult Education"]
    work_type: Literal["fiction", "non-fiction"]
    literary_form: Literal["prose", "poetry", "drama", "mixed"]
    genre: Literal[
        "Adventure", "Fantasy", "Historical", "Mystery", "Mythology", 
        "Realistic Fiction", "Science Fiction", "Biography", "Essay", 
        "Informational", "Science", "Other"
    ]
    subject: Literal["English Literature", "History", "Science", "Social Studies", "ESL/ELL", "Other"]


class ReadingAssignmentCreate(ReadingAssignmentMetadata):
    raw_content: str = Field(default="", min_length=0)


class ReadingAssignmentUpdate(BaseModel):
    assignment_title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    work_title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    author: Optional[str] = Field(default=None, max_length=255)
    grade_level: Optional[Literal["K-2", "3-5", "6-8", "9-10", "11-12", "College", "Adult Education"]] = None
    work_type: Optional[Literal["fiction", "non-fiction"]] = None
    literary_form: Optional[Literal["prose", "poetry", "drama", "mixed"]] = None
    genre: Optional[Literal[
        "Adventure", "Fantasy", "Historical", "Mystery", "Mythology", 
        "Realistic Fiction", "Science Fiction", "Biography", "Essay", 
        "Informational", "Science", "Other"
    ]] = None
    subject: Optional[Literal["English Literature", "History", "Science", "Social Studies", "ESL/ELL", "Other"]] = None
    raw_content: Optional[str] = Field(default=None, min_length=0)


class AssignmentImageUpload(BaseModel):
    custom_name: Optional[str] = Field(None, max_length=100)


class AssignmentImage(BaseModel):
    id: UUID
    image_tag: str  # 'image-1', 'image-2', etc.
    image_key: str  # Unique file identifier
    file_name: Optional[str]  # Original filename
    original_url: str  # 2000x2000 max
    display_url: str   # 800x600 max
    thumbnail_url: str  # 200x150 max
    image_url: str  # Backward compatibility (same as display_url)
    width: int  # Original dimensions
    height: int
    file_size: int  # In bytes
    mime_type: str
    ai_description: Optional[str] = None  # AI-generated description
    description_generated_at: Optional[datetime] = None
    created_at: datetime
    uploaded_at: datetime  # Backward compatibility

    class Config:
        from_attributes = True


class ReadingChunk(BaseModel):
    id: UUID
    chunk_order: int
    content: str
    has_important_sections: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReadingAssignmentBase(BaseModel):
    id: UUID
    teacher_id: UUID
    assignment_title: str
    work_title: str
    author: Optional[str]
    grade_level: str
    work_type: str
    literary_form: str
    genre: str
    subject: str
    raw_content: str
    total_chunks: Optional[int]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReadingAssignment(ReadingAssignmentBase):
    chunks: List[ReadingChunk] = []
    images: List[AssignmentImage] = []

    class Config:
        from_attributes = True


class ReadingAssignmentList(BaseModel):
    id: UUID
    assignment_title: str
    work_title: str
    author: Optional[str]
    grade_level: str
    subject: str
    status: str
    total_chunks: Optional[int]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True


class MarkupValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    chunk_count: int = 0
    image_references: List[str] = []


class PublishResult(BaseModel):
    success: bool
    message: str
    chunk_count: Optional[int] = None


class ReadingAssignmentListResponse(BaseModel):
    assignments: List[ReadingAssignmentList]
    total: int
    filtered: int
    page: int
    per_page: int