from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.types import Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base

class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    
    def __str__(self):
        return self.value

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(Enum(UserRole, name='user_role', values_callable=lambda obj: [e.value for e in obj]), default=UserRole.STUDENT, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    bypass_code = Column(String(255), nullable=True)  # Hashed 4-digit code for teachers
    bypass_code_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Soft delete fields
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    deletion_reason = Column(Text, nullable=True)
    
    # Relationships
    classrooms = relationship("Classroom", back_populates="teacher", foreign_keys="Classroom.teacher_id")
    enrollments = relationship("ClassroomStudent", back_populates="student", foreign_keys="ClassroomStudent.student_id")
    reading_assignments = relationship("ReadingAssignment", back_populates="teacher")
    vocabulary_lists = relationship("VocabularyList", back_populates="teacher")
    vocabulary_chains = relationship("VocabularyChain", back_populates="teacher")
    debate_assignments = relationship("DebateAssignment", back_populates="teacher")
    student_debates = relationship("StudentDebate", back_populates="student", foreign_keys="StudentDebate.student_id")
    writing_assignments = relationship("WritingAssignment", back_populates="teacher")
    writing_submissions = relationship("StudentWritingSubmission", back_populates="student")