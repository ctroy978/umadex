"""
Teacher settings endpoints including bypass code management
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
import bcrypt
import secrets
import string

from app.core.database import get_db
from app.utils.supabase_deps import get_current_user_supabase as get_current_user
from app.models.user import User, UserRole
from app.models.tests import TeacherBypassCode

router = APIRouter()


class BypassCodeRequest(BaseModel):
    code: str = Field(..., pattern="^[0-9]{4}$", description="4-digit bypass code")
    
    @validator('code')
    def validate_code(cls, v):
        if len(v) != 4 or not v.isdigit():
            raise ValueError("Bypass code must be exactly 4 digits")
        return v


class BypassCodeStatus(BaseModel):
    has_code: bool
    last_updated: Optional[datetime] = None


class OneTimeBypassCode(BaseModel):
    id: str
    bypass_code: str
    context_type: str
    student_email: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    used: bool


class TeacherSettings(BaseModel):
    email: str
    full_name: str
    bypass_code_status: BypassCodeStatus


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


@router.get("/settings", response_model=TeacherSettings)
async def get_teacher_settings(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get teacher settings including bypass code status"""
    return TeacherSettings(
        email=teacher.email,
        full_name=f"{teacher.first_name} {teacher.last_name}",
        bypass_code_status=BypassCodeStatus(
            has_code=teacher.bypass_code is not None,
            last_updated=teacher.bypass_code_updated_at
        )
    )


@router.put("/settings/bypass-code")
async def set_teacher_bypass_code(
    request: BypassCodeRequest,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Set or update the bypass code for the teacher"""
    # Hash the bypass code
    hashed_code = bcrypt.hashpw(request.code.encode('utf-8'), bcrypt.gensalt())
    
    # Update teacher
    teacher.bypass_code = hashed_code.decode('utf-8')
    teacher.bypass_code_updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Bypass code set successfully"}


@router.delete("/settings/bypass-code")
async def remove_teacher_bypass_code(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Remove the bypass code from the teacher's account"""
    # Remove bypass code
    teacher.bypass_code = None
    teacher.bypass_code_updated_at = None
    
    await db.commit()
    
    return {"message": "Bypass code removed successfully"}


@router.get("/settings/bypass-code/status", response_model=BypassCodeStatus)
async def get_teacher_bypass_code_status(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Check if teacher has a bypass code set (doesn't return the actual code)"""
    return BypassCodeStatus(
        has_code=teacher.bypass_code is not None,
        last_updated=teacher.bypass_code_updated_at
    )


@router.post("/settings/one-time-bypass")
async def generate_one_time_bypass_code(
    context_type: str = "general",
    student_email: Optional[str] = None,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Generate a one-time bypass code for any UMA app scenario"""
    # Generate 12-character alphanumeric code (minimum 10 chars required by frontend)
    alphabet = string.ascii_uppercase + string.digits
    bypass_code = ''.join(secrets.choice(alphabet) for _ in range(12))
    
    # Get student ID if email provided
    student_id = None
    if student_email:
        student_result = await db.execute(
            select(User).where(
                and_(
                    User.email == student_email,
                    User.role == UserRole.STUDENT
                )
            )
        )
        student = student_result.scalar_one_or_none()
        if student:
            student_id = student.id
    
    # Create bypass code record (expires in 1 hour)
    bypass_record = TeacherBypassCode(
        teacher_id=teacher.id,
        context_type=context_type,
        student_id=student_id,
        bypass_code=bypass_code,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(bypass_record)
    await db.commit()
    
    return {
        "bypass_code": bypass_code,
        "expires_at": bypass_record.expires_at.isoformat(),
        "context_type": context_type,
        "student_email": student_email
    }


@router.get("/settings/one-time-bypass/active", response_model=List[OneTimeBypassCode])
async def get_active_one_time_codes(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get all active one-time bypass codes for this teacher"""
    now = datetime.utcnow()
    
    # Query for active codes
    result = await db.execute(
        select(TeacherBypassCode, User)
        .outerjoin(User, User.id == TeacherBypassCode.student_id)
        .where(
            and_(
                TeacherBypassCode.teacher_id == teacher.id,
                TeacherBypassCode.expires_at > now,
                TeacherBypassCode.used_at.is_(None)
            )
        )
        .order_by(TeacherBypassCode.created_at.desc())
    )
    
    codes = []
    for bypass_code, student in result:
        codes.append(OneTimeBypassCode(
            id=str(bypass_code.id),
            bypass_code=bypass_code.bypass_code,
            context_type=bypass_code.context_type,
            student_email=student.email if student else None,
            created_at=bypass_code.created_at,
            expires_at=bypass_code.expires_at,
            used=False
        ))
    
    return codes


@router.delete("/settings/one-time-bypass/{code_id}")
async def revoke_one_time_code(
    code_id: str,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an unused one-time bypass code"""
    # Find the code
    result = await db.execute(
        select(TeacherBypassCode).where(
            and_(
                TeacherBypassCode.id == code_id,
                TeacherBypassCode.teacher_id == teacher.id,
                TeacherBypassCode.used_at.is_(None)
            )
        )
    )
    bypass_code = result.scalar_one_or_none()
    
    if not bypass_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bypass code not found or already used"
        )
    
    # Delete the code
    await db.delete(bypass_code)
    await db.commit()
    
    return {"message": "Bypass code revoked successfully"}