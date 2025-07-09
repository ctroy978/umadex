-- Add soft delete functionality to classroom_assignments
-- This allows teachers to remove assignments from classrooms while preserving all student work

-- Add removed_from_classroom_at column to track when an assignment was removed
ALTER TABLE classroom_assignments 
ADD COLUMN removed_from_classroom_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add removed_by column to track which teacher removed the assignment
ALTER TABLE classroom_assignments 
ADD COLUMN removed_by UUID REFERENCES users(id) DEFAULT NULL;

-- Create an index for efficient filtering of active assignments
CREATE INDEX idx_classroom_assignments_active 
ON classroom_assignments(classroom_id, removed_from_classroom_at) 
WHERE removed_from_classroom_at IS NULL;

-- Add comment explaining the soft delete approach
COMMENT ON COLUMN classroom_assignments.removed_from_classroom_at IS 
'Timestamp when the assignment was removed from the classroom. NULL means the assignment is active. When set, students can no longer access or work on this assignment, but all their work is preserved.';

COMMENT ON COLUMN classroom_assignments.removed_by IS 
'ID of the teacher who removed this assignment from the classroom.';