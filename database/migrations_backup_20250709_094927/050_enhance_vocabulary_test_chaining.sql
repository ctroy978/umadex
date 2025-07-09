-- Migration: Enhance Vocabulary Test Chaining
-- Description: Update vocabulary test system to support selecting specific lists and 1-4 review words
-- Author: Claude Code
-- Date: 2025-06-19

-- Add new columns to vocabulary_test_configs table
ALTER TABLE vocabulary_test_configs
ADD COLUMN chain_type VARCHAR(20) DEFAULT 'weeks' CHECK (chain_type IN ('weeks', 'specific_lists')),
ADD COLUMN chained_list_ids UUID[] DEFAULT '{}',
ADD COLUMN total_review_words INTEGER DEFAULT 3 CHECK (total_review_words >= 1 AND total_review_words <= 4);

-- Add comment explaining the new columns
COMMENT ON COLUMN vocabulary_test_configs.chain_type IS 'Type of chaining: weeks (previous N weeks) or specific_lists (selected lists)';
COMMENT ON COLUMN vocabulary_test_configs.chained_list_ids IS 'Array of vocabulary list IDs to chain when chain_type is specific_lists';
COMMENT ON COLUMN vocabulary_test_configs.total_review_words IS 'Total number of review words to include from all chained lists (1-4)';

-- Create index for chained_list_ids array
CREATE INDEX idx_vocabulary_test_configs_chained_lists ON vocabulary_test_configs USING GIN (chained_list_ids);

-- Update existing configs to use the new structure
UPDATE vocabulary_test_configs
SET chain_type = 'weeks',
    total_review_words = LEAST(questions_per_week * weeks_to_include, 4)
WHERE chain_enabled = TRUE;