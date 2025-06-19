"""
Vocabulary Chain Schemas
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.vocabulary import VocabularyListSummary


class VocabularyChainBase(BaseModel):
    """Base schema for vocabulary chain"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    total_review_words: int = Field(default=3, ge=1, le=4)


class VocabularyChainCreate(VocabularyChainBase):
    """Schema for creating a vocabulary chain"""
    pass


class VocabularyChainUpdate(BaseModel):
    """Schema for updating a vocabulary chain"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    total_review_words: Optional[int] = Field(None, ge=1, le=4)
    is_active: Optional[bool] = None


class VocabularyChainMemberAdd(BaseModel):
    """Schema for adding vocabulary lists to a chain"""
    vocabulary_list_ids: List[UUID]
    position_start: Optional[int] = Field(None, ge=0)  # Optional starting position


class VocabularyChainMemberReorder(BaseModel):
    """Schema for reordering vocabulary lists in a chain"""
    vocabulary_list_id: UUID
    new_position: int = Field(..., ge=0)


class VocabularyChainMember(BaseModel):
    """Schema for a vocabulary list in a chain"""
    id: UUID
    vocabulary_list_id: UUID
    position: int
    added_at: datetime
    vocabulary_list: Optional[VocabularyListSummary] = None
    
    class Config:
        from_attributes = True


class VocabularyChain(VocabularyChainBase):
    """Schema for a vocabulary chain response"""
    id: UUID
    teacher_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = 0
    members: Optional[List[VocabularyChainMember]] = []
    
    class Config:
        from_attributes = True


class VocabularyChainSummary(BaseModel):
    """Summary schema for vocabulary chain listing"""
    id: UUID
    name: str
    description: Optional[str]
    total_review_words: int
    is_active: bool
    member_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VocabularyChainList(BaseModel):
    """Schema for paginated vocabulary chain listing"""
    items: List[VocabularyChainSummary]
    total: int
    page: int
    per_page: int
    pages: int