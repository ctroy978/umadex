-- Fix classroom_assignments table to allow null assignment_id for vocabulary assignments
-- This is required because vocabulary assignments use vocabulary_list_id instead of assignment_id

ALTER TABLE classroom_assignments 
ALTER COLUMN assignment_id DROP NOT NULL;