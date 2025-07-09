-- Add vocabulary tables for UMAVocab module

-- Main vocabulary list table
CREATE TABLE vocabulary_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    context_description TEXT NOT NULL,
    grade_level VARCHAR(50) NOT NULL,
    subject_area VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'reviewing', 'published', 'archived')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Individual vocabulary words
CREATE TABLE vocabulary_words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    word VARCHAR(100) NOT NULL,
    teacher_definition TEXT,
    teacher_example_1 TEXT,
    teacher_example_2 TEXT,
    ai_definition TEXT,
    ai_example_1 TEXT,
    ai_example_2 TEXT,
    definition_source VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (definition_source IN ('pending', 'ai', 'teacher')),
    examples_source VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (examples_source IN ('pending', 'ai', 'teacher')),
    position INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Track word review status and feedback
CREATE TABLE vocabulary_word_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word_id UUID NOT NULL REFERENCES vocabulary_words(id) ON DELETE CASCADE,
    review_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending', 'accepted', 'rejected_once', 'rejected_twice')),
    rejection_feedback TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_vocabulary_lists_teacher_id ON vocabulary_lists(teacher_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_vocabulary_lists_status ON vocabulary_lists(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_vocabulary_words_list_id ON vocabulary_words(list_id);
CREATE INDEX idx_vocabulary_words_position ON vocabulary_words(list_id, position);
CREATE INDEX idx_vocabulary_word_reviews_word_id ON vocabulary_word_reviews(word_id);
CREATE INDEX idx_vocabulary_word_reviews_status ON vocabulary_word_reviews(review_status);

-- Enable RLS
ALTER TABLE vocabulary_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE vocabulary_words ENABLE ROW LEVEL SECURITY;
ALTER TABLE vocabulary_word_reviews ENABLE ROW LEVEL SECURITY;

-- RLS Policies for vocabulary_lists
-- Initial policy - will be updated in migration 018 when assignment_type is added
CREATE POLICY vocabulary_lists_select ON vocabulary_lists
    FOR SELECT
    USING (
        teacher_id = current_setting('app.current_user_id')::UUID
        OR current_setting('app.current_user_role') = 'admin'
    );

CREATE POLICY vocabulary_lists_insert ON vocabulary_lists
    FOR INSERT
    WITH CHECK (
        teacher_id = current_setting('app.current_user_id')::UUID
        AND current_setting('app.current_user_role') = 'teacher'
    );

CREATE POLICY vocabulary_lists_update ON vocabulary_lists
    FOR UPDATE
    USING (
        teacher_id = current_setting('app.current_user_id')::UUID
        OR current_setting('app.current_user_role') = 'admin'
    );

CREATE POLICY vocabulary_lists_delete ON vocabulary_lists
    FOR DELETE
    USING (
        teacher_id = current_setting('app.current_user_id')::UUID
        OR current_setting('app.current_user_role') = 'admin'
    );

-- RLS Policies for vocabulary_words (inherit from list permissions)
-- Initial policy - will be updated in migration 018 when assignment_type is added
CREATE POLICY vocabulary_words_all ON vocabulary_words
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM vocabulary_lists vl
            WHERE vl.id = vocabulary_words.list_id
            AND (
                vl.teacher_id = current_setting('app.current_user_id')::UUID
                OR current_setting('app.current_user_role') = 'admin'
            )
        )
    );

-- RLS Policies for vocabulary_word_reviews (inherit from list permissions)
CREATE POLICY vocabulary_word_reviews_all ON vocabulary_word_reviews
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM vocabulary_words vw
            JOIN vocabulary_lists vl ON vl.id = vw.list_id
            WHERE vw.id = vocabulary_word_reviews.word_id
            AND (
                vl.teacher_id = current_setting('app.current_user_id')::UUID
                OR current_setting('app.current_user_role') = 'admin'
            )
        )
    );

-- Add trigger to update updated_at timestamp
CREATE TRIGGER update_vocabulary_lists_updated_at BEFORE UPDATE ON vocabulary_lists
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_words_updated_at BEFORE UPDATE ON vocabulary_words
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE vocabulary_lists IS 'Stores vocabulary lists created by teachers';
COMMENT ON TABLE vocabulary_words IS 'Individual words within vocabulary lists with AI and teacher content';
COMMENT ON TABLE vocabulary_word_reviews IS 'Tracks review status and feedback for vocabulary words';
COMMENT ON COLUMN vocabulary_lists.status IS 'draft, processing, reviewing, published, archived';
COMMENT ON COLUMN vocabulary_words.definition_source IS 'Source of the current definition: pending, ai, teacher';
COMMENT ON COLUMN vocabulary_words.examples_source IS 'Source of the current examples: pending, ai, teacher';