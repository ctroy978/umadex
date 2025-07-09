-- Update assignment_images table to support three image versions and image tags
ALTER TABLE assignment_images
    ADD COLUMN IF NOT EXISTS image_tag VARCHAR(50),
    ADD COLUMN IF NOT EXISTS original_url TEXT,
    ADD COLUMN IF NOT EXISTS display_url TEXT,
    ADD COLUMN IF NOT EXISTS thumbnail_url TEXT,
    ADD COLUMN IF NOT EXISTS file_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS image_url TEXT,
    ADD COLUMN IF NOT EXISTS width INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS height INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();

-- Update existing data to match new schema using a CTE
WITH numbered_images AS (
    SELECT 
        id,
        ROW_NUMBER() OVER (PARTITION BY assignment_id ORDER BY uploaded_at) as row_num
    FROM assignment_images
    WHERE image_tag IS NULL
)
UPDATE assignment_images 
SET 
    image_tag = CONCAT('image-', ni.row_num),
    original_url = COALESCE(file_url, ''),
    display_url = COALESCE(file_url, ''),
    image_url = COALESCE(file_url, ''),
    thumbnail_url = COALESCE(file_url, ''),
    width = 0,
    height = 0
FROM numbered_images ni
WHERE assignment_images.id = ni.id;

-- Add unique constraint for image tags per assignment (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'unique_assignment_image_tag') THEN
        ALTER TABLE assignment_images
            ADD CONSTRAINT unique_assignment_image_tag UNIQUE(assignment_id, image_tag);
    END IF;
END $$;