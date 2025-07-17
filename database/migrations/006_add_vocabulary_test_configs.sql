-- Migration: Add vocabulary_test_configs table
-- Description: Add missing vocabulary test configuration table
-- Date: 2025-07-17

-- Create vocabulary_test_configs table if it doesn't exist
CREATE TABLE IF NOT EXISTS vocabulary_test_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    chain_enabled BOOLEAN DEFAULT FALSE,
    chain_type VARCHAR(50) DEFAULT 'weeks' CHECK (chain_type IN ('weeks', 'specific_lists', 'named_chain')),
    weeks_to_include INTEGER DEFAULT 1,
    questions_per_week INTEGER DEFAULT 5,
    chained_list_ids UUID[] DEFAULT '{}',
    chain_id UUID DEFAULT NULL,
    total_review_words INTEGER DEFAULT 3,
    current_week_questions INTEGER DEFAULT 10,
    max_attempts INTEGER DEFAULT 3,
    time_limit_minutes INTEGER DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(vocabulary_list_id)
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_vocabulary_test_configs_vocabulary_list_id ON vocabulary_test_configs(vocabulary_list_id);