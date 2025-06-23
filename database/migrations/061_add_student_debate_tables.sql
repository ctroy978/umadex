-- UMADebate Student Progress Tables Migration
-- Phase 2: Student Interface Implementation

-- Main student debate progress tracking
CREATE TABLE student_debates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES debate_assignments(id),
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id),
    
    -- Progress tracking (following UMA unit-based patterns)
    status VARCHAR(50) NOT NULL DEFAULT 'not_started' 
        CHECK (status IN ('not_started', 'debate_1', 'debate_2', 'debate_3', 'completed')),
    current_debate INTEGER DEFAULT 1 CHECK (current_debate BETWEEN 1 AND 3),
    current_round INTEGER DEFAULT 1,
    
    -- Three-debate structure
    debate_1_position VARCHAR(10), -- 'pro' or 'con' (randomly assigned)
    debate_2_position VARCHAR(10), -- opposite of debate_1
    debate_3_position VARCHAR(10), -- 'choice' (student picks)
    
    -- Fallacy tracking (hybrid random system)
    fallacy_counter INTEGER DEFAULT 0,
    fallacy_scheduled_debate INTEGER, -- which debate (1, 2, or 3) will have fallacy
    fallacy_scheduled_round INTEGER,  -- which round within that debate
    
    -- Timing controls
    assignment_started_at TIMESTAMP WITH TIME ZONE,
    current_debate_started_at TIMESTAMP WITH TIME ZONE,
    current_debate_deadline TIMESTAMP WITH TIME ZONE,
    
    -- Final scoring
    debate_1_percentage DECIMAL(5,2),
    debate_2_percentage DECIMAL(5,2), 
    debate_3_percentage DECIMAL(5,2),
    final_percentage DECIMAL(5,2),
    
    -- Standard UMA fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(student_id, assignment_id, classroom_assignment_id)
);

-- Individual posts in debates (student and AI)
CREATE TABLE debate_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_debate_id UUID NOT NULL REFERENCES student_debates(id),
    
    -- Post identification
    debate_number INTEGER NOT NULL CHECK (debate_number BETWEEN 1 AND 3),
    round_number INTEGER NOT NULL,
    post_type VARCHAR(20) NOT NULL CHECK (post_type IN ('student', 'ai')),
    
    -- Content
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    
    -- AI-specific fields
    ai_personality VARCHAR(50), -- 'scholar', 'skeptic', etc.
    is_fallacy BOOLEAN DEFAULT false,
    fallacy_type VARCHAR(50), -- 'ad_hominem', 'strawman', etc.
    
    -- Student scoring
    clarity_score DECIMAL(2,1) CHECK (clarity_score BETWEEN 1 AND 5),
    evidence_score DECIMAL(2,1) CHECK (evidence_score BETWEEN 1 AND 5),
    logic_score DECIMAL(2,1) CHECK (logic_score BETWEEN 1 AND 5),
    persuasiveness_score DECIMAL(2,1) CHECK (persuasiveness_score BETWEEN 1 AND 5),
    rebuttal_score DECIMAL(2,1) CHECK (rebuttal_score BETWEEN 1 AND 5),
    base_percentage DECIMAL(5,2), -- (sum of scores / 25) * 70
    bonus_points DECIMAL(5,2) DEFAULT 0,
    final_percentage DECIMAL(5,2),
    
    -- Moderation
    content_flagged BOOLEAN DEFAULT false,
    moderation_status VARCHAR(20) DEFAULT 'approved' 
        CHECK (moderation_status IN ('pending', 'approved', 'rejected', 'revision_requested')),
    
    -- AI feedback
    ai_feedback TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Student challenges and recognitions
CREATE TABLE debate_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES debate_posts(id),
    student_id UUID NOT NULL REFERENCES users(id),
    
    -- Challenge details
    challenge_type VARCHAR(20) NOT NULL CHECK (challenge_type IN ('fallacy', 'appeal')),
    challenge_value VARCHAR(50) NOT NULL, -- specific fallacy or appeal name
    explanation TEXT,
    
    -- Evaluation
    is_correct BOOLEAN NOT NULL,
    points_awarded DECIMAL(3,1) NOT NULL, -- +5.0, +3.0, or -1.0
    ai_feedback TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI personalities for random assignment
CREATE TABLE ai_personalities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    difficulty_levels VARCHAR(100)[], -- ['beginner', 'intermediate', 'advanced']
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fallacy templates by topic and difficulty
CREATE TABLE fallacy_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fallacy_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    template TEXT NOT NULL,
    difficulty_levels VARCHAR(100)[], 
    topic_keywords TEXT[], -- for topic-relevant fallacies
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Update content_flags table to reference debate_posts
ALTER TABLE content_flags ADD COLUMN debate_post_id UUID REFERENCES debate_posts(id);

-- Indexes for performance
CREATE INDEX idx_student_debates_student_status ON student_debates(student_id, status);
CREATE INDEX idx_student_debates_classroom ON student_debates(classroom_assignment_id);
CREATE INDEX idx_debate_posts_student_debate ON debate_posts(student_debate_id, debate_number, round_number);
CREATE INDEX idx_debate_challenges_post ON debate_challenges(post_id);
CREATE INDEX idx_content_flags_debate_post ON content_flags(debate_post_id) WHERE debate_post_id IS NOT NULL;

-- RLS Policies
ALTER TABLE student_debates ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_challenges ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_personalities ENABLE ROW LEVEL SECURITY;
ALTER TABLE fallacy_templates ENABLE ROW LEVEL SECURITY;

-- Student debates access policy
CREATE POLICY student_debates_access ON student_debates
    FOR ALL USING (true); -- Simplified for now, will be updated when auth is properly configured

-- Debate posts access policy
CREATE POLICY debate_posts_access ON debate_posts
    FOR ALL USING (true); -- Simplified for now

-- Debate challenges access policy
CREATE POLICY debate_challenges_access ON debate_challenges
    FOR ALL USING (true); -- Simplified for now

-- AI personalities and fallacy templates are read-only for non-admins
CREATE POLICY ai_personalities_read ON ai_personalities
    FOR SELECT USING (true);

CREATE POLICY ai_personalities_write ON ai_personalities
    FOR ALL USING (false); -- Admin only, disabled for now

CREATE POLICY fallacy_templates_read ON fallacy_templates
    FOR SELECT USING (true);

CREATE POLICY fallacy_templates_write ON fallacy_templates
    FOR ALL USING (false); -- Admin only, disabled for now

-- Seed data for AI personalities
INSERT INTO ai_personalities (name, display_name, description, prompt_template, difficulty_levels) VALUES
('scholar', 'The Scholar', 'Formal, evidence-heavy, cites studies', 'You are a formal academic debater who uses scholarly language and frequently cites research studies, statistics, and academic sources. Your arguments are structured and methodical, often using numbered points and clear transitions.', ARRAY['beginner', 'intermediate', 'advanced']),
('skeptic', 'The Skeptic', 'Questions everything, plays devil''s advocate', 'You are a skeptical debater who questions assumptions and plays devil''s advocate. You frequently ask "But what about..." and "Have you considered..." questions. You challenge evidence and look for logical flaws in arguments.', ARRAY['intermediate', 'advanced']),
('peer', 'The Peer', 'Casual, relatable examples', 'You are a friendly peer debater who uses casual language and relatable examples from everyday life. You often reference personal experiences, popular culture, and current events that students would understand.', ARRAY['beginner', 'intermediate']),
('philosopher', 'The Philosopher', 'Abstract thinking, thought experiments', 'You are a philosophical debater who uses abstract thinking and thought experiments. You often reference famous philosophers and ethical frameworks, using "what if" scenarios to explore ideas.', ARRAY['intermediate', 'advanced']),
('policymaker', 'The Policymaker', 'Practical implementation focus', 'You are a practical policy-focused debater who emphasizes real-world implementation and consequences. You discuss costs, benefits, stakeholders, and feasibility of proposals.', ARRAY['beginner', 'intermediate', 'advanced']);

-- Seed data for fallacy templates
INSERT INTO fallacy_templates (fallacy_type, display_name, description, template, difficulty_levels) VALUES
('ad_hominem', 'Ad Hominem', 'Attacks the person making the argument', 'Your argument fails because you''re just a {grade_level} student who doesn''t have real-world experience with this issue.', ARRAY['beginner', 'intermediate']),
('strawman', 'Strawman', 'Misrepresents the opponent''s argument', 'So you''re saying we should completely {extreme_version} without any consideration for {obvious_concern}? That''s clearly unreasonable.', ARRAY['beginner', 'intermediate', 'advanced']),
('red_herring', 'Red Herring', 'Introduces irrelevant information', 'But what about {unrelated_topic}? That''s the real issue we should be discussing, not {original_topic}.', ARRAY['intermediate', 'advanced']),
('false_dichotomy', 'False Dichotomy', 'Presents only two options when more exist', 'You''re either completely for {position} or you''re against progress. There''s no middle ground here.', ARRAY['intermediate', 'advanced']),
('appeal_to_emotion', 'Appeal to Emotion', 'Manipulates emotions instead of using logic', 'Think of the {emotional_group}! How can you be so heartless as to support a position that would cause such {emotional_consequence}?', ARRAY['beginner', 'intermediate']),
('slippery_slope', 'Slippery Slope', 'Assumes one thing leads to extreme consequences', 'If we allow {minor_thing}, next thing you know we''ll have {extreme_consequence}. It''s a dangerous path.', ARRAY['intermediate', 'advanced']),
('hasty_generalization', 'Hasty Generalization', 'Makes broad conclusions from limited examples', 'I know someone who {single_example}, therefore all {group} must be {characteristic}.', ARRAY['beginner', 'intermediate']),
('circular_reasoning', 'Circular Reasoning', 'Uses the conclusion as a premise', 'This is right because it''s the correct thing to do, and we know it''s correct because it''s right.', ARRAY['advanced']);

-- Add triggers for updated_at
CREATE TRIGGER update_student_debates_updated_at
    BEFORE UPDATE ON student_debates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add helper functions
CREATE OR REPLACE FUNCTION get_student_debate_progress(p_student_id UUID, p_assignment_id UUID)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT json_build_object(
        'student_debate', row_to_json(sd),
        'posts', COALESCE(json_agg(dp ORDER BY dp.debate_number, dp.round_number), '[]'::json),
        'challenges', COALESCE(json_agg(dc), '[]'::json)
    ) INTO v_result
    FROM student_debates sd
    LEFT JOIN debate_posts dp ON sd.id = dp.student_debate_id
    LEFT JOIN debate_challenges dc ON dp.id = dc.post_id
    WHERE sd.student_id = p_student_id AND sd.assignment_id = p_assignment_id
    GROUP BY sd.id;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;