-- Update the chain_type check constraint to include 'named_chain'
ALTER TABLE vocabulary_test_configs 
DROP CONSTRAINT vocabulary_test_configs_chain_type_check;

ALTER TABLE vocabulary_test_configs 
ADD CONSTRAINT vocabulary_test_configs_chain_type_check 
CHECK (chain_type IN ('weeks', 'specific_lists', 'named_chain'));