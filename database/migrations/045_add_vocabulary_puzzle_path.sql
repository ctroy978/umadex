-- Add vocabulary puzzle path game system
-- This is Assignment 4 of the 4 practice activities: Word Puzzle Path

-- Table for storing generated puzzles for vocabulary words
CREATE TABLE vocabulary_puzzle_games (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    puzzle_type VARCHAR(50) NOT NULL CHECK (puzzle_type IN ('scrambled', 'crossword_clue', 'fill_blank', 'word_match')),
    puzzle_data JSONB NOT NULL,
    correct_answer VARCHAR(200) NOT NULL,
    puzzle_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(vocabulary_list_id, puzzle_order)
);

-- Indexes for performance
CREATE INDEX idx_vocab_puzzle_games_list ON vocabulary_puzzle_games(vocabulary_list_id);
CREATE INDEX idx_vocab_puzzle_games_word ON vocabulary_puzzle_games(word_id);
CREATE INDEX idx_vocab_puzzle_games_type ON vocabulary_puzzle_games(puzzle_type);

-- Table for storing student puzzle responses
CREATE TABLE vocabulary_puzzle_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    puzzle_id UUID NOT NULL REFERENCES vocabulary_puzzle_games(id) ON DELETE CASCADE,
    student_answer TEXT NOT NULL,
    ai_evaluation JSONB NOT NULL,
    puzzle_score INTEGER NOT NULL CHECK (puzzle_score BETWEEN 1 AND 4),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    time_spent_seconds INTEGER,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(practice_progress_id, puzzle_id, attempt_number)
);

-- Indexes
CREATE INDEX idx_vocab_puzzle_responses_student ON vocabulary_puzzle_responses(student_id);
CREATE INDEX idx_vocab_puzzle_responses_list ON vocabulary_puzzle_responses(vocabulary_list_id);
CREATE INDEX idx_vocab_puzzle_responses_progress ON vocabulary_puzzle_responses(practice_progress_id);
CREATE INDEX idx_vocab_puzzle_responses_puzzle ON vocabulary_puzzle_responses(puzzle_id);

-- Table for tracking puzzle path attempts
CREATE TABLE vocabulary_puzzle_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    
    attempt_number INTEGER NOT NULL,
    total_puzzles INTEGER NOT NULL,
    puzzles_completed INTEGER NOT NULL DEFAULT 0,
    current_puzzle_index INTEGER NOT NULL DEFAULT 0,
    
    -- Scoring
    total_score INTEGER NOT NULL DEFAULT 0,
    max_possible_score INTEGER NOT NULL,
    passing_score INTEGER NOT NULL,
    
    -- Puzzle scores tracking
    puzzle_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned')),
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vocab_puzzle_attempts_student ON vocabulary_puzzle_attempts(student_id);
CREATE INDEX idx_vocab_puzzle_attempts_progress ON vocabulary_puzzle_attempts(practice_progress_id);
CREATE INDEX idx_vocab_puzzle_attempts_status ON vocabulary_puzzle_attempts(status);

-- Update practice_status JSON structure to include puzzle_path
-- This will be handled in the application code, but we document the expected structure here
COMMENT ON COLUMN vocabulary_practice_progress.practice_status IS 
'Expected structure includes:
{
  "assignments": {
    "vocabulary_challenge": {...},
    "story_builder": {...},
    "concept_mapping": {...},
    "puzzle_path": {
      "status": "not_started",
      "attempts": 0,
      "best_score": 0,
      "last_attempt_at": null,
      "completed_at": null,
      "current_puzzle": 0,
      "total_puzzles": 0,
      "puzzles_completed": 0
    }
  },
  "completed_assignments": [],
  "test_unlocked": false,
  "test_unlock_date": null
}';

-- Update triggers
CREATE TRIGGER update_vocabulary_puzzle_attempts_updated_at
    BEFORE UPDATE ON vocabulary_puzzle_attempts
    FOR EACH ROW EXECUTE FUNCTION update_student_assignment_updated_at();

-- Grant permissions (adjust based on your user setup)
GRANT SELECT, INSERT, UPDATE ON vocabulary_puzzle_games TO umadex_user;
GRANT SELECT, INSERT, UPDATE ON vocabulary_puzzle_responses TO umadex_user;
GRANT SELECT, INSERT, UPDATE ON vocabulary_puzzle_attempts TO umadex_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO umadex_user;