-- UMATest Module Phase 1: Test Creation System
-- This migration creates the database schema for the UMATest module
-- Following patterns established by UMARead module

-- Main test assignments table (following reading_assignments pattern)
CREATE TABLE test_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Test metadata
    test_title VARCHAR(255) NOT NULL,
    test_description TEXT,
    
    -- Selected lectures (array of reading_assignment IDs that are UMALecture type)
    selected_lecture_ids UUID[] NOT NULL,
    
    -- Test configuration
    time_limit_minutes INTEGER, -- NULL means no time limit
    attempt_limit INTEGER DEFAULT 1, -- Number of attempts allowed
    randomize_questions BOOLEAN DEFAULT FALSE,
    show_feedback_immediately BOOLEAN DEFAULT TRUE,
    
    -- Generated test content (JSONB for flexibility)
    test_structure JSONB NOT NULL DEFAULT '{}'::JSONB,
    /*
    test_structure format:
    {
      "total_questions": 50,
      "topics": {
        "topic_id_1": {
          "topic_title": "Introduction to Photosynthesis",
          "source_lecture_id": "uuid",
          "source_lecture_title": "Biology Basics",
          "questions": [
            {
              "id": "q_uuid_1",
              "question_text": "What is the primary function of chloroplasts?",
              "difficulty_level": "basic", // basic, intermediate, advanced, expert
              "source_content": "Chloroplasts are organelles...", // For reference
              "answer_key": {
                "correct_answer": "To perform photosynthesis",
                "explanation": "Chloroplasts contain chlorophyll...",
                "evaluation_rubric": "Accept answers mentioning photosynthesis, light capture, or energy production"
              }
            }
          ]
        }
      },
      "generation_metadata": {
        "generated_at": "2024-01-20T10:00:00Z",
        "ai_model": "claude-3-sonnet",
        "distribution": {
          "basic_intermediate": 70,
          "advanced": 20,
          "expert": 10
        }
      }
    }
    */
    
    -- Status management (following reading_assignments pattern)
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    
    -- Timestamps and soft delete (following UMARead pattern)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_lecture_ids CHECK (array_length(selected_lecture_ids, 1) > 0),
    CONSTRAINT valid_time_limit CHECK (time_limit_minutes IS NULL OR time_limit_minutes > 0),
    CONSTRAINT valid_attempt_limit CHECK (attempt_limit > 0)
);

-- Create indexes for performance
CREATE INDEX idx_test_assignments_teacher_id ON test_assignments(teacher_id);
CREATE INDEX idx_test_assignments_status ON test_assignments(status);
CREATE INDEX idx_test_assignments_deleted_at ON test_assignments(deleted_at);
CREATE INDEX idx_test_assignments_created_at ON test_assignments(created_at DESC);

-- Partial index for active tests (not deleted)
CREATE INDEX idx_test_assignments_active ON test_assignments(teacher_id, status) 
WHERE deleted_at IS NULL;

-- GIN index for searching within test_structure JSONB
CREATE INDEX idx_test_assignments_structure ON test_assignments USING GIN (test_structure);

-- Question generation cache table (following reading_question_cache pattern)
CREATE TABLE test_question_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Cache key components
    lecture_id UUID NOT NULL,
    topic_id VARCHAR(255) NOT NULL,
    difficulty_level VARCHAR(20) NOT NULL CHECK (difficulty_level IN ('basic', 'intermediate', 'advanced', 'expert')),
    content_hash VARCHAR(64) NOT NULL, -- SHA256 hash of the source content
    
    -- Cached questions (array of questions for this topic/level)
    questions JSONB NOT NULL DEFAULT '[]'::JSONB,
    /*
    questions format:
    [
      {
        "question_text": "What is photosynthesis?",
        "answer_key": {
          "correct_answer": "...",
          "explanation": "...",
          "evaluation_rubric": "..."
        },
        "source_excerpt": "..." // Relevant part of source content
      }
    ]
    */
    
    -- AI generation metadata
    ai_model VARCHAR(100) DEFAULT 'claude-3-sonnet',
    generation_timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure uniqueness
    CONSTRAINT unique_test_question_cache UNIQUE (lecture_id, topic_id, difficulty_level, content_hash)
);

-- Create indexes for cache lookups
CREATE INDEX idx_test_question_cache_lookup ON test_question_cache(lecture_id, topic_id, difficulty_level);

-- Test generation log table (for tracking AI processing)
CREATE TABLE test_generation_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_assignment_id UUID REFERENCES test_assignments(id) ON DELETE CASCADE,
    
    -- Processing details
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) CHECK (status IN ('processing', 'completed', 'failed')),
    error_message TEXT,
    
    -- Generation statistics
    total_topics_processed INTEGER DEFAULT 0,
    total_questions_generated INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    cache_misses INTEGER DEFAULT 0,
    
    -- AI usage tracking
    ai_tokens_used INTEGER DEFAULT 0,
    ai_model VARCHAR(100)
);

CREATE INDEX idx_test_generation_log_assignment ON test_generation_log(test_assignment_id);

-- Updated timestamp trigger (following UMARead pattern)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_test_assignments_updated_at BEFORE UPDATE
    ON test_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (following UMARead pattern)
ALTER TABLE test_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_question_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_generation_log ENABLE ROW LEVEL SECURITY;

-- RLS Policies for test_assignments
-- Teachers can only see their own tests
CREATE POLICY "Teachers can view their own tests" ON test_assignments
    FOR SELECT USING (teacher_id IS NOT NULL AND deleted_at IS NULL);

CREATE POLICY "Teachers can create tests" ON test_assignments
    FOR INSERT WITH CHECK (teacher_id IS NOT NULL);

CREATE POLICY "Teachers can update their own tests" ON test_assignments
    FOR UPDATE USING (teacher_id IS NOT NULL AND deleted_at IS NULL);

CREATE POLICY "Teachers can soft delete their own tests" ON test_assignments
    FOR UPDATE USING (teacher_id IS NOT NULL) WITH CHECK (teacher_id IS NOT NULL);

-- RLS Policies for test_question_cache (read-only for all authenticated users)
CREATE POLICY "Authenticated users can view question cache" ON test_question_cache
    FOR SELECT USING (true);

-- Only system can insert into cache
CREATE POLICY "System can manage question cache" ON test_question_cache
    FOR ALL USING (true);

-- RLS Policies for test_generation_log
CREATE POLICY "Teachers can view their test generation logs" ON test_generation_log
    FOR SELECT USING (
        test_assignment_id IN (
            SELECT id FROM test_assignments WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Helper function to validate selected lectures are UMALecture type
CREATE OR REPLACE FUNCTION validate_selected_lectures()
RETURNS TRIGGER AS $$
BEGIN
    -- Check that all selected lecture IDs are valid UMALecture assignments
    IF EXISTS (
        SELECT 1
        FROM unnest(NEW.selected_lecture_ids) AS lecture_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM reading_assignments
            WHERE id = lecture_id
            AND assignment_type = 'UMALecture'
            AND deleted_at IS NULL
            AND teacher_id = NEW.teacher_id
        )
    ) THEN
        RAISE EXCEPTION 'All selected lectures must be valid UMALecture assignments owned by the teacher';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_selected_lectures_trigger
    BEFORE INSERT OR UPDATE ON test_assignments
    FOR EACH ROW EXECUTE FUNCTION validate_selected_lectures();

-- Future tables (commented out for Phase 2)
-- CREATE TABLE test_attempts (...) -- Student test attempts
-- CREATE TABLE test_responses (...) -- Individual question responses
-- CREATE TABLE test_grades (...) -- Final grades and feedback