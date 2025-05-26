from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.schemas.admin import EmailWhitelistCreate, EmailWhitelistResponse, PromoteToTeacherRequest
from app.schemas.auth import UserResponse
from app.models import User, EmailWhitelist, UserRole
from app.services.user import UserService
from app.utils.deps import require_admin
from app.config.ai_models import get_all_models

router = APIRouter()

@router.post("/promote-to-teacher", response_model=UserResponse)
async def promote_to_teacher(
    request: PromoteToTeacherRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Promote a student to teacher role (admin only)"""
    user = await UserService.get_user_by_id(db, request.user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.role == UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a teacher"
        )
    
    # Update user role
    user.role = UserRole.TEACHER
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)

@router.post("/whitelist", response_model=EmailWhitelistResponse)
async def add_to_whitelist(
    request: EmailWhitelistCreate,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Add email or domain to whitelist (admin only)"""
    # Check if already exists
    result = await db.execute(
        select(EmailWhitelist).where(
            EmailWhitelist.email_pattern == request.email_pattern
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email pattern already whitelisted"
        )
    
    # Validate pattern
    if request.is_domain and '@' in request.email_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain patterns should not contain @ symbol"
        )
    
    if not request.is_domain and '@' not in request.email_pattern:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email patterns must contain @ symbol"
        )
    
    # Create whitelist entry
    whitelist_entry = EmailWhitelist(
        email_pattern=request.email_pattern,
        is_domain=request.is_domain
    )
    db.add(whitelist_entry)
    await db.commit()
    await db.refresh(whitelist_entry)
    
    return EmailWhitelistResponse.model_validate(whitelist_entry)

@router.get("/whitelist", response_model=list[EmailWhitelistResponse])
async def list_whitelist(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all whitelist entries (admin only)"""
    result = await db.execute(
        select(EmailWhitelist)
        .offset(skip)
        .limit(limit)
    )
    entries = result.scalars().all()
    
    return [EmailWhitelistResponse.model_validate(entry) for entry in entries]

@router.get("/ai-config")
async def get_ai_configuration(
    admin_user: User = Depends(require_admin)
):
    """Get current AI model configuration (admin only)
    
    Returns the current AI model configuration for debugging and monitoring.
    This helps administrators verify which models are being used across the platform.
    """
    models = get_all_models()
    
    # Add status information for each model
    config_with_status = {}
    for key, value in models.items():
        config_with_status[key] = {
            "model": value,
            "status": "active" if value and value != "placeholder" else "not_configured",
            "description": get_model_description(key)
        }
    
    return {
        "models": config_with_status,
        "timestamp": "2024-01-26T00:00:00Z",
        "environment": "production"  # or from config
    }

def get_model_description(model_type: str) -> str:
    """Get human-readable description for each model type"""
    descriptions = {
        'image_analysis': 'Analyzes uploaded images to extract educational content',
        'question_generation': 'Generates comprehension questions from reading content',
        'answer_evaluation': 'Evaluates student free-form responses',
        'vocab_extraction': 'Identifies challenging vocabulary from texts',
        'debate_generation': 'Creates debate topics and supporting materials',
        'speech_analysis': 'Analyzes student speech for pronunciation and fluency',
        'writing_assistance': 'Provides writing feedback and suggestions',
        'lecture_generation': 'Creates interactive lecture content',
    }
    return descriptions.get(model_type, 'Unknown model type')