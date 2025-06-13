from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, Any, Optional

from app.core.database import get_db
from app.utils.deps import require_admin
from app.models.user import User

router = APIRouter(tags=["admin"])

@router.get("/dashboard")
async def get_admin_dashboard(
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
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
        .limit(5)
    )
    recent_registrations = result.scalars().all()
    
    return {
        "total_users": total_users or 0,
        "total_students": total_students or 0,
        "total_teachers": total_teachers or 0,
        "total_admins": total_admins or 0,
        "deleted_users": deleted_users or 0,
        "recent_registrations": [
            {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "role": user.role,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat(),
                "deleted_at": None,
                "deletion_reason": None,
                "classroom_count": 0,
                "enrolled_classrooms": 0
            }
            for user in recent_registrations
        ],
        "recent_admin_actions": []
    }

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    include_deleted: bool = False,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
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
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await db.scalar(count_query)
    
    # Apply pagination
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Convert users to response format
    user_responses = []
    for user in users:
        user_responses.append({
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "role": user.role,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
            "deletion_reason": user.deletion_reason,
            "classroom_count": 0,  # Simplified for now
            "enrolled_classrooms": 0  # Simplified for now
        })
    
    return {
        "users": user_responses,
        "total": total_count or 0,
        "page": page,
        "per_page": per_page,
        "pages": (total_count + per_page - 1) // per_page if total_count else 0
    }

@router.get("/users/{user_id}/impact")
async def get_user_impact(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Analyze the impact of deleting a user."""
    from fastapi import HTTPException
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    impact = {
        "user_id": str(user.id),
        "user_email": user.email,
        "user_role": user.role,
        "is_admin": user.is_admin,
        "affected_classrooms": 0,
        "affected_assignments": 0,
        "affected_students": 0,
        "enrolled_classrooms": 0,
        "total_assignments": 0,
        "test_attempts": 0,
        "classroom_names": []
    }
    
    # Import models for queries
    try:
        from app.models.classroom import Classroom, ClassroomStudent
        from app.models.reading import ReadingAssignment
        
        if user.role == "teacher":
            # Count classrooms owned by this teacher
            affected_classrooms = await db.scalar(
                select(func.count(Classroom.id)).where(Classroom.teacher_id == user.id)
            )
            impact["affected_classrooms"] = affected_classrooms or 0
            
            # Count assignments created by this teacher
            affected_assignments = await db.scalar(
                select(func.count(ReadingAssignment.id)).where(ReadingAssignment.teacher_id == user.id)
            )
            impact["affected_assignments"] = affected_assignments or 0
            
            # Count students in their classrooms
            affected_students = await db.scalar(
                select(func.count(func.distinct(ClassroomStudent.student_id)))
                .select_from(ClassroomStudent)
                .join(Classroom)
                .where(Classroom.teacher_id == user.id)
            )
            impact["affected_students"] = affected_students or 0
            
            # Get sample classroom names
            classroom_result = await db.execute(
                select(Classroom.name)
                .where(Classroom.teacher_id == user.id)
                .limit(5)
            )
            classroom_names = [row[0] for row in classroom_result.fetchall()]
            impact["classroom_names"] = classroom_names
            
        elif user.role == "student":
            # Count classrooms student is enrolled in
            enrolled_classrooms = await db.scalar(
                select(func.count(ClassroomStudent.classroom_id))
                .where(ClassroomStudent.student_id == user.id)
            )
            impact["enrolled_classrooms"] = enrolled_classrooms or 0
            
            # Try to count student assignments (may not exist in simplified version)
            try:
                from app.models.classroom import StudentAssignment
                total_assignments = await db.scalar(
                    select(func.count(StudentAssignment.id))
                    .where(StudentAssignment.student_id == user.id)
                )
                impact["total_assignments"] = total_assignments or 0
            except ImportError:
                impact["total_assignments"] = 0
            
            # Try to count test attempts (may not exist)
            try:
                from app.models.tests import StudentTestAttempt
                test_attempts = await db.scalar(
                    select(func.count(StudentTestAttempt.id))
                    .where(StudentTestAttempt.student_id == user.id)
                )
                impact["test_attempts"] = test_attempts or 0
            except ImportError:
                impact["test_attempts"] = 0
                
    except ImportError as e:
        # If models don't exist, keep default values
        pass
    
    return impact

@router.delete("/users/{user_id}/soft")
async def soft_delete_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Soft delete a user (archive with ability to restore)."""
    from fastapi import HTTPException
    from datetime import datetime
    
    if current_admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.deleted_at:
        raise HTTPException(status_code=400, detail="User already deleted")
    
    # Perform soft delete
    user.deleted_at = datetime.utcnow()
    user.deleted_by = current_admin.id
    user.deletion_reason = "other"  # Simplified for now
    
    await db.commit()
    
    return {"message": "User soft deleted successfully", "user_id": user_id}

@router.post("/users/{user_id}/restore")
async def restore_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Restore a soft-deleted user."""
    from fastapi import HTTPException
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.deleted_at:
        raise HTTPException(status_code=400, detail="User is not deleted")
    
    # Restore user
    user.deleted_at = None
    user.deleted_by = None
    user.deletion_reason = None
    
    await db.commit()
    
    return {"message": "User restored successfully", "user_id": user_id}

@router.delete("/users/{user_id}/hard")
async def hard_delete_user(
    user_id: str,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Permanently delete a user and all associated data.
    
    WARNING: This action cannot be undone. All user data and related records
    will be permanently removed via CASCADE DELETE constraints.
    """
    from fastapi import HTTPException
    from sqlalchemy import delete
    
    try:
        if current_admin.id == user_id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Only students can be hard deleted
        if user.role == "teacher":
            raise HTTPException(
                status_code=400,
                detail="Teachers cannot be hard deleted due to content ownership. Use soft delete instead."
            )
        
        if user.is_admin:
            raise HTTPException(
                status_code=400,
                detail="Administrators cannot be hard deleted due to audit trail requirements. Use soft delete instead."
            )
        
        # For students only: Permanent deletion with CASCADE DELETE
        # This will automatically remove all related data:
        # - classroom_students (enrollments)
        # - student_assignments (assignment progress)
        # - student_test_attempts (test history)
        # - umaread_student_responses (reading responses)
        # - umaread_chunk_progress (reading progress)
        # - umaread_assignment_progress (assignment progress)
        # - student_events (activity logs)
        # - otp_requests (authentication requests)
        
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()
        
        return {
            "message": "User permanently deleted",
            "user_id": user_id,
            "warning": "All user data has been permanently removed and cannot be recovered"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: str,
    request: Dict[str, Any],
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Promote a user's role (student to teacher, or grant admin access)."""
    from fastapi import HTTPException
    from datetime import datetime
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.deleted_at:
        raise HTTPException(status_code=400, detail="Cannot promote deleted user")
    
    # Apply promotion changes
    old_role = user.role
    old_is_admin = user.is_admin
    
    if "new_role" in request and request["new_role"]:
        user.role = request["new_role"]
    
    if "make_admin" in request and request["make_admin"] is not None:
        user.is_admin = request["make_admin"]
    
    user.updated_at = datetime.utcnow()
    
    # Commit changes
    await db.commit()
    
    return {
        "message": "User promoted successfully", 
        "user_id": user_id,
        "old_role": old_role,
        "new_role": user.role,
        "old_admin": old_is_admin,
        "new_admin": user.is_admin
    }

@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    action_type: Optional[str] = None,
    admin_id: Optional[str] = None,
    current_admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get audit log of admin actions."""
    # For now, return empty audit log since the admin_actions table may not be fully implemented
    # In a full implementation, this would query the admin_actions table
    return {
        "actions": [],
        "total": 0,
        "page": page,
        "per_page": per_page,
        "pages": 0
    }