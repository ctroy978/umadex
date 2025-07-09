-- Add unique constraint to vocabulary_test_configs
ALTER TABLE vocabulary_test_configs
ADD CONSTRAINT vocabulary_test_configs_vocabulary_list_id_key UNIQUE (vocabulary_list_id);