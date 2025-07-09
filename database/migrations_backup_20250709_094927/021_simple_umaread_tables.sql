-- Simplified UMARead tables for testing (without RLS)

-- Question cache table
CREATE TABLE IF NOT EXISTS reading_question_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL,
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('summary', 'comprehension')),
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    
    question_text TEXT NOT NULL,
    question_metadata JSONB DEFAULT '{}',
    
    ai_model VARCHAR(100) NOT NULL,
    generation_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Student responses table
CREATE TABLE IF NOT EXISTS reading_student_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    assignment_id UUID NOT NULL,
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('summary', 'comprehension')),
    
    question_cache_id UUID,
    question_text TEXT NOT NULL,
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    
    student_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempt_number INTEGER NOT NULL,
    time_spent_seconds INTEGER NOT NULL,
    
    ai_feedback TEXT,
    feedback_metadata JSONB DEFAULT '{}',
    
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cache flush log
CREATE TABLE IF NOT EXISTS reading_cache_flush_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL,
    teacher_id UUID NOT NULL,
    reason TEXT,
    questions_flushed INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_reading_question_cache_lookup 
    ON reading_question_cache(assignment_id, chunk_number, question_type, difficulty_level);

CREATE INDEX IF NOT EXISTS idx_reading_responses_student 
    ON reading_student_responses(student_id, assignment_id, chunk_number);

CREATE INDEX IF NOT EXISTS idx_reading_responses_occurred 
    ON reading_student_responses(occurred_at DESC);