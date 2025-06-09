-- COMPREHENSIVE USER DELETION AUDIT FOR "herb coop"
-- This script checks all tables that could contain references to the deleted user
-- Run these queries to verify complete deletion and identify any orphaned records

-- ============================================================================
-- STEP 1: Check if user exists in main users table
-- ============================================================================

-- Check for any users with name "herb coop" (active or soft-deleted)
SELECT 
    id, email, first_name, last_name, username, role, is_admin,
    created_at, updated_at, deleted_at, deleted_by, deletion_reason
FROM users 
WHERE 
    LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
    OR LOWER(TRIM(email)) LIKE '%herb%coop%'
    OR LOWER(TRIM(username)) LIKE '%herb%coop%';

-- ============================================================================
-- STEP 2: Check user deletion audit logs
-- ============================================================================

-- Check user deletions log for herb coop
SELECT 
    id, user_id, user_email, user_name, user_role, was_admin,
    deletion_type, deletion_reason, deleted_by,
    affected_classrooms, affected_assignments, affected_students,
    created_at
FROM user_deletions 
WHERE 
    LOWER(TRIM(user_name)) = 'herb coop'
    OR LOWER(TRIM(user_email)) LIKE '%herb%coop%';

-- Check admin actions related to herb coop
SELECT 
    id, admin_id, action_type, target_id, target_type,
    action_data, created_at
FROM admin_actions 
WHERE 
    action_data::text ILIKE '%herb%coop%'
    OR target_id::text IN (
        SELECT id::text FROM users 
        WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
    );

-- ============================================================================
-- STEP 3: Check authentication-related tables
-- ============================================================================

-- Check user sessions (should auto-cascade delete)
SELECT COUNT(*) as session_count, 'user_sessions' as table_name
FROM user_sessions us 
WHERE us.user_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check refresh tokens (should auto-cascade delete)
SELECT COUNT(*) as token_count, 'refresh_tokens' as table_name
FROM refresh_tokens rt 
WHERE rt.user_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check OTP requests (no foreign key constraint - potential orphan)
SELECT COUNT(*) as otp_count, 'otp_requests' as table_name
FROM otp_requests 
WHERE LOWER(TRIM(email)) LIKE '%herb%coop%';

-- ============================================================================
-- STEP 4: Check classroom-related tables
-- ============================================================================

-- Check classrooms owned by herb coop (teacher)
SELECT 
    c.id, c.name, c.teacher_id, c.class_code, c.created_at, c.deleted_at,
    'teacher_owned_classrooms' as relationship_type
FROM classrooms c
WHERE c.teacher_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check classroom student enrollments
SELECT 
    cs.classroom_id, cs.student_id, cs.joined_at, cs.removed_at, cs.removed_by,
    'student_enrollments' as relationship_type
FROM classroom_students cs
WHERE cs.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check if herb coop removed other students (removed_by reference)
SELECT 
    cs.classroom_id, cs.student_id, cs.removed_by, cs.removed_at,
    'removed_by_herb' as relationship_type
FROM classroom_students cs
WHERE cs.removed_by::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- ============================================================================
-- STEP 5: Check assignment-related tables
-- ============================================================================

-- Check reading assignments created by herb coop
SELECT 
    ra.id, ra.teacher_id, ra.assignment_title, ra.work_title, 
    ra.status, ra.created_at, ra.deleted_at,
    'reading_assignments' as table_name
FROM reading_assignments ra
WHERE ra.teacher_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check vocabulary lists created by herb coop
SELECT 
    vl.id, vl.teacher_id, vl.title, vl.status, vl.created_at, vl.deleted_at,
    'vocabulary_lists' as table_name
FROM vocabulary_lists vl
WHERE vl.teacher_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check student assignments for herb coop
SELECT 
    sa.id, sa.student_id, sa.assignment_id, sa.assignment_type, 
    sa.status, sa.created_at,
    'student_assignments' as table_name
FROM student_assignments sa
WHERE sa.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- ============================================================================
-- STEP 6: Check test-related tables
-- ============================================================================

-- Check assignment tests approved by herb coop
SELECT 
    at.id, at.assignment_id, at.approved_by, at.status, at.created_at,
    'assignment_tests_approved_by' as relationship_type
FROM assignment_tests at
WHERE at.approved_by::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check test results for herb coop as student
SELECT 
    tr.id, tr.test_id, tr.student_id, tr.overall_score, tr.created_at,
    'test_results' as table_name
FROM test_results tr
WHERE tr.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check student test attempts
SELECT 
    sta.id, sta.student_id, sta.assignment_test_id, sta.status, 
    sta.started_at, sta.submitted_at,
    'student_test_attempts' as table_name
FROM student_test_attempts sta
WHERE sta.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check teacher bypass codes
SELECT 
    tbc.id, tbc.teacher_id, tbc.student_id, tbc.context_type, 
    tbc.used_at, tbc.created_at,
    'teacher_bypass_codes' as table_name
FROM teacher_bypass_codes tbc
WHERE 
    tbc.teacher_id::text IN (
        SELECT id::text FROM users 
        WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
    )
    OR tbc.student_id::text IN (
        SELECT id::text FROM users 
        WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
    );

-- Check test security incidents
SELECT 
    tsi.id, tsi.student_id, tsi.incident_type, tsi.created_at,
    'test_security_incidents' as table_name
FROM test_security_incidents tsi
WHERE tsi.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- ============================================================================
-- STEP 7: Check UMARead-specific tables
-- ============================================================================

-- Check UMARead student responses
SELECT 
    usr.id, usr.student_id, usr.assignment_id, usr.chunk_number, 
    usr.question_type, usr.created_at,
    'umaread_student_responses' as table_name
FROM umaread_student_responses usr
WHERE usr.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check UMARead chunk progress
SELECT 
    ucp.id, ucp.student_id, ucp.assignment_id, ucp.chunk_number, 
    ucp.completed_at, ucp.created_at,
    'umaread_chunk_progress' as table_name
FROM umaread_chunk_progress ucp
WHERE ucp.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check UMARead assignment progress
SELECT 
    uap.id, uap.student_id, uap.assignment_id, uap.current_chunk, 
    uap.started_at, uap.completed_at,
    'umaread_assignment_progress' as table_name
FROM umaread_assignment_progress uap
WHERE uap.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check reading student responses (legacy table)
SELECT 
    rsr.id, rsr.student_id, rsr.assignment_id, rsr.chunk_number, 
    rsr.question_type, rsr.occurred_at,
    'reading_student_responses' as table_name
FROM reading_student_responses rsr
WHERE rsr.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check answer evaluations
SELECT 
    ae.id, ae.student_id, ae.assignment_id, ae.chunk_number, 
    ae.question_type, ae.created_at,
    'answer_evaluations' as table_name
FROM answer_evaluations ae
WHERE ae.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check reading cache flush log (teacher actions)
SELECT 
    rcfl.id, rcfl.assignment_id, rcfl.teacher_id, rcfl.reason, 
    rcfl.questions_flushed, rcfl.created_at,
    'reading_cache_flush_log' as table_name
FROM reading_cache_flush_log rcfl
WHERE rcfl.teacher_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- ============================================================================
-- STEP 8: Check scheduling and events tables
-- ============================================================================

-- Check student events
SELECT 
    se.id, se.student_id, se.classroom_id, se.event_type, 
    se.event_data, se.created_at,
    'student_events' as table_name
FROM student_events se
WHERE se.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check classroom test schedules (created by teacher)
SELECT 
    cts.id, cts.classroom_id, cts.created_by_teacher_id, 
    cts.is_active, cts.created_at,
    'classroom_test_schedules' as table_name
FROM classroom_test_schedules cts
WHERE cts.created_by_teacher_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check classroom test overrides
SELECT 
    cto.id, cto.classroom_id, cto.teacher_id, cto.override_code, 
    cto.reason, cto.created_at,
    'classroom_test_overrides' as table_name
FROM classroom_test_overrides cto
WHERE cto.teacher_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check test override usage
SELECT 
    tou.id, tou.override_id, tou.student_id, tou.test_attempt_id, tou.used_at,
    'test_override_usage' as table_name
FROM test_override_usage tou
WHERE tou.student_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- ============================================================================
-- STEP 9: Check role change audit logs
-- ============================================================================

-- Check role changes for herb coop
SELECT 
    rc.id, rc.user_id, rc.from_role, rc.to_role, 
    rc.changed_by, rc.change_reason, rc.created_at,
    'role_changes_target' as relationship_type
FROM role_changes rc
WHERE rc.user_id::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- Check role changes made by herb coop
SELECT 
    rc.id, rc.user_id, rc.from_role, rc.to_role, 
    rc.changed_by, rc.change_reason, rc.created_at,
    'role_changes_made_by' as relationship_type
FROM role_changes rc
WHERE rc.changed_by::text IN (
    SELECT id::text FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
);

-- ============================================================================
-- STEP 10: Summary query - Count all references
-- ============================================================================

-- Summary of all potential orphaned records
WITH herb_user_ids AS (
    SELECT id::text as user_id 
    FROM users 
    WHERE LOWER(TRIM(first_name || ' ' || last_name)) = 'herb coop'
)
SELECT 
    'user_sessions' as table_name,
    COUNT(*) as orphaned_records
FROM user_sessions us, herb_user_ids hui
WHERE us.user_id::text = hui.user_id

UNION ALL

SELECT 
    'refresh_tokens' as table_name,
    COUNT(*) as orphaned_records
FROM refresh_tokens rt, herb_user_ids hui
WHERE rt.user_id::text = hui.user_id

UNION ALL

SELECT 
    'classrooms' as table_name,
    COUNT(*) as orphaned_records
FROM classrooms c, herb_user_ids hui
WHERE c.teacher_id::text = hui.user_id

UNION ALL

SELECT 
    'classroom_students' as table_name,
    COUNT(*) as orphaned_records
FROM classroom_students cs, herb_user_ids hui
WHERE cs.student_id::text = hui.user_id

UNION ALL

SELECT 
    'reading_assignments' as table_name,
    COUNT(*) as orphaned_records
FROM reading_assignments ra, herb_user_ids hui
WHERE ra.teacher_id::text = hui.user_id

UNION ALL

SELECT 
    'vocabulary_lists' as table_name,
    COUNT(*) as orphaned_records
FROM vocabulary_lists vl, herb_user_ids hui
WHERE vl.teacher_id::text = hui.user_id

UNION ALL

SELECT 
    'student_assignments' as table_name,
    COUNT(*) as orphaned_records
FROM student_assignments sa, herb_user_ids hui
WHERE sa.student_id::text = hui.user_id

UNION ALL

SELECT 
    'test_results' as table_name,
    COUNT(*) as orphaned_records
FROM test_results tr, herb_user_ids hui
WHERE tr.student_id::text = hui.user_id

UNION ALL

SELECT 
    'student_test_attempts' as table_name,
    COUNT(*) as orphaned_records
FROM student_test_attempts sta, herb_user_ids hui
WHERE sta.student_id::text = hui.user_id

UNION ALL

SELECT 
    'student_events' as table_name,
    COUNT(*) as orphaned_records
FROM student_events se, herb_user_ids hui
WHERE se.student_id::text = hui.user_id

ORDER BY table_name;

-- ============================================================================
-- STEP 11: Check for email/username patterns (in case of data inconsistency)
-- ============================================================================

-- Look for any variations in name formatting or partial matches
SELECT 
    id, email, first_name, last_name, username, role, 
    created_at, deleted_at,
    'potential_matches' as match_type
FROM users 
WHERE 
    LOWER(first_name) LIKE '%herb%' 
    OR LOWER(last_name) LIKE '%coop%'
    OR LOWER(email) LIKE '%herb%'
    OR LOWER(email) LIKE '%coop%'
    OR LOWER(username) LIKE '%herb%'
    OR LOWER(username) LIKE '%coop%';