"""Add vocabulary fill-in-the-blank tables

Revision ID: 008_vocabulary_fill_in_blank
Revises: 007_add_vocabulary_practice_status
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_vocabulary_fill_in_blank'
down_revision = '007_add_vocabulary_practice_status'
branch_labels = None
depends_on = None


def upgrade():
    # Create vocabulary_fill_in_blank_sentences table
    op.create_table('vocabulary_fill_in_blank_sentences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vocabulary_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('word_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sentence_with_blank', sa.Text(), nullable=False),
        sa.Column('correct_answer', sa.String(100), nullable=False),
        sa.Column('sentence_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['vocabulary_list_id'], ['vocabulary_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['word_id'], ['vocabulary_words.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vocabulary_list_id', 'sentence_order', name='unique_sentence_order')
    )
    
    # Create vocabulary_fill_in_blank_responses table
    op.create_table('vocabulary_fill_in_blank_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vocabulary_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('practice_progress_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sentence_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_answer', sa.String(100), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False, default=1),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vocabulary_list_id'], ['vocabulary_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['practice_progress_id'], ['vocabulary_practice_progress.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sentence_id'], ['vocabulary_fill_in_blank_sentences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('practice_progress_id', 'sentence_id', 'attempt_number', 
                          name='unique_fill_in_blank_response_attempt')
    )
    
    # Create vocabulary_fill_in_blank_attempts table
    op.create_table('vocabulary_fill_in_blank_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vocabulary_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('practice_progress_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('total_sentences', sa.Integer(), nullable=False),
        sa.Column('sentences_completed', sa.Integer(), nullable=False, default=0),
        sa.Column('current_sentence_index', sa.Integer(), nullable=False, default=0),
        sa.Column('correct_answers', sa.Integer(), nullable=False, default=0),
        sa.Column('incorrect_answers', sa.Integer(), nullable=False, default=0),
        sa.Column('score_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('passing_score', sa.Integer(), nullable=False, default=70),
        sa.Column('sentence_order', postgresql.JSONB(), nullable=False, default=list),
        sa.Column('responses', postgresql.JSONB(), nullable=False, default=dict),
        sa.Column('status', sa.String(20), nullable=False, default='in_progress'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vocabulary_list_id'], ['vocabulary_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['practice_progress_id'], ['vocabulary_practice_progress.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'passed', 'failed', 'abandoned', 'pending_confirmation', 'declined')",
            name='check_fill_in_blank_attempt_status'
        )
    )
    
    # Create indexes
    op.create_index('idx_fill_in_blank_sentences_list_id', 'vocabulary_fill_in_blank_sentences', ['vocabulary_list_id'])
    op.create_index('idx_fill_in_blank_sentences_word_id', 'vocabulary_fill_in_blank_sentences', ['word_id'])
    op.create_index('idx_fill_in_blank_responses_student_id', 'vocabulary_fill_in_blank_responses', ['student_id'])
    op.create_index('idx_fill_in_blank_responses_progress_id', 'vocabulary_fill_in_blank_responses', ['practice_progress_id'])
    op.create_index('idx_fill_in_blank_attempts_student_id', 'vocabulary_fill_in_blank_attempts', ['student_id'])
    op.create_index('idx_fill_in_blank_attempts_progress_id', 'vocabulary_fill_in_blank_attempts', ['practice_progress_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_fill_in_blank_attempts_progress_id', table_name='vocabulary_fill_in_blank_attempts')
    op.drop_index('idx_fill_in_blank_attempts_student_id', table_name='vocabulary_fill_in_blank_attempts')
    op.drop_index('idx_fill_in_blank_responses_progress_id', table_name='vocabulary_fill_in_blank_responses')
    op.drop_index('idx_fill_in_blank_responses_student_id', table_name='vocabulary_fill_in_blank_responses')
    op.drop_index('idx_fill_in_blank_sentences_word_id', table_name='vocabulary_fill_in_blank_sentences')
    op.drop_index('idx_fill_in_blank_sentences_list_id', table_name='vocabulary_fill_in_blank_sentences')
    
    # Drop tables
    op.drop_table('vocabulary_fill_in_blank_attempts')
    op.drop_table('vocabulary_fill_in_blank_responses')
    op.drop_table('vocabulary_fill_in_blank_sentences')