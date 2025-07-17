-- Migration: Fix vocabulary puzzle type constraint
-- Description: Add 'fill_blank' to the allowed puzzle types
-- Date: 2025-07-17

-- Drop the existing constraint
ALTER TABLE vocabulary_puzzle_games 
DROP CONSTRAINT IF EXISTS check_puzzle_type;

-- Add the updated constraint with 'fill_blank' included
ALTER TABLE vocabulary_puzzle_games 
ADD CONSTRAINT check_puzzle_type 
CHECK (puzzle_type IN ('scrambled', 'crossword_clue', 'word_match', 'fill_blank'));

-- Also check if the constraint exists with a different name from older migrations
ALTER TABLE vocabulary_puzzle_games 
DROP CONSTRAINT IF EXISTS vocabulary_puzzle_games_puzzle_type_check;