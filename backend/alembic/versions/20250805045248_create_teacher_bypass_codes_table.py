"""create teacher bypass codes table

Revision ID: 20250805045248
Revises: 
Create Date: 2025-08-05 04:52:48

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250805045248'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # NOTE: This migration has already been applied to Supabase
    # This file exists for documentation purposes only
    # The actual migration was applied using mcp__supabase__apply_migration
    
    op.create_table('teacher_bypass_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('teacher_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('context_type', sa.String(50), server_default='test'),
        sa.Column('context_id', postgresql.UUID(as_uuid=True)),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.Column('bypass_code', sa.String(8), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )
    
    # Create indexes
    op.create_index('idx_teacher_bypass_codes_teacher_id', 'teacher_bypass_codes', ['teacher_id'])
    op.create_index('idx_teacher_bypass_codes_student_id', 'teacher_bypass_codes', ['student_id'])
    op.create_index('idx_teacher_bypass_codes_bypass_code', 'teacher_bypass_codes', ['bypass_code'])
    op.create_index('idx_teacher_bypass_codes_expires_at', 'teacher_bypass_codes', ['expires_at'])


def downgrade():
    op.drop_index('idx_teacher_bypass_codes_expires_at', 'teacher_bypass_codes')
    op.drop_index('idx_teacher_bypass_codes_bypass_code', 'teacher_bypass_codes')
    op.drop_index('idx_teacher_bypass_codes_student_id', 'teacher_bypass_codes')
    op.drop_index('idx_teacher_bypass_codes_teacher_id', 'teacher_bypass_codes')
    op.drop_table('teacher_bypass_codes')