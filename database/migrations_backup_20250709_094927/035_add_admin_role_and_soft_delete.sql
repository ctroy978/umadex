-- Add soft delete fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES users(id) DEFAULT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deletion_reason TEXT DEFAULT NULL;

-- Create index for soft delete queries
CREATE INDEX idx_users_deleted_at ON users(deleted_at);

-- Create role changes audit table
CREATE TABLE IF NOT EXISTS role_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_role user_role NOT NULL,
    to_role user_role NOT NULL,
    from_admin BOOLEAN NOT NULL DEFAULT FALSE,
    to_admin BOOLEAN NOT NULL DEFAULT FALSE,
    changed_by UUID NOT NULL REFERENCES users(id),
    change_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for role changes
CREATE INDEX idx_role_changes_user_id ON role_changes(user_id);
CREATE INDEX idx_role_changes_changed_by ON role_changes(changed_by);
CREATE INDEX idx_role_changes_created_at ON role_changes(created_at);

-- Create user deletions audit table
CREATE TABLE IF NOT EXISTS user_deletions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    user_role user_role NOT NULL,
    was_admin BOOLEAN NOT NULL DEFAULT FALSE,
    deletion_type VARCHAR(20) NOT NULL CHECK (deletion_type IN ('soft', 'hard')),
    deletion_reason TEXT NOT NULL,
    deleted_by UUID NOT NULL REFERENCES users(id),
    affected_classrooms INTEGER DEFAULT 0,
    affected_assignments INTEGER DEFAULT 0,
    affected_students INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for user deletions
CREATE INDEX idx_user_deletions_user_id ON user_deletions(user_id);
CREATE INDEX idx_user_deletions_deleted_by ON user_deletions(deleted_by);
CREATE INDEX idx_user_deletions_deletion_type ON user_deletions(deletion_type);
CREATE INDEX idx_user_deletions_created_at ON user_deletions(created_at);

-- Create admin actions audit table for general admin activities
CREATE TABLE IF NOT EXISTS admin_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES users(id),
    action_type VARCHAR(50) NOT NULL,
    target_id UUID,
    target_type VARCHAR(50),
    action_data JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for admin actions
CREATE INDEX idx_admin_actions_admin_id ON admin_actions(admin_id);
CREATE INDEX idx_admin_actions_action_type ON admin_actions(action_type);
CREATE INDEX idx_admin_actions_created_at ON admin_actions(created_at);

-- Update all existing views and functions to filter out soft-deleted users
-- Create a view for active users
CREATE OR REPLACE VIEW active_users AS
SELECT * FROM users WHERE deleted_at IS NULL;

-- Update RLS policies to handle soft deletes
-- Drop existing policies if any
DROP POLICY IF EXISTS users_select ON users;
DROP POLICY IF EXISTS users_update ON users;

-- Create new policies that respect soft delete
CREATE POLICY users_select ON users
    FOR SELECT
    USING (
        -- Admins can see all users including soft deleted
        (current_setting('app.is_admin', true)::BOOLEAN = true) OR
        -- Regular users can only see active users
        (deleted_at IS NULL AND (
            id = current_setting('app.current_user_id', true)::UUID OR
            current_setting('app.is_admin', true)::BOOLEAN = true
        ))
    );

CREATE POLICY users_update ON users
    FOR UPDATE
    USING (
        -- Only admins can update users
        current_setting('app.is_admin', true)::BOOLEAN = true OR
        -- Users can update their own profile if not deleted
        (id = current_setting('app.current_user_id', true)::UUID AND deleted_at IS NULL)
    );

-- Add RLS to new tables
ALTER TABLE role_changes ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_deletions ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_actions ENABLE ROW LEVEL SECURITY;

-- Only admins can view audit tables
CREATE POLICY role_changes_select ON role_changes
    FOR SELECT
    USING (current_setting('app.is_admin', true)::BOOLEAN = true);

CREATE POLICY user_deletions_select ON user_deletions
    FOR SELECT
    USING (current_setting('app.is_admin', true)::BOOLEAN = true);

CREATE POLICY admin_actions_select ON admin_actions
    FOR SELECT
    USING (current_setting('app.is_admin', true)::BOOLEAN = true);

-- Function to safely soft delete a user
CREATE OR REPLACE FUNCTION soft_delete_user(
    p_user_id UUID,
    p_deleted_by UUID,
    p_reason TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_user_role user_role;
    v_was_admin BOOLEAN;
    v_affected_classrooms INTEGER;
    v_affected_assignments INTEGER;
    v_affected_students INTEGER;
BEGIN
    -- Get user info before deletion
    SELECT role, is_admin 
    INTO v_user_role, v_was_admin
    FROM users 
    WHERE id = p_user_id AND deleted_at IS NULL;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Calculate impact for teachers
    IF v_user_role = 'teacher' THEN
        SELECT COUNT(DISTINCT c.id) INTO v_affected_classrooms
        FROM classrooms c
        WHERE c.teacher_id = p_user_id;
        
        SELECT COUNT(DISTINCT a.id) INTO v_affected_assignments
        FROM reading_assignments a
        WHERE a.teacher_id = p_user_id;
        
        SELECT COUNT(DISTINCT cs.student_id) INTO v_affected_students
        FROM classroom_students cs
        JOIN classrooms c ON cs.classroom_id = c.id
        WHERE c.teacher_id = p_user_id;
    END IF;
    
    -- Perform soft delete
    UPDATE users 
    SET deleted_at = CURRENT_TIMESTAMP,
        deleted_by = p_deleted_by,
        deletion_reason = p_reason
    WHERE id = p_user_id;
    
    -- Log the deletion
    INSERT INTO user_deletions (
        user_id, user_email, user_name, user_role, was_admin,
        deletion_type, deletion_reason, deleted_by,
        affected_classrooms, affected_assignments, affected_students
    )
    SELECT 
        u.id, u.email, u.first_name || ' ' || u.last_name,
        u.role, u.is_admin, 'soft', p_reason, p_deleted_by,
        COALESCE(v_affected_classrooms, 0),
        COALESCE(v_affected_assignments, 0),
        COALESCE(v_affected_students, 0)
    FROM users u
    WHERE u.id = p_user_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to restore a soft-deleted user
CREATE OR REPLACE FUNCTION restore_user(
    p_user_id UUID,
    p_restored_by UUID
) RETURNS BOOLEAN AS $$
BEGIN
    -- Check if user is soft deleted
    IF NOT EXISTS (
        SELECT 1 FROM users 
        WHERE id = p_user_id AND deleted_at IS NOT NULL
    ) THEN
        RETURN FALSE;
    END IF;
    
    -- Restore user
    UPDATE users 
    SET deleted_at = NULL,
        deleted_by = NULL,
        deletion_reason = NULL
    WHERE id = p_user_id;
    
    -- Log the restoration
    INSERT INTO admin_actions (
        admin_id, action_type, target_id, target_type,
        action_data
    ) VALUES (
        p_restored_by, 'user_restored', p_user_id, 'user',
        jsonb_build_object('restored_at', CURRENT_TIMESTAMP)
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to promote user role
CREATE OR REPLACE FUNCTION promote_user_role(
    p_user_id UUID,
    p_new_role user_role,
    p_new_is_admin BOOLEAN,
    p_promoted_by UUID,
    p_reason TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_old_role user_role;
    v_old_is_admin BOOLEAN;
BEGIN
    -- Get current role
    SELECT role, is_admin 
    INTO v_old_role, v_old_is_admin
    FROM users 
    WHERE id = p_user_id AND deleted_at IS NULL;
    
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Update user role
    UPDATE users 
    SET role = p_new_role,
        is_admin = p_new_is_admin,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = p_user_id;
    
    -- Log the role change
    INSERT INTO role_changes (
        user_id, from_role, to_role, from_admin, to_admin,
        changed_by, change_reason
    ) VALUES (
        p_user_id, v_old_role, p_new_role, v_old_is_admin, p_new_is_admin,
        p_promoted_by, p_reason
    );
    
    -- Log admin action
    INSERT INTO admin_actions (
        admin_id, action_type, target_id, target_type,
        action_data
    ) VALUES (
        p_promoted_by, 'role_change', p_user_id, 'user',
        jsonb_build_object(
            'from_role', v_old_role,
            'to_role', p_new_role,
            'from_admin', v_old_is_admin,
            'to_admin', p_new_is_admin,
            'reason', p_reason
        )
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add comments
COMMENT ON TABLE role_changes IS 'Audit log of all user role changes';
COMMENT ON TABLE user_deletions IS 'Audit log of all user deletions with impact analysis';
COMMENT ON TABLE admin_actions IS 'General audit log for all admin actions';
COMMENT ON COLUMN users.deleted_at IS 'Timestamp when user was soft deleted';
COMMENT ON COLUMN users.deleted_by IS 'Admin who soft deleted this user';
COMMENT ON COLUMN users.deletion_reason IS 'Reason for soft deletion';