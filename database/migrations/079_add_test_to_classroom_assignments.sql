-- Add 'test' as a valid assignment type for classroom_assignments
-- This allows UMATest assignments to be attached to classrooms

-- First, normalize any UMALecture types to just 'lecture'
UPDATE classroom_assignments 
SET assignment_type = 'lecture' 
WHERE assignment_type = 'UMALecture';

-- Update the assignment type check constraint to include 'test'
ALTER TABLE classroom_assignments 
DROP CONSTRAINT IF EXISTS classroom_assignments_assignment_type_check;

ALTER TABLE classroom_assignments 
ADD CONSTRAINT classroom_assignments_assignment_type_check 
CHECK (assignment_type IN ('reading', 'vocabulary', 'debate', 'writing', 'lecture', 'test'));

-- Update the check_assignment_reference constraint to include test
ALTER TABLE classroom_assignments
DROP CONSTRAINT IF EXISTS check_assignment_reference;

ALTER TABLE classroom_assignments
ADD CONSTRAINT check_assignment_reference CHECK (
    (assignment_type = 'reading' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'vocabulary' AND assignment_id IS NULL AND vocabulary_list_id IS NOT NULL) OR
    (assignment_type = 'debate' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'writing' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'lecture' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'test' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL)
);

-- Create index for test assignments
CREATE INDEX IF NOT EXISTS idx_classroom_assignments_test 
ON classroom_assignments(assignment_id) 
WHERE assignment_type = 'test';

-- Update the comment to include test
COMMENT ON COLUMN classroom_assignments.assignment_type IS 'Type of assignment: reading, vocabulary, debate, writing, lecture, or test';