-- Ensure vocabulary test security columns and tables exist
-- This migration ensures persistence through database resets

-- Add security fields to vocabulary_test_attempts table if they don't exist
ALTER TABLE vocabulary_test_attempts
ADD COLUMN IF NOT EXISTS security_violations JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS locked_reason TEXT;

-- Create table for vocabulary test security incidents if it doesn't exist
CREATE TABLE IF NOT EXISTS vocabulary_test_security_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_attempt_id UUID NOT NULL REFERENCES vocabulary_test_attempts(id) ON DELETE CASCADE,
    incident_type VARCHAR(50) NOT NULL,
    incident_data JSONB,
    resulted_in_lock BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Index for lookups
    CONSTRAINT vocabulary_test_security_incidents_type_check CHECK (
        incident_type IN ('focus_loss', 'tab_switch', 'navigation_attempt', 
                         'window_blur', 'app_switch', 'orientation_cheat')
    )
);

-- Create indexes for performance if they don't exist
CREATE INDEX IF NOT EXISTS idx_vocabulary_test_security_incidents_attempt 
    ON vocabulary_test_security_incidents(test_attempt_id);
CREATE INDEX IF NOT EXISTS idx_vocabulary_test_security_incidents_type 
    ON vocabulary_test_security_incidents(incident_type);
CREATE INDEX IF NOT EXISTS idx_vocabulary_test_attempts_is_locked 
    ON vocabulary_test_attempts(is_locked);

-- Enable Row Level Security
ALTER TABLE vocabulary_test_security_incidents ENABLE ROW LEVEL SECURITY;

-- Add comments
COMMENT ON TABLE vocabulary_test_security_incidents IS 'Tracks security violations during vocabulary tests';
COMMENT ON COLUMN vocabulary_test_attempts.security_violations IS 'JSON array of security violation details';
COMMENT ON COLUMN vocabulary_test_attempts.is_locked IS 'Whether the test is locked due to security violations';
COMMENT ON COLUMN vocabulary_test_attempts.locked_at IS 'When the test was locked';
COMMENT ON COLUMN vocabulary_test_attempts.locked_reason IS 'Reason for locking the test';