"""
Vocabulary Practice Session Manager
Manages student sessions using Redis for active sessions and database for persistence
"""
import json
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class VocabularySessionManager:
    """Manages vocabulary practice sessions using Redis for active state"""
    
    def __init__(self):
        try:
            self.redis = get_redis_client()
        except Exception as e:
            logger.warning(f"Redis client not available: {e}")
            self.redis = None
    
    # Session State Keys
    def _activity_key(self, user_id: UUID, assignment_id: UUID) -> str:
        """Key for tracking last activity"""
        return f"vocab:activity:{user_id}:{assignment_id}"
    
    def _session_key(self, user_id: UUID, assignment_id: UUID) -> str:
        """Key for storing current game session"""
        return f"vocab:session:{user_id}:{assignment_id}"
    
    def _progress_key(self, user_id: UUID, assignment_id: UUID) -> str:
        """Key for storing progress state"""
        return f"vocab:progress:{user_id}:{assignment_id}"
    
    def _attempt_key(self, user_id: UUID, assignment_id: UUID, activity_type: str) -> str:
        """Key for storing current attempt info"""
        return f"vocab:attempt:{user_id}:{assignment_id}:{activity_type}"
    
    # Activity Tracking
    async def update_activity(self, user_id: UUID, assignment_id: UUID) -> None:
        """Update last activity timestamp"""
        if not self.redis:
            return
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            await self.redis.setex(
                self._activity_key(user_id, assignment_id),
                3600,  # 1 hour TTL
                timestamp
            )
        except Exception as e:
            logger.error(f"Failed to update activity: {e}")
    
    async def get_last_activity(self, user_id: UUID, assignment_id: UUID) -> Optional[datetime]:
        """Get last activity timestamp"""
        if not self.redis:
            return None
        try:
            timestamp_str = await self.redis.get(self._activity_key(user_id, assignment_id))
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str)
            return None
        except Exception as e:
            logger.error(f"Failed to get last activity: {e}")
            return None
    
    # Session Management
    async def set_current_session(
        self, 
        user_id: UUID, 
        assignment_id: UUID, 
        session_data: Dict[str, Any]
    ) -> None:
        """Store current session data in Redis"""
        if not self.redis:
            return
        try:
            session_json = json.dumps(session_data, default=str)
            await self.redis.setex(
                self._session_key(user_id, assignment_id),
                3600,  # 1 hour TTL
                session_json
            )
            await self.update_activity(user_id, assignment_id)
        except Exception as e:
            logger.error(f"Failed to set session: {e}")
    
    async def get_current_session(
        self, 
        user_id: UUID, 
        assignment_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get current session data from Redis"""
        if not self.redis:
            return None
        try:
            session_json = await self.redis.get(self._session_key(user_id, assignment_id))
            if session_json:
                return json.loads(session_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None
    
    async def clear_session(self, user_id: UUID, assignment_id: UUID) -> None:
        """Clear session data from Redis"""
        if not self.redis:
            return
        try:
            await self.redis.delete(self._session_key(user_id, assignment_id))
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
    
    # Progress State
    async def set_progress_state(
        self, 
        user_id: UUID, 
        assignment_id: UUID, 
        progress_data: Dict[str, Any]
    ) -> None:
        """Store progress state in Redis"""
        try:
            progress_json = json.dumps(progress_data, default=str)
            await self.redis.setex(
                self._progress_key(user_id, assignment_id),
                7200,  # 2 hours TTL for progress state
                progress_json
            )
            await self.update_activity(user_id, assignment_id)
        except Exception as e:
            logger.error(f"Failed to set progress state: {e}")
    
    async def get_progress_state(
        self, 
        user_id: UUID, 
        assignment_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get progress state from Redis"""
        try:
            progress_json = await self.redis.get(self._progress_key(user_id, assignment_id))
            if progress_json:
                return json.loads(progress_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get progress state: {e}")
            return None
    
    # Attempt Tracking
    async def set_current_attempt(
        self, 
        user_id: UUID, 
        assignment_id: UUID, 
        activity_type: str,
        attempt_data: Dict[str, Any]
    ) -> None:
        """Store current attempt data in Redis"""
        if not self.redis:
            return
        try:
            attempt_json = json.dumps(attempt_data, default=str)
            await self.redis.setex(
                self._attempt_key(user_id, assignment_id, activity_type),
                3600,  # 1 hour TTL
                attempt_json
            )
            await self.update_activity(user_id, assignment_id)
        except Exception as e:
            logger.error(f"Failed to set attempt: {e}")
    
    async def get_current_attempt(
        self, 
        user_id: UUID, 
        assignment_id: UUID, 
        activity_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get current attempt data from Redis"""
        if not self.redis:
            return None
        try:
            attempt_json = await self.redis.get(self._attempt_key(user_id, assignment_id, activity_type))
            if attempt_json:
                return json.loads(attempt_json)
            return None
        except Exception as e:
            logger.error(f"Failed to get attempt: {e}")
            return None
    
    async def clear_attempt(
        self, 
        user_id: UUID, 
        assignment_id: UUID, 
        activity_type: str
    ) -> None:
        """Clear current attempt data from Redis"""
        if not self.redis:
            return
        try:
            await self.redis.delete(self._attempt_key(user_id, assignment_id, activity_type))
        except Exception as e:
            logger.error(f"Failed to clear attempt: {e}")
    
    # Session Restoration
    async def restore_session_from_db(
        self, 
        user_id: UUID, 
        assignment_id: UUID, 
        db_session_data: Optional[Dict[str, Any]]
    ) -> None:
        """Restore session state from database to Redis"""
        if db_session_data:
            await self.set_current_session(user_id, assignment_id, db_session_data)
    
    async def restore_progress_from_db(
        self, 
        user_id: UUID, 
        assignment_id: UUID, 
        db_progress_data: Dict[str, Any]
    ) -> None:
        """Restore progress state from database to Redis"""
        await self.set_progress_state(user_id, assignment_id, db_progress_data)
    
    # Cleanup
    async def clear_all_session_data(self, user_id: UUID, assignment_id: UUID) -> None:
        """Clear all session data for an assignment"""
        try:
            keys_to_delete = [
                self._activity_key(user_id, assignment_id),
                self._session_key(user_id, assignment_id),
                self._progress_key(user_id, assignment_id),
                # Clear all activity type attempts
                self._attempt_key(user_id, assignment_id, "vocabulary_challenge"),
                self._attempt_key(user_id, assignment_id, "story_builder"),
                self._attempt_key(user_id, assignment_id, "concept_mapping"),
                self._attempt_key(user_id, assignment_id, "puzzle_path"),
            ]
            
            # Only delete keys that exist
            existing_keys = []
            for key in keys_to_delete:
                if await self.redis.exists(key):
                    existing_keys.append(key)
            
            if existing_keys:
                await self.redis.delete(*existing_keys)
                
        except Exception as e:
            logger.error(f"Failed to clear session data: {e}")
    
    # Monitoring
    async def get_active_sessions_count(self) -> int:
        """Get count of active vocabulary sessions"""
        try:
            cursor, keys = await self.redis.scan(0, match="vocab:activity:*", count=1000)
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to get active sessions count: {e}")
            return 0