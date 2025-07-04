-- Direct SQL cleanup script for UMADex database
-- This will delete all data while preserving schema

-- Disable foreign key checks
SET session_replication_role = 'replica';

-- Delete from all tables in dependency order
DELETE FROM test_security_incidents;
DELETE FROM test_override_usage;
DELETE FROM classroom_test_overrides;
DELETE FROM classroom_test_schedules;
DELETE FROM teacher_bypass_codes;
DELETE FROM student_test_attempts;
DELETE FROM test_results;
DELETE FROM assignment_tests;
DELETE FROM vocabulary_practice_progress;
DELETE FROM vocabulary_word_reviews;
DELETE FROM vocabulary_chain_members;
DELETE FROM vocabulary_chains;
DELETE FROM vocabulary_words;
DELETE FROM vocabulary_lists;
DELETE FROM umaread_assignment_progress;
DELETE FROM umaread_chunk_progress;
DELETE FROM umaread_student_responses;
DELETE FROM answer_evaluations;
DELETE FROM question_cache;
DELETE FROM assignment_images;
DELETE FROM reading_chunks;
DELETE FROM reading_assignments;
DELETE FROM student_writing_submissions;
DELETE FROM writing_assignments;
DELETE FROM student_events;
DELETE FROM student_assignments;
DELETE FROM classroom_assignments;
DELETE FROM classroom_students;
DELETE FROM classrooms;
DELETE FROM refresh_tokens;
DELETE FROM user_sessions;
DELETE FROM otp_requests;
DELETE FROM email_whitelists;
DELETE FROM users;

-- Re-enable foreign key checks
SET session_replication_role = 'origin';

-- Show counts to confirm
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'classrooms', COUNT(*) FROM classrooms
UNION ALL
SELECT 'classroom_students', COUNT(*) FROM classroom_students
UNION ALL
SELECT 'classroom_assignments', COUNT(*) FROM classroom_assignments
UNION ALL
SELECT 'student_assignments', COUNT(*) FROM student_assignments;