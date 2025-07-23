# Vocabulary Test Security Implementation

## Overview
Implemented anti-cheating measures for vocabulary tests (umavocab) based on the existing umaread completion test security system.

## Database Changes

### Migration: 015_add_vocabulary_test_security.sql
Location: `/database/migrations/015_add_vocabulary_test_security.sql`

This migration adds:

1. **New columns to `vocabulary_test_attempts` table:**
   - `security_violations` (JSONB) - Array of violation details
   - `is_locked` (BOOLEAN) - Whether test is locked due to violations
   - `locked_at` (TIMESTAMPTZ) - When the test was locked
   - `locked_reason` (TEXT) - Reason for locking

2. **New table: `vocabulary_test_security_incidents`**
   ```sql
   CREATE TABLE vocabulary_test_security_incidents (
       id UUID PRIMARY KEY,
       test_attempt_id UUID REFERENCES vocabulary_test_attempts(id),
       incident_type VARCHAR(50), -- Types: focus_loss, tab_switch, etc.
       incident_data JSONB,
       resulted_in_lock BOOLEAN,
       created_at TIMESTAMPTZ
   );
   ```

3. **Indexes for performance:**
   - `idx_vocabulary_test_security_incidents_attempt`
   - `idx_vocabulary_test_security_incidents_type`
   - `idx_vocabulary_test_attempts_is_locked`

4. **Row Level Security policies** for the new table

Note: The migration conditionally creates `teacher_bypass_codes` table, but it already exists from migration 012.

## SQLAlchemy Models

### New File: `/backend/app/models/vocabulary_test.py`
Created models to match existing tables and new security features:

1. **VocabularyTest** - Maps to existing `vocabulary_tests` table
2. **VocabularyTestAttempt** - Maps to `vocabulary_test_attempts` with new security fields
3. **VocabularyTestSecurityIncident** - Maps to new security incidents table

These models were added to `/backend/app/models/__init__.py` for proper imports.

## API Endpoints

### New Security Endpoints in `/backend/app/api/v1/student.py`

1. **Log Security Incident**
   - `POST /vocabulary/test/{test_attempt_id}/security-incident`
   - Records violations and manages warning/lock state

2. **Get Security Status**
   - `GET /vocabulary/test/{test_attempt_id}/security-status`
   - Returns current violation count and lock status

3. **Unlock Test with Bypass Code**
   - `POST /vocabulary/test/{test_attempt_id}/unlock`
   - Allows teacher bypass codes to unlock and reset tests

### Enhanced Existing Endpoints

1. **Start Vocabulary Test** (`POST /vocabulary/{assignment_id}/test/start`)
   - Now checks for existing locked attempts before creating new ones
   - Returns 423 LOCKED status if student has a locked test

2. **Submit Vocabulary Test** (`POST /vocabulary/test/submit/{test_attempt_id}`)
   - Prevents submission of locked tests
   - Returns 423 LOCKED status if test is locked

## Frontend Implementation

### New Hook: `/frontend/src/hooks/useVocabularyTestSecurity.ts`
Monitors and reports security violations:
- Tab switching (document visibility)
- Window blur/focus loss
- Navigation attempts
- Mobile app switching
- Orientation changes

### Updated Components

1. **VocabularyTestInterface.tsx**
   - Integrated security hook
   - Added SecurityWarningModal (reused from umaread tests)
   - Added TestLockoutModal (reused from umaread tests)
   - Maintains existing copy/paste prevention

2. **studentApi.ts**
   - Added three new security API methods
   - Type definitions for security responses

## Security Features

1. **Two-Strike System**
   - First violation: Warning modal with 10-second acknowledgment delay
   - Second violation: Test locked, requires teacher intervention

2. **Comprehensive Monitoring**
   - Tracks multiple cheating vectors
   - Mobile-specific detection (app switching, orientation)
   - Grace period for developer tools focus

3. **Teacher Override**
   - Uses existing teacher bypass code system
   - Unlocked tests restart from beginning
   - All previous responses cleared

4. **Persistence**
   - Security state survives page refreshes
   - Violations tracked in database
   - Lock status prevents test continuation

## Testing Considerations

When testing the implementation:
1. Open vocabulary test as student
2. Try switching tabs - should get warning
3. Switch tabs again - test should lock
4. Teacher can generate bypass code to unlock
5. Unlocked test starts fresh from beginning

## Future Considerations

The existing `teacher_bypass_codes` table from migration 012 has a different schema than what the vocabulary test expects. Currently works because:
- Code field names differ (`bypass_code` vs `code`)
- Type field differs (`context_type` vs `type`)

Consider unifying the bypass code systems in a future migration.