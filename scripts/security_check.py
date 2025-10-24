#!/usr/bin/env python3
"""
MR游戏运营管理系统 - 安全检查脚本
适用于Windows环境的简化版本
"""

import os
import sys
import requests
import json
from pathlib import Path
from datetime import datetime

class SecurityChecker:
    def __init__(self, host="http://localhost:8000"):
        self.host = host.rstrip('/')
        self.issues = []
        self.warnings = []
        self.passed = []

    def add_issue(self, severity, category, description, recommendation=""):
        self.issues.append({
            "severity": severity,
            "category": category,
            "description": description,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        })

    def add_warning(self, category, description, recommendation=""):
        self.warnings.append({
            "category": category,
            "description": description,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        })

    def add_pass(self, category, description):
        self.passed.append({
            "category": category,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })

    def check_api_health(self):
        print("检查API健康状态...")

        try:
            response = requests.get(f"{self.host}/health", timeout=10)
            if response.status_code == 200:
                self.add_pass("API健康检查", f"API健康端点正常 (状态码: {response.status_code})")
            else:
                self.add_warning("API健康检查", f"API健康端点返回异常状态码: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.add_issue("HIGH", "API连接", f"无法连接到API: {e}", "检查API服务是否正常运行")

    def check_authentication(self):
        print("检查认证机制...")

        try:
            # 测试未授权访问
            response = requests.get(f"{self.host}/api/v1/admin/operators", timeout=10)

            if response.status_code == 401:
                self.add_pass("认证机制", "API正确要求认证")
            elif response.status_code == 403:
                self.add_pass("认证机制", "API正确拒绝访问")
            else:
                self.add_issue("CRITICAL", "认证机制",
                    f"API端点返回状态码 {response.status_code}，可能未正确配置认证",
                    "确保所有敏感API端点都需要认证")

        except requests.exceptions.RequestException as e:
            self.add_warning("认证检查", f"无法测试认证机制: {e}")

    def check_config_files(self):
        print("检查配置文件安全性...")

        # 检查.env文件
        env_files = [".env", ".env.production", ".env.development"]
        for env_file in env_files:
            if os.path.exists(env_file):
                # 检查默认密钥
                with open(env_file, 'r') as f:
                    content = f.read()
                    default_keys = ["CHANGE_THIS", "dev_secret_key", "admin123", "password123"]

                    for key in default_keys:
                        if key in content:
                            self.add_issue("CRITICAL", "默认密钥",
                                f"{env_file} 包含默认密钥或占位符",
                                "立即更改所有默认密钥为强随机值")
                            break

    def check_file_permissions(self):
        print("检查文件权限...")

        # 在Windows下检查敏感文件
        sensitive_patterns = ["*.key", "*.pem", "*.p12", "id_rsa", ".env*"]

        for pattern in sensitive_patterns:
            for file_path in Path(".").glob(pattern):
                if file_path.exists():
                    self.add_warning("文件权限", f"发现敏感文件: {file_path}",
                        "确保敏感文件有适当的访问控制")

    def run_basic_checks(self):
        print("开始基础安全检查...")
        print("=" * 50)

        self.check_api_health()
        self.check_authentication()
        self.check_config_files()
        self.check_file_permissions()

        print("=" * 50)
        print("安全检查完成!")

        # 生成简单报告
        self.generate_report()

    def generate_report(self):
        report = []
        report.append("# MR游戏运营管理系统 - 安全检查报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"检查目标: {self.host}")
        report.append("")

        # 统计
        critical_count = len([i for i in self.issues if i['severity'] == 'CRITICAL'])
        high_count = len([i for i in self.issues if i['severity'] == 'HIGH'])

        report.append("## 统计信息")
        report.append(f"- 严重问题: {critical_count}")
        report.append(f"- 高风险问题: {high_count}")
        report.append(f"- 警告: {len(self.warnings)}")
        report.append(f"- 通过检查: {len(self.passed)}")
        report.append("")

        # 严重问题
        if critical_count > 0:
            report.append("## 严重问题")
            for issue in self.issues:
                if issue['severity'] == 'CRITICAL':
                    report.append(f"### {issue['category']}")
                    report.append(f"- 问题: {issue['description']}")
                    report.append(f"- 建议: {issue['recommendation']}")
                    report.append("")

        # 高风险问题
        if high_count > 0:
            report.append("## 高风险问题")
            for issue in self.issues:
                if issue['severity'] == 'HIGH':
                    report.append(f"### {issue['category']}")
                    report.append(f"- 问题: {issue['description']}")
                    report.append(f"- 建议: {issue['recommendation']}")
                    report.append("")

        # 警告
        if self.warnings:
            report.append("## 警告")
            for warning in self.warnings:
                report.append(f"### {warning['category']}")
                report.append(f"- 警告: {warning['description']}")
                if warning['recommendation']:
                    report.append(f"- 建议: {warning['recommendation']}")
                report.append("")

        # 通过的检查
        if self.passed:
            report.append("## 通过的检查")
            for passed in self.passed:
                report.append(f"- {passed['category']}: {passed['description']}")
            report.append("")

        report_content = "\n".join(report)
        report_file = f"security_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"报告已保存到: {report_file}")
        print("\n" + report_content)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MR游戏运营管理系统安全检查")
    parser.add_argument("--host", default="http://localhost:8000", help="目标服务器地址")

    args = parser.parse_args()

    checker = SecurityChecker(args.host)
    checker.run_basic_checks()

if __name__ == "__main__":
    main()