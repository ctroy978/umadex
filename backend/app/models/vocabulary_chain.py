"""
Vocabulary Chain Models
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, UniqueConstraint, text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base


class VocabularyChain(Base):
    """Named vocabulary chain for test chaining"""
    __tablename__ = "vocabulary_chains"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String)
    total_review_words = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    teacher = relationship("User", back_populates="vocabulary_chains")
    members = relationship("VocabularyChainMember", back_populates="chain", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('teacher_id', 'name', name='_teacher_chain_name_uc'),
    )
    
    @hybrid_property
    def member_count(self):
        """Get the number of vocabulary lists in this chain"""
        return len(self.members)


class VocabularyChainMember(Base):
    """Links vocabulary lists to chains"""
    __tablename__ = "vocabulary_chain_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    chain_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_chains.id", ondelete="CASCADE"), nullable=False)
    vocabulary_list_id = Column(UUID(as_uuid=True), ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chain = relationship("VocabularyChain", back_populates="members")
    vocabulary_list = relationship("VocabularyList", back_populates="chain_memberships")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('chain_id', 'vocabulary_list_id', name='_chain_list_uc'),
    )