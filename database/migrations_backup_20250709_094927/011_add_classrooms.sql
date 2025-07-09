-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add missing columns to existing classrooms table
DO $$
BEGIN
    -- Add class_code if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'classrooms' 
        AND column_name = 'class_code'
    ) THEN
        ALTER TABLE classrooms ADD COLUMN class_code VARCHAR(8) UNIQUE NOT NULL DEFAULT substr(md5(random()::text), 1, 8);
    END IF;

    -- Add deleted_at if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'classrooms' 
        AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE classrooms ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- Add missing columns to existing classroom_students table
DO $$
BEGIN
    -- Add removed_at if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'classroom_students' 
        AND column_name = 'removed_at'
    ) THEN
        ALTER TABLE classroom_students ADD COLUMN removed_at TIMESTAMP WITH TIME ZONE;
    END IF;

    -- Add removed_by if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'classroom_students' 
        AND column_name = 'removed_by'
    ) THEN
        ALTER TABLE classroom_students ADD COLUMN removed_by UUID REFERENCES users(id);
    END IF;
END $$;

-- Create classroom_assignments table if it doesn't exist
CREATE TABLE IF NOT EXISTS classroom_assignments (
    id SERIAL PRIMARY KEY,
    classroom_id UUID REFERENCES classrooms(id),
    assignment_id UUID REFERENCES reading_assignments(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    display_order INTEGER,
    start_date TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    UNIQUE(classroom_id, assignment_id)
);

-- Indexes for new columns and tables
CREATE INDEX IF NOT EXISTS idx_classrooms_class_code ON classrooms(class_code) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_classroom_students_removed ON classroom_students(student_id) WHERE removed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_classroom_assignments_classroom_id ON classroom_assignments(classroom_id);
CREATE INDEX IF NOT EXISTS idx_classroom_assignments_assignment_id ON classroom_assignments(assignment_id);

-- Enable RLS on classroom_assignments if not already enabled
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'classroom_assignments' 
        AND rowsecurity = true
    ) THEN
        ALTER TABLE classroom_assignments ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

-- Create policies for classroom_assignments
DO $$
BEGIN
    -- Teachers can manage assignments in their classrooms
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'classroom_assignments' 
        AND policyname = 'teacher_manage_assignments_policy'
    ) THEN
        CREATE POLICY teacher_manage_assignments_policy ON classroom_assignments
            FOR ALL
            USING (
                EXISTS (
                    SELECT 1 FROM classrooms c
                    WHERE c.id = classroom_assignments.classroom_id
                    AND c.teacher_id = current_setting('app.current_user_id')::UUID
                )
            );
    END IF;

    -- Students can view assignments in their classrooms
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'classroom_assignments' 
        AND policyname = 'student_view_assignments_policy'
    ) THEN
        CREATE POLICY student_view_assignments_policy ON classroom_assignments
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM classroom_students cs
                    WHERE cs.classroom_id = classroom_assignments.classroom_id
                    AND cs.student_id = current_setting('app.current_user_id')::UUID
                    AND (cs.removed_at IS NULL OR cs.status = 'active')
                )
            );
    END IF;
END $$;