-- Migration 036: Add CASCADE DELETE constraints for proper data cleanup
-- This migration adds proper foreign key constraints with CASCADE DELETE
-- to ensure orphaned records are automatically cleaned up when users are deleted.

-- =====================================================
-- STEP 1: Drop existing foreign key constraints that need modification
-- =====================================================

-- Drop constraints that need to be recreated with CASCADE DELETE
ALTER TABLE IF EXISTS classroom_students DROP CONSTRAINT IF EXISTS classroom_students_student_id_fkey;
ALTER TABLE IF EXISTS student_assignments DROP CONSTRAINT IF EXISTS student_assignments_student_id_fkey;
ALTER TABLE IF EXISTS student_test_attempts DROP CONSTRAINT IF EXISTS student_test_attempts_student_id_fkey;
ALTER TABLE IF EXISTS umaread_student_responses DROP CONSTRAINT IF EXISTS umaread_student_responses_student_id_fkey;
ALTER TABLE IF EXISTS umaread_chunk_progress DROP CONSTRAINT IF EXISTS umaread_chunk_progress_student_id_fkey;
ALTER TABLE IF EXISTS umaread_assignment_progress DROP CONSTRAINT IF EXISTS umaread_assignment_progress_student_id_fkey;
ALTER TABLE IF EXISTS student_events DROP CONSTRAINT IF EXISTS student_events_student_id_fkey;
ALTER TABLE IF EXISTS vocabulary_student_progress DROP CONSTRAINT IF EXISTS vocabulary_student_progress_student_id_fkey;
ALTER TABLE IF EXISTS answer_evaluations DROP CONSTRAINT IF EXISTS answer_evaluations_student_id_fkey;

-- Drop teacher-related constraints that need modification
ALTER TABLE IF EXISTS classrooms DROP CONSTRAINT IF EXISTS classrooms_teacher_id_fkey;
ALTER TABLE IF EXISTS reading_assignments DROP CONSTRAINT IF EXISTS reading_assignments_teacher_id_fkey;
ALTER TABLE IF EXISTS vocabulary_lists DROP CONSTRAINT IF EXISTS vocabulary_lists_teacher_id_fkey;

-- Drop admin-related constraints that need modification
ALTER TABLE IF EXISTS users DROP CONSTRAINT IF EXISTS users_deleted_by_fkey;
ALTER TABLE IF EXISTS admin_actions DROP CONSTRAINT IF EXISTS admin_actions_admin_id_fkey;
ALTER TABLE IF EXISTS role_changes DROP CONSTRAINT IF EXISTS role_changes_admin_id_fkey;
ALTER TABLE IF EXISTS user_deletions DROP CONSTRAINT IF EXISTS user_deletions_admin_id_fkey;

-- =====================================================
-- STEP 2: Add CASCADE DELETE constraints for student data
-- =====================================================

-- Student classroom enrollments - DELETE when student is deleted
ALTER TABLE classroom_students
ADD CONSTRAINT classroom_students_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- Student assignments - DELETE when student is deleted
ALTER TABLE student_assignments
ADD CONSTRAINT student_assignments_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- Student test attempts - DELETE when student is deleted
ALTER TABLE student_test_attempts
ADD CONSTRAINT student_test_attempts_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- UMARead student responses - DELETE when student is deleted
ALTER TABLE umaread_student_responses
ADD CONSTRAINT umaread_student_responses_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- UMARead chunk progress - DELETE when student is deleted
ALTER TABLE umaread_chunk_progress
ADD CONSTRAINT umaread_chunk_progress_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- UMARead assignment progress - DELETE when student is deleted
ALTER TABLE umaread_assignment_progress
ADD CONSTRAINT umaread_assignment_progress_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- Student events - DELETE when student is deleted
ALTER TABLE student_events
ADD CONSTRAINT student_events_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- Vocabulary student progress - DELETE when student is deleted
ALTER TABLE vocabulary_student_progress
ADD CONSTRAINT vocabulary_student_progress_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- Answer evaluations - DELETE when student is deleted
ALTER TABLE answer_evaluations
ADD CONSTRAINT answer_evaluations_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- =====================================================
-- STEP 3: Add SET NULL constraints for teacher data
-- Teachers cannot be hard deleted, so we preserve their content
-- =====================================================

-- Classrooms - SET NULL when teacher is deleted (preserve classroom)
ALTER TABLE classrooms
ADD CONSTRAINT classrooms_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;

-- Reading assignments - SET NULL when teacher is deleted (preserve assignment)
ALTER TABLE reading_assignments
ADD CONSTRAINT reading_assignments_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;

-- Vocabulary lists - SET NULL when teacher is deleted (preserve vocabulary)
ALTER TABLE vocabulary_lists
ADD CONSTRAINT vocabulary_lists_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;

-- =====================================================
-- STEP 4: Add SET NULL constraints for admin audit trails
-- Preserve audit history even if admin is deleted
-- =====================================================

-- User deletion tracking - SET NULL when admin is deleted
ALTER TABLE users
ADD CONSTRAINT users_deleted_by_fkey
FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL;

-- Admin actions - SET NULL when admin is deleted (preserve audit trail)
ALTER TABLE admin_actions
ADD CONSTRAINT admin_actions_admin_id_fkey
FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL;

-- Role changes - SET NULL when admin is deleted (preserve audit trail)
ALTER TABLE role_changes
ADD CONSTRAINT role_changes_admin_id_fkey
FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL;

-- User deletions - SET NULL when admin is deleted (preserve audit trail)
ALTER TABLE user_deletions
ADD CONSTRAINT user_deletions_admin_id_fkey
FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL;

-- =====================================================
-- STEP 5: Add missing OTP constraint with CASCADE DELETE
-- =====================================================

-- Add foreign key for OTP requests (currently missing)
-- First add the user_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'otp_requests' AND column_name = 'user_id') THEN
        ALTER TABLE otp_requests ADD COLUMN user_id UUID;
        
        -- Populate existing records by matching email
        UPDATE otp_requests 
        SET user_id = users.id 
        FROM users 
        WHERE otp_requests.email = users.email;
    END IF;
END
$$;

-- Add the constraint
ALTER TABLE otp_requests
ADD CONSTRAINT otp_requests_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- =====================================================
-- STEP 6: Create indexes for performance
-- =====================================================

-- Add indexes on foreign key columns for better deletion performance
CREATE INDEX IF NOT EXISTS idx_classroom_students_student_id ON classroom_students(student_id);
CREATE INDEX IF NOT EXISTS idx_student_assignments_student_id ON student_assignments(student_id);
CREATE INDEX IF NOT EXISTS idx_student_test_attempts_student_id ON student_test_attempts(student_id);
CREATE INDEX IF NOT EXISTS idx_umaread_responses_student_id ON umaread_student_responses(student_id);
CREATE INDEX IF NOT EXISTS idx_umaread_chunk_progress_student_id ON umaread_chunk_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_umaread_assignment_progress_student_id ON umaread_assignment_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_users_deleted_by ON users(deleted_by);

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

-- Log the migration completion
INSERT INTO schema_migrations (version, applied_at) 
VALUES ('036', NOW()) 
ON CONFLICT (version) DO NOTHING;

-- Add a comment explaining the migration
COMMENT ON TABLE users IS 'Users table with CASCADE DELETE constraints for student data and SET NULL for teacher content preservation';