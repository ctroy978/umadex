-- Add teacher_bypass_codes table for one-time bypass functionality
CREATE TABLE IF NOT EXISTS teacher_bypass_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    context_type VARCHAR(50) DEFAULT 'test',
    context_id UUID,
    student_id UUID REFERENCES users(id) ON DELETE SET NULL,
    bypass_code VARCHAR(8) NOT NULL,
    used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    CONSTRAINT idx_teacher_bypass_codes_teacher_id_idx FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT idx_teacher_bypass_codes_student_id_idx FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_teacher_bypass_codes_teacher_id ON teacher_bypass_codes(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_bypass_codes_student_id ON teacher_bypass_codes(student_id);
CREATE INDEX IF NOT EXISTS idx_teacher_bypass_codes_bypass_code ON teacher_bypass_codes(bypass_code);
CREATE INDEX IF NOT EXISTS idx_teacher_bypass_codes_expires_at ON teacher_bypass_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_teacher_bypass_codes_used_at ON teacher_bypass_codes(used_at);