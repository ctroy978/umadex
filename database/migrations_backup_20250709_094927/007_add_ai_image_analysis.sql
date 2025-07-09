-- Add AI description fields to assignment_images table
ALTER TABLE assignment_images 
ADD COLUMN ai_description TEXT,
ADD COLUMN description_generated_at TIMESTAMP;

-- Add processing status to assignments
ALTER TABLE reading_assignments 
ADD COLUMN images_processed BOOLEAN DEFAULT FALSE;

-- Add index for faster queries on processing status
CREATE INDEX idx_reading_assignments_images_processed ON reading_assignments(images_processed);