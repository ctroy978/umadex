from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Classroom(Base):
    __tablename__ = "classrooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    class_code = Column(String(8), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    teacher = relationship("User", foreign_keys=[teacher_id])
    students = relationship("ClassroomStudent", back_populates="classroom")
    assignments = relationship("ClassroomAssignment", back_populates="classroom")


class ClassroomStudent(Base):
    __tablename__ = "classroom_students"
    __table_args__ = (
        UniqueConstraint('classroom_id', 'student_id', name='_classroom_student_uc'),
    )
    
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id"), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    removed_at = Column(DateTime(timezone=True), nullable=True)
    removed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    classroom = relationship("Classroom", back_populates="students")
    student = relationship("User", foreign_keys=[student_id])
    remover = relationship("User", foreign_keys=[removed_by])


class ClassroomAssignment(Base):
    __tablename__ = "classroom_assignments"
    __table_args__ = (
        UniqueConstraint('classroom_id', 'assignment_id', name='_classroom_assignment_uc'),
    )
    
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id"), primary_key=True)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    display_order = Column(Integer, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    classroom = relationship("Classroom", back_populates="assignments")
    assignment = relationship("ReadingAssignment")