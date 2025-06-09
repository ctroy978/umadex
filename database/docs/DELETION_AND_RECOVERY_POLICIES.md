# UMADex Database Deletion and Recovery Policies

## Overview
This document establishes consistent policies for data deletion and recovery across the UMADex platform. These policies ensure data integrity, audit compliance, and proper handling of user data throughout the application lifecycle.

## Deletion Types

### 1. Soft Delete (Default for all user accounts)
- **What**: Records marked as deleted but preserved in database
- **When**: Default deletion method for all users
- **Why**: Audit compliance, data recovery, referential integrity
- **Implementation**: 
  - `deleted_at` timestamp set
  - `deleted_by` admin ID recorded
  - `deletion_reason` documented

### 2. Hard Delete (Students only, admin-initiated)
- **What**: Permanent removal from database with CASCADE cleanup
- **When**: Only for students after impact analysis and confirmation
- **Why**: Data privacy compliance, storage optimization
- **Restrictions**: 
  - ❌ Teachers cannot be hard deleted (content ownership)
  - ❌ Admins cannot be hard deleted (audit trail)
  - ✅ Students only, with multi-step confirmation

### 3. Automatic Cleanup (System-initiated)
- **What**: CASCADE DELETE triggers for related data
- **When**: When parent record is hard deleted
- **Why**: Prevent orphaned records and data inconsistency

## User Role Deletion Policies

### Students
```
Soft Delete: ✅ Default (reversible)
Hard Delete: ✅ With confirmation (irreversible)
CASCADE DELETE: ✅ All student-specific data
```

**Student data affected by CASCADE DELETE:**
- `classroom_students` - Classroom enrollments
- `student_assignments` - Assignment progress
- `student_test_attempts` - Test history
- `umaread_student_responses` - Reading responses
- `umaread_chunk_progress` - Reading progress
- `umaread_assignment_progress` - Assignment progress
- `student_events` - Activity logs
- `vocabulary_student_progress` - Vocabulary progress
- `answer_evaluations` - Answer feedback
- `otp_requests` - Authentication requests

### Teachers
```
Soft Delete: ✅ Default (reversible)
Hard Delete: ❌ Prohibited (content preservation)
CASCADE DELETE: ❌ Content preserved with SET NULL
```

**Teacher data handling with SET NULL:**
- `classrooms.teacher_id` → NULL (classroom preserved)
- `reading_assignments.teacher_id` → NULL (assignments preserved)
- `vocabulary_lists.teacher_id` → NULL (vocabulary preserved)

**Rationale**: Teachers create educational content that should persist even if the teacher leaves. This preserves institutional knowledge and prevents data loss.

### Admins
```
Soft Delete: ✅ Default (reversible)
Hard Delete: ❌ Prohibited (audit trail preservation)
CASCADE DELETE: ❌ Audit trail preserved with SET NULL
```

**Admin data handling with SET NULL:**
- `users.deleted_by` → NULL (deletion record preserved)
- `admin_actions.admin_id` → NULL (audit trail preserved)
- `role_changes.admin_id` → NULL (promotion history preserved)
- `user_deletions.admin_id` → NULL (deletion history preserved)

## Database Constraints Summary

### CASCADE DELETE Constraints
```sql
-- Student data - automatically deleted
classroom_students.student_id → users.id ON DELETE CASCADE
student_assignments.student_id → users.id ON DELETE CASCADE
student_test_attempts.student_id → users.id ON DELETE CASCADE
umaread_student_responses.student_id → users.id ON DELETE CASCADE
umaread_chunk_progress.student_id → users.id ON DELETE CASCADE
umaread_assignment_progress.student_id → users.id ON DELETE CASCADE
student_events.student_id → users.id ON DELETE CASCADE
vocabulary_student_progress.student_id → users.id ON DELETE CASCADE
answer_evaluations.student_id → users.id ON DELETE CASCADE
otp_requests.user_id → users.id ON DELETE CASCADE
```

### SET NULL Constraints
```sql
-- Teacher content - preserved
classrooms.teacher_id → users.id ON DELETE SET NULL
reading_assignments.teacher_id → users.id ON DELETE SET NULL
vocabulary_lists.teacher_id → users.id ON DELETE SET NULL

-- Admin audit trail - preserved
users.deleted_by → users.id ON DELETE SET NULL
admin_actions.admin_id → users.id ON DELETE SET NULL
role_changes.admin_id → users.id ON DELETE SET NULL
user_deletions.admin_id → users.id ON DELETE SET NULL
```

## Implementation Guidelines

### Adding New Tables
When creating new tables that reference users, follow these patterns:

#### For Student-Specific Data:
```sql
ALTER TABLE new_student_table
ADD CONSTRAINT new_student_table_student_id_fkey
FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE;
```

#### For Teacher-Created Content:
```sql
ALTER TABLE new_content_table
ADD CONSTRAINT new_content_table_teacher_id_fkey
FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE SET NULL;
```

#### For Admin Audit Data:
```sql
ALTER TABLE new_audit_table
ADD CONSTRAINT new_audit_table_admin_id_fkey
FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL;
```

### API Endpoint Requirements

#### Soft Delete Endpoints
```
DELETE /api/v1/admin/users/{id}/soft
- Available for all user types
- Requires admin privileges
- Records deletion reason
- Reversible via restore endpoint
```

#### Hard Delete Endpoints
```
DELETE /api/v1/admin/users/{id}/hard
- Students only
- Requires impact analysis
- Requires confirmation phrase
- Irreversible - triggers CASCADE DELETE
```

#### Restore Endpoints
```
POST /api/v1/admin/users/{id}/restore
- Soft deleted users only
- Clears deleted_at, deleted_by, deletion_reason
- Logs restoration action
```

## Data Recovery Procedures

### Soft Delete Recovery
1. **Immediate Recovery**: Use restore endpoint
2. **Database Recovery**: Update deleted_at to NULL
3. **Verification**: Confirm user can access account
4. **Audit**: Log restoration in admin_actions

### Hard Delete Recovery
❌ **Not possible** - data permanently removed
- Prevention: Always perform soft delete first
- Backup: Regular database backups are only recovery option
- Timeline: Must restore from backup before next backup cycle

## Security Considerations

### Access Control
- Only admins can delete users
- Hard delete requires elevated confirmation
- All deletions logged in audit trail
- Deletion impact analysis required

### Data Privacy
- Soft delete maintains data for operational needs
- Hard delete ensures complete removal for privacy compliance
- Anonymous data (SET NULL) preserves functionality without personal data

### Audit Requirements
- All deletions logged with timestamp, admin, and reason
- Audit trail preserved even if admin account deleted
- Impact analysis required before irreversible actions

## Testing Guidelines

### Unit Tests Required
```javascript
// Test CASCADE DELETE behavior
test('hard delete student removes all related data')
test('soft delete teacher preserves content with SET NULL')
test('admin deletion preserves audit trail')

// Test constraint enforcement
test('cannot hard delete teacher')
test('cannot hard delete admin')
test('soft delete is reversible')
```

### Integration Tests Required
```javascript
// Test full deletion workflows
test('complete student deletion process')
test('teacher soft delete workflow')
test('deletion impact analysis accuracy')
test('restore functionality')
```

## Migration Best Practices

### When Adding User References
1. **Identify the data type**: Student data, teacher content, or audit data
2. **Choose appropriate constraint**: CASCADE DELETE or SET NULL
3. **Add performance indexes**: On foreign key columns
4. **Update documentation**: Add to this policy document
5. **Test deletion behavior**: Verify constraints work as expected

### When Modifying Existing Tables
1. **Assess impact**: Check existing data relationships
2. **Plan migration**: Handle existing NULL values
3. **Backup data**: Before constraint changes
4. **Test thoroughly**: Verify no data loss
5. **Update policies**: Reflect changes in documentation

## Monitoring and Alerts

### Metrics to Track
- Soft deletion rate by user type
- Hard deletion requests and completions
- Orphaned record detection (should be zero)
- Restoration requests and success rate

### Alerts to Configure
- Hard delete attempts on teachers/admins
- Orphaned records detected
- Failed CASCADE DELETE operations
- Unusual deletion patterns

## Future Considerations

### Potential Enhancements
1. **Automated cleanup**: Scheduled removal of old soft-deleted records
2. **Data archival**: Move old deleted data to archive tables
3. **Enhanced audit**: More detailed deletion impact tracking
4. **User self-deletion**: Allow students to request account deletion

### Compliance Evolution
- **GDPR**: Right to be forgotten requirements
- **COPPA**: Student data protection requirements
- **Institutional**: School district data policies

---

## Document Maintenance
- **Last Updated**: June 9, 2025
- **Next Review**: When adding new user-referenced tables
- **Maintainers**: Database team, Admin system developers
- **Approval**: Technical lead, Security team

## Related Documentation
- `/database/docs/SCHEMA_DESIGN.md`
- `/database/docs/AUDIT_LOGGING.md`
- `/backend/docs/ADMIN_API.md`
- `/docs/SECURITY_POLICIES.md`