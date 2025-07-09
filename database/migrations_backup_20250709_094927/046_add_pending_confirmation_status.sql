-- Add pending_confirmation status to vocabulary game attempts
-- This allows vocabulary challenges to use the confirmation flow like other activities

ALTER TABLE vocabulary_game_attempts 
DROP CONSTRAINT vocabulary_game_attempts_status_check;

ALTER TABLE vocabulary_game_attempts 
ADD CONSTRAINT vocabulary_game_attempts_status_check 
CHECK (status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined'));

-- Update student_assignments unique constraint to include subtype
-- This allows multiple StudentAssignment records per student/assignment for different activity subtypes

ALTER TABLE student_assignments 
DROP CONSTRAINT student_assignments_student_id_assignment_id_classroom_assi_key;

CREATE UNIQUE INDEX student_assignments_unique_subtype_idx
ON student_assignments (student_id, assignment_id, classroom_assignment_id, (progress_metadata->>'subtype'));