-- Add storage_path and public_url columns to lecture_images table
-- These columns are needed for Supabase storage integration

-- Add storage_path column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'lecture_images' 
                   AND column_name = 'storage_path') THEN
        ALTER TABLE lecture_images ADD COLUMN storage_path TEXT;
    END IF;
END $$;

-- Add public_url column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'lecture_images' 
                   AND column_name = 'public_url') THEN
        ALTER TABLE lecture_images ADD COLUMN public_url TEXT;
    END IF;
END $$;

-- Update existing rows to populate public_url from original_url if needed
UPDATE lecture_images 
SET public_url = original_url 
WHERE public_url IS NULL AND original_url IS NOT NULL;