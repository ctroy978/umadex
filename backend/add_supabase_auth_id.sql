-- Add supabase_auth_id column to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS supabase_auth_id UUID UNIQUE;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_supabase_auth_id 
ON users(supabase_auth_id) 
WHERE supabase_auth_id IS NOT NULL;