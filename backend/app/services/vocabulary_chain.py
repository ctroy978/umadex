"""
Vocabulary Chain Service
"""
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import VocabularyChain, VocabularyChainMember, VocabularyList, User
from app.schemas.vocabulary_chain import (
    VocabularyChainCreate, VocabularyChainUpdate, 
    VocabularyChainMemberAdd, VocabularyChainMemberReorder,
    VocabularyChain as VocabularyChainSchema
)

logger = logging.getLogger(__name__)


class VocabularyChainService:
    """Service for managing vocabulary chains"""
    
    @staticmethod
    async def create_chain(
        db: AsyncSession,
        teacher_id: UUID,
        chain_data: VocabularyChainCreate
    ) -> VocabularyChain:
        """Create a new vocabulary chain"""
        
        # Check if chain name already exists for this teacher
        existing = await db.execute(
            select(VocabularyChain).where(
                and_(
                    VocabularyChain.teacher_id == teacher_id,
                    VocabularyChain.name == chain_data.name,
                    VocabularyChain.is_active == True
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Chain with name '{chain_data.name}' already exists")
        
        # Create new chain
        chain = VocabularyChain(
            teacher_id=teacher_id,
            **chain_data.dict()
        )
        db.add(chain)
        await db.commit()
        await db.refresh(chain)
        
        # Return a simplified response without relationships
        return VocabularyChainSchema(
            id=chain.id,
            teacher_id=chain.teacher_id,
            name=chain.name,
            description=chain.description,
            total_review_words=chain.total_review_words,
            is_active=chain.is_active,
            created_at=chain.created_at,
            updated_at=chain.updated_at,
            member_count=0,
            members=[]
        )
    
    @staticmethod
    async def get_chains(
        db: AsyncSession,
        teacher_id: UUID,
        include_inactive: bool = False,
        page: int = 1,
        per_page: int = 20
    ) -> dict:
        """Get paginated list of vocabulary chains for a teacher"""
        
        # Base query
        query = select(VocabularyChain).where(
            VocabularyChain.teacher_id == teacher_id
        )
        
        if not include_inactive:
            query = query.where(VocabularyChain.is_active == True)
        
        # Count total
        count_query = select(func.count()).select_from(VocabularyChain).where(
            VocabularyChain.teacher_id == teacher_id
        )
        if not include_inactive:
            count_query = count_query.where(VocabularyChain.is_active == True)
        
        total = await db.scalar(count_query)
        
        # Get paginated results with member count
        query = query.options(selectinload(VocabularyChain.members))
        query = query.order_by(VocabularyChain.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        chains = result.scalars().all()
        
        # Calculate pages
        pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        return {
            "items": chains,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages
        }
    
    @staticmethod
    async def get_chain(
        db: AsyncSession,
        chain_id: UUID,
        teacher_id: UUID,
        include_members: bool = True
    ) -> Optional[VocabularyChain]:
        """Get a specific vocabulary chain"""
        
        query = select(VocabularyChain).where(
            and_(
                VocabularyChain.id == chain_id,
                VocabularyChain.teacher_id == teacher_id
            )
        )
        
        if include_members:
            query = query.options(
                selectinload(VocabularyChain.members).selectinload(
                    VocabularyChainMember.vocabulary_list
                )
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_chain(
        db: AsyncSession,
        chain_id: UUID,
        teacher_id: UUID,
        update_data: VocabularyChainUpdate
    ) -> Optional[VocabularyChain]:
        """Update a vocabulary chain"""
        
        chain = await VocabularyChainService.get_chain(
            db, chain_id, teacher_id, include_members=False
        )
        
        if not chain:
            return None
        
        # Check if new name conflicts with existing chain
        if update_data.name and update_data.name != chain.name:
            existing = await db.execute(
                select(VocabularyChain).where(
                    and_(
                        VocabularyChain.teacher_id == teacher_id,
                        VocabularyChain.name == update_data.name,
                        VocabularyChain.id != chain_id,
                        VocabularyChain.is_active == True
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Chain with name '{update_data.name}' already exists")
        
        # Update fields
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(chain, field, value)
        
        await db.commit()
        await db.refresh(chain)
        
        return chain
    
    @staticmethod
    async def delete_chain(
        db: AsyncSession,
        chain_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Delete (deactivate) a vocabulary chain"""
        
        chain = await VocabularyChainService.get_chain(
            db, chain_id, teacher_id, include_members=False
        )
        
        if not chain:
            return False
        
        chain.is_active = False
        await db.commit()
        
        return True
    
    @staticmethod
    async def add_members(
        db: AsyncSession,
        chain_id: UUID,
        teacher_id: UUID,
        member_data: VocabularyChainMemberAdd
    ) -> List[VocabularyChainMember]:
        """Add vocabulary lists to a chain"""
        
        # Verify chain ownership
        chain = await VocabularyChainService.get_chain(
            db, chain_id, teacher_id, include_members=True
        )
        
        if not chain:
            raise ValueError("Chain not found")
        
        # Verify all vocabulary lists exist and belong to teacher
        list_ids = member_data.vocabulary_list_ids
        result = await db.execute(
            select(VocabularyList).where(
                and_(
                    VocabularyList.id.in_(list_ids),
                    VocabularyList.teacher_id == teacher_id,
                    VocabularyList.deleted_at.is_(None)
                )
            )
        )
        valid_lists = result.scalars().all()
        valid_list_ids = {list.id for list in valid_lists}
        
        if len(valid_list_ids) != len(list_ids):
            invalid_ids = set(list_ids) - valid_list_ids
            raise ValueError(f"Invalid vocabulary list IDs: {invalid_ids}")
        
        # Get current max position
        current_max_position = max(
            (m.position for m in chain.members), default=-1
        )
        
        # Add new members
        new_members = []
        position_start = member_data.position_start or (current_max_position + 1)
        
        for i, list_id in enumerate(list_ids):
            # Check if already a member
            if any(m.vocabulary_list_id == list_id for m in chain.members):
                continue
            
            member = VocabularyChainMember(
                chain_id=chain_id,
                vocabulary_list_id=list_id,
                position=position_start + i
            )
            db.add(member)
            new_members.append(member)
        
        await db.commit()
        
        # Refresh to get full member data
        for member in new_members:
            await db.refresh(member)
        
        return new_members
    
    @staticmethod
    async def remove_member(
        db: AsyncSession,
        chain_id: UUID,
        vocabulary_list_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Remove a vocabulary list from a chain"""
        
        # Verify chain ownership
        chain = await VocabularyChainService.get_chain(
            db, chain_id, teacher_id, include_members=False
        )
        
        if not chain:
            return False
        
        # Find and remove member
        result = await db.execute(
            select(VocabularyChainMember).where(
                and_(
                    VocabularyChainMember.chain_id == chain_id,
                    VocabularyChainMember.vocabulary_list_id == vocabulary_list_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            return False
        
        await db.delete(member)
        
        # Reorder remaining members to fill gap
        await db.execute(
            text("""
                UPDATE vocabulary_chain_members 
                SET position = position - 1 
                WHERE chain_id = :chain_id 
                AND position > :removed_position
            """),
            {
                "chain_id": str(chain_id),
                "removed_position": member.position
            }
        )
        
        await db.commit()
        
        return True
    
    @staticmethod
    async def reorder_member(
        db: AsyncSession,
        chain_id: UUID,
        teacher_id: UUID,
        reorder_data: VocabularyChainMemberReorder
    ) -> bool:
        """Reorder a vocabulary list within a chain"""
        
        # Verify chain ownership
        chain = await VocabularyChainService.get_chain(
            db, chain_id, teacher_id, include_members=True
        )
        
        if not chain:
            return False
        
        # Find the member to move
        member_to_move = None
        for member in chain.members:
            if member.vocabulary_list_id == reorder_data.vocabulary_list_id:
                member_to_move = member
                break
        
        if not member_to_move:
            return False
        
        old_position = member_to_move.position
        new_position = reorder_data.new_position
        
        if old_position == new_position:
            return True
        
        # Reorder other members
        if old_position < new_position:
            # Moving down - shift others up
            await db.execute(
                text("""
                    UPDATE vocabulary_chain_members 
                    SET position = position - 1 
                    WHERE chain_id = :chain_id 
                    AND position > :old_position 
                    AND position <= :new_position
                """),
                {
                    "chain_id": str(chain_id),
                    "old_position": old_position,
                    "new_position": new_position
                }
            )
        else:
            # Moving up - shift others down
            await db.execute(
                text("""
                    UPDATE vocabulary_chain_members 
                    SET position = position + 1 
                    WHERE chain_id = :chain_id 
                    AND position >= :new_position 
                    AND position < :old_position
                """),
                {
                    "chain_id": str(chain_id),
                    "new_position": new_position,
                    "old_position": old_position
                }
            )
        
        # Update the moved member's position
        member_to_move.position = new_position
        
        await db.commit()
        
        return True
    
    @staticmethod
    async def get_lists_for_chain(
        db: AsyncSession,
        chain_id: UUID
    ) -> List[VocabularyList]:
        """Get all vocabulary lists in a chain, ordered by position"""
        
        result = await db.execute(
            select(VocabularyList)
            .join(VocabularyChainMember)
            .where(VocabularyChainMember.chain_id == chain_id)
            .order_by(VocabularyChainMember.position)
        )
        
        return result.scalars().all()