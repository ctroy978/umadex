"""add schedule tracking to test attempts

Revision ID: 012
Revises: 011
Create Date: 2025-07-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    # Add started_within_schedule column to student_test_attempts
    op.add_column('student_test_attempts',
        sa.Column('started_within_schedule', sa.Boolean(), nullable=True, server_default='true')
    )
    
    # Add override_code_used column to student_test_attempts
    op.add_column('student_test_attempts',
        sa.Column('override_code_used', postgresql.UUID(as_uuid=True), nullable=True)
    )
    
    # Note: Foreign key constraint to test_override_codes table removed 
    # as that table doesn't exist yet


def downgrade():
    # Remove columns
    op.drop_column('student_test_attempts', 'override_code_used')
    op.drop_column('student_test_attempts', 'started_within_schedule')