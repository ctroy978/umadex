from datetime import datetime, timedelta, timezone, time
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select
from uuid import UUID
import pytz
import random
import string

from app.models.test_schedule import ClassroomTestSchedule, ClassroomTestOverride, TestOverrideUsage
from app.models.classroom import Classroom
from app.models.user import User
from app.schemas.test_schedule import (
    ClassroomTestScheduleCreate, 
    ClassroomTestScheduleUpdate,
    OverrideCodeCreate,
    ValidateOverrideRequest,
    TestAvailabilityStatus,
    ScheduleWindow,
    DayOfWeek
)
from app.core.config import settings


class TestScheduleService:
    @staticmethod
    async def create_or_update_schedule(
        db: AsyncSession,
        teacher_id: UUID,
        classroom_id: UUID,
        schedule_data: ClassroomTestScheduleCreate
    ) -> ClassroomTestSchedule:
        # Verify teacher owns classroom
        result = await db.execute(
            select(Classroom).where(
                and_(
                    Classroom.id == classroom_id,
                    Classroom.teacher_id == teacher_id
                )
            )
        )
        classroom = result.scalar_one_or_none()
        
        if not classroom:
            raise ValueError("Classroom not found or access denied")
        
        # Check if schedule already exists
        result = await db.execute(
            select(ClassroomTestSchedule).where(
                ClassroomTestSchedule.classroom_id == classroom_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing schedule
            for key, value in schedule_data.dict(exclude_unset=True).items():
                if key != 'classroom_id':
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new schedule
            db_schedule = ClassroomTestSchedule(
                classroom_id=classroom_id,
                created_by_teacher_id=teacher_id,
                **schedule_data.dict(exclude={'classroom_id'})
            )
            db.add(db_schedule)
            await db.commit()
            await db.refresh(db_schedule)
            return db_schedule
    
    @staticmethod
    async def get_schedule(db: AsyncSession, classroom_id: UUID) -> Optional[ClassroomTestSchedule]:
        from sqlalchemy.orm import joinedload
        result = await db.execute(
            select(ClassroomTestSchedule)
            .options(joinedload(ClassroomTestSchedule.classroom))
            .where(ClassroomTestSchedule.classroom_id == classroom_id)
        )
        return result.unique().scalar_one_or_none()
    
    @staticmethod
    async def check_test_availability(
        db: AsyncSession,
        classroom_id: UUID,
        check_time: Optional[datetime] = None
    ) -> TestAvailabilityStatus:
        if check_time is None:
            check_time = datetime.now(timezone.utc)
        
        schedule = await TestScheduleService.get_schedule(db, classroom_id)
        
        # If no schedule exists or it's inactive, testing is always allowed
        if not schedule or not schedule.is_active:
            return TestAvailabilityStatus(
                allowed=True,
                schedule_active=False,
                message="Testing is available 24/7 for this classroom"
            )
        
        # Get timezone and convert check time
        tz = pytz.timezone(schedule.timezone)
        local_time = check_time.astimezone(tz)
        current_time = local_time.time()
        current_day = local_time.strftime('%A').lower()
        
        # Check if current time falls within any window
        windows = schedule.schedule_data.get('windows', [])
        current_window_end = None
        
        for window in windows:
            if current_day in window['days']:
                start_time = time.fromisoformat(window['start_time'])
                end_time = time.fromisoformat(window['end_time'])
                
                if start_time <= current_time <= end_time:
                    # Currently in a testing window
                    current_window_end = local_time.replace(
                        hour=end_time.hour,
                        minute=end_time.minute,
                        second=0,
                        microsecond=0
                    )
                    
                    return TestAvailabilityStatus(
                        allowed=True,
                        current_window_end=current_window_end,
                        schedule_active=True,
                        message=f"Testing available until {end_time.strftime('%I:%M %p')}"
                    )
        
        # Not in a testing window, find next available window
        next_window = TestScheduleService._find_next_window(schedule, local_time)
        
        if next_window:
            time_until = next_window - check_time
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            
            time_str = f"{hours} hours" if hours > 0 else ""
            if minutes > 0:
                time_str += f" {minutes} minutes" if time_str else f"{minutes} minutes"
            
            return TestAvailabilityStatus(
                allowed=False,
                next_window=next_window,
                schedule_active=True,
                message=f"Testing will be available in {time_str}",
                time_until_next=time_str
            )
        
        return TestAvailabilityStatus(
            allowed=False,
            schedule_active=True,
            message="No upcoming testing windows scheduled"
        )
    
    @staticmethod
    def _find_next_window(schedule: ClassroomTestSchedule, from_time: datetime) -> Optional[datetime]:
        windows = schedule.schedule_data.get('windows', [])
        tz = pytz.timezone(schedule.timezone)
        
        # Look ahead up to 7 days
        for days_ahead in range(7):
            check_date = from_time + timedelta(days=days_ahead)
            check_day = check_date.strftime('%A').lower()
            
            for window in sorted(windows, key=lambda w: w['start_time']):
                if check_day in window['days']:
                    start_time = time.fromisoformat(window['start_time'])
                    window_datetime = check_date.replace(
                        hour=start_time.hour,
                        minute=start_time.minute,
                        second=0,
                        microsecond=0
                    )
                    
                    # Only return if the window is in the future
                    if window_datetime > from_time:
                        return window_datetime.astimezone(timezone.utc)
        
        return None
    
    @staticmethod
    async def generate_override_code(
        db: AsyncSession,
        teacher_id: UUID,
        override_data: OverrideCodeCreate
    ) -> ClassroomTestOverride:
        # Verify teacher owns classroom
        result = await db.execute(
            select(Classroom).where(
                and_(
                    Classroom.id == override_data.classroom_id,
                    Classroom.teacher_id == teacher_id
                )
            )
        )
        classroom = result.scalar_one_or_none()
        
        if not classroom:
            raise ValueError("Classroom not found or access denied")
        
        # Generate unique code
        code = await TestScheduleService._generate_unique_code(db)
        
        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(hours=override_data.expires_in_hours)
        
        # Create override
        db_override = ClassroomTestOverride(
            classroom_id=override_data.classroom_id,
            teacher_id=teacher_id,
            override_code=code,
            reason=override_data.reason,
            expires_at=expires_at,
            max_uses=override_data.max_uses
        )
        
        db.add(db_override)
        await db.commit()
        await db.refresh(db_override)
        
        return db_override
    
    @staticmethod
    async def _generate_unique_code(db: AsyncSession) -> str:
        while True:
            # Generate 8-character alphanumeric code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            
            # Check if code already exists
            result = await db.execute(
                select(ClassroomTestOverride).where(
                    ClassroomTestOverride.override_code == code
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                return code
    
    @staticmethod
    async def validate_and_use_override(
        db: AsyncSession,
        validation_data: ValidateOverrideRequest
    ) -> Dict[str, Any]:
        # Find the override code (case-insensitive comparison)
        result = await db.execute(
            select(ClassroomTestOverride).where(
                func.upper(ClassroomTestOverride.override_code) == validation_data.override_code.upper()
            )
        )
        override = result.scalar_one_or_none()
        
        if not override:
            return {
                "valid": False,
                "message": "Invalid override code"
            }
        
        # Check if expired
        if override.expires_at < datetime.now(timezone.utc):
            return {
                "valid": False,
                "message": "Override code has expired"
            }
        
        # Check if max uses reached
        if override.current_uses >= override.max_uses:
            return {
                "valid": False,
                "message": "Override code has reached maximum uses"
            }
        
        # Check if student is in the classroom
        from app.models.classroom import ClassroomStudent
        result = await db.execute(
            select(ClassroomStudent).where(
                and_(
                    ClassroomStudent.classroom_id == override.classroom_id,
                    ClassroomStudent.student_id == validation_data.student_id,
                    ClassroomStudent.removed_at.is_(None)
                )
            )
        )
        student_enrollment = result.scalar_one_or_none()
        
        if not student_enrollment:
            return {
                "valid": False,
                "message": "Student not enrolled in this classroom"
            }
        
        # Record usage if test_attempt_id provided
        if validation_data.test_attempt_id:
            usage = TestOverrideUsage(
                override_id=override.id,
                student_id=validation_data.student_id,
                test_attempt_id=validation_data.test_attempt_id
            )
            db.add(usage)
            
            # Increment usage count
            override.current_uses += 1
            override.used_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return {
            "valid": True,
            "override_id": override.id,
            "message": "Override code validated successfully"
        }
    
    @staticmethod
    async def get_active_overrides(
        db: AsyncSession,
        teacher_id: UUID,
        classroom_id: Optional[UUID] = None
    ) -> List[ClassroomTestOverride]:
        query = select(ClassroomTestOverride).where(
            and_(
                ClassroomTestOverride.teacher_id == teacher_id,
                ClassroomTestOverride.expires_at > datetime.now(timezone.utc)
            )
        )
        
        if classroom_id:
            query = query.where(ClassroomTestOverride.classroom_id == classroom_id)
        
        query = query.order_by(ClassroomTestOverride.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def delete_schedule(db: AsyncSession, teacher_id: UUID, classroom_id: UUID) -> bool:
        # Verify teacher owns classroom
        result = await db.execute(
            select(Classroom).where(
                and_(
                    Classroom.id == classroom_id,
                    Classroom.teacher_id == teacher_id
                )
            )
        )
        classroom = result.scalar_one_or_none()
        
        if not classroom:
            return False
        
        # Delete schedule
        result = await db.execute(
            select(ClassroomTestSchedule).where(
                ClassroomTestSchedule.classroom_id == classroom_id
            )
        )
        schedule = result.scalar_one_or_none()
        
        if schedule:
            await db.delete(schedule)
            await db.commit()
            return True
        return False
    
    @staticmethod
    def get_schedule_templates() -> List[Dict[str, Any]]:
        """Return predefined schedule templates"""
        return [
            {
                "id": "standard_school_day",
                "name": "Standard School Day",
                "description": "Monday-Friday, 8:00 AM - 3:00 PM",
                "category": "standard",
                "schedule_data": {
                    "windows": [
                        {
                            "id": "school_hours",
                            "name": "School Hours",
                            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                            "start_time": "08:00",
                            "end_time": "15:00",
                            "color": "#3B82F6"
                        }
                    ],
                    "settings": {
                        "pre_test_buffer_minutes": 5,
                        "allow_weekend_testing": False,
                        "emergency_override_enabled": True
                    }
                }
            },
            {
                "id": "block_schedule",
                "name": "Block Schedule",
                "description": "Alternating A/B day blocks",
                "category": "block",
                "schedule_data": {
                    "windows": [
                        {
                            "id": "a_day_morning",
                            "name": "A Day Morning Block",
                            "days": ["monday", "wednesday", "friday"],
                            "start_time": "08:00",
                            "end_time": "10:30",
                            "color": "#10B981"
                        },
                        {
                            "id": "a_day_afternoon",
                            "name": "A Day Afternoon Block",
                            "days": ["monday", "wednesday", "friday"],
                            "start_time": "13:00",
                            "end_time": "15:30",
                            "color": "#10B981"
                        },
                        {
                            "id": "b_day_morning",
                            "name": "B Day Morning Block",
                            "days": ["tuesday", "thursday"],
                            "start_time": "08:00",
                            "end_time": "11:00",
                            "color": "#F59E0B"
                        },
                        {
                            "id": "b_day_afternoon",
                            "name": "B Day Afternoon Block",
                            "days": ["tuesday", "thursday"],
                            "start_time": "12:30",
                            "end_time": "15:30",
                            "color": "#F59E0B"
                        }
                    ],
                    "settings": {
                        "pre_test_buffer_minutes": 10,
                        "allow_weekend_testing": False,
                        "emergency_override_enabled": True
                    }
                }
            },
            {
                "id": "after_school",
                "name": "After School Only",
                "description": "3:30 PM - 6:00 PM for working students",
                "category": "flexible",
                "schedule_data": {
                    "windows": [
                        {
                            "id": "after_school",
                            "name": "After School",
                            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                            "start_time": "15:30",
                            "end_time": "18:00",
                            "color": "#8B5CF6"
                        }
                    ],
                    "settings": {
                        "pre_test_buffer_minutes": 5,
                        "allow_weekend_testing": True,
                        "emergency_override_enabled": True
                    }
                }
            },
            {
                "id": "exam_week",
                "name": "Exam Week",
                "description": "Extended testing windows for final exams",
                "category": "exam",
                "schedule_data": {
                    "windows": [
                        {
                            "id": "morning_exam",
                            "name": "Morning Exam Period",
                            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                            "start_time": "08:00",
                            "end_time": "12:00",
                            "color": "#DC2626"
                        },
                        {
                            "id": "afternoon_exam",
                            "name": "Afternoon Exam Period",
                            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                            "start_time": "13:00",
                            "end_time": "17:00",
                            "color": "#DC2626"
                        }
                    ],
                    "settings": {
                        "pre_test_buffer_minutes": 15,
                        "allow_weekend_testing": False,
                        "emergency_override_enabled": True
                    }
                }
            }
        ]