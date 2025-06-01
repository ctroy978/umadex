-- Migration: Add evaluation tracking for answer attempts
-- This table tracks student answer attempts and AI evaluation results

CREATE TABLE IF NOT EXISTS answer_evaluations (
    id UUID PRIMARY KEY,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('summary', 'comprehension')),
    question_text TEXT NOT NULL,
    student_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    feedback TEXT NOT NULL,
    difficulty_level INTEGER NOT NULL CHECK (difficulty_level BETWEEN 1 AND 8),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_answer_evaluations_student ON answer_evaluations(student_id, assignment_id);
CREATE INDEX idx_answer_evaluations_lookup ON answer_evaluations(student_id, assignment_id, chunk_number, question_type);

-- Add column to track consecutive errors for difficulty adjustment
ALTER TABLE student_assignments ADD COLUMN IF NOT EXISTS consecutive_errors INTEGER DEFAULT 0;