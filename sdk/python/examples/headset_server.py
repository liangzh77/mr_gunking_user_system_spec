#!/usr/bin/env python3
"""头显Server集成示例

这是一个模拟MR头显服务器的示例，展示如何在实际项目中集成MR游戏SDK。
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from mr_game_sdk import MRGameClient, MRGameAPIError, MRGameAuthError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GameSession:
    """游戏会话管理"""

    def __init__(self, session_id: str, app_id: int, player_count: int, auth_token: str):
        self.session_id = session_id
        self.app_id = app_id
        self.player_count = player_count
        self.auth_token = auth_token
        self.start_time = datetime.now()
        self.active = True
        self.current_players = player_count

    def get_duration(self) -> int:
        """获取会话持续时间(秒)"""
        return int((datetime.now() - self.start_time).total_seconds())

    def update_player_count(self, count: int):
        """更新玩家数量"""
        self.current_players = max(0, count)
        logger.info(f"会话 {self.session_id} 玩家数量更新为: {self.current_players}")


class HeadsetServer:
    """模拟头显服务器"""

    def __init__(self, api_key: str, api_secret: str, base_url: str = "http://localhost:8000"):
        self.client = MRGameClient(api_key, api_secret, base_url)
        self.active_sessions: Dict[str, GameSession] = {}
        self.running = True
        self.executor = ThreadPoolExecutor(max_workers=4)

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("头显服务器初始化完成")

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，正在关闭服务器...")
        self.running = False

    async def start_game_session(self, app_id: int, player_count: int,
                               device_id: str, location: Optional[str] = None) -> Optional[GameSession]:
        """启动游戏会话

        Args:
            app_id: 应用ID
            player_count: 玩家数量
            device_id: 设备ID
            location: 位置信息

        Returns:
            游戏会话对象，失败时返回None
        """
        session_id = f"{device_id}_{int(datetime.now().timestamp())}"

        try:
            logger.info(f"启动游戏会话: app_id={app_id}, players={player_count}")

            # 请求授权
            authorize_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.authorize_game,
                app_id,
                player_count,
                session_id,
                location,
                {
                    "device_id": device_id,
                    "location": location,
                    "server_version": "1.0.0"
                }
            )

            if not authorize_result.success:
                logger.error(f"游戏授权失败: {authorize_result.message}")
                return None

            # 创建会话对象
            session = GameSession(
                session_id=session_id,
                app_id=app_id,
                player_count=player_count,
                auth_token=authorize_result.auth_token or ""
            )

            self.active_sessions[session_id] = session
            logger.info(f"游戏会话启动成功: {session_id}")

            return session

        except Exception as e:
            logger.error(f"启动游戏会话失败: {e}")
            return None

    async def end_game_session(self, session_id: str) -> bool:
        """结束游戏会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功结束
        """
        if session_id not in self.active_sessions:
            logger.warning(f"会话不存在: {session_id}")
            return False

        session = self.active_sessions[session_id]

        try:
            logger.info(f"结束游戏会话: {session_id}")

            # 调用SDK结束会话
            end_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.client.end_game_session,
                session.app_id,
                session.session_id,
                session.current_players,
                None,
                {
                    "duration": session.get_duration(),
                    "final_players": session.current_players
                }
            )

            if end_result.success:
                logger.info(f"会话结束成功: {session_id}, 费用: ¥{end_result.total_cost}")
            else:
                logger.error(f"会话结束失败: {session_id}, 错误: {end_result.message}")

            # 清理会话
            del self.active_sessions[session_id]
            return end_result.success

        except Exception as e:
            logger.error(f"结束游戏会话失败: {e}")
            # 即使API调用失败，也要清理本地会话
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            return False

    def update_session_players(self, session_id: str, player_count: int):
        """更新会话玩家数量

        Args:
            session_id: 会话ID
            player_count: 新的玩家数量
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id].update_player_count(player_count)
        else:
            logger.warning(f"尝试更新不存在的会话: {session_id}")

    def get_active_sessions(self) -> Dict[str, GameSession]:
        """获取所有活跃会话"""
        return self.active_sessions.copy()

    def get_balance(self) -> Optional[float]:
        """获取账户余额"""
        try:
            balance_result = self.client.get_balance()
            if balance_result.success:
                return balance_result.balance
            else:
                logger.error(f"获取余额失败: {balance_result.message}")
                return None
        except Exception as e:
            logger.error(f"获取余额异常: {e}")
            return None

    async def check_sessions_health(self):
        """定期检查会话健康状态"""
        while self.running:
            try:
                # 检查超时会话（超过2小时自动结束）
                current_time = datetime.now()
                timeout_sessions = []

                for session_id, session in self.active_sessions.items():
                    duration = (current_time - session.start_time).total_seconds()
                    if duration > 7200:  # 2小时
                        timeout_sessions.append(session_id)

                # 结束超时会话
                for session_id in timeout_sessions:
                    logger.warning(f"会话超时，自动结束: {session_id}")
                    await self.end_game_session(session_id)

                # 每5分钟检查一次
                await asyncio.sleep(300)

            except Exception as e:
                logger.error(f"会话健康检查异常: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟再重试

    async def run_simulation(self):
        """运行模拟场景"""
        logger.info("开始模拟游戏场景...")

        # 模拟多个游戏会话
        scenarios = [
            {"app_id": 1, "players": 4, "device": "headset_001", "location": "beijing_store_01"},
            {"app_id": 2, "players": 2, "device": "headset_002", "location": "beijing_store_01"},
            {"app_id": 1, "players": 6, "device": "headset_003", "location": "shanghai_store_01"},
        ]

        # 启动会话健康检查任务
        health_task = asyncio.create_task(self.check_sessions_health())

        try:
            # 依次启动游戏会话
            for i, scenario in enumerate(scenarios):
                if not self.running:
                    break

                logger.info(f"启动场景 {i+1}: {scenario}")
                session = await self.start_game_session(
                    app_id=scenario["app_id"],
                    player_count=scenario["players"],
                    device_id=scenario["device"],
                    location=scenario["location"]
                )

                if session:
                    # 模拟游戏运行
                    await asyncio.sleep(10)

                    # 随机更新玩家数量
                    import random
                    new_players = max(1, session.current_players + random.choice([-1, 0, 1]))
                    self.update_session_players(session.session_id, new_players)

                    # 结束会话
                    await self.end_game_session(session.session_id)

                # 场景间隔
                await asyncio.sleep(5)

            # 等待用户中断
            logger.info("模拟场景完成，按 Ctrl+C 退出...")
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("用户中断，正在关闭...")
        finally:
            # 取消健康检查任务
            health_task.cancel()

            # 清理所有活跃会话
            logger.info("清理所有活跃会话...")
            for session_id in list(self.active_sessions.keys()):
                await self.end_game_session(session_id)

            # 关闭客户端
            self.client.close()
            self.executor.shutdown(wait=True)

    async def print_status(self):
        """定期打印状态信息"""
        while self.running:
            try:
                balance = self.get_balance()
                active_count = len(self.active_sessions)

                print(f"\n=== 服务器状态 ===")
                print(f"账户余额: ¥{balance or '未知'}")
                print(f"活跃会话数: {active_count}")

                if self.active_sessions:
                    print("活跃会话:")
                    for session_id, session in self.active_sessions.items():
                        duration = session.get_duration()
                        print(f"  {session_id}: {session.current_players}玩家, {duration}秒")

                print("================\n")

                # 每30秒打印一次状态
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"状态打印异常: {e}")
                await asyncio.sleep(60)

    async def start(self):
        """启动服务器"""
        logger.info("启动头显服务器...")

        # 启动状态打印任务
        status_task = asyncio.create_task(self.print_status())

        # 启动模拟场景
        await self.run_simulation()

        # 清理
        status_task.cancel()


async def main():
    """主函数"""
    # 配置信息 (请替换为实际的API密钥)
    API_KEY = "demo_api_key"
    API_SECRET = "demo_api_secret"
    BASE_URL = "http://localhost:8000"  # 开发环境

    # 创建并启动服务器
    server = HeadsetServer(API_KEY, API_SECRET, BASE_URL)

    try:
        await server.start()
    except Exception as e:
        logger.error(f"服务器运行异常: {e}")
    finally:
        logger.info("服务器已关闭")


if __name__ == "__main__":
    print("MR头显服务器集成示例")
    print("=" * 50)
    print("注意: 请确保后端服务正在运行 (http://localhost:8000)")
    print("请替换 API_KEY 和 API_SECRET 为实际值")
    print("=" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)