"""Fix assignment_images file_url nullable constraint

Revision ID: 015
Revises: 014
Create Date: 2025-01-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # Make file_url nullable
    op.alter_column('assignment_images', 'file_url',
                    existing_type=sa.String(length=1000),
                    nullable=True)
    
    # Fix column length mismatch between display_url and thumbnail_url
    op.alter_column('assignment_images', 'display_url',
                    existing_type=sa.String(length=500),
                    type_=sa.String(length=1000),
                    existing_nullable=False)
    
    op.alter_column('assignment_images', 'thumbnail_url',
                    existing_type=sa.String(length=500),
                    type_=sa.String(length=1000),
                    existing_nullable=False)


def downgrade():
    # Revert column length changes
    op.alter_column('assignment_images', 'thumbnail_url',
                    existing_type=sa.String(length=1000),
                    type_=sa.String(length=500),
                    existing_nullable=False)
    
    op.alter_column('assignment_images', 'display_url',
                    existing_type=sa.String(length=1000),
                    type_=sa.String(length=500),
                    existing_nullable=False)
    
    # Make file_url NOT NULL again (this might fail if there are NULL values)
    op.alter_column('assignment_images', 'file_url',
                    existing_type=sa.String(length=1000),
                    nullable=False)