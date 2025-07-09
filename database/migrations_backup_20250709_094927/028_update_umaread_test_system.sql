-- Update UMARead test system tables with additional columns

-- Add missing columns to assignment_tests
ALTER TABLE assignment_tests 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'archived')),
ADD COLUMN IF NOT EXISTS teacher_notes TEXT,
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Foreign key already references reading_assignments correctly

-- Make expires_at nullable for draft tests
ALTER TABLE assignment_tests 
ALTER COLUMN expires_at DROP NOT NULL;

-- Add missing columns to test_results
ALTER TABLE test_results
ADD COLUMN IF NOT EXISTS attempt_number INTEGER NOT NULL DEFAULT 1;

-- Add unique constraint for attempt tracking
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'test_results_test_student_attempt_unique'
    ) THEN
        ALTER TABLE test_results
        ADD CONSTRAINT test_results_test_student_attempt_unique 
        UNIQUE(test_id, student_id, attempt_number);
    END IF;
END $$;

-- Add check constraint for score
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'test_results_overall_score_check'
    ) THEN
        ALTER TABLE test_results
        ADD CONSTRAINT test_results_overall_score_check 
        CHECK (overall_score >= 0 AND overall_score <= 100);
    END IF;
END $$;