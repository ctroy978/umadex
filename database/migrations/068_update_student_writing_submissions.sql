-- Drop the old table to recreate with new structure
DROP TABLE IF EXISTS student_writing_submissions CASCADE;

-- Create student writing submissions table with new structure
CREATE TABLE student_writing_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_assignment_id UUID NOT NULL REFERENCES student_assignments(id) ON DELETE CASCADE,
    writing_assignment_id UUID NOT NULL REFERENCES writing_assignments(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL,
    selected_techniques TEXT[] DEFAULT '{}',
    word_count INTEGER NOT NULL,
    submission_attempt INTEGER NOT NULL DEFAULT 1,
    is_final_submission BOOLEAN DEFAULT FALSE,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    score DECIMAL(3,2),
    ai_feedback JSONB,
    CONSTRAINT check_score_range CHECK (score IS NULL OR (score >= 0 AND score <= 10))
);

-- Create indexes for student submissions
CREATE INDEX idx_student_writing_submissions_student_id ON student_writing_submissions(student_id);
CREATE INDEX idx_student_writing_submissions_student_assignment_id ON student_writing_submissions(student_assignment_id);
CREATE INDEX idx_student_writing_submissions_writing_assignment_id ON student_writing_submissions(writing_assignment_id);
CREATE INDEX idx_student_writing_submissions_submitted_at ON student_writing_submissions(submitted_at);

-- Enable RLS on student submissions
ALTER TABLE student_writing_submissions ENABLE ROW LEVEL SECURITY;

-- Create trigger for updating updated_at on submissions
CREATE TRIGGER update_student_writing_submissions_updated_at
    BEFORE UPDATE ON student_writing_submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();