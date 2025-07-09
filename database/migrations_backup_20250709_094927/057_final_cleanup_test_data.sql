-- Database Cleanup Script (Final Version)
-- This script removes all test data except the admin user (admin-csd8) and email whitelist

-- Start transaction
BEGIN;

-- Store the admin user ID for reference
DO $$
DECLARE
    admin_user_id UUID;
BEGIN
    -- Get the admin user ID
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin-csd8';
    
    IF admin_user_id IS NULL THEN
        RAISE EXCEPTION 'Admin user admin-csd8 not found!';
    END IF;

    RAISE NOTICE 'Found admin user with ID: %', admin_user_id;

    -- Delete in dependency order (most dependent first)
    
    -- 1. Delete all vocabulary practice/game/test attempt data
    DELETE FROM vocabulary_concept_map_attempts;
    DELETE FROM vocabulary_fill_in_blank_attempts;
    DELETE FROM vocabulary_fill_in_blank_responses;
    DELETE FROM vocabulary_game_attempts;
    DELETE FROM vocabulary_puzzle_attempts;
    DELETE FROM vocabulary_puzzle_responses;
    DELETE FROM vocabulary_story_attempts;
    DELETE FROM vocabulary_story_responses;
    DELETE FROM vocabulary_test_attempts;
    DELETE FROM vocabulary_practice_progress;
    RAISE NOTICE 'Deleted vocabulary attempt/response data';
    
    -- 2. Delete vocabulary practice content
    DELETE FROM vocabulary_concept_maps;
    DELETE FROM vocabulary_fill_in_blank_sentences;
    DELETE FROM vocabulary_game_questions;
    DELETE FROM vocabulary_puzzle_games;
    DELETE FROM vocabulary_story_prompts;
    DELETE FROM vocabulary_tests;
    RAISE NOTICE 'Deleted vocabulary practice content';
    
    -- 3. Delete vocabulary chain members
    DELETE FROM vocabulary_chain_members;
    RAISE NOTICE 'Deleted vocabulary_chain_members';
    
    -- 4. Delete vocabulary test configs
    DELETE FROM vocabulary_test_configs;
    RAISE NOTICE 'Deleted vocabulary_test_configs';
    
    -- 5. Delete student data
    DELETE FROM student_vocabulary_progress;
    DELETE FROM student_assignments;
    DELETE FROM student_events;
    DELETE FROM student_test_attempts;
    DELETE FROM reading_student_responses;
    DELETE FROM umaread_student_responses;
    RAISE NOTICE 'Deleted student data';
    
    -- 6. Delete vocabulary word data
    DELETE FROM vocabulary_word_reviews;
    DELETE FROM vocabulary_words;
    RAISE NOTICE 'Deleted vocabulary word data';
    
    -- 7. Delete reading data
    DELETE FROM reading_chunks;
    DELETE FROM reading_comprehensive_tests;
    DELETE FROM reading_question_cache;
    DELETE FROM reading_cache_flush_log;
    DELETE FROM assignment_images;
    RAISE NOTICE 'Deleted reading data';
    
    -- 8. Delete classroom data
    DELETE FROM classroom_test_overrides;
    DELETE FROM classroom_test_schedules;
    DELETE FROM classroom_assignments;
    DELETE FROM classroom_students;
    RAISE NOTICE 'Deleted classroom data';
    
    -- 9. Delete content tables
    DELETE FROM vocabulary_lists;
    DELETE FROM vocabulary_chains;
    DELETE FROM reading_assignments;
    DELETE FROM classrooms;
    RAISE NOTICE 'Deleted content tables';
    
    -- 10. Delete OTP records
    DELETE FROM otps;
    RAISE NOTICE 'Deleted otps';
    
    -- 11. Delete all users except the admin
    DELETE FROM users WHERE id != admin_user_id;
    RAISE NOTICE 'Deleted all users except admin';
    
    RAISE NOTICE 'Database cleaned successfully. Admin user % preserved.', admin_user_id;
END $$;

-- Verify the cleanup
DO $$
DECLARE
    user_count INTEGER;
    whitelist_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO whitelist_count FROM email_whitelist;
    
    RAISE NOTICE 'Remaining users: %', user_count;
    RAISE NOTICE 'Email whitelist entries: %', whitelist_count;
END $$;

-- Commit the transaction
COMMIT;

-- Show summary of remaining data
SELECT 'Users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'Email Whitelist', COUNT(*) FROM email_whitelist
UNION ALL
SELECT 'Classrooms', COUNT(*) FROM classrooms
UNION ALL
SELECT 'Vocabulary Lists', COUNT(*) FROM vocabulary_lists
UNION ALL
SELECT 'Reading Assignments', COUNT(*) FROM reading_assignments
UNION ALL
SELECT 'Vocabulary Chains', COUNT(*) FROM vocabulary_chains
UNION ALL
SELECT 'Classroom Assignments', COUNT(*) FROM classroom_assignments
UNION ALL
SELECT 'Classroom Students', COUNT(*) FROM classroom_students
UNION ALL
SELECT 'OTPs', COUNT(*) FROM otps
ORDER BY table_name;