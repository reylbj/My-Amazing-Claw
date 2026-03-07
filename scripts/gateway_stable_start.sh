#!/usr/bin/env bash
# OpenClaw 网关稳定启动守护脚本
# 目标：不改业务代码，仅通过运行时固化避免 -11 read 再次出现

set -euo pipefail

NODE22_BIN="${HOME}/.npm-global/lib/node_modules/node/bin/node"
OPENCLAW_BIN="${HOME}/.npm-global/bin/openclaw"
EXPECTED_NODE_PATTERN="${HOME}/.npm-global/lib/node_modules/node/bin/node"

info() { printf '[gateway-stable] %s\n' "$1"; }
ok() { printf '[gateway-stable] OK: %s\n' "$1"; }
warn() { printf '[gateway-stable] WARN: %s\n' "$1"; }
err() { printf '[gateway-stable] ERROR: %s\n' "$1" >&2; }

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    err "缺少命令: ${cmd}"
    exit 1
  fi
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

gateway_status() {
  PATH="${HOME}/.npm-global/bin:${PATH}" "$OPENCLAW_BIN" gateway status 2>&1
}

install_force_node22() {
  info "固化 LaunchAgent 到 Node 22 路径"
  PATH="${HOME}/.npm-global/lib/node_modules/node/bin:${HOME}/.npm-global/bin:${PATH}" \
    "$OPENCLAW_BIN" gateway install --force >/dev/null
}

restart_gateway() {
  info "重启网关"
  PATH="${HOME}/.npm-global/bin:${PATH}" "$OPENCLAW_BIN" gateway restart >/dev/null
}

verify_status_or_fail() {
  local status_text="$1"

  if echo "$status_text" | rg -q "Command: ${EXPECTED_NODE_PATTERN} "; then
    ok "网关服务已固定使用 Node 22"
  else
    err "网关服务未固定到 Node 22，当前 Command 如下："
    echo "$status_text" | rg -n '^Command: ' -S || true
    return 1
  fi

  if echo "$status_text" | rg -q 'RPC probe: ok'; then
    ok "RPC probe: ok"
  else
    err "RPC probe 未通过"
    echo "$status_text" | rg -n 'RPC probe|gateway closed|Runtime:|Command:' -S || true
    return 1
  fi
}

main() {
  need_cmd rg
  ensure_runtime_prereq

  local before_status after_status
  before_status="$(gateway_status || true)"

  if ! echo "$before_status" | rg -q "Command: ${EXPECTED_NODE_PATTERN} "; then
    warn "检测到网关运行时漂移，执行 install --force 修复"
    install_force_node22
  fi

  restart_gateway
  after_status="$(gateway_status || true)"

  if verify_status_or_fail "$after_status"; then
    ok "稳定启动完成"
    exit 0
  fi

  warn "首次修复后仍异常，执行二次 install+restart"
  install_force_node22
  restart_gateway
  after_status="$(gateway_status || true)"
  verify_status_or_fail "$after_status"
  ok "二次修复成功"
}

main "$@"
