#!/bin/bash

# 🐟多账号自动回复系统 - 启动脚本
# Multi-Account Auto-Reply System - Start Script

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🐟多账号自动回复系统 v2.0                     ║${NC}"
echo -e "${BLUE}║                Multi-Account Auto-Reply System               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查是否已有进程在运行
PID_FILE="xianyu_multi.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  系统已经在运行中 (PID: $PID)${NC}"
        echo -e "${YELLOW}请先运行 ./stop.sh 停止现有进程${NC}"
        exit 1
    else
        # PID文件存在但进程不存在，清理PID文件
        rm -f "$PID_FILE"
    fi
fi

# 检查端口5002是否被占用
PORT_CHECK=$(lsof -ti:5002)
if [ ! -z "$PORT_CHECK" ]; then
    echo -e "${RED}❌ 端口5002被占用，正在清理...${NC}"
    kill -9 $PORT_CHECK 2>/dev/null
    sleep 2
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未找到，请先安装Python3${NC}"
    exit 1
fi

# 检查必要的文件
if [ ! -f "main_multi.py" ]; then
    echo -e "${RED}❌ 主程序文件 main_multi.py 不存在${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ 配置文件 .env 不存在${NC}"
    echo -e "${YELLOW}请参考 .env.example 创建配置文件${NC}"
    exit 1
fi

# 创建必要的目录
mkdir -p data logs prompts templates static

echo -e "${GREEN}🚀 正在启动多账号自动回复系统...${NC}"
echo ""

# 启动主程序（后台运行）
nohup python3 main_multi.py > logs/system.log 2>&1 &
MAIN_PID=$!

# 保存PID
echo $MAIN_PID > "$PID_FILE"

# 等待服务启动
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 3

# 检查进程是否正常运行
if ps -p $MAIN_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 系统启动成功！${NC}"
    echo -e "${GREEN}   PID: $MAIN_PID${NC}"
    echo -e "${GREEN}   Web管理界面: http://localhost:5002${NC}"
    echo -e "${GREEN}   日志文件: logs/system.log${NC}"
    echo ""
    echo -e "${BLUE}📝 使用说明:${NC}"
    echo -e "   • 访问 http://localhost:5002 进行Web管理"
    echo -e "   • 运行 ./stop.sh 停止系统"
    echo -e "   • 运行 tail -f logs/system.log 查看实时日志"
    echo ""
else
    echo -e "${RED}❌ 系统启动失败${NC}"
    rm -f "$PID_FILE"
    echo -e "${YELLOW}请检查日志文件: logs/system.log${NC}"
    exit 1
fi