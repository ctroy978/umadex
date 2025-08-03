-- Add security fields to vocabulary_test_attempts table
ALTER TABLE vocabulary_test_attempts
ADD COLUMN IF NOT EXISTS security_violations JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS locked_reason TEXT;

-- Create table for vocabulary test security incidents
CREATE TABLE IF NOT EXISTS vocabulary_test_security_incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_vocabulary_test_security_incidents_attempt 
    ON vocabulary_test_security_incidents(test_attempt_id);
CREATE INDEX IF NOT EXISTS idx_vocabulary_test_security_incidents_type 
    ON vocabulary_test_security_incidents(incident_type);
CREATE INDEX IF NOT EXISTS idx_vocabulary_test_attempts_is_locked 
    ON vocabulary_test_attempts(is_locked);

-- Create table for teacher bypass codes (can be used for both regular tests and vocabulary tests)
-- Check if teacher_bypass_codes already exists before creating
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables 
                   WHERE table_schema = 'public' AND table_name = 'teacher_bypass_codes') THEN
        CREATE TABLE teacher_bypass_codes (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            code VARCHAR(10) NOT NULL UNIQUE,
            type VARCHAR(20) NOT NULL DEFAULT 'general',
            is_used BOOLEAN DEFAULT FALSE,
            used_at TIMESTAMPTZ,
            used_by UUID REFERENCES users(id),
            used_for_attempt_id UUID,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            
            CONSTRAINT teacher_bypass_codes_type_check CHECK (
                type IN ('general', 'vocabulary_test', 'regular_test')
            )
        );
        
        CREATE INDEX idx_teacher_bypass_codes_code ON teacher_bypass_codes(code);
        CREATE INDEX idx_teacher_bypass_codes_teacher ON teacher_bypass_codes(teacher_id);
        CREATE INDEX idx_teacher_bypass_codes_expires ON teacher_bypass_codes(expires_at);
    END IF;
END$$;

-- Enable Row Level Security
ALTER TABLE vocabulary_test_security_incidents ENABLE ROW LEVEL SECURITY;

-- Note: RLS policies would be added here if using Supabase auth
-- For now, security is handled at the application level

-- Add comment
COMMENT ON TABLE vocabulary_test_security_incidents IS 'Tracks security violations during vocabulary tests';
COMMENT ON COLUMN vocabulary_test_attempts.security_violations IS 'JSON array of security violation details';
COMMENT ON COLUMN vocabulary_test_attempts.is_locked IS 'Whether the test is locked due to security violations';
COMMENT ON COLUMN vocabulary_test_attempts.locked_at IS 'When the test was locked';
COMMENT ON COLUMN vocabulary_test_attempts.locked_reason IS 'Reason for locking the test';