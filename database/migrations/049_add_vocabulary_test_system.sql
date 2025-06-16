-- Migration: Add Vocabulary Test System
-- Description: Implement comprehensive vocabulary testing with chaining, prerequisites, and gradebook integration
-- Author: Claude Code
-- Date: 2025-06-16

-- Add test chaining configuration to vocabulary_lists
ALTER TABLE vocabulary_lists 
ADD COLUMN chain_previous_tests BOOLEAN DEFAULT FALSE,
ADD COLUMN chain_weeks_back INTEGER DEFAULT 0;

-- Test configuration table
CREATE TABLE vocabulary_test_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    chain_enabled BOOLEAN DEFAULT FALSE,
    weeks_to_include INTEGER DEFAULT 1,  -- How many previous weeks to include
    questions_per_week INTEGER DEFAULT 5,  -- Questions from each included week
    current_week_questions INTEGER DEFAULT 10,  -- Questions from current week
    max_attempts INTEGER DEFAULT 3,
    time_limit_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track individual assignment completion and test eligibility
CREATE TABLE student_vocabulary_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id) ON DELETE CASCADE,
    
    -- Track completion of each assignment type
    flashcards_completed BOOLEAN DEFAULT FALSE,
    practice_completed BOOLEAN DEFAULT FALSE,
    challenge_completed BOOLEAN DEFAULT FALSE,
    sentences_completed BOOLEAN DEFAULT FALSE,
    
    -- Completion tracking
    assignments_completed_count INTEGER DEFAULT 0,
    test_eligible BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(student_id, vocabulary_list_id, classroom_assignment_id)
);

-- Store generated vocabulary tests
CREATE TABLE vocabulary_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id) ON DELETE CASCADE,
    
    -- Test configuration
    questions JSONB NOT NULL,  -- Array of question objects
    total_questions INTEGER NOT NULL,
    chained_lists JSONB DEFAULT '[]',  -- Array of list IDs included
    
    -- Metadata
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    max_attempts INTEGER DEFAULT 3,
    time_limit_minutes INTEGER DEFAULT 30,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Store student test attempts
CREATE TABLE vocabulary_test_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES vocabulary_tests(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Test data
    responses JSONB NOT NULL,  -- Student answers
    score_percentage DECIMAL(5,2) NOT NULL,
    questions_correct INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Extend gradebook system for vocabulary tests
CREATE TABLE gradebook_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    
    -- Assignment reference (polymorphic)
    assignment_type VARCHAR(20) NOT NULL CHECK (assignment_type IN ('umaread', 'umavocab_test', 'umadebate', 'umawrite', 'umaspeak')),
    assignment_id UUID NOT NULL,  -- References different tables based on type
    
    -- Scoring
    score_percentage DECIMAL(5,2) NOT NULL,
    points_earned DECIMAL(8,2),
    points_possible DECIMAL(8,2),
    
    -- Metadata
    attempt_number INTEGER DEFAULT 1,
    completed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    graded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Additional data (JSON for flexibility)
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_vocabulary_test_configs_vocabulary_list_id ON vocabulary_test_configs(vocabulary_list_id);
CREATE INDEX idx_student_vocabulary_progress_student_list ON student_vocabulary_progress(student_id, vocabulary_list_id);
CREATE INDEX idx_student_vocabulary_progress_test_eligible ON student_vocabulary_progress(test_eligible);
CREATE INDEX idx_vocabulary_tests_expires_at ON vocabulary_tests(expires_at);
CREATE INDEX idx_vocabulary_test_attempts_test_student ON vocabulary_test_attempts(test_id, student_id);
CREATE INDEX idx_vocabulary_test_attempts_status ON vocabulary_test_attempts(status);
CREATE INDEX idx_gradebook_entries_student_classroom ON gradebook_entries(student_id, classroom_id);
CREATE INDEX idx_gradebook_entries_assignment_type ON gradebook_entries(assignment_type);

-- Create function to update assignments_completed_count automatically
CREATE OR REPLACE FUNCTION update_vocabulary_progress_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate completed assignments count
    NEW.assignments_completed_count := 
        (CASE WHEN NEW.flashcards_completed THEN 1 ELSE 0 END) +
        (CASE WHEN NEW.practice_completed THEN 1 ELSE 0 END) +
        (CASE WHEN NEW.challenge_completed THEN 1 ELSE 0 END) +
        (CASE WHEN NEW.sentences_completed THEN 1 ELSE 0 END);
    
    -- Set test eligibility (3 or more assignments completed)
    NEW.test_eligible := NEW.assignments_completed_count >= 3;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update progress counts
CREATE TRIGGER trigger_update_vocabulary_progress_count
    BEFORE INSERT OR UPDATE ON student_vocabulary_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_vocabulary_progress_count();

-- Function to check if test time is allowed
CREATE OR REPLACE FUNCTION is_test_time_allowed(
    assignment_id INTEGER,
    check_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
RETURNS BOOLEAN AS $$
DECLARE
    assignment RECORD;
    restrictions JSONB;
    allowed_days TEXT[];
    allowed_times JSONB;
    current_day TEXT;
    check_time_time TIME;
    time_range JSONB;
    start_time TIME;
    end_time TIME;
BEGIN
    -- Get assignment with time restrictions
    SELECT test_start_date, test_end_date, test_time_restrictions
    INTO assignment
    FROM classroom_assignments
    WHERE id = assignment_id;
    
    -- Check if assignment exists
    IF assignment IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check date range
    IF assignment.test_start_date IS NOT NULL AND check_time < assignment.test_start_date THEN
        RETURN FALSE;
    END IF;
    
    IF assignment.test_end_date IS NOT NULL AND check_time > assignment.test_end_date THEN
        RETURN FALSE;
    END IF;
    
    -- If no time restrictions, allow access
    IF assignment.test_time_restrictions IS NULL OR assignment.test_time_restrictions = '{}' THEN
        RETURN TRUE;
    END IF;
    
    restrictions := assignment.test_time_restrictions;
    
    -- Check allowed days
    IF restrictions ? 'allowed_days' THEN
        allowed_days := ARRAY(SELECT jsonb_array_elements_text(restrictions->'allowed_days'));
        current_day := LOWER(TO_CHAR(check_time, 'Day'));
        current_day := TRIM(current_day);
        
        IF NOT (current_day = ANY(allowed_days)) THEN
            RETURN FALSE;
        END IF;
    END IF;
    
    -- Check allowed times
    IF restrictions ? 'allowed_times' THEN
        allowed_times := restrictions->'allowed_times';
        check_time_time := check_time::TIME;
        
        -- Check if current time falls within any allowed time range
        FOR time_range IN SELECT * FROM jsonb_array_elements(allowed_times)
        LOOP
            start_time := (time_range->>'start')::TIME;
            end_time := (time_range->>'end')::TIME;
            
            IF check_time_time >= start_time AND check_time_time <= end_time THEN
                RETURN TRUE;
            END IF;
        END LOOP;
        
        -- If no time ranges matched, return false
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;