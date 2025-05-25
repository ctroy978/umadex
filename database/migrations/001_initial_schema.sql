-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create enum for user roles
CREATE TYPE user_role AS ENUM ('student', 'teacher');

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    username VARCHAR(255) UNIQUE NOT NULL,
    role user_role DEFAULT 'student' NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create email whitelist table
CREATE TABLE email_whitelist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_pattern VARCHAR(255) NOT NULL UNIQUE,
    is_domain BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create OTP requests table
CREATE TABLE otp_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    otp_code VARCHAR(6) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create user sessions table
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_otp_requests_email ON otp_requests(email);
CREATE INDEX idx_otp_requests_expires ON otp_requests(expires_at);
CREATE INDEX idx_user_sessions_token ON user_sessions(token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);

-- Create function to generate username from email
CREATE OR REPLACE FUNCTION generate_username(email_input VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    local_part VARCHAR;
    domain_part VARCHAR;
    domain_name VARCHAR;
    base_username VARCHAR;
    final_username VARCHAR;
    counter INTEGER := 0;
BEGIN
    -- Split email into local and domain parts
    local_part := SPLIT_PART(email_input, '@', 1);
    domain_part := SPLIT_PART(email_input, '@', 2);
    
    -- Extract domain name (without TLD)
    domain_name := SPLIT_PART(domain_part, '.', 1);
    
    -- Replace dots with hyphens in local part
    local_part := REPLACE(local_part, '.', '-');
    
    -- Combine to create base username
    base_username := LOWER(local_part || '-' || domain_name);
    
    -- Remove any special characters except hyphens
    base_username := REGEXP_REPLACE(base_username, '[^a-z0-9-]', '', 'g');
    
    -- Check if username already exists and append number if needed
    final_username := base_username;
    WHILE EXISTS (SELECT 1 FROM users WHERE username = final_username) LOOP
        counter := counter + 1;
        final_username := base_username || '-' || counter;
    END LOOP;
    
    RETURN final_username;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-generate username
CREATE OR REPLACE FUNCTION trigger_generate_username()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.username IS NULL OR NEW.username = '' THEN
        NEW.username := generate_username(NEW.email);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_insert_user_generate_username
BEFORE INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION trigger_generate_username();

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_whitelist ENABLE ROW LEVEL SECURITY;
ALTER TABLE otp_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for users table
CREATE POLICY users_select_own ON users
    FOR SELECT
    USING (id = current_setting('app.current_user_id', true)::uuid OR 
           current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY users_update_own ON users
    FOR UPDATE
    USING (id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (id = current_setting('app.current_user_id', true)::uuid);

-- Admin policies for users
CREATE POLICY users_admin_all ON users
    FOR ALL
    USING (current_setting('app.is_admin', true)::boolean = true);

-- Create RLS policies for email_whitelist (admin only)
CREATE POLICY whitelist_admin_all ON email_whitelist
    FOR ALL
    USING (current_setting('app.is_admin', true)::boolean = true);

-- Create RLS policies for otp_requests
CREATE POLICY otp_requests_insert_all ON otp_requests
    FOR INSERT
    WITH CHECK (true);

CREATE POLICY otp_requests_select_own ON otp_requests
    FOR SELECT
    USING (email = current_setting('app.current_user_email', true) OR
           current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY otp_requests_update_own ON otp_requests
    FOR UPDATE
    USING (email = current_setting('app.current_user_email', true))
    WITH CHECK (email = current_setting('app.current_user_email', true));

-- Create RLS policies for user_sessions
CREATE POLICY sessions_select_own ON user_sessions
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id', true)::uuid OR
           current_setting('app.is_admin', true)::boolean = true);

CREATE POLICY sessions_delete_own ON user_sessions
    FOR DELETE
    USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY sessions_insert_authenticated ON user_sessions
    FOR INSERT
    WITH CHECK (true);

-- Insert default whitelist entries (examples)
INSERT INTO email_whitelist (email_pattern, is_domain) VALUES
    ('swocc.edu', true),
    ('admin@umadex.local', false);

-- Create a default admin user (for development)
INSERT INTO users (email, first_name, last_name, username, role, is_admin) VALUES
    ('admin@umadex.local', 'Admin', 'User', 'admin-umadex', 'teacher', true);