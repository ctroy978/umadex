-- ============================================================================
-- PERFORMANCE INDEXES FOR UMAREAD
-- ============================================================================

-- Add indexes for reading_assignments queries
CREATE INDEX IF NOT EXISTS idx_reading_assignments_teacher_type_deleted 
ON reading_assignments(teacher_id, assignment_type, deleted_at)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_reading_assignments_created_at 
ON reading_assignments(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reading_assignments_search 
ON reading_assignments USING gin(to_tsvector('english', assignment_title || ' ' || COALESCE(work_title, '') || ' ' || COALESCE(author, '')));

-- Add index for assignment_tests lookup
CREATE INDEX IF NOT EXISTS idx_assignment_tests_assignment_id 
ON assignment_tests(assignment_id);

CREATE INDEX IF NOT EXISTS idx_assignment_tests_assignment_status 
ON assignment_tests(assignment_id, status);

-- Add composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_reading_assignments_teacher_status 
ON reading_assignments(teacher_id, status)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_reading_assignments_grade_work_type 
ON reading_assignments(grade_level, work_type)
WHERE deleted_at IS NULL;

-- Analyze tables to update statistics
ANALYZE reading_assignments;
ANALYZE assignment_tests;