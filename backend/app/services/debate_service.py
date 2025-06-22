"""
Service layer for UMADebate operations
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.debate import DebateAssignment, ContentFlag
from app.models.classroom import ClassroomAssignment
from app.schemas.debate import (
    DebateAssignmentCreate,
    DebateAssignmentUpdate,
    DebateAssignmentFilters
)


class DebateService:
    """Service class for debate-related operations"""
    
    async def create_assignment(
        self,
        db: AsyncSession,
        teacher_id: UUID,
        assignment_data: DebateAssignmentCreate
    ) -> DebateAssignment:
        """Create a new debate assignment"""
        db_assignment = DebateAssignment(
            teacher_id=teacher_id,
            **assignment_data.model_dump()
        )
        
        db.add(db_assignment)
        await db.commit()
        await db.refresh(db_assignment)
        
        return db_assignment
    
    async def get_assignment(
        self,
        db: AsyncSession,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> Optional[DebateAssignment]:
        """Get a specific debate assignment"""
        query = select(DebateAssignment).where(
            and_(
                DebateAssignment.id == assignment_id,
                DebateAssignment.teacher_id == teacher_id
            )
        )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_assignments(
        self,
        db: AsyncSession,
        teacher_id: UUID,
        filters: DebateAssignmentFilters,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """List debate assignments with filtering and pagination"""
        # Base query
        query = select(DebateAssignment).where(
            DebateAssignment.teacher_id == teacher_id
        )
        
        # Apply filters
        filter_conditions = []
        
        if not filters.include_archived:
            filter_conditions.append(DebateAssignment.deleted_at.is_(None))
        
        if filters.search:
            search_term = f"%{filters.search}%"
            filter_conditions.append(
                or_(
                    DebateAssignment.title.ilike(search_term),
                    DebateAssignment.topic.ilike(search_term),
                    DebateAssignment.description.ilike(search_term)
                )
            )
        
        if filters.grade_level:
            filter_conditions.append(DebateAssignment.grade_level == filters.grade_level)
        
        if filters.subject:
            filter_conditions.append(DebateAssignment.subject == filters.subject)
        
        if filters.date_from:
            filter_conditions.append(DebateAssignment.created_at >= filters.date_from)
        
        if filters.date_to:
            filter_conditions.append(DebateAssignment.created_at <= filters.date_to)
        
        if filter_conditions:
            query = query.where(and_(*filter_conditions))
        
        # Get counts
        total_query = select(func.count()).select_from(
            select(DebateAssignment).where(
                DebateAssignment.teacher_id == teacher_id
            ).subquery()
        )
        total_result = await db.execute(total_query)
        total_count = total_result.scalar()
        
        filtered_query = select(func.count()).select_from(query.subquery())
        filtered_result = await db.execute(filtered_query)
        filtered_count = filtered_result.scalar()
        
        # Apply pagination
        query = query.order_by(DebateAssignment.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        assignments = result.scalars().all()
        
        return {
            "assignments": assignments,
            "total": total_count,
            "filtered": filtered_count,
            "page": page,
            "per_page": per_page
        }
    
    async def update_assignment(
        self,
        db: AsyncSession,
        assignment: DebateAssignment,
        update_data: DebateAssignmentUpdate
    ) -> DebateAssignment:
        """Update a debate assignment"""
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(assignment, field, value)
        
        assignment.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(assignment)
        
        return assignment
    
    async def archive_assignment(
        self,
        db: AsyncSession,
        assignment: DebateAssignment
    ) -> None:
        """Soft delete a debate assignment"""
        assignment.deleted_at = datetime.utcnow()
        await db.commit()
    
    async def restore_assignment(
        self,
        db: AsyncSession,
        assignment: DebateAssignment
    ) -> None:
        """Restore a soft-deleted debate assignment"""
        assignment.deleted_at = None
        assignment.updated_at = datetime.utcnow()
        await db.commit()
    
    async def get_assignment_stats(
        self,
        db: AsyncSession,
        assignment_id: UUID
    ) -> Dict[str, Any]:
        """Get statistics for a debate assignment"""
        # This will be expanded in Phase 2 to include:
        # - Number of students enrolled
        # - Completion rates
        # - Average performance metrics
        # - Engagement statistics
        
        # For now, return basic stats
        assignment_count = await db.execute(
            select(func.count()).select_from(
                select(ClassroomAssignment).where(
                    and_(
                        ClassroomAssignment.assignment_id == assignment_id,
                        ClassroomAssignment.assignment_type == "debate"
                    )
                ).subquery()
            )
        )
        
        return {
            "classroom_count": assignment_count.scalar() or 0,
            "student_count": 0,  # Will be implemented in Phase 2
            "completion_rate": 0.0,  # Will be implemented in Phase 2
            "average_score": 0.0  # Will be implemented in Phase 2
        }
    
    async def validate_debate_topic(
        self,
        topic: str
    ) -> Dict[str, Any]:
        """Validate if a topic is suitable for debate"""
        # This will use AI in production to validate topics
        # For now, basic validation
        
        validation_result = {
            "is_valid": True,
            "confidence": 0.95,
            "suggestions": []
        }
        
        # Basic checks
        if len(topic) < 10:
            validation_result["is_valid"] = False
            validation_result["suggestions"].append("Topic is too short. Please provide more detail.")
        
        if not any(word in topic.lower() for word in ["should", "is", "are", "can", "will", "does"]):
            validation_result["suggestions"].append(
                "Consider framing your topic as a debatable question or statement."
            )
        
        return validation_result