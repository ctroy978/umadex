-- Fix writing score precision to support percentage scores (0-100) with bonus points (up to 125)
-- Previous schema limited scores to 0-10, causing numeric overflow errors

-- Drop the existing check constraint
ALTER TABLE student_writing_submissions 
DROP CONSTRAINT IF EXISTS student_writing_submissions_score_check;

-- Alter the score column to support larger values
ALTER TABLE student_writing_submissions 
ALTER COLUMN score TYPE DECIMAL(5,2);

-- Add new check constraint to ensure scores are within valid range (0-125)
ALTER TABLE student_writing_submissions 
ADD CONSTRAINT student_writing_submissions_score_check 
CHECK (score IS NULL OR (score >= 0 AND score <= 125));

-- Add comment to document the column
COMMENT ON COLUMN student_writing_submissions.score IS 'Writing submission score as percentage (0-100) with possible bonus points up to 125';