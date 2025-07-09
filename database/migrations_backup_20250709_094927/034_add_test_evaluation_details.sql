-- Migration: Add detailed test evaluation storage
-- This extends the student_test_attempts table to store comprehensive evaluation data

-- Add evaluation-specific columns to student_test_attempts
ALTER TABLE student_test_attempts
ADD COLUMN IF NOT EXISTS evaluation_status VARCHAR(50) DEFAULT 'pending'
    CHECK (evaluation_status IN ('pending', 'evaluating', 'completed', 'failed', 'manual_review')),
ADD COLUMN IF NOT EXISTS evaluated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS evaluation_model VARCHAR(100),
ADD COLUMN IF NOT EXISTS evaluation_version VARCHAR(50),
ADD COLUMN IF NOT EXISTS raw_ai_response JSONB,
ADD COLUMN IF NOT EXISTS evaluation_metadata JSONB DEFAULT '{}';

-- Create table for individual question evaluations
CREATE TABLE IF NOT EXISTS test_question_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL CHECK (question_number >= 0 AND question_number <= 9),
    
    -- Question and answer data
    question_text TEXT NOT NULL,
    student_answer TEXT,
    answer_key TEXT,
    answer_explanation TEXT,
    
    -- Scoring data (4-point rubric scale)
    rubric_score INTEGER CHECK (rubric_score >= 0 AND rubric_score <= 4),
    points_earned INTEGER CHECK (points_earned IN (0, 2, 5, 8, 10)),
    scoring_rationale TEXT,
    
    -- Feedback and analysis
    feedback_text TEXT,
    key_concepts_identified JSONB DEFAULT '[]',
    misconceptions_detected JSONB DEFAULT '[]',
    evaluation_confidence DECIMAL(3,2) CHECK (evaluation_confidence >= 0 AND evaluation_confidence <= 1),
    
    -- Timing data
    time_spent_seconds INTEGER,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_question_evaluation UNIQUE(test_attempt_id, question_number)
);

-- Create table for evaluation audit and quality tracking
CREATE TABLE IF NOT EXISTS test_evaluation_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id) ON DELETE CASCADE,
    
    -- Evaluation tracking
    evaluation_attempt_number INTEGER DEFAULT 1,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    
    -- AI call details
    ai_model VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    ai_cost_estimate DECIMAL(10,4),
    
    -- Quality metrics
    average_confidence DECIMAL(3,2),
    score_distribution JSONB, -- {"0": count, "1": count, etc.}
    unusual_patterns JSONB DEFAULT '[]',
    requires_review BOOLEAN DEFAULT FALSE,
    review_reason TEXT,
    
    -- Error tracking
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    error_details JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for teacher evaluation overrides
CREATE TABLE IF NOT EXISTS teacher_evaluation_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id),
    question_number INTEGER, -- NULL means overall score override
    
    -- Override data
    original_score INTEGER,
    override_score INTEGER NOT NULL,
    override_reason TEXT NOT NULL,
    override_feedback TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_teacher_override UNIQUE(test_attempt_id, question_number)
);

-- Create indexes for performance
CREATE INDEX idx_question_evaluations_attempt ON test_question_evaluations(test_attempt_id);
CREATE INDEX idx_question_evaluations_score ON test_question_evaluations(rubric_score);
CREATE INDEX idx_evaluation_audits_attempt ON test_evaluation_audits(test_attempt_id);
CREATE INDEX idx_evaluation_audits_review ON test_evaluation_audits(requires_review) WHERE requires_review = TRUE;
CREATE INDEX idx_teacher_overrides_attempt ON teacher_evaluation_overrides(test_attempt_id);
CREATE INDEX idx_teacher_overrides_teacher ON teacher_evaluation_overrides(teacher_id);
CREATE INDEX idx_test_attempts_eval_status ON student_test_attempts(evaluation_status);

-- Add RLS policies for test_question_evaluations
ALTER TABLE test_question_evaluations ENABLE ROW LEVEL SECURITY;

-- Students can view their own question evaluations
CREATE POLICY question_evaluations_student_select ON test_question_evaluations
    FOR SELECT
    -- TO authenticated (removed - not using role-based access)
    USING (
        EXISTS (
            SELECT 1 FROM student_test_attempts sta
            WHERE sta.id = test_question_evaluations.test_attempt_id
            AND sta.student_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Teachers can view evaluations for their students
CREATE POLICY question_evaluations_teacher_select ON test_question_evaluations
    FOR SELECT
    -- TO authenticated (removed - not using role-based access)
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = current_setting('app.current_user_id', true)::uuid
            AND u.role = 'teacher'
        )
        AND EXISTS (
            SELECT 1 FROM student_test_attempts sta
            JOIN reading_assignments ra ON ra.id = sta.assignment_id
            WHERE sta.id = test_question_evaluations.test_attempt_id
            AND ra.teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Add RLS policies for test_evaluation_audits
ALTER TABLE test_evaluation_audits ENABLE ROW LEVEL SECURITY;

-- Only teachers can view evaluation audits
CREATE POLICY evaluation_audits_teacher_select ON test_evaluation_audits
    FOR SELECT
    -- TO authenticated (removed - not using role-based access)
    USING (
        EXISTS (
            SELECT 1 FROM users u
            WHERE u.id = current_setting('app.current_user_id', true)::uuid
            AND u.role = 'teacher'
        )
        AND EXISTS (
            SELECT 1 FROM student_test_attempts sta
            JOIN reading_assignments ra ON ra.id = sta.assignment_id
            WHERE sta.id = test_evaluation_audits.test_attempt_id
            AND ra.teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Add RLS policies for teacher_evaluation_overrides
ALTER TABLE teacher_evaluation_overrides ENABLE ROW LEVEL SECURITY;

-- Teachers can manage their own overrides
CREATE POLICY teacher_overrides_teacher_all ON teacher_evaluation_overrides
    FOR ALL
    -- TO authenticated (removed - not using role-based access)
    USING (teacher_id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (teacher_id = current_setting('app.current_user_id', true)::uuid);

-- Students can view overrides for their tests
CREATE POLICY teacher_overrides_student_select ON teacher_evaluation_overrides
    FOR SELECT
    -- TO authenticated (removed - not using role-based access)
    USING (
        EXISTS (
            SELECT 1 FROM student_test_attempts sta
            WHERE sta.id = teacher_evaluation_overrides.test_attempt_id
            AND sta.student_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Add trigger to update timestamps
CREATE TRIGGER test_question_evaluations_updated_at
    BEFORE UPDATE ON test_question_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Function to calculate final score considering overrides
CREATE OR REPLACE FUNCTION calculate_test_final_score(p_test_attempt_id UUID)
RETURNS TABLE (
    final_score DECIMAL(5,2),
    original_score DECIMAL(5,2),
    has_overrides BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH question_scores AS (
        SELECT 
            qe.question_number,
            COALESCE(teo.override_score, qe.points_earned) as final_points,
            qe.points_earned as original_points,
            CASE WHEN teo.id IS NOT NULL THEN TRUE ELSE FALSE END as is_overridden
        FROM test_question_evaluations qe
        LEFT JOIN teacher_evaluation_overrides teo 
            ON teo.test_attempt_id = qe.test_attempt_id 
            AND teo.question_number = qe.question_number
        WHERE qe.test_attempt_id = p_test_attempt_id
    ),
    overall_override AS (
        SELECT override_score
        FROM teacher_evaluation_overrides
        WHERE test_attempt_id = p_test_attempt_id
        AND question_number IS NULL
        LIMIT 1
    )
    SELECT 
        COALESCE(
            oo.override_score,
            SUM(qs.final_points)
        )::DECIMAL(5,2) as final_score,
        SUM(qs.original_points)::DECIMAL(5,2) as original_score,
        (COUNT(CASE WHEN qs.is_overridden THEN 1 END) > 0 OR oo.override_score IS NOT NULL) as has_overrides
    FROM question_scores qs
    LEFT JOIN overall_override oo ON TRUE
    GROUP BY oo.override_score;
END;
$$ LANGUAGE plpgsql;

-- Add function to check if evaluation needs review
CREATE OR REPLACE FUNCTION check_evaluation_quality(p_test_attempt_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_needs_review BOOLEAN := FALSE;
    v_score_distribution JSONB;
    v_avg_confidence DECIMAL(3,2);
    v_zero_count INTEGER;
    v_four_count INTEGER;
BEGIN
    -- Get score distribution and average confidence
    SELECT 
        jsonb_object_agg(rubric_score::text, count) as score_dist,
        AVG(evaluation_confidence) as avg_conf
    INTO v_score_distribution, v_avg_confidence
    FROM (
        SELECT rubric_score, COUNT(*) as count, evaluation_confidence
        FROM test_question_evaluations
        WHERE test_attempt_id = p_test_attempt_id
        GROUP BY rubric_score, evaluation_confidence
    ) scores;
    
    -- Check for suspicious patterns
    v_zero_count := COALESCE((v_score_distribution->>'0')::INTEGER, 0);
    v_four_count := COALESCE((v_score_distribution->>'4')::INTEGER, 0);
    
    -- Flag for review if:
    -- 1. All answers are scored 0 or 4 (too extreme)
    -- 2. Average confidence is below 0.7
    -- 3. More than 7 questions scored 0
    IF (v_zero_count + v_four_count = 10) OR 
       (v_avg_confidence < 0.7) OR 
       (v_zero_count > 7) THEN
        v_needs_review := TRUE;
    END IF;
    
    RETURN v_needs_review;
END;
$$ LANGUAGE plpgsql;