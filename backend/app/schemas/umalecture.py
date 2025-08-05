"""
Pydantic schemas for UMALecture module
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator


class LectureAssignmentBase(BaseModel):
    """Base schema for lecture assignments"""
    title: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=100)
    grade_level: str = Field(..., min_length=1, max_length=50)
    learning_objectives: List[str] = Field(..., min_items=1, max_items=10)


class LectureAssignmentCreate(LectureAssignmentBase):
    """Schema for creating a lecture assignment"""
    pass


class LectureAssignmentUpdate(BaseModel):
    """Schema for updating a lecture assignment"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = Field(None, min_length=1, max_length=100)
    grade_level: Optional[str] = Field(None, min_length=1, max_length=50)
    learning_objectives: Optional[List[str]] = Field(None, min_items=1, max_items=10)
    topic_outline: Optional[str] = Field(None, min_length=10)
    lecture_structure: Optional[Dict[str, Any]] = None


class LectureAssignmentResponse(LectureAssignmentBase):
    """Schema for lecture assignment responses"""
    id: UUID
    teacher_id: UUID
    topic_outline: Optional[str] = None
    lecture_structure: Optional[Dict[str, Any]] = None
    status: str
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    classroom_count: Optional[int] = None  # Add classroom_count as optional field for list views
    
    class Config:
        from_attributes = True


class LectureImageUpload(BaseModel):
    """Schema for image upload metadata"""
    node_id: str = Field(..., min_length=1, max_length=100)
    teacher_description: str = Field(..., min_length=1, max_length=500)
    position: int = Field(1, ge=1)


class LectureImageResponse(BaseModel):
    """Schema for lecture image responses"""
    id: UUID
    lecture_id: UUID
    filename: str
    teacher_description: str
    ai_description: Optional[str] = None
    node_id: str
    position: int
    original_url: str
    display_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class LectureProcessingStatus(BaseModel):
    """Schema for lecture processing status"""
    lecture_id: UUID
    status: str
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    processing_steps: Optional[Dict[str, Any]] = None


class LectureTopicContent(BaseModel):
    """Schema for topic content at a specific difficulty"""
    content: str
    images: List[LectureImageResponse]
    questions: List[Dict[str, Any]]


class LectureTopicResponse(BaseModel):
    """Schema for lecture topic information"""
    topic_id: str
    title: str
    available_difficulties: List[str]
    completed_difficulties: List[str] = []


class LectureContentResponse(BaseModel):
    """Schema for lecture content responses"""
    topic_id: str
    difficulty_level: str
    content: str
    images: List[LectureImageResponse]
    questions: List[Dict[str, Any]]
    next_difficulties: List[str]
    next_topics: List[str]


class LectureQuestionAnswer(BaseModel):
    """Schema for submitting question answers"""
    question_index: int
    answer: str


class LectureAnswerResult(BaseModel):
    """Schema for answer evaluation results"""
    is_correct: bool
    feedback: str
    next_action: str  # "next_question", "next_difficulty", "complete_topic"
    points_earned: int = 0


class LectureStudentProgress(BaseModel):
    """Schema for student progress on a lecture"""
    assignment_id: int  # classroom_assignment_id
    lecture_id: UUID
    current_topic: Optional[str] = None
    current_difficulty: Optional[str] = None
    topics_completed: List[str] = []
    topic_progress: Dict[str, List[str]] = {}  # topic_id -> completed difficulties
    total_points: int = 0
    last_activity_at: Optional[datetime] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class LectureOutlineContent(BaseModel):
    """Schema for lecture outline content submission"""
    topic_outline: str = Field(..., min_length=50, max_length=10000)
    
    @validator('topic_outline')
    def validate_outline_structure(cls, v):
        """Ensure outline has some structure"""
        lines = v.strip().split('\n')
        if len(lines) < 3:
            raise ValueError("Outline must have at least 3 lines")
        
        # Check for some indentation or bullet points
        has_structure = any(
            line.strip().startswith(('-', '*', '•', '  ', '\t'))
            for line in lines
        )
        if not has_structure:
            raise ValueError("Outline must have hierarchical structure with indentation or bullet points")
        
        return v


class LectureClassroomAssignment(BaseModel):
    """Schema for assigning lecture to classrooms"""
    classroom_ids: List[UUID]
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


# Progress Report Schemas for Teacher Analytics
class LectureProgressBadge(BaseModel):
    """Badge representation for a difficulty level"""
    level: str  # basic, intermediate, advanced, expert
    completed: bool
    questions_correct: int
    total_questions: int


class StudentLectureProgress(BaseModel):
    """Individual student progress for a lecture"""
    student_id: UUID
    student_name: str
    assignment_id: int
    lecture_id: UUID
    lecture_title: str
    started_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    current_topic: Optional[str]
    current_tab: Optional[str]
    topics_completed: int
    total_topics: int
    badges: List[LectureProgressBadge]
    overall_progress: float  # Percentage 0-100
    status: str  # not_started, in_progress, completed


class LectureProgressSummary(BaseModel):
    """Summary statistics for a lecture"""
    total_students: int
    students_started: int
    students_completed: int
    average_progress: float
    badge_distribution: Dict[str, int]  # {basic: 15, intermediate: 10, advanced: 5, expert: 2}


class LectureProgressReport(BaseModel):
    """Complete progress report for a classroom's lectures"""
    classroom_id: UUID
    classroom_name: str
    lectures: List[Dict[str, Any]]  # List of lectures with their student progress
    summary: LectureProgressSummary