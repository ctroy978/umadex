-- Migration 038: Add database functions and views for active (non-deleted) users
-- This migration creates helper functions and views to ensure soft deleted users
-- are properly excluded from queries throughout the application.

-- =====================================================
-- STEP 1: Create a view for active users only
-- =====================================================

CREATE OR REPLACE VIEW active_users AS
SELECT * FROM users WHERE deleted_at IS NULL;

-- Add comment
COMMENT ON VIEW active_users IS 'View showing only non-deleted (active) users. Use this instead of direct users table queries to automatically exclude soft deleted users.';

-- =====================================================
-- STEP 2: Create helper functions for common user queries
-- =====================================================

-- Function to check if a user is active (not soft deleted)
CREATE OR REPLACE FUNCTION is_user_active(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users 
        WHERE id = user_uuid AND deleted_at IS NULL
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get active user by email
CREATE OR REPLACE FUNCTION get_active_user_by_email(user_email TEXT)
RETURNS TABLE(
    id UUID,
    email TEXT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    username VARCHAR(50),
    role VARCHAR(20),
    is_admin BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.email, u.first_name, u.last_name, u.username, 
           u.role, u.is_admin, u.created_at, u.updated_at
    FROM users u
    WHERE u.email = user_email AND u.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to get active user by ID
CREATE OR REPLACE FUNCTION get_active_user_by_id(user_uuid UUID)
RETURNS TABLE(
    id UUID,
    email TEXT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    username VARCHAR(50),
    role VARCHAR(20),
    is_admin BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.email, u.first_name, u.last_name, u.username, 
           u.role, u.is_admin, u.created_at, u.updated_at
    FROM users u
    WHERE u.id = user_uuid AND u.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- STEP 3: Add RLS policies to enforce soft delete filtering
-- =====================================================

-- Enable RLS on users table if not already enabled
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy to automatically exclude soft deleted users for non-admin operations
CREATE POLICY users_exclude_deleted ON users
    FOR SELECT
    USING (
        deleted_at IS NULL OR 
        current_setting('app.is_admin', true)::boolean = true OR
        current_setting('app.current_user_id', true) = id::text
    );

-- Allow admins to see all users (including deleted) in admin operations
CREATE POLICY users_admin_access ON users
    FOR ALL
    TO PUBLIC
    USING (
        current_setting('app.is_admin', true)::boolean = true OR
        deleted_at IS NULL
    );

-- =====================================================
-- STEP 4: Add comments and documentation
-- =====================================================

COMMENT ON FUNCTION is_user_active(UUID) IS 'Check if a user is active (not soft deleted). Returns false for deleted users.';
COMMENT ON FUNCTION get_active_user_by_email(TEXT) IS 'Get user by email, excluding soft deleted users. Returns empty result for deleted users.';
COMMENT ON FUNCTION get_active_user_by_id(UUID) IS 'Get user by ID, excluding soft deleted users. Returns empty result for deleted users.';

-- =====================================================
-- STEP 5: Create indexes for performance
-- =====================================================

-- Index for active users queries
CREATE INDEX IF NOT EXISTS idx_users_active ON users(id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_active_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_active_role ON users(role) WHERE deleted_at IS NULL;

-- =====================================================
-- STEP 6: Migration completion
-- =====================================================

-- Log the migration completion
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations') THEN
        INSERT INTO schema_migrations (version, applied_at) 
        VALUES ('038', NOW()) 
        ON CONFLICT (version) DO NOTHING;
    END IF;
END $$;

-- Add comment
COMMENT ON SCHEMA public IS 'Added active_users view and helper functions to automatically exclude soft deleted users from queries';