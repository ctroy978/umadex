-- Increase the length of bypass_code column to support longer codes
ALTER TABLE teacher_bypass_codes 
ALTER COLUMN bypass_code TYPE VARCHAR(20);