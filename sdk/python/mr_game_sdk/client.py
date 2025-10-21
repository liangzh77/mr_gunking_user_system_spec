"""MR游戏SDK主客户端"""

import time
import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    MRGameAPIError,
    MRGameAuthError,
    MRGameValidationError,
    MRGameNetworkError,
    MRGameRateLimitError,
    MRGameInsufficientBalanceError,
)
from .models import (
    AuthorizeResponse,
    EndSessionResponse,
    BalanceResponse,
    TransactionListResponse,
    UsageRecordListResponse,
)

logger = logging.getLogger(__name__)


class MRGameClient:
    """MR游戏系统客户端

    为头显Server提供游戏授权、计费等功能的Python客户端。
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.mr-game.com",
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.3,
    ):
        """初始化客户端

        Args:
            api_key: 运营商API Key
            api_secret: 运营商API Secret
            base_url: API基础URL
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            retry_backoff_factor: 重试间隔因子
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # 配置requests session
        self.session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
            backoff_factor=retry_backoff_factor,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置默认headers
        self.session.headers.update({
            'User-Agent': 'MRGameSDK-Python/1.0.0',
            'Content-Type': 'application/json',
        })

    def _generate_signature(self, method: str, path: str, params: Dict[str, Any] = None,
                          body: str = "", timestamp: int = None) -> str:
        """生成HMAC签名

        Args:
            method: HTTP方法
            path: API路径
            params: 查询参数
            body: 请求体
            timestamp: 时间戳

        Returns:
            HMAC签名
        """
        if timestamp is None:
            timestamp = int(time.time())

        # 构建签名字符串
        sign_parts = [
            method.upper(),
            path,
            "",
            str(timestamp),
            self.api_key
        ]

        # 添加查询参数
        if params:
            sorted_params = sorted(params.items())
            query_string = urlencode(sorted_params)
            sign_parts[2] = query_string

        # 添加请求体
        if body:
            sign_parts.append(body)

        # 计算签名
        sign_string = "\n".join(sign_parts)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _make_request(self, method: str, path: str, params: Dict[str, Any] = None,
                     data: Dict[str, Any] = None) -> Dict[str, Any]:
        """发起API请求

        Args:
            method: HTTP方法
            path: API路径
            params: 查询参数
            data: 请求数据

        Returns:
            API响应数据

        Raises:
            MRGameNetworkError: 网络连接错误
            MRGameAuthError: 认证错误
            MRGameAPIError: API调用错误
        """
        url = f"{self.base_url}{path}"
        timestamp = int(time.time())

        # 准备请求体
        body = ""
        if data is not None:
            body = json.dumps(data, separators=(',', ':'), ensure_ascii=False)

        # 生成签名
        signature = self._generate_signature(method, path, params, body, timestamp)

        # 设置认证headers
        headers = {
            'X-API-Key': self.api_key,
            'X-Timestamp': str(timestamp),
            'X-Signature': signature,
        }

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=body,
                headers=headers,
                timeout=self.timeout
            )

            # 检查HTTP状态码
            if response.status_code == 401:
                raise MRGameAuthError("认证失败，请检查API Key和Secret")
            elif response.status_code == 429:
                raise MRGameRateLimitError("请求频率过高，请稍后重试")
            elif response.status_code >= 500:
                raise MRGameAPIError(f"服务器错误: HTTP {response.status_code}")

            # 解析响应
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                raise MRGameAPIError("无效的JSON响应")

            # 检查业务状态码
            if not response_data.get('success', False):
                error_code = response_data.get('error_code', 'UNKNOWN_ERROR')
                message = response_data.get('message', '未知错误')

                # 特殊错误类型处理
                if error_code == 'INSUFFICIENT_BALANCE':
                    raise MRGameInsufficientBalanceError(message, error_code, response_data)
                elif error_code in ['INVALID_API_KEY', 'INVALID_SIGNATURE']:
                    raise MRGameAuthError(message, error_code, response_data)
                elif error_code.startswith('VALIDATION_'):
                    raise MRGameValidationError(message, error_code, response_data)
                else:
                    raise MRGameAPIError(message, error_code, response_data)

            return response_data

        except requests.exceptions.Timeout:
            raise MRGameNetworkError(f"请求超时 (>{self.timeout}秒)")
        except requests.exceptions.ConnectionError:
            raise MRGameNetworkError("网络连接失败")
        except requests.exceptions.RequestException as e:
            raise MRGameNetworkError(f"网络请求失败: {str(e)}")

    def authorize_game(
        self,
        app_id: int,
        player_count: int,
        session_id: str,
        site_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuthorizeResponse:
        """游戏授权请求

        Args:
            app_id: 应用ID
            player_count: 玩家数量
            session_id: 会话唯一标识
            site_id: 运营点ID (可选)
            metadata: 额外元数据 (可选)

        Returns:
            授权响应结果
        """
        # 参数验证
        if not app_id or app_id <= 0:
            raise MRGameValidationError("app_id必须是正整数")
        if not player_count or player_count <= 0:
            raise MRGameValidationError("player_count必须是正整数")
        if not session_id or len(session_id) > 128:
            raise MRGameValidationError("session_id不能为空且长度不超过128字符")

        # 构建请求数据
        data = {
            'app_id': app_id,
            'player_count': player_count,
            'session_id': session_id,
        }

        if site_id:
            data['site_id'] = site_id
        if metadata:
            data['metadata'] = metadata

        logger.info(f"请求游戏授权: app_id={app_id}, player_count={player_count}")

        # 发起请求
        response_data = self._make_request('POST', '/v1/games/authorize', data=data)

        # 解析响应
        result = AuthorizeResponse(**response_data)
        logger.info(f"授权请求成功: success={result.success}, session_id={result.session_id}")

        return result

    def end_game_session(
        self,
        app_id: int,
        session_id: str,
        player_count: int,
        site_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EndSessionResponse:
        """结束游戏会话

        Args:
            app_id: 应用ID
            session_id: 会话ID
            player_count: 最终玩家数量
            site_id: 运营点ID (可选)
            metadata: 额外元数据 (可选)

        Returns:
            结束会话响应结果
        """
        # 参数验证
        if not app_id or app_id <= 0:
            raise MRGameValidationError("app_id必须是正整数")
        if not session_id:
            raise MRGameValidationError("session_id不能为空")
        if not player_count or player_count < 0:
            raise MRGameValidationError("player_count必须是非负整数")

        # 构建请求数据
        data = {
            'app_id': app_id,
            'session_id': session_id,
            'player_count': player_count,
        }

        if site_id:
            data['site_id'] = site_id
        if metadata:
            data['metadata'] = metadata

        logger.info(f"结束游戏会话: app_id={app_id}, session_id={session_id}")

        # 发起请求
        response_data = self._make_request('POST', '/v1/games/end-session', data=data)

        # 解析响应
        result = EndSessionResponse(**response_data)
        logger.info(f"会话结束成功: success={result.success}, total_cost={result.total_cost}")

        return result

    def get_balance(self) -> BalanceResponse:
        """查询账户余额

        Returns:
            余额查询结果
        """
        logger.info("查询账户余额")

        # 发起请求
        response_data = self._make_request('GET', '/v1/balance')

        # 解析响应
        result = BalanceResponse(**response_data)
        logger.info(f"余额查询成功: balance={result.balance} {result.currency}")

        return result

    def get_transactions(
        self,
        page: int = 1,
        page_size: int = 20,
        transaction_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> TransactionListResponse:
        """查询交易记录

        Args:
            page: 页码
            page_size: 每页大小
            transaction_type: 交易类型过滤 (可选)
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)

        Returns:
            交易记录列表
        """
        # 参数验证
        if page < 1:
            raise MRGameValidationError("page必须大于0")
        if page_size < 1 or page_size > 100:
            raise MRGameValidationError("page_size必须在1-100之间")

        # 构建查询参数
        params = {
            'page': page,
            'page_size': page_size,
        }

        if transaction_type:
            params['transaction_type'] = transaction_type
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()

        logger.info(f"查询交易记录: page={page}, page_size={page_size}")

        # 发起请求
        response_data = self._make_request('GET', '/v1/transactions', params=params)

        # 解析响应
        result = TransactionListResponse(**response_data)
        logger.info(f"交易记录查询成功: total={result.total}")

        return result

    def get_usage_records(
        self,
        page: int = 1,
        page_size: int = 20,
        app_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageRecordListResponse:
        """查询使用记录

        Args:
            page: 页码
            page_size: 每页大小
            app_id: 应用ID过滤 (可选)
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)

        Returns:
            使用记录列表
        """
        # 参数验证
        if page < 1:
            raise MRGameValidationError("page必须大于0")
        if page_size < 1 or page_size > 100:
            raise MRGameValidationError("page_size必须在1-100之间")
        if app_id and app_id <= 0:
            raise MRGameValidationError("app_id必须是正整数")

        # 构建查询参数
        params = {
            'page': page,
            'page_size': page_size,
        }

        if app_id:
            params['app_id'] = app_id
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()

        logger.info(f"查询使用记录: page={page}, page_size={page_size}")

        # 发起请求
        response_data = self._make_request('GET', '/v1/usage-records', params=params)

        # 解析响应
        result = UsageRecordListResponse(**response_data)
        logger.info(f"使用记录查询成功: total={result.total}")

        return result

    def close(self):
        """关闭客户端连接"""
        if self.session:
            self.session.close()
            logger.info("客户端连接已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()