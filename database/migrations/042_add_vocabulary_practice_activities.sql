-- Add vocabulary practice activities and game questions

-- Table for storing generated questions for vocabulary practice activities
CREATE TABLE vocabulary_game_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    question_type VARCHAR(50) NOT NULL CHECK (question_type IN ('riddle', 'poem', 'sentence_completion', 'word_association', 'scenario')),
    difficulty_level VARCHAR(10) NOT NULL CHECK (difficulty_level IN ('easy', 'medium', 'hard')),
    question_text TEXT NOT NULL,
    correct_answer VARCHAR(200) NOT NULL,
    explanation TEXT NOT NULL,
    question_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(vocabulary_list_id, question_order)
);

-- Indexes for performance
CREATE INDEX idx_vocab_game_questions_list ON vocabulary_game_questions(vocabulary_list_id);
CREATE INDEX idx_vocab_game_questions_word ON vocabulary_game_questions(word_id);
CREATE INDEX idx_vocab_game_questions_type ON vocabulary_game_questions(question_type);

-- Table for tracking student progress on vocabulary practice activities
CREATE TABLE vocabulary_practice_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id),
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id),
    
    -- Practice activity status tracking
    practice_status JSONB NOT NULL DEFAULT '{
        "assignments": {
            "vocabulary_challenge": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": null,
                "completed_at": null
            },
            "definition_match": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": null,
                "completed_at": null
            },
            "context_clues": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": null,
                "completed_at": null
            },
            "word_builder": {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": null,
                "completed_at": null
            }
        },
        "completed_assignments": [],
        "test_unlocked": false,
        "test_unlock_date": null
    }'::jsonb,
    
    -- Current game session tracking
    current_game_session JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(student_id, vocabulary_list_id, classroom_assignment_id)
);

-- Indexes
CREATE INDEX idx_vocab_practice_student ON vocabulary_practice_progress(student_id);
CREATE INDEX idx_vocab_practice_list ON vocabulary_practice_progress(vocabulary_list_id);
CREATE INDEX idx_vocab_practice_classroom ON vocabulary_practice_progress(classroom_assignment_id);

-- Table for storing individual game attempts
CREATE TABLE vocabulary_game_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id),
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id),
    
    game_type VARCHAR(50) NOT NULL CHECK (game_type IN ('vocabulary_challenge', 'definition_match', 'context_clues', 'word_builder')),
    attempt_number INTEGER NOT NULL,
    
    -- Game session data
    total_questions INTEGER NOT NULL,
    questions_answered INTEGER NOT NULL DEFAULT 0,
    current_score INTEGER NOT NULL DEFAULT 0,
    max_possible_score INTEGER NOT NULL,
    passing_score INTEGER NOT NULL,
    
    -- Question-level tracking
    question_responses JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Format: [
    --   {
    --     "question_id": "uuid",
    --     "question_order": 1,
    --     "attempts": 1,
    --     "correct": true,
    --     "points_earned": 5,
    --     "student_answer": "relevant",
    --     "time_spent_seconds": 45
    --   }
    -- ]
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned')),
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vocab_attempts_student ON vocabulary_game_attempts(student_id, game_type);
CREATE INDEX idx_vocab_attempts_progress ON vocabulary_game_attempts(practice_progress_id);
CREATE INDEX idx_vocab_attempts_status ON vocabulary_game_attempts(status);

-- Update triggers
CREATE TRIGGER update_vocabulary_practice_progress_updated_at
    BEFORE UPDATE ON vocabulary_practice_progress
    FOR EACH ROW EXECUTE FUNCTION update_student_assignment_updated_at();

CREATE TRIGGER update_vocabulary_game_attempts_updated_at
    BEFORE UPDATE ON vocabulary_game_attempts
    FOR EACH ROW EXECUTE FUNCTION update_student_assignment_updated_at();

-- Function to check if test should be unlocked
CREATE OR REPLACE FUNCTION check_vocabulary_test_unlock(progress_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    completed_count INTEGER;
    practice_data JSONB;
BEGIN
    SELECT practice_status INTO practice_data
    FROM vocabulary_practice_progress
    WHERE id = progress_id;
    
    -- Count completed assignments
    SELECT COUNT(*) INTO completed_count
    FROM jsonb_array_elements_text(practice_data->'completed_assignments') AS assignment;
    
    -- Test unlocks when 3 of 4 assignments are completed
    RETURN completed_count >= 3;
END;
$$ LANGUAGE plpgsql;

-- Add column to track practice requirements in vocabulary settings
ALTER TABLE classroom_assignments
ADD COLUMN IF NOT EXISTS vocab_practice_settings JSONB DEFAULT '{
    "practice_required": true,
    "assignments_to_complete": 3,
    "allow_retakes": true,
    "show_explanations": true
}'::jsonb;

-- Update existing vocabulary assignments to include practice settings
UPDATE classroom_assignments
SET vocab_practice_settings = '{
    "practice_required": true,
    "assignments_to_complete": 3,
    "allow_retakes": true,
    "show_explanations": true
}'::jsonb
WHERE assignment_type = 'vocabulary' AND vocab_practice_settings IS NULL;