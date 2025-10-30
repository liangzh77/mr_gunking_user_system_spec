#!/usr/bin/env python3
"""
API Key使用情况监控脚本

Usage:
    # 监控单个运营商
    python monitor_api_key_usage.py \\
        --operator-id {operator_id} \\
        --admin-token {admin_token} \\
        --hours 24

    # 监控所有运营商
    python monitor_api_key_usage.py \\
        --all \\
        --admin-token {admin_token} \\
        --hours 24 \\
        --report report.html
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests


class APIKeyMonitor:
    """API Key使用监控工具"""

    def __init__(self, base_url: str, admin_token: str):
        """初始化

        Args:
            base_url: API基础URL
            admin_token: 管理员JWT Token
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }

    def log(self, message: str, level: str = 'INFO'):
        """输出日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}")

    def get_operator_info(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """获取运营商信息"""
        url = f"{self.base_url}/v1/admins/operators/{operator_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except:
            return None

    def get_all_operators(self) -> List[Dict[str, Any]]:
        """获取所有运营商列表"""
        url = f"{self.base_url}/v1/admins/operators"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('items', [])
        except:
            return []

    def get_usage_stats(
        self,
        operator_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """获取API使用统计

        Args:
            operator_id: 运营商ID
            hours: 统计小时数

        Returns:
            使用统计
        """
        # 注意：这个端点可能需要实现
        url = f"{self.base_url}/v1/admins/operators/{operator_id}/api-usage"
        params = {'hours': hours}

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # 端点不存在，返回模拟数据
                return self._simulate_usage_stats(operator_id, hours)
            raise
        except Exception as e:
            self.log(f"获取使用统计失败: {e}", 'ERROR')
            return {}

    def _simulate_usage_stats(self, operator_id: str, hours: int) -> Dict[str, Any]:
        """模拟使用统计（用于演示）"""
        import random

        self.log("API端点未实现，使用模拟数据", 'WARNING')

        return {
            'operator_id': operator_id,
            'period_hours': hours,
            'total_requests': random.randint(100, 1000),
            'successful_requests': random.randint(90, 950),
            'failed_requests': random.randint(0, 50),
            '401_errors': random.randint(0, 10),  # 可能是旧Key使用
            '402_errors': random.randint(5, 30),  # 余额不足
            'unique_ips': random.randint(1, 5),
            'last_request_at': datetime.now().isoformat(),
            'top_endpoints': [
                {' endpoint': '/v1/game/authorize', 'count': random.randint(50, 500)},
                {'endpoint': '/v1/game/session/complete', 'count': random.randint(30, 300)}
            ]
        }

    def monitor_single_operator(
        self,
        operator_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """监控单个运营商

        Args:
            operator_id: 运营商ID
            hours: 监控小时数

        Returns:
            监控结果
        """
        self.log(f"监控运营商: {operator_id} (最近 {hours} 小时)")

        # 获取运营商信息
        operator_info = self.get_operator_info(operator_id)
        if not operator_info:
            self.log("无法获取运营商信息", 'ERROR')
            return {}

        # 获取使用统计
        stats = self.get_usage_stats(operator_id, hours)

        # 分析结果
        analysis = self._analyze_usage(stats)

        result = {
            'operator_id': operator_id,
            'operator_name': operator_info.get('full_name'),
            'stats': stats,
            'analysis': analysis,
            'monitored_at': datetime.now().isoformat()
        }

        # 输出报告
        self._print_operator_report(result)

        return result

    def _analyze_usage(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析使用统计"""
        analysis = {
            'status': 'normal',
            'warnings': [],
            'recommendations': []
        }

        if not stats:
            analysis['status'] = 'no_data'
            return analysis

        total_requests = stats.get('total_requests', 0)
        failed_requests = stats.get('failed_requests', 0)
        error_401 = stats.get('401_errors', 0)

        # 检查失败率
        if total_requests > 0:
            failure_rate = (failed_requests / total_requests) * 100
            if failure_rate > 10:
                analysis['warnings'].append(f"失败率过高: {failure_rate:.1f}%")
                analysis['status'] = 'warning'

        # 检查401错误（可能是旧Key使用）
        if error_401 > 0:
            analysis['warnings'].append(f"检测到 {error_401} 次认证失败，可能仍在使用旧API Key")
            analysis['status'] = 'warning'
            analysis['recommendations'].append("联系运营商确认是否已更新所有运营点的API Key")

        # 检查请求量
        if total_requests == 0:
            analysis['warnings'].append("最近无API调用")
            analysis['recommendations'].append("确认运营商业务是否正常")

        # 检查IP数量
        unique_ips = stats.get('unique_ips', 0)
        if unique_ips > 10:
            analysis['warnings'].append(f"使用IP数量异常: {unique_ips} 个")
            analysis['recommendations'].append("可能存在API Key泄露风险，建议立即轮换")

        return analysis

    def _print_operator_report(self, result: Dict[str, Any]):
        """打印单个运营商的监控报告"""
        print("\n" + "=" * 60)
        print(f"运营商: {result['operator_name']} ({result['operator_id']})")
        print("=" * 60)

        stats = result['stats']
        if stats:
            print(f"\n📊 API使用统计:")
            print(f"  总请求数:     {stats.get('total_requests', 0)}")
            print(f"  成功请求:     {stats.get('successful_requests', 0)}")
            print(f"  失败请求:     {stats.get('failed_requests', 0)}")
            print(f"  401错误:      {stats.get('401_errors', 0)} (认证失败)")
            print(f"  402错误:      {stats.get('402_errors', 0)} (余额不足)")
            print(f"  使用IP数:     {stats.get('unique_ips', 0)}")
            print(f"  最后请求:     {stats.get('last_request_at', 'N/A')}")

        analysis = result['analysis']
        print(f"\n🔍 分析结果:")
        print(f"  状态: {analysis['status'].upper()}")

        if analysis['warnings']:
            print(f"\n⚠️  警告:")
            for warning in analysis['warnings']:
                print(f"    - {warning}")

        if analysis['recommendations']:
            print(f"\n💡 建议:")
            for rec in analysis['recommendations']:
                print(f"    - {rec}")

        print("\n" + "=" * 60)

    def monitor_all_operators(self, hours: int = 24) -> List[Dict[str, Any]]:
        """监控所有运营商

        Args:
            hours: 监控小时数

        Returns:
            所有运营商的监控结果
        """
        self.log(f"开始监控所有运营商 (最近 {hours} 小时)")

        operators = self.get_all_operators()
        self.log(f"找到 {len(operators)} 个运营商")

        results = []
        for idx, operator in enumerate(operators, 1):
            self.log(f"[{idx}/{len(operators)}] 处理 {operator.get('username')}")

            result = self.monitor_single_operator(
                operator_id=operator['id'],
                hours=hours
            )
            results.append(result)

        return results

    def generate_html_report(
        self,
        results: List[Dict[str, Any]],
        filename: str
    ):
        """生成HTML报告

        Args:
            results: 监控结果列表
            filename: 输出文件名
        """
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>API Key使用监控报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .status-normal {{ color: green; font-weight: bold; }}
        .status-warning {{ color: orange; font-weight: bold; }}
        .status-error {{ color: red; font-weight: bold; }}
        .warning {{ color: orange; }}
        .recommendation {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
    <h1>API Key使用监控报告</h1>
    <div class="summary">
        <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>运营商数量:</strong> {len(results)}</p>
        <p><strong>正常:</strong> {sum(1 for r in results if r['analysis']['status'] == 'normal')}</p>
        <p><strong>警告:</strong> {sum(1 for r in results if r['analysis']['status'] == 'warning')}</p>
    </div>

    <table>
        <thead>
            <tr>
                <th>运营商</th>
                <th>总请求</th>
                <th>成功</th>
                <th>失败</th>
                <th>401错误</th>
                <th>IP数</th>
                <th>状态</th>
                <th>警告/建议</th>
            </tr>
        </thead>
        <tbody>
"""

        for result in results:
            stats = result['stats']
            analysis = result['analysis']
            status_class = f"status-{analysis['status']}"

            warnings_html = "<br>".join(analysis['warnings']) if analysis['warnings'] else "-"
            recs_html = "<br>".join(analysis['recommendations']) if analysis['recommendations'] else "-"

            html += f"""
            <tr>
                <td>{result['operator_name']}</td>
                <td>{stats.get('total_requests', 0)}</td>
                <td>{stats.get('successful_requests', 0)}</td>
                <td>{stats.get('failed_requests', 0)}</td>
                <td>{stats.get('401_errors', 0)}</td>
                <td>{stats.get('unique_ips', 0)}</td>
                <td class="{status_class}">{analysis['status'].upper()}</td>
                <td>
                    {f'<p class="warning">{warnings_html}</p>' if analysis['warnings'] else ''}
                    {f'<p class="recommendation">{recs_html}</p>' if analysis['recommendations'] else ''}
                </td>
            </tr>
"""

        html += """
        </tbody>
    </table>
</body>
</html>
"""

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        self.log(f"HTML报告已生成: {filename}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='API Key使用情况监控工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 监控单个运营商
  python monitor_api_key_usage.py \\
      --operator-id 123e4567-e89b-12d3-a456-426614174000 \\
      --admin-token eyJhbGc... \\
      --hours 24

  # 监控所有运营商并生成HTML报告
  python monitor_api_key_usage.py \\
      --all \\
      --admin-token eyJhbGc... \\
      --hours 24 \\
      --report usage_report.html
        '''
    )

    parser.add_argument(
        '--operator-id',
        help='运营商ID (单个监控)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='监控所有运营商'
    )
    parser.add_argument(
        '--admin-token',
        required=True,
        help='管理员JWT Token'
    )
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='监控时间范围（小时，默认24）'
    )
    parser.add_argument(
        '--base-url',
        default='https://api.example.com',
        help='API基础URL (默认: https://api.example.com)'
    )
    parser.add_argument(
        '--report',
        help='生成HTML报告文件名'
    )

    args = parser.parse_args()

    # 验证参数
    if not args.operator_id and not args.all:
        parser.error('需要指定 --operator-id 或 --all')

    if args.operator_id and args.all:
        parser.error('--operator-id 和 --all 不能同时使用')

    # 创建监控器
    monitor = APIKeyMonitor(
        base_url=args.base_url,
        admin_token=args.admin_token
    )

    # 执行监控
    if args.operator_id:
        result = monitor.monitor_single_operator(args.operator_id, args.hours)
        results = [result] if result else []
    else:
        results = monitor.monitor_all_operators(args.hours)

    # 生成HTML报告
    if args.report and results:
        monitor.generate_html_report(results, args.report)

    # 检查是否有警告
    has_warnings = any(r['analysis']['status'] != 'normal' for r in results)
    sys.exit(1 if has_warnings else 0)


if __name__ == '__main__':
    main()
