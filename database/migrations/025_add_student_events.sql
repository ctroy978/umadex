-- Create student events table for tracking various student activities including bypass code usage
CREATE TABLE IF NOT EXISTS student_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    classroom_id UUID REFERENCES classrooms(id) ON DELETE CASCADE,
    assignment_id UUID,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_student_events_student_id ON student_events(student_id);
CREATE INDEX idx_student_events_classroom_id ON student_events(classroom_id);
CREATE INDEX idx_student_events_type ON student_events(event_type);
CREATE INDEX idx_student_events_created_at ON student_events(created_at);

-- Add comment explaining the table
COMMENT ON TABLE student_events IS 'Tracks various student activities including bypass code usage, assignment completion, etc.';
COMMENT ON COLUMN student_events.event_type IS 'Type of event: bypass_code_used, assignment_started, assignment_completed, etc.';
COMMENT ON COLUMN student_events.event_data IS 'JSON data specific to the event type';