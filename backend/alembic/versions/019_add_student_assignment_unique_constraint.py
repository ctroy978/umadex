"""add student assignment unique constraint

Revision ID: 019
Create Date: 2025-07-29

"""

# This migration adds a unique constraint to prevent duplicate student_assignments

def upgrade():
    """
    Run this SQL manually:
    
    ALTER TABLE student_assignments 
    ADD CONSTRAINT _student_assignment_uc 
    UNIQUE (student_id, assignment_id, classroom_assignment_id);
    """
    pass

def downgrade():
    """
    Run this SQL manually:
    
    ALTER TABLE student_assignments 
    DROP CONSTRAINT IF EXISTS _student_assignment_uc;
    """
    pass