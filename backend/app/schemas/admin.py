from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID

class EmailWhitelistCreate(BaseModel):
    email_pattern: str = Field(..., min_length=1, max_length=255)
    is_domain: bool = False

class EmailWhitelistResponse(BaseModel):
    id: UUID
    email_pattern: str
    is_domain: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class PromoteToTeacherRequest(BaseModel):
    user_id: UUID