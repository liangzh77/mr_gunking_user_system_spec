#!/usr/bin/env python3
"""
批量运营商API Key轮换脚本

Usage:
    python batch_rotate_api_keys.py \\
        --config rotation_config.json \\
        --admin-token {admin_token} \\
        --execute
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import requests


class BatchAPIKeyRotator:
    """批量API Key轮换工具"""

    def __init__(self, base_url: str, admin_token: str, dry_run: bool = True):
        """初始化

        Args:
            base_url: API基础URL
            admin_token: 管理员JWT Token
            dry_run: 是否为测试模式
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
        self.dry_run = dry_run
        self.results = []

    def log(self, message: str, level: str = 'INFO'):
        """输出日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prefix = "[DRY-RUN] " if self.dry_run else ""
        print(f"{prefix}[{timestamp}] [{level}] {message}")

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典
        """
        self.log(f"加载配置文件: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 验证配置
        if 'batches' not in config:
            raise ValueError("配置文件缺少 'batches' 字段")

        self.log(f"配置加载成功: {len(config['batches'])} 个批次")
        return config

    def rotate_single_operator(
        self,
        operator_id: str,
        reason: str,
        notify: bool = False
    ) -> Dict[str, Any]:
        """轮换单个运营商的API Key

        Args:
            operator_id: 运营商ID
            reason: 轮换原因
            notify: 是否通知

        Returns:
            轮换结果
        """
        if self.dry_run:
            self.log(f"  [模拟] 轮换运营商 {operator_id}")
            return {
                'operator_id': operator_id,
                'success': True,
                'new_api_key': 'SIMULATED_KEY_' + 'x' * 50,
                'message': '测试模式，未实际执行'
            }

        url = f"{self.base_url}/v1/admins/operators/{operator_id}/reset-api-key"
        payload = {
            'reason': reason,
            'notify_operator': notify
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            return {
                'operator_id': operator_id,
                'success': True,
                **response.json()
            }
        except requests.exceptions.HTTPError as e:
            return {
                'operator_id': operator_id,
                'success': False,
                'error': str(e),
                'status_code': e.response.status_code if e.response else None
            }
        except Exception as e:
            return {
                'operator_id': operator_id,
                'success': False,
                'error': str(e)
            }

    def execute_batch(
        self,
        batch: Dict[str, Any],
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """执行一个批次的轮换

        Args:
            batch: 批次配置
            config: 全局配置

        Returns:
            批次执行结果列表
        """
        batch_name = batch.get('name', 'Unknown')
        operator_ids = batch.get('operator_ids', [])
        reason = batch.get('reason', '批量定期轮换')

        self.log("=" * 60)
        self.log(f"开始执行批次: {batch_name}")
        self.log(f"运营商数量: {len(operator_ids)}")
        self.log("=" * 60)

        # 获取通知配置
        notification_config = config.get('notification', {})
        notify = notification_config.get('in_app', False)

        batch_results = []

        for idx, operator_id in enumerate(operator_ids, 1):
            self.log(f"[{idx}/{len(operator_ids)}] 处理运营商: {operator_id}")

            # 执行轮换
            result = self.rotate_single_operator(operator_id, reason, notify)
            batch_results.append(result)

            if result['success']:
                self.log(f"  ✓ 轮换成功")
                if 'new_api_key' in result:
                    masked_key = result['new_api_key'][:8] + '...' + result['new_api_key'][-8:]
                    self.log(f"    新Key: {masked_key}")
            else:
                self.log(f"  ✗ 轮换失败: {result.get('error')}", 'ERROR')

            # 避免API限流
            if idx < len(operator_ids):
                time.sleep(1)

        # 批次统计
        success_count = sum(1 for r in batch_results if r['success'])
        failure_count = len(batch_results) - success_count

        self.log("=" * 60)
        self.log(f"批次 '{batch_name}' 执行完成")
        self.log(f"成功: {success_count}, 失败: {failure_count}")
        self.log("=" * 60)

        return batch_results

    def run(self, config_path: str) -> bool:
        """执行完整的批量轮换流程

        Args:
            config_path: 配置文件路径

        Returns:
            是否全部成功
        """
        try:
            # 加载配置
            config = self.load_config(config_path)

            # 执行所有批次
            all_results = []
            for batch in config['batches']:
                batch_results = self.execute_batch(batch, config)
                all_results.extend(batch_results)

                # 批次间延迟
                if batch != config['batches'][-1]:
                    delay = batch.get('delay_minutes', 5) * 60
                    self.log(f"等待 {delay / 60} 分钟后执行下一批次...")
                    if not self.dry_run:
                        time.sleep(delay)

            # 生成报告
            self.generate_report(all_results, config_path)

            # 统计总体结果
            total_success = sum(1 for r in all_results if r['success'])
            total_failure = len(all_results) - total_success

            self.log("")
            self.log("=" * 60)
            self.log("批量轮换完成")
            self.log(f"总计: {len(all_results)} 个运营商")
            self.log(f"成功: {total_success}")
            self.log(f"失败: {total_failure}")
            self.log("=" * 60)

            return total_failure == 0

        except Exception as e:
            self.log(f"批量轮换失败: {e}", 'ERROR')
            return False

    def generate_report(self, results: List[Dict[str, Any]], config_path: str):
        """生成轮换报告

        Args:
            results: 轮换结果列表
            config_path: 配置文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"rotation_report_{timestamp}.json"

        report = {
            'timestamp': datetime.now().isoformat(),
            'config_file': config_path,
            'dry_run': self.dry_run,
            'total_operators': len(results),
            'successful': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
            'results': results
        }

        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.log(f"报告已生成: {report_filename}")


def create_sample_config():
    """创建示例配置文件"""
    sample_config = {
        "batches": [
            {
                "name": "试点批次",
                "operator_ids": [
                    "operator-id-1",
                    "operator-id-2"
                ],
                "schedule_time": "2025-11-01T02:00:00Z",
                "notify_days_before": 7,
                "reason": "定期轮换 - 试点",
                "delay_minutes": 5
            },
            {
                "name": "主要批次-第1组",
                "operator_ids": [
                    "operator-id-3",
                    "operator-id-4",
                    "operator-id-5"
                ],
                "schedule_time": "2025-11-02T02:00:00Z",
                "notify_days_before": 7,
                "reason": "定期轮换 - 主要批次",
                "delay_minutes": 5
            },
            {
                "name": "VIP批次",
                "operator_ids": [
                    "vip-operator-1"
                ],
                "schedule_time": "2025-11-03T02:00:00Z",
                "notify_days_before": 10,
                "reason": "定期轮换 - VIP客户",
                "delay_minutes": 0
            }
        ],
        "notification": {
            "email": True,
            "sms": False,
            "in_app": True
        },
        "validation": {
            "test_endpoint": True,
            "monitor_hours": 24
        }
    }

    filename = "rotation_config_sample.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)

    print(f"示例配置文件已创建: {filename}")
    print("请根据实际情况修改operator_ids和时间")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='批量运营商API Key轮换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 生成示例配置
  python batch_rotate_api_keys.py --create-sample-config

  # 测试运行（不实际执行）
  python batch_rotate_api_keys.py \\
      --config rotation_config.json \\
      --admin-token eyJhbGc... \\
      --dry-run

  # 正式执行
  python batch_rotate_api_keys.py \\
      --config rotation_config.json \\
      --admin-token eyJhbGc... \\
      --execute
        '''
    )

    parser.add_argument(
        '--config',
        help='配置文件路径 (JSON格式)'
    )
    parser.add_argument(
        '--admin-token',
        help='管理员JWT Token'
    )
    parser.add_argument(
        '--base-url',
        default='https://api.example.com',
        help='API基础URL (默认: https://api.example.com)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='测试模式，不实际执行轮换'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='正式执行轮换（与--dry-run互斥）'
    )
    parser.add_argument(
        '--create-sample-config',
        action='store_true',
        help='创建示例配置文件'
    )

    args = parser.parse_args()

    # 创建示例配置
    if args.create_sample_config:
        create_sample_config()
        return

    # 验证参数
    if not args.config or not args.admin_token:
        parser.error('需要 --config 和 --admin-token 参数（或使用 --create-sample-config）')

    if args.dry_run and args.execute:
        parser.error('--dry-run 和 --execute 不能同时使用')

    # 确定是否为测试模式
    dry_run = not args.execute

    # 创建批量轮换器
    rotator = BatchAPIKeyRotator(
        base_url=args.base_url,
        admin_token=args.admin_token,
        dry_run=dry_run
    )

    # 执行批量轮换
    success = rotator.run(args.config)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
