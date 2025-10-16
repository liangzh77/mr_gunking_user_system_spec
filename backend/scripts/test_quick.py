"""快速API测试 - 测试核心功能"""
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 60)
print("快速API测试")
print("=" * 60)

# 1. 注册
username = f"quick_test_{datetime.now().strftime('%H%M%S')}"
print(f"\n[1/5] 注册用户: {username}")
resp = requests.post(
    f"{BASE_URL}/auth/operators/register",
    json={
        "username": username,
        "password": "Test123456",
        "name": "测试公司",
        "email": f"{username}@test.com",
        "phone": "13900139000"
    },
    timeout=10
)
print(f"  状态: {resp.status_code}")
if resp.status_code != 201:
    print(f"  错误: {resp.text}")
    exit(1)

# 2. 登录
print(f"\n[2/5] 登录...")
resp = requests.post(
    f"{BASE_URL}/auth/operators/login",
    json={"username": username, "password": "Test123456"},
    timeout=10
)
print(f"  状态: {resp.status_code}")
if resp.status_code != 200:
    print(f"  错误: {resp.text}")
    exit(1)

token = resp.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"  Token获取成功")

# 3. 创建运营点
print(f"\n[3/5] 创建运营点...")
resp = requests.post(
    f"{BASE_URL}/operators/me/sites",
    json={
        "name": "测试运营点",
        "address": "北京市朝阳区",
        "contact_person": "张三",
        "contact_phone": "13800138000"
    },
    headers=headers,
    timeout=10
)
print(f"  状态: {resp.status_code}")
if resp.status_code != 201:
    print(f"  错误: {resp.text}")
    exit(1)
print(f"  创建成功!")

# 4. 查询运营点
print(f"\n[4/5] 查询运营点列表...")
resp = requests.get(
    f"{BASE_URL}/operators/me/sites",
    headers=headers,
    timeout=10
)
print(f"  状态: {resp.status_code}")
if resp.status_code != 200:
    print(f"  错误: {resp.text}")
    exit(1)
data = resp.json().get("data", resp.json())
sites = data.get("sites", data.get("items", data if isinstance(data, list) else []))
print(f"  运营点数量: {len(sites)}")

# 5. 查询可用应用
print(f"\n[5/5] 查询可用应用...")
resp = requests.get(
    f"{BASE_URL}/operators/me/applications",
    headers=headers,
    timeout=10
)
print(f"  状态: {resp.status_code}")
if resp.status_code != 200:
    print(f"  错误: {resp.text}")
    exit(1)
data = resp.json().get("data", resp.json())
apps = data.get("applications", data.get("items", data if isinstance(data, list) else []))
print(f"  可用应用数量: {len(apps)}")

print("\n" + "=" * 60)
print("测试全部通过!")
print("=" * 60)
