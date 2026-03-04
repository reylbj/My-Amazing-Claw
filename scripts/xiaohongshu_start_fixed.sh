#!/usr/bin/env bash
# 小红书MCP服务启动脚本（修复版）

set -euo pipefail

log() {
  printf '[xhs-start] %s\n' "$1"
}

# 停止现有服务
log "停止现有MCP服务"
pkill -9 -f xiaohongshu-mcp 2>/dev/null || true
sleep 1

# 检查Cookie文件
if [[ ! -f ~/xhs_workspace/xiaohongshu-send/data/cookies.json ]]; then
  log "❌ Cookie文件不存在"
  log "请先运行: bash /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/scripts/xiaohongshu_quick_fix.sh"
  exit 1
fi

# 启动服务
log "启动MCP服务"
cd ~/xhs_workspace/xiaohongshu-send
COOKIES_PATH=./data/cookies.json nohup ./bin/xiaohongshu-mcp -port :18060 -headless=true -rod "dir=./profile" > logs/mcp.log 2>&1 &
echo $! > run/mcp.pid

sleep 3

# 验证服务
if curl -fsS "http://127.0.0.1:18060/health" >/dev/null 2>&1; then
  log "✅ MCP服务启动成功"

  # 检查登录状态
  login_status=$(curl -fsS "http://127.0.0.1:18060/api/v1/login/status" 2>/dev/null || echo '{"data":{"is_logged_in":false}}')
  is_logged_in=$(echo "${login_status}" | grep -o '"is_logged_in":[^,}]*' | cut -d':' -f2 || echo "false")

  if [[ "${is_logged_in}" == "true" ]]; then
    log "✅ 登录状态: 已登录"
    log "=========================================="
    log "服务已就绪，可以发布内容了！"
    log "=========================================="
    exit 0
  else
    log "⚠️  登录状态: 未登录"
    log "Cookie可能无效，请重新导出Cookie"
    exit 2
  fi
else
  log "❌ MCP服务启动失败"
  tail -20 logs/mcp.log
  exit 1
fi
