-- ============================================================================
-- MISSING TABLES FOR CLASSROOM ASSIGNMENTS
-- ============================================================================

-- Add missing columns to classroom_assignments if they don't exist
ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS vocab_settings JSONB DEFAULT '{}' NOT NULL;

ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS vocab_practice_settings JSONB DEFAULT '{
    "practice_required": true,
    "assignments_to_complete": 3,
    "allow_retakes": true,
    "show_explanations": true
}' NOT NULL;

ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS removed_from_classroom_at TIMESTAMPTZ;

ALTER TABLE classroom_assignments 
ADD COLUMN IF NOT EXISTS removed_by UUID REFERENCES users(id);

-- Create index for faster queries on removed items
CREATE INDEX IF NOT EXISTS idx_classroom_assignments_removed 
ON classroom_assignments(removed_from_classroom_at) 
WHERE removed_from_classroom_at IS NOT NULL;

-- ============================================================================
-- MISSING COLUMNS FOR DEBATE ASSIGNMENTS
-- ============================================================================

-- Add missing columns to debate_assignments table
ALTER TABLE debate_assignments 
ADD COLUMN IF NOT EXISTS statements_per_round INTEGER DEFAULT 5;

ALTER TABLE debate_assignments 
ADD COLUMN IF NOT EXISTS coaching_enabled BOOLEAN DEFAULT TRUE;

ALTER TABLE debate_assignments 
ADD COLUMN IF NOT EXISTS grading_baseline INTEGER DEFAULT 70;

ALTER TABLE debate_assignments 
ADD COLUMN IF NOT EXISTS grading_scale VARCHAR(20) DEFAULT 'lenient';

-- ============================================================================
-- DEBATE MODULE TABLES
-- ============================================================================

-- Content flags for moderation
CREATE TABLE IF NOT EXISTS content_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES debate_assignments(id) ON DELETE CASCADE,
    flag_type VARCHAR(20) NOT NULL CHECK (flag_type IN ('profanity', 'inappropriate', 'off_topic', 'spam')),
    flag_reason TEXT,
    auto_flagged BOOLEAN DEFAULT FALSE,
    confidence_score NUMERIC(3, 2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'escalated')),
    teacher_action VARCHAR(50),
    teacher_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

-- Student debates tracking
CREATE TABLE IF NOT EXISTS student_debates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES debate_assignments(id) ON DELETE CASCADE,
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id) ON DELETE CASCADE,
    
    -- Progress tracking
    status VARCHAR(50) NOT NULL DEFAULT 'not_started',
    current_debate INTEGER DEFAULT 1,
    current_round INTEGER DEFAULT 1,
    
    -- Three-debate structure
    debate_1_position VARCHAR(10) CHECK (debate_1_position IN ('pro', 'con')),
    debate_2_position VARCHAR(10) CHECK (debate_2_position IN ('pro', 'con')),
    debate_3_position VARCHAR(10) CHECK (debate_3_position IN ('pro', 'con')),
    
    -- Single point per round
    debate_1_point TEXT,
    debate_2_point TEXT,
    debate_3_point TEXT,
    
    -- Fallacy tracking
    fallacy_counter INTEGER DEFAULT 0,
    fallacy_scheduled_debate INTEGER,
    fallacy_scheduled_round INTEGER,
    
    -- Timing controls
    assignment_started_at TIMESTAMPTZ,
    current_debate_started_at TIMESTAMPTZ,
    current_debate_deadline TIMESTAMPTZ,
    
    -- Final scoring
    debate_1_percentage NUMERIC(5, 2),
    debate_2_percentage NUMERIC(5, 2),
    debate_3_percentage NUMERIC(5, 2),
    final_percentage NUMERIC(5, 2),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Debate posts
CREATE TABLE IF NOT EXISTS debate_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_debate_id UUID NOT NULL REFERENCES student_debates(id) ON DELETE CASCADE,
    
    -- Post identification
    debate_number INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    statement_number INTEGER NOT NULL,
    post_type VARCHAR(20) NOT NULL CHECK (post_type IN ('student', 'ai')),
    
    -- Content
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    
    -- AI-specific fields
    ai_personality VARCHAR(50),
    is_fallacy BOOLEAN DEFAULT FALSE,
    fallacy_type VARCHAR(50),
    
    -- Student scoring
    clarity_score NUMERIC(2, 1),
    evidence_score NUMERIC(2, 1),
    logic_score NUMERIC(2, 1),
    persuasiveness_score NUMERIC(2, 1),
    rebuttal_score NUMERIC(2, 1),
    base_percentage NUMERIC(5, 2),
    bonus_points NUMERIC(5, 2) DEFAULT 0,
    final_percentage NUMERIC(5, 2),
    
    -- Moderation
    content_flagged BOOLEAN DEFAULT FALSE,
    moderation_status VARCHAR(20) DEFAULT 'approved',
    
    -- AI feedback
    ai_feedback TEXT,
    
    -- Rhetorical technique
    selected_technique VARCHAR(100),
    technique_bonus_awarded NUMERIC(3, 1),
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Debate challenges
CREATE TABLE IF NOT EXISTS debate_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES debate_posts(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Challenge details
    challenge_type VARCHAR(20) NOT NULL CHECK (challenge_type IN ('fallacy', 'appeal')),
    challenge_value VARCHAR(50) NOT NULL,
    explanation TEXT,
    
    -- Evaluation
    is_correct BOOLEAN NOT NULL,
    points_awarded NUMERIC(3, 1) NOT NULL,
    ai_feedback TEXT,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- AI personalities
CREATE TABLE IF NOT EXISTS ai_personalities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    difficulty_levels JSONB,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Fallacy templates
CREATE TABLE IF NOT EXISTS fallacy_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fallacy_type VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    template TEXT NOT NULL,
    difficulty_levels JSONB,
    topic_keywords JSONB,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Debate round feedback
CREATE TABLE IF NOT EXISTS debate_round_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_debate_id UUID NOT NULL REFERENCES student_debates(id) ON DELETE CASCADE,
    debate_number INTEGER NOT NULL,
    
    -- Coaching feedback
    coaching_feedback TEXT NOT NULL,
    strengths TEXT,
    improvement_areas TEXT,
    specific_suggestions TEXT,
    
    -- Round completion tracking
    round_completed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- AI debate points
CREATE TABLE IF NOT EXISTS ai_debate_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES debate_assignments(id) ON DELETE CASCADE,
    debate_number INTEGER NOT NULL,
    position VARCHAR(10) NOT NULL CHECK (position IN ('pro', 'con')),
    
    -- The single point for this round
    debate_point TEXT NOT NULL,
    supporting_evidence JSONB,
    
    -- Metadata
    difficulty_appropriate BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Rhetorical techniques
CREATE TABLE IF NOT EXISTS rhetorical_techniques (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    technique_type VARCHAR(20) NOT NULL CHECK (technique_type IN ('proper', 'improper')),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    example TEXT NOT NULL,
    tip_or_reason TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- UMAREAD MODULE TABLES
-- ============================================================================

-- UMARead student responses
CREATE TABLE IF NOT EXISTS umaread_student_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) NOT NULL CHECK (question_type IN ('summary', 'comprehension')),
    question_text VARCHAR NOT NULL,
    student_answer VARCHAR NOT NULL,
    is_correct BOOLEAN NOT NULL,
    ai_feedback VARCHAR,
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    time_spent_seconds INTEGER,
    attempt_number INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT umaread_responses_student_assignment_idx UNIQUE (student_id, assignment_id, chunk_number, question_type, attempt_number)
);

-- UMARead chunk progress
CREATE TABLE IF NOT EXISTS umaread_chunk_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    chunk_number INTEGER NOT NULL,
    summary_completed BOOLEAN DEFAULT FALSE,
    comprehension_completed BOOLEAN DEFAULT FALSE,
    current_difficulty_level INTEGER DEFAULT 3 CHECK (current_difficulty_level BETWEEN 1 AND 8),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT umaread_chunk_progress_unique UNIQUE (student_id, assignment_id, chunk_number)
);

-- UMARead assignment progress
CREATE TABLE IF NOT EXISTS umaread_assignment_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id),
    student_assignment_id UUID REFERENCES student_assignments(id),
    current_chunk INTEGER DEFAULT 1,
    total_chunks_completed INTEGER DEFAULT 0,
    current_difficulty_level INTEGER DEFAULT 3 CHECK (current_difficulty_level BETWEEN 1 AND 8),
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT umaread_assignment_progress_unique UNIQUE (student_id, assignment_id)
);

-- ============================================================================
-- VOCABULARY PRACTICE MODULE TABLES
-- ============================================================================

-- Vocabulary practice progress
CREATE TABLE IF NOT EXISTS vocabulary_practice_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id),
    classroom_assignment_id INTEGER NOT NULL REFERENCES classroom_assignments(id),
    
    -- Practice status tracking
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
    }',
    
    -- Current game session tracking
    current_game_session JSONB,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_student_vocab_practice UNIQUE (student_id, vocabulary_list_id, classroom_assignment_id)
);

-- Vocabulary story prompts
CREATE TABLE IF NOT EXISTS vocabulary_story_prompts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    required_words JSONB NOT NULL,
    setting VARCHAR(100) NOT NULL,
    tone VARCHAR(50) NOT NULL,
    max_score INTEGER NOT NULL DEFAULT 100,
    prompt_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_prompt_order UNIQUE (vocabulary_list_id, prompt_order)
);

-- Vocabulary story responses
CREATE TABLE IF NOT EXISTS vocabulary_story_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    prompt_id UUID NOT NULL REFERENCES vocabulary_story_prompts(id) ON DELETE CASCADE,
    story_text TEXT NOT NULL,
    ai_evaluation JSONB NOT NULL,
    total_score INTEGER NOT NULL CHECK (total_score BETWEEN 0 AND 100),
    attempt_number INTEGER NOT NULL DEFAULT 1 CHECK (attempt_number BETWEEN 1 AND 2),
    time_spent_seconds INTEGER,
    submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Vocabulary story attempts
CREATE TABLE IF NOT EXISTS vocabulary_story_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    story_responses JSONB NOT NULL DEFAULT '[]',
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' CHECK (
        status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')
    ),
    
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Vocabulary concept maps
CREATE TABLE IF NOT EXISTS vocabulary_concept_maps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    
    -- Student responses
    definition TEXT NOT NULL,
    synonyms TEXT NOT NULL,
    antonyms TEXT NOT NULL,
    context_theme TEXT NOT NULL,
    connotation TEXT NOT NULL,
    example_sentence TEXT NOT NULL,
    
    -- Evaluation
    ai_evaluation JSONB NOT NULL,
    word_score NUMERIC(3, 2) NOT NULL CHECK (word_score >= 1.0 AND word_score <= 4.0),
    
    -- Tracking
    attempt_number INTEGER NOT NULL DEFAULT 1,
    word_order INTEGER NOT NULL,
    time_spent_seconds INTEGER,
    completed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_concept_map_word_attempt UNIQUE (practice_progress_id, word_id, attempt_number)
);

-- Vocabulary concept map attempts
CREATE TABLE IF NOT EXISTS vocabulary_concept_map_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    
    attempt_number INTEGER NOT NULL,
    total_words INTEGER NOT NULL,
    words_completed INTEGER NOT NULL DEFAULT 0,
    current_word_index INTEGER NOT NULL DEFAULT 0,
    
    -- Scoring
    total_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    max_possible_score NUMERIC(5, 2) NOT NULL,
    passing_score NUMERIC(5, 2) NOT NULL,
    average_score NUMERIC(3, 2),
    
    -- Word scores tracking
    word_scores JSONB NOT NULL DEFAULT '{}',
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' CHECK (
        status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')
    ),
    
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Vocabulary puzzle games
CREATE TABLE IF NOT EXISTS vocabulary_puzzle_games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    puzzle_type VARCHAR(50) NOT NULL CHECK (puzzle_type IN ('scrambled', 'crossword_clue', 'word_match')),
    puzzle_data JSONB NOT NULL,
    correct_answer VARCHAR(200) NOT NULL,
    puzzle_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_puzzle_order UNIQUE (vocabulary_list_id, puzzle_order)
);

-- Vocabulary puzzle responses
CREATE TABLE IF NOT EXISTS vocabulary_puzzle_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    puzzle_id UUID NOT NULL REFERENCES vocabulary_puzzle_games(id) ON DELETE CASCADE,
    student_answer TEXT NOT NULL,
    ai_evaluation JSONB NOT NULL,
    puzzle_score INTEGER NOT NULL CHECK (puzzle_score BETWEEN 1 AND 4),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    time_spent_seconds INTEGER,
    completed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_puzzle_response_attempt UNIQUE (practice_progress_id, puzzle_id, attempt_number)
);

-- Vocabulary puzzle attempts
CREATE TABLE IF NOT EXISTS vocabulary_puzzle_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    puzzle_scores JSONB NOT NULL DEFAULT '{}',
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' CHECK (
        status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')
    ),
    
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Vocabulary fill-in-the-blank sentences
CREATE TABLE IF NOT EXISTS vocabulary_fill_in_blank_sentences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    sentence_with_blank TEXT NOT NULL,
    correct_answer VARCHAR(100) NOT NULL,
    sentence_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_sentence_order UNIQUE (vocabulary_list_id, sentence_order)
);

-- Vocabulary fill-in-the-blank responses
CREATE TABLE IF NOT EXISTS vocabulary_fill_in_blank_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    sentence_id UUID NOT NULL REFERENCES vocabulary_fill_in_blank_sentences(id) ON DELETE CASCADE,
    student_answer VARCHAR(100) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    time_spent_seconds INTEGER,
    answered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_fill_in_blank_response_attempt UNIQUE (practice_progress_id, sentence_id, attempt_number)
);

-- Vocabulary fill-in-the-blank attempts
CREATE TABLE IF NOT EXISTS vocabulary_fill_in_blank_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    practice_progress_id UUID NOT NULL REFERENCES vocabulary_practice_progress(id) ON DELETE CASCADE,
    
    attempt_number INTEGER NOT NULL,
    total_sentences INTEGER NOT NULL,
    sentences_completed INTEGER NOT NULL DEFAULT 0,
    current_sentence_index INTEGER NOT NULL DEFAULT 0,
    
    -- Scoring
    correct_answers INTEGER NOT NULL DEFAULT 0,
    incorrect_answers INTEGER NOT NULL DEFAULT 0,
    score_percentage NUMERIC(5, 2),
    passing_score INTEGER NOT NULL DEFAULT 70,
    
    -- Tracking
    sentence_order JSONB NOT NULL DEFAULT '[]',
    responses JSONB NOT NULL DEFAULT '{}',
    
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' CHECK (
        status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')
    ),
    
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    time_spent_seconds INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Debate module indexes
CREATE INDEX IF NOT EXISTS idx_content_flags_assignment ON content_flags(assignment_id);
CREATE INDEX IF NOT EXISTS idx_content_flags_status ON content_flags(status);
CREATE INDEX IF NOT EXISTS idx_student_debates_student ON student_debates(student_id);
CREATE INDEX IF NOT EXISTS idx_student_debates_assignment ON student_debates(assignment_id);
CREATE INDEX IF NOT EXISTS idx_debate_posts_student_debate ON debate_posts(student_debate_id);
CREATE INDEX IF NOT EXISTS idx_debate_challenges_post ON debate_challenges(post_id);

-- UMARead module indexes
CREATE INDEX IF NOT EXISTS idx_umaread_responses_student ON umaread_student_responses(student_id);
CREATE INDEX IF NOT EXISTS idx_umaread_responses_assignment ON umaread_student_responses(assignment_id);
CREATE INDEX IF NOT EXISTS idx_umaread_chunk_progress_student ON umaread_chunk_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_umaread_chunk_progress_assignment ON umaread_chunk_progress(assignment_id);
CREATE INDEX IF NOT EXISTS idx_umaread_assignment_progress_student ON umaread_assignment_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_umaread_assignment_progress_assignment ON umaread_assignment_progress(assignment_id);

-- Vocabulary practice indexes
CREATE INDEX IF NOT EXISTS idx_vocab_practice_student ON vocabulary_practice_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_vocab_practice_list ON vocabulary_practice_progress(vocabulary_list_id);
CREATE INDEX IF NOT EXISTS idx_vocab_story_responses_student ON vocabulary_story_responses(student_id);
CREATE INDEX IF NOT EXISTS idx_vocab_concept_maps_student ON vocabulary_concept_maps(student_id);
CREATE INDEX IF NOT EXISTS idx_vocab_puzzle_responses_student ON vocabulary_puzzle_responses(student_id);
CREATE INDEX IF NOT EXISTS idx_vocab_fill_blank_responses_student ON vocabulary_fill_in_blank_responses(student_id);

-- ============================================================================
-- UPDATE TRIGGERS
-- ============================================================================

-- Add update triggers for new tables
CREATE TRIGGER update_student_debates_updated_at BEFORE UPDATE ON student_debates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_umaread_chunk_progress_updated_at BEFORE UPDATE ON umaread_chunk_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_practice_progress_updated_at BEFORE UPDATE ON vocabulary_practice_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_story_attempts_updated_at BEFORE UPDATE ON vocabulary_story_attempts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_concept_map_attempts_updated_at BEFORE UPDATE ON vocabulary_concept_map_attempts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_puzzle_attempts_updated_at BEFORE UPDATE ON vocabulary_puzzle_attempts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_fill_in_blank_attempts_updated_at BEFORE UPDATE ON vocabulary_fill_in_blank_attempts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();