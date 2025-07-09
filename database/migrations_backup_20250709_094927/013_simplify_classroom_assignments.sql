-- Remove date fields from classroom_assignments table
ALTER TABLE classroom_assignments 
DROP COLUMN IF EXISTS start_date,
DROP COLUMN IF EXISTS due_date;

-- Ensure we have the correct structure
-- The table should only have: classroom_id, assignment_id, assigned_at, display_order