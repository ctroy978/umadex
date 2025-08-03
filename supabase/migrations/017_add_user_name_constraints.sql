-- Migration: Add constraints to ensure user names are not empty
-- and fix any existing users with empty names

-- First, update any existing users with empty names
-- This query will set a temporary name based on their email for any users with empty names
UPDATE users 
SET 
    first_name = CASE 
        WHEN first_name IS NULL OR TRIM(first_name) = '' 
        THEN SPLIT_PART(email, '@', 1)
        ELSE first_name 
    END,
    last_name = CASE 
        WHEN last_name IS NULL OR TRIM(last_name) = '' 
        THEN 'User'
        ELSE last_name 
    END
WHERE 
    (first_name IS NULL OR TRIM(first_name) = '') 
    OR (last_name IS NULL OR TRIM(last_name) = '');

-- Add check constraints to ensure names are not empty
ALTER TABLE users 
    ADD CONSTRAINT check_first_name_not_empty 
    CHECK (first_name IS NOT NULL AND TRIM(first_name) != '');

ALTER TABLE users 
    ADD CONSTRAINT check_last_name_not_empty 
    CHECK (last_name IS NOT NULL AND TRIM(last_name) != '');