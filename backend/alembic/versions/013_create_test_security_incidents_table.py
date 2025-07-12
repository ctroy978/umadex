"""create test security incidents table

Revision ID: 013
Revises: 012
Create Date: 2025-07-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    # Create test_security_incidents table if it doesn't exist
    op.create_table('test_security_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_attempt_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('incident_type', sa.String(length=50), nullable=False),
        sa.Column('incident_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('resulted_in_lock', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['test_attempt_id'], ['student_test_attempts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on test_attempt_id for performance
    op.create_index(op.f('ix_test_security_incidents_test_attempt_id'), 'test_security_incidents', ['test_attempt_id'], unique=False)
    
    # Create index on student_id for performance
    op.create_index(op.f('ix_test_security_incidents_student_id'), 'test_security_incidents', ['student_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_test_security_incidents_student_id'), table_name='test_security_incidents')
    op.drop_index(op.f('ix_test_security_incidents_test_attempt_id'), table_name='test_security_incidents')
    
    # Drop table
    op.drop_table('test_security_incidents')