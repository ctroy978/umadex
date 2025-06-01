-- Add bypass code fields to classrooms table
ALTER TABLE classrooms
ADD COLUMN bypass_code VARCHAR(255),
ADD COLUMN bypass_code_updated_at TIMESTAMP WITH TIME ZONE;

-- Add index for bypass code lookups
CREATE INDEX idx_classrooms_bypass_code ON classrooms(id) WHERE bypass_code IS NOT NULL;

-- Add comment explaining the field
COMMENT ON COLUMN classrooms.bypass_code IS 'Hashed 4-digit bypass code for overriding AI evaluation in this classroom';
COMMENT ON COLUMN classrooms.bypass_code_updated_at IS 'Timestamp when bypass code was last updated';