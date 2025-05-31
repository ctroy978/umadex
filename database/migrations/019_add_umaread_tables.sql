-- UMARead Database Schema
-- Module-specific tables for reading comprehension assignments

-- =====================================================
-- 1. QUESTION CACHE TABLES
-- =====================================================

-- Cache for AI-generated questions at each difficulty level
CREATE TABLE reading_question_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('summary', 'comprehension')),
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    
    -- Question content
    question_text TEXT NOT NULL,
    question_metadata JSONB DEFAULT '{}', -- for storing rubric, hints, etc.
    
    -- Generation metadata
    ai_model VARCHAR(100) NOT NULL,
    generation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Summary questions don't have difficulty levels
    CHECK (
        (question_type = 'summary' AND difficulty_level IS NULL) OR
        (question_type = 'comprehension' AND difficulty_level IS NOT NULL)
    ),
    
    UNIQUE(assignment_id, chunk_number, question_type, difficulty_level)
);

-- Track question cache flushes for audit purposes
CREATE TABLE reading_cache_flush_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id),
    reason TEXT,
    questions_flushed INTEGER NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================
-- 2. STUDENT RESPONSE TABLES
-- =====================================================

-- Track individual question attempts within chunks
CREATE TABLE reading_student_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('summary', 'comprehension')),
    
    -- Link to cached question if available
    question_cache_id UUID REFERENCES reading_question_cache(id) ON DELETE SET NULL,
    
    -- Store question text in case cache is flushed
    question_text TEXT NOT NULL,
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    
    -- Student response data
    student_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempt_number INTEGER NOT NULL,
    time_spent_seconds INTEGER NOT NULL,
    
    -- AI feedback for wrong answers
    ai_feedback TEXT,
    feedback_metadata JSONB DEFAULT '{}',
    
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure comprehension questions have difficulty level
    CHECK (
        (question_type = 'summary' AND difficulty_level IS NULL) OR
        (question_type = 'comprehension' AND difficulty_level IS NOT NULL)
    )
);

-- =====================================================
-- 3. COMPREHENSIVE TEST TABLES
-- =====================================================

-- Store generated comprehensive tests
CREATE TABLE reading_comprehensive_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    
    -- Test configuration
    total_questions INTEGER NOT NULL,
    passing_score INTEGER NOT NULL,
    time_limit_minutes INTEGER,
    
    -- Test questions stored as JSONB array
    test_questions JSONB NOT NULL,
    /* Structure:
    [
        {
            "question_number": 1,
            "question_type": "multiple_choice|short_answer|essay",
            "question_text": "...",
            "options": ["A", "B", "C", "D"], // for multiple choice
            "correct_answer": "B", // for multiple choice
            "rubric": {...}, // for short answer/essay
            "points": 10,
            "chunk_reference": 3 // which chunk this relates to
        }
    ]
    */
    
    -- Generation metadata
    ai_model VARCHAR(100) NOT NULL,
    generation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track student test attempts
CREATE TABLE reading_test_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    test_id UUID NOT NULL REFERENCES reading_comprehensive_tests(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    
    -- Test status
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' 
        CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    
    -- Results
    score INTEGER,
    passed BOOLEAN,
    
    -- Detailed answers stored as JSONB
    answers JSONB DEFAULT '[]',
    /* Structure:
    [
        {
            "question_number": 1,
            "student_answer": "B",
            "is_correct": true,
            "points_earned": 10,
            "ai_feedback": "..." // for essay/short answer
        }
    ]
    */
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Only one active attempt per student per test
    UNIQUE(student_id, test_id, status) WHERE status = 'in_progress'
);

-- =====================================================
-- 4. INDEXES FOR PERFORMANCE
-- =====================================================

-- Question cache lookups
CREATE INDEX idx_reading_question_cache_lookup 
    ON reading_question_cache(assignment_id, chunk_number, question_type, difficulty_level);

-- Student response queries
CREATE INDEX idx_reading_responses_student 
    ON reading_student_responses(student_id, assignment_id, chunk_number);

CREATE INDEX idx_reading_responses_occurred 
    ON reading_student_responses(occurred_at DESC);

-- Test attempt lookups
CREATE INDEX idx_reading_test_attempts_student 
    ON reading_test_attempts(student_id, assignment_id, status);

-- Cache flush audit
CREATE INDEX idx_reading_cache_flush_assignment 
    ON reading_cache_flush_log(assignment_id, created_at DESC);

-- =====================================================
-- 5. ROW LEVEL SECURITY POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE reading_question_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_cache_flush_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_student_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_comprehensive_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_test_attempts ENABLE ROW LEVEL SECURITY;

-- Question cache policies
CREATE POLICY "Teachers can view question cache for their assignments"
    ON reading_question_cache FOR SELECT
    USING (
        assignment_id IN (
            SELECT id FROM reading_assignments 
            WHERE teacher_id = auth.uid()
        )
    );

CREATE POLICY "Teachers can manage question cache for their assignments"
    ON reading_question_cache FOR ALL
    USING (
        assignment_id IN (
            SELECT id FROM reading_assignments 
            WHERE teacher_id = auth.uid()
        )
    );

-- Students can view questions when attempting assignments
CREATE POLICY "Students can view questions for active assignments"
    ON reading_question_cache FOR SELECT
    USING (
        assignment_id IN (
            SELECT sa.assignment_id 
            FROM student_assignments sa
            WHERE sa.student_id = auth.uid()
            AND sa.status IN ('in_progress', 'test_available')
        )
    );

-- Cache flush log policies
CREATE POLICY "Teachers can view their cache flush logs"
    ON reading_cache_flush_log FOR SELECT
    USING (teacher_id = auth.uid());

CREATE POLICY "Teachers can create cache flush logs"
    ON reading_cache_flush_log FOR INSERT
    WITH CHECK (teacher_id = auth.uid());

-- Student response policies
CREATE POLICY "Students can view their own responses"
    ON reading_student_responses FOR SELECT
    USING (student_id = auth.uid());

CREATE POLICY "Students can create their own responses"
    ON reading_student_responses FOR INSERT
    WITH CHECK (student_id = auth.uid());

CREATE POLICY "Teachers can view responses for their assignments"
    ON reading_student_responses FOR SELECT
    USING (
        assignment_id IN (
            SELECT id FROM reading_assignments 
            WHERE teacher_id = auth.uid()
        )
    );

-- Comprehensive test policies
CREATE POLICY "Teachers can manage tests for their assignments"
    ON reading_comprehensive_tests FOR ALL
    USING (
        assignment_id IN (
            SELECT id FROM reading_assignments 
            WHERE teacher_id = auth.uid()
        )
    );

CREATE POLICY "Students can view tests for completed assignments"
    ON reading_comprehensive_tests FOR SELECT
    USING (
        assignment_id IN (
            SELECT sa.assignment_id 
            FROM student_assignments sa
            WHERE sa.student_id = auth.uid()
            AND sa.status IN ('test_available', 'test_completed')
        )
    );

-- Test attempt policies
CREATE POLICY "Students can manage their own test attempts"
    ON reading_test_attempts FOR ALL
    USING (student_id = auth.uid());

CREATE POLICY "Teachers can view test attempts for their assignments"
    ON reading_test_attempts FOR SELECT
    USING (
        assignment_id IN (
            SELECT id FROM reading_assignments 
            WHERE teacher_id = auth.uid()
        )
    );

-- =====================================================
-- 6. HELPER FUNCTIONS
-- =====================================================

-- Function to flush question cache for an assignment
CREATE OR REPLACE FUNCTION flush_reading_question_cache(
    p_assignment_id UUID,
    p_teacher_id UUID,
    p_reason TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Count questions to be deleted
    SELECT COUNT(*) INTO v_count
    FROM reading_question_cache
    WHERE assignment_id = p_assignment_id;
    
    -- Delete questions
    DELETE FROM reading_question_cache
    WHERE assignment_id = p_assignment_id;
    
    -- Log the flush
    INSERT INTO reading_cache_flush_log (
        assignment_id, teacher_id, reason, questions_flushed
    ) VALUES (
        p_assignment_id, p_teacher_id, p_reason, v_count
    );
    
    RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if a student can proceed to next chunk
CREATE OR REPLACE FUNCTION can_proceed_to_next_chunk(
    p_student_id UUID,
    p_assignment_id UUID,
    p_chunk_number INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_summary_correct BOOLEAN;
    v_comprehension_correct BOOLEAN;
BEGIN
    -- Check if both questions answered correctly
    SELECT 
        MAX(CASE WHEN question_type = 'summary' AND is_correct THEN TRUE ELSE FALSE END),
        MAX(CASE WHEN question_type = 'comprehension' AND is_correct THEN TRUE ELSE FALSE END)
    INTO v_summary_correct, v_comprehension_correct
    FROM reading_student_responses
    WHERE student_id = p_student_id
    AND assignment_id = p_assignment_id
    AND chunk_number = p_chunk_number;
    
    RETURN COALESCE(v_summary_correct, FALSE) AND COALESCE(v_comprehension_correct, FALSE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =====================================================
-- 7. UPDATE TRIGGERS
-- =====================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_reading_question_cache_updated_at
    BEFORE UPDATE ON reading_question_cache
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reading_comprehensive_tests_updated_at
    BEFORE UPDATE ON reading_comprehensive_tests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reading_test_attempts_updated_at
    BEFORE UPDATE ON reading_test_attempts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();