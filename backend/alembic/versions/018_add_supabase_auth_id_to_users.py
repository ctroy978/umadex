"""Add supabase_auth_id to users table

Revision ID: 018_add_supabase_auth_id
Revises: 017_add_teacher_bypass_codes
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '018_add_supabase_auth_id'
down_revision = '017_add_teacher_bypass_codes'
branch_labels = None
depends_on = None


def upgrade():
    # Add supabase_auth_id column to users table
    op.add_column('users', sa.Column('supabase_auth_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Create index for faster lookups
    op.create_index('ix_users_supabase_auth_id', 'users', ['supabase_auth_id'], unique=True)


def downgrade():
    # Drop index
    op.drop_index('ix_users_supabase_auth_id', table_name='users')
    
    # Drop column
    op.drop_column('users', 'supabase_auth_id')