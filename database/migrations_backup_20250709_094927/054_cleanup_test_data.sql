-- Database Cleanup Script
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

    -- Delete all vocabulary chain data
    DELETE FROM vocabulary_chain_members;
    DELETE FROM vocabulary_chains;
    
    -- Delete all vocabulary test data
    DELETE FROM vocabulary_test_attempts;
    DELETE FROM vocabulary_test_configs;
    
    -- Delete all vocabulary practice data
    DELETE FROM vocabulary_puzzle_progress;
    DELETE FROM vocabulary_puzzle_games;
    DELETE FROM vocabulary_story_progress;
    DELETE FROM vocabulary_story_prompts;
    DELETE FROM vocabulary_fill_in_blank_progress;
    DELETE FROM vocabulary_fill_in_blank_sentences;
    
    -- Delete all student vocabulary progress
    DELETE FROM student_vocabulary_progress;
    
    -- Delete all vocabulary data
    DELETE FROM vocabulary_word_reviews;
    DELETE FROM vocabulary_words;
    DELETE FROM vocabulary_lists;
    
    -- Delete all reading assignment data
    DELETE FROM reading_progress;
    DELETE FROM reading_chunks;
    DELETE FROM assignment_images;
    DELETE FROM reading_assignments;
    
    -- Delete all classroom assignment data
    DELETE FROM classroom_assignments;
    
    -- Delete all classroom student data
    DELETE FROM classroom_students;
    
    -- Delete all classrooms
    DELETE FROM classrooms;
    
    -- Delete all OTP records
    DELETE FROM otps;
    
    -- Delete all users except the admin
    DELETE FROM users WHERE id != admin_user_id;
    
    -- Reset sequences if needed (optional)
    -- This helps ensure clean IDs for new data
    
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
SELECT 'Vocabulary Chains', COUNT(*) FROM vocabulary_chains;