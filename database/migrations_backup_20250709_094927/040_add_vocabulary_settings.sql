-- Add vocabulary settings to classroom assignments
-- This allows teachers to configure how vocabulary words are delivered to students

-- Add vocab_settings JSONB column to store vocabulary-specific settings
ALTER TABLE classroom_assignments 
ADD COLUMN vocab_settings JSONB DEFAULT '{}';

-- Add comment explaining the structure
COMMENT ON COLUMN classroom_assignments.vocab_settings IS 'Vocabulary-specific settings like delivery method, group size, test configuration. Empty object {} means "all at once" mode (default).';

-- Example structure:
-- {
--   "delivery_mode": "all_at_once" | "in_groups" | "teacher_controlled",
--   "group_size": 5-8 (only for in_groups/teacher_controlled),
--   "release_condition": "immediate" | "after_test" (only for in_groups),
--   "allow_test_retakes": true/false,
--   "max_test_attempts": 2,
--   "released_groups": [1, 2, 3] (only for teacher_controlled, tracks which groups have been released)
-- }
-- 
-- Note: Test time restrictions are handled at the classroom level via classroom_test_schedules
-- and apply to both UMARead and UMAVocab tests consistently.

-- Create index for better query performance on vocabulary assignments with settings
CREATE INDEX idx_classroom_assignments_vocab_settings ON classroom_assignments(id) 
WHERE assignment_type = 'vocabulary' AND vocab_settings != '{}';