-- Fix assignment_images file_url nullable constraint
-- Date: 2025-01-19

-- Make file_url nullable to match the SQLAlchemy model
ALTER TABLE assignment_images 
ALTER COLUMN file_url DROP NOT NULL;

-- Fix column length mismatch between display_url and thumbnail_url
-- Increase from 500 to 1000 characters to match file_url
ALTER TABLE assignment_images 
ALTER COLUMN display_url TYPE VARCHAR(1000);

ALTER TABLE assignment_images 
ALTER COLUMN thumbnail_url TYPE VARCHAR(1000);

-- Add comment explaining the change
COMMENT ON COLUMN assignment_images.file_url IS 'Optional file URL - may be null if only display and thumbnail versions exist';