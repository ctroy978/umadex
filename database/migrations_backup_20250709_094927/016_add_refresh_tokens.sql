-- Add refresh tokens table for JWT refresh token system
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    device_info JSONB DEFAULT '{}',
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Create indexes for efficient queries
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash) WHERE revoked_at IS NULL;

-- Add RLS policies
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;

-- Users can only see their own refresh tokens
CREATE POLICY refresh_tokens_select ON refresh_tokens
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::UUID);

-- Users can only delete their own refresh tokens
CREATE POLICY refresh_tokens_delete ON refresh_tokens
    FOR DELETE
    USING (user_id = current_setting('app.current_user_id')::UUID);

-- Add token_type to user_sessions for backward compatibility during migration
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS token_type VARCHAR(20) DEFAULT 'session';

-- Create function to clean up expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
    -- Delete expired refresh tokens
    DELETE FROM refresh_tokens 
    WHERE expires_at < CURRENT_TIMESTAMP 
    OR revoked_at IS NOT NULL;
    
    -- Delete expired user sessions
    DELETE FROM user_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- Add comment on table
COMMENT ON TABLE refresh_tokens IS 'Stores refresh tokens for JWT authentication with automatic refresh capability';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'SHA-256 hash of the actual refresh token for security';
COMMENT ON COLUMN refresh_tokens.device_info IS 'Optional JSON data about the device/browser used for this session';
COMMENT ON COLUMN refresh_tokens.revoked_at IS 'Timestamp when token was revoked, NULL if still valid';