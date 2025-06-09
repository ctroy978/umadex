-- Run this AFTER admin@csd8.info has registered through the normal signup flow
-- This promotes the existing user to admin status

UPDATE users 
SET is_admin = true, updated_at = CURRENT_TIMESTAMP
WHERE email = 'admin@csd8.info' 
AND deleted_at IS NULL;

-- Verify the admin was created
SELECT 
    id,
    email,
    first_name,
    last_name,
    role,
    is_admin,
    created_at
FROM users 
WHERE email = 'admin@csd8.info';

-- Show confirmation message
DO $$
DECLARE
    admin_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO admin_count 
    FROM users 
    WHERE email = 'admin@csd8.info' AND is_admin = true AND deleted_at IS NULL;
    
    IF admin_count > 0 THEN
        RAISE NOTICE 'SUCCESS: admin@csd8.info is now an admin!';
        RAISE NOTICE 'They can access the admin panel at: /admin/dashboard';
    ELSE
        RAISE NOTICE 'ERROR: User admin@csd8.info was not found or could not be promoted';
        RAISE NOTICE 'Make sure they have registered first through the normal signup flow';
    END IF;
END $$;