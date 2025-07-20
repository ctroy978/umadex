"""add text simplification cache table

Revision ID: 016
Revises: 015
Create Date: 2025-07-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    # Create text_simplification_cache table
    op.create_table('text_simplification_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('assignment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_number', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('original_grade_level', sa.String(length=20), nullable=True),
        sa.Column('target_grade_level', sa.Integer(), nullable=False),
        sa.Column('simplified_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['assignment_id'], ['reading_assignments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assignment_id', 'chunk_number', 'content_hash', 'target_grade_level', name='unique_simplification')
    )
    
    # Create indexes for efficient lookups
    op.create_index('idx_text_simplification_cache_lookup', 'text_simplification_cache', 
                    ['assignment_id', 'chunk_number', 'content_hash', 'target_grade_level'], unique=False)
    op.create_index('idx_text_simplification_cache_created', 'text_simplification_cache', 
                    ['created_at'], unique=False)
    
    # Add table comment
    op.execute("COMMENT ON TABLE text_simplification_cache IS 'Caches AI-simplified versions of reading chunks for the UMARead \"Crunch Text\" feature'")


def downgrade():
    # Drop indexes
    op.drop_index('idx_text_simplification_cache_created', table_name='text_simplification_cache')
    op.drop_index('idx_text_simplification_cache_lookup', table_name='text_simplification_cache')
    
    # Drop table
    op.drop_table('text_simplification_cache')