-- Add missing vocab_settings and vocab_practice_settings columns to classroom_assignments table
-- These columns are needed for vocabulary assignment configuration

-- Add vocab_settings column
ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS vocab_settings JSONB DEFAULT '{}' NOT NULL;

-- Add vocab_practice_settings column with default values
ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS vocab_practice_settings JSONB DEFAULT '{
    "practice_required": true,
    "assignments_to_complete": 3,
    "allow_retakes": true,
    "show_explanations": true
}' NOT NULL;

-- Add removed_from_classroom_at and removed_by columns for soft delete functionality
ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS removed_from_classroom_at TIMESTAMPTZ;

ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS removed_by UUID REFERENCES users(id);

-- Create index for faster queries on removed items
CREATE INDEX IF NOT EXISTS idx_classroom_assignments_removed 
ON classroom_assignments(removed_from_classroom_at) 
WHERE removed_from_classroom_at IS NOT NULL;