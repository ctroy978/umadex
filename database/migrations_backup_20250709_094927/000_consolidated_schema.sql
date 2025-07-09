-- UMADeX Consolidated Database Schema
-- This file replaces all individual migration files with a single, comprehensive schema

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Custom Types
CREATE TYPE user_role AS ENUM ('student', 'teacher');
CREATE TYPE uma_type AS ENUM ('read', 'debate', 'vocab', 'write', 'lecture');

-- Core utility function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Username generation function
CREATE OR REPLACE FUNCTION generate_username(email_addr TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN REPLACE(SPLIT_PART(email_addr, '@', 1), '.', '');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- USER MANAGEMENT & AUTHENTICATION
-- ============================================================================

-- Main users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL DEFAULT generate_username(email),
    role user_role NOT NULL DEFAULT 'student',
    is_admin BOOLEAN DEFAULT FALSE,
    bypass_code VARCHAR(255),
    bypass_code_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Email whitelist for registration
CREATE TABLE email_whitelist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_pattern VARCHAR(255) NOT NULL UNIQUE,
    is_domain BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- OTP requests for authentication
CREATE TABLE otp_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- User sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    token_type VARCHAR(20) DEFAULT 'session',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Refresh tokens for JWT
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMPTZ,
    device_info JSONB DEFAULT '{}',
    revoked_at TIMESTAMPTZ
);

-- ============================================================================
-- CLASSROOM MANAGEMENT
-- ============================================================================

-- Teacher classrooms
CREATE TABLE classrooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    grade_level VARCHAR(50),
    school_year VARCHAR(20),
    class_code VARCHAR(8) UNIQUE NOT NULL,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Student enrollment in classrooms
CREATE TABLE classroom_students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    removed_at TIMESTAMPTZ,
    removed_by UUID REFERENCES users(id),
    UNIQUE(classroom_id, student_id)
);

-- Assignment-to-classroom mapping
CREATE TABLE classroom_assignments (
    id SERIAL PRIMARY KEY,
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL,
    vocabulary_list_id UUID,
    assignment_type VARCHAR(50) NOT NULL CHECK (assignment_type IN ('reading', 'vocabulary', 'debate', 'writing', 'lecture', 'test')),
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    display_order INTEGER,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    UNIQUE(classroom_id, assignment_id)
);

-- ============================================================================
-- UMAREAD MODULE
-- ============================================================================

-- Main reading assignments
CREATE TABLE reading_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_title VARCHAR(255) NOT NULL,
    work_title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    grade_level VARCHAR(50) NOT NULL,
    work_type VARCHAR(20) CHECK (work_type IN ('fiction', 'non-fiction')),
    literary_form VARCHAR(20) CHECK (literary_form IN ('prose', 'poetry', 'drama', 'mixed')),
    genre VARCHAR(50) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    raw_content TEXT NOT NULL,
    total_chunks INTEGER,
    status VARCHAR(50) DEFAULT 'draft',
    assignment_type VARCHAR(50) DEFAULT 'UMARead',
    images_processed BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Text chunks for reading
CREATE TABLE reading_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_order INTEGER NOT NULL,
    content TEXT NOT NULL,
    has_important_sections BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Images for assignments
CREATE TABLE assignment_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    image_key VARCHAR(50) NOT NULL,
    custom_name VARCHAR(100),
    file_url TEXT NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(50),
    image_tag VARCHAR(50),
    original_url TEXT,
    display_url TEXT,
    thumbnail_url TEXT,
    file_name VARCHAR(255),
    image_url TEXT,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    ai_description TEXT,
    description_generated_at TIMESTAMPTZ,
    uploaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- AI-generated questions cache
CREATE TABLE reading_question_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) CHECK (question_type IN ('summary', 'comprehension')),
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    question_text TEXT NOT NULL,
    question_metadata JSONB DEFAULT '{}',
    ai_model VARCHAR(100) NOT NULL,
    generation_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Student responses to reading questions
CREATE TABLE reading_student_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    question_type VARCHAR(20) CHECK (question_type IN ('summary', 'comprehension')),
    question_cache_id UUID REFERENCES reading_question_cache(id),
    question_text TEXT NOT NULL,
    difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 8),
    student_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempt_number INTEGER NOT NULL,
    time_spent_seconds INTEGER NOT NULL,
    ai_feedback TEXT,
    feedback_metadata JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- UMARead tests
CREATE TABLE assignment_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'archived')),
    test_questions JSONB NOT NULL,
    teacher_notes TEXT,
    expires_at TIMESTAMPTZ,
    max_attempts INTEGER DEFAULT 1,
    time_limit_minutes INTEGER DEFAULT 60,
    approved_at TIMESTAMPTZ,
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Cache flush log
CREATE TABLE reading_cache_flush_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    flushed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- UMATEST MODULE
-- ============================================================================

-- Test assignments
CREATE TABLE test_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_title VARCHAR(255) NOT NULL,
    test_description TEXT,
    selected_lecture_ids UUID[] NOT NULL,
    time_limit_minutes INTEGER,
    attempt_limit INTEGER DEFAULT 1,
    randomize_questions BOOLEAN DEFAULT FALSE,
    show_feedback_immediately BOOLEAN DEFAULT TRUE,
    test_structure JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- Test question cache
CREATE TABLE test_question_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lecture_id UUID NOT NULL,
    topic_id VARCHAR(255) NOT NULL,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('basic', 'intermediate', 'advanced', 'expert')),
    content_hash VARCHAR(64) NOT NULL,
    questions JSONB NOT NULL,
    ai_model VARCHAR(100),
    generation_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- UMAVOCAB MODULE
-- ============================================================================

-- Vocabulary lists
CREATE TABLE vocabulary_lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    context_description TEXT NOT NULL,
    grade_level VARCHAR(50) NOT NULL,
    subject_area VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'reviewing', 'published', 'archived')),
    chain_previous_tests BOOLEAN DEFAULT FALSE,
    chain_weeks_back INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- Individual vocabulary words
CREATE TABLE vocabulary_words (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    word VARCHAR(100) NOT NULL,
    teacher_definition TEXT,
    teacher_example_1 TEXT,
    teacher_example_2 TEXT,
    ai_definition TEXT,
    ai_example_1 TEXT,
    ai_example_2 TEXT,
    definition_source VARCHAR(20) DEFAULT 'pending' CHECK (definition_source IN ('pending', 'ai', 'teacher')),
    examples_source VARCHAR(20) DEFAULT 'pending' CHECK (examples_source IN ('pending', 'ai', 'teacher')),
    position INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Generated vocabulary tests
CREATE TABLE vocabulary_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    classroom_assignment_id INTEGER REFERENCES classroom_assignments(id),
    questions JSONB NOT NULL,
    total_questions INTEGER NOT NULL,
    chained_lists JSONB DEFAULT '[]',
    expires_at TIMESTAMPTZ NOT NULL,
    max_attempts INTEGER DEFAULT 3,
    time_limit_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Student vocabulary test attempts
CREATE TABLE vocabulary_test_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_id UUID NOT NULL REFERENCES vocabulary_tests(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    responses JSONB NOT NULL,
    score_percentage DECIMAL(5,2) NOT NULL,
    questions_correct INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    time_spent_seconds INTEGER,
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'abandoned')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- UMADEBATE MODULE
-- ============================================================================

-- Debate assignments
CREATE TABLE debate_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    topic TEXT NOT NULL,
    description TEXT,
    grade_level VARCHAR(50) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    rounds_per_debate INTEGER DEFAULT 3 CHECK (rounds_per_debate BETWEEN 2 AND 4),
    debate_count INTEGER DEFAULT 3,
    time_limit_hours INTEGER DEFAULT 8,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    fallacy_frequency VARCHAR(20) CHECK (fallacy_frequency IN ('every_1_2', 'every_2_3', 'every_3_4', 'disabled')),
    ai_personalities_enabled BOOLEAN DEFAULT TRUE,
    content_moderation_enabled BOOLEAN DEFAULT TRUE,
    auto_flag_off_topic BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- ============================================================================
-- UMAWRITE MODULE
-- ============================================================================

-- Writing assignments
CREATE TABLE writing_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    prompt_text TEXT NOT NULL,
    word_count_min INTEGER DEFAULT 50,
    word_count_max INTEGER DEFAULT 500,
    evaluation_criteria JSONB NOT NULL DEFAULT '{}',
    instructions TEXT,
    grade_level VARCHAR(50),
    subject VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- Student writing submissions
CREATE TABLE student_writing_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_assignment_id UUID NOT NULL,
    writing_assignment_id UUID NOT NULL REFERENCES writing_assignments(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL,
    selected_techniques TEXT[] DEFAULT '{}',
    word_count INTEGER NOT NULL,
    submission_attempt INTEGER DEFAULT 1,
    is_final_submission BOOLEAN DEFAULT FALSE,
    submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    score DECIMAL(3,2) CHECK (score BETWEEN 0 AND 10),
    ai_feedback JSONB,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- UMALECTURE MODULE
-- ============================================================================

-- Lecture assignments
CREATE TABLE lecture_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    grade_level VARCHAR(50) NOT NULL,
    topic_outline TEXT,
    learning_objectives TEXT[],
    lecture_structure JSONB,
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'published', 'archived')),
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ
);

-- Lecture images
CREATE TABLE lecture_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lecture_id UUID NOT NULL REFERENCES lecture_assignments(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    teacher_description TEXT NOT NULL,
    ai_description TEXT,
    node_id VARCHAR(100) NOT NULL,
    position INTEGER DEFAULT 1,
    original_url TEXT NOT NULL,
    display_url TEXT,
    thumbnail_url TEXT,
    file_size INTEGER,
    mime_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- STUDENT PROGRESS & ASSIGNMENT TRACKING
-- ============================================================================

-- Individual student assignment tracking
CREATE TABLE student_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL,
    classroom_assignment_id INTEGER REFERENCES classroom_assignments(id),
    assignment_type VARCHAR(50) DEFAULT 'reading',
    status VARCHAR(50) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'test_available', 'test_completed')),
    current_position INTEGER DEFAULT 1,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    progress_metadata JSONB DEFAULT '{}',
    consecutive_errors INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Unified student test attempts (for both UMARead and UMATest)
CREATE TABLE student_test_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_test_id UUID REFERENCES assignment_tests(id),
    test_id UUID REFERENCES test_assignments(id),
    assignment_id UUID REFERENCES reading_assignments(id),
    classroom_assignment_id INTEGER REFERENCES classroom_assignments(id),
    current_question INTEGER DEFAULT 1,
    answers_data JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'submitted', 'graded')),
    attempt_number INTEGER DEFAULT 1,
    started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMPTZ,
    time_spent_seconds INTEGER DEFAULT 0,
    score DECIMAL(5,2),
    passed BOOLEAN,
    feedback JSONB,
    evaluation_status VARCHAR(50) DEFAULT 'pending' CHECK (evaluation_status IN ('pending', 'evaluating', 'completed', 'failed', 'manual_review')),
    evaluated_at TIMESTAMPTZ,
    evaluation_model VARCHAR(100),
    evaluation_version VARCHAR(50),
    raw_ai_response JSONB,
    evaluation_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Detailed question evaluations
CREATE TABLE test_question_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id) ON DELETE CASCADE,
    question_number INTEGER CHECK (question_number BETWEEN 0 AND 9),
    question_text TEXT NOT NULL,
    student_answer TEXT,
    answer_key TEXT,
    answer_explanation TEXT,
    rubric_score INTEGER CHECK (rubric_score BETWEEN 0 AND 4),
    points_earned INTEGER CHECK (points_earned IN (0, 2, 5, 8, 10)),
    scoring_rationale TEXT,
    feedback_text TEXT,
    key_concepts_identified JSONB DEFAULT '[]',
    misconceptions_detected JSONB DEFAULT '[]',
    evaluation_confidence DECIMAL(3,2) CHECK (evaluation_confidence BETWEEN 0 AND 1),
    time_spent_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- SCHEDULING & ACCESS CONTROL
-- ============================================================================

-- Test scheduling system
CREATE TABLE classroom_test_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    created_by_teacher_id UUID NOT NULL REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    grace_period_minutes INTEGER DEFAULT 30,
    schedule_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Emergency override codes
CREATE TABLE classroom_test_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id),
    override_code VARCHAR(8) NOT NULL UNIQUE,
    reason TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    max_uses INTEGER DEFAULT 1,
    current_uses INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMPTZ
);

-- Override usage tracking
CREATE TABLE test_override_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    override_id UUID NOT NULL REFERENCES classroom_test_overrides(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id),
    used_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

-- ============================================================================
-- AUDIT & TRACKING TABLES
-- ============================================================================

-- Student activity tracking
CREATE TABLE student_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    classroom_id UUID REFERENCES classrooms(id),
    assignment_id UUID,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Gradebook system
CREATE TABLE gradebook_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    assignment_type VARCHAR(20) CHECK (assignment_type IN ('umaread', 'umavocab_test', 'umadebate', 'umawrite', 'umaspeak')),
    assignment_id UUID NOT NULL,
    score_percentage DECIMAL(5,2) NOT NULL,
    points_earned DECIMAL(8,2),
    points_possible DECIMAL(8,2),
    attempt_number INTEGER DEFAULT 1,
    completed_at TIMESTAMPTZ NOT NULL,
    graded_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Progress tracking for UMARead
CREATE TABLE student_reading_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id UUID NOT NULL REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_number INTEGER NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    time_spent_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Progress tracking for UMATest
CREATE TABLE student_test_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_assignment_id UUID NOT NULL REFERENCES test_assignments(id) ON DELETE CASCADE,
    lecture_id UUID NOT NULL,
    topic_id VARCHAR(255) NOT NULL,
    completed_at TIMESTAMPTZ,
    score DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- User indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Classroom indexes
CREATE INDEX idx_classrooms_teacher_id ON classrooms(teacher_id);
CREATE INDEX idx_classrooms_class_code ON classrooms(class_code);
CREATE INDEX idx_classrooms_deleted_at ON classrooms(deleted_at);
CREATE INDEX idx_classroom_students_classroom_id ON classroom_students(classroom_id);
CREATE INDEX idx_classroom_students_student_id ON classroom_students(student_id);
CREATE INDEX idx_classroom_students_status ON classroom_students(status);
CREATE INDEX idx_classroom_assignments_classroom_id ON classroom_assignments(classroom_id);
CREATE INDEX idx_classroom_assignments_assignment_id ON classroom_assignments(assignment_id);
CREATE INDEX idx_classroom_assignments_type ON classroom_assignments(assignment_type);

-- Reading assignment indexes
CREATE INDEX idx_reading_assignments_teacher_id ON reading_assignments(teacher_id);
CREATE INDEX idx_reading_assignments_status ON reading_assignments(status);
CREATE INDEX idx_reading_assignments_deleted_at ON reading_assignments(deleted_at);
CREATE INDEX idx_reading_chunks_assignment_id ON reading_chunks(assignment_id);
CREATE INDEX idx_reading_chunks_order ON reading_chunks(assignment_id, chunk_order);
CREATE INDEX idx_assignment_images_assignment_id ON assignment_images(assignment_id);

-- Question cache indexes
CREATE INDEX idx_reading_question_cache_lookup ON reading_question_cache(assignment_id, chunk_number, question_type);
CREATE INDEX idx_reading_question_cache_timestamp ON reading_question_cache(generation_timestamp);
CREATE INDEX idx_reading_responses_student ON reading_student_responses(student_id, assignment_id);
CREATE INDEX idx_reading_responses_occurred ON reading_student_responses(occurred_at);

-- Student progress indexes
CREATE INDEX idx_student_assignments_student_id ON student_assignments(student_id);
CREATE INDEX idx_student_assignments_assignment_id ON student_assignments(assignment_id);
CREATE INDEX idx_student_assignments_status ON student_assignments(status);
CREATE INDEX idx_student_assignments_classroom ON student_assignments(classroom_assignment_id);
CREATE INDEX idx_student_test_attempts_student_id ON student_test_attempts(student_id);
CREATE INDEX idx_student_test_attempts_assignment_test_id ON student_test_attempts(assignment_test_id);
CREATE INDEX idx_student_test_attempts_test_id ON student_test_attempts(test_id);
CREATE INDEX idx_student_test_attempts_status ON student_test_attempts(status);

-- Vocabulary indexes
CREATE INDEX idx_vocabulary_lists_teacher_id ON vocabulary_lists(teacher_id);
CREATE INDEX idx_vocabulary_lists_status ON vocabulary_lists(status);
CREATE INDEX idx_vocabulary_words_list_id ON vocabulary_words(list_id);
CREATE INDEX idx_vocabulary_words_position ON vocabulary_words(list_id, position);
CREATE INDEX idx_vocabulary_tests_list_id ON vocabulary_tests(vocabulary_list_id);
CREATE INDEX idx_vocabulary_test_attempts_test_id ON vocabulary_test_attempts(test_id);
CREATE INDEX idx_vocabulary_test_attempts_student_id ON vocabulary_test_attempts(student_id);

-- Test system indexes
CREATE INDEX idx_test_assignments_teacher_id ON test_assignments(teacher_id);
CREATE INDEX idx_test_assignments_status ON test_assignments(status);
CREATE INDEX idx_test_question_cache_lecture_id ON test_question_cache(lecture_id);
CREATE INDEX idx_test_question_cache_topic_id ON test_question_cache(topic_id);
CREATE INDEX idx_test_question_evaluations_attempt_id ON test_question_evaluations(test_attempt_id);

-- Scheduling indexes
CREATE INDEX idx_classroom_test_schedules_classroom_id ON classroom_test_schedules(classroom_id);
CREATE INDEX idx_classroom_test_schedules_active ON classroom_test_schedules(is_active);
CREATE INDEX idx_classroom_test_overrides_classroom_id ON classroom_test_overrides(classroom_id);
CREATE INDEX idx_classroom_test_overrides_code ON classroom_test_overrides(override_code);
CREATE INDEX idx_classroom_test_overrides_expires ON classroom_test_overrides(expires_at);

-- Audit indexes
CREATE INDEX idx_student_events_student_id ON student_events(student_id);
CREATE INDEX idx_student_events_classroom_id ON student_events(classroom_id);
CREATE INDEX idx_student_events_created_at ON student_events(created_at);
CREATE INDEX idx_gradebook_entries_student_id ON gradebook_entries(student_id);
CREATE INDEX idx_gradebook_entries_classroom_id ON gradebook_entries(classroom_id);
CREATE INDEX idx_gradebook_entries_completed_at ON gradebook_entries(completed_at);

-- Session indexes
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(token);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Function to flush reading question cache
CREATE OR REPLACE FUNCTION flush_reading_question_cache(assignment_id UUID)
RETURNS VOID AS $$
BEGIN
    DELETE FROM reading_question_cache WHERE assignment_id = $1;
    INSERT INTO reading_cache_flush_log (assignment_id) VALUES ($1);
END;
$$ LANGUAGE plpgsql;

-- Function to check if student can proceed to next chunk
CREATE OR REPLACE FUNCTION can_proceed_to_next_chunk(
    p_student_id UUID,
    p_assignment_id UUID,
    p_chunk_number INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_correct_responses INTEGER;
    v_total_responses INTEGER;
BEGIN
    SELECT 
        COUNT(*) FILTER (WHERE is_correct = true),
        COUNT(*)
    INTO v_correct_responses, v_total_responses
    FROM reading_student_responses
    WHERE student_id = p_student_id 
      AND assignment_id = p_assignment_id 
      AND chunk_number = p_chunk_number;
    
    -- Allow progression if student has answered at least one question correctly
    -- or has made at least 3 attempts
    RETURN v_correct_responses > 0 OR v_total_responses >= 3;
END;
$$ LANGUAGE plpgsql;

-- Function to check if testing is allowed for a classroom
CREATE OR REPLACE FUNCTION is_testing_allowed(
    p_classroom_id UUID,
    p_check_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
)
RETURNS TABLE (
    allowed BOOLEAN,
    next_window TIMESTAMPTZ,
    current_window_end TIMESTAMPTZ,
    schedule_active BOOLEAN
) AS $$
DECLARE
    v_schedule RECORD;
    v_timezone TEXT;
    v_local_time TIME;
    v_local_dow INTEGER;
    v_window JSONB;
    v_window_start TIME;
    v_window_end TIME;
    v_allowed BOOLEAN := false;
    v_current_end TIMESTAMPTZ;
    v_next_start TIMESTAMPTZ;
BEGIN
    -- Get schedule for classroom
    SELECT * INTO v_schedule
    FROM classroom_test_schedules
    WHERE classroom_id = p_classroom_id AND is_active = true;
    
    -- If no active schedule, testing is always allowed
    IF NOT FOUND THEN
        RETURN QUERY SELECT true, NULL::TIMESTAMPTZ, NULL::TIMESTAMPTZ, false;
        RETURN;
    END IF;
    
    -- Get timezone and convert to local time
    v_timezone := v_schedule.timezone;
    v_local_time := (p_check_time AT TIME ZONE v_timezone)::TIME;
    v_local_dow := EXTRACT(DOW FROM (p_check_time AT TIME ZONE v_timezone))::INTEGER;
    
    -- Check each window in schedule
    FOR v_window IN SELECT * FROM jsonb_array_elements(v_schedule.schedule_data->'windows')
    LOOP
        -- Check if current day is in window days
        IF v_window->'days' ? (CASE v_local_dow
            WHEN 0 THEN 'sunday'
            WHEN 1 THEN 'monday'
            WHEN 2 THEN 'tuesday'
            WHEN 3 THEN 'wednesday'
            WHEN 4 THEN 'thursday'
            WHEN 5 THEN 'friday'
            WHEN 6 THEN 'saturday'
        END) THEN
            v_window_start := (v_window->>'start_time')::TIME;
            v_window_end := (v_window->>'end_time')::TIME;
            
            -- Check if current time is within window
            IF v_local_time >= v_window_start AND v_local_time <= v_window_end THEN
                v_allowed := true;
                v_current_end := (p_check_time::DATE + v_window_end) AT TIME ZONE v_timezone;
                EXIT;
            END IF;
        END IF;
    END LOOP;
    
    -- Calculate next window if not currently allowed
    IF NOT v_allowed THEN
        -- This would require more complex logic to find the next available window
        -- For now, return NULL
        v_next_start := NULL;
    END IF;
    
    RETURN QUERY SELECT v_allowed, v_next_start, v_current_end, true;
END;
$$ LANGUAGE plpgsql;

-- Function to generate unique override code
CREATE OR REPLACE FUNCTION generate_override_code()
RETURNS VARCHAR(8) AS $$
DECLARE
    v_code VARCHAR(8);
    v_exists BOOLEAN;
BEGIN
    LOOP
        v_code := UPPER(substring(md5(random()::text) from 1 for 8));
        SELECT EXISTS(SELECT 1 FROM classroom_test_overrides WHERE override_code = v_code) INTO v_exists;
        EXIT WHEN NOT v_exists;
    END LOOP;
    RETURN v_code;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate final test score
CREATE OR REPLACE FUNCTION calculate_test_final_score(
    p_test_attempt_id UUID
) RETURNS DECIMAL(5,2) AS $$
DECLARE
    v_total_points INTEGER := 0;
    v_max_points INTEGER := 100;
    v_score DECIMAL(5,2);
BEGIN
    SELECT COALESCE(SUM(points_earned), 0) INTO v_total_points
    FROM test_question_evaluations
    WHERE test_attempt_id = p_test_attempt_id;
    
    v_score := (v_total_points::DECIMAL / v_max_points::DECIMAL) * 100;
    
    -- Update the test attempt with the calculated score
    UPDATE student_test_attempts
    SET score = v_score,
        evaluation_status = 'completed',
        evaluated_at = CURRENT_TIMESTAMP
    WHERE id = p_test_attempt_id;
    
    RETURN v_score;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamp triggers
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classrooms_updated_at
    BEFORE UPDATE ON classrooms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reading_assignments_updated_at
    BEFORE UPDATE ON reading_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reading_question_cache_updated_at
    BEFORE UPDATE ON reading_question_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_assignment_tests_updated_at
    BEFORE UPDATE ON assignment_tests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_student_assignments_updated_at
    BEFORE UPDATE ON student_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_student_test_attempts_updated_at
    BEFORE UPDATE ON student_test_attempts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_question_evaluations_updated_at
    BEFORE UPDATE ON test_question_evaluations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_lists_updated_at
    BEFORE UPDATE ON vocabulary_lists
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_words_updated_at
    BEFORE UPDATE ON vocabulary_words
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_assignments_updated_at
    BEFORE UPDATE ON test_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_debate_assignments_updated_at
    BEFORE UPDATE ON debate_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_writing_assignments_updated_at
    BEFORE UPDATE ON writing_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_student_writing_submissions_updated_at
    BEFORE UPDATE ON student_writing_submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_lecture_assignments_updated_at
    BEFORE UPDATE ON lecture_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_classroom_test_schedules_updated_at
    BEFORE UPDATE ON classroom_test_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_gradebook_entries_updated_at
    BEFORE UPDATE ON gradebook_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_student_reading_progress_updated_at
    BEFORE UPDATE ON student_reading_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_student_test_progress_updated_at
    BEFORE UPDATE ON student_test_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_whitelist ENABLE ROW LEVEL SECURITY;
ALTER TABLE otp_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE classrooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignment_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_question_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_student_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignment_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_test_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_question_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE vocabulary_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE vocabulary_words ENABLE ROW LEVEL SECURITY;
ALTER TABLE vocabulary_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE vocabulary_test_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_question_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE debate_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE writing_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_writing_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE lecture_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE lecture_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_test_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_test_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_override_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE gradebook_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_reading_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_test_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_cache_flush_log ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Users can view their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT
    USING (id = current_setting('app.current_user_id', true)::uuid);

-- Teachers can view their classrooms
CREATE POLICY "Teachers access own classrooms" ON classrooms
    FOR ALL
    USING (teacher_id = current_setting('app.current_user_id', true)::uuid);

-- Students can view classrooms they're enrolled in
CREATE POLICY "Students view enrolled classrooms" ON classrooms
    FOR SELECT
    USING (id IN (
        SELECT classroom_id FROM classroom_students 
        WHERE student_id = current_setting('app.current_user_id', true)::uuid
    ));

-- Classroom students policies
CREATE POLICY "Teachers manage classroom students" ON classroom_students
    FOR ALL
    USING (classroom_id IN (
        SELECT id FROM classrooms 
        WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
    ));

CREATE POLICY "Students view own enrollment" ON classroom_students
    FOR SELECT
    USING (student_id = current_setting('app.current_user_id', true)::uuid);

-- Classroom assignments policies
CREATE POLICY "Teachers manage classroom assignments" ON classroom_assignments
    FOR ALL
    USING (classroom_id IN (
        SELECT id FROM classrooms 
        WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
    ));

CREATE POLICY "Students view classroom assignments" ON classroom_assignments
    FOR SELECT
    USING (classroom_id IN (
        SELECT classroom_id FROM classroom_students 
        WHERE student_id = current_setting('app.current_user_id', true)::uuid 
        AND status = 'active'
    ));

-- Reading assignments policies
CREATE POLICY "Teachers manage reading assignments" ON reading_assignments
    FOR ALL
    USING (teacher_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY "Students view assigned reading" ON reading_assignments
    FOR SELECT
    USING (id IN (
        SELECT ca.assignment_id FROM classroom_assignments ca
        JOIN classroom_students cs ON ca.classroom_id = cs.classroom_id
        WHERE cs.student_id = current_setting('app.current_user_id', true)::uuid
        AND cs.status = 'active'
        AND ca.assignment_type = 'reading'
    ));

-- Reading chunks policies
CREATE POLICY "Teachers manage reading chunks" ON reading_chunks
    FOR ALL
    USING (assignment_id IN (
        SELECT id FROM reading_assignments 
        WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
    ));

CREATE POLICY "Students view assigned chunks" ON reading_chunks
    FOR SELECT
    USING (assignment_id IN (
        SELECT ca.assignment_id FROM classroom_assignments ca
        JOIN classroom_students cs ON ca.classroom_id = cs.classroom_id
        WHERE cs.student_id = current_setting('app.current_user_id', true)::uuid
        AND cs.status = 'active'
        AND ca.assignment_type = 'reading'
    ));

-- Student assignment policies
CREATE POLICY "Teachers view student assignments" ON student_assignments
    FOR SELECT
    USING (classroom_assignment_id IN (
        SELECT ca.id FROM classroom_assignments ca
        JOIN classrooms c ON ca.classroom_id = c.id
        WHERE c.teacher_id = current_setting('app.current_user_id', true)::uuid
    ));

CREATE POLICY "Students manage own assignments" ON student_assignments
    FOR ALL
    USING (student_id = current_setting('app.current_user_id', true)::uuid);

-- Student test attempts policies
CREATE POLICY "Teachers view student test attempts" ON student_test_attempts
    FOR SELECT
    USING (
        assignment_id IN (
            SELECT id FROM reading_assignments 
            WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
        )
        OR test_id IN (
            SELECT id FROM test_assignments 
            WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

CREATE POLICY "Students manage own test attempts" ON student_test_attempts
    FOR ALL
    USING (student_id = current_setting('app.current_user_id', true)::uuid);

-- Students can view questions for active assignments
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'reading_question_cache' 
        AND policyname = 'Students can view questions for active assignments'
    ) THEN
        CREATE POLICY "Students can view questions for active assignments"
            ON reading_question_cache FOR SELECT
            USING (
                assignment_id IN (
                    SELECT sa.assignment_id 
                    FROM student_assignments sa
                    WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
                    AND sa.status IN ('in_progress', 'test_available')
                )
            );
    END IF;
END
$$;

-- Students can view tests for completed assignments
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'assignment_tests' 
        AND policyname = 'Students can view tests for completed assignments'
    ) THEN
        CREATE POLICY "Students can view tests for completed assignments"
            ON assignment_tests FOR SELECT
            USING (
                assignment_id IN (
                    SELECT sa.assignment_id 
                    FROM student_assignments sa
                    WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
                    AND sa.status IN ('test_available', 'test_completed')
                )
            );
    END IF;
END
$$;

-- Students can use override codes
CREATE POLICY "Students use override codes" ON classroom_test_overrides
    FOR SELECT
    USING (
        classroom_id IN (
            SELECT classroom_id FROM classroom_students 
            WHERE student_id = current_setting('app.current_user_id', true)::uuid AND status = 'active'
        )
    );

-- Track override usage
CREATE POLICY "Track override usage" ON test_override_usage
    FOR INSERT
    WITH CHECK (student_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY "View override usage" ON test_override_usage
    FOR SELECT
    USING (
        student_id = current_setting('app.current_user_id', true)::uuid OR
        override_id IN (
            SELECT id FROM classroom_test_overrides 
            WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default admin user roles
INSERT INTO users (email, first_name, last_name, username, role, is_admin)
VALUES 
    ('admin@umadex.com', 'Admin', 'User', 'admin', 'teacher', true),
    ('demo@teacher.com', 'Demo', 'Teacher', 'demo_teacher', 'teacher', false)
ON CONFLICT (email) DO NOTHING;

-- Insert default whitelist entries
INSERT INTO email_whitelist (email_pattern, is_domain)
VALUES 
    ('umadex.com', true),
    ('demo.edu', true),
    ('test.com', true)
ON CONFLICT (email_pattern) DO NOTHING;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE users IS 'Core user accounts for students and teachers';
COMMENT ON TABLE classrooms IS 'Teacher-managed classrooms containing students';
COMMENT ON TABLE reading_assignments IS 'UMARead assignments with literary content';
COMMENT ON TABLE student_assignments IS 'Individual student progress tracking';
COMMENT ON TABLE student_test_attempts IS 'Unified test attempts for all modules';
COMMENT ON TABLE vocabulary_lists IS 'UMAVocab vocabulary learning lists';
COMMENT ON TABLE test_assignments IS 'UMATest structured assessments';
COMMENT ON TABLE debate_assignments IS 'UMADebate discussion assignments';
COMMENT ON TABLE writing_assignments IS 'UMAWrite composition assignments';
COMMENT ON TABLE lecture_assignments IS 'UMALecture educational content';
COMMENT ON TABLE classroom_test_schedules IS 'Time-based testing restrictions';
COMMENT ON TABLE gradebook_entries IS 'Student grade tracking across modules';

COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates timestamp columns';
COMMENT ON FUNCTION can_proceed_to_next_chunk() IS 'Validates reading progression requirements';
COMMENT ON FUNCTION is_testing_allowed() IS 'Checks if testing is permitted based on schedule';
COMMENT ON FUNCTION generate_override_code() IS 'Creates unique emergency access codes';
COMMENT ON FUNCTION calculate_test_final_score() IS 'Computes final test scores from evaluations';