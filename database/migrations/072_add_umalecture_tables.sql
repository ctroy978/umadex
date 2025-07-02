-- UMALecture Module Tables
-- Migration: 072_add_umalecture_tables.sql

-- Main lecture assignments table
CREATE TABLE lecture_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    grade_level VARCHAR(50) NOT NULL,
    
    -- Core content
    topic_outline TEXT, -- Original teacher outline
    learning_objectives TEXT[], -- Array of key objectives
    
    -- AI-generated structure (stored as JSONB)
    lecture_structure JSONB, -- Full node graph with choices
    
    -- Status management
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'published', 'archived')),
    processing_started_at TIMESTAMP WITH TIME ZONE,
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    processing_error TEXT,
    
    -- Metadata following existing patterns
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL -- Soft delete pattern
);

-- Lecture images (following UMARead image pattern)
CREATE TABLE lecture_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lecture_id UUID NOT NULL REFERENCES lecture_assignments(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    teacher_description TEXT NOT NULL, -- Brief teacher input
    ai_description TEXT, -- AI-enhanced description
    node_id VARCHAR(100) NOT NULL, -- Which outline section this belongs to
    position INTEGER NOT NULL DEFAULT 1, -- Order within node
    
    -- Image versions (following existing pattern)
    original_url TEXT NOT NULL,
    display_url TEXT, -- 800x600 version
    thumbnail_url TEXT, -- 200x150 version
    file_size INTEGER,
    mime_type VARCHAR(50),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI content cache for lectures
CREATE TABLE lecture_content_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lecture_id UUID NOT NULL REFERENCES lecture_assignments(id) ON DELETE CASCADE,
    topic_id VARCHAR(100) NOT NULL,
    difficulty_level VARCHAR(20) NOT NULL CHECK (difficulty_level IN ('basic', 'intermediate', 'advanced', 'expert')),
    
    content_text TEXT NOT NULL,
    questions JSONB NOT NULL DEFAULT '[]',
    
    ai_model VARCHAR(100) NOT NULL,
    generation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(lecture_id, topic_id, difficulty_level)
);

-- Student lecture interactions
CREATE TABLE lecture_student_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES student_assignments(id) ON DELETE CASCADE,
    lecture_id UUID NOT NULL REFERENCES lecture_assignments(id),
    
    -- Interaction data
    topic_id VARCHAR(100) NOT NULL,
    difficulty_level VARCHAR(20) NOT NULL CHECK (difficulty_level IN ('basic', 'intermediate', 'advanced', 'expert')),
    interaction_type VARCHAR(50) NOT NULL CHECK (interaction_type IN ('view_content', 'answer_question', 'change_difficulty', 'navigate_topic')),
    
    -- Question response data (null for non-question interactions)
    question_text TEXT,
    student_answer TEXT,
    is_correct BOOLEAN,
    
    -- Timing
    time_spent_seconds INTEGER,
    
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add lecture_assignments to reading_assignments for unified management
-- This allows reuse of existing teacher interfaces
-- Note: The assignment_type constraint was already updated in migration 014

-- Create indexes for performance
CREATE INDEX idx_lecture_assignments_teacher_id ON lecture_assignments(teacher_id);
CREATE INDEX idx_lecture_assignments_status ON lecture_assignments(status);
CREATE INDEX idx_lecture_assignments_deleted_at ON lecture_assignments(deleted_at);
CREATE INDEX idx_lecture_images_lecture_id ON lecture_images(lecture_id);
CREATE INDEX idx_lecture_content_cache_lookup ON lecture_content_cache(lecture_id, topic_id, difficulty_level);
CREATE INDEX idx_lecture_interactions_student ON lecture_student_interactions(student_id, assignment_id);
CREATE INDEX idx_lecture_interactions_occurred ON lecture_student_interactions(occurred_at DESC);

-- Update trigger for updated_at
CREATE TRIGGER update_lecture_assignments_updated_at 
    BEFORE UPDATE ON lecture_assignments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lecture_content_cache_updated_at 
    BEFORE UPDATE ON lecture_content_cache 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS on all tables
ALTER TABLE lecture_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE lecture_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE lecture_content_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE lecture_student_interactions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for lecture_assignments
-- Teachers can view and manage their own lectures
CREATE POLICY lecture_assignments_teacher_all ON lecture_assignments
    FOR ALL
    USING (
        teacher_id = current_setting('app.current_user_id', true)::uuid 
        AND EXISTS (
            SELECT 1 FROM users 
            WHERE id = current_setting('app.current_user_id', true)::uuid 
            AND role = 'teacher'
        )
    )
    WITH CHECK (
        teacher_id = current_setting('app.current_user_id', true)::uuid 
        AND EXISTS (
            SELECT 1 FROM users 
            WHERE id = current_setting('app.current_user_id', true)::uuid 
            AND role = 'teacher'
        )
    );

-- Students can view lectures assigned to them
CREATE POLICY lecture_assignments_student_select ON lecture_assignments
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM student_assignments sa
            JOIN classroom_assignments ca ON ca.id = sa.classroom_assignment_id
            WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
            AND ca.assignment_id = lecture_assignments.id
            AND ca.assignment_type = 'UMALecture'
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'student'
            )
        )
    );

-- RLS Policies for lecture_images
-- Teachers can manage images for their lectures
CREATE POLICY lecture_images_teacher_all ON lecture_images
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM lecture_assignments la
            WHERE la.id = lecture_images.lecture_id
            AND la.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM lecture_assignments la
            WHERE la.id = lecture_images.lecture_id
            AND la.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    );

-- Students can view images for assigned lectures
CREATE POLICY lecture_images_student_select ON lecture_images
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM lecture_assignments la
            JOIN student_assignments sa ON true
            JOIN classroom_assignments ca ON ca.id = sa.classroom_assignment_id
            WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
            AND ca.assignment_id = la.id
            AND ca.assignment_type = 'UMALecture'
            AND la.id = lecture_images.lecture_id
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'student'
            )
        )
    );

-- RLS Policies for lecture_content_cache
-- Teachers can view and manage cache for their lectures
CREATE POLICY lecture_cache_teacher_all ON lecture_content_cache
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM lecture_assignments la
            WHERE la.id = lecture_content_cache.lecture_id
            AND la.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM lecture_assignments la
            WHERE la.id = lecture_content_cache.lecture_id
            AND la.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    );

-- Students can view cache for assigned lectures
CREATE POLICY lecture_cache_student_select ON lecture_content_cache
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM lecture_assignments la
            JOIN student_assignments sa ON true
            JOIN classroom_assignments ca ON ca.id = sa.classroom_assignment_id
            WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
            AND ca.assignment_id = la.id
            AND ca.assignment_type = 'UMALecture'
            AND la.id = lecture_content_cache.lecture_id
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'student'
            )
        )
    );

-- RLS Policies for lecture_student_interactions
-- Students can insert and view their own interactions
CREATE POLICY lecture_interactions_student_all ON lecture_student_interactions
    FOR ALL
    USING (
        student_id = current_setting('app.current_user_id', true)::uuid
        AND EXISTS (
            SELECT 1 FROM users 
            WHERE id = current_setting('app.current_user_id', true)::uuid
            AND role = 'student'
        )
    )
    WITH CHECK (
        student_id = current_setting('app.current_user_id', true)::uuid
        AND EXISTS (
            SELECT 1 FROM users 
            WHERE id = current_setting('app.current_user_id', true)::uuid
            AND role = 'student'
        )
    );

-- Teachers can view interactions for their lectures
CREATE POLICY lecture_interactions_teacher_select ON lecture_student_interactions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM lecture_assignments la
            WHERE la.id = lecture_student_interactions.lecture_id
            AND la.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    );

-- Helper function to get lecture path for a student
CREATE OR REPLACE FUNCTION get_student_lecture_path(
    p_student_id UUID,
    p_assignment_id UUID
) RETURNS JSONB AS $$
DECLARE
    v_path JSONB;
BEGIN
    SELECT COALESCE(progress_metadata->>'lecture_path', '[]')::JSONB
    INTO v_path
    FROM student_assignments
    WHERE id = p_assignment_id
    AND student_id = p_student_id;
    
    RETURN COALESCE(v_path, '[]'::JSONB);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;