-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Classrooms table
CREATE TABLE IF NOT EXISTS classrooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    teacher_id UUID NOT NULL REFERENCES users(id),
    class_code VARCHAR(8) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Students in classrooms
CREATE TABLE IF NOT EXISTS classroom_students (
    classroom_id UUID REFERENCES classrooms(id),
    student_id UUID REFERENCES users(id),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    removed_at TIMESTAMP WITH TIME ZONE,
    removed_by UUID REFERENCES users(id),
    PRIMARY KEY (classroom_id, student_id)
);

-- Assignments in classrooms  
CREATE TABLE IF NOT EXISTS classroom_assignments (
    classroom_id UUID REFERENCES classrooms(id),
    assignment_id UUID REFERENCES reading_assignments(id),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    display_order INTEGER,
    start_date TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (classroom_id, assignment_id)
);

-- Indexes for performance
CREATE INDEX idx_classrooms_teacher_id ON classrooms(teacher_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_classrooms_class_code ON classrooms(class_code) WHERE deleted_at IS NULL;
CREATE INDEX idx_classroom_students_student_id ON classroom_students(student_id) WHERE removed_at IS NULL;
CREATE INDEX idx_classroom_students_classroom_id ON classroom_students(classroom_id) WHERE removed_at IS NULL;
CREATE INDEX idx_classroom_assignments_classroom_id ON classroom_assignments(classroom_id);
CREATE INDEX idx_classroom_assignments_assignment_id ON classroom_assignments(assignment_id);

-- Row Level Security (RLS) policies
ALTER TABLE classrooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_assignments ENABLE ROW LEVEL SECURITY;

-- Teachers can view and manage their own classrooms
CREATE POLICY teacher_classrooms_policy ON classrooms
    FOR ALL 
    USING (teacher_id = current_setting('app.current_user_id')::UUID);

-- Students can view classrooms they're enrolled in
CREATE POLICY student_view_classrooms_policy ON classrooms
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM classroom_students cs
            WHERE cs.classroom_id = classrooms.id
            AND cs.student_id = current_setting('app.current_user_id')::UUID
            AND cs.removed_at IS NULL
        )
    );

-- Teachers can manage students in their classrooms
CREATE POLICY teacher_manage_students_policy ON classroom_students
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM classrooms c
            WHERE c.id = classroom_students.classroom_id
            AND c.teacher_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Students can view their own enrollment records
CREATE POLICY student_view_enrollment_policy ON classroom_students
    FOR SELECT
    USING (student_id = current_setting('app.current_user_id')::UUID);

-- Teachers can manage assignments in their classrooms
CREATE POLICY teacher_manage_assignments_policy ON classroom_assignments
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM classrooms c
            WHERE c.id = classroom_assignments.classroom_id
            AND c.teacher_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Students can view assignments in their classrooms
CREATE POLICY student_view_assignments_policy ON classroom_assignments
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM classroom_students cs
            WHERE cs.classroom_id = classroom_assignments.classroom_id
            AND cs.student_id = current_setting('app.current_user_id')::UUID
            AND cs.removed_at IS NULL
        )
    );