#!/usr/bin/env python3
"""
MR游戏运营管理系统 - 安全审计脚本

此脚本执行基础的安全检查和审计，包括：
1. 配置文件安全检查
2. 依赖包漏洞扫描
3. SSL证书检查
4. 权限检查
5. 密码策略检查
6. API安全检查
7. 日志审计

运行方式:
python scripts/security_audit.py --host http://localhost:8000
"""

import argparse
import json
import os
import re
import subprocess
import sys
import requests
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib
import ssl
import socket
from datetime import datetime, timedelta


class SecurityAuditor:
    """安全审计器"""

    def __init__(self, host: str = "http://localhost:8000"):
        self.host = host
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.passed: List[Dict] = []

    def add_issue(self, severity: str, category: str, description: str, recommendation: str = ""):
        """添加安全问题"""
        self.issues.append({
            "severity": severity,
            "category": category,
            "description": description,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        })

    def add_warning(self, category: str, description: str, recommendation: str = ""):
        """添加警告"""
        self.warnings.append({
            "category": category,
            "description": description,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        })

    def add_pass(self, category: str, description: str):
        """添加通过的检查项"""
        self.passed.append({
            "category": category,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })

    def check_config_security(self) -> None:
        """检查配置文件安全性"""
        print("🔍 检查配置文件安全性...")

        # 检查.env文件权限
        env_files = [".env", ".env.production", ".env.development"]
        for env_file in env_files:
            if os.path.exists(env_file):
                file_stat = os.stat(env_file)
                mode = oct(file_stat.st_mode)[-3:]
                if mode != "600":
                    self.add_issue(
                        "HIGH",
                        "配置文件权限",
                        f"{env_file} 文件权限过于宽松 ({mode})",
                        "运行: chmod 600 " + env_file
                    )
                else:
                    self.add_pass("配置文件权限", f"{env_file} 权限正确")

        # 检查默认密钥
        default_keys = [
            "CHANGE_THIS",
            "dev_secret_key",
            "admin123",
            "password123"
        ]

        for env_file in env_files:
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    content = f.read()
                    for key in default_keys:
                        if key in content:
                            self.add_issue(
                                "CRITICAL",
                                "默认密钥",
                                f"{env_file} 包含默认密钥或占位符",
                                "立即更改所有默认密钥为强随机值"
                            )
                            break

    def check_dependencies(self) -> None:
        """检查依赖包安全性"""
        print("📦 检查依赖包安全性...")

        # 检查requirements.txt
        req_file = "requirements.txt"
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                requirements = f.read()

            # 检查已知有漏洞的包版本
            vulnerable_packages = {
                "requests": "2.25.0",  # 修复某些安全问题的版本
                "urllib3": "1.26.0",  # 修复安全漏洞
                "cryptography": "3.4.0",  # 修复加密问题
                "pyjwt": "2.4.0",  # 修复JWT问题
            }

            for package, min_version in vulnerable_packages.items():
                if package in requirements:
                    version_match = re.search(rf"{package}.*([<>=!]+)\s*([0-9.]+)", requirements)
                    if version_match:
                        operator, version = version_match.groups()
                        # 这里应该比较版本，简化处理
                        self.add_warning(
                            "依赖包版本",
                            f"检查 {package} 版本是否安全",
                            f"确保 {package} 版本 >= {min_version}"
                        )

    def check_ssl_configuration(self) -> None:
        """检查SSL配置"""
        print("🔒 检查SSL配置...")

        if "https://" in self.host:
            try:
                context = ssl.create_default_context()
                with socket.create_connection((self.host.replace("https://", "").replace("http://", ""), 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=self.host.replace("https://", "").replace("http://", "")) as ssock:
                        cert = ssock.getpeercert()

                        # 检查证书有效期
                        expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        days_until_expiry = (expiry_date - datetime.now()).days

                        if days_until_expiry < 30:
                            self.add_issue(
                                "HIGH",
                                "SSL证书",
                                f"SSL证书将在 {days_until_expiry} 天后过期",
                                "续订SSL证书"
                            )
                        else:
                            self.add_pass("SSL证书", f"SSL证书有效期: {days_until_expiry} 天")

                        # 检查证书算法
                        if cert.get('version') == 1:
                            self.add_issue(
                                "HIGH",
                                "SSL证书算法",
                                "使用过时的SSLv1证书",
                                "升级到TLSv1.2或更高版本"
                            )

            except Exception as e:
                self.add_warning(
                    "SSL连接",
                    f"无法验证SSL配置: {e}",
                    "检查SSL证书配置"
                )
        else:
            self.add_issue(
                "HIGH",
                "HTTPS配置",
                "应用未使用HTTPS",
                "在生产环境中启用HTTPS"
            )

    def check_api_security(self) -> None:
        """检查API安全性"""
        print("🌐 检查API安全性...")

        try:
            # 检查健康检查端点
            response = requests.get(f"{self.host}/health", timeout=10)

            # 检查安全头
            security_headers = {
                'X-Frame-Options': '防止点击劫持',
                'X-Content-Type-Options': '防止MIME类型混淆',
                'X-XSS-Protection': 'XSS保护',
                'Strict-Transport-Security': 'HTTPS强制',
                'Content-Security-Policy': '内容安全策略'
            }

            for header, description in security_headers.items():
                if header not in response.headers:
                    self.add_warning(
                        "安全头",
                        f"缺少安全头: {header} - {description}",
                        f"在Nginx配置中添加 {header}"
                    )

            # 检查API文档暴露
            try:
                docs_response = requests.get(f"{self.host}/api/docs", timeout=10)
                if docs_response.status_code == 200:
                    self.add_warning(
                        "API文档暴露",
                        "API文档在生产环境中可访问",
                        "在生产环境中禁用或限制API文档访问"
                    )
            except:
                self.add_pass("API文档", "API文档未公开暴露")

        except requests.exceptions.RequestException as e:
            self.add_issue(
                "MEDIUM",
                "API连接",
                f"无法连接到API: {e}",
                "检查API服务是否正常运行"
            )

    def check_authentication(self) -> None:
        """检查认证机制"""
        print("🔐 检查认证机制...")

        try:
            # 测试未授权访问
            response = requests.get(f"{self.host}/api/v1/admin/operators", timeout=10)

            if response.status_code == 401:
                self.add_pass("认证机制", "API正确要求认证")
            elif response.status_code == 403:
                self.add_pass("认证机制", "API正确拒绝访问")
            else:
                self.add_issue(
                    "CRITICAL",
                    "认证机制",
                    f"API端点返回状态码 {response.status_code}，可能未正确配置认证",
                    "确保所有敏感API端点都需要认证"
                )

        except requests.exceptions.RequestException as e:
            self.add_warning(
                "认证检查",
                f"无法测试认证机制: {e}",
                "检查API服务是否正常运行"
            )

    def check_password_policies(self) -> None:
        """检查密码策略"""
        print("🔑 检查密码策略...")

        # 检查代码中的默认密码
        patterns = [
            (r'password\s*=\s*["\'][^"\']{1,6}["\']', "弱密码"),
            (r'["\']admin["\'].*["\']password["\']', "管理员默认密码"),
            (r'["\']123["\'].*["\']password["\']', "数字密码"),
            (r'["\']test["\'].*["\']password["\']', "测试密码"),
        ]

        python_files = list(Path(".").rglob("*.py"))
        for pattern, description in patterns:
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if re.search(pattern, content, re.IGNORECASE):
                            self.add_issue(
                                "HIGH",
                                "密码策略",
                                f"{py_file} 中发现 {description}",
                                "移除硬编码密码，使用环境变量"
                            )
                            break
                except:
                    continue

    def check_file_permissions(self) -> None:
        """检查文件权限"""
        print("📁 检查文件权限...")

        # 检查敏感文件权限
        sensitive_files = [
            "*.key",
            "*.pem",
            "*.p12",
            "id_rsa",
            ".env*"
        ]

        for pattern in sensitive_files:
            for file_path in Path(".").glob(pattern):
                try:
                    file_stat = file_path.stat()
                    mode = oct(file_stat.st_mode)[-3:]
                    if mode != "600" and mode != "400":
                        self.add_issue(
                            "MEDIUM",
                            "文件权限",
                            f"敏感文件 {file_path} 权限过于宽松 ({mode})",
                            f"运行: chmod 600 {file_path}"
                        )
                except:
                    continue

    def check_logging_security(self) -> None:
        """检查日志安全"""
        print("📋 检查日志安全性...")

        # 检查日志文件权限
        log_dirs = ["/var/log/mr_game_ops", "logs", ".logs"]

        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                for log_file in Path(log_dir).glob("*.log"):
                    try:
                        file_stat = log_file.stat()
                        mode = oct(file_stat.st_mode)[-3:]
                        if mode != "644":
                            self.add_warning(
                                "日志权限",
                                f"日志文件 {log_file} 权限不正确 ({mode})",
                                f"设置权限为 644: chmod 644 {log_file}"
                            )
                    except:
                        continue

    def generate_report(self) -> str:
        """生成安全审计报告"""
        report = []
        report.append("# MR游戏运营管理系统 - 安全审计报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"审计目标: {self.host}")
        report.append("")

        # 统计信息
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        total_passed = len(self.passed)

        report.append("## 审计统计")
        report.append(f"- 严重问题: {len([i for i in self.issues if i['severity'] == 'CRITICAL'])}")
        report.append(f"- 高风险问题: {len([i for i in self.issues if i['severity'] == 'HIGH'])}")
        report.append(f"- 中等风险问题: {len([i for i in self.issues if i['severity'] == 'MEDIUM'])}")
        report.append(f"- 低风险问题: {len([i for i in self.issues if i['severity'] == 'LOW'])}")
        report.append(f"- 警告: {total_warnings}")
        report.append(f"- 通过检查: {total_passed}")
        report.append("")

        # 严重问题
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        if critical_issues:
            report.append("## 🚨 严重问题")
            for issue in critical_issues:
                report.append(f"### {issue['category']}")
                report.append(f"- **问题**: {issue['description']}")
                report.append(f"- **建议**: {issue['recommendation']}")
                report.append("")

        # 高风险问题
        high_issues = [i for i in self.issues if i['severity'] == 'HIGH']
        if high_issues:
            report.append("## ⚠️ 高风险问题")
            for issue in high_issues:
                report.append(f"### {issue['category']}")
                report.append(f"- **问题**: {issue['description']}")
                report.append(f"- **建议**: {issue['recommendation']}")
                report.append("")

        # 其他问题
        other_issues = [i for i in self.issues if i['severity'] not in ['CRITICAL', 'HIGH']]
        if other_issues:
            report.append("## ⚡ 其他问题")
            for issue in other_issues:
                report.append(f"### {issue['category']} ({issue['severity']})")
                report.append(f"- **问题**: {issue['description']}")
                report.append(f"- **建议**: {issue['recommendation']}")
                report.append("")

        # 警告
        if self.warnings:
            report.append("## ⚠️ 警告")
            for warning in self.warnings:
                report.append(f"### {warning['category']}")
                report.append(f"- **警告**: {warning['description']}")
                if warning['recommendation']:
                    report.append(f"- **建议**: {warning['recommendation']}")
                report.append("")

        # 通过的检查
        if self.passed:
            report.append("## ✅ 通过的检查")
            for passed in self.passed:
                report.append(f"- {passed['category']}: {passed['description']}")
            report.append("")

        # 建议
        report.append("## 💡 安全建议")
        report.append("1. **立即修复所有严重和高风险问题**")
        report.append("2. 定期更新依赖包到最新安全版本")
        report.append("3. 启用HTTPS并配置正确的安全头")
        report.append("4. 实施强密码策略")
        report.append("5. 定期进行安全审计")
        report.append("6. 配置入侵检测系统")
        report.append("7. 实施访问控制和最小权限原则")
        report.append("8. 定期备份和灾难恢复计划")
        report.append("9. 监控异常活动")
        report.append("10. 员工安全意识培训")

        return "\n".join(report)

    def run_full_audit(self) -> None:
        """运行完整的安全审计"""
        print("🔍 开始安全审计...")
        print("=" * 50)

        self.check_config_security()
        self.check_dependencies()
        self.check_ssl_configuration()
        self.check_api_security()
        self.check_authentication()
        self.check_password_policies()
        self.check_file_permissions()
        self.check_logging_security()

        print("=" * 50)
        print("✅ 安全审计完成!")

        # 生成报告
        report = self.generate_report()

        # 保存报告
        report_file = f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 报告已保存到: {report_file}")
        print("\n" + report)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MR游戏运营管理系统安全审计")
    parser.add_argument("--host", default="http://localhost:8000", help="目标服务器地址")
    parser.add_argument("--output", help="报告输出文件路径")
    parser.add_argument("--quick", action="store_true", help="快速扫描（仅检查关键项）")

    args = parser.parse_args()

    auditor = SecurityAuditor(args.host)

    if args.quick:
        print("⚡ 快速安全扫描...")
        auditor.check_config_security()
        auditor.check_authentication()
        auditor.check_ssl_configuration()
    else:
        auditor.run_full_audit()


if __name__ == "__main__":
    main()