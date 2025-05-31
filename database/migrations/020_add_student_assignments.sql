-- Add student assignments table for tracking individual student progress

CREATE TABLE student_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL, -- will reference reading_assignments or other assignment types
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id),
    assignment_type VARCHAR(50) NOT NULL DEFAULT 'reading',
    
    status VARCHAR(50) NOT NULL DEFAULT 'not_started' 
        CHECK (status IN ('not_started', 'in_progress', 'completed', 'test_available', 'test_completed')),
    current_position INTEGER DEFAULT 1, -- current chunk number or position
    
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    progress_metadata JSONB DEFAULT '{}', -- module-specific data
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(student_id, assignment_id, classroom_assignment_id)
);

-- Indexes for performance
CREATE INDEX idx_student_assignments_student ON student_assignments(student_id, status);
CREATE INDEX idx_student_assignments_assignment ON student_assignments(assignment_id, assignment_type);
CREATE INDEX idx_student_assignments_classroom ON student_assignments(classroom_assignment_id);
CREATE INDEX idx_student_assignments_activity ON student_assignments(last_activity_at DESC);

-- Update trigger
CREATE OR REPLACE FUNCTION update_student_assignment_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_student_assignments_updated_at
    BEFORE UPDATE ON student_assignments
    FOR EACH ROW EXECUTE FUNCTION update_student_assignment_updated_at();

-- RLS policies (basic setup)
ALTER TABLE student_assignments ENABLE ROW LEVEL SECURITY;

-- Students can view and update their own assignments
CREATE POLICY "Students can manage their own assignments"
    ON student_assignments FOR ALL
    USING (student_id = auth.uid());

-- Teachers can view assignments for their students in their classrooms
CREATE POLICY "Teachers can view classroom assignments"
    ON student_assignments FOR SELECT
    USING (
        classroom_assignment_id IN (
            SELECT ca.id 
            FROM classroom_assignments ca
            JOIN classrooms c ON c.id = ca.classroom_id
            WHERE c.teacher_id = auth.uid()
        )
    );