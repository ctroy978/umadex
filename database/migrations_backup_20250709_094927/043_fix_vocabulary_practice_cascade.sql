-- Fix vocabulary practice progress foreign key to allow cascade deletion
-- This migration fixes the issue where vocabulary assignments cannot be deleted
-- due to foreign key constraints from vocabulary_practice_progress table

-- Drop the existing foreign key constraint
ALTER TABLE vocabulary_practice_progress
DROP CONSTRAINT vocabulary_practice_progress_classroom_assignment_id_fkey;

-- Add the foreign key back with CASCADE DELETE
ALTER TABLE vocabulary_practice_progress
ADD CONSTRAINT vocabulary_practice_progress_classroom_assignment_id_fkey
FOREIGN KEY (classroom_assignment_id) 
REFERENCES classroom_assignments(id) 
ON DELETE CASCADE;

-- Also check and fix vocabulary_game_attempts if needed
-- This table references vocabulary_practice_progress which should cascade properly
ALTER TABLE vocabulary_game_attempts
DROP CONSTRAINT IF EXISTS vocabulary_game_attempts_practice_progress_id_fkey;

ALTER TABLE vocabulary_game_attempts
ADD CONSTRAINT vocabulary_game_attempts_practice_progress_id_fkey
FOREIGN KEY (practice_progress_id)
REFERENCES vocabulary_practice_progress(id)
ON DELETE CASCADE;