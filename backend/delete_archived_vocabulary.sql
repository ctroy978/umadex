-- Delete all vocabulary lists with status = 'archived'
DELETE FROM vocabulary_lists WHERE status = 'archived';

-- Verify the deletion
SELECT COUNT(*) as remaining_archived FROM vocabulary_lists WHERE status = 'archived';

-- Show remaining vocabulary lists
SELECT id, title, status, created_at FROM vocabulary_lists ORDER BY created_at DESC;