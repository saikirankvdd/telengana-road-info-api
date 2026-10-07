"""001_initial_production_schema

Revision ID: 001_initial_production
Revises: 
Create Date: 2026-10-05 03:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_production'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='READ_ONLY'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Canonical Tables (Projects, Roads, Tenders, Contractors, Authorities)
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.String(length=100), nullable=False),
        sa.Column('project_name', sa.Text(), nullable=False),
        sa.Column('normalized_project_name', sa.Text(), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('ulb_name', sa.String(length=100), nullable=True),
        sa.Column('work_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('cost_inr', sa.Float(), nullable=True),
        sa.Column('sanctioned_amount', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_project_id'), 'projects', ['project_id'], unique=True)

    # 3. Research Runs & Audit
    op.create_table(
        'research_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('query_project_name', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('searched_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('sources_checked', sa.Integer(), nullable=True),
        sa.Column('sources_accessed', sa.Integer(), nullable=True),
        sa.Column('fields_found', sa.Integer(), nullable=True),
        sa.Column('fields_verified', sa.Integer(), nullable=True),
        sa.Column('conflicts_found', sa.Integer(), nullable=True),
        sa.Column('result_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'project_research_sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('research_run_id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.Text(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('authority_level', sa.String(length=50), nullable=True),
        sa.Column('retrieval_status', sa.String(length=50), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('accessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'project_field_evidences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('research_run_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('extracted_value', sa.Text(), nullable=True),
        sa.Column('verification_status', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('evidence_text', sa.Text(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Entity Match Reviews & Controlled Merge Audits
    op.create_table(
        'research_merge_reviews',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('research_run_id', sa.Integer(), nullable=False),
        sa.Column('candidate_entity_type', sa.String(length=50), nullable=False),
        sa.Column('candidate_entity_id', sa.Integer(), nullable=True),
        sa.Column('match_status', sa.String(length=50), nullable=False),
        sa.Column('match_confidence', sa.Float(), nullable=True),
        sa.Column('matching_signals', sa.JSON(), nullable=True),
        sa.Column('negative_signals', sa.JSON(), nullable=True),
        sa.Column('field_comparison', sa.JSON(), nullable=True),
        sa.Column('field_decisions', sa.JSON(), nullable=True),
        sa.Column('review_status', sa.String(length=50), nullable=False),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['candidate_entity_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'research_merge_actions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=False),
        sa.Column('research_run_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('target_table', sa.String(length=100), nullable=False),
        sa.Column('target_record_id', sa.Integer(), nullable=False),
        sa.Column('previous_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('approved_by', sa.String(length=100), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['review_id'], ['research_merge_reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Data Quality & Quarantine Reports
    op.create_table(
        'research_quality_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('research_run_id', sa.Integer(), nullable=False),
        sa.Column('project_name', sa.Text(), nullable=False),
        sa.Column('overall_quality_score', sa.Float(), nullable=False),
        sa.Column('quality_class', sa.String(length=50), nullable=False),
        sa.Column('fields_checked', sa.Integer(), nullable=True),
        sa.Column('fields_valid', sa.Integer(), nullable=True),
        sa.Column('fields_suspicious', sa.Integer(), nullable=True),
        sa.Column('fields_invalid', sa.Integer(), nullable=True),
        sa.Column('fields_missing', sa.Integer(), nullable=True),
        sa.Column('fields_unsupported', sa.Integer(), nullable=True),
        sa.Column('cross_source_conflicts', sa.Integer(), nullable=True),
        sa.Column('duplicate_candidates_count', sa.Integer(), nullable=True),
        sa.Column('stale_fields_count', sa.Integer(), nullable=True),
        sa.Column('merge_eligible', sa.Boolean(), nullable=False),
        sa.Column('merge_blockers', sa.JSON(), nullable=True),
        sa.Column('is_quarantined', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['research_run_id'], ['research_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('research_quality_reports')
    op.drop_table('research_merge_actions')
    op.drop_table('research_merge_reviews')
    op.drop_table('project_field_evidences')
    op.drop_table('project_research_sources')
    op.drop_table('research_runs')
    op.drop_table('projects')
    op.drop_table('users')
