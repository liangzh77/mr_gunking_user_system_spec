@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================
echo MR游戏运营管理系统 - OpenAPI契约验证
echo ============================================
echo.

REM 检查依赖工具
echo 1. 检查依赖工具...

where npx >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未安装 npx，请先安装 Node.js
    exit /b 1
)

echo ✓ npx 已安装
echo.

REM 验证主契约文件
echo 2. 验证主契约文件（openapi.yaml）...
npx @redocly/cli lint openapi.yaml --skip-rule=no-invalid-media-type-examples

if %errorlevel% neq 0 (
    echo ✗ openapi.yaml 验证失败
    exit /b 1
)

echo ✓ openapi.yaml 验证通过
echo.

REM 统计接口数量
echo 3. 统计API接口数量...
echo.

set /a total_count=0

for /f %%i in ('findstr /c:"operationId:" auth.yaml ^| find /c /v ""') do set auth_count=%%i
for /f %%i in ('findstr /c:"operationId:" operator.yaml ^| find /c /v ""') do set operator_count=%%i
for /f %%i in ('findstr /c:"operationId:" admin.yaml ^| find /c /v ""') do set admin_count=%%i
for /f %%i in ('findstr /c:"operationId:" finance.yaml ^| find /c /v ""') do set finance_count=%%i

set /a total_count=%auth_count% + %operator_count% + %admin_count% + %finance_count%

echo ├── 授权接口 (auth.yaml):      %auth_count% 个
echo ├── 运营商接口 (operator.yaml): %operator_count% 个
echo ├── 管理员接口 (admin.yaml):    %admin_count% 个
echo ├── 财务接口 (finance.yaml):    %finance_count% 个
echo └── 总计:                       %total_count% 个
echo.

REM 统计代码行数
echo 4. 统计代码行数...
echo.

for /f %%i in ('find /c /v "" ^< openapi.yaml') do set openapi_lines=%%i
for /f %%i in ('find /c /v "" ^< auth.yaml') do set auth_lines=%%i
for /f %%i in ('find /c /v "" ^< operator.yaml') do set operator_lines=%%i
for /f %%i in ('find /c /v "" ^< admin.yaml') do set admin_lines=%%i
for /f %%i in ('find /c /v "" ^< finance.yaml') do set finance_lines=%%i

set /a total_lines=%openapi_lines% + %auth_lines% + %operator_lines% + %admin_lines% + %finance_lines%

echo ├── openapi.yaml:  %openapi_lines% 行
echo ├── auth.yaml:     %auth_lines% 行
echo ├── operator.yaml: %operator_lines% 行
echo ├── admin.yaml:    %admin_lines% 行
echo ├── finance.yaml:  %finance_lines% 行
echo └── 总计:          %total_lines% 行
echo.

REM 生成文档预览
echo 5. 生成HTML文档预览...

npx @redocly/cli build-docs openapi.yaml -o api-docs.html >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ HTML文档已生成: api-docs.html
    echo   打开方式: 在浏览器中打开 api-docs.html
) else (
    echo ✗ HTML文档生成失败（可能需要安装 @redocly/cli）
)
echo.

REM 验证完成
echo ============================================
echo 验证完成！
echo ============================================
echo.
echo 接口总数: %total_count% 个
echo 代码总行数: %total_lines% 行
echo.
echo 下一步操作:
echo 1. 查看HTML文档: 在浏览器中打开 api-docs.html
echo 2. 导入Swagger Editor: https://editor.swagger.io/
echo 3. 生成客户端代码: npx @openapitools/openapi-generator-cli generate
echo 4. 生成服务端代码: npx @openapitools/openapi-generator-cli generate
echo.

pause
