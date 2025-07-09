"""add test question evaluation table

Revision ID: 010
Revises: 009
Create Date: 2025-01-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Create test_question_evaluations table
    op.create_table('test_question_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_attempt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('question_index', sa.Integer(), nullable=False),
        sa.Column('rubric_score', sa.Integer(), nullable=False),
        sa.Column('points_earned', sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column('max_points', sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column('scoring_rationale', sa.Text(), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('key_concepts_identified', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('misconceptions_detected', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evaluation_confidence', sa.DECIMAL(precision=3, scale=2), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['test_attempt_id'], ['student_test_attempts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('rubric_score >= 0 AND rubric_score <= 4', name='check_rubric_score_range'),
        sa.CheckConstraint('evaluation_confidence >= 0 AND evaluation_confidence <= 1', name='check_confidence_range'),
        sa.CheckConstraint('points_earned >= 0', name='check_points_earned_positive'),
        sa.CheckConstraint('max_points > 0', name='check_max_points_positive')
    )
    
    # Create index on test_attempt_id for faster lookups
    op.create_index('idx_test_question_evaluations_attempt_id', 'test_question_evaluations', ['test_attempt_id'])


def downgrade():
    # Drop index
    op.drop_index('idx_test_question_evaluations_attempt_id', table_name='test_question_evaluations')
    
    # Drop table
    op.drop_table('test_question_evaluations')