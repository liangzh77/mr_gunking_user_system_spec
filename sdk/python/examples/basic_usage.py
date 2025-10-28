#!/usr/bin/env python3
"""MR游戏SDK基本使用示例"""

import logging
from datetime import datetime, timedelta
from mr_game_sdk import MRGameClient, MRGameAPIError, MRGameAuthError

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    # 初始化客户端
    client = MRGameClient(
        api_key="your_api_key_here",
        api_secret="your_api_secret_here",
        base_url="http://localhost:8000",  # 开发环境
        timeout=30
    )

    try:
        # 1. 查询账户余额
        print("=== 查询账户余额 ===")
        balance = client.get_balance()
        if balance.success:
            print(f"当前余额: ¥{balance.balance}")
            print(f"更新时间: {balance.updated_at}")
        else:
            print(f"余额查询失败: {balance.message}")
            return

        # 2. 游戏授权
        print("\n=== 游戏授权 ===")
        session_id = f"demo_session_{int(datetime.now().timestamp())}"

        authorize_result = client.authorize_game(
            app_id=1,
            player_count=5,
            session_id=session_id,
            site_id="site_001",
            metadata={
                "device_id": "headset_001",
                "location": "beijing_store_01"
            }
        )

        if authorize_result.success:
            print(f"✅ 授权成功!")
            print(f"会话ID: {authorize_result.session_id}")
            print(f"授权Token: {authorize_result.auth_token}")
            print(f"过期时间: {authorize_result.expires_at}")
            print(f"玩家数量: {authorize_result.player_count}")
            print(f"计费费率: ¥{authorize_result.billing_rate}/人/小时")
            print(f"预估费用: ¥{authorize_result.estimated_cost}")
        else:
            print(f"❌ 授权失败: {authorize_result.message}")
            return

        # 3. 模拟游戏运行
        print("\n=== 模拟游戏运行 ===")
        import time
        print("游戏运行中... (模拟5秒)")
        time.sleep(5)

        # 4. 结束游戏会话
        print("\n=== 结束游戏会话 ===")
        end_result = client.end_game_session(
            app_id=1,
            session_id=session_id,
            player_count=5,  # 最终玩家数量
            metadata={
                "actual_duration": 5,
                "satisfaction_score": 4.5
            }
        )

        if end_result.success:
            print(f"✅ 会话结束成功!")
            print(f"最终玩家数: {end_result.final_player_count}")
            print(f"游戏时长: {end_result.total_duration}秒")
            print(f"总费用: ¥{end_result.total_cost}")
            print(f"交易ID: {end_result.transaction_id}")
        else:
            print(f"❌ 会话结束失败: {end_result.message}")

        # 5. 查询交易记录
        print("\n=== 查询最近交易记录 ===")
        transactions = client.get_transactions(
            page=1,
            page_size=5,
            transaction_type="billing"
        )

        if transactions.success:
            print(f"找到 {len(transactions.items)} 条交易记录:")
            for i, tx in enumerate(transactions.items, 1):
                print(f"  {i}. {tx.transaction_type}: ¥{tx.amount} ({tx.created_at})")
                print(f"     描述: {tx.description}")
        else:
            print(f"交易记录查询失败: {transactions.message}")

        # 6. 查询使用记录
        print("\n=== 查询使用记录 ===")
        usage_records = client.get_usage_records(
            page=1,
            page_size=5,
            start_date=datetime.now() - timedelta(days=7)
        )

        if usage_records.success:
            print(f"找到 {len(usage_records.items)} 条使用记录:")
            for i, record in enumerate(usage_records.items, 1):
                print(f"  {i}. 应用{record.app_id}: {record.player_count}人, {record.duration}秒")
                print(f"     费用: ¥{record.cost}, 会话: {record.session_id}")

    except MRGameAuthError as e:
        print(f"❌ 认证错误: {e}")
        print("请检查API Key和Secret是否正确")
    except MRGameAPIError as e:
        print(f"❌ API错误: {e}")
        if e.error_code == "INSUFFICIENT_BALANCE":
            print("账户余额不足，请先充值")
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        logger.exception("发生未知错误")

if __name__ == "__main__":
    main()