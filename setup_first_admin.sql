-- Setup script for first admin account: admin@csd8.info
-- Run this script in your PostgreSQL database

-- 1. Add the admin email to the whitelist so they can register
INSERT INTO email_whitelist (email_pattern, is_domain, created_at) 
VALUES ('admin@csd8.info', false, CURRENT_TIMESTAMP)
ON CONFLICT (email_pattern) DO NOTHING;

-- 2. Also add the domain so other users from csd8.info can register
INSERT INTO email_whitelist (email_pattern, is_domain, created_at) 
VALUES ('csd8.info', true, CURRENT_TIMESTAMP)
ON CONFLICT (email_pattern) DO NOTHING;

-- 3. If the user already exists, promote them to admin
-- (This will only work if they've already registered)
UPDATE users 
SET is_admin = true, updated_at = CURRENT_TIMESTAMP
WHERE email = 'admin@csd8.info' AND deleted_at IS NULL;

-- 4. Check if the user exists and show result
DO $$
DECLARE
    user_count INTEGER;
    whitelist_count INTEGER;
BEGIN
    -- Check whitelist entries
    SELECT COUNT(*) INTO whitelist_count 
    FROM email_whitelist 
    WHERE email_pattern IN ('admin@csd8.info', 'csd8.info');
    
    -- Check if user exists
    SELECT COUNT(*) INTO user_count 
    FROM users 
    WHERE email = 'admin@csd8.info' AND deleted_at IS NULL;
    
    RAISE NOTICE 'Setup Results:';
    RAISE NOTICE '- Email whitelist entries added: %', whitelist_count;
    
    IF user_count > 0 THEN
        RAISE NOTICE '- User admin@csd8.info found and promoted to admin';
        RAISE NOTICE '- You can now access the admin panel at /admin/dashboard';
    ELSE
        RAISE NOTICE '- User admin@csd8.info not found yet';
        RAISE NOTICE '- Next steps:';
        RAISE NOTICE '  1. Go to your app login page';
        RAISE NOTICE '  2. Register with email: admin@csd8.info';
        RAISE NOTICE '  3. Run this command after registration:';
        RAISE NOTICE '     UPDATE users SET is_admin = true WHERE email = ''admin@csd8.info'';';
    END IF;
END $$;