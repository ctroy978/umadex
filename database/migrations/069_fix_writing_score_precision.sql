-- Fix the score field precision to handle percentage scores (0-125)
-- Change from DECIMAL(3,2) which only allows up to 9.99 
-- to DECIMAL(5,2) which allows up to 999.99

ALTER TABLE student_writing_submissions
ALTER COLUMN score TYPE DECIMAL(5,2);

-- Update the check constraint to allow scores up to 125% (with bonus points)
ALTER TABLE student_writing_submissions 
DROP CONSTRAINT IF EXISTS check_score_range;

ALTER TABLE student_writing_submissions 
ADD CONSTRAINT check_score_range 
CHECK (score IS NULL OR (score >= 0 AND score <= 125));

-- Add comment to clarify the field usage
COMMENT ON COLUMN student_writing_submissions.score IS 'Percentage score from 0.00 to 125.00 (includes up to 25 bonus points)';