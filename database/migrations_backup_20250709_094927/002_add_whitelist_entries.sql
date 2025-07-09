-- Add additional whitelist entries for domains and specific email
INSERT INTO email_whitelist (email_pattern, is_domain) VALUES
    ('csd8.info', true),
    ('coquille.k12.or.us', true),
    ('ctroy978@gmail.com', false)
ON CONFLICT (email_pattern) DO NOTHING;