-- Migration: Add text simplification cache table for "Crunch Text" feature
-- This table caches AI-simplified text to improve performance and reduce API calls

CREATE TABLE IF NOT EXISTS text_simplification_cache (
    id UUID PRIMARY KEY,
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    original_grade_level INTEGER,
    target_grade_level INTEGER NOT NULL,
    simplified_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(assignment_id, chunk_number, content_hash, target_grade_level)
);

-- Add index for faster lookups
CREATE INDEX idx_text_simplification_lookup ON text_simplification_cache(assignment_id, chunk_number, content_hash, target_grade_level);

-- Add index for cleanup queries
CREATE INDEX idx_text_simplification_created ON text_simplification_cache(created_at);