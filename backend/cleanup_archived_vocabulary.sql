-- This script will handle archived vocabulary lists
-- Option 1: Convert archived to deleted (preserving data)
UPDATE vocabulary_lists 
SET deleted_at = NOW(), 
    status = 'published'
WHERE status = 'archived';

-- Option 2: If you want to completely remove archived lists (destructive)
-- DELETE FROM vocabulary_lists WHERE status = 'archived';

-- Check the results
SELECT id, title, status, deleted_at 
FROM vocabulary_lists 
WHERE deleted_at IS NOT NULL;