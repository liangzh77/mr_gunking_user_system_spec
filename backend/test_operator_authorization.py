"""测试运营商是否能看到已授权的应用"""
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 运营商登录
print("=" * 60)
print("1. 运营商登录")
print("=" * 60)

login_resp = requests.post(
    f"{BASE_URL}/auth/operators/login",
    json={"username": "test_operator_110834", "password": "Test123456"}
)

if login_resp.status_code != 200:
    print(f"[ERROR] 登录失败: {login_resp.text}")
    exit(1)

token = login_resp.json()["data"]["access_token"]
print("[OK] 登录成功")

# 2. 查询已授权的应用
print("\n" + "=" * 60)
print("2. 查询已授权的应用")
print("=" * 60)

headers = {"Authorization": f"Bearer {token}"}
apps_resp = requests.get(
    f"{BASE_URL}/operators/me/applications",
    headers=headers
)

if apps_resp.status_code != 200:
    print(f"[ERROR] 查询失败: {apps_resp.text}")
    exit(1)

result = apps_resp.json()
data = result.get("data", result)

# 适配不同的返回格式
if isinstance(data, list):
    apps = data
elif isinstance(data, dict):
    apps = data.get("applications", data.get("items", []))
else:
    apps = []

print(f"[OK] 查询成功，共 {len(apps)} 个已授权应用")

for app in apps:
    app_name = app.get("app_name", "N/A")
    app_code = app.get("app_code", "N/A")
    price = app.get("price_per_player", "N/A")
    print(f"\n  应用: {app_name} ({app_code})")
    print(f"    价格: {price}元/人")

if len(apps) == 0:
    print("\n[WARN] 运营商没有任何授权应用！")
    exit(1)

print("\n" + "=" * 60)
print("[OK] 测试通过！运营商已成功获得应用授权")
print("=" * 60)
