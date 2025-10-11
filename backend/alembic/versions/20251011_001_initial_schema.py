"""Initial database schema - 16 tables for MR Game Ops System

Revision ID: 001_initial
Revises:
Create Date: 2025-10-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ========== 1. system_configs (系统配置表) ==========
    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('config_key', sa.String(length=128), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(length=32), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_editable', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key', name='uq_config_key'),
        sa.CheckConstraint("value_type IN ('string', 'integer', 'float', 'boolean', 'json')", name='chk_value_type')
    )
    op.create_index('idx_config_category', 'system_configs', ['category'])

    # ========== 2. admin_accounts (管理员账号) ==========
    op.create_table(
        'admin_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='operator'),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['admin_accounts.id'], name='fk_admin_creator', ondelete='SET NULL'),
        sa.CheckConstraint("role IN ('super_admin', 'admin', 'operator')", name='chk_admin_role')
    )
    op.create_index('uq_admin_username', 'admin_accounts', ['username'], unique=True, postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_admin_role', 'admin_accounts', ['role', 'is_active'])
    op.create_index('idx_admin_email', 'admin_accounts', ['email'])

    # ========== 3. finance_accounts (财务账号) ==========
    op.create_table(
        'finance_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='specialist'),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by'], ['admin_accounts.id'], name='fk_finance_creator', ondelete='SET NULL'),
        sa.CheckConstraint("role IN ('specialist', 'manager', 'auditor')", name='chk_finance_role')
    )
    op.create_index('uq_finance_username', 'finance_accounts', ['username'], unique=True, postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_finance_role', 'finance_accounts', ['role', 'is_active'])
    op.create_index('idx_finance_email', 'finance_accounts', ['email'])

    # ========== 4. operator_accounts (运营商账户) ==========
    op.create_table(
        'operator_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('api_key', sa.String(length=64), nullable=False),
        sa.Column('api_key_hash', sa.String(length=255), nullable=False),
        sa.Column('balance', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('customer_tier', sa.String(length=32), nullable=False, server_default='trial'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('locked_reason', sa.Text(), nullable=True),
        sa.Column('locked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_login_ip', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('balance >= 0', name='chk_balance_non_negative'),
        sa.CheckConstraint("customer_tier IN ('vip', 'standard', 'trial')", name='chk_customer_tier')
    )
    op.create_index('uq_operator_username', 'operator_accounts', ['username'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('uq_operator_api_key', 'operator_accounts', ['api_key'], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_operator_email', 'operator_accounts', ['email'])
    op.create_index('idx_operator_tier', 'operator_accounts', ['customer_tier', 'is_active'])
    op.create_index('idx_operator_balance', 'operator_accounts', ['balance'], postgresql_where=sa.text('balance < 100'))

    # ========== 5. operation_sites (运营点) ==========
    op.create_table(
        'operation_sites',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('contact_person', sa.String(length=64), nullable=True),
        sa.Column('contact_phone', sa.String(length=32), nullable=True),
        sa.Column('server_identifier', sa.String(length=128), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_site_operator', ondelete='RESTRICT')
    )
    op.create_index('idx_site_operator', 'operation_sites', ['operator_id', 'is_active'])
    op.create_index('idx_site_name', 'operation_sites', ['name'])
    op.create_index('idx_site_server', 'operation_sites', ['server_identifier'], postgresql_where=sa.text('server_identifier IS NOT NULL'))

    # ========== 6. applications (应用) ==========
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('app_code', sa.String(length=64), nullable=False),
        sa.Column('app_name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_per_player', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('min_players', sa.Integer(), nullable=False),
        sa.Column('max_players', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('app_code', name='uq_app_code'),
        sa.ForeignKeyConstraint(['created_by'], ['admin_accounts.id'], name='fk_app_creator', ondelete='SET NULL'),
        sa.CheckConstraint('price_per_player > 0', name='chk_price_positive'),
        sa.CheckConstraint('min_players >= 1 AND max_players >= min_players AND max_players <= 100', name='chk_players_range')
    )
    op.create_index('idx_app_name', 'applications', ['app_name'])
    op.create_index('idx_app_active', 'applications', ['is_active'])
    op.create_index('idx_app_price', 'applications', ['price_per_player'])

    # ========== 7. operator_app_authorizations (运营者应用授权) ==========
    op.create_table(
        'operator_app_authorizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('authorized_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('authorized_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('application_request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_auth_operator', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name='fk_auth_application', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['authorized_by'], ['admin_accounts.id'], name='fk_auth_admin', ondelete='SET NULL'),
        sa.CheckConstraint('expires_at IS NULL OR expires_at > authorized_at', name='chk_expiry_future')
    )
    op.create_index('uq_operator_app', 'operator_app_authorizations', ['operator_id', 'application_id'], unique=True, postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_auth_operator', 'operator_app_authorizations', ['operator_id', 'is_active'])
    op.create_index('idx_auth_application', 'operator_app_authorizations', ['application_id', 'is_active'])
    op.create_index('idx_auth_expiry', 'operator_app_authorizations', ['expires_at'], postgresql_where=sa.text('expires_at IS NOT NULL'))

    # ========== 8. application_authorization_requests (应用授权申请) ==========
    op.create_table(
        'application_authorization_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('requested_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reject_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_request_operator', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name='fk_request_application', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['admin_accounts.id'], name='fk_request_reviewer', ondelete='SET NULL'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='chk_request_status')
    )
    op.create_index('idx_request_operator', 'application_authorization_requests', ['operator_id', 'requested_at'])
    op.create_index('idx_request_status', 'application_authorization_requests', ['status', 'requested_at'])
    op.create_index('idx_request_application', 'application_authorization_requests', ['application_id'])

    # Add FK after table creation
    op.create_foreign_key('fk_auth_app_request', 'operator_app_authorizations', 'application_authorization_requests', ['application_request_id'], ['id'], ondelete='SET NULL')

    # ========== 9. usage_records (使用记录) ==========
    op.create_table(
        'usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('session_id', sa.String(length=128), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('player_count', sa.Integer(), nullable=False),
        sa.Column('price_per_player', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total_cost', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('authorization_token', sa.String(length=64), nullable=False),
        sa.Column('game_started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('game_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('game_ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('client_ip', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_session_id'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_usage_operator', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['site_id'], ['operation_sites.id'], name='fk_usage_site', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name='fk_usage_application', ondelete='RESTRICT'),
        sa.CheckConstraint('player_count > 0', name='chk_player_count_positive'),
        sa.CheckConstraint('total_cost = player_count * price_per_player', name='chk_total_cost'),
        sa.CheckConstraint('game_duration_minutes IS NULL OR game_duration_minutes > 0', name='chk_game_duration')
    )
    op.create_index('idx_usage_operator', 'usage_records', ['operator_id', sa.text('game_started_at DESC')])
    op.create_index('idx_usage_site', 'usage_records', ['site_id', sa.text('game_started_at DESC')])
    op.create_index('idx_usage_application', 'usage_records', ['application_id', sa.text('game_started_at DESC')])
    op.create_index('idx_usage_date', 'usage_records', ['game_started_at'])
    op.create_index('idx_usage_cost', 'usage_records', ['total_cost'])

    # ========== 10. transaction_records (交易记录) ==========
    op.create_table(
        'transaction_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_type', sa.String(length=32), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('balance_before', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('balance_after', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('related_usage_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('related_refund_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payment_channel', sa.String(length=32), nullable=True),
        sa.Column('payment_order_no', sa.String(length=128), nullable=True),
        sa.Column('payment_status', sa.String(length=32), nullable=True),
        sa.Column('payment_callback_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_trans_operator', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['related_usage_id'], ['usage_records.id'], name='fk_trans_usage', ondelete='SET NULL'),
        sa.CheckConstraint("transaction_type IN ('recharge', 'consumption', 'refund')", name='chk_trans_type'),
        sa.CheckConstraint("payment_channel IS NULL OR payment_channel IN ('wechat', 'alipay')", name='chk_payment_channel'),
        sa.CheckConstraint("payment_status IS NULL OR payment_status IN ('pending', 'success', 'failed')", name='chk_payment_status'),
        sa.CheckConstraint('balance_after = balance_before + amount', name='chk_balance_calc')
    )
    op.create_index('idx_trans_operator', 'transaction_records', ['operator_id', sa.text('created_at DESC')])
    op.create_index('idx_trans_type', 'transaction_records', ['transaction_type', sa.text('created_at DESC')])
    op.create_index('idx_trans_payment', 'transaction_records', ['payment_order_no'], postgresql_where=sa.text('payment_order_no IS NOT NULL'))
    op.create_index('idx_trans_date', 'transaction_records', ['created_at'])

    # ========== 11. invoice_records (发票记录) ==========
    op.create_table(
        'invoice_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_type', sa.String(length=32), nullable=False),
        sa.Column('invoice_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('invoice_title', sa.String(length=128), nullable=False),
        sa.Column('tax_id', sa.String(length=32), nullable=False),
        sa.Column('bank_name', sa.String(length=128), nullable=True),
        sa.Column('bank_account', sa.String(length=64), nullable=True),
        sa.Column('company_address', sa.Text(), nullable=True),
        sa.Column('company_phone', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('requested_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reject_reason', sa.Text(), nullable=True),
        sa.Column('invoice_number', sa.String(length=64), nullable=True),
        sa.Column('invoice_file_url', sa.Text(), nullable=True),
        sa.Column('issued_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_invoice_operator', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['finance_accounts.id'], name='fk_invoice_reviewer', ondelete='SET NULL'),
        sa.CheckConstraint("invoice_type IN ('vat_normal', 'vat_special')", name='chk_invoice_type'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'issued')", name='chk_invoice_status'),
        sa.CheckConstraint('invoice_amount > 0', name='chk_invoice_amount_positive')
    )
    op.create_index('idx_invoice_operator', 'invoice_records', ['operator_id', sa.text('requested_at DESC')])
    op.create_index('idx_invoice_status', 'invoice_records', ['status', sa.text('requested_at DESC')])
    op.create_index('idx_invoice_number', 'invoice_records', ['invoice_number'], postgresql_where=sa.text('invoice_number IS NOT NULL'))

    # ========== 12. refund_records (退款记录) ==========
    op.create_table(
        'refund_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('actual_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('refund_reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('requested_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reject_reason', sa.Text(), nullable=True),
        sa.Column('refund_channel', sa.String(length=32), nullable=True),
        sa.Column('refund_order_no', sa.String(length=128), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_refund_operator', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['finance_accounts.id'], name='fk_refund_reviewer', ondelete='SET NULL'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'completed')", name='chk_refund_status'),
        sa.CheckConstraint("refund_channel IS NULL OR refund_channel IN ('wechat', 'alipay', 'bank_transfer')", name='chk_refund_channel'),
        sa.CheckConstraint('requested_amount > 0 AND (actual_amount IS NULL OR actual_amount > 0)', name='chk_refund_amount_positive')
    )
    op.create_index('idx_refund_operator', 'refund_records', ['operator_id', sa.text('requested_at DESC')])
    op.create_index('idx_refund_status', 'refund_records', ['status', sa.text('requested_at DESC')])
    op.create_index('idx_refund_order', 'refund_records', ['refund_order_no'], postgresql_where=sa.text('refund_order_no IS NOT NULL'))

    # Add FK for transaction_records.related_refund_id (now refund_records exists)
    op.create_foreign_key('fk_trans_refund', 'transaction_records', 'refund_records', ['related_refund_id'], ['id'], ondelete='SET NULL')

    # ========== 13. message_notifications (消息通知) ==========
    op.create_table(
        'message_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('message_type', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=32), nullable=False, server_default='normal'),
        sa.Column('target_type', sa.String(length=32), nullable=False),
        sa.Column('target_filter', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('related_resource_type', sa.String(length=64), nullable=True),
        sa.Column('related_resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('sent_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['sent_by'], ['admin_accounts.id'], name='fk_message_sender', ondelete='SET NULL'),
        sa.CheckConstraint("message_type IN ('system_announcement', 'price_change', 'low_balance', 'authorization_expiry')", name='chk_message_type'),
        sa.CheckConstraint("priority IN ('high', 'normal', 'low')", name='chk_message_priority'),
        sa.CheckConstraint("target_type IN ('all_operators', 'specific_operators', 'operator_tier')", name='chk_target_type')
    )
    op.create_index('idx_message_type', 'message_notifications', ['message_type', sa.text('sent_at DESC')])
    op.create_index('idx_message_sent', 'message_notifications', [sa.text('sent_at DESC')])
    op.create_index('idx_message_priority', 'message_notifications', ['priority', sa.text('sent_at DESC')])
    op.create_index('idx_message_target', 'message_notifications', ['target_type'])

    # ========== 14. operator_message_reads (运营商消息阅读状态) ==========
    op.create_table(
        'operator_message_reads',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('operator_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operator_id', 'message_id', name='uq_operator_message'),
        sa.ForeignKeyConstraint(['operator_id'], ['operator_accounts.id'], name='fk_read_operator', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['message_notifications.id'], name='fk_read_message', ondelete='CASCADE')
    )
    op.create_index('idx_read_operator_unread', 'operator_message_reads', ['operator_id', 'is_read'], postgresql_where=sa.text('is_read = false'))
    op.create_index('idx_read_message', 'operator_message_reads', ['message_id'])

    # ========== 15. finance_operation_logs (财务操作记录) - PARTITIONED TABLE ==========
    op.execute("""
        CREATE TABLE finance_operation_logs (
            id UUID NOT NULL DEFAULT uuid_generate_v4(),
            finance_account_id UUID NOT NULL,
            operation_type VARCHAR(64) NOT NULL,
            target_resource_type VARCHAR(64),
            target_resource_id UUID,
            operation_details JSONB NOT NULL DEFAULT '{}',
            ip_address VARCHAR(64) NOT NULL,
            user_agent TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, created_at),
            CONSTRAINT fk_log_finance_account FOREIGN KEY (finance_account_id) REFERENCES finance_accounts(id) ON DELETE RESTRICT
        ) PARTITION BY RANGE (created_at)
    """)

    # Create first partition for current month
    op.execute("""
        CREATE TABLE finance_operation_logs_2025_10 PARTITION OF finance_operation_logs
        FOR VALUES FROM ('2025-10-01') TO ('2025-11-01')
    """)

    op.create_index('idx_finance_log_account', 'finance_operation_logs', ['finance_account_id', sa.text('created_at DESC')])
    op.create_index('idx_finance_log_type', 'finance_operation_logs', ['operation_type', sa.text('created_at DESC')])
    op.create_index('idx_finance_log_target', 'finance_operation_logs', ['target_resource_type', 'target_resource_id'])

    # ========== 16. api_key_usage_logs (API Key使用记录) - PARTITIONED TABLE ==========
    op.execute("""
        CREATE TABLE api_key_usage_logs (
            id UUID NOT NULL DEFAULT uuid_generate_v4(),
            api_key_hash VARCHAR(255) NOT NULL,
            operator_id UUID,
            site_id UUID,
            application_id UUID,
            request_result VARCHAR(32) NOT NULL,
            error_code VARCHAR(64),
            error_message TEXT,
            request_ip VARCHAR(64) NOT NULL,
            request_user_agent TEXT,
            request_payload JSONB,
            response_time_ms INTEGER,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, created_at),
            CONSTRAINT fk_api_log_operator FOREIGN KEY (operator_id) REFERENCES operator_accounts(id) ON DELETE SET NULL,
            CONSTRAINT fk_api_log_site FOREIGN KEY (site_id) REFERENCES operation_sites(id) ON DELETE SET NULL,
            CONSTRAINT fk_api_log_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL,
            CONSTRAINT chk_request_result CHECK (request_result IN ('success', 'auth_failed', 'insufficient_balance', 'app_unauthorized', 'invalid_player_count', 'rate_limit_exceeded', 'account_locked'))
        ) PARTITION BY RANGE (created_at)
    """)

    # Create first partition for current month
    op.execute("""
        CREATE TABLE api_key_usage_logs_2025_10 PARTITION OF api_key_usage_logs
        FOR VALUES FROM ('2025-10-01') TO ('2025-11-01')
    """)

    op.create_index('idx_api_log_operator', 'api_key_usage_logs', ['operator_id', sa.text('created_at DESC')])
    op.create_index('idx_api_log_result', 'api_key_usage_logs', ['request_result', sa.text('created_at DESC')])
    op.create_index('idx_api_log_ip', 'api_key_usage_logs', ['request_ip', sa.text('created_at DESC')])
    op.create_index('idx_api_log_hash', 'api_key_usage_logs', ['api_key_hash', sa.text('created_at DESC')])

    # Add FK constraint for system_configs.updated_by (now admin_accounts exists)
    op.create_foreign_key('fk_config_updater', 'system_configs', 'admin_accounts', ['updated_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # Drop tables in reverse order (considering FK dependencies)
    op.drop_table('api_key_usage_logs_2025_10')
    op.drop_table('api_key_usage_logs')
    op.drop_table('finance_operation_logs_2025_10')
    op.drop_table('finance_operation_logs')
    op.drop_table('operator_message_reads')
    op.drop_table('message_notifications')
    op.drop_table('refund_records')
    op.drop_table('invoice_records')
    op.drop_table('transaction_records')
    op.drop_table('usage_records')
    op.drop_table('application_authorization_requests')
    op.drop_table('operator_app_authorizations')
    op.drop_table('applications')
    op.drop_table('operation_sites')
    op.drop_table('operator_accounts')
    op.drop_table('finance_accounts')
    op.drop_table('admin_accounts')
    op.drop_table('system_configs')

    # Disable UUID extension
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
