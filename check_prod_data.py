#!/usr/bin/env python3
"""检查生产环境数据"""
import requests
import json
import urllib3
urllib3.disable_warnings()

BASE_URL = "https://mrgun.chu-jiao.com/api/v1"

print("=== Testing Production Environment ===\n")

# 测试1: 检查API是否可访问
print("1. Testing API health...")
try:
    response = requests.get("https://mrgun.chu-jiao.com/health", verify=False, timeout=5)
    if response.status_code == 200:
        print("[OK] API is accessible")
    else:
        print(f"[WARN] Health check returned: {response.status_code}")
except Exception as e:
    print(f"[ERROR] Cannot access API: {e}")
    exit(1)

# 测试2: 尝试登录
print("\n2. Testing operator login...")
passwords_to_try = ["operator123", "Test123456", "Operator123"]

operator_token = None
for password in passwords_to_try:
    try:
        login_url = f"{BASE_URL}/auth/operators/login"
        login_data = {"username": "operator1", "password": password}

        response = requests.post(login_url, json=login_data, verify=False, timeout=5)
        if response.status_code == 200:
            resp_json = response.json()
            operator_token = resp_json.get("access_token") or resp_json.get("data", {}).get("access_token")
            print(f"[OK] Login successful with password: {password}")
            break
        else:
            print(f"[FAIL] Login failed with password '{password}': {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Login attempt failed: {e}")

if not operator_token:
    print("\n[ERROR] All login attempts failed. Cannot proceed.")
    exit(1)

# 测试3: 检查使用记录
print("\n3. Checking usage records...")
try:
    headers = {"Authorization": f"Bearer {operator_token}"}
    list_url = f"{BASE_URL}/operators/me/usage-records?page=1&page_size=10"

    response = requests.get(list_url, headers=headers, verify=False, timeout=5)
    if response.status_code == 200:
        data = response.json()
        items = data.get("data", {}).get("items", [])
        total = data.get("data", {}).get("total", 0)

        print(f"[OK] Found {total} usage records")
        if items:
            print(f"    Latest record: session_id={items[0].get('session_id')[:50]}...")
        else:
            print("    [WARN] No usage records found - this is why statistics page is empty")
    else:
        print(f"[FAIL] Cannot get usage records: {response.status_code}")
        print(f"    Response: {response.text[:200]}")
except Exception as e:
    print(f"[ERROR] Failed to check usage records: {e}")

# 测试4: 检查统计数据
print("\n4. Checking statistics data...")
try:
    headers = {"Authorization": f"Bearer {operator_token}"}
    stats_url = f"{BASE_URL}/operators/me/statistics/by-site"

    response = requests.get(stats_url, headers=headers, verify=False, timeout=5)
    if response.status_code == 200:
        data = response.json()
        sites = data.get("sites", [])

        if sites:
            print(f"[OK] Found statistics for {len(sites)} sites")
            for site in sites:
                print(f"    - {site.get('site_name')}: {site.get('total_sessions')} sessions, {site.get('total_cost')} yuan")
        else:
            print("[WARN] No statistics data found")
            print("    This is expected if there are no usage records")
    else:
        print(f"[FAIL] Cannot get statistics: {response.status_code}")
        print(f"    Response: {response.text[:200]}")
except Exception as e:
    print(f"[ERROR] Failed to check statistics: {e}")

# 测试5: 检查运营点
print("\n5. Checking operation sites...")
try:
    headers = {"Authorization": f"Bearer {operator_token}"}
    sites_url = f"{BASE_URL}/operators/me/sites"

    response = requests.get(sites_url, headers=headers, verify=False, timeout=5)
    if response.status_code == 200:
        data = response.json()
        sites = data.get("data", {}).get("sites", [])

        if sites:
            print(f"[OK] Found {len(sites)} operation sites")
            for site in sites:
                print(f"    - {site.get('site_name')} (ID: {site.get('site_id')})")
        else:
            print("[WARN] No operation sites found")
    else:
        print(f"[FAIL] Cannot get sites: {response.status_code}")
except Exception as e:
    print(f"[ERROR] Failed to check sites: {e}")

# 测试6: 检查应用授权
print("\n6. Checking authorized applications...")
try:
    headers = {"Authorization": f"Bearer {operator_token}"}
    apps_url = f"{BASE_URL}/operators/me/applications"

    response = requests.get(apps_url, headers=headers, verify=False, timeout=5)
    if response.status_code == 200:
        data = response.json()
        apps = data.get("data", {}).get("applications", [])

        if apps:
            print(f"[OK] Found {len(apps)} authorized applications")
            for app in apps:
                print(f"    - {app.get('app_name')} (Price: {app.get('price_per_player')} yuan/player)")
        else:
            print("[WARN] No authorized applications found")
    else:
        print(f"[FAIL] Cannot get applications: {response.status_code}")
except Exception as e:
    print(f"[ERROR] Failed to check applications: {e}")

print("\n=== Summary ===")
print("To have data in statistics page, you need:")
print("1. At least one operation site")
print("2. At least one authorized application")
print("3. At least one usage record (game session)")
print("\nIf statistics page is empty, it means there are no usage records yet.")
print("You need to:")
print("  a) Create game authorization using /api/v1/auth/game/authorize")
print("  b) Upload game session data using /api/v1/auth/game/session/upload")
