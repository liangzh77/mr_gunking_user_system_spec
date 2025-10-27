#!/usr/bin/env python3
"""
临时测试脚本：检查管理员登录API的实际响应
"""
import requests
import json

def test_admin_login():
    """测试管理员登录API"""
    url = "http://localhost:8001/api/v1/admin/login"
    data = {
        "username": "superadmin",
        "password": "admin123456"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        print(f"正在测试: {url}")
        print(f"请求数据: {json.dumps(data, indent=2)}")

        response = requests.post(url, json=data, headers=headers)

        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")

        if response.status_code == 200:
            try:
                response_json = response.json()
                print(f"\n响应数据结构:")
                print(json.dumps(response_json, indent=2, ensure_ascii=False))

                # 检查关键字段
                if isinstance(response_json, dict):
                    if 'access_token' in response_json:
                        print(f"\n✅ access_token: 存在")
                    else:
                        print(f"\n❌ access_token: 缺失")

                    if 'user' in response_json:
                        print(f"✅ user: 存在")
                        user_data = response_json['user']
                        if isinstance(user_data, dict) and 'id' in user_data:
                            print(f"✅ user.id: {user_data['id']}")
                        else:
                            print(f"❌ user.id: 缺失")
                    else:
                        print(f"❌ user: 缺失")

                    if 'data' in response_json:
                        print(f"⚠️ data: 存在 (可能被包装)")
                        print(f"data内容: {response_json['data']}")
                else:
                    print(f"❌ 响应不是JSON对象: {type(response_json)}")

            except json.JSONDecodeError as e:
                print(f"\n❌ JSON解析失败: {e}")
                print(f"原始响应: {response.text}")
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(f"错误响应: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 {url}")
        print("请确保后端服务在8001端口运行")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    test_admin_login()