"""Playwright E2E 测试配置 (T285)

此文件配置 Playwright 测试环境和共享 fixtures。
"""

import pytest
from playwright.sync_api import Page, Browser, BrowserContext


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """自定义浏览器上下文参数"""
    return {
        **browser_context_args,
        "viewport": {
            "width": 1920,
            "height": 1080,
        },
        "ignore_https_errors": True,  # 开发环境可能使用自签名证书
    }


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Page:
    """为每个测试创建新页面"""
    page = context.new_page()
    yield page
    page.close()


# 基础 URL 配置
BASE_URL = "http://localhost:8000"


@pytest.fixture
def base_url():
    """返回基础 URL"""
    return BASE_URL
