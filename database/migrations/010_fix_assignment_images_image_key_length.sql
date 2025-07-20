-- Fix assignment_images image_key column length
-- Date: 2025-01-19
-- Issue: image_key was limited to 50 chars but we need 100 to match the SQLAlchemy model

ALTER TABLE assignment_images 
ALTER COLUMN image_key TYPE VARCHAR(100);

-- Add comment explaining the change
COMMENT ON COLUMN assignment_images.image_key IS 'Unique file identifier - format: {assignment_id}_{image_tag}_{timestamp}';