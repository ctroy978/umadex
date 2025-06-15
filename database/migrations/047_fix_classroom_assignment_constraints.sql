-- Fix classroom assignment constraints to prevent duplicates
-- This migration removes the old constraint and adds separate constraints
-- for reading and vocabulary assignments

-- Drop the old constraint that allows duplicates for vocabulary assignments
ALTER TABLE classroom_assignments 
DROP CONSTRAINT IF EXISTS _classroom_assignment_uc;

-- Add constraint for reading assignments (classroom_id + assignment_id must be unique)
ALTER TABLE classroom_assignments 
ADD CONSTRAINT _classroom_reading_assignment_uc 
UNIQUE (classroom_id, assignment_id);

-- Add constraint for vocabulary assignments (classroom_id + vocabulary_list_id + assignment_type must be unique)
ALTER TABLE classroom_assignments 
ADD CONSTRAINT _classroom_vocab_assignment_uc 
UNIQUE (classroom_id, vocabulary_list_id, assignment_type);

-- Clean up any existing duplicate vocabulary assignments before applying constraint
-- Keep only the first occurrence of duplicates
WITH duplicates AS (
    SELECT id, 
           ROW_NUMBER() OVER (
               PARTITION BY classroom_id, vocabulary_list_id, assignment_type 
               ORDER BY assigned_at, id
           ) as row_num
    FROM classroom_assignments 
    WHERE assignment_type = 'vocabulary'
)
DELETE FROM classroom_assignments 
WHERE id IN (
    SELECT id FROM duplicates WHERE row_num > 1
);