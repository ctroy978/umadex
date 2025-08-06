"""
Pydantic schemas for UMATest module
Phase 1: Test Creation System
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID


# Question distribution constants
QUESTION_DISTRIBUTION = {
    "BASIC_INTERMEDIATE_PERCENT": 70,
    "ADVANCED_PERCENT": 20,
    "EXPERT_PERCENT": 10,
    "QUESTIONS_PER_TOPIC": 10
}


class AnswerKey(BaseModel):
    """Answer key for a test question"""
    correct_answer: str
    explanation: str
    evaluation_rubric: str


class TestQuestion(BaseModel):
    """Individual test question"""
    id: str
    question_text: str
    difficulty_level: str
    source_content: str
    answer_key: AnswerKey


class TopicQuestions(BaseModel):
    """Questions for a specific topic"""
    topic_title: str
    source_lecture_id: str
    source_lecture_title: str
    questions: List[TestQuestion]


class GenerationMetadata(BaseModel):
    """Metadata about test generation"""
    generated_at: datetime
    ai_model: str
    distribution: Dict[str, int]


class TestStructure(BaseModel):
    """Complete test structure"""
    total_questions: int
    topics: Dict[str, TopicQuestions]
    generation_metadata: GenerationMetadata


# Hand-built test schemas
class HandBuiltQuestionCreate(BaseModel):
    """Create a hand-built test question"""
    question_text: str = Field(..., min_length=1)
    correct_answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)
    evaluation_rubric: str = Field(..., min_length=1)
    difficulty_level: str = Field(..., pattern='^(basic|intermediate|advanced|expert)$')
    points: Optional[int] = Field(10, gt=0)


class HandBuiltQuestionUpdate(BaseModel):
    """Update a hand-built test question"""
    question_text: Optional[str] = Field(None, min_length=1)
    correct_answer: Optional[str] = Field(None, min_length=1)
    explanation: Optional[str] = Field(None, min_length=1)
    evaluation_rubric: Optional[str] = Field(None, min_length=1)
    difficulty_level: Optional[str] = Field(None, pattern='^(basic|intermediate|advanced|expert)$')
    points: Optional[int] = Field(None, gt=0)


class HandBuiltQuestionResponse(BaseModel):
    """Response for a hand-built test question"""
    id: UUID
    test_assignment_id: UUID
    question_text: str
    correct_answer: str
    explanation: str
    evaluation_rubric: str
    difficulty_level: str
    position: int
    points: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Request schemas
class CreateTestRequest(BaseModel):
    """Request to create a new test"""
    test_title: str = Field(..., min_length=1, max_length=255)
    test_description: Optional[str] = None
    test_type: str = Field('lecture_based', pattern='^(lecture_based|hand_built)$')
    selected_lecture_ids: Optional[List[UUID]] = None
    time_limit_minutes: Optional[int] = Field(None, gt=0)
    attempt_limit: Optional[int] = Field(1, gt=0)
    randomize_questions: Optional[bool] = False
    show_feedback_immediately: Optional[bool] = True
    
    @validator('selected_lecture_ids')
    def validate_lecture_ids(cls, v, values):
        test_type = values.get('test_type', 'lecture_based')
        if test_type == 'lecture_based' and (not v or len(v) == 0):
            raise ValueError("At least one lecture must be selected for lecture-based tests")
        elif test_type == 'hand_built' and v:
            raise ValueError("Hand-built tests should not have selected lectures")
        return v


class UpdateTestRequest(BaseModel):
    """Request to update test settings"""
    test_title: Optional[str] = Field(None, min_length=1, max_length=255)
    test_description: Optional[str] = None
    time_limit_minutes: Optional[int] = Field(None, gt=0)
    attempt_limit: Optional[int] = Field(None, gt=0)
    randomize_questions: Optional[bool] = None
    show_feedback_immediately: Optional[bool] = None
    status: Optional[str] = Field(None, pattern='^(draft|published|archived)$')


class GenerateTestQuestionsRequest(BaseModel):
    """Request to generate test questions"""
    test_assignment_id: UUID
    regenerate: Optional[bool] = False


# Response schemas
class TestAssignmentBase(BaseModel):
    """Base test assignment data"""
    id: UUID
    teacher_id: UUID
    test_title: str
    test_description: Optional[str]
    test_type: str
    selected_lecture_ids: Optional[List[UUID]]
    time_limit_minutes: Optional[int]
    attempt_limit: int
    randomize_questions: bool
    show_feedback_immediately: bool
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TestAssignmentResponse(TestAssignmentBase):
    """Test assignment response with structure"""
    test_structure: Optional[Dict[str, Any]] = None
    total_questions: Optional[int] = None
    is_archived: Optional[bool] = False
    
    @validator('total_questions', always=True)
    def calculate_total_questions(cls, v, values):
        if 'test_structure' in values and values['test_structure'] and isinstance(values['test_structure'], dict):
            return values['test_structure'].get('total_questions', 0)
        return 0


class LectureInfo(BaseModel):
    """Basic info about a lecture"""
    id: UUID
    title: str
    subject: str
    grade_level: str
    topic_count: int


class TestDetailResponse(TestAssignmentResponse):
    """Detailed test response with lecture info"""
    selected_lectures: Optional[List[LectureInfo]] = None


class TestListResponse(BaseModel):
    """Paginated list of tests"""
    tests: List[TestAssignmentResponse]
    total_count: int
    page: int
    page_size: int


class QuestionGenerationProgress(BaseModel):
    """Progress update for question generation"""
    test_assignment_id: UUID
    status: str
    progress: Dict[str, Any]
    error: Optional[str] = None


class GenerationLogResponse(BaseModel):
    """Generation log details"""
    id: UUID
    test_assignment_id: UUID
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    error_message: Optional[str]
    total_topics_processed: int
    total_questions_generated: int
    cache_hits: int
    cache_misses: int
    ai_tokens_used: int
    ai_model: Optional[str]
    
    class Config:
        from_attributes = True


# Helper functions
def calculate_question_counts(total_topics: int) -> Dict[str, Any]:
    """Calculate question distribution based on topic count"""
    questions_per_topic = QUESTION_DISTRIBUTION["QUESTIONS_PER_TOPIC"]
    total = total_topics * questions_per_topic
    
    return {
        "total": total,
        "basic_intermediate": round((total * QUESTION_DISTRIBUTION["BASIC_INTERMEDIATE_PERCENT"]) / 100),
        "advanced": round((total * QUESTION_DISTRIBUTION["ADVANCED_PERCENT"]) / 100),
        "expert": round((total * QUESTION_DISTRIBUTION["EXPERT_PERCENT"]) / 100),
        "per_topic": {
            "basic_intermediate": round((questions_per_topic * QUESTION_DISTRIBUTION["BASIC_INTERMEDIATE_PERCENT"]) / 100),
            "advanced": round((questions_per_topic * QUESTION_DISTRIBUTION["ADVANCED_PERCENT"]) / 100),
            "expert": round((questions_per_topic * QUESTION_DISTRIBUTION["EXPERT_PERCENT"]) / 100)
        }
    }