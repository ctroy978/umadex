-- Add soft delete functionality to reading_assignments
ALTER TABLE reading_assignments 
ADD COLUMN deleted_at TIMESTAMP;

-- Create index for performance when filtering deleted assignments
CREATE INDEX idx_reading_assignments_deleted_at ON reading_assignments(deleted_at);

-- Update views or add comments for clarity
COMMENT ON COLUMN reading_assignments.deleted_at IS 'Timestamp when assignment was soft deleted, NULL if active';