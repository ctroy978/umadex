"""add missing test columns

Revision ID: 011
Revises: 010
Create Date: 2025-01-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # Add evaluated_at column to student_test_attempts
    op.add_column('student_test_attempts',
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add grace_period_end column to student_test_attempts
    op.add_column('student_test_attempts',
        sa.Column('grace_period_end', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add schedule_violation_reason column to student_test_attempts
    op.add_column('student_test_attempts',
        sa.Column('schedule_violation_reason', sa.Text(), nullable=True)
    )
    
    # Add created_at column to student_test_attempts if it doesn't exist
    op.add_column('student_test_attempts',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)
    )
    
    # Add updated_at column to student_test_attempts if it doesn't exist
    op.add_column('student_test_attempts',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)
    )


def downgrade():
    # Remove columns
    op.drop_column('student_test_attempts', 'updated_at')
    op.drop_column('student_test_attempts', 'created_at')
    op.drop_column('student_test_attempts', 'schedule_violation_reason')
    op.drop_column('student_test_attempts', 'grace_period_end')
    op.drop_column('student_test_attempts', 'evaluated_at')