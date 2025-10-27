"""
契约测试：管理员登录接口 (T120)

测试范围：POST /v1/auth/admin/login
契约定义：specs/001-mr/contracts/auth.yaml#/paths/~1auth~1admin~1login
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestAdminLoginContract:
    """管理员登录接口契约测试"""

    @pytest.mark.asyncio
    async def test_admin_login_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """测试成功登录场景"""
        # 准备测试数据：使用种子数据中的管理员账号
        payload = {
            "username": "admin",
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码
        assert response.status_code == 200

        # 验证响应结构
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "data" in data

        # 验证 Token 数据
        token_data = data["data"]
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert "expires_in" in token_data
        assert "admin" in token_data

        assert token_data["token_type"] == "Bearer"
        assert isinstance(token_data["expires_in"], int)
        assert token_data["expires_in"] > 0

        # 验证管理员信息
        admin_info = token_data["admin"]
        assert "admin_id" in admin_info
        assert "username" in admin_info
        assert "name" in admin_info
        assert admin_info["username"] == "admin"

    @pytest.mark.asyncio
    async def test_admin_login_wrong_password(
        self,
        async_client: AsyncClient,
    ):
        """测试错误密码场景"""
        payload = {
            "username": "admin",
            "password": "WrongPassword123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码
        assert response.status_code == 401

        # 验证错误响应结构
        data = response.json()
        assert "error_code" in data
        assert "message" in data
        assert data["error_code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_admin_login_nonexistent_user(
        self,
        async_client: AsyncClient,
    ):
        """测试不存在的用户名"""
        payload = {
            "username": "nonexistent_admin",
            "password": "SomePassword123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码
        assert response.status_code == 401

        # 验证错误响应结构
        data = response.json()
        assert "error_code" in data
        assert data["error_code"] == "UNAUTHORIZED"

    @pytest.mark.asyncio
    async def test_admin_login_missing_username(
        self,
        async_client: AsyncClient,
    ):
        """测试缺少用户名字段"""
        payload = {
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_admin_login_missing_password(
        self,
        async_client: AsyncClient,
    ):
        """测试缺少密码字段"""
        payload = {
            "username": "admin"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_admin_login_empty_username(
        self,
        async_client: AsyncClient,
    ):
        """测试空用户名"""
        payload = {
            "username": "",
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码（应该是验证错误或认证失败）
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_admin_login_empty_password(
        self,
        async_client: AsyncClient,
    ):
        """测试空密码"""
        payload = {
            "username": "admin",
            "password": ""
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码（应该是验证错误或认证失败）
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_admin_login_invalid_json(
        self,
        async_client: AsyncClient,
    ):
        """测试无效的JSON格式"""
        response = await async_client.post(
            "/v1/auth/admin/login",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )

        # 验证响应状态码
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_admin_login_extra_fields(
        self,
        async_client: AsyncClient,
    ):
        """测试额外字段（应被忽略）"""
        payload = {
            "username": "admin",
            "password": "Admin@123",
            "extra_field": "should_be_ignored"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 验证响应状态码
        assert response.status_code == 200

        # 验证登录成功
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_admin_login_token_format(
        self,
        async_client: AsyncClient,
    ):
        """测试Token格式正确性"""
        payload = {
            "username": "admin",
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        assert response.status_code == 200
        data = response.json()
        token = data["data"]["access_token"]

        # 验证JWT Token格式（应该是 header.payload.signature）
        parts = token.split(".")
        assert len(parts) == 3
        assert all(len(part) > 0 for part in parts)

    @pytest.mark.asyncio
    async def test_admin_login_response_content_type(
        self,
        async_client: AsyncClient,
    ):
        """测试响应Content-Type"""
        payload = {
            "username": "admin",
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_admin_login_case_sensitive_username(
        self,
        async_client: AsyncClient,
    ):
        """测试用户名大小写敏感性"""
        payload = {
            "username": "ADMIN",  # 大写
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 用户名应该区分大小写，大写的ADMIN不存在
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_whitespace_handling(
        self,
        async_client: AsyncClient,
    ):
        """测试用户名前后空格处理"""
        payload = {
            "username": " admin ",
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 应该返回401（空格导致用户名不匹配）或400（验证错误）
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_admin_login_sql_injection_attempt(
        self,
        async_client: AsyncClient,
    ):
        """测试SQL注入防护"""
        payload = {
            "username": "admin' OR '1'='1",
            "password": "anything"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 应该返回401（SQL注入被防护，用户名不存在）
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_very_long_username(
        self,
        async_client: AsyncClient,
    ):
        """测试超长用户名"""
        payload = {
            "username": "a" * 1000,
            "password": "Admin@123"
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 应该返回401或422
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_admin_login_very_long_password(
        self,
        async_client: AsyncClient,
    ):
        """测试超长密码"""
        payload = {
            "username": "admin",
            "password": "P" * 1000
        }

        response = await async_client.post("/v1/auth/admin/login", json=payload)

        # 应该返回401或422
        assert response.status_code in [401, 422]
