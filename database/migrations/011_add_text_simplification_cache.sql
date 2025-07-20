-- Add text_simplification_cache table for UMARead "Crunch Text" feature
-- This table caches AI-simplified versions of reading chunks to improve performance

CREATE TABLE IF NOT EXISTS text_simplification_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,  -- SHA256 hash of original content
    original_grade_level VARCHAR(20),   -- e.g., "6-8", "9-10"
    target_grade_level INTEGER NOT NULL,
    simplified_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure uniqueness for each simplification variant
    CONSTRAINT unique_simplification UNIQUE (assignment_id, chunk_number, content_hash, target_grade_level)
);

-- Add indexes for efficient lookups
CREATE INDEX idx_text_simplification_cache_lookup ON text_simplification_cache(assignment_id, chunk_number, content_hash, target_grade_level);
CREATE INDEX idx_text_simplification_cache_created ON text_simplification_cache(created_at);

-- Add comment explaining the table
COMMENT ON TABLE text_simplification_cache IS 'Caches AI-simplified versions of reading chunks for the UMARead "Crunch Text" feature';