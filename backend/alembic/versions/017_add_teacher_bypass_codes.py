"""add teacher bypass codes table

Revision ID: 017
Revises: 016
Create Date: 2025-07-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # Create teacher_bypass_codes table
    op.create_table('teacher_bypass_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('teacher_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('context_type', sa.String(length=50), nullable=True, server_default='test'),
        sa.Column('context_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('bypass_code', sa.String(length=8), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient queries
    op.create_index('idx_teacher_bypass_codes_teacher_id', 'teacher_bypass_codes', ['teacher_id'], unique=False)
    op.create_index('idx_teacher_bypass_codes_student_id', 'teacher_bypass_codes', ['student_id'], unique=False)
    op.create_index('idx_teacher_bypass_codes_bypass_code', 'teacher_bypass_codes', ['bypass_code'], unique=False)
    op.create_index('idx_teacher_bypass_codes_expires_at', 'teacher_bypass_codes', ['expires_at'], unique=False)
    op.create_index('idx_teacher_bypass_codes_used_at', 'teacher_bypass_codes', ['used_at'], unique=False)
    
    # Add table comment
    op.execute("COMMENT ON TABLE teacher_bypass_codes IS 'Stores temporary bypass codes that teachers can generate for specific contexts (tests, assignments, etc.)'")


def downgrade():
    # Drop indexes
    op.drop_index('idx_teacher_bypass_codes_used_at', table_name='teacher_bypass_codes')
    op.drop_index('idx_teacher_bypass_codes_expires_at', table_name='teacher_bypass_codes')
    op.drop_index('idx_teacher_bypass_codes_bypass_code', table_name='teacher_bypass_codes')
    op.drop_index('idx_teacher_bypass_codes_student_id', table_name='teacher_bypass_codes')
    op.drop_index('idx_teacher_bypass_codes_teacher_id', table_name='teacher_bypass_codes')
    
    # Drop table
    op.drop_table('teacher_bypass_codes')