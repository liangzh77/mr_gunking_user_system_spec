"""MR游戏运营管理系统 Python SDK

用于头显Server集成的Python SDK，提供游戏授权、余额查询等功能。
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mr-game-sdk",
    version="1.0.0",
    author="MR游戏团队",
    author_email="support@mr-game.com",
    description="MR游戏运营管理系统 Python SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mr-game/mr-game-sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "pydantic>=2.0.0",
        "cryptography>=3.4.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.18.0",
            "black>=21.0",
            "flake8>=3.9",
            "mypy>=0.910",
        ],
    },
    keywords="mr-game, sdk, game-authorization, billing",
    project_urls={
        "Bug Reports": "https://github.com/mr-game/mr-game-sdk/issues",
        "Source": "https://github.com/mr-game/mr-game-sdk",
        "Documentation": "https://mr-game-sdk.readthedocs.io/",
    },
)