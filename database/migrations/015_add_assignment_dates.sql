-- Add date fields to classroom_assignments table
ALTER TABLE classroom_assignments 
ADD COLUMN start_date TIMESTAMP WITH TIME ZONE,
ADD COLUMN end_date TIMESTAMP WITH TIME ZONE;

-- Add check constraint to ensure end date is after start date
ALTER TABLE classroom_assignments
ADD CONSTRAINT check_end_after_start 
CHECK (end_date IS NULL OR start_date IS NULL OR end_date > start_date);

-- Create index for date filtering performance
CREATE INDEX idx_classroom_assignments_dates 
ON classroom_assignments(classroom_id, start_date, end_date);