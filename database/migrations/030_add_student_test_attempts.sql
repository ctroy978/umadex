-- Migration: Add student test attempts tracking
-- This table tracks student progress and answers for UMARead tests

CREATE TABLE IF NOT EXISTS student_test_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_test_id UUID NOT NULL REFERENCES assignment_tests(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    
    -- Progress tracking
    current_question INTEGER DEFAULT 1,
    answers_data JSONB DEFAULT '{}', -- {question_id: answer_text}
    status VARCHAR(50) DEFAULT 'in_progress' 
        CHECK (status IN ('in_progress', 'completed', 'submitted', 'graded')),
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER DEFAULT 0,
    
    -- Results (populated after grading)
    score DECIMAL(5,2),
    passed BOOLEAN,
    feedback JSONB, -- Detailed feedback per question
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_student_test UNIQUE(student_id, assignment_test_id)
);

-- Create indexes for performance
CREATE INDEX idx_test_attempts_student ON student_test_attempts(student_id);
CREATE INDEX idx_test_attempts_assignment ON student_test_attempts(assignment_id);
CREATE INDEX idx_test_attempts_status ON student_test_attempts(status);

-- Add RLS policies
ALTER TABLE student_test_attempts ENABLE ROW LEVEL SECURITY;

-- Students can only see their own test attempts
CREATE POLICY student_test_attempts_student_select ON student_test_attempts
    FOR SELECT
    TO authenticated
    USING (student_id = auth.uid()::uuid);

-- Students can insert their own test attempts
CREATE POLICY student_test_attempts_student_insert ON student_test_attempts
    FOR INSERT
    TO authenticated
    WITH CHECK (student_id = auth.uid()::uuid);

-- Students can update their own in-progress tests
CREATE POLICY student_test_attempts_student_update ON student_test_attempts
    FOR UPDATE
    TO authenticated
    USING (student_id = auth.uid()::uuid AND status = 'in_progress')
    WITH CHECK (student_id = auth.uid()::uuid);

-- Teachers can view test attempts for their students
CREATE POLICY student_test_attempts_teacher_select ON student_test_attempts
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = auth.uid()::uuid
            AND u.role = 'teacher'
        )
        AND EXISTS (
            SELECT 1 FROM reading_assignments ra
            JOIN assignment_tests at ON at.assignment_id = ra.id
            WHERE ra.id = student_test_attempts.assignment_id
            AND ra.teacher_id = auth.uid()::uuid
        )
    );

-- Add trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_student_test_attempts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    NEW.last_activity_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER student_test_attempts_updated_at
    BEFORE UPDATE ON student_test_attempts
    FOR EACH ROW
    EXECUTE FUNCTION update_student_test_attempts_updated_at();

-- Add a column to track attempt number
ALTER TABLE student_test_attempts ADD COLUMN attempt_number INTEGER DEFAULT 1;

-- Update the unique constraint to allow multiple attempts
ALTER TABLE student_test_attempts DROP CONSTRAINT unique_student_test;
ALTER TABLE student_test_attempts ADD CONSTRAINT unique_student_test_attempt 
    UNIQUE(student_id, assignment_test_id, attempt_number);