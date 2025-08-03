-- Add supabase_auth_id column to users table for Supabase Auth integration
-- This column links local users to their Supabase Auth records

-- Add the column if it doesn't already exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'users' 
        AND column_name = 'supabase_auth_id'
    ) THEN
        ALTER TABLE users ADD COLUMN supabase_auth_id UUID;
    END IF;
END $$;

-- Create index for faster lookups by supabase_auth_id
CREATE INDEX IF NOT EXISTS idx_users_supabase_auth_id ON users(supabase_auth_id);

-- Add unique constraint to ensure one-to-one mapping
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE constraint_type = 'UNIQUE' 
        AND table_name = 'users' 
        AND constraint_name = 'users_supabase_auth_id_key'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_supabase_auth_id_key UNIQUE (supabase_auth_id);
    END IF;
END $$;

-- Comment for documentation
COMMENT ON COLUMN users.supabase_auth_id IS 'Links to auth.users.id in Supabase Auth';