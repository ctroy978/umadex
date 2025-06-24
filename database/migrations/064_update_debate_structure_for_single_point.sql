-- Update debate structure for new single-point-per-round format
-- Changes:
-- 1. Each round is now a complete debate with 5 statements (student: 1st, 3rd, 5th; AI: 2nd, 4th)
-- 2. Add AI coaching feedback after each round
-- 3. Support new scoring structure with 70/100 baseline

-- Add statement_number to replace round_number concept
ALTER TABLE debate_posts ADD COLUMN statement_number INTEGER;

-- Migrate existing data (assuming old round_number maps to statement pairs)
UPDATE debate_posts 
SET statement_number = CASE 
    WHEN post_type = 'student' AND round_number = 1 THEN 1
    WHEN post_type = 'ai' AND round_number = 1 THEN 2
    WHEN post_type = 'student' AND round_number = 2 THEN 3
    WHEN post_type = 'ai' AND round_number = 2 THEN 4
    WHEN post_type = 'student' AND round_number = 3 THEN 5
    ELSE round_number * 2 - (CASE WHEN post_type = 'student' THEN 1 ELSE 0 END)
END;

-- Make statement_number NOT NULL after migration
ALTER TABLE debate_posts ALTER COLUMN statement_number SET NOT NULL;

-- Add constraint for statement numbers
ALTER TABLE debate_posts ADD CONSTRAINT check_statement_number 
    CHECK (statement_number BETWEEN 1 AND 5);

-- Add coaching feedback table for round-level feedback
CREATE TABLE debate_round_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_debate_id UUID NOT NULL REFERENCES student_debates(id),
    debate_number INTEGER NOT NULL CHECK (debate_number BETWEEN 1 AND 3),
    
    -- Coaching feedback after the round
    coaching_feedback TEXT NOT NULL,
    strengths TEXT,
    improvement_areas TEXT,
    specific_suggestions TEXT,
    
    -- Round completion tracking
    round_completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint to ensure one feedback per round
    UNIQUE(student_debate_id, debate_number)
);

-- Update debate assignments to clarify new structure
ALTER TABLE debate_assignments ADD COLUMN IF NOT EXISTS statements_per_round INTEGER DEFAULT 5;
ALTER TABLE debate_assignments ADD COLUMN IF NOT EXISTS coaching_enabled BOOLEAN DEFAULT true;

-- Add fields to track the single point being debated in each round
ALTER TABLE student_debates ADD COLUMN debate_1_point TEXT;
ALTER TABLE student_debates ADD COLUMN debate_2_point TEXT;
ALTER TABLE student_debates ADD COLUMN debate_3_point TEXT;

-- Update scoring to support new lenient grading (70/100 baseline)
-- Add grading configuration
ALTER TABLE debate_assignments ADD COLUMN IF NOT EXISTS grading_baseline INTEGER DEFAULT 70;
ALTER TABLE debate_assignments ADD COLUMN IF NOT EXISTS grading_scale VARCHAR(20) DEFAULT 'lenient' 
    CHECK (grading_scale IN ('lenient', 'standard', 'strict'));

-- Add AI debate point generation table
CREATE TABLE ai_debate_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES debate_assignments(id),
    debate_number INTEGER NOT NULL CHECK (debate_number BETWEEN 1 AND 3),
    position VARCHAR(10) NOT NULL CHECK (position IN ('pro', 'con')),
    
    -- The single point for this round
    debate_point TEXT NOT NULL,
    supporting_evidence TEXT[],
    
    -- Metadata
    difficulty_appropriate BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Allow multiple points per assignment for variety
    UNIQUE(assignment_id, debate_number, debate_point)
);

-- Update the function to handle statement-based structure
CREATE OR REPLACE FUNCTION get_current_statement_number(p_student_debate_id UUID, p_debate_number INTEGER)
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM debate_posts
    WHERE student_debate_id = p_student_debate_id 
    AND debate_number = p_debate_number;
    
    -- Next statement number is count + 1
    RETURN COALESCE(v_count, 0) + 1;
END;
$$ LANGUAGE plpgsql;

-- Add function to check if round is complete (5 statements)
CREATE OR REPLACE FUNCTION is_round_complete(p_student_debate_id UUID, p_debate_number INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM debate_posts
    WHERE student_debate_id = p_student_debate_id 
    AND debate_number = p_debate_number;
    
    RETURN v_count >= 5;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for new structure
CREATE INDEX idx_debate_posts_statement ON debate_posts(student_debate_id, debate_number, statement_number);
CREATE INDEX idx_debate_round_feedback ON debate_round_feedback(student_debate_id, debate_number);
CREATE INDEX idx_ai_debate_points ON ai_debate_points(assignment_id, debate_number);

-- Enable RLS on new tables
ALTER TABLE debate_round_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_debate_points ENABLE ROW LEVEL SECURITY;

-- Add policies
CREATE POLICY debate_round_feedback_access ON debate_round_feedback
    FOR ALL USING (true); -- Will be updated with proper auth

CREATE POLICY ai_debate_points_read ON ai_debate_points
    FOR SELECT USING (true);

CREATE POLICY ai_debate_points_write ON ai_debate_points
    FOR ALL USING (false); -- Admin only

-- Seed some AI debate points for testing
INSERT INTO ai_debate_points (assignment_id, debate_number, position, debate_point, supporting_evidence) 
SELECT 
    id, 
    2, 
    'con',
    'The UN bureaucracy wastes over $1 billion annually in administrative overhead that could be better spent on domestic programs',
    ARRAY[
        'UN administrative costs account for 15% of total budget',
        'US contribution of $10 billion could fund 100,000 teachers domestically',
        'Multiple reports show inefficiencies in UN procurement processes'
    ]
FROM debate_assignments 
WHERE topic ILIKE '%UN%' 
LIMIT 1;