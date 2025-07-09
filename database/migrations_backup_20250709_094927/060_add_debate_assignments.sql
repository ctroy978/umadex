-- UMADebate Teacher Interface - Database Schema
-- Migration: 060_add_debate_assignments.sql

-- Primary Table for Debate Assignments
CREATE TABLE debate_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Assignment metadata (Step 1)
    title VARCHAR(200) NOT NULL,
    topic TEXT NOT NULL,
    description TEXT,
    grade_level VARCHAR(50) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    
    -- Debate configuration (Step 2)
    rounds_per_debate INTEGER NOT NULL DEFAULT 3 CHECK (rounds_per_debate BETWEEN 2 AND 4),
    debate_count INTEGER NOT NULL DEFAULT 3,
    time_limit_hours INTEGER NOT NULL DEFAULT 8,
    difficulty_level VARCHAR(20) NOT NULL DEFAULT 'medium' 
        CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    
    -- AI configuration
    fallacy_frequency VARCHAR(20) DEFAULT 'every_2_3' 
        CHECK (fallacy_frequency IN ('every_1_2', 'every_2_3', 'every_3_4', 'disabled')),
    ai_personalities_enabled BOOLEAN DEFAULT true,
    
    -- Content moderation
    content_moderation_enabled BOOLEAN DEFAULT true,
    auto_flag_off_topic BOOLEAN DEFAULT true,
    
    -- Standard UMA fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    
    -- Constraints
    CONSTRAINT valid_title_length CHECK (LENGTH(title) >= 5),
    CONSTRAINT valid_topic_length CHECK (LENGTH(topic) >= 10)
);

-- Indexes following UMA patterns
CREATE INDEX idx_debate_assignments_teacher ON debate_assignments(teacher_id);
CREATE INDEX idx_debate_assignments_grade_subject ON debate_assignments(grade_level, subject);
CREATE INDEX idx_debate_assignments_active ON debate_assignments(teacher_id) WHERE deleted_at IS NULL;

-- RLS policies (follow existing UMA patterns)
ALTER TABLE debate_assignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY debate_assignments_teacher_access ON debate_assignments
    FOR ALL USING (
        teacher_id = current_setting('app.current_user_id', true)::uuid OR 
        EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', true)::uuid AND role = 'admin')
    );

-- Content Moderation Support Table
CREATE TABLE content_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID, -- Will reference debate_posts in Phase 2
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES debate_assignments(id) ON DELETE CASCADE,
    
    flag_type VARCHAR(50) NOT NULL CHECK (flag_type IN ('profanity', 'inappropriate', 'off_topic', 'spam')),
    flag_reason TEXT,
    auto_flagged BOOLEAN DEFAULT false,
    confidence_score DECIMAL(3,2), -- For AI flagging confidence
    
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'escalated')),
    teacher_action VARCHAR(50), -- 'approve', 'request_revision', 'remove_post', 'escalate'
    teacher_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_content_flags_teacher_pending ON content_flags(teacher_id, status) WHERE status = 'pending';
CREATE INDEX idx_content_flags_assignment ON content_flags(assignment_id);

-- RLS policies for content_flags
ALTER TABLE content_flags ENABLE ROW LEVEL SECURITY;

CREATE POLICY content_flags_teacher_access ON content_flags
    FOR ALL USING (
        teacher_id = current_setting('app.current_user_id', true)::uuid OR 
        EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', true)::uuid AND role = 'admin')
    );

-- Update trigger for updated_at
CREATE TRIGGER update_debate_assignments_updated_at BEFORE UPDATE
    ON debate_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment to describe the table
COMMENT ON TABLE debate_assignments IS 'Stores debate assignments created by teachers for the UMADebate module';
COMMENT ON TABLE content_flags IS 'Stores content moderation flags for student posts in debates';