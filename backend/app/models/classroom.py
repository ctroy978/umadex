from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Enum
import enum
import uuid

from app.core.database import Base

class UmaType(str, enum.Enum):
    READ = "read"
    DEBATE = "debate" 
    VOCAB = "vocab"
    WRITE = "write"
    LECTURE = "lecture"
    
    def __str__(self):
        return self.value

class Classroom(Base):
    __tablename__ = "classrooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    subject = Column(String(255))
    grade_level = Column(String(50))
    school_year = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    teacher = relationship("User", back_populates="classrooms")
    enrollments = relationship("ClassroomStudent", back_populates="classroom", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="classroom", cascade="all, delete-orphan")

class ClassroomStudent(Base):
    __tablename__ = "classroom_students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="active")
    
    # Relationships
    classroom = relationship("Classroom", back_populates="enrollments")
    student = relationship("User", back_populates="enrollments")

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    classroom_id = Column(UUID(as_uuid=True), ForeignKey("classrooms.id"))
    uma_type = Column(Enum(UmaType, name='uma_type', values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String)
    content = Column(String)  # Will be JSONB in database
    due_date = Column(DateTime(timezone=True))
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    teacher = relationship("User", foreign_keys=[teacher_id])
    classroom = relationship("Classroom", back_populates="assignments")