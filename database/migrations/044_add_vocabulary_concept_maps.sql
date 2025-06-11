-- Add vocabulary concept map builder activity
-- This is Assignment 3 of the 4 practice activities

-- Table for storing student concept maps for vocabulary words
CREATE TABLE vocabulary_concept_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    
    -- Student responses for the six components
    definition TEXT NOT NULL,
    synonyms TEXT NOT NULL,
    antonyms TEXT NOT NULL,
    context_theme TEXT NOT NULL,
    connotation TEXT NOT NULL,
    example_sentence TEXT NOT NULL,
    
    -- AI evaluation results
    ai_evaluation JSONB NOT NULL,
    word_score DECIMAL(3,2) NOT NULL CHECK (word_score >= 1.0 AND word_score <= 4.0),
    
    -- Tracking
    attempt_number INTEGER NOT NULL DEFAULT 1,
    word_order INTEGER NOT NULL,
    time_spent_seconds INTEGER,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(practice_progress_id, word_id, attempt_number)
);

-- Indexes for performance
CREATE INDEX idx_vocab_concept_maps_student ON vocabulary_concept_maps(student_id);
CREATE INDEX idx_vocab_concept_maps_list ON vocabulary_concept_maps(vocabulary_list_id);
CREATE INDEX idx_vocab_concept_maps_progress ON vocabulary_concept_maps(practice_progress_id);
CREATE INDEX idx_vocab_concept_maps_word ON vocabulary_concept_maps(word_id);

-- Table for tracking concept map builder attempts
CREATE TABLE vocabulary_concept_map_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    
    attempt_number INTEGER NOT NULL,
    total_words INTEGER NOT NULL,
    words_completed INTEGER NOT NULL DEFAULT 0,
    current_word_index INTEGER NOT NULL DEFAULT 0,
    
    -- Scoring
    total_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    max_possible_score DECIMAL(5,2) NOT NULL,
    passing_score DECIMAL(5,2) NOT NULL,
    average_score DECIMAL(3,2),
    
    -- Word scores tracking
    word_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned')),
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_vocab_concept_attempts_student ON vocabulary_concept_map_attempts(student_id);
CREATE INDEX idx_vocab_concept_attempts_progress ON vocabulary_concept_map_attempts(practice_progress_id);
CREATE INDEX idx_vocab_concept_attempts_status ON vocabulary_concept_map_attempts(status);

-- Update practice_status JSON structure to include concept_mapping
-- This will be handled in the application code, but we document the expected structure here
COMMENT ON COLUMN vocabulary_practice_progress.practice_status IS 
'Expected structure includes:
{
  "assignments": {
    "vocabulary_challenge": {...},
    "story_builder": {...},
    "concept_mapping": {
      "status": "not_started",
      "attempts": 0,
      "best_score": 0,
      "average_score": 0,
      "last_attempt_at": null,
      "completed_at": null,
      "current_word_index": 0,
      "total_words": 0,
      "words_completed": 0
    },
    "word_builder": {...}
  },
  "completed_assignments": [],
  "test_unlocked": false,
  "test_unlock_date": null
}';

-- Update triggers
CREATE TRIGGER update_vocabulary_concept_map_attempts_updated_at
    BEFORE UPDATE ON vocabulary_concept_map_attempts
    FOR EACH ROW EXECUTE FUNCTION update_student_assignment_updated_at();

-- Grant permissions (adjust based on your user setup)
GRANT SELECT, INSERT, UPDATE ON vocabulary_concept_maps TO umadex_user;
GRANT SELECT, INSERT, UPDATE ON vocabulary_concept_map_attempts TO umadex_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO umadex_user;