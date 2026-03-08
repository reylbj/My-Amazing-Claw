#!/bin/bash

# 🐟多账号自动回复系统 - 停止脚本
# Multi-Account Auto-Reply System - Stop Script

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🐟多账号自动回复系统 v2.0                     ║${NC}"
echo -e "${BLUE}║                    系统停止脚本                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

PID_FILE="xianyu_multi.pid"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  未找到PID文件，尝试通过端口查找进程...${NC}"
    
    # 通过端口5002查找进程
    PORT_PID=$(lsof -ti:5002)
    if [ ! -z "$PORT_PID" ]; then
        echo -e "${YELLOW}🔍 发现占用端口5002的进程: $PORT_PID${NC}"
        echo -e "${GREEN}🛑 正在停止进程...${NC}"
        kill -TERM $PORT_PID 2>/dev/null
        sleep 2
        
        # 检查进程是否还在运行
        if ps -p $PORT_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  进程未响应TERM信号，使用KILL信号...${NC}"
            kill -9 $PORT_PID 2>/dev/null
            sleep 1
        fi
        
        if ! ps -p $PORT_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 进程已停止${NC}"
        else
            echo -e "${RED}❌ 无法停止进程${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}ℹ️  未发现运行中的系统${NC}"
    fi
    
    exit 0
fi

# 读取PID
PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  PID文件中的进程($PID)不存在，清理PID文件${NC}"
    rm -f "$PID_FILE"
    
    # 额外检查端口占用
    PORT_PID=$(lsof -ti:5002)
    if [ ! -z "$PORT_PID" ]; then
        echo -e "${YELLOW}🔍 发现其他进程占用端口5002: $PORT_PID${NC}"
        kill -9 $PORT_PID 2>/dev/null
        echo -e "${GREEN}✅ 端口已清理${NC}"
    fi
    
    exit 0
fi

echo -e "${YELLOW}🛑 正在停止系统 (PID: $PID)...${NC}"

# 发送TERM信号优雅关闭
kill -TERM $PID 2>/dev/null

# 等待进程停止
WAIT_COUNT=0
while ps -p $PID > /dev/null 2>&1 && [ $WAIT_COUNT -lt 10 ]; do
    echo -e "${YELLOW}⏳ 等待进程停止... ($((WAIT_COUNT+1))/10)${NC}"
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT+1))
done

# 检查进程是否已停止
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  进程未响应TERM信号，使用KILL信号强制停止...${NC}"
    kill -9 $PID 2>/dev/null
    sleep 1
    
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${RED}❌ 无法停止进程${NC}"
        exit 1
    fi
fi

# 清理PID文件
rm -f "$PID_FILE"

# 额外清理可能的端口占用
PORT_PID=$(lsof -ti:5002)
if [ ! -z "$PORT_PID" ]; then
    kill -9 $PORT_PID 2>/dev/null
fi

echo -e "${GREEN}✅ 系统已成功停止${NC}"
echo -e "${GREEN}   • Web服务已关闭${NC}"
echo -e "${GREEN}   • 所有账号连接已断开${NC}"
echo -e "${GREEN}   • 端口5002已释放${NC}"
echo ""
echo -e "${BLUE}📝 提示:${NC}"
echo -e "   • 运行 ./start.sh 重新启动系统"
echo -e "   • 查看 logs/system.log 了解运行日志"