-- Database Cleanup Script (Safe Version)
-- This script removes all test data except the admin user (admin-csd8) and email whitelist

-- Start transaction
BEGIN;

-- Store the admin user ID for reference
DO $$
DECLARE
    admin_user_id UUID;
    table_exists BOOLEAN;
BEGIN
    -- Get the admin user ID
    SELECT id INTO admin_user_id FROM users WHERE username = 'admin-csd8';
    
    IF admin_user_id IS NULL THEN
        RAISE EXCEPTION 'Admin user admin-csd8 not found!';
    END IF;

    RAISE NOTICE 'Found admin user with ID: %', admin_user_id;

    -- Helper function to check if table exists
    -- Delete vocabulary chain data if tables exist
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vocabulary_chain_members'
    ) INTO table_exists;
    IF table_exists THEN
        DELETE FROM vocabulary_chain_members;
        RAISE NOTICE 'Deleted vocabulary_chain_members';
    END IF;

    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vocabulary_chains'
    ) INTO table_exists;
    IF table_exists THEN
        DELETE FROM vocabulary_chains;
        RAISE NOTICE 'Deleted vocabulary_chains';
    END IF;
    
    -- Delete vocabulary test data
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vocabulary_test_attempts'
    ) INTO table_exists;
    IF table_exists THEN
        DELETE FROM vocabulary_test_attempts;
        RAISE NOTICE 'Deleted vocabulary_test_attempts';
    END IF;

    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'vocabulary_test_configs'
    ) INTO table_exists;
    IF table_exists THEN
        DELETE FROM vocabulary_test_configs;
        RAISE NOTICE 'Deleted vocabulary_test_configs';
    END IF;
    
    -- Delete student vocabulary progress
    DELETE FROM student_vocabulary_progress;
    RAISE NOTICE 'Deleted student_vocabulary_progress';
    
    -- Delete vocabulary data
    DELETE FROM vocabulary_word_reviews;
    RAISE NOTICE 'Deleted vocabulary_word_reviews';
    
    DELETE FROM vocabulary_words;
    RAISE NOTICE 'Deleted vocabulary_words';
    
    DELETE FROM vocabulary_lists;
    RAISE NOTICE 'Deleted vocabulary_lists';
    
    -- Delete reading assignment data
    DELETE FROM reading_progress;
    RAISE NOTICE 'Deleted reading_progress';
    
    DELETE FROM reading_chunks;
    RAISE NOTICE 'Deleted reading_chunks';
    
    DELETE FROM assignment_images;
    RAISE NOTICE 'Deleted assignment_images';
    
    DELETE FROM reading_assignments;
    RAISE NOTICE 'Deleted reading_assignments';
    
    -- Delete classroom assignment data
    DELETE FROM classroom_assignments;
    RAISE NOTICE 'Deleted classroom_assignments';
    
    -- Delete classroom student data
    DELETE FROM classroom_students;
    RAISE NOTICE 'Deleted classroom_students';
    
    -- Delete all classrooms
    DELETE FROM classrooms;
    RAISE NOTICE 'Deleted classrooms';
    
    -- Delete all OTP records
    DELETE FROM otps;
    RAISE NOTICE 'Deleted otps';
    
    -- Delete all users except the admin
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
ORDER BY table_name;