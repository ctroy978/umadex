from datetime import datetime, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID
from enum import Enum


class DayOfWeek(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ScheduleWindow(BaseModel):
    id: str
    name: str
    days: List[DayOfWeek]
    start_time: str  # HH:MM format
    end_time: str    # HH:MM format
    color: Optional[str] = "#3B82F6"
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        try:
            time.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format')
    
    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values:
            start = time.fromisoformat(values['start_time'])
            end = time.fromisoformat(v)
            if end <= start:
                raise ValueError('End time must be after start time')
        return v


class ScheduleSettings(BaseModel):
    pre_test_buffer_minutes: int = Field(default=5, ge=0, le=30)
    allow_weekend_testing: bool = False
    emergency_override_enabled: bool = True


class ScheduleData(BaseModel):
    windows: List[ScheduleWindow]
    settings: ScheduleSettings = ScheduleSettings()
    templates_used: List[str] = []


class ClassroomTestScheduleBase(BaseModel):
    is_active: bool = True
    timezone: str = "America/New_York"
    grace_period_minutes: int = Field(default=30, ge=0, le=120)
    schedule_data: ScheduleData


class ClassroomTestScheduleCreate(ClassroomTestScheduleBase):
    classroom_id: UUID


class ClassroomTestScheduleUpdate(BaseModel):
    is_active: Optional[bool] = None
    timezone: Optional[str] = None
    grace_period_minutes: Optional[int] = Field(None, ge=0, le=120)
    schedule_data: Optional[ScheduleData] = None


class ClassroomTestScheduleResponse(ClassroomTestScheduleBase):
    id: UUID
    classroom_id: UUID
    created_by_teacher_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TestAvailabilityStatus(BaseModel):
    allowed: bool
    next_window: Optional[datetime] = None
    current_window_end: Optional[datetime] = None
    schedule_active: bool
    message: str
    time_until_next: Optional[str] = None


class OverrideCodeCreate(BaseModel):
    classroom_id: UUID
    reason: str
    expires_in_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week
    max_uses: int = Field(default=1, ge=1, le=100)


class OverrideCodeResponse(BaseModel):
    id: UUID
    classroom_id: UUID
    override_code: str
    reason: str
    expires_at: datetime
    max_uses: int
    current_uses: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ValidateOverrideRequest(BaseModel):
    override_code: str
    student_id: UUID
    test_attempt_id: Optional[UUID] = None


class ValidateOverrideResponse(BaseModel):
    valid: bool
    override_id: Optional[UUID] = None
    message: str


class ScheduleTemplate(BaseModel):
    id: str
    name: str
    description: str
    schedule_data: ScheduleData
    category: str  # e.g., "standard", "block", "flexible"


class StudentScheduleView(BaseModel):
    classroom_id: UUID
    classroom_name: str
    schedule_active: bool
    current_status: TestAvailabilityStatus
    upcoming_windows: List[Dict[str, Any]]
    
    
class ScheduleStatusDashboard(BaseModel):
    testing_currently_allowed: bool
    active_test_sessions: int
    next_window: Optional[Dict[str, Any]]
    schedule_overview: List[ScheduleWindow]
    recent_overrides: List[OverrideCodeResponse]


class ToggleScheduleRequest(BaseModel):
    is_active: bool