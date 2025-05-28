-- Add assignment_type field to reading_assignments
ALTER TABLE reading_assignments 
ADD COLUMN IF NOT EXISTS assignment_type VARCHAR(50) NOT NULL DEFAULT 'UMARead';

-- Add check constraint for valid assignment types
ALTER TABLE reading_assignments
ADD CONSTRAINT check_assignment_type CHECK (
  assignment_type IN ('UMARead', 'UMAVocab', 'UMADebate', 'UMAWrite', 'UMALecture')
);