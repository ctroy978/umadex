-- ============================================================================
-- FIX TEST QUESTION EVALUATIONS TABLE
-- Adds missing columns that the application expects
-- ============================================================================

-- Add missing columns to test_question_evaluations table
ALTER TABLE test_question_evaluations 
ADD COLUMN IF NOT EXISTS question_number INTEGER NOT NULL DEFAULT 0;

ALTER TABLE test_question_evaluations 
ADD COLUMN IF NOT EXISTS question_text TEXT;

ALTER TABLE test_question_evaluations 
ADD COLUMN IF NOT EXISTS student_answer TEXT;

ALTER TABLE test_question_evaluations 
ADD COLUMN IF NOT EXISTS feedback_text TEXT;

-- Update existing feedback column name if it exists
DO $$ 
BEGIN
    -- Check if 'feedback' column exists and 'feedback_text' doesn't
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'test_question_evaluations' 
               AND column_name = 'feedback'
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name = 'test_question_evaluations' 
                              AND column_name = 'feedback_text')) THEN
        ALTER TABLE test_question_evaluations RENAME COLUMN feedback TO feedback_text;
    END IF;
END $$;

-- Add index on question_number for better query performance
CREATE INDEX IF NOT EXISTS idx_test_question_evaluations_question_number 
ON test_question_evaluations(test_attempt_id, question_number);

-- Add any missing columns to student_test_attempts if they don't exist
ALTER TABLE student_test_attempts 
ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMPTZ;

-- Update the check constraint on student_test_attempts status to include 'evaluated'
ALTER TABLE student_test_attempts DROP CONSTRAINT IF EXISTS check_test_attempt_status;
ALTER TABLE student_test_attempts ADD CONSTRAINT check_test_attempt_status 
CHECK (status IN ('in_progress', 'completed', 'submitted', 'graded', 'evaluated'));

-- Create a function to populate question_number from question_index if needed
CREATE OR REPLACE FUNCTION populate_question_number()
RETURNS void AS $$
BEGIN
    UPDATE test_question_evaluations 
    SET question_number = question_index + 1
    WHERE question_number = 0;
END;
$$ LANGUAGE plpgsql;

-- Call the function to populate question_number
SELECT populate_question_number();

-- Drop the function after use
DROP FUNCTION populate_question_number();

-- Add comment to clarify the columns
COMMENT ON COLUMN test_question_evaluations.question_index IS 'Zero-based index of the question';
COMMENT ON COLUMN test_question_evaluations.question_number IS 'One-based number of the question for display';
COMMENT ON COLUMN test_question_evaluations.question_text IS 'The actual question text';
COMMENT ON COLUMN test_question_evaluations.student_answer IS 'The student''s response to the question';
COMMENT ON COLUMN test_question_evaluations.feedback_text IS 'AI-generated feedback for the student';