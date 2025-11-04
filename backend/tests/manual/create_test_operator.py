#!/usr/bin/env python3
"""创建测试运营商账号"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# 注册新运营商
payload = {
    "username": "headset_test_op",
    "password": "Test123456",  # 包含大小写字母和数字
    "name": "头显测试运营商",  # API需要name字段
    "phone": "13800138000",
    "email": "headset_test@example.com"
}

print("正在注册测试运营商...")
response = requests.post(f"{BASE_URL}/auth/operators/register", json=payload)

print(f"状态码: {response.status_code}")
try:
    data = response.json()
    print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
except:
    print(f"响应: {response.text}")

if response.status_code == 201:
    print("\n[OK] Test operator created successfully!")
    print(f"Username: {payload['username']}")
    print(f"Password: {payload['password']}")
else:
    print("\n[FAIL] Creation failed")
