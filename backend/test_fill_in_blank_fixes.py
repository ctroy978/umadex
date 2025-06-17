#!/usr/bin/env python3
"""
Test script to verify fill-in-the-blank fixes
Tests:
1. Failed attempt shows confirmation dialog
2. Declining a failed attempt allows retake
3. Student can retake after failing
"""

import asyncio
import os
import sys
from uuid import UUID

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.config import get_settings
from app.core.database import get_async_session
from app.services.vocabulary_practice import VocabularyPracticeService
from app.services.vocabulary_session_manager import VocabularySessionManager
import redis.asyncio as redis

async def test_fill_in_blank_fixes():
    settings = get_settings()
    
    # Initialize Redis connection
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    session_manager = VocabularySessionManager(redis_client)
    
    async for db in get_async_session():
        service = VocabularyPracticeService(db, session_manager)
        
        # Test data - update these with actual IDs from your database
        student_id = UUID("12345678-1234-5678-1234-567812345678")  # Update with real student ID
        vocabulary_list_id = UUID("87654321-4321-8765-4321-876543218765")  # Update with real vocabulary list ID
        classroom_assignment_id = 1  # Update with real classroom assignment ID
        
        print("=== Testing Fill-in-the-Blank Fixes ===\n")
        
        try:
            # Step 1: Start a new fill-in-blank attempt
            print("1. Starting new fill-in-blank attempt...")
            start_result = await service.start_fill_in_blank(
                student_id=student_id,
                vocabulary_list_id=vocabulary_list_id,
                classroom_assignment_id=classroom_assignment_id
            )
            
            attempt_id = UUID(start_result['fill_in_blank_attempt_id'])
            print(f"   ✓ Started attempt: {attempt_id}")
            print(f"   Total sentences: {start_result['total_sentences']}")
            print(f"   Passing score: {start_result['passing_score']}%")
            
            # Step 2: Submit wrong answers to ensure failure
            print("\n2. Submitting wrong answers to simulate failure...")
            for i in range(start_result['total_sentences']):
                progress = await service.get_fill_in_blank_progress(attempt_id)
                if progress['current_sentence']:
                    # Submit intentionally wrong answer
                    submit_result = await service.submit_fill_in_blank_answer(
                        fill_in_blank_attempt_id=attempt_id,
                        sentence_id=UUID(progress['current_sentence']['id']),
                        student_answer="WRONG_ANSWER",
                        time_spent_seconds=10
                    )
                    print(f"   Sentence {i+1}: Submitted wrong answer")
            
            print(f"   ✓ Completed with score: {submit_result['score_percentage']:.0f}%")
            print(f"   needs_confirmation: {submit_result['needs_confirmation']}")
            
            # Step 3: Check that status is pending_confirmation
            progress = await service.get_fill_in_blank_progress(attempt_id)
            print(f"\n3. Checking attempt status...")
            print(f"   ✓ Status: {progress['status']}")
            assert progress['status'] == 'pending_confirmation', "Failed attempt should be pending_confirmation"
            
            # Step 4: Decline the completion
            print("\n4. Declining completion to test retake...")
            decline_result = await service.decline_fill_in_blank_completion(
                fill_in_blank_attempt_id=attempt_id,
                student_id=student_id
            )
            print(f"   ✓ {decline_result['message']}")
            
            # Step 5: Try to start a new attempt (should work)
            print("\n5. Starting new attempt after decline...")
            new_attempt_result = await service.start_fill_in_blank(
                student_id=student_id,
                vocabulary_list_id=vocabulary_list_id,
                classroom_assignment_id=classroom_assignment_id
            )
            
            new_attempt_id = UUID(new_attempt_result['fill_in_blank_attempt_id'])
            print(f"   ✓ Successfully started new attempt: {new_attempt_id}")
            assert new_attempt_id != attempt_id, "Should be a different attempt ID"
            
            print("\n✅ All tests passed! Fill-in-the-blank fixes are working correctly.")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            await redis_client.close()

if __name__ == "__main__":
    print("Note: Update the student_id, vocabulary_list_id, and classroom_assignment_id")
    print("with real values from your database before running this test.\n")
    asyncio.run(test_fill_in_blank_fixes())