#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""准备头显API测试所需的全部测试数据"""

import sys
import io
import requests
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "headset_test_op"
PASSWORD = "Test123456"

def login():
    """登录获取Token"""
    print("1. 登录运营商账号...")
    response = requests.post(
        f"{BASE_URL}/auth/operators/login",
        json={"username": USERNAME, "password": PASSWORD}
    )

    if response.status_code == 200:
        data = response.json()
        token = data["data"]["access_token"]
        print(f"   ✓ 登录成功")
        return token
    else:
        print(f"   ✗ 登录失败: {response.text}")
        return None

def recharge(token):
    """财务账号充值"""
    print("\n2. 财务账号充值（需admin_finance权限）...")
    print("   提示: 这一步需要财务管理员权限，跳过")
    print("   请手动在数据库中给账号充值，或使用管理员账号充值")
    # 直接在数据库中更新余额
    return True

def create_site(token):
    """创建运营点"""
    print("\n3. 创建运营点...")
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "name": "测试运营点1号",  # API字段名是name不是site_name
        "contact_person": "张测试",
        "contact_phone": "13900139000",
        "address": "测试市测试区测试路1号"
    }

    response = requests.post(
        f"{BASE_URL}/operators/me/sites",
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        data = response.json()
        site_id = data["data"]["site_id"]
        print(f"   ✓ 运营点创建成功: {site_id}")
        return site_id
    else:
        print(f"   ✗ 创建失败: {response.text}")
        return None

def apply_application(token, site_id):
    """申请应用授权"""
    print("\n4. 申请应用授权...")
    headers = {"Authorization": f"Bearer {token}"}

    # 先查询可用的应用
    response = requests.get(f"{BASE_URL}/admin/applications", headers=headers)

    if response.status_code != 200:
        print(f"   ✗ 查询应用失败: {response.text}")
        return None

    apps = response.json()["data"]["items"]
    if not apps:
        print("   ✗ 没有可用的应用")
        return None

    app_code = apps[0]["app_code"]
    print(f"   找到应用: {app_code}")

    # 申请授权
    payload = {
        "app_code": app_code,
        "site_id": site_id,
        "reason": "测试头显API集成"
    }

    response = requests.post(
        f"{BASE_URL}/operators/me/applications/requests",
        headers=headers,
        json=payload
    )

    if response.status_code == 201:
        print(f"   ✓ 应用授权申请已提交")
        print(f"   提示: 需要管理员审批授权申请")
        return app_code
    else:
        print(f"   ✗ 申请失败: {response.text}")
        return None

def main():
    print("=" * 60)
    print("准备头显API测试数据")
    print("=" * 60)

    # 1. 登录
    token = login()
    if not token:
        print("\n✗ 测试数据准备失败: 登录失败")
        return

    # 2. 充值 (跳过,需手动)
    recharge(token)

    # 3. 创建运营点
    site_id = create_site(token)
    if not site_id:
        print("\n✗ 测试数据准备失败: 创建运营点失败")
        return

    # 4. 申请应用授权
    app_code = apply_application(token, site_id)

    print("\n" + "=" * 60)
    print("测试数据准备完成")
    print("=" * 60)
    print(f"运营商用户: {USERNAME}")
    print(f"密码: {PASSWORD}")
    print(f"运营点ID: {site_id}")
    if app_code:
        print(f"应用代码: {app_code}")

    print("\n后续步骤:")
    print("1. 在数据库中给账号充值 (或使用管理员账号充值)")
    print("2. 使用管理员账号审批应用授权申请")
    print("3. 运行 python test_headset_api.py 测试")

if __name__ == "__main__":
    main()
