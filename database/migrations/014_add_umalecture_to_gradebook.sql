-- Migration: Add UMALecture to gradebook assignment types
-- Date: 2025-07-22
-- Description: Updates the gradebook_entries assignment_type constraint to include 'umalecture'

-- Drop the existing constraint
ALTER TABLE gradebook_entries 
DROP CONSTRAINT IF EXISTS gradebook_entries_assignment_type_check;

-- Add the new constraint including 'umalecture'
ALTER TABLE gradebook_entries 
ADD CONSTRAINT gradebook_entries_assignment_type_check 
CHECK (assignment_type IN ('umaread', 'umavocab_test', 'umadebate', 'umawrite', 'umaspeak', 'umalecture'));

-- Add comment about the change
COMMENT ON COLUMN gradebook_entries.assignment_type IS 
'Type of assignment: umaread, umavocab_test, umadebate, umawrite, umaspeak, or umalecture';

-- Verify the constraint was updated
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.check_constraints 
        WHERE constraint_name = 'gradebook_entries_assignment_type_check'
        AND check_clause LIKE '%umalecture%'
    ) THEN
        RAISE EXCEPTION 'Failed to update gradebook_entries assignment_type constraint';
    END IF;
END $$;