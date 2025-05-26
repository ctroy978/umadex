import random
import string
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models import Classroom, ClassroomStudent, ClassroomAssignment, ReadingAssignment, User
from app.schemas.classroom import ClassroomCreate, ClassroomUpdate


def generate_class_code() -> str:
    """Generate a unique 6-character class code avoiding confusing characters."""
    # Avoid confusing characters: O, 0, I, 1
    chars = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
    return ''.join(random.choices(chars, k=6))


def create_classroom(db: Session, teacher_id: UUID, classroom: ClassroomCreate) -> Classroom:
    """Create a new classroom with a unique class code."""
    # Generate unique class code
    while True:
        class_code = generate_class_code()
        existing = db.query(Classroom).filter(
            and_(Classroom.class_code == class_code, Classroom.deleted_at.is_(None))
        ).first()
        if not existing:
            break
    
    db_classroom = Classroom(
        name=classroom.name,
        teacher_id=teacher_id,
        class_code=class_code
    )
    db.add(db_classroom)
    db.commit()
    db.refresh(db_classroom)
    return db_classroom


def get_classroom(db: Session, classroom_id: UUID, teacher_id: Optional[UUID] = None) -> Optional[Classroom]:
    """Get a classroom by ID, optionally filtered by teacher."""
    query = db.query(Classroom).filter(
        and_(Classroom.id == classroom_id, Classroom.deleted_at.is_(None))
    )
    if teacher_id:
        query = query.filter(Classroom.teacher_id == teacher_id)
    return query.first()


def get_classroom_by_code(db: Session, class_code: str) -> Optional[Classroom]:
    """Get a classroom by its class code."""
    return db.query(Classroom).filter(
        and_(Classroom.class_code == class_code, Classroom.deleted_at.is_(None))
    ).first()


def list_teacher_classrooms(db: Session, teacher_id: UUID) -> List[Classroom]:
    """List all classrooms for a teacher."""
    return db.query(Classroom).filter(
        and_(Classroom.teacher_id == teacher_id, Classroom.deleted_at.is_(None))
    ).order_by(Classroom.created_at.desc()).all()


def list_student_classrooms(db: Session, student_id: UUID) -> List[Classroom]:
    """List all classrooms a student is enrolled in."""
    return db.query(Classroom).join(ClassroomStudent).filter(
        and_(
            ClassroomStudent.student_id == student_id,
            ClassroomStudent.removed_at.is_(None),
            Classroom.deleted_at.is_(None)
        )
    ).order_by(ClassroomStudent.joined_at.desc()).all()


def update_classroom(db: Session, classroom_id: UUID, classroom_update: ClassroomUpdate) -> Optional[Classroom]:
    """Update a classroom's details."""
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        return None
    
    update_data = classroom_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(classroom, field, value)
    
    db.commit()
    db.refresh(classroom)
    return classroom


def soft_delete_classroom(db: Session, classroom_id: UUID) -> bool:
    """Soft delete a classroom."""
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        return False
    
    classroom.deleted_at = datetime.utcnow()
    db.commit()
    return True


def join_classroom(db: Session, student_id: UUID, classroom_id: UUID) -> Optional[ClassroomStudent]:
    """Add a student to a classroom."""
    # Check if already enrolled
    existing = db.query(ClassroomStudent).filter(
        and_(
            ClassroomStudent.classroom_id == classroom_id,
            ClassroomStudent.student_id == student_id
        )
    ).first()
    
    if existing:
        if existing.removed_at:
            # Re-enroll previously removed student
            existing.removed_at = None
            existing.removed_by = None
            existing.joined_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        return None  # Already enrolled
    
    # Create new enrollment
    enrollment = ClassroomStudent(
        classroom_id=classroom_id,
        student_id=student_id
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def leave_classroom(db: Session, student_id: UUID, classroom_id: UUID) -> bool:
    """Student leaves a classroom."""
    enrollment = db.query(ClassroomStudent).filter(
        and_(
            ClassroomStudent.classroom_id == classroom_id,
            ClassroomStudent.student_id == student_id,
            ClassroomStudent.removed_at.is_(None)
        )
    ).first()
    
    if not enrollment:
        return False
    
    enrollment.removed_at = datetime.utcnow()
    db.commit()
    return True


def remove_student_from_classroom(db: Session, classroom_id: UUID, student_id: UUID, removed_by: UUID) -> bool:
    """Teacher removes a student from classroom."""
    enrollment = db.query(ClassroomStudent).filter(
        and_(
            ClassroomStudent.classroom_id == classroom_id,
            ClassroomStudent.student_id == student_id,
            ClassroomStudent.removed_at.is_(None)
        )
    ).first()
    
    if not enrollment:
        return False
    
    enrollment.removed_at = datetime.utcnow()
    enrollment.removed_by = removed_by
    db.commit()
    return True


def get_classroom_students(db: Session, classroom_id: UUID) -> List[User]:
    """Get all active students in a classroom."""
    return db.query(User).join(ClassroomStudent).filter(
        and_(
            ClassroomStudent.classroom_id == classroom_id,
            ClassroomStudent.removed_at.is_(None)
        )
    ).all()


def get_classroom_assignments(db: Session, classroom_id: UUID) -> List[ReadingAssignment]:
    """Get all assignments in a classroom."""
    return db.query(ReadingAssignment).join(ClassroomAssignment).filter(
        ClassroomAssignment.classroom_id == classroom_id
    ).order_by(ClassroomAssignment.display_order, ClassroomAssignment.assigned_at).all()


def update_classroom_assignments(db: Session, classroom_id: UUID, assignment_ids: List[UUID]) -> dict:
    """Update the assignments in a classroom."""
    # Get current assignments
    current_assignments = db.query(ClassroomAssignment).filter(
        ClassroomAssignment.classroom_id == classroom_id
    ).all()
    
    current_ids = {ca.assignment_id for ca in current_assignments}
    new_ids = set(assignment_ids)
    
    # Remove assignments no longer in the list
    to_remove = current_ids - new_ids
    if to_remove:
        db.query(ClassroomAssignment).filter(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.assignment_id.in_(to_remove)
            )
        ).delete(synchronize_session=False)
    
    # Add new assignments
    to_add = new_ids - current_ids
    for idx, assignment_id in enumerate(assignment_ids):
        if assignment_id in to_add:
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                display_order=idx
            )
            db.add(ca)
        else:
            # Update display order for existing assignments
            db.query(ClassroomAssignment).filter(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.assignment_id == assignment_id
                )
            ).update({"display_order": idx})
    
    db.commit()
    
    return {
        "added": list(to_add),
        "removed": list(to_remove),
        "total": len(new_ids)
    }


def get_teacher_available_assignments(db: Session, teacher_id: UUID, classroom_id: Optional[UUID] = None) -> List[dict]:
    """Get all assignments available to a teacher, with assignment status for a specific classroom."""
    assignments = db.query(ReadingAssignment).filter(
        and_(
            ReadingAssignment.teacher_id == teacher_id,
            ReadingAssignment.archived != True
        )
    ).all()
    
    assigned_ids = set()
    if classroom_id:
        assigned = db.query(ClassroomAssignment.assignment_id).filter(
            ClassroomAssignment.classroom_id == classroom_id
        ).all()
        assigned_ids = {a[0] for a in assigned}
    
    return [
        {
            "id": a.id,
            "title": a.title,
            "assignment_type": a.assignment_type,
            "created_at": a.created_at,
            "is_assigned": a.id in assigned_ids
        }
        for a in assignments
    ]


def count_classroom_students(db: Session, classroom_id: UUID) -> int:
    """Count active students in a classroom."""
    return db.query(ClassroomStudent).filter(
        and_(
            ClassroomStudent.classroom_id == classroom_id,
            ClassroomStudent.removed_at.is_(None)
        )
    ).count()


def count_classroom_assignments(db: Session, classroom_id: UUID) -> int:
    """Count assignments in a classroom."""
    return db.query(ClassroomAssignment).filter(
        ClassroomAssignment.classroom_id == classroom_id
    ).count()