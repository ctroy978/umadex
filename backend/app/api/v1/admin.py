from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from app.core.database import get_db
from app.utils.deps import require_admin
from app.models.user import User
from app.models.classroom import Classroom, ClassroomStudent
from app.models.reading import ReadingAssignment
from app.models.classroom import StudentAssignment
from app.models.tests import StudentTestAttempt
from app.schemas.admin import (
    AdminUserResponse,
    AdminUserListResponse,
    UserPromotionRequest,
    UserDeletionRequest,
    UserRestoreRequest,
    AdminDashboardResponse,
    AdminAuditLogResponse,
    UserImpactAnalysis,
    UserSearchFilters
)
from app.services.auth import log_admin_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard overview with statistics."""
    # User statistics
    total_users = await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None)))
    total_students = await db.scalar(
        select(func.count(User.id))
        .where(and_(User.role == "student", User.deleted_at.is_(None)))
    )
    total_teachers = await db.scalar(
        select(func.count(User.id))
        .where(and_(User.role == "teacher", User.deleted_at.is_(None)))
    )
    total_admins = await db.scalar(
        select(func.count(User.id))
        .where(and_(User.is_admin == True, User.deleted_at.is_(None)))
    )
    deleted_users = await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_not(None)))
    
    # Recent activity
    result = await db.execute(
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
        .limit(10)
    )
    recent_registrations = result.scalars().all()
    
    # For now, skip recent admin actions as the table may not exist yet
    recent_admin_actions = []
    
    return AdminDashboardResponse(
        total_users=total_users or 0,
        total_students=total_students or 0,
        total_teachers=total_teachers or 0,
        total_admins=total_admins or 0,
        deleted_users=deleted_users or 0,
        recent_registrations=recent_registrations[:5],  # Limit to 5
        recent_admin_actions=recent_admin_actions
    )

@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    include_deleted: bool = False,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users with pagination and filtering."""
    query = select(User)
    
    # Apply filters
    filters = []
    if not include_deleted:
        filters.append(User.deleted_at.is_(None))
    
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                User.email.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.username.ilike(search_term)
            )
        )
    
    if role:
        if role == "admin":
            filters.append(User.is_admin == True)
        else:
            filters.append(User.role == role)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    total_count = db.scalar(select(func.count()).select_from(query.subquery()))
    
    # Apply pagination
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    users = db.scalars(query).all()
    
    # Get additional stats for each user
    user_responses = []
    for user in users:
        # Get classroom count for teachers
        classroom_count = 0
        if user.role == "teacher":
            classroom_count = db.scalar(
                select(func.count(Classroom.id))
                .where(Classroom.teacher_id == user.id)
            )
        
        # Get enrolled classrooms for students
        enrolled_classrooms = 0
        if user.role == "student":
            enrolled_classrooms = db.scalar(
                select(func.count(ClassroomStudent.classroom_id))
                .where(ClassroomStudent.student_id == user.id)
            )
        
        user_responses.append(AdminUserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            role=user.role,
            is_admin=user.is_admin,
            created_at=user.created_at,
            deleted_at=user.deleted_at,
            deletion_reason=user.deletion_reason,
            classroom_count=classroom_count,
            enrolled_classrooms=enrolled_classrooms
        ))
    
    return AdminUserListResponse(
        users=user_responses,
        total=total_count,
        page=page,
        per_page=per_page,
        pages=(total_count + per_page - 1) // per_page
    )

@router.get("/users/{user_id}/impact", response_model=UserImpactAnalysis)
async def analyze_user_deletion_impact(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Analyze the impact of deleting a user."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    impact = UserImpactAnalysis(
        user_id=user.id,
        user_email=user.email,
        user_role=user.role,
        is_admin=user.is_admin
    )
    
    if user.role == "teacher":
        # Count affected classrooms
        impact.affected_classrooms = db.scalar(
            select(func.count(Classroom.id))
            .where(Classroom.teacher_id == user.id)
        )
        
        # Count affected assignments
        impact.affected_assignments = db.scalar(
            select(func.count(ReadingAssignment.id))
            .where(ReadingAssignment.teacher_id == user.id)
        )
        
        # Count affected students
        impact.affected_students = db.scalar(
            select(func.count(func.distinct(ClassroomStudent.student_id)))
            .select_from(ClassroomStudent)
            .join(Classroom)
            .where(Classroom.teacher_id == user.id)
        )
        
        # Get sample of affected classrooms
        sample_classrooms = db.scalars(
            select(Classroom)
            .where(Classroom.teacher_id == user.id)
            .limit(5)
        ).all()
        
        impact.classroom_names = [c.name for c in sample_classrooms]
        
    elif user.role == "student":
        # Count enrolled classrooms
        impact.enrolled_classrooms = db.scalar(
            select(func.count(ClassroomStudent.classroom_id))
            .where(ClassroomStudent.student_id == user.id)
        )
        
        # Count assignments
        impact.total_assignments = db.scalar(
            select(func.count(StudentAssignment.id))
            .where(StudentAssignment.student_id == user.id)
        )
        
        # Count test attempts
        impact.test_attempts = db.scalar(
            select(func.count(StudentTestAttempt.id))
            .where(StudentTestAttempt.student_id == user.id)
        )
    
    return impact

@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: str,
    request: UserPromotionRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Promote a user's role (student to teacher, or grant admin access)."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.deleted_at:
        raise HTTPException(status_code=400, detail="Cannot promote deleted user")
    
    # Validate promotion
    old_role = user.role
    old_is_admin = user.is_admin
    
    # Apply promotion
    if request.new_role:
        user.role = request.new_role
    if request.make_admin is not None:
        user.is_admin = request.make_admin
    
    user.updated_at = datetime.utcnow()
    
    # TODO: Log the action
    # log_admin_action(
        db=db,
        admin_id=current_admin.id,
        action_type="user_promotion",
        target_id=user.id,
        target_type="user",
        action_data={
            "from_role": old_role,
            "to_role": user.role,
            "from_admin": old_is_admin,
            "to_admin": user.is_admin,
            "reason": request.reason
        }
    )
    
    db.commit()
    
    return {"message": "User promoted successfully", "user_id": user.id}

@router.delete("/users/{user_id}/soft")
async def soft_delete_user(
    user_id: str,
    request: UserDeletionRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a user (archive with ability to restore)."""
    if current_admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.deleted_at:
        raise HTTPException(status_code=400, detail="User already deleted")
    
    # Perform soft delete
    user.deleted_at = datetime.utcnow()
    user.deleted_by = current_admin.id
    user.deletion_reason = request.reason
    
    # TODO: Log the action
    # log_admin_action(
        db=db,
        admin_id=current_admin.id,
        action_type="user_soft_delete",
        target_id=user.id,
        target_type="user",
        action_data={
            "reason": request.reason,
            "notify_teachers": request.notify_affected_teachers
        }
    )
    
    db.commit()
    
    return {"message": "User soft deleted successfully", "user_id": user.id}

@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted user."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.deleted_at:
        raise HTTPException(status_code=400, detail="User is not deleted")
    
    # Restore user
    user.deleted_at = None
    user.deleted_by = None
    user.deletion_reason = None
    
    # TODO: Log the action
    # log_admin_action(
        db=db,
        admin_id=current_admin.id,
        action_type="user_restore",
        target_id=user.id,
        target_type="user",
        action_data={}
    )
    
    db.commit()
    
    return {"message": "User restored successfully", "user_id": user.id}

@router.delete("/users/{user_id}/hard")
async def hard_delete_user(
    user_id: str,
    request: UserDeletionRequest,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Permanently delete a user and all associated data.
    
    WARNING: This action cannot be undone and will delete all user data.
    """
    if current_admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    if not request.confirmation_phrase:
        raise HTTPException(
            status_code=400,
            detail="Confirmation phrase required for hard delete"
        )
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    expected_phrase = f"PERMANENTLY DELETE {user.first_name} {user.last_name}"
    if request.confirmation_phrase != expected_phrase:
        raise HTTPException(
            status_code=400,
            detail=f"Confirmation phrase must be: '{expected_phrase}'"
        )
    
    # Teachers cannot be hard deleted
    if user.role == "teacher":
        raise HTTPException(
            status_code=400,
            detail="Teachers cannot be hard deleted due to content ownership. Use soft delete instead."
        )
    
    # Log before deletion
    log_admin_action(
        db=db,
        admin_id=current_admin.id,
        action_type="user_hard_delete",
        target_id=user.id,
        target_type="user",
        action_data={
            "user_email": user.email,
            "user_name": f"{user.first_name} {user.last_name}",
            "reason": request.reason
        }
    )
    
    # Delete in correct order (handled by CASCADE in most cases)
    db.delete(user)
    db.commit()
    
    return {"message": "User permanently deleted", "user_id": user_id}

@router.get("/audit-log", response_model=List[AdminAuditLogResponse])
async def get_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    action_type: Optional[str] = None,
    admin_id: Optional[str] = None,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get audit log of admin actions."""
    # Note: This would query the admin_actions table
    # For now, returning empty list as the table doesn't exist yet
    return []