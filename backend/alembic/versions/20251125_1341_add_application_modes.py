"""add application modes

Revision ID: add_application_modes
Revises: 20251121_1600_add_payment_method_to_bank_transfer
Create Date: 2025-11-25 13:41:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'add_application_modes'
down_revision = '20251121_1600'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库：添加应用模式系统"""

    # 1. 创建 application_modes 表
    op.create_table(
        'application_modes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('application_id', UUID(as_uuid=True), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mode_name', sa.String(64), nullable=False, comment='模式名称，如"5分钟"'),
        sa.Column('price', sa.DECIMAL(10, 2), nullable=False, comment='模式价格'),
        sa.Column('description', sa.Text, nullable=True, comment='模式描述'),
        sa.Column('sort_order', sa.Integer, server_default='0', nullable=False, comment='排序顺序'),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False, comment='是否启用'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.CheckConstraint('price > 0', name='chk_mode_price_positive'),
        sa.UniqueConstraint('application_id', 'mode_name', name='uq_app_mode_name')
    )

    op.create_index('idx_app_mode_app_id', 'application_modes', ['application_id'])
    op.create_index('idx_app_mode_active', 'application_modes', ['is_active'])

    # 2. 为所有现有应用创建默认模式（基于 price_per_player）
    connection = op.get_bind()
    apps = connection.execute(
        sa.text("SELECT id, price_per_player FROM applications")
    ).fetchall()

    for app in apps:
        connection.execute(
            sa.text("""
                INSERT INTO application_modes
                (id, application_id, mode_name, price, description, sort_order, is_active)
                VALUES
                (gen_random_uuid(), :app_id, '标准模式', :price, '默认游戏模式', 0, true)
            """),
            {"app_id": str(app.id), "price": float(app.price_per_player)}
        )

    # 3. 修改 usage_records 表 - 添加模式相关字段
    op.add_column('usage_records',
        sa.Column('application_mode_id', UUID(as_uuid=True), nullable=True, comment='使用的模式ID'))
    op.add_column('usage_records',
        sa.Column('mode_name_snapshot', sa.String(64), nullable=True, comment='模式名称快照'))
    op.add_column('usage_records',
        sa.Column('price_snapshot', sa.DECIMAL(10, 2), nullable=True, comment='价格快照'))

    # 4. 创建授权模式关联表
    op.create_table(
        'operator_app_authorization_modes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('authorization_id', UUID(as_uuid=True),
                  sa.ForeignKey('operator_app_authorizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('application_mode_id', UUID(as_uuid=True),
                  sa.ForeignKey('application_modes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.UniqueConstraint('authorization_id', 'application_mode_id', name='uq_auth_mode')
    )

    op.create_index('idx_auth_mode_auth_id', 'operator_app_authorization_modes', ['authorization_id'])
    op.create_index('idx_auth_mode_mode_id', 'operator_app_authorization_modes', ['application_mode_id'])

    # 5. 为所有现有授权添加默认模式关联
    authorizations = connection.execute(
        sa.text("""
            SELECT oa.id as auth_id, am.id as mode_id
            FROM operator_app_authorizations oa
            JOIN application_modes am ON am.application_id = oa.application_id
            WHERE am.mode_name = '标准模式'
        """)
    ).fetchall()

    for auth in authorizations:
        connection.execute(
            sa.text("""
                INSERT INTO operator_app_authorization_modes
                (id, authorization_id, application_mode_id)
                VALUES (gen_random_uuid(), :auth_id, :mode_id)
            """),
            {"auth_id": str(auth.auth_id), "mode_id": str(auth.mode_id)}
        )

    # 6. 创建申请模式关联表
    op.create_table(
        'application_request_modes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_id', UUID(as_uuid=True),
                  sa.ForeignKey('application_requests.id', ondelete='CASCADE'), nullable=False),
        sa.Column('application_mode_id', UUID(as_uuid=True),
                  sa.ForeignKey('application_modes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.current_timestamp(), nullable=False),
        sa.UniqueConstraint('request_id', 'application_mode_id', name='uq_request_mode')
    )

    op.create_index('idx_req_mode_req_id', 'application_request_modes', ['request_id'])
    op.create_index('idx_req_mode_mode_id', 'application_request_modes', ['application_mode_id'])

    # 7. 为现有未审批的申请添加默认模式关联
    requests = connection.execute(
        sa.text("""
            SELECT ar.id as req_id, am.id as mode_id
            FROM application_requests ar
            JOIN application_modes am ON am.application_id = ar.application_id
            WHERE ar.status = 'pending' AND am.mode_name = '标准模式'
        """)
    ).fetchall()

    for req in requests:
        connection.execute(
            sa.text("""
                INSERT INTO application_request_modes
                (id, request_id, application_mode_id)
                VALUES (gen_random_uuid(), :req_id, :mode_id)
            """),
            {"req_id": str(req.req_id), "mode_id": str(req.mode_id)}
        )


def downgrade():
    """降级数据库：移除应用模式系统"""

    # 删除创建的表和字段
    op.drop_table('application_request_modes')
    op.drop_table('operator_app_authorization_modes')

    op.drop_column('usage_records', 'price_snapshot')
    op.drop_column('usage_records', 'mode_name_snapshot')
    op.drop_column('usage_records', 'application_mode_id')

    op.drop_table('application_modes')
