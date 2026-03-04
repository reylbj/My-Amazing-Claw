#!/usr/bin/env bash
# 小红书快速修复脚本 - 从浏览器导入Cookie

set -euo pipefail

log() {
  printf '[xhs-fix] %s\n' "$1"
}

log "=========================================="
log "小红书快速修复方案"
log "=========================================="

# 1. 停止所有MCP进程
log "1. 停止现有MCP服务"
pkill -9 -f xiaohongshu-mcp 2>/dev/null || true
sleep 1

# 2. 确保工作目录存在
log "2. 准备工作目录"
mkdir -p ~/xhs_workspace/xiaohongshu-send/{bin,data,logs,profile}

# 3. 复制二进制文件（如果不存在）
if [[ ! -f ~/xhs_workspace/xiaohongshu-send/bin/xiaohongshu-mcp ]]; then
  log "3. 复制MCP二进制文件"
  cp -r "/Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/xiaohongshu-send/bin/"* ~/xhs_workspace/xiaohongshu-send/bin/
  chmod +x ~/xhs_workspace/xiaohongshu-send/bin/*
fi

# 4. 提示用户导出Cookie
log "=========================================="
log "请按以下步骤操作："
log ""
log "1. 打开Chrome浏览器，访问 https://www.xiaohongshu.com"
log "2. 确认已登录状态"
log "3. 按F12打开开发者工具"
log "4. 切换到Console标签"
log "5. 粘贴以下代码并回车："
log ""
echo 'copy(JSON.stringify(document.cookie.split("; ").map(c => {const [name, value] = c.split("="); return {name, value, domain: ".xiaohongshu.com", path: "/", expires: Date.now()/1000 + 31536000, httpOnly: false, secure: false, session: false}})))'
log ""
log "6. Cookie已复制到剪贴板"
log "7. 运行以下命令保存Cookie："
log ""
echo "   pbpaste > ~/xhs_workspace/xiaohongshu-send/data/cookies.json"
log ""
log "8. 然后运行："
log ""
echo "   bash /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/scripts/xiaohongshu_start_fixed.sh"
log ""
log "=========================================="
