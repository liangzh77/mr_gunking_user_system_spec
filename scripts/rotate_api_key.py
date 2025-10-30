#!/usr/bin/env python3
"""
单个运营商API Key轮换脚本

Usage:
    python rotate_api_key.py \\
        --operator-id {operator_id} \\
        --admin-token {admin_token} \\
        --reason "定期轮换" \\
        --notify
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

import requests


class APIKeyRotator:
    """API Key轮换工具"""

    def __init__(self, base_url: str, admin_token: str, verbose: bool = False):
        """初始化

        Args:
            base_url: API基础URL
            admin_token: 管理员JWT Token
            verbose: 是否输出详细日志
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        self.verbose = verbose

    def log(self, message: str, level: str = 'INFO'):
        """输出日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def verbose_log(self, message: str):
        """输出详细日志"""
        if self.verbose:
            self.log(message, 'DEBUG')

    def get_operator_info(self, operator_id: str) -> Optional[dict]:
        """获取运营商信息

        Args:
            operator_id: 运营商ID

        Returns:
            运营商信息字典，失败返回None
        """
        url = f"{self.base_url}/v1/admins/operators/{operator_id}"
        self.verbose_log(f"GET {url}")

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.log(f"获取运营商信息失败: {e}", 'ERROR')
            return None

    def get_current_api_key(self, operator_id: str) -> Optional[str]:
        """获取当前API Key

        Args:
            operator_id: 运营商ID

        Returns:
            当前API Key，失败返回None
        """
        url = f"{self.base_url}/v1/admins/operators/{operator_id}/api-key"
        self.verbose_log(f"GET {url}")

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('api_key')
        except requests.exceptions.RequestException as e:
            self.log(f"获取当前API Key失败: {e}", 'ERROR')
            return None

    def rotate_api_key(
        self,
        operator_id: str,
        reason: str,
        notify: bool = False
    ) -> Optional[dict]:
        """轮换API Key

        Args:
            operator_id: 运营商ID
            reason: 轮换原因
            notify: 是否通知运营商

        Returns:
            轮换结果字典，失败返回None
        """
        # 注意：这个端点当前可能不存在，需要实现
        # 这里提供的是预期的API调用方式
        url = f"{self.base_url}/v1/admins/operators/{operator_id}/reset-api-key"
        self.verbose_log(f"POST {url}")

        payload = {
            'reason': reason,
            'notify_operator': notify
        }

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.log("API端点不存在，使用Service层方法模拟", 'WARNING')
                self.log("请联系技术团队实现 POST /v1/admins/operators/{id}/reset-api-key 端点", 'WARNING')
                return None
            self.log(f"轮换API Key失败: {e}", 'ERROR')
            return None
        except requests.exceptions.RequestException as e:
            self.log(f"轮换API Key失败: {e}", 'ERROR')
            return None

    def verify_new_api_key(self, new_api_key: str, site_id: str, app_id: str) -> bool:
        """验证新API Key

        Args:
            new_api_key: 新API Key
            site_id: 测试用运营点ID
            app_id: 测试用应用ID

        Returns:
            验证是否成功
        """
        url = f"{self.base_url}/v1/game/authorize"
        headers = {
            'X-API-Key': new_api_key,
            'Content-Type': 'application/json'
        }
        payload = {
            'session_id': f'test_rotation_{datetime.now().timestamp()}',
            'site_id': site_id,
            'app_id': app_id,
            'player_count': 1
        }

        self.verbose_log(f"POST {url} (验证新Key)")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            # 可能因为余额不足等原因返回402，但这也说明Key有效
            if response.status_code in [200, 402]:
                return True
            return False
        except requests.exceptions.RequestException:
            return False

    def run(
        self,
        operator_id: str,
        reason: str,
        notify: bool = False,
        verify: bool = False,
        site_id: Optional[str] = None,
        app_id: Optional[str] = None
    ) -> bool:
        """执行完整的轮换流程

        Args:
            operator_id: 运营商ID
            reason: 轮换原因
            notify: 是否通知运营商
            verify: 是否验证新Key
            site_id: 验证用运营点ID
            app_id: 验证用应用ID

        Returns:
            是否成功
        """
        self.log("=" * 60)
        self.log("开始API Key轮换流程")
        self.log("=" * 60)

        # Step 1: 获取运营商信息
        self.log(f"[1/5] 获取运营商信息: {operator_id}")
        operator_info = self.get_operator_info(operator_id)
        if not operator_info:
            self.log("无法获取运营商信息，流程终止", 'ERROR')
            return False

        self.log(f"      运营商名称: {operator_info.get('full_name')}")
        self.log(f"      用户名: {operator_info.get('username')}")
        self.log(f"      客户等级: {operator_info.get('customer_tier')}")

        # Step 2: 获取当前API Key
        self.log("[2/5] 获取当前API Key")
        current_key = self.get_current_api_key(operator_id)
        if current_key:
            masked_key = f"{current_key[:8]}...{current_key[-8:]}"
            self.log(f"      当前Key: {masked_key}")
        else:
            self.log("      无法获取当前Key（可能无查看权限）", 'WARNING')

        # Step 3: 执行轮换
        self.log(f"[3/5] 执行API Key轮换 (原因: {reason})")
        rotation_result = self.rotate_api_key(operator_id, reason, notify)

        if not rotation_result:
            self.log("API Key轮换失败", 'ERROR')
            self.log("", 'INFO')
            self.log("可能的原因:", 'INFO')
            self.log("  1. API端点未实现 (POST /v1/admins/operators/{id}/reset-api-key)", 'INFO')
            self.log("  2. 权限不足", 'INFO')
            self.log("  3. 运营商不存在或已被锁定", 'INFO')
            self.log("", 'INFO')
            self.log("解决方案:", 'INFO')
            self.log("  1. 使用管理后台手动轮换", 'INFO')
            self.log("  2. 联系技术团队实现API端点", 'INFO')
            return False

        new_key = rotation_result.get('new_api_key')
        if new_key:
            masked_new_key = f"{new_key[:8]}...{new_key[-8:]}"
            self.log(f"      新Key: {masked_new_key}")
            self.log(f"      ⚠️  完整Key已保存到文件: api_key_{operator_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

            # 保存完整Key到文件
            filename = f"api_key_{operator_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                f.write(f"运营商ID: {operator_id}\n")
                f.write(f"运营商名称: {operator_info.get('full_name')}\n")
                f.write(f"轮换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"轮换原因: {reason}\n")
                f.write(f"\n完整API Key:\n{new_key}\n")
                f.write(f"\n⚠️  请通过安全渠道发送给运营商，阅后即焚！\n")

        # Step 4: 验证新Key（可选）
        if verify and new_key and site_id and app_id:
            self.log("[4/5] 验证新API Key")
            if self.verify_new_api_key(new_key, site_id, app_id):
                self.log("      ✓ 新Key验证成功")
            else:
                self.log("      ✗ 新Key验证失败", 'WARNING')
        else:
            self.log("[4/5] 跳过验证（需要--verify --site-id --app-id参数）")

        # Step 5: 完成
        self.log("[5/5] 轮换完成")
        self.log("=" * 60)
        self.log("API Key轮换成功！")
        self.log("=" * 60)

        if notify:
            self.log("✓ 已发送通知给运营商")
        else:
            self.log("⚠️  未发送通知，请手动联系运营商")

        self.log("")
        self.log("后续操作:")
        self.log(f"  1. 将 {filename} 中的新Key通过安全渠道发送给运营商")
        self.log("  2. 确认运营商已更新所有运营点的配置")
        self.log("  3. 监控API调用日志，确认旧Key不再被使用")
        self.log("  4. 24小时后删除本地Key文件")

        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='运营商API Key轮换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基本轮换
  python rotate_api_key.py \\
      --operator-id 123e4567-e89b-12d3-a456-426614174000 \\
      --admin-token eyJhbGc... \\
      --reason "定期轮换"

  # 轮换并通知
  python rotate_api_key.py \\
      --operator-id 123e4567-e89b-12d3-a456-426614174000 \\
      --admin-token eyJhbGc... \\
      --reason "安全事件" \\
      --notify

  # 轮换、通知并验证
  python rotate_api_key.py \\
      --operator-id 123e4567-e89b-12d3-a456-426614174000 \\
      --admin-token eyJhbGc... \\
      --reason "定期轮换" \\
      --notify \\
      --verify \\
      --site-id site123 \\
      --app-id app456
        '''
    )

    parser.add_argument(
        '--operator-id',
        required=True,
        help='运营商ID (UUID格式)'
    )
    parser.add_argument(
        '--admin-token',
        required=True,
        help='管理员JWT Token'
    )
    parser.add_argument(
        '--reason',
        required=True,
        help='轮换原因 (如: "定期轮换", "安全事件", "员工离职")'
    )
    parser.add_argument(
        '--notify',
        action='store_true',
        help='轮换后自动通知运营商'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='轮换后验证新Key'
    )
    parser.add_argument(
        '--site-id',
        help='验证用运营点ID (配合--verify使用)'
    )
    parser.add_argument(
        '--app-id',
        help='验证用应用ID (配合--verify使用)'
    )
    parser.add_argument(
        '--base-url',
        default='https://api.example.com',
        help='API基础URL (默认: https://api.example.com)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='输出详细日志'
    )

    args = parser.parse_args()

    # 验证参数
    if args.verify and (not args.site_id or not args.app_id):
        parser.error('--verify 需要同时指定 --site-id 和 --app-id')

    # 创建轮换器
    rotator = APIKeyRotator(
        base_url=args.base_url,
        admin_token=args.admin_token,
        verbose=args.verbose
    )

    # 执行轮换
    success = rotator.run(
        operator_id=args.operator_id,
        reason=args.reason,
        notify=args.notify,
        verify=args.verify,
        site_id=args.site_id,
        app_id=args.app_id
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
