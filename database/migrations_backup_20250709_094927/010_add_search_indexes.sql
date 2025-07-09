-- Add indexes for search performance on reading_assignments table

-- Index for text search on assignment_title
CREATE INDEX IF NOT EXISTS idx_reading_assignments_assignment_title 
ON reading_assignments USING gin(to_tsvector('english', assignment_title));

-- Index for text search on work_title
CREATE INDEX IF NOT EXISTS idx_reading_assignments_work_title 
ON reading_assignments USING gin(to_tsvector('english', work_title));

-- Index for text search on author (with null check)
CREATE INDEX IF NOT EXISTS idx_reading_assignments_author 
ON reading_assignments USING gin(to_tsvector('english', COALESCE(author, '')));

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_reading_assignments_filters 
ON reading_assignments(teacher_id, deleted_at, created_at DESC);

-- Index for grade_level filter
CREATE INDEX IF NOT EXISTS idx_reading_assignments_grade_level 
ON reading_assignments(grade_level) WHERE deleted_at IS NULL;

-- Index for work_type filter
CREATE INDEX IF NOT EXISTS idx_reading_assignments_work_type 
ON reading_assignments(work_type) WHERE deleted_at IS NULL;

-- Index for date range queries
CREATE INDEX IF NOT EXISTS idx_reading_assignments_created_at 
ON reading_assignments(created_at DESC) WHERE deleted_at IS NULL;