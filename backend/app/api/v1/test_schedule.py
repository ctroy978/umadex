from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.utils.supabase_deps import get_current_user_supabase as get_current_user
from app.models.user import User, UserRole
from app.models.test_schedule import ClassroomTestSchedule, ClassroomTestOverride
from app.models.classroom import Classroom, ClassroomStudent
from app.schemas.test_schedule import (
    ClassroomTestScheduleCreate,
    ClassroomTestScheduleUpdate,
    ClassroomTestScheduleResponse,
    OverrideCodeCreate,
    OverrideCodeResponse,
    ValidateOverrideRequest,
    ValidateOverrideResponse,
    TestAvailabilityStatus,
    StudentScheduleView,
    ScheduleStatusDashboard,
    ScheduleTemplate,
    ToggleScheduleRequest
)
from app.services.test_schedule import TestScheduleService

router = APIRouter(prefix="/test-schedule", tags=["test-schedule"])


@router.get("/templates", response_model=List[ScheduleTemplate])
async def get_schedule_templates(
    current_user: User = Depends(get_current_user)
):
    """Get available schedule templates"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access schedule templates"
        )
    
    templates = TestScheduleService.get_schedule_templates()
    return templates


@router.get("/classrooms/{classroom_id}", response_model=Optional[ClassroomTestScheduleResponse])
async def get_classroom_schedule(
    classroom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get schedule for a specific classroom"""
    # Check if user has access to this classroom
    if current_user.role == UserRole.TEACHER:
        # Check if teacher owns this classroom
        result = await db.execute(
            select(Classroom).where(
                and_(
                    Classroom.id == classroom_id,
                    Classroom.teacher_id == current_user.id,
                    Classroom.deleted_at.is_(None)
                )
            )
        )
        classroom = result.scalar_one_or_none()
        if not classroom:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this classroom"
            )
    else:
        # Check if student is enrolled in this classroom
        result = await db.execute(
            select(ClassroomStudent).where(
                and_(
                    ClassroomStudent.classroom_id == classroom_id,
                    ClassroomStudent.student_id == current_user.id,
                    ClassroomStudent.removed_at.is_(None)
                )
            )
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this classroom"
            )
    
    schedule = await TestScheduleService.get_schedule(db, classroom_id)
    return schedule


@router.post("/classrooms/{classroom_id}", response_model=ClassroomTestScheduleResponse)
async def create_or_update_schedule(
    classroom_id: UUID,
    schedule_data: ClassroomTestScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create or update schedule for a classroom"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can manage schedules"
        )
    
    try:
        schedule = await TestScheduleService.create_or_update_schedule(
            db=db,
            teacher_id=current_user.id,
            classroom_id=classroom_id,
            schedule_data=schedule_data
        )
        return schedule
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/classrooms/{classroom_id}/toggle")
async def toggle_schedule(
    classroom_id: UUID,
    request: ToggleScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enable or disable schedule for a classroom"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can toggle schedules"
        )
    
    schedule = await TestScheduleService.get_schedule(db, classroom_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    
    # Verify teacher owns classroom
    if schedule.classroom.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    schedule.is_active = request.is_active
    await db.commit()
    
    return {"message": f"Schedule {'enabled' if request.is_active else 'disabled'} successfully"}


@router.delete("/classrooms/{classroom_id}")
async def delete_schedule(
    classroom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete schedule for a classroom (returns to 24/7 testing)"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can delete schedules"
        )
    
    deleted = await TestScheduleService.delete_schedule(db, current_user.id, classroom_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found or access denied"
        )
    
    return {"message": "Schedule deleted successfully"}


@router.get("/classrooms/{classroom_id}/availability", response_model=TestAvailabilityStatus)
async def check_test_availability(
    classroom_id: UUID,
    check_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if testing is currently available for a classroom"""
    # Students can check availability for their enrolled classrooms
    if current_user.role == UserRole.STUDENT:
        result = await db.execute(
            select(ClassroomStudent).where(
                and_(
                    ClassroomStudent.classroom_id == classroom_id,
                    ClassroomStudent.student_id == current_user.id,
                    ClassroomStudent.removed_at.is_(None)
                )
            )
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enrolled in this classroom"
            )
    
    availability = await TestScheduleService.check_test_availability(db, classroom_id, check_time)
    return availability


@router.get("/classrooms/{classroom_id}/next-window")
async def get_next_testing_window(
    classroom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the next available testing window for a classroom"""
    availability = await TestScheduleService.check_test_availability(db, classroom_id)
    
    if availability.allowed:
        return {
            "message": "Testing is currently available",
            "current_window_end": availability.current_window_end
        }
    
    return {
        "next_window": availability.next_window,
        "time_until_next": availability.time_until_next,
        "message": availability.message
    }


@router.post("/classrooms/{classroom_id}/validate-access")
async def validate_test_access(
    classroom_id: UUID,
    override_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate if a student can start a test now"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can validate test access"
        )
    
    # Check normal availability first
    availability = await TestScheduleService.check_test_availability(db, classroom_id)
    
    if availability.allowed:
        return {
            "allowed": True,
            "message": "Testing is available",
            "requires_override": False
        }
    
    # If not available and override code provided, validate it
    if override_code:
        validation = await TestScheduleService.validate_and_use_override(
            db,
            ValidateOverrideRequest(
                override_code=override_code,
                student_id=current_user.id
            )
        )
        
        if validation["valid"]:
            return {
                "allowed": True,
                "message": "Access granted with override code",
                "requires_override": True,
                "override_id": validation.get("override_id")
            }
    
    return {
        "allowed": False,
        "message": availability.message,
        "next_window": availability.next_window,
        "requires_override": True
    }


@router.get("/classrooms/{classroom_id}/status", response_model=ScheduleStatusDashboard)
async def get_schedule_status(
    classroom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive schedule status for teacher dashboard"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view schedule status"
        )
    
    # First verify teacher owns the classroom
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == current_user.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this classroom"
        )
    
    schedule = await TestScheduleService.get_schedule(db, classroom_id)
    
    # Get current availability
    availability = await TestScheduleService.check_test_availability(db, classroom_id)
    
    # Get active test sessions (would need to implement this query)
    # For now, return 0
    active_sessions = 0
    
    # Get recent overrides
    recent_overrides = await TestScheduleService.get_active_overrides(db, current_user.id, classroom_id)
    
    # Return appropriate response based on whether schedule exists
    if schedule:
        return ScheduleStatusDashboard(
            testing_currently_allowed=availability.allowed,
            active_test_sessions=active_sessions,
            next_window={"start": availability.next_window} if availability.next_window else None,
            schedule_overview=schedule.schedule_data.get("windows", []),
            recent_overrides=recent_overrides
        )
    else:
        # No schedule exists - testing is available 24/7
        return ScheduleStatusDashboard(
            testing_currently_allowed=True,
            active_test_sessions=active_sessions,
            next_window=None,
            schedule_overview=[],
            recent_overrides=recent_overrides
        )


@router.post("/overrides/generate", response_model=OverrideCodeResponse)
async def generate_override_code(
    override_data: OverrideCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate an emergency override code"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can generate override codes"
        )
    
    try:
        override = await TestScheduleService.generate_override_code(
            db=db,
            teacher_id=current_user.id,
            override_data=override_data
        )
        return override
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/overrides/validate", response_model=ValidateOverrideResponse)
async def validate_override_code(
    validation_data: ValidateOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate and optionally use an override code"""
    result = await TestScheduleService.validate_and_use_override(db, validation_data)
    return ValidateOverrideResponse(**result)


@router.get("/overrides/active", response_model=List[OverrideCodeResponse])
async def get_active_overrides(
    classroom_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active override codes for teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view override codes"
        )
    
    overrides = await TestScheduleService.get_active_overrides(db, current_user.id, classroom_id)
    return overrides


@router.delete("/overrides/{override_id}")
async def revoke_override_code(
    override_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke an unused override code"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can revoke override codes"
        )
    
    result = await db.execute(
        select(ClassroomTestOverride).where(
            and_(
                ClassroomTestOverride.id == override_id,
                ClassroomTestOverride.teacher_id == current_user.id
            )
        )
    )
    override = result.scalar_one_or_none()
    
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Override code not found"
        )
    
    if override.current_uses > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke a code that has been used"
        )
    
    await db.delete(override)
    await db.commit()
    
    return {"message": "Override code revoked successfully"}


@router.get("/student/availability", response_model=List[StudentScheduleView])
async def get_student_test_availability(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get test availability across all enrolled classrooms for a student"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is for students only"
        )
    
    # Get all classrooms the student is enrolled in
    result = await db.execute(
        select(Classroom).join(
            ClassroomStudent, 
            and_(
                ClassroomStudent.classroom_id == Classroom.id,
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.removed_at.is_(None)
            )
        ).where(
            Classroom.deleted_at.is_(None)
        )
    )
    classrooms = result.scalars().all()
    
    schedule_views = []
    for classroom in classrooms:
        availability = TestScheduleService.check_test_availability(db, classroom.id)
        schedule = await TestScheduleService.get_schedule(db, classroom.id)
        
        view = StudentScheduleView(
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            schedule_active=schedule.is_active if schedule else False,
            current_status=availability,
            upcoming_windows=[]  # Would need to implement logic to get upcoming windows
        )
        schedule_views.append(view)
    
    return schedule_views