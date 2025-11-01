"""add headset and session tables

Revision ID: f9a3b2c1d8e7
Revises: 0bd27f43a475
Create Date: 2025-11-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP

# revision identifiers, used by Alembic.
revision: str = 'f9a3b2c1d8e7'
down_revision: Union[str, None] = '0bd27f43a475'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create headset_devices, game_sessions, and headset_game_records tables."""

    # Create headset_devices table
    op.create_table(
        'headset_devices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), comment='主键'),
        sa.Column('device_id', sa.String(100), unique=True, nullable=False, comment='设备唯一ID'),
        sa.Column('site_id', UUID(as_uuid=True), sa.ForeignKey('operation_sites.id'), nullable=False, comment='所属运营点ID'),
        sa.Column('device_name', sa.String(200), nullable=True, comment='设备名称'),
        sa.Column('status', sa.String(20), server_default='active', nullable=False, comment='设备状态: active/inactive'),
        sa.Column('first_used_at', TIMESTAMP(timezone=True), nullable=True, comment='首次使用时间'),
        sa.Column('last_used_at', TIMESTAMP(timezone=True), nullable=True, comment='最后使用时间'),
        sa.Column('created_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='更新时间'),
        comment='头显设备表'
    )

    # Create indexes for headset_devices
    op.create_index('idx_headset_devices_site', 'headset_devices', ['site_id'])
    op.create_index('idx_headset_devices_device_id', 'headset_devices', ['device_id'])

    # Create game_sessions table
    op.create_table(
        'game_sessions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), comment='主键'),
        sa.Column('usage_record_id', UUID(as_uuid=True), sa.ForeignKey('game_usage_records.id'), nullable=False, comment='关联的使用记录ID'),
        sa.Column('start_time', TIMESTAMP(timezone=True), nullable=True, comment='游戏开始时间'),
        sa.Column('end_time', TIMESTAMP(timezone=True), nullable=True, comment='游戏结束时间'),
        sa.Column('process_info', sa.Text(), nullable=True, comment='游戏过程信息'),
        sa.Column('created_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='更新时间'),
        comment='游戏局信息表'
    )

    # Create index for game_sessions
    op.create_index('idx_game_sessions_usage', 'game_sessions', ['usage_record_id'])

    # Create headset_game_records table
    op.create_table(
        'headset_game_records',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'), comment='主键'),
        sa.Column('game_session_id', UUID(as_uuid=True), sa.ForeignKey('game_sessions.id', ondelete='CASCADE'), nullable=False, comment='关联的游戏局ID'),
        sa.Column('headset_device_id', UUID(as_uuid=True), sa.ForeignKey('headset_devices.id'), nullable=False, comment='关联的头显设备ID'),
        sa.Column('start_time', TIMESTAMP(timezone=True), nullable=True, comment='设备开始时间'),
        sa.Column('end_time', TIMESTAMP(timezone=True), nullable=True, comment='设备结束时间'),
        sa.Column('process_info', sa.Text(), nullable=True, comment='设备过程信息'),
        sa.Column('created_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False, comment='更新时间'),
        comment='头显设备游戏记录表'
    )

    # Create indexes for headset_game_records
    op.create_index('idx_headset_game_records_session', 'headset_game_records', ['game_session_id'])
    op.create_index('idx_headset_game_records_device', 'headset_game_records', ['headset_device_id'])


def downgrade() -> None:
    """Drop headset_game_records, game_sessions, and headset_devices tables."""

    # Drop tables in reverse order
    op.drop_table('headset_game_records')
    op.drop_table('game_sessions')
    op.drop_table('headset_devices')
