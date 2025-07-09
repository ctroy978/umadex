-- Create writing assignments table
CREATE TABLE writing_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    prompt_text TEXT NOT NULL,
    word_count_min INTEGER DEFAULT 50 CHECK (word_count_min > 0),
    word_count_max INTEGER DEFAULT 500 CHECK (word_count_max > word_count_min),
    evaluation_criteria JSONB NOT NULL DEFAULT '{}',
    instructions TEXT,
    grade_level VARCHAR(50),
    subject VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- Create indexes for writing assignments
CREATE INDEX idx_writing_assignments_teacher_id ON writing_assignments(teacher_id);
CREATE INDEX idx_writing_assignments_created_at ON writing_assignments(created_at);
CREATE INDEX idx_writing_assignments_deleted_at ON writing_assignments(deleted_at);
CREATE INDEX idx_writing_assignments_grade_level ON writing_assignments(grade_level);

-- Enable Row Level Security
ALTER TABLE writing_assignments ENABLE ROW LEVEL SECURITY;

-- RLS policy: Teachers can only access their own assignments
-- Note: RLS will be handled at the application level since we don't have auth schema

-- Create trigger for updating updated_at
CREATE TRIGGER update_writing_assignments_updated_at
    BEFORE UPDATE ON writing_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update check_assignment_reference constraint to include writing
ALTER TABLE classroom_assignments 
DROP CONSTRAINT check_assignment_reference;

ALTER TABLE classroom_assignments 
ADD CONSTRAINT check_assignment_reference CHECK (
    (assignment_type = 'reading' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'vocabulary' AND assignment_id IS NULL AND vocabulary_list_id IS NOT NULL) OR
    (assignment_type = 'debate' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'writing' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL)
);

-- Create student writing submissions table
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

-- RLS policies: Will be handled at the application level since we don't have auth schema

-- Create trigger for updating updated_at on submissions
CREATE TRIGGER update_student_writing_submissions_updated_at
    BEFORE UPDATE ON student_writing_submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();