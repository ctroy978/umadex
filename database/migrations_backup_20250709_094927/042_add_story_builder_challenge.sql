-- Add Story Builder Challenge tables for UMAVocab Practice Activities
-- This replaces the definition_match assignment type with story_builder

-- Story prompts for vocabulary assignments
CREATE TABLE vocabulary_story_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    required_words JSONB NOT NULL, -- ["word1", "word2", "word3"]
    setting VARCHAR(100) NOT NULL,
    tone VARCHAR(50) NOT NULL,
    max_score INTEGER DEFAULT 100,
    prompt_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Student story responses
CREATE TABLE vocabulary_story_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    prompt_id UUID NOT NULL REFERENCES vocabulary_story_prompts(id) ON DELETE CASCADE,
    story_text TEXT NOT NULL,
    ai_evaluation JSONB NOT NULL, -- scores and detailed feedback
    total_score INTEGER NOT NULL,
    attempt_number INTEGER DEFAULT 1,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_attempt_number CHECK (attempt_number BETWEEN 1 AND 2),
    CONSTRAINT check_total_score CHECK (total_score BETWEEN 0 AND 100)
);

-- Story Builder game attempts (similar to vocabulary challenge)
CREATE TABLE vocabulary_story_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    
    attempt_number INTEGER NOT NULL,
    total_prompts INTEGER NOT NULL,
    prompts_completed INTEGER NOT NULL DEFAULT 0,
    current_score INTEGER NOT NULL DEFAULT 0,
    max_possible_score INTEGER NOT NULL,
    passing_score INTEGER NOT NULL,
    
    -- Story responses tracking
    story_responses JSONB NOT NULL DEFAULT '[]', -- Array of response data
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_story_attempt_status CHECK (status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned'))
);

-- Indexes for performance
CREATE INDEX idx_vocab_story_prompts_list_id ON vocabulary_story_prompts(vocabulary_list_id);
CREATE INDEX idx_vocab_story_prompts_order ON vocabulary_story_prompts(vocabulary_list_id, prompt_order);

CREATE INDEX idx_vocab_story_responses_student ON vocabulary_story_responses(student_id);
CREATE INDEX idx_vocab_story_responses_prompt ON vocabulary_story_responses(prompt_id);
CREATE INDEX idx_vocab_story_responses_progress ON vocabulary_story_responses(practice_progress_id);

CREATE INDEX idx_vocab_story_attempts_student ON vocabulary_story_attempts(student_id);
CREATE INDEX idx_vocab_story_attempts_progress ON vocabulary_story_attempts(practice_progress_id);

-- Settings and tones reference data
INSERT INTO vocabulary_story_prompts (id, vocabulary_list_id, prompt_text, required_words, setting, tone, max_score, prompt_order) VALUES 
('00000000-0000-0000-0000-000000000000', '00000000-0000-0000-0000-000000000000', 'REFERENCE_DATA', '[]', 'SETTINGS_LIST', 'TONES_LIST', 0, 0);

-- Comment: The above INSERT is just for documentation. Actual prompts will be generated dynamically.
-- Available settings: enchanted forest, abandoned space station, underwater city, ancient castle, 
-- bustling marketplace, mysterious island, time machine laboratory, dragon's lair, robot factory, 
-- magical library, pirate ship, mountain peak, desert oasis, hidden cave, futuristic city

-- Available tones: mysterious, humorous, adventurous, suspenseful, dramatic, whimsical, 
-- heroic, peaceful, exciting, eerie