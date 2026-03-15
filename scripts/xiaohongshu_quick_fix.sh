#!/usr/bin/env bash
# 小红书快速修复脚本 - 从浏览器导入Cookie

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=./xiaohongshu_paths.sh
source "${SCRIPT_DIR}/xiaohongshu_paths.sh"

WORKSPACE_XHS_HOME="$(xhs_resolve_home "${WORKSPACE_DIR}")"
RUNTIME_XHS_HOME="${XHS_RUNTIME_HOME:-$HOME/xhs_workspace/xiaohongshu-send}"
SOURCE_BIN_DIR="${WORKSPACE_XHS_HOME}/bin"

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
mkdir -p "${RUNTIME_XHS_HOME}/bin" "${RUNTIME_XHS_HOME}/data" "${RUNTIME_XHS_HOME}/logs" "${RUNTIME_XHS_HOME}/profile"

# 3. 复制二进制文件（如果不存在）
if [[ ! -f "${RUNTIME_XHS_HOME}/bin/xiaohongshu-mcp" ]]; then
  log "3. 复制MCP二进制文件"
  [[ -d "${SOURCE_BIN_DIR}" ]] || {
    log "❌ 未找到MCP二进制目录: ${SOURCE_BIN_DIR}"
    exit 1
  }
  cp -r "${SOURCE_BIN_DIR}/"* "${RUNTIME_XHS_HOME}/bin/"
  chmod +x "${RUNTIME_XHS_HOME}/bin/"*
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
echo "   pbpaste > ${RUNTIME_XHS_HOME}/data/cookies.json"
log ""
log "8. 然后运行："
log ""
echo "   bash ${SCRIPT_DIR}/xiaohongshu_start_fixed.sh"
log ""
log "=========================================="
