"""
Debug script to understand why UMAWrite assignments aren't showing in gradebook
"""

# The UMAWrite query from teacher_reports.py joins these tables:
# StudentWritingSubmission -> StudentAssignment -> ClassroomAssignment -> Classroom

# To debug, we need to check:
# 1. Are there any WritingAssignment records?
# 2. Are there any ClassroomAssignment records with assignment_type='writing'?
# 3. Are there any StudentAssignment records for those classroom assignments?
# 4. Are there any StudentWritingSubmission records with is_final_submission=True?

# The query structure:
"""
write_query = select(
    StudentWritingSubmission,
    User,
    StudentAssignment,
    ClassroomAssignment,
    WritingAssignment,
    Classroom
).join(
    User, StudentWritingSubmission.student_id == User.id
).join(
    StudentAssignment, StudentWritingSubmission.student_assignment_id == StudentAssignment.id
).join(
    ClassroomAssignment, StudentAssignment.classroom_assignment_id == ClassroomAssignment.id
).join(
    WritingAssignment, StudentWritingSubmission.writing_assignment_id == WritingAssignment.id
).join(
    Classroom, ClassroomAssignment.classroom_id == Classroom.id
).where(
    and_(
        Classroom.id.in_(classroom_ids),
        Classroom.teacher_id == teacher.id,
        Classroom.deleted_at.is_(None),
        ClassroomAssignment.assignment_type == 'writing',
        User.deleted_at.is_(None),
        StudentWritingSubmission.is_final_submission == True  # Only include final submissions
    )
)
"""

# Potential issues:
# 1. No WritingAssignment records created
# 2. WritingAssignments not assigned to classrooms (no ClassroomAssignment with assignment_type='writing')
# 3. Students haven't started the assignments (no StudentAssignment records)
# 4. Students haven't submitted final submissions (no StudentWritingSubmission with is_final_submission=True)
# 5. The joins are failing due to missing relationships

print("To debug UMAWrite gradebook issues, check the following in the database:")
print("1. SELECT COUNT(*) FROM writing_assignments;")
print("2. SELECT COUNT(*) FROM classroom_assignments WHERE assignment_type = 'writing';")
print("3. SELECT COUNT(*) FROM student_assignments WHERE assignment_type = 'writing';")
print("4. SELECT COUNT(*) FROM student_writing_submissions WHERE is_final_submission = true;")
print("\nIf any of these counts are 0, that's where the issue lies.")