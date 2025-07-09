-- Add policies that depend on student_assignments table
-- These were originally in migration 019 but need to come after migration 020

-- Students can view questions when attempting assignments
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'reading_question_cache' 
        AND policyname = 'Students can view questions for active assignments'
    ) THEN
        CREATE POLICY "Students can view questions for active assignments"
            ON reading_question_cache FOR SELECT
            USING (
                assignment_id IN (
                    SELECT sa.assignment_id 
                    FROM student_assignments sa
                    WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
                    AND sa.status IN ('in_progress', 'test_available')
                )
            );
    END IF;
END
$$;

-- Students can view tests for completed assignments
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'reading_comprehensive_tests' 
        AND policyname = 'Students can view tests for completed assignments'
    ) THEN
        CREATE POLICY "Students can view tests for completed assignments"
            ON reading_comprehensive_tests FOR SELECT
            USING (
                assignment_id IN (
                    SELECT sa.assignment_id 
                    FROM student_assignments sa
                    WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
                    AND sa.status IN ('test_available', 'test_completed')
                )
            );
    END IF;
END
$$;