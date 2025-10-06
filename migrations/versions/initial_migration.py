"""
Initial migration for KYC Verification Platform

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('email', sa.String, unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('api_key', sa.String(64), unique=True, index=True, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Create verifications table
    op.create_table(
        'verifications',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('session_id', sa.String(36), unique=True, index=True, nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('id_document_path', sa.String(500), nullable=True),
        sa.Column('selfie_video_path', sa.String(500), nullable=True),
        sa.Column('processed_images_path', postgresql.JSONB, nullable=True),
        sa.Column('document_type', sa.String(50), nullable=True),
        sa.Column('document_valid', sa.Boolean, default=False),
        sa.Column('extracted_data', postgresql.JSONB, nullable=True),
        sa.Column('document_confidence', sa.Float, nullable=True),
        sa.Column('face_detected', sa.Boolean, default=False),
        sa.Column('face_embedding', sa.Text, nullable=True),
        sa.Column('face_match_score', sa.Float, nullable=True),
        sa.Column('face_match_confidence', sa.Float, nullable=True),
        sa.Column('liveness_score', sa.Float, nullable=True),
        sa.Column('liveness_passed', sa.Boolean, default=False),
        sa.Column('liveness_method', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('decision', sa.String(20), nullable=True),
        sa.Column('decision_reason', sa.Text, nullable=True),
        sa.Column('processing_time', sa.Float, nullable=True),
        sa.Column('reviewer_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_notes', sa.Text, nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('client_ip', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime, default=sa.text('now()'), onupdate=sa.text('now()'))
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        sa.Column('verification_id', sa.Integer, sa.ForeignKey('verifications.id'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(100), nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime, default=sa.text('now()'))
    )

    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_api_key', 'users', ['api_key'])
    op.create_index('ix_verifications_session_id', 'verifications', ['session_id'])
    op.create_index('ix_verifications_user_id', 'verifications', ['user_id'])
    op.create_index('ix_verifications_status', 'verifications', ['status'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_verification_id', 'audit_logs', ['verification_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_verification_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_verifications_status', table_name='verifications')
    op.drop_index('ix_verifications_user_id', table_name='verifications')
    op.drop_index('ix_verifications_session_id', table_name='verifications')
    op.drop_index('ix_users_api_key', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('verifications')
    op.drop_table('users')