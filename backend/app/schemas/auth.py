from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.user import UserRole

class OTPRequestSchema(BaseModel):
    email: EmailStr
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)

class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")

class UserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    username: str
    role: UserRole
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse