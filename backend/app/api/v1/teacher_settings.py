"""
Teacher settings endpoints including bypass code management
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
import bcrypt

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole

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