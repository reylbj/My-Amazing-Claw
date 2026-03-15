#!/bin/bash

# 🐟多账号自动回复系统 - 状态查看脚本
# Multi-Account Auto-Reply System - Status Script

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              🐟多账号自动回复系统 v2.0                     ║${NC}"
echo -e "${BLUE}║                    系统状态检查                              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

PID_FILE="xianyu_multi.pid"

# 检查PID文件
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo -e "${BLUE}📄 PID文件: ${GREEN}存在${NC} (PID: $PID)"
    
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${BLUE}🔄 进程状态: ${GREEN}运行中${NC}"
        
        # 获取进程信息（macOS兼容）
        PROCESS_INFO=$(ps -p $PID -o pid,ppid,etime,pcpu,pmem,command | tail -n +2)
        echo -e "${BLUE}📊 进程信息:${NC}"
        echo "   $PROCESS_INFO"
    else
        echo -e "${BLUE}🔄 进程状态: ${RED}未运行${NC}"
    fi
else
    echo -e "${BLUE}📄 PID文件: ${RED}不存在${NC}"
fi

# 检查端口5002
PORT_CHECK=$(lsof -ti:5002)
if [ ! -z "$PORT_CHECK" ]; then
    echo -e "${BLUE}🌐 端口5002: ${GREEN}被占用${NC} (PID: $PORT_CHECK)"
    PORT_INFO=$(lsof -i:5002 | tail -n +2)
    echo -e "${BLUE}🔍 端口详情:${NC}"
    echo "$PORT_INFO"
else
    echo -e "${BLUE}🌐 端口5002: ${RED}未占用${NC}"
fi

# 检查Web服务
echo ""
echo -e "${BLUE}🌍 Web服务检查:${NC}"
if curl -s --max-time 3 http://localhost:5002 > /dev/null 2>&1; then
    echo -e "   http://localhost:5002 -> ${GREEN}可访问${NC}"
else
    echo -e "   http://localhost:5002 -> ${RED}不可访问${NC}"
fi

# 检查API状态
if curl -s --max-time 3 http://localhost:5002/api/accounts/status > /dev/null 2>&1; then
    echo -e "   API接口 -> ${GREEN}正常${NC}"
else
    echo -e "   API接口 -> ${RED}异常${NC}"
fi

# 检查日志文件
echo ""
echo -e "${BLUE}📋 日志文件:${NC}"
if [ -f "logs/system.log" ]; then
    LOG_SIZE=$(du -h logs/system.log | cut -f1)
    LOG_LINES=$(wc -l < logs/system.log)
    echo -e "   logs/system.log -> ${GREEN}存在${NC} ($LOG_SIZE, $LOG_LINES 行)"
    
    # 显示最后5行日志
    echo -e "${YELLOW}📄 最近日志 (最后5行):${NC}"
    tail -n 5 logs/system.log | sed 's/^/   /'
else
    echo -e "   logs/system.log -> ${RED}不存在${NC}"
fi

echo ""
echo -e "${BLUE}🛠️  管理命令:${NC}"
echo -e "   ./start.sh  - 启动系统"
echo -e "   ./stop.sh   - 停止系统"
echo -e "   ./status.sh - 查看状态(当前命令)"
echo -e "   tail -f logs/system.log - 实时查看日志"