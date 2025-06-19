from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class VocabularyStatus(str, enum.Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    REVIEWING = "reviewing"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DefinitionSource(str, enum.Enum):
    PENDING = "pending"
    AI = "ai"
    TEACHER = "teacher"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED_ONCE = "rejected_once"
    REJECTED_TWICE = "rejected_twice"


class VocabularyList(Base):
    __tablename__ = "vocabulary_lists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    context_description = Column(Text, nullable=False)
    grade_level = Column(String(50), nullable=False)
    subject_area = Column(String(100), nullable=False)
    status = Column(SQLEnum(VocabularyStatus, name='vocabularystatus', values_callable=lambda x: [e.value for e in x]), nullable=False, default=VocabularyStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    words = relationship("VocabularyWord", back_populates="vocabulary_list", cascade="all, delete-orphan")
    teacher = relationship("User", back_populates="vocabulary_lists")
    chain_memberships = relationship("VocabularyChainMember", back_populates="vocabulary_list", cascade="all, delete-orphan")


class VocabularyWord(Base):
    __tablename__ = "vocabulary_words"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    word = Column(String(100), nullable=False)
    teacher_definition = Column(Text, nullable=True)
    teacher_example_1 = Column(Text, nullable=True)
    teacher_example_2 = Column(Text, nullable=True)
    ai_definition = Column(Text, nullable=True)
    ai_example_1 = Column(Text, nullable=True)
    ai_example_2 = Column(Text, nullable=True)
    definition_source = Column(SQLEnum(DefinitionSource, name='definitionsource', values_callable=lambda x: [e.value for e in x]), nullable=False, default=DefinitionSource.PENDING)
    examples_source = Column(SQLEnum(DefinitionSource, name='definitionsource', values_callable=lambda x: [e.value for e in x]), nullable=False, default=DefinitionSource.PENDING)
    position = Column(Integer, nullable=False)
    audio_url = Column(String(500), nullable=True)  # Store pronunciation audio URL
    phonetic_text = Column(String(200), nullable=True)  # Store phonetic spelling
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vocabulary_list = relationship("VocabularyList", back_populates="words")
    review = relationship("VocabularyWordReview", back_populates="word", uselist=False, cascade="all, delete-orphan")
    
    @property
    def definition(self) -> str:
        """Get the appropriate definition based on source preference"""
        if self.definition_source == DefinitionSource.TEACHER and self.teacher_definition:
            return self.teacher_definition
        elif self.definition_source == DefinitionSource.AI and self.ai_definition:
            return self.ai_definition
        elif self.teacher_definition:
            return self.teacher_definition
        elif self.ai_definition:
            return self.ai_definition
        else:
            return f"Definition for '{self.word}'"
    
    @property
    def part_of_speech(self) -> str:
        """Get part of speech - for now return a default since it's not stored in DB"""
        # TODO: Add part_of_speech column to database in future migration
        return "word"


class VocabularyWordReview(Base):
    __tablename__ = "vocabulary_word_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_words.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    review_status = Column(SQLEnum(ReviewStatus, name='reviewstatus', values_callable=lambda x: [e.value for e in x]), nullable=False, default=ReviewStatus.PENDING)
    rejection_feedback = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    word = relationship("VocabularyWord", back_populates="review")