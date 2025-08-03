"""Add storage_path column to assignment_images table

Revision ID: 020
Revises: 019
Create Date: 2025-08-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '020'
down_revision = '019'
branch_labels = None
depends_on = None


def upgrade():
    # Add storage_path column to assignment_images table
    op.add_column('assignment_images', 
                  sa.Column('storage_path', sa.Text(), nullable=True))


def downgrade():
    # Remove storage_path column
    op.drop_column('assignment_images', 'storage_path')