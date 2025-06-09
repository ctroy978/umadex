from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any
from enum import Enum

class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"

class DeletionReason(str, Enum):
    graduation = "graduation"
    transfer = "transfer"
    disciplinary = "disciplinary"
    inactive = "inactive"
    other = "other"

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

class AdminUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    username: str
    role: UserRole
    is_admin: bool
    created_at: datetime
    deleted_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None
    classroom_count: int = 0
    enrolled_classrooms: int = 0

    class Config:
        from_attributes = True

class AdminUserListResponse(BaseModel):
    users: List[AdminUserResponse]
    total: int
    page: int
    per_page: int
    pages: int

class UserPromotionRequest(BaseModel):
    new_role: Optional[UserRole] = None
    make_admin: Optional[bool] = None
    reason: Optional[str] = None

class UserDeletionRequest(BaseModel):
    reason: DeletionReason
    custom_reason: Optional[str] = None
    notify_affected_teachers: bool = False
    confirmation_phrase: Optional[str] = None  # Required for hard delete

class UserRestoreRequest(BaseModel):
    pass

class AdminDashboardResponse(BaseModel):
    total_users: int
    total_students: int
    total_teachers: int
    total_admins: int
    deleted_users: int
    recent_registrations: List[AdminUserResponse]
    recent_admin_actions: List[Dict[str, Any]]

class AdminAuditLogResponse(BaseModel):
    id: UUID
    admin_id: UUID
    admin_email: str
    action_type: str
    target_id: Optional[UUID] = None
    target_type: Optional[str] = None
    action_data: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserImpactAnalysis(BaseModel):
    user_id: UUID
    user_email: str
    user_role: UserRole
    is_admin: bool
    
    # Teacher impacts
    affected_classrooms: int = 0
    affected_assignments: int = 0
    affected_students: int = 0
    classroom_names: List[str] = []
    
    # Student impacts
    enrolled_classrooms: int = 0
    total_assignments: int = 0
    test_attempts: int = 0
    
    warnings: List[str] = []

class UserSearchFilters(BaseModel):
    search: Optional[str] = None
    role: Optional[UserRole] = None
    is_admin: Optional[bool] = None
    include_deleted: bool = False

class BulkActionRequest(BaseModel):
    user_ids: List[UUID]
    action: str  # "promote", "soft_delete", etc.
    action_params: Dict[str, Any] = {}

class AdminStatistics(BaseModel):
    daily_registrations: List[Dict[str, Any]]
    role_distribution: Dict[str, int]
    deletion_statistics: Dict[str, int]
    activity_summary: Dict[str, Any]