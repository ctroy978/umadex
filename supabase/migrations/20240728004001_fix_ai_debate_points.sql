-- Migration to create missing ai_debate_points table
-- This table stores AI-generated debate points for each round

CREATE TABLE IF NOT EXISTS ai_debate_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES debate_assignments(id) ON DELETE CASCADE,
    debate_number INTEGER NOT NULL,
    position VARCHAR(10) NOT NULL CHECK (position IN ('pro', 'con')),
    
    -- The single point for this round
    debate_point TEXT NOT NULL,
    supporting_evidence JSONB,
    
    -- Metadata
    difficulty_appropriate BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_debate_points_assignment 
    ON ai_debate_points(assignment_id, debate_number, position);

-- Grant necessary permissions if using RLS
ALTER TABLE ai_debate_points ENABLE ROW LEVEL SECURITY;

-- Allow backend service to access the table
CREATE POLICY "Service role can manage ai_debate_points" ON ai_debate_points
    FOR ALL USING (auth.role() = 'service_role');