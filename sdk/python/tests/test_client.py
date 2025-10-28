#!/usr/bin/env python3
"""MR游戏SDK客户端测试"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime

from mr_game_sdk import MRGameClient
from mr_game_sdk.exceptions import (
    MRGameAPIError,
    MRGameAuthError,
    MRGameValidationError,
    MRGameNetworkError,
)
from mr_game_sdk.models import AuthorizeResponse, BalanceResponse


class TestMRGameClient:
    """MR游戏客户端测试类"""

    def setup_method(self):
        """测试前设置"""
        self.client = MRGameClient(
            api_key="test_api_key",
            api_secret="test_api_secret",
            base_url="http://test.example.com"
        )

    def test_init(self):
        """测试客户端初始化"""
        assert self.client.api_key == "test_api_key"
        assert self.client.api_secret == "test_api_secret"
        assert self.client.base_url == "http://test.example.com"
        assert self.client.timeout == 30

    def test_generate_signature(self):
        """测试签名生成"""
        signature = self.client._generate_signature(
            method="POST",
            path="/v1/test",
            params={"param1": "value1"},
            body='{"data": "test"}',
            timestamp=1234567890
        )

        # 签名应该是32位十六进制字符串
        assert isinstance(signature, str)
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature.lower())

    def test_authorize_game_validation(self):
        """测试游戏授权参数验证"""
        # 测试无效的app_id
        with pytest.raises(MRGameValidationError):
            self.client.authorize_game(app_id=0, player_count=5, session_id="test")

        # 测试无效的player_count
        with pytest.raises(MRGameValidationError):
            self.client.authorize_game(app_id=1, player_count=0, session_id="test")

        # 测试空的session_id
        with pytest.raises(MRGameValidationError):
            self.client.authorize_game(app_id=1, player_count=5, session_id="")

        # 测试过长的session_id
        with pytest.raises(MRGameValidationError):
            self.client.authorize_game(app_id=1, player_count=5, session_id="x" * 129)

    @patch('mr_game_sdk.client.requests.Session.request')
    def test_authorize_game_success(self, mock_request):
        """测试游戏授权成功"""
        # 模拟成功响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "auth_token": "test_token",
            "session_id": "test_session",
            "expires_at": "2025-01-01T12:00:00Z",
            "player_count": 5,
            "billing_rate": 10.0,
            "estimated_cost": 50.0
        }
        mock_request.return_value = mock_response

        result = self.client.authorize_game(
            app_id=1,
            player_count=5,
            session_id="test_session"
        )

        assert isinstance(result, AuthorizeResponse)
        assert result.success is True
        assert result.auth_token == "test_token"
        assert result.session_id == "test_session"
        assert result.player_count == 5

    @patch('mr_game_sdk.client.requests.Session.request')
    def test_authorize_game_failure(self, mock_request):
        """测试游戏授权失败"""
        # 模拟失败响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": False,
            "error_code": "INSUFFICIENT_BALANCE",
            "message": "余额不足"
        }
        mock_request.return_value = mock_response

        with pytest.raises(MRGameAPIError) as exc_info:
            self.client.authorize_game(app_id=1, player_count=5, session_id="test")

        assert "余额不足" in str(exc_info.value)

    @patch('mr_game_sdk.client.requests.Session.request')
    def test_get_balance_success(self, mock_request):
        """测试余额查询成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "balance": 1000.50,
            "currency": "CNY",
            "updated_at": "2025-01-01T12:00:00Z"
        }
        mock_request.return_value = mock_response

        result = self.client.get_balance()

        assert isinstance(result, BalanceResponse)
        assert result.success is True
        assert result.balance == 1000.50
        assert result.currency == "CNY"

    @patch('mr_game_sdk.client.requests.Session.request')
    def test_network_error(self, mock_request):
        """测试网络错误"""
        mock_request.side_effect = Exception("Connection failed")

        with pytest.raises(MRGameNetworkError):
            self.client.get_balance()

    @patch('mr_game_sdk.client.requests.Session.request')
    def test_auth_error(self, mock_request):
        """测试认证错误"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response

        with pytest.raises(MRGameAuthError):
            self.client.get_balance()

    def test_end_game_session_validation(self):
        """测试结束游戏会话参数验证"""
        # 测试无效的app_id
        with pytest.raises(MRGameValidationError):
            self.client.end_game_session(app_id=0, session_id="test", player_count=5)

        # 测试空的session_id
        with pytest.raises(MRGameValidationError):
            self.client.end_game_session(app_id=1, session_id="", player_count=5)

        # 测试负数的player_count
        with pytest.raises(MRGameValidationError):
            self.client.end_game_session(app_id=1, session_id="test", player_count=-1)

    def test_get_transactions_validation(self):
        """测试查询交易记录参数验证"""
        # 测试无效的页码
        with pytest.raises(MRGameValidationError):
            self.client.get_transactions(page=0)

        # 测试无效的页面大小
        with pytest.raises(MRGameValidationError):
            self.client.get_transactions(page_size=0)

        with pytest.raises(MRGameValidationError):
            self.client.get_transactions(page_size=101)

    def test_get_usage_records_validation(self):
        """测试查询使用记录参数验证"""
        # 测试无效的app_id
        with pytest.raises(MRGameValidationError):
            self.client.get_usage_records(app_id=0)

    def test_context_manager(self):
        """测试上下文管理器"""
        with MRGameClient("test_key", "test_secret") as client:
            assert client.api_key == "test_key"
        # 客户端应该自动关闭

    def test_custom_base_url(self):
        """测试自定义基础URL"""
        custom_client = MRGameClient(
            api_key="test",
            api_secret="test",
            base_url="https://custom.example.com/v2/"
        )
        assert custom_client.base_url == "https://custom.example.com/v2"

    def test_headers(self):
        """测试请求头设置"""
        # 检查默认headers
        assert 'User-Agent' in self.client.session.headers
        assert 'Content-Type' in self.client.session.headers
        assert self.client.session.headers['Content-Type'] == 'application/json'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])