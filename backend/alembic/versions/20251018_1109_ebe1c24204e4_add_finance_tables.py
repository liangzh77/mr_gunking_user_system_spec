"""add_finance_tables

Revision ID: ebe1c24204e4
Revises: 002_add_site_description
Create Date: 2025-10-18 11:09:54.002155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = 'ebe1c24204e4'
down_revision: Union[str, None] = '002_add_site_description'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create finance_accounts and finance_operation_logs tables for US6 财务后台功能."""

    # Create finance_accounts table
    op.create_table(
        'finance_accounts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, comment='财务账号ID'),
        sa.Column('username', sa.String(64), nullable=False, unique=True, comment='用户名'),
        sa.Column('password_hash', sa.String(255), nullable=False, comment='密码hash'),
        sa.Column('full_name', sa.String(128), nullable=False, comment='真实姓名'),
        sa.Column('phone', sa.String(32), nullable=False, comment='联系电话'),
        sa.Column('email', sa.String(128), nullable=False, comment='邮箱地址'),
        sa.Column('role', sa.String(32), nullable=False, server_default='specialist', comment='角色: specialist/manager/auditor'),
        sa.Column('permissions', JSONB, nullable=False, server_default='{}', comment='权限配置(specialist角色使用)'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true', comment='是否激活'),
        sa.Column('last_login_at', TIMESTAMP(timezone=True), nullable=True, comment='最后登录时间'),
        sa.Column('last_login_ip', sa.String(64), nullable=True, comment='最后登录IP'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', TIMESTAMP(timezone=True), nullable=True, onupdate=sa.func.now(), comment='更新时间'),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('admin_accounts.id', ondelete='SET NULL'), nullable=True, comment='创建人(管理员ID)'),
        comment='财务账号表'
    )

    # Create indexes for finance_accounts
    op.create_index('ix_finance_accounts_username', 'finance_accounts', ['username'])
    op.create_index('ix_finance_accounts_email', 'finance_accounts', ['email'])
    op.create_index('ix_finance_accounts_role', 'finance_accounts', ['role'])
    op.create_index('ix_finance_accounts_is_active', 'finance_accounts', ['is_active'])

    # Create finance_operation_logs table (partition table design with composite PK)
    op.create_table(
        'finance_operation_logs',
        sa.Column('id', UUID(as_uuid=True), nullable=False, comment='操作记录ID'),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, comment='操作时间(分区键)'),
        sa.Column('finance_account_id', UUID(as_uuid=True), sa.ForeignKey('finance_accounts.id', ondelete='RESTRICT'), nullable=False, comment='财务人员ID'),
        sa.Column('operation_type', sa.String(64), nullable=False, comment='操作类型: refund_approve/refund_reject/invoice_approve/invoice_reject/report_generate/view_api_key'),
        sa.Column('target_resource_id', sa.String(255), nullable=True, comment='目标资源ID(退款ID/发票ID等)'),
        sa.Column('operation_details', JSONB, nullable=False, server_default='{}', comment='操作详情(JSON格式)'),
        sa.Column('ip_address', sa.String(64), nullable=False, comment='操作IP地址'),
        sa.Column('user_agent', sa.Text, nullable=True, comment='用户代理'),
        sa.PrimaryKeyConstraint('id', 'created_at', name='pk_finance_operation_logs'),
        comment='财务操作记录表(分区表,按月分区)'
    )

    # Create indexes for finance_operation_logs
    op.create_index('ix_finance_operation_logs_finance_account_id', 'finance_operation_logs', ['finance_account_id'])
    op.create_index('ix_finance_operation_logs_operation_type', 'finance_operation_logs', ['operation_type'])
    op.create_index('ix_finance_operation_logs_created_at', 'finance_operation_logs', ['created_at'])
    op.create_index('ix_finance_operation_logs_target_resource_id', 'finance_operation_logs', ['target_resource_id'])

    # Add FK constraints to existing tables for finance review tracking
    # Note: These columns should already exist from initial migration, just adding FK constraints
    op.create_foreign_key(
        'fk_refund_requests_reviewed_by',
        'refund_requests', 'finance_accounts',
        ['reviewed_by'], ['id'],
        ondelete='SET NULL'
    )

    op.create_foreign_key(
        'fk_invoice_records_reviewed_by',
        'invoice_records', 'finance_accounts',
        ['reviewed_by'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Remove finance tables and FK constraints."""

    # Drop FK constraints first
    op.drop_constraint('fk_invoice_records_reviewed_by', 'invoice_records', type_='foreignkey')
    op.drop_constraint('fk_refund_requests_reviewed_by', 'refund_requests', type_='foreignkey')

    # Drop finance_operation_logs table
    op.drop_index('ix_finance_operation_logs_target_resource_id', table_name='finance_operation_logs')
    op.drop_index('ix_finance_operation_logs_created_at', table_name='finance_operation_logs')
    op.drop_index('ix_finance_operation_logs_operation_type', table_name='finance_operation_logs')
    op.drop_index('ix_finance_operation_logs_finance_account_id', table_name='finance_operation_logs')
    op.drop_table('finance_operation_logs')

    # Drop finance_accounts table
    op.drop_index('ix_finance_accounts_is_active', table_name='finance_accounts')
    op.drop_index('ix_finance_accounts_role', table_name='finance_accounts')
    op.drop_index('ix_finance_accounts_email', table_name='finance_accounts')
    op.drop_index('ix_finance_accounts_username', table_name='finance_accounts')
    op.drop_table('finance_accounts')
