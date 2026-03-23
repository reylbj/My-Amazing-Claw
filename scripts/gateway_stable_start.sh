#!/usr/bin/env bash
# OpenClaw 网关稳定启动守护脚本
# 目标：不改业务代码，仅通过运行时固化避免 -11 read 再次出现

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARDIAN_SCRIPT="${SCRIPT_DIR}/openclaw_guardian.py"
NODE22_BIN="${HOME}/.npm-global/lib/node_modules/node/bin/node"
OPENCLAW_BIN="${HOME}/.npm-global/bin/openclaw"
STABLE_REQUIRED_OK=3
STABLE_MAX_ATTEMPTS=12
STABLE_SLEEP_SEC=2

info() { printf '[gateway-stable] %s\n' "$1"; }
ok() { printf '[gateway-stable] OK: %s\n' "$1"; }
warn() { printf '[gateway-stable] WARN: %s\n' "$1"; }
err() { printf '[gateway-stable] ERROR: %s\n' "$1" >&2; }

has_match() {
  local pattern="$1"
  if command -v rg >/dev/null 2>&1; then
    rg -q -S -- "$pattern"
  else
    grep -Eq -- "$pattern"
  fi
}

show_matches() {
  local pattern="$1"
  if command -v rg >/dev/null 2>&1; then
    rg -n -S -- "$pattern"
  else
    grep -En -- "$pattern"
  fi
}

extract_command_node_path() {
  local status_text="$1"
  echo "$status_text" | sed -n 's/^Command: \([^ ]*\) .*/\1/p' | head -n 1
}

node_path_is_v22() {
  local node_path="$1"
  local version

  if [[ -z "$node_path" || ! -x "$node_path" ]]; then
    return 1
  fi

  version="$("$node_path" -v 2>/dev/null || true)"
  [[ "$version" =~ ^v22\. ]]
}

ensure_runtime_prereq() {
  if [[ ! -x "$NODE22_BIN" ]]; then
    err "未找到 Node 22 运行时: ${NODE22_BIN}"
    err "请先执行: npm install -g node@22"
    exit 1
  fi

  if [[ ! -x "$OPENCLAW_BIN" ]]; then
    err "未找到 openclaw CLI: ${OPENCLAW_BIN}"
    err "请先确认 openclaw 已正确安装到 ~/.npm-global/bin"
    exit 1
  fi
}

repair_local_config() {
  if [[ ! -f "$GUARDIAN_SCRIPT" ]]; then
    warn "未找到本地 guardian 配置修复器，跳过启动前配置归一化"
    return 0
  fi

  info "启动前执行配置归一化"
  python3 "$GUARDIAN_SCRIPT" configure >/dev/null
}

gateway_status() {
  PATH="${HOME}/.npm-global/bin:${PATH}" "$OPENCLAW_BIN" gateway status 2>&1
}

install_force_node22() {
  info "重装 LaunchAgent 并校准到 Node 22"
  PATH="${HOME}/.npm-global/lib/node_modules/node/bin:${HOME}/.npm-global/bin:${PATH}" \
    "$OPENCLAW_BIN" gateway install --force >/dev/null
}

restart_gateway() {
  info "重启网关"
  PATH="${HOME}/.npm-global/bin:${PATH}" "$OPENCLAW_BIN" gateway restart >/dev/null
}

verify_status_or_fail() {
  local status_text="$1"
  local node_path

  if status_has_expected_node22 "$status_text"; then
    node_path="$(extract_command_node_path "$status_text")"
    ok "网关服务已使用 Node 22 (${node_path})"
  else
    err "网关服务未固定到 Node 22，当前 Command 如下："
    echo "$status_text" | rg -n '^Command: ' -S || true
    return 1
  fi

  if status_probe_ok "$status_text"; then
    ok "RPC probe: ok"
  else
    err "RPC probe 未通过"
    echo "$status_text" | rg -n 'RPC probe|Warm-up|gateway closed|Runtime:|Command:' -S || true
    return 1
  fi

  if status_in_warmup "$status_text"; then
    err "网关仍处于 Warm-up，暂不允许新会话"
    return 1
  fi
}

status_has_expected_node22() {
  local status_text="$1"
  local node_path

  node_path="$(extract_command_node_path "$status_text")"
  node_path_is_v22 "$node_path"
}

status_probe_ok() {
  local status_text="$1"
  echo "$status_text" | has_match 'RPC probe: ok'
}

status_in_warmup() {
  local status_text="$1"
  echo "$status_text" | has_match 'Warm-up:'
}

status_missing_service() {
  local status_text="$1"
  echo "$status_text" | has_match 'Service not installed|Service unit not found|Could not find service "ai\.openclaw\.gateway"'
}

dashboard_status() {
  curl -sS -i --max-time 3 http://127.0.0.1:18789/ 2>/dev/null || true
}

dashboard_http_ok() {
  local dashboard_text="$1"
  echo "$dashboard_text" | has_match '^HTTP/1\.[01] 200'
}

dashboard_assets_missing() {
  local dashboard_text="$1"
  echo "$dashboard_text" | has_match 'Control UI assets not found'
}

dashboard_healthy() {
  local dashboard_text="$1"
  dashboard_http_ok "$dashboard_text" && ! dashboard_assets_missing "$dashboard_text"
}

verify_dashboard_or_fail() {
  local dashboard_text

  dashboard_text="$(dashboard_status)"
  if dashboard_healthy "$dashboard_text"; then
    ok "Dashboard 可访问 (http://127.0.0.1:18789/)"
    return 0
  fi

  err "Dashboard 未就绪"
  echo "$dashboard_text" | show_matches 'HTTP/|Control UI assets not found' || true
  return 1
}

probe_until_stable() {
  local attempt=1
  local consecutive_ok=0
  local status_text
  local dashboard_text

  while (( attempt <= STABLE_MAX_ATTEMPTS )); do
    status_text="$(gateway_status || true)"
    dashboard_text="$(dashboard_status)"

    if status_has_expected_node22 "$status_text" && \
      status_probe_ok "$status_text" && \
      ! status_in_warmup "$status_text" && \
      dashboard_healthy "$dashboard_text"; then
      consecutive_ok=$((consecutive_ok + 1))
      info "稳定探针通过 ${consecutive_ok}/${STABLE_REQUIRED_OK}（第${attempt}次）"
      if (( consecutive_ok >= STABLE_REQUIRED_OK )); then
        printf '%s' "$status_text"
        return 0
      fi
    else
      consecutive_ok=0
      warn "网关尚未稳定（第${attempt}次），继续等待"
      echo "$status_text" | show_matches 'RPC probe|Warm-up|gateway closed|Runtime:|Command:' || true
      echo "$dashboard_text" | show_matches 'HTTP/|Control UI assets not found' || true
    fi

    attempt=$((attempt + 1))
    sleep "$STABLE_SLEEP_SEC"
  done

  err "网关在 ${STABLE_MAX_ATTEMPTS} 次探针后仍未稳定"
  return 1
}

main() {
  ensure_runtime_prereq
  repair_local_config

  local before_status after_status
  before_status="$(gateway_status || true)"

  if status_missing_service "$before_status"; then
    warn "检测到网关服务未安装，执行 install --force 修复"
    install_force_node22
    repair_local_config
    before_status="$(gateway_status || true)"
  fi

  if ! status_has_expected_node22 "$before_status"; then
    warn "检测到网关运行时漂移，执行 install --force 修复"
    install_force_node22
    repair_local_config
  fi

  restart_gateway
  if after_status="$(probe_until_stable)"; then
    verify_status_or_fail "$after_status"
    verify_dashboard_or_fail
    ok "稳定启动完成（可安全新建会话）"
    exit 0
  fi

  warn "首次稳定化失败，执行二次 install+restart"
  install_force_node22
  repair_local_config
  restart_gateway
  after_status="$(probe_until_stable)"
  verify_status_or_fail "$after_status"
  verify_dashboard_or_fail
  ok "二次修复成功（可安全新建会话）"
}

main "$@"
