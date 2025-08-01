-- Add storage_path column to assignment_images table for Supabase storage integration
ALTER TABLE assignment_images 
ADD COLUMN IF NOT EXISTS storage_path TEXT;

-- Comment on the column
COMMENT ON COLUMN assignment_images.storage_path IS 'Path to the image in Supabase Storage';