#!/usr/bin/env bash
# 小红书Chrome浏览器登录脚本
# 使用系统Chrome浏览器弹出登录页面

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
XHS_HOME="${WORKSPACE_DIR}/xiaohongshu-send"
DATA_DIR="${XHS_HOME}/data"
PROFILE_DIR="${XHS_HOME}/profile"
COOKIE_FILE="${DATA_DIR}/cookies.json"
TMP_COOKIE="/tmp/cookies.json"

log() {
  printf '[xhs-login] %s\n' "$1"
}

# 查找Chrome浏览器路径
find_chrome() {
  local chrome_paths=(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
    "/usr/bin/google-chrome"
    "/usr/bin/chromium"
  )

  for path in "${chrome_paths[@]}"; do
    if [[ -x "${path}" ]]; then
      echo "${path}"
      return 0
    fi
  done

  log "❌ 未找到Chrome浏览器"
  return 1
}

# 停止现有服务
stop_existing() {
  log "停止现有MCP服务"
  bash "${SCRIPT_DIR}/xiaohongshu_send_setup.sh" stop 2>/dev/null || true
  pkill -f "xiaohongshu-mcp" 2>/dev/null || true
  pkill -f "xiaohongshu-login" 2>/dev/null || true
  sleep 1
}

# 清理锁文件
cleanup_locks() {
  local lock_file="${PROFILE_DIR}/SingletonLock"
  if [[ -f "${lock_file}" ]]; then
    log "清理浏览器锁文件"
    rm -f "${lock_file}"
  fi
}

# 备份旧Cookie
backup_old_cookie() {
  if [[ -f "${COOKIE_FILE}" ]]; then
    local backup="${DATA_DIR}/cookies.backup.$(date +%Y%m%d_%H%M%S).json"
    cp "${COOKIE_FILE}" "${backup}"
    log "已备份旧Cookie: ${backup}"
  fi
}

# 启动登录流程
start_login() {
  local chrome_bin
  chrome_bin=$(find_chrome)

  log "使用Chrome浏览器: ${chrome_bin}"
  log "=========================================="
  log "即将弹出Chrome浏览器，请扫码登录"
  log "登录成功后Cookie会自动保存"
  log "=========================================="

  export COOKIES_PATH="${COOKIE_FILE}"

  bash "${SCRIPT_DIR}/xiaohongshu_send_setup.sh" login \
    --browser-bin "${chrome_bin}" \
    --rod "dir=${PROFILE_DIR}"
}

# 验证Cookie
verify_cookie() {
  if [[ ! -f "${COOKIE_FILE}" ]]; then
    log "❌ Cookie文件未生成"
    return 1
  fi

  local cookie_size
  cookie_size=$(wc -c < "${COOKIE_FILE}" | tr -d ' ')

  if [[ ${cookie_size} -lt 100 ]]; then
    log "❌ Cookie文件异常（大小: ${cookie_size} bytes）"
    return 1
  fi

  log "✅ Cookie文件已生成（大小: ${cookie_size} bytes）"

  # 创建软链接
  rm -f "${TMP_COOKIE}"
  ln -sf "${COOKIE_FILE}" "${TMP_COOKIE}"
  log "✅ 已创建Cookie软链接"

  return 0
}

main() {
  log "=========================================="
  log "小红书Chrome浏览器登录"
  log "=========================================="

  # 步骤1: 停止现有服务
  stop_existing

  # 步骤2: 清理锁文件
  cleanup_locks

  # 步骤3: 备份旧Cookie
  backup_old_cookie

  # 步骤4: 启动登录流程
  if ! start_login; then
    log "❌ 登录流程失败"
    exit 1
  fi

  # 步骤5: 验证Cookie
  if verify_cookie; then
    log "=========================================="
    log "✅ 登录成功！Cookie已保存"
    log "现在可以运行: bash scripts/xiaohongshu_stable_start.sh"
    log "=========================================="
    exit 0
  else
    log "=========================================="
    log "❌ 登录失败，请重试"
    log "=========================================="
    exit 1
  fi
}

main "$@"
