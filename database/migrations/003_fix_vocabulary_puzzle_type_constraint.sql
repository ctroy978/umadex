-- Fix vocabulary_puzzle_games puzzle_type constraint to include 'fill_blank'
-- This was missing from the consolidated schema but was in the original migration

-- Drop the existing constraint
ALTER TABLE vocabulary_puzzle_games 
DROP CONSTRAINT IF EXISTS vocabulary_puzzle_games_puzzle_type_check;

-- Add the updated constraint that includes 'fill_blank'
ALTER TABLE vocabulary_puzzle_games 
ADD CONSTRAINT vocabulary_puzzle_games_puzzle_type_check 
CHECK (puzzle_type IN ('scrambled', 'crossword_clue', 'word_match', 'fill_blank'));