-- Create classrooms table
CREATE TABLE classrooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(255),
    grade_level VARCHAR(50),
    school_year VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create classroom_students junction table
CREATE TABLE classroom_students (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    UNIQUE(classroom_id, student_id)
);

-- Create UMA type enum
CREATE TYPE uma_type AS ENUM ('read', 'debate', 'vocab', 'write', 'lecture');

-- Create assignments table
CREATE TABLE assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    classroom_id UUID REFERENCES classrooms(id) ON DELETE CASCADE,
    uma_type uma_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content JSONB,
    due_date TIMESTAMP WITH TIME ZONE,
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_classrooms_teacher ON classrooms(teacher_id);
CREATE INDEX idx_classroom_students_classroom ON classroom_students(classroom_id);
CREATE INDEX idx_classroom_students_student ON classroom_students(student_id);
CREATE INDEX idx_assignments_teacher ON assignments(teacher_id);
CREATE INDEX idx_assignments_classroom ON assignments(classroom_id);
CREATE INDEX idx_assignments_uma_type ON assignments(uma_type);

-- Create updated_at trigger for classrooms
CREATE TRIGGER update_classrooms_updated_at
BEFORE UPDATE ON classrooms
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Create updated_at trigger for assignments
CREATE TRIGGER update_assignments_updated_at
BEFORE UPDATE ON assignments
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE classrooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_students ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;

-- RLS Policies for classrooms
-- Teachers can see and manage their own classrooms
CREATE POLICY classrooms_teacher_all ON classrooms
    FOR ALL
    USING (teacher_id = current_setting('app.current_user_id', true)::uuid OR 
           current_setting('app.is_admin', true)::boolean = true);

-- Students can see classrooms they're enrolled in
CREATE POLICY classrooms_student_select ON classrooms
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM classroom_students
            WHERE classroom_students.classroom_id = classrooms.id
            AND classroom_students.student_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- RLS Policies for classroom_students
-- Teachers can manage enrollments in their classrooms
CREATE POLICY classroom_students_teacher_all ON classroom_students
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM classrooms
            WHERE classrooms.id = classroom_students.classroom_id
            AND classrooms.teacher_id = current_setting('app.current_user_id', true)::uuid
        )
        OR current_setting('app.is_admin', true)::boolean = true
    );

-- Students can see their own enrollments
CREATE POLICY classroom_students_student_select ON classroom_students
    FOR SELECT
    USING (student_id = current_setting('app.current_user_id', true)::uuid);

-- RLS Policies for assignments
-- Teachers can manage their own assignments
CREATE POLICY assignments_teacher_all ON assignments
    FOR ALL
    USING (teacher_id = current_setting('app.current_user_id', true)::uuid OR 
           current_setting('app.is_admin', true)::boolean = true);

-- Students can see published assignments in their classrooms
CREATE POLICY assignments_student_select ON assignments
    FOR SELECT
    USING (
        is_published = true AND
        EXISTS (
            SELECT 1 FROM classroom_students cs
            JOIN classrooms c ON c.id = cs.classroom_id
            WHERE cs.student_id = current_setting('app.current_user_id', true)::uuid
            AND c.id = assignments.classroom_id
        )
    );