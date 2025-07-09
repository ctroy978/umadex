-- Migration: Add Named Vocabulary Chains
-- Description: Create a system for named vocabulary test chains that teachers can manage
-- Author: Claude Code
-- Date: 2025-06-19

-- Create vocabulary chains table
CREATE TABLE vocabulary_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    total_review_words INTEGER DEFAULT 3 CHECK (total_review_words >= 1 AND total_review_words <= 4),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique chain names per teacher
    UNIQUE(teacher_id, name)
);

-- Create chain members table (links vocabulary lists to chains)
CREATE TABLE vocabulary_chain_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id UUID NOT NULL REFERENCES vocabulary_chains(id) ON DELETE CASCADE,
    vocabulary_list_id UUID NOT NULL REFERENCES vocabulary_lists(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0, -- Order within the chain
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure a vocabulary list can only be in a chain once
    UNIQUE(chain_id, vocabulary_list_id)
);

-- Update vocabulary_test_configs to reference chains instead of specific lists
ALTER TABLE vocabulary_test_configs
ADD COLUMN chain_id UUID REFERENCES vocabulary_chains(id) ON DELETE SET NULL;

-- Add comment explaining the new column
COMMENT ON COLUMN vocabulary_test_configs.chain_id IS 'Reference to the vocabulary chain to use for test chaining';

-- Create indexes for performance
CREATE INDEX idx_vocabulary_chains_teacher_id ON vocabulary_chains(teacher_id);
CREATE INDEX idx_vocabulary_chains_is_active ON vocabulary_chains(is_active);
CREATE INDEX idx_vocabulary_chain_members_chain_id ON vocabulary_chain_members(chain_id);
CREATE INDEX idx_vocabulary_chain_members_vocabulary_list_id ON vocabulary_chain_members(vocabulary_list_id);
CREATE INDEX idx_vocabulary_chain_members_position ON vocabulary_chain_members(chain_id, position);
CREATE INDEX idx_vocabulary_test_configs_chain_id ON vocabulary_test_configs(chain_id);

-- Create a view to easily see chain compositions
CREATE VIEW vocabulary_chain_details AS
SELECT 
    vc.id as chain_id,
    vc.name as chain_name,
    vc.description as chain_description,
    vc.total_review_words,
    vc.teacher_id,
    vcm.vocabulary_list_id,
    vcm.position,
    vl.title as vocabulary_list_title,
    (SELECT COUNT(*) FROM vocabulary_words vw WHERE vw.list_id = vl.id) as word_count,
    vl.grade_level,
    vl.subject_area,
    vl.status as list_status
FROM vocabulary_chains vc
LEFT JOIN vocabulary_chain_members vcm ON vc.id = vcm.chain_id
LEFT JOIN vocabulary_lists vl ON vcm.vocabulary_list_id = vl.id
WHERE vc.is_active = true
ORDER BY vc.name, vcm.position;

-- Migrate existing chain configurations to the new system
-- This creates a default chain for each teacher who has existing chain configurations
INSERT INTO vocabulary_chains (teacher_id, name, description, total_review_words)
SELECT DISTINCT 
    vl.teacher_id,
    'Default Chain',
    'Automatically created from existing chain configuration',
    COALESCE(vtc.total_review_words, 3)
FROM vocabulary_test_configs vtc
JOIN vocabulary_lists vl ON vtc.vocabulary_list_id = vl.id
WHERE vtc.chain_enabled = true
AND vtc.chain_type = 'specific_lists'
AND vtc.chained_list_ids IS NOT NULL
AND array_length(vtc.chained_list_ids, 1) > 0
ON CONFLICT (teacher_id, name) DO NOTHING;

-- Populate chain members from existing configurations
INSERT INTO vocabulary_chain_members (chain_id, vocabulary_list_id, position)
SELECT 
    vc.id,
    unnest(vtc.chained_list_ids),
    row_number() OVER (PARTITION BY vc.id ORDER BY vl2.created_at) - 1
FROM vocabulary_test_configs vtc
JOIN vocabulary_lists vl ON vtc.vocabulary_list_id = vl.id
JOIN vocabulary_chains vc ON vc.teacher_id = vl.teacher_id AND vc.name = 'Default Chain'
JOIN vocabulary_lists vl2 ON vl2.id = ANY(vtc.chained_list_ids)
WHERE vtc.chain_enabled = true
AND vtc.chain_type = 'specific_lists'
AND vtc.chained_list_ids IS NOT NULL
AND array_length(vtc.chained_list_ids, 1) > 0
ON CONFLICT (chain_id, vocabulary_list_id) DO NOTHING;

-- Also add the current list to its own chain
INSERT INTO vocabulary_chain_members (chain_id, vocabulary_list_id, position)
SELECT 
    vc.id,
    vtc.vocabulary_list_id,
    COALESCE(MAX(vcm.position) + 1, 0)
FROM vocabulary_test_configs vtc
JOIN vocabulary_lists vl ON vtc.vocabulary_list_id = vl.id
JOIN vocabulary_chains vc ON vc.teacher_id = vl.teacher_id AND vc.name = 'Default Chain'
LEFT JOIN vocabulary_chain_members vcm ON vcm.chain_id = vc.id
WHERE vtc.chain_enabled = true
AND vtc.chain_type = 'specific_lists'
AND vtc.chained_list_ids IS NOT NULL
AND array_length(vtc.chained_list_ids, 1) > 0
GROUP BY vc.id, vtc.vocabulary_list_id
ON CONFLICT (chain_id, vocabulary_list_id) DO NOTHING;

-- Update test configs to reference the new chains
UPDATE vocabulary_test_configs vtc
SET chain_id = vc.id
FROM vocabulary_lists vl
JOIN vocabulary_chains vc ON vc.teacher_id = vl.teacher_id AND vc.name = 'Default Chain'
WHERE vtc.vocabulary_list_id = vl.id
AND vtc.chain_enabled = true
AND vtc.chain_type = 'specific_lists';