-- Fix lecture_images foreign key to reference reading_assignments instead of lecture_assignments
-- Since UMALectures are stored in reading_assignments table, we need to update the reference

-- First, drop the existing foreign key constraint
ALTER TABLE lecture_images 
DROP CONSTRAINT IF EXISTS lecture_images_lecture_id_fkey;

-- Add new foreign key constraint to reading_assignments
ALTER TABLE lecture_images 
ADD CONSTRAINT lecture_images_lecture_id_fkey 
FOREIGN KEY (lecture_id) 
REFERENCES reading_assignments(id) 
ON DELETE CASCADE;

-- Update the RLS policies to work with reading_assignments table

-- Drop existing policies
DROP POLICY IF EXISTS lecture_images_teacher_all ON lecture_images;
DROP POLICY IF EXISTS lecture_images_student_select ON lecture_images;

-- Recreate policies to use reading_assignments table
-- Teachers can manage images for their lectures
CREATE POLICY lecture_images_teacher_all ON lecture_images
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM reading_assignments ra
            WHERE ra.id = lecture_images.lecture_id
            AND ra.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND ra.assignment_type = 'UMALecture'
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM reading_assignments ra
            WHERE ra.id = lecture_images.lecture_id
            AND ra.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND ra.assignment_type = 'UMALecture'
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    );

-- Students can view images for assigned lectures
CREATE POLICY lecture_images_student_select ON lecture_images
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM reading_assignments ra
            JOIN student_assignments sa ON true
            JOIN classroom_assignments ca ON ca.id = sa.classroom_assignment_id
            WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
            AND ca.assignment_id = ra.id
            AND ca.assignment_type = 'UMALecture'
            AND ra.id = lecture_images.lecture_id
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'student'
            )
        )
    );

-- Also update lecture_content_cache policies to use reading_assignments
DROP POLICY IF EXISTS lecture_cache_teacher_all ON lecture_content_cache;
DROP POLICY IF EXISTS lecture_cache_student_select ON lecture_content_cache;

-- Update lecture_content_cache foreign key
ALTER TABLE lecture_content_cache 
DROP CONSTRAINT IF EXISTS lecture_content_cache_lecture_id_fkey;

ALTER TABLE lecture_content_cache 
ADD CONSTRAINT lecture_content_cache_lecture_id_fkey 
FOREIGN KEY (lecture_id) 
REFERENCES reading_assignments(id) 
ON DELETE CASCADE;

-- Recreate policies for lecture_content_cache
CREATE POLICY lecture_cache_teacher_all ON lecture_content_cache
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM reading_assignments ra
            WHERE ra.id = lecture_content_cache.lecture_id
            AND ra.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND ra.assignment_type = 'UMALecture'
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM reading_assignments ra
            WHERE ra.id = lecture_content_cache.lecture_id
            AND ra.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND ra.assignment_type = 'UMALecture'
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    );

CREATE POLICY lecture_cache_student_select ON lecture_content_cache
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM reading_assignments ra
            JOIN student_assignments sa ON true
            JOIN classroom_assignments ca ON ca.id = sa.classroom_assignment_id
            WHERE sa.student_id = current_setting('app.current_user_id', true)::uuid
            AND ca.assignment_id = ra.id
            AND ca.assignment_type = 'UMALecture'
            AND ra.id = lecture_content_cache.lecture_id
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'student'
            )
        )
    );

-- Update lecture_student_interactions foreign key and policies
DROP POLICY IF EXISTS lecture_interactions_teacher_select ON lecture_student_interactions;

ALTER TABLE lecture_student_interactions 
DROP CONSTRAINT IF EXISTS lecture_student_interactions_lecture_id_fkey;

ALTER TABLE lecture_student_interactions 
ADD CONSTRAINT lecture_student_interactions_lecture_id_fkey 
FOREIGN KEY (lecture_id) 
REFERENCES reading_assignments(id) 
ON DELETE CASCADE;

-- Recreate policy for teachers to view interactions
CREATE POLICY lecture_interactions_teacher_select ON lecture_student_interactions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM reading_assignments ra
            WHERE ra.id = lecture_student_interactions.lecture_id
            AND ra.teacher_id = current_setting('app.current_user_id', true)::uuid
            AND ra.assignment_type = 'UMALecture'
            AND EXISTS (
                SELECT 1 FROM users 
                WHERE id = current_setting('app.current_user_id', true)::uuid
                AND role = 'teacher'
            )
        )
    );

-- Since we're not using lecture_assignments table, we can drop it to avoid confusion
DROP TABLE IF EXISTS lecture_assignments CASCADE;

-- Add a comment to clarify the design
COMMENT ON TABLE lecture_images IS 'Images for UMALecture assignments stored in reading_assignments table';
COMMENT ON TABLE lecture_content_cache IS 'AI-generated content cache for UMALecture assignments stored in reading_assignments table';
COMMENT ON TABLE lecture_student_interactions IS 'Student interactions with UMALecture assignments stored in reading_assignments table';