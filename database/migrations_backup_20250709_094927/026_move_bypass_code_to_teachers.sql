-- Move bypass code from classrooms to users (teachers)
-- First, add bypass code columns to users table
ALTER TABLE users
ADD COLUMN bypass_code VARCHAR(255),
ADD COLUMN bypass_code_updated_at TIMESTAMP WITH TIME ZONE;

-- Add index for teachers with bypass codes
CREATE INDEX idx_users_bypass_code ON users(id) WHERE bypass_code IS NOT NULL AND role = 'teacher';

-- Drop the columns from classrooms table
ALTER TABLE classrooms
DROP COLUMN IF EXISTS bypass_code,
DROP COLUMN IF EXISTS bypass_code_updated_at;

-- Drop the old index
DROP INDEX IF EXISTS idx_classrooms_bypass_code;

-- Add comments
COMMENT ON COLUMN users.bypass_code IS 'Hashed 4-digit bypass code for teacher to override AI evaluation across all their classrooms';
COMMENT ON COLUMN users.bypass_code_updated_at IS 'Timestamp when bypass code was last updated';