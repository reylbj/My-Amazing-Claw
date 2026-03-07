#!/usr/bin/env bash
# OpenClaw 本地安全基线检查/修复（低侵入）

set -euo pipefail
umask 077

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
CONFIG_FILE="${STATE_DIR}/openclaw.json"
MODE="${1:-check}"

ok_count=0
warn_count=0
err_count=0

info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
ok() { echo -e "${GREEN}✅ $1${NC}"; ok_count=$((ok_count + 1)); }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; warn_count=$((warn_count + 1)); }
err() { echo -e "${RED}❌ $1${NC}"; err_count=$((err_count + 1)); }

usage() {
  cat <<'EOF'
OpenClaw 安全基线脚本

用法:
  bash scripts/security_baseline.sh check   # 仅检查（默认）
  bash scripts/security_baseline.sh fix     # 检查 + 权限自动收敛

检查项:
  - ~/.openclaw/openclaw.json 核心安全项（gateway bind/auth/token）
  - dangerously*/insecure* 配置开启检测
  - 18789 端口监听暴露检测
  - 关键凭证文件权限检测（可在 fix 模式自动修复）
  - 工作区脚本高风险模式快速扫描
EOF
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

perm_of() {
  local p="$1"
  if stat -f '%Lp' "$p" >/dev/null 2>&1; then
    stat -f '%Lp' "$p"
  else
    stat -c '%a' "$p"
  fi
}

resolve_symlink_target() {
  local link_path="$1"
  local raw
  raw="$(readlink "$link_path")"
  if [[ "$raw" = /* ]]; then
    echo "$raw"
  else
    local base
    base="$(cd "$(dirname "$link_path")" && pwd)"
    echo "${base}/${raw}"
  fi
}

check_or_fix_path_perm() {
  local path="$1"
  local wanted="$2"
  local kind="$3"

  [[ -e "$path" ]] || return 0

  if [[ -L "$path" ]]; then
    local target
    target="$(resolve_symlink_target "$path")"
    if [[ -e "$target" ]]; then
      check_or_fix_path_perm "$target" "$wanted" "${kind}(symlink->target)"
      return 0
    fi
    warn "符号链接目标不存在: ${path} -> ${target}"
    return 0
  fi

  local current
  current="$(perm_of "$path")"

  if [[ "$current" -le "$wanted" ]]; then
    ok "权限合规: ${path} (${current})"
    return 0
  fi

  if [[ "$MODE" == "fix" ]]; then
    chmod "$wanted" "$path"
    local fixed
    fixed="$(perm_of "$path")"
    if [[ "$fixed" -le "$wanted" ]]; then
      ok "权限已收敛: ${path} (${current} -> ${fixed})"
    else
      err "权限修复失败: ${path} (当前 ${fixed}, 期望 <= ${wanted})"
    fi
  else
    warn "${kind}权限偏宽: ${path} (${current}, 期望 <= ${wanted})"
  fi
}

check_or_fix_tree_file_perms() {
  local root="$1"
  local wanted="$2"
  [[ -d "$root" ]] || return 0

  local total=0
  local bad=0
  local fixed_bad=0
  local samples=()

  while IFS= read -r f; do
    total=$((total + 1))
    local current
    current="$(perm_of "$f")"
    if [[ "$current" -le "$wanted" ]]; then
      continue
    fi

    bad=$((bad + 1))
    if [[ "${#samples[@]}" -lt 5 ]]; then
      samples+=("${f} (${current})")
    fi

    if [[ "$MODE" == "fix" ]]; then
      chmod "$wanted" "$f"
      local after
      after="$(perm_of "$f")"
      if [[ "$after" -le "$wanted" ]]; then
        fixed_bad=$((fixed_bad + 1))
      fi
    fi
  done < <(find "$root" -type f 2>/dev/null)

  if [[ "$bad" -eq 0 ]]; then
    ok "权限合规: ${root} 下文件 ${total} 个"
    return 0
  fi

  if [[ "$MODE" == "fix" && "$fixed_bad" -eq "$bad" ]]; then
    ok "权限已收敛: ${root} 修复 ${fixed_bad}/${bad} 个文件"
    return 0
  fi

  warn "权限偏宽: ${root} 发现 ${bad}/${total} 个文件超出 ${wanted}"
  local s
  for s in "${samples[@]}"; do
    echo "  - ${s}"
  done
}

json_get() {
  local query="$1"
  if ! has_cmd jq || [[ ! -f "$CONFIG_FILE" ]]; then
    echo ""
    return 0
  fi
  jq -r "${query} // empty" "$CONFIG_FILE" 2>/dev/null || true
}

check_gateway_config() {
  info "1) OpenClaw 配置基线检查"

  if [[ ! -f "$CONFIG_FILE" ]]; then
    warn "未找到配置文件: ${CONFIG_FILE}"
    return 0
  fi
  ok "配置文件存在: ${CONFIG_FILE}"

  if ! has_cmd jq; then
    warn "未安装 jq，跳过 JSON 精细检查"
    return 0
  fi

  local bind auth_mode token
  bind="$(json_get '.gateway.bind')"
  auth_mode="$(json_get '.gateway.auth.mode')"
  token="$(json_get '.gateway.auth.token')"

  if [[ "$bind" == "127.0.0.1" || "$bind" == "localhost" || "$bind" == "::1" || "$bind" == "loopback" ]]; then
    ok "gateway.bind 安全: ${bind}"
  elif [[ -z "$bind" ]]; then
    warn "未读取到 gateway.bind，请人工确认是否仅本地监听"
  else
    err "gateway.bind 非本地地址: ${bind}"
  fi

  if [[ "$auth_mode" == "token" ]]; then
    ok "gateway.auth.mode=token"
  elif [[ -z "$auth_mode" ]]; then
    warn "未读取到 gateway.auth.mode，请人工确认"
  else
    err "gateway.auth.mode 非 token: ${auth_mode}"
  fi

  if [[ -n "$token" ]]; then
    ok "gateway.auth.token 已配置"
  else
    warn "gateway.auth.token 为空（若仅本机使用可接受，远程访问场景不安全）"
  fi

  local dangerous_flags
  dangerous_flags="$(
    jq -r '
      paths(scalars) as $p
      | (getpath($p)) as $v
      | select(
          ($p[-1] | tostring | test("^(dangerously|insecure)"; "i"))
          and ($v == true or $v == "true")
        )
      | $p | map(tostring) | join(".")
    ' "$CONFIG_FILE" 2>/dev/null || true
  )"

  if [[ -n "$dangerous_flags" ]]; then
    err "检测到高风险配置开启:"
    echo "$dangerous_flags" | sed 's/^/  - /'
  else
    ok "未发现 dangerously*/insecure* = true"
  fi
}

check_gateway_port_exposure() {
  info "2) 18789 端口暴露检查"

  local out=""
  if has_cmd lsof; then
    out="$(lsof -nP -iTCP:18789 -sTCP:LISTEN 2>/dev/null || true)"
  elif has_cmd ss; then
    out="$(ss -lnt 2>/dev/null | rg '18789' || true)"
  fi

  if [[ -z "$out" ]]; then
    warn "未检测到 18789 监听（可能未启动，或命令不可用）"
    return 0
  fi

  echo "$out" | sed 's/^/  /'

  if echo "$out" | rg -q '(\*:18789|0\.0\.0\.0:18789|:::18789)'; then
    err "18789 监听在全网地址（*:18789 / 0.0.0.0 / ::）"
  elif echo "$out" | rg -q '(127\.0\.0\.1:18789|localhost:18789|\[::1\]:18789)'; then
    ok "18789 仅本地监听"
  else
    warn "18789 监听地址无法自动判定，请人工确认"
  fi
}

check_sensitive_permissions() {
  info "3) 敏感文件权限检查${MODE:+ (${MODE})}"

  check_or_fix_path_perm "$STATE_DIR" 700 "目录"
  check_or_fix_path_perm "$CONFIG_FILE" 600 "文件"
  check_or_fix_path_perm "$STATE_DIR/devices/paired.json" 600 "文件"
  check_or_fix_path_perm "$STATE_DIR/credentials" 700 "目录"
  check_or_fix_path_perm "$STATE_DIR/identity" 700 "目录"

  check_or_fix_tree_file_perms "$STATE_DIR/credentials" 600
  check_or_fix_tree_file_perms "$STATE_DIR/identity" 600

  local cookie_files=(
    "$WORKSPACE_DIR/xiaohongshu-send/data/cookies.json"
    "$WORKSPACE_DIR/xiaohongshu-send/data/cookies.backup.json"
    "$HOME/xhs_workspace/xiaohongshu-send/data/cookies.json"
    "$HOME/xhs_workspace/xiaohongshu-send/data/cookies.backup.json"
  )

  local cookie_dirs=(
    "$WORKSPACE_DIR/xiaohongshu-send/data"
    "$HOME/xhs_workspace/xiaohongshu-send/data"
  )

  local d
  for d in "${cookie_dirs[@]}"; do
    check_or_fix_path_perm "$d" 700 "目录"
  done

  local f
  for f in "${cookie_files[@]}"; do
    check_or_fix_path_perm "$f" 600 "文件"
  done
}

scan_risky_patterns() {
  info "4) 工作区高风险模式扫描"

  local targets=(
    "$WORKSPACE_DIR/scripts"
    "$WORKSPACE_DIR/小红书笔记技能包/scripts"
  )

  local findings
  findings="$(
    rg -n --no-heading \
      -e 'eval\s+\"\$' \
      -e 'eval\s*\(' \
      -e 'shell=True' \
      -e 'os\.system\(' \
      -e 'subprocess\..*shell=True' \
      -g '!security_baseline.sh' \
      "${targets[@]}" 2>/dev/null || true
  )"

  if [[ -z "$findings" ]]; then
    ok "未发现高风险动态执行模式"
  else
    warn "发现需人工复核的风险模式:"
    echo "$findings" | sed 's/^/  - /'
  fi
}

main() {
  case "$MODE" in
    check|fix)
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 1
      ;;
  esac

  info "开始执行 OpenClaw 安全基线 (${MODE})"
  echo ""

  check_gateway_config
  echo ""
  check_gateway_port_exposure
  echo ""
  check_sensitive_permissions
  echo ""
  scan_risky_patterns
  echo ""

  info "完成: ✅ ${ok_count} | ⚠️ ${warn_count} | ❌ ${err_count}"
  if [[ "${err_count}" -gt 0 ]]; then
    exit 2
  fi
}

main "$@"
