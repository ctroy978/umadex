-- Migration: Add Classroom Test Scheduling System
-- This migration implements comprehensive time-based access controls for all UMA tests at the classroom level
-- Teachers can configure test availability windows that apply to every test in their classroom

-- Main schedule table for classroom-wide test scheduling
CREATE TABLE classroom_test_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    created_by_teacher_id UUID NOT NULL REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    timezone VARCHAR(50) NOT NULL DEFAULT 'America/New_York',
    grace_period_minutes INTEGER DEFAULT 30 CHECK (grace_period_minutes >= 0 AND grace_period_minutes <= 120),
    schedule_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(classroom_id)
);

-- Emergency override codes for test access outside scheduled windows
CREATE TABLE classroom_test_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    classroom_id UUID NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    teacher_id UUID NOT NULL REFERENCES users(id),
    override_code VARCHAR(8) NOT NULL UNIQUE,
    reason TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    max_uses INTEGER DEFAULT 1 CHECK (max_uses > 0),
    current_uses INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMPTZ,
    CONSTRAINT valid_usage CHECK (current_uses <= max_uses)
);

-- Track override code usage
CREATE TABLE test_override_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    override_id UUID NOT NULL REFERENCES classroom_test_overrides(id) ON DELETE CASCADE,
    student_id UUID NOT NULL REFERENCES users(id),
    test_attempt_id UUID NOT NULL REFERENCES student_test_attempts(id),
    used_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(override_id, student_id, test_attempt_id)
);

-- Add scheduling fields to student_test_attempts
ALTER TABLE student_test_attempts 
ADD COLUMN started_within_schedule BOOLEAN DEFAULT true,
ADD COLUMN override_code_used UUID REFERENCES classroom_test_overrides(id),
ADD COLUMN grace_period_end TIMESTAMPTZ,
ADD COLUMN schedule_violation_reason TEXT;

-- Add scheduling fields to assignment_tests
ALTER TABLE assignment_tests
ADD COLUMN respect_classroom_schedule BOOLEAN DEFAULT true,
ADD COLUMN schedule_override_level VARCHAR(20) DEFAULT 'strict' CHECK (schedule_override_level IN ('strict', 'lenient', 'disabled'));

-- Create indexes for performance
CREATE INDEX idx_classroom_test_schedules_classroom ON classroom_test_schedules(classroom_id);
CREATE INDEX idx_classroom_test_schedules_active ON classroom_test_schedules(is_active) WHERE is_active = true;
CREATE INDEX idx_classroom_test_overrides_classroom ON classroom_test_overrides(classroom_id);
CREATE INDEX idx_classroom_test_overrides_code ON classroom_test_overrides(override_code);
CREATE INDEX idx_classroom_test_overrides_expires ON classroom_test_overrides(expires_at);
CREATE INDEX idx_test_override_usage_override ON test_override_usage(override_id);
CREATE INDEX idx_test_override_usage_student ON test_override_usage(student_id);

-- Add RLS policies
ALTER TABLE classroom_test_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE classroom_test_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_override_usage ENABLE ROW LEVEL SECURITY;

-- Teachers can manage schedules for their classrooms
CREATE POLICY "Teachers manage classroom schedules" ON classroom_test_schedules
    FOR ALL -- TO authenticated (removed - not using role-based access)
    USING (
        classroom_id IN (
            SELECT id FROM classrooms WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Teachers can manage override codes for their classrooms
CREATE POLICY "Teachers manage override codes" ON classroom_test_overrides
    FOR ALL -- TO authenticated (removed - not using role-based access)
    USING (
        teacher_id = current_setting('app.current_user_id', true)::uuid AND
        classroom_id IN (
            SELECT id FROM classrooms WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Students can view schedules for their enrolled classrooms
CREATE POLICY "Students view classroom schedules" ON classroom_test_schedules
    FOR SELECT -- TO authenticated (removed - not using role-based access)
    USING (
        classroom_id IN (
            SELECT classroom_id FROM classroom_students 
            WHERE student_id = current_setting('app.current_user_id', true)::uuid AND is_active = true
        )
    );

-- Students can use override codes
CREATE POLICY "Students use override codes" ON classroom_test_overrides
    FOR SELECT -- TO authenticated (removed - not using role-based access)
    USING (
        classroom_id IN (
            SELECT classroom_id FROM classroom_students 
            WHERE student_id = current_setting('app.current_user_id', true)::uuid AND status = 'active'
        )
    );

-- Track override usage
CREATE POLICY "Track override usage" ON test_override_usage
    FOR INSERT -- TO authenticated (removed - not using role-based access)
    WITH CHECK (student_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY "View override usage" ON test_override_usage
    FOR SELECT -- TO authenticated (removed - not using role-based access)
    USING (
        student_id = current_setting('app.current_user_id', true)::uuid OR
        override_id IN (
            SELECT id FROM classroom_test_overrides WHERE teacher_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_classroom_test_schedules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_classroom_test_schedules_timestamp
    BEFORE UPDATE ON classroom_test_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_classroom_test_schedules_updated_at();

-- Function to check if testing is allowed for a classroom at current time
CREATE OR REPLACE FUNCTION is_testing_allowed(
    p_classroom_id UUID,
    p_check_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
)
RETURNS TABLE (
    allowed BOOLEAN,
    next_window TIMESTAMPTZ,
    current_window_end TIMESTAMPTZ,
    schedule_active BOOLEAN
) AS $$
DECLARE
    v_schedule RECORD;
    v_timezone TEXT;
    v_local_time TIME;
    v_local_dow INTEGER;
    v_window JSONB;
    v_window_start TIME;
    v_window_end TIME;
    v_allowed BOOLEAN := false;
    v_current_end TIMESTAMPTZ;
    v_next_start TIMESTAMPTZ;
BEGIN
    -- Get schedule for classroom
    SELECT * INTO v_schedule
    FROM classroom_test_schedules
    WHERE classroom_id = p_classroom_id AND is_active = true;
    
    -- If no active schedule, testing is always allowed
    IF NOT FOUND THEN
        RETURN QUERY SELECT true, NULL::TIMESTAMPTZ, NULL::TIMESTAMPTZ, false;
        RETURN;
    END IF;
    
    -- Get timezone and convert to local time
    v_timezone := v_schedule.timezone;
    v_local_time := (p_check_time AT TIME ZONE v_timezone)::TIME;
    v_local_dow := EXTRACT(DOW FROM (p_check_time AT TIME ZONE v_timezone))::INTEGER;
    
    -- Check each window in schedule
    FOR v_window IN SELECT * FROM jsonb_array_elements(v_schedule.schedule_data->'windows')
    LOOP
        -- Check if current day is in window days
        IF v_window->'days' ? (CASE v_local_dow
            WHEN 0 THEN 'sunday'
            WHEN 1 THEN 'monday'
            WHEN 2 THEN 'tuesday'
            WHEN 3 THEN 'wednesday'
            WHEN 4 THEN 'thursday'
            WHEN 5 THEN 'friday'
            WHEN 6 THEN 'saturday'
        END) THEN
            v_window_start := (v_window->>'start_time')::TIME;
            v_window_end := (v_window->>'end_time')::TIME;
            
            -- Check if current time is within window
            IF v_local_time >= v_window_start AND v_local_time <= v_window_end THEN
                v_allowed := true;
                v_current_end := (p_check_time::DATE + v_window_end) AT TIME ZONE v_timezone;
                EXIT;
            END IF;
        END IF;
    END LOOP;
    
    -- Calculate next window if not currently allowed
    IF NOT v_allowed THEN
        -- This would require more complex logic to find the next available window
        -- For now, return NULL
        v_next_start := NULL;
    END IF;
    
    RETURN QUERY SELECT v_allowed, v_next_start, v_current_end, true;
END;
$$ LANGUAGE plpgsql;

-- Function to generate unique override code
CREATE OR REPLACE FUNCTION generate_override_code()
RETURNS VARCHAR(8) AS $$
DECLARE
    v_code VARCHAR(8);
    v_exists BOOLEAN;
BEGIN
    LOOP
        -- Generate 8-character alphanumeric code
        v_code := upper(substring(md5(random()::text || clock_timestamp()::text) for 8));
        
        -- Check if code already exists
        SELECT EXISTS(SELECT 1 FROM classroom_test_overrides WHERE override_code = v_code) INTO v_exists;
        
        EXIT WHEN NOT v_exists;
    END LOOP;
    
    RETURN v_code;
END;
$$ LANGUAGE plpgsql;