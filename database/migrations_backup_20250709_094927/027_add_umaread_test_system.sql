-- Add UMARead test system tables

-- Main test storage table
CREATE TABLE assignment_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'archived')),
    test_questions JSONB NOT NULL, -- stores questions + answer keys + grading context
    teacher_notes TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    max_attempts INTEGER DEFAULT 1,
    time_limit_minutes INTEGER DEFAULT 60,
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test results storage
CREATE TABLE test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES assignment_tests(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id),
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id),
    
    -- Student responses and AI grading
    responses JSONB NOT NULL, -- student answers + AI scores + AI justifications
    overall_score DECIMAL(5,2) NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    
    -- Timing and completion
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_minutes INTEGER,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure student can't exceed max attempts
    UNIQUE(test_id, student_id, attempt_number)
);

-- Indexes for performance
CREATE INDEX idx_assignment_tests_assignment_id ON assignment_tests(assignment_id);
CREATE INDEX idx_assignment_tests_status ON assignment_tests(status);
CREATE INDEX idx_test_results_test_id ON test_results(test_id);
CREATE INDEX idx_test_results_student_id ON test_results(student_id);
CREATE INDEX idx_test_results_classroom_assignment_id ON test_results(classroom_assignment_id);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_assignment_tests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update the updated_at column
CREATE TRIGGER update_assignment_tests_updated_at
    BEFORE UPDATE ON assignment_tests
    FOR EACH ROW
    EXECUTE FUNCTION update_assignment_tests_updated_at();