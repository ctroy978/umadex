-- Remove date-related indexes
DROP INDEX IF EXISTS idx_reading_assignments_start_date;
DROP INDEX IF EXISTS idx_reading_assignments_end_date;

-- Remove check constraint
ALTER TABLE reading_assignments 
DROP CONSTRAINT IF EXISTS check_date_order;

-- Remove date columns
ALTER TABLE reading_assignments 
DROP COLUMN IF EXISTS start_date,
DROP COLUMN IF EXISTS end_date;