-- Add support for vocabulary assignments in classrooms

-- First, add assignment_type to classroom_assignments to support different types
ALTER TABLE classroom_assignments 
ADD COLUMN assignment_type VARCHAR(50) NOT NULL DEFAULT 'reading';

-- Update existing records to have 'reading' type
UPDATE classroom_assignments SET assignment_type = 'reading';

-- Now we need to modify the foreign key constraint to be conditional
-- Drop the existing foreign key constraint
ALTER TABLE classroom_assignments 
DROP CONSTRAINT IF EXISTS classroom_assignments_assignment_id_fkey;

-- No need to drop primary key since it's now on the id column

-- Add a nullable vocabulary_list_id column
ALTER TABLE classroom_assignments 
ADD COLUMN vocabulary_list_id UUID REFERENCES vocabulary_lists(id);

-- Make assignment_id nullable since we'll use either assignment_id or vocabulary_list_id
ALTER TABLE classroom_assignments 
ALTER COLUMN assignment_id DROP NOT NULL;

-- We'll add a proper unique constraint later after setting up the check constraint

-- Add check constraint to ensure exactly one assignment reference is set
ALTER TABLE classroom_assignments
ADD CONSTRAINT check_assignment_reference CHECK (
    (assignment_type = 'reading' AND assignment_id IS NOT NULL AND vocabulary_list_id IS NULL) OR
    (assignment_type = 'vocabulary' AND assignment_id IS NULL AND vocabulary_list_id IS NOT NULL)
);

-- Update the unique constraint to include assignment_type
ALTER TABLE classroom_assignments
DROP CONSTRAINT IF EXISTS _classroom_assignment_uc;

-- Add a new unique constraint
ALTER TABLE classroom_assignments
ADD CONSTRAINT _classroom_assignment_uc UNIQUE (classroom_id, assignment_id, vocabulary_list_id);

-- Create indexes for performance
CREATE INDEX idx_classroom_assignments_vocabulary ON classroom_assignments(vocabulary_list_id) 
WHERE vocabulary_list_id IS NOT NULL;

-- Add foreign key constraints only if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'classroom_assignments_assignment_id_fkey'
    ) THEN
        ALTER TABLE classroom_assignments
        ADD CONSTRAINT classroom_assignments_assignment_id_fkey 
        FOREIGN KEY (assignment_id) REFERENCES reading_assignments(id) ON DELETE CASCADE;
    END IF;

    -- vocabulary_list_id constraint is already created with the column definition
END $$;

-- Update RLS policies for vocabulary_lists to use the new structure
DROP POLICY IF EXISTS vocabulary_lists_select ON vocabulary_lists;

CREATE POLICY vocabulary_lists_select ON vocabulary_lists
    FOR SELECT
    USING (
        teacher_id = current_setting('app.current_user_id')::UUID
        OR current_setting('app.current_user_role') = 'admin'
        OR EXISTS (
            SELECT 1 FROM classroom_assignments ca
            JOIN classroom_students cs ON cs.classroom_id = ca.classroom_id
            WHERE ca.vocabulary_list_id = vocabulary_lists.id
            AND ca.assignment_type = 'vocabulary'
            AND cs.student_id = current_setting('app.current_user_id')::UUID
            AND cs.removed_at IS NULL
            AND (ca.end_date IS NULL OR ca.end_date > CURRENT_TIMESTAMP)
        )
    );

-- Update RLS policies for vocabulary_words
DROP POLICY IF EXISTS vocabulary_words_all ON vocabulary_words;

CREATE POLICY vocabulary_words_all ON vocabulary_words
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM vocabulary_lists vl
            WHERE vl.id = vocabulary_words.list_id
            AND (
                vl.teacher_id = current_setting('app.current_user_id')::UUID
                OR current_setting('app.current_user_role') = 'admin'
                OR EXISTS (
                    SELECT 1 FROM classroom_assignments ca
                    JOIN classroom_students cs ON cs.classroom_id = ca.classroom_id
                    WHERE ca.vocabulary_list_id = vl.id
                    AND ca.assignment_type = 'vocabulary'
                    AND cs.student_id = current_setting('app.current_user_id')::UUID
                    AND cs.removed_at IS NULL
                    AND (ca.end_date IS NULL OR ca.end_date > CURRENT_TIMESTAMP)
                )
            )
        )
    );

-- Add comment
COMMENT ON COLUMN classroom_assignments.assignment_type IS 'Type of assignment: reading or vocabulary';
COMMENT ON COLUMN classroom_assignments.vocabulary_list_id IS 'Reference to vocabulary_lists table when assignment_type is vocabulary';