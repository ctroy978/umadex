-- Update teacher_bypass_codes table to be more generic for all UMA apps
-- Remove the specific test_attempt_id constraint and make it more flexible

-- First, drop the existing constraint
ALTER TABLE teacher_bypass_codes 
DROP CONSTRAINT IF EXISTS unique_active_code_per_attempt;

-- Add new columns for flexible usage
ALTER TABLE teacher_bypass_codes
ADD COLUMN IF NOT EXISTS context_type VARCHAR(50) DEFAULT 'test',
ADD COLUMN IF NOT EXISTS context_id UUID, -- Can be test_attempt_id, assignment_id, etc.
ADD COLUMN IF NOT EXISTS student_id UUID REFERENCES users(id);

-- Migrate existing data
UPDATE teacher_bypass_codes 
SET context_type = 'test', 
    context_id = test_attempt_id
WHERE test_attempt_id IS NOT NULL;

-- Now we can drop the old column
ALTER TABLE teacher_bypass_codes 
DROP COLUMN IF EXISTS test_attempt_id;

-- Add new constraint for one active code per context
ALTER TABLE teacher_bypass_codes
ADD CONSTRAINT unique_active_code_per_context 
UNIQUE(teacher_id, context_type, context_id, student_id, used_at) DEFERRABLE;

-- Update index for bypass code lookup
DROP INDEX IF EXISTS idx_bypass_code_lookup;
CREATE INDEX idx_bypass_code_lookup ON teacher_bypass_codes(bypass_code, expires_at) 
WHERE used_at IS NULL;

-- Add index for teacher lookup
CREATE INDEX idx_teacher_bypass_codes ON teacher_bypass_codes(teacher_id, created_at DESC);