"""
Vocabulary Chain API Routes
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models import User
from app.schemas.vocabulary_chain import (
    VocabularyChainCreate, VocabularyChainUpdate, VocabularyChain,
    VocabularyChainList, VocabularyChainMemberAdd, VocabularyChainMemberReorder,
    VocabularyChainMember
)
from app.services.vocabulary_chain import VocabularyChainService

router = APIRouter()


async def get_current_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Ensure current user is a teacher"""
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


@router.post("/chains", response_model=VocabularyChain)
async def create_chain(
    chain_data: VocabularyChainCreate,
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vocabulary chain"""
    try:
        chain = await VocabularyChainService.create_chain(
            db, current_teacher.id, chain_data
        )
        return chain
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/chains", response_model=VocabularyChainList)
async def list_chains(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    include_inactive: bool = Query(False),
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of vocabulary chains"""
    result = await VocabularyChainService.get_chains(
        db, current_teacher.id, include_inactive, page, per_page
    )
    return result


@router.get("/chains/{chain_id}", response_model=VocabularyChain)
async def get_chain(
    chain_id: UUID,
    include_members: bool = Query(True),
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vocabulary chain"""
    chain = await VocabularyChainService.get_chain(
        db, chain_id, current_teacher.id, include_members
    )
    
    if not chain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chain not found"
        )
    
    return chain


@router.put("/chains/{chain_id}", response_model=VocabularyChain)
async def update_chain(
    chain_id: UUID,
    update_data: VocabularyChainUpdate,
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update a vocabulary chain"""
    try:
        chain = await VocabularyChainService.update_chain(
            db, chain_id, current_teacher.id, update_data
        )
        
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chain not found"
            )
        
        return chain
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/chains/{chain_id}")
async def delete_chain(
    chain_id: UUID,
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) a vocabulary chain"""
    success = await VocabularyChainService.delete_chain(
        db, chain_id, current_teacher.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chain not found"
        )
    
    return {"detail": "Chain deleted successfully"}


@router.post("/chains/{chain_id}/members", response_model=List[VocabularyChainMember])
async def add_members(
    chain_id: UUID,
    member_data: VocabularyChainMemberAdd,
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Add vocabulary lists to a chain"""
    try:
        members = await VocabularyChainService.add_members(
            db, chain_id, current_teacher.id, member_data
        )
        return members
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/chains/{chain_id}/members/{vocabulary_list_id}")
async def remove_member(
    chain_id: UUID,
    vocabulary_list_id: UUID,
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Remove a vocabulary list from a chain"""
    success = await VocabularyChainService.remove_member(
        db, chain_id, vocabulary_list_id, current_teacher.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chain or member not found"
        )
    
    return {"detail": "Member removed successfully"}


@router.put("/chains/{chain_id}/members/reorder")
async def reorder_member(
    chain_id: UUID,
    reorder_data: VocabularyChainMemberReorder,
    current_teacher: User = Depends(get_current_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Reorder a vocabulary list within a chain"""
    success = await VocabularyChainService.reorder_member(
        db, chain_id, current_teacher.id, reorder_data
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chain or member not found"
        )
    
    return {"detail": "Member reordered successfully"}