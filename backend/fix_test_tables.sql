-- Fix test_question_evaluations table schema
-- This script fixes the mismatch between the database schema and the application models

-- First, check if UUID extension is enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop the existing table if it exists (backup data first if needed!)
DROP TABLE IF EXISTS test_question_evaluations CASCADE;

-- Recreate the table with the correct schema matching the SQLAlchemy model
CREATE TABLE test_question_evaluations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id) ON DELETE CASCADE,
    question_index INTEGER NOT NULL,
    question_number INTEGER NOT NULL,
    question_text TEXT,
    student_answer TEXT,
    rubric_score INTEGER NOT NULL CHECK (rubric_score >= 0 AND rubric_score <= 4),
    points_earned DECIMAL(5,2) NOT NULL CHECK (points_earned >= 0),
    max_points DECIMAL(5,2) NOT NULL CHECK (max_points > 0),
    scoring_rationale TEXT NOT NULL,
    feedback_text TEXT,
    key_concepts_identified JSONB DEFAULT '[]'::jsonb,
    misconceptions_detected JSONB DEFAULT '[]'::jsonb,
    evaluation_confidence DECIMAL(3,2) NOT NULL CHECK (evaluation_confidence >= 0 AND evaluation_confidence <= 1),
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_test_question_evaluations_attempt_id ON test_question_evaluations(test_attempt_id);
CREATE INDEX idx_test_question_evaluations_question ON test_question_evaluations(test_attempt_id, question_index);

-- Add any missing columns to student_test_attempts if they don't exist
DO $$ 
BEGIN
    -- Check if evaluated_at column exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'student_test_attempts' 
                   AND column_name = 'evaluated_at') THEN
        ALTER TABLE student_test_attempts ADD COLUMN evaluated_at TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Check if grace_period_end column exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'student_test_attempts' 
                   AND column_name = 'grace_period_end') THEN
        ALTER TABLE student_test_attempts ADD COLUMN grace_period_end TIMESTAMP WITH TIME ZONE;
    END IF;
    
    -- Check if started_within_schedule column exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'student_test_attempts' 
                   AND column_name = 'started_within_schedule') THEN
        ALTER TABLE student_test_attempts ADD COLUMN started_within_schedule BOOLEAN DEFAULT TRUE;
    END IF;
    
    -- Check if override_code_used column exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'student_test_attempts' 
                   AND column_name = 'override_code_used') THEN
        ALTER TABLE student_test_attempts ADD COLUMN override_code_used UUID;
    END IF;
    
    -- Check if schedule_violation_reason column exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'student_test_attempts' 
                   AND column_name = 'schedule_violation_reason') THEN
        ALTER TABLE student_test_attempts ADD COLUMN schedule_violation_reason TEXT;
    END IF;
END $$;

-- Ensure test_security_incidents table exists
CREATE TABLE IF NOT EXISTS test_security_incidents (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id),
    student_id UUID NOT NULL REFERENCES users(id),
    incident_type VARCHAR(50) NOT NULL CHECK (incident_type IN ('focus_loss', 'tab_switch', 'navigation_attempt', 'window_blur', 'app_switch', 'orientation_cheat')),
    incident_data JSONB,
    resulted_in_lock BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Ensure teacher_bypass_codes table exists
CREATE TABLE IF NOT EXISTS teacher_bypass_codes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    teacher_id UUID NOT NULL REFERENCES users(id),
    context_type VARCHAR(50) DEFAULT 'test',
    context_id UUID,
    student_id UUID REFERENCES users(id),
    bypass_code VARCHAR(8) NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Grant necessary permissions (adjust the user as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_db_user;

COMMIT;