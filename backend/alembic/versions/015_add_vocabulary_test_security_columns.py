"""add vocabulary test security columns

Revision ID: 015
Revises: 014
Create Date: 2025-07-30

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
    # Add security columns to vocabulary_test_attempts table
    op.add_column('vocabulary_test_attempts', 
        sa.Column('security_violations', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column('vocabulary_test_attempts', 
        sa.Column('is_locked', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('vocabulary_test_attempts', 
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('vocabulary_test_attempts', 
        sa.Column('locked_reason', sa.Text(), nullable=True))
    
    # Create vocabulary_test_security_incidents table
    op.create_table('vocabulary_test_security_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_attempt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('incident_type', sa.String(length=50), nullable=False),
        sa.Column('incident_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('resulted_in_lock', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['test_attempt_id'], ['vocabulary_test_attempts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_vocabulary_test_security_incidents_test_attempt_id'), 
                    'vocabulary_test_security_incidents', ['test_attempt_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_vocabulary_test_security_incidents_test_attempt_id'), 
                  table_name='vocabulary_test_security_incidents')
    
    # Drop table
    op.drop_table('vocabulary_test_security_incidents')
    
    # Remove columns from vocabulary_test_attempts
    op.drop_column('vocabulary_test_attempts', 'locked_reason')
    op.drop_column('vocabulary_test_attempts', 'locked_at')
    op.drop_column('vocabulary_test_attempts', 'is_locked')
    op.drop_column('vocabulary_test_attempts', 'security_violations')