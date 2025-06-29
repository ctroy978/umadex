-- Add updated_at column to student_writing_submissions table
ALTER TABLE student_writing_submissions 
ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Update existing rows to have updated_at same as submitted_at
UPDATE student_writing_submissions 
SET updated_at = submitted_at 
WHERE updated_at IS NULL;