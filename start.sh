#!/bin/bash

# 自动学习系统启动脚本
# 使用方法: ./start.sh [选项]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示标题
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                   自动学习系统                            ║"
echo "║                 Auto Study System                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查Python环境
echo -e "${YELLOW}🔍 检查运行环境...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到Python3，请先安装Python 3.8+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}❌ 错误: Python版本 $PYTHON_VERSION 过低，需要 $REQUIRED_VERSION 或更高版本${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python版本: $PYTHON_VERSION${NC}"

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}✅ 虚拟环境: $VIRTUAL_ENV${NC}"
else
    echo -e "${YELLOW}⚠️  警告: 未检测到虚拟环境，建议使用虚拟环境运行${NC}"
    read -p "是否继续? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查依赖
echo -e "${YELLOW}📦 检查依赖包...${NC}"

if ! python3 -c "import playwright" &> /dev/null; then
    echo -e "${RED}❌ 错误: 未安装playwright，请运行: pip install -r requirements.txt${NC}"
    exit 1
fi

if ! python3 -c "import loguru" &> /dev/null; then
    echo -e "${RED}❌ 错误: 未安装loguru，请运行: pip install -r requirements.txt${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 依赖包检查通过${NC}"

# 检查配置文件
echo -e "${YELLOW}⚙️  检查配置文件...${NC}"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}📝 未找到.env文件，正在从.env.example创建...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️  请编辑.env文件，配置您的用户名和密码${NC}"
        read -p "按回车键继续..."
    else
        echo -e "${RED}❌ 错误: 未找到配置文件.env和.env.example${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ 配置文件检查通过${NC}"

# 创建必要目录
echo -e "${YELLOW}📁 创建数据目录...${NC}"
mkdir -p data logs cache backup

# 解析命令行参数
MODE="full"
case "${1:-}" in
    "demo")
        MODE="demo"
        ;;
    "monitoring")
        MODE="monitoring-only"
        ;;
    "recovery")
        MODE="recovery-only"
        ;;
    "basic")
        MODE="basic"
        ;;
    "help"|"-h"|"--help")
        echo "使用方法:"
        echo "  ./start.sh           - 运行完整系统（默认）"
        echo "  ./start.sh demo      - 运行演示模式"
        echo "  ./start.sh monitoring - 只运行监控演示"
        echo "  ./start.sh recovery  - 只运行恢复演示"
        echo "  ./start.sh basic     - 运行基础功能（无恢复和监控）"
        echo "  ./start.sh help      - 显示此帮助信息"
        exit 0
        ;;
esac

# 显示运行模式
echo -e "${BLUE}🚀 启动模式: ${MODE}${NC}"

# 设置错误处理
trap 'echo -e "\n${YELLOW}⏹️  系统已停止${NC}"; exit 0' INT

# 启动系统
echo -e "${GREEN}🎯 启动自动学习系统...${NC}"
echo

case "$MODE" in
    "demo")
        python3 run.py --demo
        ;;
    "monitoring-only")
        python3 run.py --monitoring-only
        ;;
    "recovery-only")
        python3 run.py --recovery-only
        ;;
    "basic")
        python3 -m src.auto_study.main
        ;;
    *)
        python3 run.py
        ;;
esac

echo
echo -e "${GREEN}✨ 感谢使用自动学习系统！${NC}"