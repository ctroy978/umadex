"""
UMARead Redis session management service
Handles temporary session state for active reading sessions
"""
import json
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from app.core.redis import get_redis_client


class UMAReadSessionManager:
    """Manages temporary session state in Redis for UMARead"""
    
    # Key prefixes for different types of session data
    QUESTION_STATE_PREFIX = "umaread:qstate"
    DIFFICULTY_PREFIX = "umaread:difficulty"
    QUESTION_CACHE_PREFIX = "umaread:questions"
    RATE_LIMIT_PREFIX = "umaread:ratelimit"
    
    # TTL values (in seconds)
    SESSION_TTL = 3600  # 1 hour for active sessions
    QUESTION_CACHE_TTL = 1800  # 30 minutes for cached questions
    RATE_LIMIT_TTL = 300  # 5 minutes for rate limiting
    
    def __init__(self):
        self.redis = get_redis_client()
    
    # Question state management
    async def get_question_state(self, user_id: UUID, assignment_id: UUID, chunk_number: int) -> Optional[str]:
        """Get the current question state for a user/assignment/chunk"""
        key = f"{self.QUESTION_STATE_PREFIX}:{user_id}:{assignment_id}:{chunk_number}"
        state = await self.redis.get(key)
        return state
    
    async def set_question_state(self, user_id: UUID, assignment_id: UUID, chunk_number: int, state: str):
        """Set the question state (e.g., 'summary_complete', 'chunk_complete')"""
        key = f"{self.QUESTION_STATE_PREFIX}:{user_id}:{assignment_id}:{chunk_number}"
        await self.redis.setex(key, self.SESSION_TTL, state)
    
    async def clear_question_state(self, user_id: UUID, assignment_id: UUID, chunk_number: int):
        """Clear the question state when moving to a new chunk"""
        key = f"{self.QUESTION_STATE_PREFIX}:{user_id}:{assignment_id}:{chunk_number}"
        await self.redis.delete(key)
    
    # Difficulty level management
    async def get_difficulty_level(self, user_id: UUID, assignment_id: UUID) -> Optional[int]:
        """Get the current difficulty level for a user/assignment"""
        key = f"{self.DIFFICULTY_PREFIX}:{user_id}:{assignment_id}"
        level = await self.redis.get(key)
        return int(level) if level else None
    
    async def set_difficulty_level(self, user_id: UUID, assignment_id: UUID, level: int):
        """Set the current difficulty level"""
        key = f"{self.DIFFICULTY_PREFIX}:{user_id}:{assignment_id}"
        await self.redis.setex(key, self.SESSION_TTL, str(level))
    
    # Question caching for evaluation
    async def cache_questions(self, user_id: UUID, assignment_id: UUID, chunk_number: int, questions: Dict[str, Any]):
        """Cache generated questions for later evaluation"""
        key = f"{self.QUESTION_CACHE_PREFIX}:{user_id}:{assignment_id}:{chunk_number}"
        await self.redis.setex(key, self.QUESTION_CACHE_TTL, json.dumps(questions))
    
    async def get_cached_questions(self, user_id: UUID, assignment_id: UUID, chunk_number: int) -> Optional[Dict[str, Any]]:
        """Retrieve cached questions"""
        key = f"{self.QUESTION_CACHE_PREFIX}:{user_id}:{assignment_id}:{chunk_number}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def clear_question_cache(self, user_id: UUID, assignment_id: UUID, chunk_number: int):
        """Clear cached questions for a specific chunk"""
        key = f"{self.QUESTION_CACHE_PREFIX}:{user_id}:{assignment_id}:{chunk_number}"
        await self.redis.delete(key)
    
    # Rate limiting for answer submissions
    async def check_rate_limit(self, user_id: UUID, assignment_id: UUID, chunk_number: int) -> bool:
        """Check if user is within rate limits for answer submission"""
        key = f"{self.RATE_LIMIT_PREFIX}:{user_id}:{assignment_id}:{chunk_number}"
        
        # Get current count
        current = await self.redis.get(key)
        if current and int(current) >= 10:  # Max 10 submissions per 5 minutes
            return False
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, self.RATE_LIMIT_TTL)
        await pipe.execute()
        
        return True
    
    # Session cleanup
    async def clear_assignment_session(self, user_id: UUID, assignment_id: UUID):
        """Clear all session data for a user/assignment when completed"""
        pattern = f"umaread:*:{user_id}:{assignment_id}*"
        
        # Find all keys matching the pattern
        cursor = 0
        keys_to_delete = []
        
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break
        
        # Delete all found keys
        if keys_to_delete:
            await self.redis.delete(*keys_to_delete)
    
    # Session activity tracking
    async def update_activity(self, user_id: UUID, assignment_id: UUID):
        """Update last activity timestamp for a session"""
        key = f"umaread:activity:{user_id}:{assignment_id}"
        await self.redis.setex(key, self.SESSION_TTL, datetime.utcnow().isoformat())
    
    async def get_last_activity(self, user_id: UUID, assignment_id: UUID) -> Optional[datetime]:
        """Get last activity timestamp"""
        key = f"umaread:activity:{user_id}:{assignment_id}"
        timestamp = await self.redis.get(key)
        return datetime.fromisoformat(timestamp) if timestamp else None
    
    # Bulk operations for monitoring
    async def get_active_sessions_count(self) -> int:
        """Get count of active reading sessions"""
        pattern = "umaread:activity:*"
        cursor = 0
        count = 0
        
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break
        
        return count