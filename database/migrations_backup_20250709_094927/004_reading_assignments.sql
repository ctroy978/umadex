-- Reading Assignments Feature Tables
-- Migration: 004_reading_assignments.sql

-- Main assignments table
CREATE TABLE reading_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID REFERENCES users(id),
    assignment_title VARCHAR(255) NOT NULL,
    work_title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    grade_level VARCHAR(50) NOT NULL,
    work_type VARCHAR(20) NOT NULL CHECK (work_type IN ('fiction', 'non-fiction')),
    literary_form VARCHAR(20) NOT NULL CHECK (literary_form IN ('prose', 'poetry', 'drama', 'mixed')),
    genre VARCHAR(50) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    raw_content TEXT NOT NULL,
    total_chunks INTEGER,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Parsed chunks
CREATE TABLE reading_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID REFERENCES reading_assignments(id) ON DELETE CASCADE,
    chunk_order INTEGER NOT NULL,
    content TEXT NOT NULL,
    has_important_sections BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Assignment images
CREATE TABLE assignment_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID REFERENCES reading_assignments(id) ON DELETE CASCADE,
    image_key VARCHAR(50) NOT NULL,
    custom_name VARCHAR(100),
    file_url TEXT NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(50),
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX idx_reading_assignments_teacher_id ON reading_assignments(teacher_id);
CREATE INDEX idx_reading_assignments_status ON reading_assignments(status);
CREATE INDEX idx_reading_chunks_assignment_id ON reading_chunks(assignment_id);
CREATE INDEX idx_assignment_images_assignment_id ON assignment_images(assignment_id);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_reading_assignments_updated_at BEFORE UPDATE
    ON reading_assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();