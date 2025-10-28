@echo off
REM 测试运行脚本 - 使用Python 3.12虚拟环境

echo ========================================
echo MR游戏运营管理系统 - 测试运行器
echo User Story 1: 游戏授权与实时计费
echo ========================================
echo.

REM 设置PYTHONPATH
set PYTHONPATH=%cd%

REM 检查虚拟环境是否存在
if not exist ".venv312\Scripts\python.exe" (
    echo [错误] Python 3.12虚拟环境未找到！
    echo 请先运行: python3.12 -m venv .venv312
    echo 然后运行: .venv312\Scripts\pip.exe install -r requirements.txt aiosqlite
    pause
    exit /b 1
)

echo [信息] 使用Python版本:
.venv312\Scripts\python.exe --version
echo.

REM 根据参数运行不同的测试
if "%1"=="" (
    echo [运行] 所有测试 + 覆盖率报告
    .venv312\Scripts\pytest.exe -v
) else if "%1"=="quick" (
    echo [运行] 快速测试 (无覆盖率)
    .venv312\Scripts\pytest.exe -v --no-cov
) else if "%1"=="contract" (
    echo [运行] 契约测试 (T029)
    .venv312\Scripts\pytest.exe tests/contract/ -v
) else if "%1"=="integration" (
    echo [运行] 集成测试 (T030-T034, T033a)
    .venv312\Scripts\pytest.exe tests/integration/ -v
) else if "%1"=="unit" (
    echo [运行] 单元测试 (T048-T049)
    .venv312\Scripts\pytest.exe tests/unit/ -v
) else if "%1"=="smoke" (
    echo [运行] 冒烟测试 (关键路径)
    .venv312\Scripts\pytest.exe tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success tests/integration/test_insufficient_balance.py::test_insufficient_balance_returns_402 tests/integration/test_session_idempotency.py::test_duplicate_session_id_no_double_charge -v
) else (
    echo [运行] 指定测试文件: %1
    .venv312\Scripts\pytest.exe %1 -v
)

echo.
echo ========================================
echo 测试完成！
echo ========================================
pause
