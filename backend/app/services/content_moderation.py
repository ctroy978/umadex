"""
Content moderation service for UMADebate
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.debate import ContentFlag, FlagType, FlagStatus
from app.schemas.debate import ContentFlagCreate


class ContentModerationService:
    """Service for content moderation in debates"""
    
    # Basic profanity patterns (will be enhanced with AI in production)
    PROFANITY_PATTERNS = [
        # This would contain actual patterns in production
        # For now, using placeholder patterns
        r'\b(bad_word_1|bad_word_2)\b',
    ]
    
    # Off-topic detection keywords (will be AI-powered in production)
    OFF_TOPIC_INDICATORS = [
        "homework", "test", "grade", "unrelated"
    ]
    
    async def analyze_content(
        self,
        content: str,
        debate_topic: str,
        assignment_id: UUID
    ) -> Dict[str, Any]:
        """Analyze content for potential issues"""
        results = {
            "should_flag": False,
            "flags": [],
            "confidence_scores": {}
        }
        
        # Check for profanity
        profanity_check = self._check_profanity(content)
        if profanity_check["found"]:
            results["should_flag"] = True
            results["flags"].append({
                "type": FlagType.PROFANITY,
                "confidence": profanity_check["confidence"],
                "reason": "Profanity detected in content"
            })
            results["confidence_scores"]["profanity"] = profanity_check["confidence"]
        
        # Check if content is appropriate
        appropriateness_check = self._check_appropriateness(content)
        if not appropriateness_check["appropriate"]:
            results["should_flag"] = True
            results["flags"].append({
                "type": FlagType.INAPPROPRIATE,
                "confidence": appropriateness_check["confidence"],
                "reason": appropriateness_check["reason"]
            })
            results["confidence_scores"]["inappropriate"] = appropriateness_check["confidence"]
        
        # Check if content is on-topic
        topic_relevance = self._check_topic_relevance(content, debate_topic)
        if topic_relevance["off_topic"]:
            results["should_flag"] = True
            results["flags"].append({
                "type": FlagType.OFF_TOPIC,
                "confidence": topic_relevance["confidence"],
                "reason": "Content appears to be off-topic"
            })
            results["confidence_scores"]["off_topic"] = topic_relevance["confidence"]
        
        # Check for spam patterns
        spam_check = self._check_spam(content)
        if spam_check["is_spam"]:
            results["should_flag"] = True
            results["flags"].append({
                "type": FlagType.SPAM,
                "confidence": spam_check["confidence"],
                "reason": spam_check["reason"]
            })
            results["confidence_scores"]["spam"] = spam_check["confidence"]
        
        return results
    
    def _check_profanity(self, content: str) -> Dict[str, Any]:
        """Check content for profanity"""
        content_lower = content.lower()
        
        for pattern in self.PROFANITY_PATTERNS:
            if re.search(pattern, content_lower):
                return {
                    "found": True,
                    "confidence": 0.95
                }
        
        return {
            "found": False,
            "confidence": 0.0
        }
    
    def _check_appropriateness(self, content: str) -> Dict[str, Any]:
        """Check if content is appropriate for educational context"""
        # In production, this would use AI to check for:
        # - Violence or threats
        # - Harassment or bullying
        # - Adult content
        # - Personal attacks
        
        # For now, basic checks
        inappropriate_patterns = [
            r'\b(threat|violence|attack)\b',
            r'\b(stupid|dumb|idiot)\b',  # Personal attacks
        ]
        
        content_lower = content.lower()
        for pattern in inappropriate_patterns:
            if re.search(pattern, content_lower):
                return {
                    "appropriate": False,
                    "confidence": 0.85,
                    "reason": "Content may contain inappropriate language or personal attacks"
                }
        
        return {
            "appropriate": True,
            "confidence": 0.9,
            "reason": None
        }
    
    def _check_topic_relevance(self, content: str, debate_topic: str) -> Dict[str, Any]:
        """Check if content is relevant to the debate topic"""
        # In production, this would use AI to:
        # - Analyze semantic similarity
        # - Check for topic drift
        # - Identify completely unrelated content
        
        # For now, basic keyword matching
        content_lower = content.lower()
        topic_lower = debate_topic.lower()
        
        # Extract key words from topic
        topic_words = set(word for word in topic_lower.split() if len(word) > 3)
        content_words = set(word for word in content_lower.split() if len(word) > 3)
        
        # Check overlap
        overlap = len(topic_words.intersection(content_words))
        relevance_score = overlap / max(len(topic_words), 1)
        
        # Check for off-topic indicators
        off_topic_found = any(indicator in content_lower for indicator in self.OFF_TOPIC_INDICATORS)
        
        if relevance_score < 0.1 or off_topic_found:
            return {
                "off_topic": True,
                "confidence": 0.7,
                "relevance_score": relevance_score
            }
        
        return {
            "off_topic": False,
            "confidence": 0.8,
            "relevance_score": relevance_score
        }
    
    def _check_spam(self, content: str) -> Dict[str, Any]:
        """Check for spam patterns"""
        # Check for repetitive content
        words = content.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_ratio = len(unique_words) / len(words)
            
            if repetition_ratio < 0.3:
                return {
                    "is_spam": True,
                    "confidence": 0.9,
                    "reason": "Content appears to be repetitive spam"
                }
        
        # Check for excessive caps
        if len(content) > 20:
            caps_ratio = sum(1 for c in content if c.isupper()) / len(content)
            if caps_ratio > 0.7:
                return {
                    "is_spam": True,
                    "confidence": 0.85,
                    "reason": "Excessive use of capital letters"
                }
        
        # Check for link spam (in student debates, links might be suspicious)
        link_pattern = r'https?://|www\.'
        link_count = len(re.findall(link_pattern, content))
        if link_count > 2:
            return {
                "is_spam": True,
                "confidence": 0.8,
                "reason": "Multiple links detected"
            }
        
        return {
            "is_spam": False,
            "confidence": 0.0,
            "reason": None
        }
    
    async def flag_content(
        self,
        db: AsyncSession,
        content: str,
        student_id: UUID,
        teacher_id: UUID,
        assignment_id: UUID,
        post_id: Optional[UUID] = None
    ) -> Optional[ContentFlag]:
        """Create a content flag based on analysis"""
        analysis = await self.analyze_content(
            content,
            "",  # Will get debate topic from assignment in production
            assignment_id
        )
        
        if not analysis["should_flag"]:
            return None
        
        # Create flag for the highest confidence issue
        highest_confidence_flag = max(
            analysis["flags"],
            key=lambda x: x["confidence"]
        )
        
        content_flag = ContentFlag(
            post_id=post_id,
            student_id=student_id,
            teacher_id=teacher_id,
            assignment_id=assignment_id,
            flag_type=highest_confidence_flag["type"],
            flag_reason=highest_confidence_flag["reason"],
            auto_flagged=True,
            confidence_score=highest_confidence_flag["confidence"],
            status=FlagStatus.PENDING
        )
        
        db.add(content_flag)
        await db.commit()
        await db.refresh(content_flag)
        
        return content_flag
    
    async def get_teacher_flags(
        self,
        db: AsyncSession,
        teacher_id: UUID,
        status: Optional[FlagStatus] = None
    ) -> List[ContentFlag]:
        """Get content flags for teacher review"""
        query = select(ContentFlag).where(
            ContentFlag.teacher_id == teacher_id
        )
        
        if status:
            query = query.where(ContentFlag.status == status)
        
        query = query.order_by(ContentFlag.created_at.desc())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def resolve_flag(
        self,
        db: AsyncSession,
        flag_id: UUID,
        status: FlagStatus,
        teacher_action: Optional[str] = None,
        teacher_notes: Optional[str] = None
    ) -> ContentFlag:
        """Resolve a content flag"""
        query = select(ContentFlag).where(ContentFlag.id == flag_id)
        result = await db.execute(query)
        flag = result.scalar_one()
        
        flag.status = status
        flag.teacher_action = teacher_action
        flag.teacher_notes = teacher_notes
        flag.resolved_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(flag)
        
        return flag
    
    async def check_student_post(
        self,
        content: str,
        assignment_id: UUID
    ) -> Dict[str, Any]:
        """Quick check for student post moderation"""
        # This is a simplified version for the student debate API
        # Returns a result compatible with ModerationResult schema
        
        analysis = await self.analyze_content(
            content,
            "",  # Will get debate topic from assignment in production
            assignment_id
        )
        
        if analysis["should_flag"]:
            highest_flag = max(analysis["flags"], key=lambda x: x["confidence"])
            return {
                "flagged": True,
                "flag_type": highest_flag["type"].value if hasattr(highest_flag["type"], 'value') else str(highest_flag["type"]),
                "confidence": highest_flag["confidence"],
                "requires_review": highest_flag["confidence"] > 0.7,
                "suggested_revision": highest_flag.get("reason", "Please revise your content")
            }
        
        return {
            "flagged": False,
            "flag_type": None,
            "confidence": 0.0,
            "requires_review": False,
            "suggested_revision": None
        }
        
    async def _ai_content_check(self, content: str) -> Dict[str, Any]:
        """Basic AI content check - placeholder for now"""
        # In production, this would use actual AI
        return {
            'appropriate': True,
            'confidence': 0.0,
            'reason': '',
            'suggestion': ''
        }
    
    async def _check_topic_relevance_ai(self, content: str, assignment_id: UUID) -> float:
        """Check topic relevance using AI - placeholder for now"""
        # In production, would check actual topic relevance using AI
        return 0.9
    
    def _contains_profanity(self, content: str) -> bool:
        """Basic profanity check - placeholder"""
        # In production, would have actual profanity list
        return False
    
    def _suggest_revision(self, content: str) -> str:
        """Suggest revision - placeholder"""
        return "Please revise your content"