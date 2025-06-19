-- Migration: Update vocabulary test question format for AI-enhanced testing
-- This migration documents the change in the JSONB structure of the questions field
-- in the vocabulary_tests table. No schema changes are required as the field is JSONB.

-- Previous question format:
-- {
--   "id": "word_uuid",
--   "word": "vocabulary_word",
--   "definition": "word_definition",
--   "question_type": "definition|example|riddle",
--   "question_text": "What does the word 'X' mean?",
--   "correct_answer": "vocabulary_word",
--   "vocabulary_list_id": "list_uuid",
--   "difficulty_level": "standard"
-- }

-- New question format:
-- {
--   "id": "word_uuid",
--   "word": "vocabulary_word",
--   "example_sentence": "The word used in a contextual sentence.",
--   "reference_definition": "Teacher or AI generated definition for evaluation",
--   "question_type": "definition_from_context",
--   "vocabulary_list_id": "list_uuid"
-- }

-- The evaluation system has also been updated:
-- - Old: Simple string matching with Levenshtein distance
-- - New: AI-powered evaluation of student-provided definitions

-- Add a comment to track this change
COMMENT ON TABLE vocabulary_tests IS 
'Stores vocabulary test data. As of migration 059, questions use the new AI-enhanced format where students provide definitions based on contextual examples.';