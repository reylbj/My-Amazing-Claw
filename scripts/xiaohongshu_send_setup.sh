#!/usr/bin/env bash
# xiaohongshu-send 环境准备与服务管理脚本

set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

XHS_HOME="${XHS_HOME:-${WORKSPACE_DIR}/xiaohongshu-send}"
BIN_DIR="${XHS_HOME}/bin"
DATA_DIR="${XHS_HOME}/data"
LOG_DIR="${XHS_HOME}/logs"
RUN_DIR="${XHS_HOME}/run"
PROFILE_DIR="${XHS_HOME}/profile"
PID_FILE="${RUN_DIR}/mcp.pid"
MCP_LOG="${LOG_DIR}/mcp.log"
DEFAULT_PORT="${XHS_PORT:-18060}"
COOKIE_BACKUP_FILE="${DATA_DIR}/cookies.backup.json"
TMP_COOKIE_PATH="/tmp/cookies.json"

REPO_API_URL="https://api.github.com/repos/xpzouying/xiaohongshu-mcp/releases/latest"

usage() {
  cat <<'EOF'
xiaohongshu-send setup script

Usage:
  bash scripts/xiaohongshu_send_setup.sh setup
  bash scripts/xiaohongshu_send_setup.sh login [--browser-bin /path/to/chrome] [--rod "dir=/path/to/profile"]
  bash scripts/xiaohongshu_send_setup.sh start [--port 18060] [--headless true|false] [--browser-bin /path/to/chrome] [--rod "dir=/path/to/profile"]
  bash scripts/xiaohongshu_send_setup.sh stop
  bash scripts/xiaohongshu_send_setup.sh status [--port 18060]
  bash scripts/xiaohongshu_send_setup.sh paths

Environment:
  XHS_HOME      默认: <workspace>/xiaohongshu-send
  XHS_PORT      默认: 18060
  COOKIES_PATH  默认: <XHS_HOME>/data/cookies.json
  XHS_ROD_OPTIONS 默认: dir=<XHS_HOME>/profile
  XHS_PROXY     可选，代理地址，例如: http://user:pass@host:port
EOF
}

log() {
  printf '[xhs] %s\n' "$1"
}

fatal() {
  printf '[xhs][error] %s\n' "$1" >&2
  exit 1
}

ensure_cmd() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || fatal "缺少命令: ${cmd}"
}

ensure_dirs() {
  mkdir -p "${BIN_DIR}" "${DATA_DIR}" "${LOG_DIR}" "${RUN_DIR}" "${PROFILE_DIR}"
  ensure_private_permissions
}

ensure_private_permissions() {
  chmod 700 "${XHS_HOME}" "${DATA_DIR}" "${LOG_DIR}" "${RUN_DIR}" "${PROFILE_DIR}" 2>/dev/null || true
  chmod 600 "${PID_FILE}" "${MCP_LOG}" "${COOKIE_BACKUP_FILE}" 2>/dev/null || true
  local cpath
  cpath="$(cookies_path)"
  chmod 600 "${cpath}" 2>/dev/null || true
}

validate_port() {
  local port="$1"
  [[ "${port}" =~ ^[0-9]+$ ]] || fatal "端口必须是数字: ${port}"
  (( port >= 1 && port <= 65535 )) || fatal "端口范围非法: ${port}"
}

validate_bool() {
  local name="$1"
  local value="$2"
  case "${value}" in
    true|false) ;;
    *)
      fatal "${name} 只能是 true 或 false，当前: ${value}"
      ;;
  esac
}

cookies_path() {
  if [[ -n "${COOKIES_PATH:-}" ]]; then
    echo "${COOKIES_PATH}"
  else
    echo "${DATA_DIR}/cookies.json"
  fi
}

rod_options() {
  if [[ -n "${XHS_ROD_OPTIONS:-}" ]]; then
    echo "${XHS_ROD_OPTIONS}"
  else
    echo "dir=${PROFILE_DIR}"
  fi
}

sync_cookie_store() {
  ensure_dirs

  local primary legacy
  primary="$(cookies_path)"
  legacy="${TMP_COOKIE_PATH}"

  mkdir -p "$(dirname "${primary}")"

  # upstream 会优先读取 /tmp/cookies.json；这里统一到 primary，避免会话漂移。
  if [[ -f "${legacy}" && ! -L "${legacy}" ]]; then
    if [[ ! -f "${primary}" || "${legacy}" -nt "${primary}" ]]; then
      cp -f "${legacy}" "${primary}"
    fi
    rm -f "${legacy}"
  fi

  if [[ -L "${legacy}" ]]; then
    local legacy_target
    legacy_target="$(readlink "${legacy}" || true)"
    if [[ "${legacy_target}" != "${primary}" ]]; then
      rm -f "${legacy}"
    fi
  fi

  if [[ ! -e "${legacy}" ]]; then
    ln -s "${primary}" "${legacy}" 2>/dev/null || true
  fi

  if [[ ! -f "${primary}" && -f "${COOKIE_BACKUP_FILE}" ]]; then
    cp -f "${COOKIE_BACKUP_FILE}" "${primary}"
  fi

  if [[ -s "${primary}" ]]; then
    cp -f "${primary}" "${COOKIE_BACKUP_FILE}"
  fi
  ensure_private_permissions
}

print_cookie_debug() {
  local primary
  primary="$(cookies_path)"
  if [[ -f "${primary}" ]]; then
    log "cookies 文件: ${primary} ($(wc -c < "${primary}") bytes)"
  else
    log "cookies 文件不存在: ${primary}"
  fi
  if [[ -f "${COOKIE_BACKUP_FILE}" ]]; then
    log "cookies 备份: ${COOKIE_BACKUP_FILE} ($(wc -c < "${COOKIE_BACKUP_FILE}") bytes)"
  else
    log "cookies 备份不存在: ${COOKIE_BACKUP_FILE}"
  fi
  if [[ -L "${TMP_COOKIE_PATH}" ]]; then
    log "/tmp/cookies.json -> $(readlink "${TMP_COOKIE_PATH}")"
  elif [[ -f "${TMP_COOKIE_PATH}" ]]; then
    log "/tmp/cookies.json 存在（普通文件，建议检查来源）"
  else
    log "/tmp/cookies.json 不存在"
  fi
}

detect_asset_name() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "${os}:${arch}" in
    Darwin:arm64)
      echo "xiaohongshu-mcp-darwin-arm64.tar.gz"
      ;;
    Darwin:x86_64)
      echo "xiaohongshu-mcp-darwin-amd64.tar.gz"
      ;;
    Linux:x86_64)
      echo "xiaohongshu-mcp-linux-amd64.tar.gz"
      ;;
    Linux:aarch64|Linux:arm64)
      echo "xiaohongshu-mcp-linux-arm64.tar.gz"
      ;;
    MINGW64_NT*:x86_64|MSYS_NT*:x86_64|CYGWIN_NT*:x86_64)
      echo "xiaohongshu-mcp-windows-amd64.zip"
      ;;
    *)
      fatal "不支持的平台: ${os}/${arch}"
      ;;
  esac
}

extract_release() {
  local archive="$1"
  local outdir="$2"

  mkdir -p "${outdir}"
  case "${archive}" in
    *.tar.gz)
      tar -xzf "${archive}" -C "${outdir}"
      ;;
    *.zip)
      ensure_cmd unzip
      unzip -q "${archive}" -d "${outdir}"
      ;;
    *)
      fatal "未知压缩格式: ${archive}"
      ;;
  esac
}

setup_release() {
  ensure_cmd curl
  ensure_cmd jq
  ensure_cmd tar

  ensure_dirs

  local asset release_json tag asset_url tmpdir archive extract_dir mcp_src login_src
  asset="$(detect_asset_name)"

  release_json="$(curl -fsSL "${REPO_API_URL}")"
  tag="$(jq -r '.tag_name // empty' <<<"${release_json}")"
  [[ -n "${tag}" ]] || fatal "无法读取 release tag"

  asset_url="$(
    jq -r --arg name "${asset}" '.assets[] | select(.name == $name) | .browser_download_url' <<<"${release_json}"
  )"
  [[ -n "${asset_url}" ]] || fatal "release 中未找到资产: ${asset}"

  tmpdir="$(mktemp -d)"
  archive="${tmpdir}/${asset}"
  extract_dir="${tmpdir}/extract"

  log "下载 ${tag}: ${asset}"
  curl -fL "${asset_url}" -o "${archive}"
  extract_release "${archive}" "${extract_dir}"

  mcp_src="$(find "${extract_dir}" -type f -name 'xiaohongshu-mcp-*' | head -n 1)"
  login_src="$(find "${extract_dir}" -type f -name 'xiaohongshu-login-*' | head -n 1)"

  [[ -n "${mcp_src}" ]] || fatal "压缩包中未找到 xiaohongshu-mcp 可执行文件"
  [[ -n "${login_src}" ]] || fatal "压缩包中未找到 xiaohongshu-login 可执行文件"

  cp "${mcp_src}" "${BIN_DIR}/xiaohongshu-mcp"
  cp "${login_src}" "${BIN_DIR}/xiaohongshu-login"
  chmod +x "${BIN_DIR}/xiaohongshu-mcp" "${BIN_DIR}/xiaohongshu-login"

  {
    echo "release_tag=${tag}"
    echo "asset=${asset}"
    echo "installed_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } > "${XHS_HOME}/release.txt"
  chmod 600 "${XHS_HOME}/release.txt" 2>/dev/null || true

  rm -rf "${tmpdir}"

  log "安装完成"
  log "mcp: ${BIN_DIR}/xiaohongshu-mcp"
  log "login: ${BIN_DIR}/xiaohongshu-login"
  log "cookies: $(cookies_path)"
}

assert_binaries() {
  [[ -x "${BIN_DIR}/xiaohongshu-mcp" ]] || fatal "缺少可执行文件: ${BIN_DIR}/xiaohongshu-mcp，先运行 setup"
  [[ -x "${BIN_DIR}/xiaohongshu-login" ]] || fatal "缺少可执行文件: ${BIN_DIR}/xiaohongshu-login，先运行 setup"
}

login_once() {
  assert_binaries
  ensure_dirs
  sync_cookie_store

  local browser_bin=""
  local rod_opt
  rod_opt="$(rod_options)"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --browser-bin)
        browser_bin="${2:-}"
        shift 2
        ;;
      --rod)
        rod_opt="${2:-}"
        shift 2
        ;;
      *)
        fatal "未知参数: $1"
        ;;
    esac
  done

  local cmd=("${BIN_DIR}/xiaohongshu-login")
  if [[ -n "${browser_bin}" ]]; then
    cmd+=("-bin" "${browser_bin}")
  fi
  if [[ -n "${rod_opt}" ]]; then
    cmd+=("-rod" "${rod_opt}")
  fi

  log "启动登录流程（会弹浏览器，扫码后自动保存 cookies）"
  if [[ -n "${rod_opt}" ]]; then
    log "使用 rod 选项: ${rod_opt}"
  fi
  (
    export COOKIES_PATH="$(cookies_path)"
    exec "${cmd[@]}"
  )
  sync_cookie_store
}

is_running() {
  if [[ -f "${PID_FILE}" ]]; then
    local pid
    pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      return 0
    fi
    rm -f "${PID_FILE}"
  fi
  return 1
}

http_alive() {
  local port="$1"
  curl -fsS "http://127.0.0.1:${port}/health" >/dev/null 2>&1
}

start_server() {
  assert_binaries
  ensure_dirs
  sync_cookie_store

  local port="${DEFAULT_PORT}"
  local headless="true"
  local browser_bin=""
  local rod_opt
  rod_opt="$(rod_options)"
  local proxy="${XHS_PROXY:-}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --port)
        port="${2:-}"
        shift 2
        ;;
      --headless)
        headless="${2:-}"
        shift 2
        ;;
      --browser-bin)
        browser_bin="${2:-}"
        shift 2
        ;;
      --rod)
        rod_opt="${2:-}"
        shift 2
        ;;
      --proxy)
        proxy="${2:-}"
        shift 2
        ;;
      *)
        fatal "未知参数: $1"
        ;;
    esac
  done

  if is_running; then
    log "MCP 服务已在运行（PID: $(cat "${PID_FILE}")）"
    return 0
  fi
  if http_alive "${port}"; then
    log "检测到端口 ${port} 已有可用 MCP 服务（PID 文件未接管），跳过重复启动"
    return 0
  fi

  validate_port "${port}"
  validate_bool "headless" "${headless}"

  local cmd=("${BIN_DIR}/xiaohongshu-mcp" "-port" ":${port}" "-headless=${headless}")
  if [[ -n "${browser_bin}" ]]; then
    cmd+=("-bin" "${browser_bin}")
  fi
  if [[ -n "${rod_opt}" ]]; then
    cmd+=("-rod" "${rod_opt}")
  fi

  log "启动 MCP 服务，端口: ${port}，headless: ${headless}"
  if [[ -n "${rod_opt}" ]]; then
    log "使用 rod 选项: ${rod_opt}"
  fi
  (
    export COOKIES_PATH="$(cookies_path)"
    if [[ -n "${proxy}" ]]; then
      export XHS_PROXY="${proxy}"
    fi
    nohup "${cmd[@]}" > "${MCP_LOG}" 2>&1 &
    echo "$!" > "${PID_FILE}"
  )
  ensure_private_permissions

  sleep 2

  local health_url="http://127.0.0.1:${port}/health"
  if curl -fsS "${health_url}" >/dev/null 2>&1; then
    sync_cookie_store
    log "服务已就绪: ${health_url}"
    return 0
  fi

  tail -n 40 "${MCP_LOG}" || true
  fatal "服务启动失败，请检查日志: ${MCP_LOG}"
}

stop_server() {
  if ! is_running; then
    log "MCP 服务未运行"
    rm -f "${PID_FILE}"
    return 0
  fi

  local pid
  pid="$(cat "${PID_FILE}")"
  kill "${pid}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
  rm -f "${PID_FILE}"
  log "已停止 MCP 服务"
}

print_status() {
  local port="${DEFAULT_PORT}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --port)
        port="${2:-}"
        shift 2
        ;;
      *)
        fatal "未知参数: $1"
        ;;
    esac
  done

  validate_port "${port}"

  log "XHS_HOME: ${XHS_HOME}"
  log "COOKIES_PATH: $(cookies_path)"
  sync_cookie_store
  print_cookie_debug
  local base_url="http://127.0.0.1:${port}"
  local healthy="false"
  if http_alive "${port}"; then
    healthy="true"
  fi
  if is_running; then
    log "MCP 进程: running (PID: $(cat "${PID_FILE}"))"
  elif [[ "${healthy}" == "true" ]]; then
    log "MCP 进程: running (HTTP 可达，PID 文件未跟踪)"
  else
    log "MCP 进程: stopped"
  fi

  if [[ "${healthy}" == "true" ]]; then
    log "健康检查: ${base_url}/health"
    curl -fsS "${base_url}/health"
    echo
    log "登录状态: ${base_url}/api/v1/login/status"
    curl -fsS "${base_url}/api/v1/login/status"
    echo
  else
    log "HTTP 服务不可达: ${base_url}"
  fi
}

print_paths() {
  ensure_dirs
  cat <<EOF
XHS_HOME=${XHS_HOME}
BIN_DIR=${BIN_DIR}
DATA_DIR=${DATA_DIR}
LOG_DIR=${LOG_DIR}
RUN_DIR=${RUN_DIR}
PROFILE_DIR=${PROFILE_DIR}
COOKIES_PATH=$(cookies_path)
COOKIE_BACKUP_FILE=${COOKIE_BACKUP_FILE}
EOF
}

main() {
  local cmd="${1:-}"
  if [[ -z "${cmd}" ]]; then
    usage
    exit 1
  fi
  shift || true

  case "${cmd}" in
    setup)
      setup_release "$@"
      ;;
    login)
      login_once "$@"
      ;;
    start)
      start_server "$@"
      ;;
    stop)
      stop_server "$@"
      ;;
    status)
      print_status "$@"
      ;;
    paths)
      print_paths
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      fatal "未知命令: ${cmd}"
      ;;
  esac
}

main "$@"
