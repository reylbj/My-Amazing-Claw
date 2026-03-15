#!/usr/bin/env bash
# 小红书MCP服务稳定启动脚本
# 解决Cookie加载和登录状态问题

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=./xiaohongshu_paths.sh
source "${SCRIPT_DIR}/xiaohongshu_paths.sh"
XHS_HOME="$(xhs_resolve_home "${WORKSPACE_DIR}")"
DATA_DIR="${XHS_HOME}/data"
PROFILE_DIR="${XHS_HOME}/profile"
COOKIE_FILE="${DATA_DIR}/cookies.json"
TMP_COOKIE="/tmp/cookies.json"

log() {
  printf '[xhs-stable] %s\n' "$1"
}

# 1. 确保Cookie文件正确链接
ensure_cookie_link() {
  if [[ -f "${COOKIE_FILE}" ]]; then
    log "✅ Cookie文件存在: ${COOKIE_FILE}"

    # 确保/tmp/cookies.json是软链接
    if [[ -L "${TMP_COOKIE}" ]]; then
      local target
      target="$(readlink "${TMP_COOKIE}")"
      if [[ "${target}" != "${COOKIE_FILE}" ]]; then
        log "⚠️  /tmp/cookies.json链接错误，重新创建"
        rm -f "${TMP_COOKIE}"
        ln -sf "${COOKIE_FILE}" "${TMP_COOKIE}"
      fi
    elif [[ -f "${TMP_COOKIE}" ]]; then
      log "⚠️  /tmp/cookies.json是普通文件，转换为软链接"
      rm -f "${TMP_COOKIE}"
      ln -sf "${COOKIE_FILE}" "${TMP_COOKIE}"
    else
      log "创建Cookie软链接"
      ln -sf "${COOKIE_FILE}" "${TMP_COOKIE}"
    fi
  else
    log "❌ Cookie文件不存在，需要先登录"
    return 1
  fi
}

# 2. 清理可能导致崩溃的锁文件
cleanup_locks() {
  local lock_file="${PROFILE_DIR}/SingletonLock"
  if [[ -f "${lock_file}" ]]; then
    log "清理浏览器锁文件"
    rm -f "${lock_file}"
  fi
}

# 3. 停止现有服务
stop_existing() {
  log "停止现有MCP服务"
  bash "${SCRIPT_DIR}/xiaohongshu_send_setup.sh" stop 2>/dev/null || true

  # 强制清理残留进程
  pkill -f "xiaohongshu-mcp" 2>/dev/null || true
  sleep 1
}

# 4. 启动服务（headless模式，使用已有Cookie）
start_service() {
  log "启动MCP服务（使用已有Cookie）"

  export COOKIES_PATH="${COOKIE_FILE}"

  bash "${SCRIPT_DIR}/xiaohongshu_send_setup.sh" start \
    --port 18060 \
    --headless true \
    --rod "dir=${PROFILE_DIR}"
}

# 5. 验证服务状态
verify_service() {
  log "验证服务状态"
  sleep 3

  local health_check
  health_check=$(curl -fsS "http://127.0.0.1:18060/health" 2>/dev/null || echo "failed")

  if [[ "${health_check}" == "failed" ]]; then
    log "❌ 健康检查失败"
    return 1
  fi

  log "✅ 健康检查通过"

  # 检查登录状态
  local login_status
  login_status=$(curl -fsS "http://127.0.0.1:18060/api/v1/login/status" 2>/dev/null || echo '{"data":{"is_logged_in":false}}')

  local is_logged_in
  is_logged_in=$(echo "${login_status}" | grep -o '"is_logged_in":[^,}]*' | cut -d':' -f2 || echo "false")

  if [[ "${is_logged_in}" == "true" ]]; then
    log "✅ 登录状态: 已登录"
    return 0
  else
    log "⚠️  登录状态: 未登录（Cookie可能过期）"
    return 2
  fi
}

main() {
  log "=========================================="
  log "小红书MCP服务稳定启动"
  log "=========================================="

  # 步骤1: 确保Cookie正确
  if ! ensure_cookie_link; then
    log "请先运行登录流程"
    exit 1
  fi

  # 步骤2: 清理锁文件
  cleanup_locks

  # 步骤3: 停止现有服务
  stop_existing

  # 步骤4: 启动服务
  if ! start_service; then
    log "❌ 服务启动失败"
    exit 1
  fi

  # 步骤5: 验证服务
  local verify_result=0
  verify_service || verify_result=$?

  if [[ ${verify_result} -eq 0 ]]; then
    log "=========================================="
    log "✅ MCP服务启动成功，登录状态正常"
    log "=========================================="
    exit 0
  elif [[ ${verify_result} -eq 2 ]]; then
    log "=========================================="
    log "⚠️  MCP服务启动成功，但需要重新登录"
    log "请运行: bash scripts/xiaohongshu_login_chrome.sh"
    log "=========================================="
    exit 2
  else
    log "=========================================="
    log "❌ MCP服务启动失败"
    log "=========================================="
    exit 1
  fi
}

main "$@"
