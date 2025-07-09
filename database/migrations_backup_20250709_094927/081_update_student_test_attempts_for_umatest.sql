-- Update student_test_attempts to support both UMARead and UMATest
-- This migration adds classroom_assignment_id for better tracking

-- Add classroom_assignment_id column
ALTER TABLE student_test_attempts 
ADD COLUMN IF NOT EXISTS classroom_assignment_id INTEGER REFERENCES classroom_assignments(id);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_student_test_attempts_classroom_assignment 
ON student_test_attempts(classroom_assignment_id) 
WHERE classroom_assignment_id IS NOT NULL;

-- Add composite index for UMATest lookups
CREATE INDEX IF NOT EXISTS idx_student_test_attempts_umatest 
ON student_test_attempts(student_id, classroom_assignment_id, test_id) 
WHERE test_id IS NOT NULL;

-- Update existing constraint to be more flexible
ALTER TABLE student_test_attempts 
DROP CONSTRAINT IF EXISTS check_test_reference;

ALTER TABLE student_test_attempts 
ADD CONSTRAINT check_test_reference CHECK (
    -- UMARead test: needs assignment_test_id and assignment_id
    (assignment_test_id IS NOT NULL AND assignment_id IS NOT NULL AND test_id IS NULL) OR 
    -- UMATest: needs test_id and classroom_assignment_id
    (assignment_test_id IS NULL AND test_id IS NOT NULL AND classroom_assignment_id IS NOT NULL)
);

COMMENT ON COLUMN student_test_attempts.classroom_assignment_id IS 'Reference to classroom assignment (for UMATest)';