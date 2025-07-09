-- Migration: Add question cache table for AI-generated questions
-- This table caches AI-generated questions to improve performance and reduce API calls

CREATE TABLE IF NOT EXISTS question_cache (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,
    difficulty_level INTEGER NOT NULL CHECK (difficulty_level BETWEEN 1 AND 8),
    content_hash VARCHAR(64) NOT NULL,
    question_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(assignment_id, chunk_id, difficulty_level, content_hash)
);

-- Add index for faster lookups
CREATE INDEX idx_question_cache_lookup ON question_cache(assignment_id, chunk_id, difficulty_level, content_hash);

-- Add index for cleanup queries
CREATE INDEX idx_question_cache_created ON question_cache(created_at);