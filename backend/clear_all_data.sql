-- Clear all data from the database for testing
-- This script removes all data but preserves table structures

-- Disable foreign key checks temporarily
SET session_replication_role = 'replica';

-- Clear test-related tables
TRUNCATE TABLE test_security_incidents CASCADE;
TRUNCATE TABLE teacher_bypass_codes CASCADE;
TRUNCATE TABLE student_test_attempts CASCADE;
TRUNCATE TABLE test_results CASCADE;
TRUNCATE TABLE assignment_tests CASCADE;

-- Clear umaread tables
TRUNCATE TABLE umaread_test_override_usage CASCADE;
TRUNCATE TABLE umaread_test_questions CASCADE;
TRUNCATE TABLE umaread_test_results CASCADE;
TRUNCATE TABLE umaread_student_events CASCADE;
TRUNCATE TABLE umaread_assignment_progress CASCADE;
TRUNCATE TABLE umaread_simple_questions CASCADE;
TRUNCATE TABLE umaread_simple_sessions CASCADE;
TRUNCATE TABLE student_assignments CASCADE;
TRUNCATE TABLE umaread_assignments CASCADE;

-- Clear vocabulary tables
TRUNCATE TABLE classroom_vocabulary_assignments CASCADE;
TRUNCATE TABLE student_vocabulary_progress CASCADE;
TRUNCATE TABLE vocabulary_assignments CASCADE;

-- Clear classroom tables
TRUNCATE TABLE classroom_test_schedules CASCADE;
TRUNCATE TABLE classroom_assignments CASCADE;
TRUNCATE TABLE classroom_students CASCADE;
TRUNCATE TABLE classrooms CASCADE;

-- Clear reading/assignment tables
TRUNCATE TABLE ai_image_analysis CASCADE;
TRUNCATE TABLE assignment_images CASCADE;
TRUNCATE TABLE reading_chunks CASCADE;
TRUNCATE TABLE reading_assignments CASCADE;

-- Clear user-related tables
TRUNCATE TABLE refresh_tokens CASCADE;
TRUNCATE TABLE whitelist_entries CASCADE;
TRUNCATE TABLE users CASCADE;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- Verify tables are empty
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'reading_assignments', COUNT(*) FROM reading_assignments
UNION ALL
SELECT 'assignment_tests', COUNT(*) FROM assignment_tests
UNION ALL
SELECT 'test_results', COUNT(*) FROM test_results
UNION ALL
SELECT 'classrooms', COUNT(*) FROM classrooms
UNION ALL
SELECT 'umaread_assignments', COUNT(*) FROM umaread_assignments
UNION ALL
SELECT 'student_test_attempts', COUNT(*) FROM student_test_attempts;

-- Reset sequences (optional - uncomment if you want IDs to start from 1)
-- ALTER SEQUENCE users_id_seq RESTART WITH 1;
-- ALTER SEQUENCE reading_assignments_id_seq RESTART WITH 1;
-- etc...