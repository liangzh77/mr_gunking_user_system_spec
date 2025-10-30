#!/usr/bin/env python3
"""
Docker部署验证脚本
用于自动化测试Docker Compose配置和部署流程
用法: python validate_docker_deployment.py [dev|prod]
"""

import sys
import subprocess
import time
import json
import requests
from pathlib import Path
from typing import Optional, Tuple

# 颜色代码（Windows CMD可能不支持，但VSCode终端支持）
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def log_info(msg: str):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")

def log_success(msg: str):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg: str):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def run_command(cmd: list, capture_output: bool = True, timeout: int = 120) -> Tuple[bool, str]:
    """执行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
        return result.returncode == 0, result.stdout if capture_output else ""
    except subprocess.TimeoutExpired:
        return False, "命令超时"
    except Exception as e:
        return False, str(e)

def check_step(description: str, command: list) -> bool:
    """检查单个步骤"""
    print()
    log_info(f"检查: {description}")

    success, output = run_command(command)

    if success:
        log_success(f"{description} - 通过")
        return True
    else:
        log_error(f"{description} - 失败")
        if output:
            print(f"  输出: {output[:200]}")
        return False

def main():
    """主函数"""
    # 环境选择
    env = sys.argv[1] if len(sys.argv) > 1 else "dev"

    if env not in ["dev", "prod"]:
        log_error("无效的环境参数。使用方法: python validate_docker_deployment.py [dev|prod]")
        sys.exit(1)

    compose_file = "docker-compose.yml" if env == "dev" else "docker-compose.yml"

    log_info(f"开始验证 {env} 环境的Docker部署配置")
    log_info(f"使用配置文件: {compose_file}")

    # =============================================================================
    # 1. 前置检查
    # =============================================================================
    print("\n=================================")
    print("阶段 1: 前置环境检查")
    print("=================================")

    if not check_step("Docker已安装", ["docker", "--version"]):
        sys.exit(1)

    if not check_step("Docker Compose已安装", ["docker-compose", "--version"]):
        sys.exit(1)

    if not check_step("Docker服务运行中", ["docker", "info"]):
        sys.exit(1)

    # =============================================================================
    # 2. 配置文件验证
    # =============================================================================
    print("\n=================================")
    print("阶段 2: 配置文件验证")
    print("=================================")

    if not check_step("docker-compose.yml语法正确",
                     ["docker-compose", "-f", compose_file, "config"]):
        sys.exit(1)

    # 检查配置文件
    if env == "dev":
        env_file = Path("backend/.env.development")
    else:
        env_file = Path("backend/.env.production")

    if env_file.exists():
        log_success(f"配置文件 {env_file} 存在")
    else:
        log_error(f"配置文件 {env_file} 不存在")
        sys.exit(1)

    # =============================================================================
    # 3. Docker镜像验证
    # =============================================================================
    print("\n=================================")
    print("阶段 3: Docker镜像验证")
    print("=================================")

    log_info("检查已存在的镜像...")
    success, output = run_command(["docker", "images"])
    if success:
        print(output[:500])  # 显示前500字符

    # =============================================================================
    # 4. 配置验证测试（不实际启动）
    # =============================================================================
    print("\n=================================")
    print("阶段 4: 配置验证测试")
    print("=================================")

    log_info("验证docker-compose配置...")
    success, output = run_command(["docker-compose", "-f", compose_file, "config"])

    if success:
        log_success("Docker Compose配置验证通过")
        # 检查关键配置
        if "postgres" in output:
            log_success("  [OK] PostgreSQL服务已配置")
        if "redis" in output:
            log_success("  [OK] Redis服务已配置")
        if "backend" in output:
            log_success("  [OK] 后端服务已配置")
        if env == "dev" and "frontend" in output:
            log_success("  [OK] 前端服务已配置")
    else:
        log_error("配置验证失败")
        sys.exit(1)

    # =============================================================================
    # 5. 网络和卷配置检查
    # =============================================================================
    print("\n=================================")
    print("阶段 5: 网络和卷配置检查")
    print("=================================")

    # 检查volumes配置
    if "postgres_data" in output:
        log_success("  [OK] PostgreSQL数据卷已配置")
    if "redis_data" in output:
        log_success("  [OK] Redis数据卷已配置")

    # 检查网络配置
    if "networks:" in output:
        log_success("  [OK] Docker网络已配置")

    # =============================================================================
    # 6. 健康检查配置验证
    # =============================================================================
    print("\n=================================")
    print("阶段 6: 健康检查配置验证")
    print("=================================")

    if "healthcheck:" in output:
        log_success("  [OK] 健康检查已配置")
    else:
        log_warning("  [WARN] 部分服务可能缺少健康检查配置")

    # =============================================================================
    # 7. 依赖关系验证
    # =============================================================================
    print("\n=================================")
    print("阶段 7: 服务依赖关系验证")
    print("=================================")

    if "depends_on:" in output:
        log_success("  [OK] 服务依赖关系已配置")

    # =============================================================================
    # 8. 端口映射检查
    # =============================================================================
    print("\n=================================")
    print("阶段 8: 端口映射检查")
    print("=================================")

    log_info("检查端口映射配置...")

    # 检查常见端口
    ports_to_check = {
        "5432": "PostgreSQL",
        "6379": "Redis",
        "8000": "后端API",
    }

    if env == "dev":
        ports_to_check.update({
            "5173": "前端开发服务器",
            "5050": "PgAdmin",
            "8081": "Redis Commander"
        })

    for port, service in ports_to_check.items():
        if f"{port}:" in output or f":{port}" in output:
            log_success(f"  [OK] {service} 端口 {port} 已配置")

    # =============================================================================
    # 9. 环境变量检查
    # =============================================================================
    print("\n=================================")
    print("阶段 9: 环境变量配置检查")
    print("=================================")

    critical_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "JWT_SECRET_KEY",
    ]

    if env == "prod":
        critical_vars.extend(["REDIS_PASSWORD", "POSTGRES_PASSWORD"])

    log_info(f"检查关键环境变量配置（在 {env_file}）...")

    env_content = env_file.read_text(encoding='utf-8')
    for var in critical_vars:
        if var in env_content:
            # 检查是否为占位符
            if "CHANGE_THIS" in env_content or "your_" in env_content.lower():
                log_warning(f"  [WARN] {var} 使用占位符值，生产环境需修改")
            else:
                log_success(f"  [OK] {var} 已配置")
        else:
            log_error(f"  [ERR] {var} 未配置")

    # =============================================================================
    # 10. Dockerfile存在性检查
    # =============================================================================
    print("\n=================================")
    print("阶段 10: Dockerfile存在性检查")
    print("=================================")

    if env == "dev":
        dockerfile_paths = [
            Path("backend/Dockerfile.dev"),
            Path("frontend/Dockerfile.dev"),
        ]
    else:
        dockerfile_paths = [
            Path("backend/Dockerfile"),
            Path("frontend/Dockerfile"),
        ]

    for dockerfile in dockerfile_paths:
        if dockerfile.exists():
            log_success(f"  [OK] {dockerfile} 存在")
        else:
            log_error(f"  [ERR] {dockerfile} 不存在")

    # =============================================================================
    # 11. Nginx配置检查（生产环境）
    # =============================================================================
    if env == "prod":
        print("\n=================================")
        print("阶段 11: Nginx配置检查")
        print("=================================")

        nginx_files = [
            Path("nginx/nginx.conf"),
            Path("nginx/conf.d/mr_game_ops.conf"),
        ]

        for nginx_file in nginx_files:
            if nginx_file.exists():
                log_success(f"  [OK] {nginx_file} 存在")
            else:
                log_error(f"  [ERR] {nginx_file} 不存在")

    # =============================================================================
    # 12. 生产环境特定检查
    # =============================================================================
    if env == "prod":
        print("\n=================================")
        print("阶段 12: 生产环境安全检查")
        print("=================================")

        log_info("检查生产环境安全配置...")

        # 检查DEBUG模式
        if "DEBUG=false" in env_content or "DEBUG=False" in env_content:
            log_success("  [OK] DEBUG模式已关闭")
        else:
            log_error("  [ERR] DEBUG模式未关闭")

        # 检查环境标识
        if "ENVIRONMENT=production" in env_content:
            log_success("  [OK] 环境标识为production")
        else:
            log_warning("  [WARN] 环境标识可能不正确")

        # 检查CORS配置
        if "CORS_ORIGINS" in env_content:
            if "localhost" in env_content and "production" in env_content:
                log_warning("  [WARN] CORS配置包含localhost，生产环境应移除")
            else:
                log_success("  [OK] CORS配置已设置")

    # =============================================================================
    # 总结
    # =============================================================================
    print("\n=================================")
    print("验证完成总结")
    print("=================================")

    log_success(f"{env} 环境的Docker配置验证完成！")

    print("\n下一步操作：")
    if env == "dev":
        print("  1. 启动服务: docker-compose up -d")
        print("  2. 查看日志: docker-compose logs -f")
        print("  3. 访问API: http://localhost:8000/api/docs")
        print("  4. 访问前端: http://localhost:5173")
    else:
        print("  1. 设置环境变量:")
        print("     export POSTGRES_PASSWORD=<strong_password>")
        print("     export REDIS_PASSWORD=<strong_password>")
        print("  2. 修改 backend/.env.production 中的所有密钥")
        print("  3. 配置SSL证书到 nginx/ssl/ 目录")
        print("  4. 启动服务: docker-compose -f docker-compose.yml up -d")

    print("\n提示:")
    print("  - 完整部署文档: docs/DEPLOYMENT.md")
    print("  - 快速参考: docs/PRODUCTION_QUICKSTART.md")

    log_success("验证脚本执行完成！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        log_warning("验证被用户中断")
        sys.exit(130)
    except Exception as e:
        log_error(f"验证过程出现异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
