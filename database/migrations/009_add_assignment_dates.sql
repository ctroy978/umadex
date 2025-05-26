-- Add start_date and end_date columns to reading_assignments table
ALTER TABLE reading_assignments 
ADD COLUMN start_date TIMESTAMP WITH TIME ZONE DEFAULT NULL,
ADD COLUMN end_date TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add check constraint to ensure end_date is after start_date
ALTER TABLE reading_assignments 
ADD CONSTRAINT check_date_order CHECK (
  (start_date IS NULL OR end_date IS NULL) OR 
  (end_date > start_date)
);

-- Create indexes for better query performance on date filtering
CREATE INDEX idx_reading_assignments_start_date ON reading_assignments(start_date) WHERE start_date IS NOT NULL;
CREATE INDEX idx_reading_assignments_end_date ON reading_assignments(end_date) WHERE end_date IS NOT NULL;