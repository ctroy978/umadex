from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, UniqueConstraint, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    test_schedule = relationship("ClassroomTestSchedule", back_populates="classroom", uselist=False)
    test_overrides = relationship("ClassroomTestOverride", back_populates="classroom")


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
        UniqueConstraint('classroom_id', 'assignment_id', 'vocabulary_list_id', name='_classroom_assignment_uc'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("reading_assignments.id"), nullable=True)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id"), nullable=True)
    assignment_type = Column(String(50), nullable=False, default="reading")
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    display_order = Column(Integer, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    vocab_settings = Column(JSONB, default={}, nullable=False, server_default='{}')
    
    # Relationships
    classroom = relationship("Classroom", back_populates="assignments")
    assignment = relationship("ReadingAssignment")
    vocabulary_list = relationship("VocabularyList")


class StudentAssignment(Base):
    __tablename__ = "student_assignments"
    __table_args__ = (
        UniqueConstraint('student_id', 'assignment_id', 'classroom_assignment_id', name='_student_assignment_uc'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), nullable=False)  # Generic assignment reference
    classroom_assignment_id = Column(Integer, ForeignKey("classroom_assignments.id"), nullable=False)
    assignment_type = Column(String(50), nullable=False, default="reading")
    
    status = Column(String(50), nullable=False, default="not_started")
    current_position = Column(Integer, default=1)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    
    progress_metadata = Column(JSONB, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    classroom_assignment = relationship("ClassroomAssignment")


class StudentEvent(Base):
    __tablename__ = "student_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id"), nullable=True)
    assignment_id = Column(UUID(as_uuid=True), nullable=True)
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_student_events_student_id', 'student_id'),
        Index('idx_student_events_classroom_id', 'classroom_id'),
        Index('idx_student_events_type', 'event_type'),
        Index('idx_student_events_created_at', 'created_at'),
    )
    
    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    classroom = relationship("Classroom", foreign_keys=[classroom_id])