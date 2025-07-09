-- Update classroom_assignments table to support debate assignments

-- First, drop the existing check constraint
ALTER TABLE classroom_assignments
DROP CONSTRAINT check_assignment_reference;

-- Add new check constraint that includes debate type
ALTER TABLE classroom_assignments
ADD CONSTRAINT check_assignment_reference CHECK (
    (assignment_type = 'reading' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'vocabulary' AND assignment_id IS NULL AND vocabulary_list_id IS NOT NULL) OR
    (assignment_type = 'debate' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL)
);

-- Since debate assignments use the assignment_id column (like reading assignments),
-- we need to ensure the foreign key can reference both reading_assignments and debate_assignments
-- However, PostgreSQL doesn't support conditional foreign keys, so we'll handle this at the application level

-- Add an index for debate assignments
CREATE INDEX idx_classroom_assignments_debate ON classroom_assignments(assignment_id) 
WHERE assignment_type = 'debate';

-- Update the comment to include debate
COMMENT ON COLUMN classroom_assignments.assignment_type IS 'Type of assignment: reading, vocabulary, or debate';