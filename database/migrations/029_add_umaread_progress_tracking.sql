-- Migration: Add UMARead progress tracking tables
-- This creates permanent storage for student progress and responses

-- Table to track student responses to questions
CREATE TABLE IF NOT EXISTS umaread_student_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('summary', 'comprehension')),
    question_text TEXT NOT NULL,
    student_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    ai_feedback TEXT,
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    time_spent_seconds INTEGER,
    attempt_number INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for common queries
    CONSTRAINT umaread_responses_student_assignment_idx 
        UNIQUE (student_id, assignment_id, chunk_number, question_type, attempt_number)
);

-- Table to track chunk completion status
CREATE TABLE IF NOT EXISTS umaread_chunk_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    chunk_number INTEGER NOT NULL,
    summary_completed BOOLEAN DEFAULT FALSE,
    comprehension_completed BOOLEAN DEFAULT FALSE,
    current_difficulty_level INTEGER DEFAULT 3 CHECK (current_difficulty_level BETWEEN 1 AND 8),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one record per student/assignment/chunk
    CONSTRAINT umaread_chunk_progress_unique 
        UNIQUE (student_id, assignment_id, chunk_number)
);

-- Table to track overall assignment progress
CREATE TABLE IF NOT EXISTS umaread_assignment_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    student_assignment_id UUID REFERENCES student_assignments(id),
    current_chunk INTEGER DEFAULT 1,
    total_chunks_completed INTEGER DEFAULT 0,
    current_difficulty_level INTEGER DEFAULT 3 CHECK (current_difficulty_level BETWEEN 1 AND 8),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one record per student/assignment
    CONSTRAINT umaread_assignment_progress_unique 
        UNIQUE (student_id, assignment_id)
);

-- Indexes for performance
CREATE INDEX idx_umaread_responses_student ON umaread_student_responses(student_id);
CREATE INDEX idx_umaread_responses_assignment ON umaread_student_responses(assignment_id);
CREATE INDEX idx_umaread_responses_lookup ON umaread_student_responses(student_id, assignment_id, chunk_number);

CREATE INDEX idx_umaread_chunk_student ON umaread_chunk_progress(student_id);
CREATE INDEX idx_umaread_chunk_assignment ON umaread_chunk_progress(assignment_id);

CREATE INDEX idx_umaread_progress_student ON umaread_assignment_progress(student_id);
CREATE INDEX idx_umaread_progress_assignment ON umaread_assignment_progress(assignment_id);
CREATE INDEX idx_umaread_progress_activity ON umaread_assignment_progress(last_activity_at);

-- Add trigger to update last_activity_at
CREATE OR REPLACE FUNCTION update_umaread_last_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE umaread_assignment_progress
    SET last_activity_at = CURRENT_TIMESTAMP
    WHERE student_id = NEW.student_id 
    AND assignment_id = NEW.assignment_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_activity_on_response
AFTER INSERT ON umaread_student_responses
FOR EACH ROW
EXECUTE FUNCTION update_umaread_last_activity();

-- Add trigger to update chunk progress updated_at
CREATE OR REPLACE FUNCTION update_chunk_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_chunk_progress_timestamp
BEFORE UPDATE ON umaread_chunk_progress
FOR EACH ROW
EXECUTE FUNCTION update_chunk_progress_timestamp();