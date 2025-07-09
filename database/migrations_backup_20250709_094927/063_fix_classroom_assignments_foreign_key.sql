-- Fix foreign key constraint for classroom_assignments to support debate assignments

-- Drop the existing foreign key that only references reading_assignments
ALTER TABLE classroom_assignments 
DROP CONSTRAINT classroom_assignments_assignment_id_fkey;

-- Note: We cannot create a foreign key that references multiple tables in PostgreSQL.
-- The assignment_id will be validated at the application level based on assignment_type.
-- The check constraint already ensures proper assignment_id usage based on type.

COMMENT ON COLUMN classroom_assignments.assignment_id IS 'References reading_assignments.id when assignment_type is "reading", or debate_assignments.id when assignment_type is "debate"';