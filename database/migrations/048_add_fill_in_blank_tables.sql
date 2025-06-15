-- Migration: Add vocabulary fill-in-the-blank tables
-- Author: Claude Code
-- Date: 2025-01-15

-- Create vocabulary_fill_in_blank_sentences table
CREATE TABLE vocabulary_fill_in_blank_sentences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    sentence_with_blank TEXT NOT NULL,
    correct_answer VARCHAR(100) NOT NULL,
    sentence_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_sentence_order UNIQUE (vocabulary_list_id, sentence_order)
);

-- Create vocabulary_fill_in_blank_responses table
CREATE TABLE vocabulary_fill_in_blank_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    sentence_id UUID NOT NULL REFERENCES vocabulary_fill_in_blank_sentences(id) ON DELETE CASCADE,
    student_answer VARCHAR(100) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    time_spent_seconds INTEGER,
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_fill_in_blank_response_attempt UNIQUE (practice_progress_id, sentence_id, attempt_number)
);

-- Create vocabulary_fill_in_blank_attempts table
CREATE TABLE vocabulary_fill_in_blank_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    total_sentences INTEGER NOT NULL,
    sentences_completed INTEGER NOT NULL DEFAULT 0,
    current_sentence_index INTEGER NOT NULL DEFAULT 0,
    correct_answers INTEGER NOT NULL DEFAULT 0,
    incorrect_answers INTEGER NOT NULL DEFAULT 0,
    score_percentage NUMERIC(5, 2),
    passing_score INTEGER NOT NULL DEFAULT 70,
    sentence_order JSONB NOT NULL DEFAULT '[]'::jsonb,
    responses JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT check_fill_in_blank_attempt_status CHECK (
        status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')
    )
);

-- Create indexes for performance
CREATE INDEX idx_fill_in_blank_sentences_list_id ON vocabulary_fill_in_blank_sentences (vocabulary_list_id);
CREATE INDEX idx_fill_in_blank_sentences_word_id ON vocabulary_fill_in_blank_sentences (word_id);
CREATE INDEX idx_fill_in_blank_responses_student_id ON vocabulary_fill_in_blank_responses (student_id);
CREATE INDEX idx_fill_in_blank_responses_progress_id ON vocabulary_fill_in_blank_responses (practice_progress_id);
CREATE INDEX idx_fill_in_blank_attempts_student_id ON vocabulary_fill_in_blank_attempts (student_id);
CREATE INDEX idx_fill_in_blank_attempts_progress_id ON vocabulary_fill_in_blank_attempts (practice_progress_id);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_vocabulary_fill_in_blank_attempts_updated_at
    BEFORE UPDATE ON vocabulary_fill_in_blank_attempts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();