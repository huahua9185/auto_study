@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

REM 自动学习系统启动脚本 (Windows版)
REM 使用方法: start.bat [选项]

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                   自动学习系统                            ║
echo ║                 Auto Study System                        ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM 检查Python环境
echo 🔍 检查运行环境...
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python版本: %PYTHON_VERSION%

REM 检查虚拟环境
if defined VIRTUAL_ENV (
    echo ✅ 虚拟环境: %VIRTUAL_ENV%
) else (
    echo ⚠️  警告: 未检测到虚拟环境，建议使用虚拟环境运行
    set /p REPLY="是否继续? (y/n): "
    if /i not "!REPLY!"=="y" (
        exit /b 1
    )
)

REM 检查依赖
echo 📦 检查依赖包...
python -c "import playwright" > nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未安装playwright，请运行: pip install -r requirements.txt
    pause
    exit /b 1
)

python -c "import loguru" > nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未安装loguru，请运行: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ 依赖包检查通过

REM 检查配置文件
echo ⚙️  检查配置文件...
if not exist ".env" (
    if exist ".env.example" (
        echo 📝 未找到.env文件，正在从.env.example创建...
        copy .env.example .env > nul
        echo ⚠️  请编辑.env文件，配置您的用户名和密码
        pause
    ) else (
        echo ❌ 错误: 未找到配置文件.env和.env.example
        pause
        exit /b 1
    )
)

echo ✅ 配置文件检查通过

REM 创建必要目录
echo 📁 创建数据目录...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache
if not exist "backup" mkdir backup

REM 解析命令行参数
set MODE=full
if "%1"=="demo" set MODE=demo
if "%1"=="monitoring" set MODE=monitoring-only
if "%1"=="recovery" set MODE=recovery-only
if "%1"=="basic" set MODE=basic
if "%1"=="help" goto :help
if "%1"=="-h" goto :help
if "%1"=="--help" goto :help

REM 显示运行模式
echo 🚀 启动模式: %MODE%

REM 启动系统
echo 🎯 启动自动学习系统...
echo.

if "%MODE%"=="demo" (
    python run.py --demo
) else if "%MODE%"=="monitoring-only" (
    python run.py --monitoring-only
) else if "%MODE%"=="recovery-only" (
    python run.py --recovery-only
) else if "%MODE%"=="basic" (
    python -m src.auto_study.main
) else (
    python run.py
)

echo.
echo ✨ 感谢使用自动学习系统！
pause
exit /b 0

:help
echo 使用方法:
echo   start.bat           - 运行完整系统（默认）
echo   start.bat demo      - 运行演示模式
echo   start.bat monitoring - 只运行监控演示
echo   start.bat recovery  - 只运行恢复演示
echo   start.bat basic     - 运行基础功能（无恢复和监控）
echo   start.bat help      - 显示此帮助信息
pause
exit /b 0