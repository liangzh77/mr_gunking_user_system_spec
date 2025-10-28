#!/usr/bin/env python3
"""
MR游戏运营管理系统 - API安全测试脚本
测试API端点的安全性
"""

import requests
import json
import sys
from datetime import datetime

class APISecurityTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results = []

    def log_result(self, test_name, status, details=""):
        self.results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"   {details}")

    def test_health_endpoint(self):
        """测试健康检查端点"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                self.log_result("健康检查端点", "PASS", f"状态码: {response.status_code}")
            else:
                self.log_result("健康检查端点", "FAIL", f"异常状态码: {response.status_code}")
        except Exception as e:
            self.log_result("健康检查端点", "FAIL", f"连接失败: {e}")

    def test_unauthorized_access(self):
        """测试未授权访问"""
        protected_endpoints = [
            "/api/v1/admin/operators",
            "/api/v1/admin/users",
            "/api/v1/finance/statistics",
            "/api/v1/game/sites"
        ]

        for endpoint in protected_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code in [401, 403]:
                    self.log_result(f"未授权访问 {endpoint}", "PASS", f"正确拒绝访问 (状态码: {response.status_code})")
                else:
                    self.log_result(f"未授权访问 {endpoint}", "FAIL", f"可能存在认证绕过 (状态码: {response.status_code})")
            except Exception as e:
                self.log_result(f"未授权访问 {endpoint}", "ERROR", f"请求失败: {e}")

    def test_sql_injection_basic(self):
        """测试基础SQL注入"""
        sql_payloads = [
            "' OR '1'='1",
            "admin'--",
            "' OR 1=1--",
            "'; DROP TABLE users; --"
        ]

        # 测试登录端点
        for payload in sql_payloads:
            try:
                response = requests.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={"username": payload, "password": "password123"},
                    timeout=10
                )

                # 检查响应中是否包含SQL错误
                if "sql" in response.text.lower() or "error" in response.text.lower():
                    self.log_result(f"SQL注入测试 {payload}", "FAIL", "可能的SQL注入漏洞")
                else:
                    self.log_result(f"SQL注入测试 {payload}", "PASS", "未发现SQL注入")

            except Exception as e:
                self.log_result(f"SQL注入测试 {payload}", "ERROR", f"请求失败: {e}")

    def test_xss_basic(self):
        """测试基础XSS"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')"
        ]

        # 测试各种端点
        test_endpoints = [
            ("/api/v1/auth/login", {"username": "test", "password": "test"}),
            ("/api/v1/game/sites", {"site_name": "test", "domain": "test.com"})
        ]

        for payload in xss_payloads:
            for endpoint, data in test_endpoints:
                try:
                    # 修改数据包含XSS载荷
                    test_data = data.copy()
                    if "username" in test_data:
                        test_data["username"] = payload
                    elif "site_name" in test_data:
                        test_data["site_name"] = payload

                    response = requests.post(f"{self.base_url}{endpoint}", json=test_data, timeout=10)

                    if payload in response.text and response.status_code == 200:
                        self.log_result(f"XSS测试 {endpoint}", "FAIL", f"可能的XSS漏洞: {payload}")
                    else:
                        self.log_result(f"XSS测试 {endpoint}", "PASS", "未发现XSS")

                except Exception as e:
                    self.log_result(f"XSS测试 {endpoint}", "ERROR", f"请求失败: {e}")

    def test_rate_limiting(self):
        """测试速率限制"""
        login_endpoint = f"{self.base_url}/api/v1/auth/login"

        # 快速发送多个登录请求
        success_count = 0
        for i in range(20):
            try:
                response = requests.post(
                    login_endpoint,
                    json={"username": f"test{i}", "password": "wrong"},
                    timeout=5
                )
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    self.log_result("速率限制", "PASS", f"在第{i+1}次请求后被限制")
                    return
            except Exception:
                continue

        if success_count >= 15:
            self.log_result("速率限制", "FAIL", "未检测到有效的速率限制")
        else:
            self.log_result("速率限制", "PASS", "似乎存在某种限制机制")

    def test_information_disclosure(self):
        """测试信息泄露"""
        sensitive_paths = [
            "/api/v1/nonexistent",
            "/api/docs",
            "/debug",
            "/health"
        ]

        for path in sensitive_paths:
            try:
                response = requests.get(f"{self.base_url}{path}", timeout=10)

                # 检查响应中的敏感信息
                sensitive_keywords = [
                    "password", "secret", "key", "token", "error", "exception",
                    "stack trace", "database", "internal", "debug"
                ]

                response_text = response.text.lower()
                found_sensitive = False

                for keyword in sensitive_keywords:
                    if keyword in response_text:
                        self.log_result(f"信息泄露 {path}", "WARNING", f"可能泄露敏感信息: {keyword}")
                        found_sensitive = True
                        break

                if not found_sensitive:
                    self.log_result(f"信息泄露 {path}", "PASS", "未发现明显信息泄露")

            except Exception as e:
                self.log_result(f"信息泄露 {path}", "ERROR", f"请求失败: {e}")

    def run_all_tests(self):
        """运行所有安全测试"""
        print("开始API安全测试...")
        print("=" * 50)

        self.test_health_endpoint()
        self.test_unauthorized_access()
        self.test_sql_injection_basic()
        self.test_xss_basic()
        self.test_rate_limiting()
        self.test_information_disclosure()

        print("=" * 50)
        self.generate_report()

    def generate_report(self):
        """生成测试报告"""
        # 统计结果
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL'])
        warnings = len([r for r in self.results if r['status'] == 'WARNING'])
        errors = len([r for r in self.results if r['status'] == 'ERROR'])

        print(f"\n📊 测试总结:")
        print(f"   ✅ 通过: {passed}")
        print(f"   ❌ 失败: {failed}")
        print(f"   ⚠️  警告: {warnings}")
        print(f"   ❌ 错误: {errors}")

        # 保存详细报告
        report = {
            "test_time": datetime.now().isoformat(),
            "target": self.base_url,
            "summary": {
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "errors": errors,
                "total": len(self.results)
            },
            "results": self.results
        }

        report_file = f"api_security_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

        # 安全建议
        if failed > 0 or warnings > 0:
            print(f"\n🔧 安全建议:")
            if failed > 0:
                print("   - 立即修复所有失败的测试项")
            if warnings > 0:
                print("   - 检查并处理警告项")
            print("   - 定期进行安全测试")
            print("   - 实施更强的认证和授权机制")
            print("   - 添加输入验证和错误处理")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MR游戏运营管理系统API安全测试")
    parser.add_argument("--host", default="http://localhost:8000", help="目标服务器地址")

    args = parser.parse_args()

    tester = APISecurityTester(args.host)
    tester.run_all_tests()

if __name__ == "__main__":
    main()