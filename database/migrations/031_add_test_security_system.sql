-- Add security columns to student_test_attempts
ALTER TABLE student_test_attempts 
ADD COLUMN security_violations JSONB DEFAULT '[]',
ADD COLUMN is_locked BOOLEAN DEFAULT FALSE,
ADD COLUMN locked_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN locked_reason VARCHAR(255);

-- Teacher bypass codes table
CREATE TABLE teacher_bypass_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id),
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id),
    bypass_code VARCHAR(8) NOT NULL, -- 8-character alphanumeric code
    used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Only one active code per test attempt
    CONSTRAINT unique_active_code_per_attempt UNIQUE(test_attempt_id, used_at) DEFERRABLE
);

-- Create index for bypass code lookup
CREATE INDEX idx_bypass_code_lookup ON teacher_bypass_codes(bypass_code, expires_at) WHERE used_at IS NULL;

-- Security incident logging
CREATE TABLE test_security_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id),
    student_id UUID NOT NULL REFERENCES users(id),
    incident_type VARCHAR(50) NOT NULL 
        CHECK (incident_type IN ('focus_loss', 'tab_switch', 'navigation_attempt', 'window_blur', 'app_switch', 'orientation_cheat')),
    incident_data JSONB, -- Browser info, timestamp, etc.
    resulted_in_lock BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for security incident queries
CREATE INDEX idx_security_incidents_test_attempt ON test_security_incidents(test_attempt_id);
CREATE INDEX idx_security_incidents_student ON test_security_incidents(student_id);
CREATE INDEX idx_security_incidents_created ON test_security_incidents(created_at);