from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Literal
from uuid import UUID

from pydantic import BaseModel, Field, validator


# Enums
DebateStatus = Literal['not_started', 'debate_1', 'debate_2', 'debate_3', 'completed']
DebatePosition = Literal['pro', 'con', 'choice']
PostType = Literal['student', 'ai']
ChallengeType = Literal['fallacy', 'appeal']
ModerationStatus = Literal['pending', 'approved', 'rejected', 'revision_requested']


# Student Debate Models
class StudentDebateBase(BaseModel):
    assignment_id: UUID
    classroom_assignment_id: int


class StudentDebateCreate(StudentDebateBase):
    pass


class StudentDebateUpdate(BaseModel):
    status: Optional[DebateStatus] = None
    current_debate: Optional[int] = Field(None, ge=1, le=3)
    current_round: Optional[int] = Field(None, ge=1)
    debate_3_position: Optional[DebatePosition] = None
    current_debate_started_at: Optional[datetime] = None
    current_debate_deadline: Optional[datetime] = None


class StudentDebate(StudentDebateBase):
    id: UUID
    student_id: UUID
    status: DebateStatus
    current_debate: int
    current_round: int
    
    debate_1_position: Optional[DebatePosition]
    debate_2_position: Optional[DebatePosition]
    debate_3_position: Optional[DebatePosition]
    
    fallacy_counter: int
    fallacy_scheduled_debate: Optional[int]
    fallacy_scheduled_round: Optional[int]
    
    assignment_started_at: Optional[datetime]
    current_debate_started_at: Optional[datetime]
    current_debate_deadline: Optional[datetime]
    
    debate_1_percentage: Optional[Decimal]
    debate_2_percentage: Optional[Decimal]
    debate_3_percentage: Optional[Decimal]
    final_percentage: Optional[Decimal]
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Debate Post Models
class DebatePostBase(BaseModel):
    content: str = Field(..., min_length=1)
    word_count: int = Field(..., ge=0)


class StudentPostCreate(DebatePostBase):
    @validator('word_count')
    def validate_word_count(cls, v, values):
        # Validate word count is within assignment limits (75-300 for high school)
        if v < 75 or v > 300:
            raise ValueError('Post must be between 75-300 words')
        return v


class AIPostCreate(DebatePostBase):
    ai_personality: str
    is_fallacy: bool = False
    fallacy_type: Optional[str] = None


class DebatePost(DebatePostBase):
    id: UUID
    student_debate_id: UUID
    debate_number: int
    round_number: int
    statement_number: int  # 1-5 for the debate flow
    post_type: PostType
    
    ai_personality: Optional[str]
    is_fallacy: bool
    fallacy_type: Optional[str]
    
    clarity_score: Optional[Decimal]
    evidence_score: Optional[Decimal]
    logic_score: Optional[Decimal]
    persuasiveness_score: Optional[Decimal]
    rebuttal_score: Optional[Decimal]
    base_percentage: Optional[Decimal]
    bonus_points: Decimal
    final_percentage: Optional[Decimal]
    
    content_flagged: bool
    moderation_status: ModerationStatus
    ai_feedback: Optional[str]
    
    created_at: datetime

    class Config:
        from_attributes = True


# Challenge Models
class ChallengeCreate(BaseModel):
    post_id: UUID
    challenge_type: ChallengeType
    challenge_value: str
    explanation: Optional[str] = Field(None, min_length=10, max_length=500)


class ChallengeResult(BaseModel):
    is_correct: bool
    points_awarded: Decimal
    ai_feedback: str


class DebateChallenge(BaseModel):
    id: UUID
    post_id: UUID
    student_id: UUID
    challenge_type: ChallengeType
    challenge_value: str
    explanation: Optional[str]
    is_correct: bool
    points_awarded: Decimal
    ai_feedback: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Scoring Models
class PostScore(BaseModel):
    clarity: Decimal = Field(..., ge=1, le=5)
    evidence: Decimal = Field(..., ge=1, le=5)
    logic: Decimal = Field(..., ge=1, le=5)
    persuasiveness: Decimal = Field(..., ge=1, le=5)
    rebuttal: Decimal = Field(..., ge=1, le=5)
    base_percentage: Decimal
    bonus_points: Decimal = Decimal('0.0')
    final_percentage: Decimal
    feedback: str


class DebateScore(BaseModel):
    debate_number: int
    posts: List[PostScore]
    average_percentage: Decimal
    total_bonus_points: Decimal
    final_percentage: Decimal


class AssignmentScore(BaseModel):
    debate_1_score: Optional[DebateScore]
    debate_2_score: Optional[DebateScore]
    debate_3_score: Optional[DebateScore]
    improvement_bonus: Decimal = Decimal('0.0')
    consistency_bonus: Decimal = Decimal('0.0')
    final_grade: Decimal


# Progress Models
class DebateProgress(BaseModel):
    student_debate: StudentDebate
    current_posts: List[DebatePost]
    available_challenges: List[dict]
    time_remaining: Optional[int]  # seconds
    can_submit_post: bool
    next_action: Literal['submit_post', 'await_ai', 'choose_position', 'debate_complete', 'assignment_complete']


class AssignmentOverview(BaseModel):
    assignment_id: UUID
    title: str
    topic: str
    difficulty_level: str
    debate_format: dict
    status: DebateStatus
    debates_completed: int
    current_debate_position: Optional[DebatePosition]
    time_remaining: Optional[int]
    can_start: bool
    access_date: datetime
    due_date: datetime


# AI Personality Models
class AIPersonality(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: str
    prompt_template: str
    difficulty_levels: List[str]
    active: bool

    class Config:
        from_attributes = True


# Fallacy Template Models
class FallacyTemplate(BaseModel):
    id: UUID
    fallacy_type: str
    display_name: str
    description: str
    template: str
    difficulty_levels: List[str]
    topic_keywords: List[str]
    active: bool

    class Config:
        from_attributes = True


# Position Selection
class PositionSelection(BaseModel):
    position: Literal['pro', 'con']
    reason: Optional[str] = Field(None, max_length=200)


# Round Feedback Models
class RoundFeedback(BaseModel):
    id: UUID
    student_debate_id: UUID
    debate_number: int
    coaching_feedback: str
    strengths: Optional[str]
    improvement_areas: Optional[str]
    specific_suggestions: Optional[str]
    round_completed_at: datetime

    class Config:
        from_attributes = True


# AI Debate Point Models
class AIDebatePointCreate(BaseModel):
    assignment_id: UUID
    debate_number: int = Field(..., ge=1, le=3)
    position: Literal['pro', 'con']
    debate_point: str
    supporting_evidence: List[str]


# Content Moderation
class ModerationResult(BaseModel):
    flagged: bool
    flag_type: Optional[Literal['profanity', 'inappropriate', 'off_topic']]
    confidence: float
    requires_review: bool
    suggested_revision: Optional[str]