-- Migration 037: Fix remaining NO ACTION constraints that prevent hard delete
-- This migration updates all remaining foreign key constraints that have NO ACTION
-- to appropriate CASCADE DELETE or SET NULL policies.

-- =====================================================
-- STEP 1: Drop existing NO ACTION constraints
-- =====================================================

-- Test and evaluation related constraints (student data - should CASCADE)
ALTER TABLE IF EXISTS test_security_incidents DROP CONSTRAINT IF EXISTS test_security_incidents_student_id_fkey;
ALTER TABLE IF EXISTS test_results DROP CONSTRAINT IF EXISTS test_results_student_id_fkey;
ALTER TABLE IF EXISTS test_evaluation_results DROP CONSTRAINT IF EXISTS test_evaluation_results_student_id_fkey;
ALTER TABLE IF EXISTS test_override_usage DROP CONSTRAINT IF EXISTS test_override_usage_student_id_fkey;
ALTER TABLE IF EXISTS reading_student_responses DROP CONSTRAINT IF EXISTS reading_student_responses_student_id_fkey;

-- Teacher/admin action constraints (audit data - should SET NULL)
ALTER TABLE IF EXISTS assignment_tests DROP CONSTRAINT IF EXISTS assignment_tests_approved_by_fkey;
ALTER TABLE IF EXISTS classroom_students DROP CONSTRAINT IF EXISTS classroom_students_removed_by_fkey;
ALTER TABLE IF EXISTS classroom_test_overrides DROP CONSTRAINT IF EXISTS classroom_test_overrides_teacher_id_fkey;
ALTER TABLE IF EXISTS classroom_test_schedules DROP CONSTRAINT IF EXISTS classroom_test_schedules_created_by_teacher_id_fkey;
ALTER TABLE IF EXISTS reading_cache_flush_log DROP CONSTRAINT IF EXISTS reading_cache_flush_log_teacher_id_fkey;
ALTER TABLE IF EXISTS role_changes DROP CONSTRAINT IF EXISTS role_changes_changed_by_fkey;
ALTER TABLE IF EXISTS teacher_evaluation_overrides DROP CONSTRAINT IF EXISTS teacher_evaluation_overrides_teacher_id_fkey;
ALTER TABLE IF EXISTS test_evaluation_results DROP CONSTRAINT IF EXISTS test_evaluation_results_teacher_override_by_fkey;
ALTER TABLE IF EXISTS user_deletions DROP CONSTRAINT IF EXISTS user_deletions_deleted_by_fkey;

-- Bypass code constraints (mixed - needs analysis)
ALTER TABLE IF EXISTS teacher_bypass_codes DROP CONSTRAINT IF EXISTS teacher_bypass_codes_student_id_fkey;
ALTER TABLE IF EXISTS teacher_bypass_codes DROP CONSTRAINT IF EXISTS teacher_bypass_codes_teacher_id_fkey;

-- =====================================================
-- STEP 2: Add CASCADE DELETE for student data
-- =====================================================

-- Student test and evaluation data - DELETE when student is deleted
ALTER TABLE test_security_incidents
ADD CONSTRAINT test_security_incidents_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE test_results
ADD CONSTRAINT test_results_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE test_evaluation_results
ADD CONSTRAINT test_evaluation_results_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE test_override_usage
ADD CONSTRAINT test_override_usage_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE reading_student_responses
ADD CONSTRAINT reading_student_responses_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- Student bypass codes - DELETE when student is deleted
ALTER TABLE teacher_bypass_codes
ADD CONSTRAINT teacher_bypass_codes_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;

-- =====================================================
-- STEP 3: Add SET NULL for audit/administrative data
-- =====================================================

-- Assignment approval tracking - SET NULL when admin is deleted
ALTER TABLE assignment_tests
ADD CONSTRAINT assignment_tests_approved_by_fkey
FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;

-- Classroom removal tracking - SET NULL when admin is deleted  
ALTER TABLE classroom_students
ADD CONSTRAINT classroom_students_removed_by_fkey
FOREIGN KEY (removed_by) REFERENCES users(id) ON DELETE SET NULL;

-- Test schedule and override tracking - SET NULL when teacher is deleted
ALTER TABLE classroom_test_overrides
ADD CONSTRAINT classroom_test_overrides_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE classroom_test_schedules
ADD CONSTRAINT classroom_test_schedules_created_by_teacher_id_fkey
FOREIGN KEY (created_by_teacher_id) REFERENCES users(id) ON DELETE SET NULL;

-- Cache management tracking - SET NULL when teacher is deleted
ALTER TABLE reading_cache_flush_log
ADD CONSTRAINT reading_cache_flush_log_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;

-- Role change tracking - SET NULL when admin is deleted
ALTER TABLE role_changes
ADD CONSTRAINT role_changes_changed_by_fkey
FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL;

-- Teacher evaluation overrides - SET NULL when teacher is deleted
ALTER TABLE teacher_evaluation_overrides
ADD CONSTRAINT teacher_evaluation_overrides_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;

-- Test evaluation overrides - SET NULL when teacher is deleted
ALTER TABLE test_evaluation_results
ADD CONSTRAINT test_evaluation_results_teacher_override_by_fkey
FOREIGN KEY (teacher_override_by) REFERENCES users(id) ON DELETE SET NULL;

-- User deletion tracking - SET NULL when admin is deleted
ALTER TABLE user_deletions
ADD CONSTRAINT user_deletions_deleted_by_fkey
FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL;

-- Teacher bypass codes - SET NULL when teacher is deleted (preserve bypass code record)
ALTER TABLE teacher_bypass_codes
ADD CONSTRAINT teacher_bypass_codes_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;

-- =====================================================
-- STEP 4: Add indexes for performance
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_test_security_incidents_student_id ON test_security_incidents(student_id);
CREATE INDEX IF NOT EXISTS idx_test_results_student_id ON test_results(student_id);
CREATE INDEX IF NOT EXISTS idx_test_evaluation_results_student_id ON test_evaluation_results(student_id);
CREATE INDEX IF NOT EXISTS idx_test_override_usage_student_id ON test_override_usage(student_id);
CREATE INDEX IF NOT EXISTS idx_reading_student_responses_student_id ON reading_student_responses(student_id);
CREATE INDEX IF NOT EXISTS idx_teacher_bypass_codes_student_id ON teacher_bypass_codes(student_id);
CREATE INDEX IF NOT EXISTS idx_teacher_bypass_codes_teacher_id ON teacher_bypass_codes(teacher_id);

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================

-- Log the migration completion
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations') THEN
        INSERT INTO schema_migrations (version, applied_at) 
        VALUES ('037', NOW()) 
        ON CONFLICT (version) DO NOTHING;
    END IF;
END $$;

-- Add comment
COMMENT ON SCHEMA public IS 'All foreign key constraints properly configured with CASCADE DELETE for student data and SET NULL for audit/administrative data';