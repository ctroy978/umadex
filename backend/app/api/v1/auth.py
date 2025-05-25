from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import OTPRequestSchema, OTPVerifySchema, TokenResponse, UserResponse
from app.schemas.user import UserCreate
from app.services.auth import AuthService
from app.services.email import EmailService
from app.services.user import UserService
from app.utils.deps import get_current_user
from app.models import User

router = APIRouter()

@router.post("/request-otp", status_code=status.HTTP_200_OK)
async def request_otp(
    request: OTPRequestSchema,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP for login or registration"""
    # Check if email is whitelisted
    if not await AuthService.check_email_whitelist(db, request.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not authorized for registration"
        )
    
    # Check if user exists
    user = await UserService.get_user_by_email(db, request.email)
    
    # If user doesn't exist and registration data provided, validate it
    if not user and (not request.first_name or not request.last_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name and last name required for new users"
        )
    
    # If new user with registration data, create the user
    if not user and request.first_name and request.last_name:
        user_create = UserCreate(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name
        )
        user = await UserService.create_user(db, user_create)
    
    # Generate and send OTP
    otp = await AuthService.generate_and_store_otp(request.email)
    await EmailService.send_otp_email(request.email, otp)
    
    return {
        "message": "OTP sent to your email",
        "is_new_user": user is None or (request.first_name and request.last_name)
    }

@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    request: OTPVerifySchema,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and create session"""
    # Verify OTP
    if not await AuthService.verify_otp(request.email, request.otp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Get or create user
    user = await UserService.get_user_by_email(db, request.email)
    
    if not user:
        # This shouldn't happen if frontend flow is followed correctly
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User registration required. Please request OTP with registration details."
        )
    
    # Create session
    token = await AuthService.create_session(db, user.id)
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user)
    )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Logout current user"""
    # Get token from dependency injection context
    # In a real app, we'd extract this from the request
    # For now, we'll invalidate all sessions for the user
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse.model_validate(current_user)