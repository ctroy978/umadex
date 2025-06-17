# Vocabulary Assignment Fix Guide

## Overview
This guide documents the issues found and fixes applied to the Concept Mapping assignment, which should be applied to the other three vocabulary assignments (Word Builder, Context Clues, Definition Match).

## Critical Issues to Fix

### 1. Database Status Constraints
**Problem**: The database constraint for attempt status doesn't include all necessary states.

**Check for**: 
- Look for CHECK constraints on status columns in the models
- Verify they include: `'pending_confirmation'` and `'declined'` states

**Fix**:
```python
# In models/vocabulary_practice.py
CheckConstraint(
    "status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')",
    name='check_[assignment]_attempt_status'
)
```

### 2. Completion Dialog Not Showing for Failed Attempts
**Problem**: When students fail (score < 70%), they don't see a completion dialog to confirm they understand they failed.

**Check for**:
- In the `submit_[assignment]` method, look for where status is set upon completion
- Verify if failed attempts get a different status than passed attempts

**Fix**:
```python
# In services/vocabulary_practice.py - submit method
if is_complete:
    # Set status to pending_confirmation for BOTH pass and fail
    # This ensures the dialog shows for both scenarios
    attempt.status = 'pending_confirmation'
```

### 3. Decline/Retake Functionality
**Problem**: When students decline to complete a failed assignment, the system doesn't properly clean up for retakes.

**Check for**:
- The `decline_[assignment]_completion` method
- Whether it deletes attempt records and clears session data

**Fix**:
```python
async def decline_[assignment]_completion(self, attempt_id: UUID, student_id: UUID):
    # 1. Delete all submission records for this attempt
    await self.db.execute(
        delete(VocabularyAssignmentTable)
        .where(
            and_(
                VocabularyAssignmentTable.practice_progress_id == attempt.practice_progress_id,
                VocabularyAssignmentTable.attempt_number == attempt.attempt_number
            )
        )
    )
    
    # 2. Delete the attempt record itself
    await self.db.delete(attempt)
    
    # 3. Clear Redis session data
    await self.session_manager.clear_all_session_data(student_id, attempt.vocabulary_list_id)
    
    # 4. Clear practice progress game session
    if attempt.practice_progress:
        attempt.practice_progress.current_game_session = {}
```

### 4. Session Resume Error Handling
**Problem**: When trying to resume a session with a deleted attempt, the system throws an error instead of starting fresh.

**Check for**:
- In `start_[assignment]` method, how it handles existing sessions
- Whether it has error handling for stale sessions

**Fix**:
```python
# In start_[assignment] method
existing_session = await self.session_manager.get_current_session(student_id, vocabulary_list_id)
if existing_session and '[assignment]_attempt_id' in existing_session:
    try:
        return await self._resume_[assignment](student_id, vocabulary_list_id, existing_session)
    except ValueError:
        # Session is stale, continue to create new attempt
        pass
```

### 5. Redis Session Cleanup on Successful Completion
**Problem**: Redis session data should be cleared after BOTH successful and failed completions.

**Check for**:
- In `confirm_[assignment]_completion` method
- Whether it calls `clear_all_session_data`

**Fix**:
```python
# In confirm_[assignment]_completion method, after updating database:
await self.session_manager.clear_all_session_data(student_id, attempt.vocabulary_list_id)
```

### 6. Frontend Response Handling
**Check for**:
- In the frontend page component, verify the submission response includes:
  - `needs_confirmation` flag
  - `percentage_score` for display
  - `is_complete` flag

**Ensure**:
```typescript
// The completion dialog shows when:
if (result.is_complete && result.needs_confirmation) {
    setShowCompletionDialog(true)
}
```

## Testing Checklist

1. **Failed Attempt Flow**:
   - Complete assignment with score < 70%
   - Verify dialog appears
   - Click "Retake Assignment Later"
   - Verify you can start a new attempt without errors

2. **Successful Attempt Flow**:
   - Complete assignment with score ≥ 70%
   - Verify dialog appears
   - Click "Complete Assignment"
   - Verify assignment marked as completed in practice progress

3. **Database Verification**:
   - Check attempt records have correct status
   - Verify Redis sessions are cleared after completion
   - Confirm practice_status JSON is updated correctly

4. **Error Prevention**:
   - No duplicate key violations on retake
   - No "session is no longer valid" errors
   - No 500 errors when starting new attempts

## Common Patterns to Look For

1. **Status values**: Each assignment may use different status strings - verify all are included in constraints
2. **Unique constraints**: Check for constraints on (practice_progress_id, word_id, attempt_number) or similar
3. **Session management**: Ensure consistent pattern of checking, resuming, and clearing sessions
4. **Practice progress updates**: Verify the assignment is added to completed_assignments array

Remember: The goal is to ensure students can always complete assignments, see appropriate feedback, and retry failed attempts without technical errors.