"""fix vocabulary puzzle type constraint

Revision ID: 021_fix_vocabulary_puzzle_type_constraint
Revises: 020_add_storage_path_to_assignment_images
Create Date: 2025-08-04 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021_fix_vocabulary_puzzle_type_constraint'
down_revision = '020_add_storage_path_to_assignment_images'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing constraint
    op.execute("""
        ALTER TABLE vocabulary_puzzle_games 
        DROP CONSTRAINT IF EXISTS vocabulary_puzzle_games_puzzle_type_check;
    """)
    
    # Add the updated constraint that includes 'fill_blank'
    op.execute("""
        ALTER TABLE vocabulary_puzzle_games 
        ADD CONSTRAINT vocabulary_puzzle_games_puzzle_type_check 
        CHECK (puzzle_type IN ('scrambled', 'crossword_clue', 'word_match', 'fill_blank'));
    """)


def downgrade():
    # Drop the updated constraint
    op.execute("""
        ALTER TABLE vocabulary_puzzle_games 
        DROP CONSTRAINT IF EXISTS vocabulary_puzzle_games_puzzle_type_check;
    """)
    
    # Add back the original constraint without 'fill_blank'
    op.execute("""
        ALTER TABLE vocabulary_puzzle_games 
        ADD CONSTRAINT vocabulary_puzzle_games_puzzle_type_check 
        CHECK (puzzle_type IN ('scrambled', 'crossword_clue', 'word_match'));
    """)