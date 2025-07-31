from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.user import UserRole

class OTPRequestSchema(BaseModel):
    email: EmailStr
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = UserRole.STUDENT
    
    @field_validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and v.strip() == '':
            raise ValueError('Name cannot be empty')
        return v

class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")

class UserResponse(BaseModel):
    id: str  # Changed from UUID to str
    email: str
    first_name: str
    last_name: str
    username: str
    role: UserRole
    is_admin: bool
    created_at: Optional[datetime] = None  # Made optional
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = 3600  # Made optional with default
    user: UserResponse

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires