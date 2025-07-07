-- Add test_id column to student_test_attempts for UMATest support
-- This allows StudentTestAttempt to be used for both UMARead tests (via assignment_test_id)
-- and UMATest tests (via test_id)

ALTER TABLE student_test_attempts 
ADD COLUMN IF NOT EXISTS test_id UUID REFERENCES test_assignments(id);

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_student_test_attempts_test_id 
ON student_test_attempts(test_id) 
WHERE test_id IS NOT NULL;

-- Update the constraint to make either assignment_test_id or test_id required (but not both)
ALTER TABLE student_test_attempts 
DROP CONSTRAINT IF EXISTS check_test_reference;

ALTER TABLE student_test_attempts 
ADD CONSTRAINT check_test_reference CHECK (
    (assignment_test_id IS NOT NULL AND test_id IS NULL) OR 
    (assignment_test_id IS NULL AND test_id IS NOT NULL)
);

COMMENT ON COLUMN student_test_attempts.test_id IS 'Reference to UMATest assignment (test_assignments table)';