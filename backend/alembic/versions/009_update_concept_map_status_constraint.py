"""Update concept map status constraint

Revision ID: 009
Revises: 008
Create Date: 2025-06-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing constraint
    op.execute("""
        ALTER TABLE vocabulary_concept_map_attempts 
        DROP CONSTRAINT IF EXISTS check_concept_map_attempt_status;
    """)
    
    # Add the updated constraint with new status values
    op.execute("""
        ALTER TABLE vocabulary_concept_map_attempts 
        ADD CONSTRAINT check_concept_map_attempt_status 
        CHECK (status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined'));
    """)


def downgrade():
    # Drop the updated constraint
    op.execute("""
        ALTER TABLE vocabulary_concept_map_attempts 
        DROP CONSTRAINT IF EXISTS check_concept_map_attempt_status;
    """)
    
    # Restore the original constraint
    op.execute("""
        ALTER TABLE vocabulary_concept_map_attempts 
        ADD CONSTRAINT check_concept_map_attempt_status 
        CHECK (status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned'));
    """)