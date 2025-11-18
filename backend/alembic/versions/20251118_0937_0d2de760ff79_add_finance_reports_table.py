"""add_finance_reports_table

Revision ID: 0d2de760ff79
Revises: ad756a9bce16
Create Date: 2025-11-18 09:37:00.701184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = '0d2de760ff79'
down_revision: Union[str, None] = 'ad756a9bce16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建财务报表表
    op.create_table(
        'finance_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', sa.String(64), nullable=False, unique=True, comment='报表编号(rpt_YYYYMMDD_XXXXXX)'),
        sa.Column('report_type', sa.String(32), nullable=False, comment='报表类型: daily/weekly/monthly/custom'),

        # 报表周期
        sa.Column('start_date', sa.TIMESTAMP(timezone=True), nullable=False, comment='报表开始日期'),
        sa.Column('end_date', sa.TIMESTAMP(timezone=True), nullable=False, comment='报表结束日期'),
        sa.Column('period', sa.String(128), nullable=False, comment='报表周期描述'),

        # 报表数据
        sa.Column('total_recharge', sa.Numeric(15, 2), nullable=False, server_default='0', comment='总充值金额'),
        sa.Column('total_consumption', sa.Numeric(15, 2), nullable=False, server_default='0', comment='总消费金额'),
        sa.Column('total_refund', sa.Numeric(15, 2), nullable=False, server_default='0', comment='总退款金额'),
        sa.Column('net_income', sa.Numeric(15, 2), nullable=False, server_default='0', comment='净收入'),

        # 统计数据
        sa.Column('total_transactions', sa.Integer, nullable=False, server_default='0', comment='总交易笔数'),
        sa.Column('total_operators', sa.Integer, nullable=False, server_default='0', comment='涉及运营商数量'),
        sa.Column('active_operators', sa.Integer, nullable=False, server_default='0', comment='活跃运营商数量'),

        # 详细数据(JSON)
        sa.Column('daily_breakdown', JSON, nullable=True, comment='每日明细数据'),
        sa.Column('top_customers', JSON, nullable=True, comment='Top客户数据'),
        sa.Column('statistics_data', JSON, nullable=True, comment='其他统计数据'),

        # 导出格式和文件
        sa.Column('export_format', sa.String(16), nullable=False, server_default='pdf', comment='导出格式: pdf/excel/csv'),
        sa.Column('file_path', sa.String(512), nullable=True, comment='文件存储路径'),
        sa.Column('file_size', sa.Integer, nullable=True, comment='文件大小(字节)'),

        # 生成状态
        sa.Column('status', sa.String(32), nullable=False, server_default='generating', comment='生成状态: generating/completed/failed'),
        sa.Column('error_message', sa.Text, nullable=True, comment='错误信息'),

        # 生成者信息
        sa.Column('generated_by', UUID(as_uuid=True), sa.ForeignKey('finance_accounts.id', ondelete='SET NULL'), nullable=True, comment='生成者ID'),

        # 时间戳
        sa.Column('generated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='生成时间'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='更新时间'),
    )

    # 创建索引
    op.create_index('ix_finance_reports_report_id', 'finance_reports', ['report_id'])
    op.create_index('ix_finance_reports_report_type', 'finance_reports', ['report_type'])
    op.create_index('ix_finance_reports_status', 'finance_reports', ['status'])
    op.create_index('ix_finance_reports_generated_by', 'finance_reports', ['generated_by'])
    op.create_index('ix_finance_reports_created_at', 'finance_reports', ['created_at'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_finance_reports_created_at', 'finance_reports')
    op.drop_index('ix_finance_reports_generated_by', 'finance_reports')
    op.drop_index('ix_finance_reports_status', 'finance_reports')
    op.drop_index('ix_finance_reports_report_type', 'finance_reports')
    op.drop_index('ix_finance_reports_report_id', 'finance_reports')

    # 删除表
    op.drop_table('finance_reports')
