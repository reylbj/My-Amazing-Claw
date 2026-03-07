#!/usr/bin/env bash
# OpenClaw 一站式体检脚本
# 用途：
# 1) 检查运行环境与关键脚本
# 2) 检查本地技能库配置
# 3) 检查 Obsidian OpenClaw配置 软链接是否正确
#
# 用法：
#   bash scripts/doctor.sh
#   bash scripts/doctor.sh --vault "/path/to/ObsidianVault"
#   bash scripts/doctor.sh --vault "/path/to/ObsidianVault" --workspace "/path/to/openclaw-workspace"

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

ok_count=0
warn_count=0
err_count=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE="$DEFAULT_WORKSPACE"
VAULT=""

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_ok() { echo -e "${GREEN}✅ $1${NC}"; ok_count=$((ok_count + 1)); }
print_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; warn_count=$((warn_count + 1)); }
print_err() { echo -e "${RED}❌ $1${NC}"; err_count=$((err_count + 1)); }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault)
      VAULT="${2:-}"
      shift 2
      ;;
    --workspace)
      WORKSPACE="${2:-}"
      shift 2
      ;;
    -h|--help)
      cat << 'EOF'
OpenClaw 体检脚本

参数:
  --vault PATH        Obsidian Vault 路径（可选，不传则仅做环境与技能库检查）
  --workspace PATH    OpenClaw 工作区路径（可选，默认当前仓库）
EOF
      exit 0
      ;;
    *)
      print_err "未知参数: $1"
      exit 1
      ;;
  esac
done

check_cmd() {
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    print_ok "命令可用: $cmd"
  else
    print_warn "命令缺失: $cmd"
  fi
}

check_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    print_ok "文件存在: $path"
  else
    print_err "文件缺失: $path"
  fi
}

check_env() {
  local name="$1"
  if [[ -n "${!name:-}" ]]; then
    print_ok "环境变量已设置: $name"
  else
    print_warn "环境变量未设置: $name"
  fi
}

check_claude_api_key() {
  local cfg="$HOME/.openclaw/openclaw.json"
  if [[ -n "${CLAUDE_API_KEY:-}" ]]; then
    print_ok "已设置 CLAUDE_API_KEY（环境变量）"
    return
  fi

  if [[ -f "$cfg" ]] && rg -q '"api123"\s*:' "$cfg" && rg -q '"apiKey"\s*:\s*"' "$cfg"; then
    print_ok "已在 ~/.openclaw/openclaw.json 检测到 Claude 提供商 API Key 配置"
    return
  fi

  print_warn "未检测到 Claude API Key（可设置 CLAUDE_API_KEY 或在 openclaw.json 中配置 provider apiKey）"
}

check_gateway_token() {
  local cfg="$HOME/.openclaw/openclaw.json"
  if [[ -n "${OPENCLAW_AUTH_TOKEN:-}" ]]; then
    print_ok "已设置 OPENCLAW_AUTH_TOKEN（环境变量）"
    return
  fi

  if [[ -f "$cfg" ]] && rg -q '"gateway"\s*:' "$cfg" && rg -q '"token"\s*:\s*"' "$cfg"; then
    print_ok "已在 ~/.openclaw/openclaw.json 检测到 gateway token 配置"
    return
  fi

  print_warn "未检测到 gateway token（可设置 OPENCLAW_AUTH_TOKEN 或在 openclaw.json 中配置）"
}

resolve_vault_candidates() {
  local candidates=()
  local icloud_root="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents"

  if [[ -d "$icloud_root" ]]; then
    while IFS= read -r path; do
      candidates+=("$path")
    done < <(find "$icloud_root" -maxdepth 3 -type d -name ".obsidian" 2>/dev/null | sed 's#/.obsidian$##')
  fi

  if [[ -d "$HOME/Desktop" ]]; then
    while IFS= read -r path; do
      candidates+=("$path")
    done < <(find "$HOME/Desktop" -maxdepth 5 -type d -name ".obsidian" 2>/dev/null | sed 's#/.obsidian$##')
  fi

  if [[ -d "$HOME/Documents" ]]; then
    while IFS= read -r path; do
      candidates+=("$path")
    done < <(find "$HOME/Documents" -maxdepth 5 -type d -name ".obsidian" 2>/dev/null | sed 's#/.obsidian$##')
  fi

  # 去重输出
  if [[ "${#candidates[@]}" -gt 0 ]]; then
    printf "%s\n" "${candidates[@]}" | awk 'NF && !seen[$0]++'
  fi
}

check_workspace() {
  print_info "检查工作区: $WORKSPACE"
  if [[ ! -d "$WORKSPACE" ]]; then
    print_err "工作区不存在: $WORKSPACE"
    return
  fi
  print_ok "工作区可访问"

  check_file "$WORKSPACE/SKILLS.md"
  check_file "$WORKSPACE/AGENTS.md"
  check_file "$WORKSPACE/SOUL.md"
  check_file "$WORKSPACE/scripts/setup_obsidian_bridge.sh"
  check_file "$WORKSPACE/scripts/wechat_article_to_obsidian.py"
  check_file "$WORKSPACE/scripts/wechat_draft.py"
  check_file "$WORKSPACE/scripts/whatsapp_bot.py"
  check_file "$WORKSPACE/scripts/security_baseline.sh"
}

check_skills_library() {
  local skills_file="$WORKSPACE/SKILLS.md"
  if [[ ! -f "$skills_file" ]]; then
    print_err "技能库文档不存在: $skills_file"
    return
  fi

  local skill_count
  skill_count="$(rg -n '^## skill:' "$skills_file" | wc -l | tr -d ' ')"
  if [[ "$skill_count" -gt 0 ]]; then
    print_ok "检测到技能定义数量: $skill_count"
    print_info "技能清单:"
    rg -n '^## skill:' "$skills_file" | sed 's/^/  - /'
  else
    print_warn "未在 SKILLS.md 中检测到 '## skill:' 标题"
  fi
}

check_runtime_skills() {
  local runtime_dir="$HOME/.openclaw/skills"
  if [[ ! -d "$runtime_dir" ]]; then
    print_warn "未找到运行时技能目录: $runtime_dir"
    return
  fi

  print_ok "运行时技能目录存在: $runtime_dir"

  local dir_count
  dir_count="$(find "$runtime_dir" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
  print_info "运行时技能目录数量: $dir_count"

  if [[ "$dir_count" -eq 0 ]]; then
    print_info "运行时技能目录为空（可按需执行 clawhub 安装）"
    return
  fi

  local skill_dir file_count name
  while IFS= read -r skill_dir; do
    [[ -z "$skill_dir" ]] && continue
    name="$(basename "$skill_dir")"
    file_count="$(find "$skill_dir" -maxdepth 2 -type f | wc -l | tr -d ' ')"
    if [[ "$file_count" -gt 0 ]]; then
      print_ok "运行时技能有效: ${name}（文件数: ${file_count}）"
    else
      print_info "运行时技能目录为空: ${name}（可按需补充）"
    fi
  done < <(find "$runtime_dir" -mindepth 1 -maxdepth 1 -type d | sort)
}

check_obsidian_bridge() {
  local vault_path="$1"
  local bridge_dir="$vault_path/OpenClaw配置"

  print_info "检查 Obsidian Vault: $vault_path"
  if [[ ! -d "$vault_path" ]]; then
    print_err "Vault 不存在: $vault_path"
    return
  fi
  print_ok "Vault 存在"

  if [[ -d "$vault_path/.obsidian" ]]; then
    print_ok "检测到 .obsidian 配置目录"
  else
    print_warn "未检测到 .obsidian 目录（可能不是标准 Vault 根目录）"
  fi

  if [[ ! -d "$bridge_dir" ]]; then
    print_err "未找到桥接目录: $bridge_dir"
    print_info "可执行: bash scripts/setup_obsidian_bridge.sh --vault \"$vault_path\" --workspace \"$WORKSPACE\" --skip-install"
    return
  fi
  print_ok "桥接目录存在: $bridge_dir"

  local links=("workspace" "SOUL.md" "AGENTS.md" "SKILLS.md" "TOOLS.md" "HEARTBEAT.md" "USER.md" "IDENTITY.md")
  local item target
  for item in "${links[@]}"; do
    if [[ -L "$bridge_dir/$item" ]]; then
      target="$(readlink "$bridge_dir/$item")"
      if [[ -e "$target" ]]; then
        print_ok "软链接有效: $item -> $target"
      else
        print_err "软链接目标不存在: $item -> $target"
      fi
    elif [[ -e "$bridge_dir/$item" ]]; then
      print_warn "存在同名文件但不是软链接: $bridge_dir/$item"
    else
      print_warn "缺少链接: $bridge_dir/$item"
    fi
  done
}

check_security_baseline() {
  local script="$WORKSPACE/scripts/security_baseline.sh"
  if [[ ! -x "$script" ]]; then
    print_warn "安全基线脚本不可执行: $script"
    return
  fi

  if bash "$script" check; then
    print_ok "安全基线检查通过（无 CRITICAL）"
  else
    local rc=$?
    if [[ "$rc" -eq 2 ]]; then
      print_err "安全基线检查发现 CRITICAL，请先修复后再执行高风险任务"
    else
      print_warn "安全基线检查执行异常（退出码: $rc）"
    fi
  fi
}

check_gateway_runtime() {
  print_info "7) 网关稳定性检查"

  if ! command -v openclaw >/dev/null 2>&1; then
    print_warn "未安装 openclaw，跳过网关检查"
    return
  fi

  local status_text=""
  status_text="$(openclaw gateway status 2>&1 || true)"
  if [[ -z "$status_text" ]]; then
    print_warn "无法获取网关状态（输出为空）"
    return
  fi

  if echo "$status_text" | rg -q "Command: ${HOME}/.npm-global/lib/node_modules/node/bin/node "; then
    print_ok "网关服务已固定到 Node 22 路径"
  elif echo "$status_text" | rg -q "Command: /opt/homebrew/opt/node/bin/node "; then
    print_err "网关服务使用 Homebrew Node（可能漂移到 Node 25），建议执行: bash scripts/gateway_stable_start.sh"
  else
    print_warn "未识别网关 Node 路径，请人工确认 Command 行"
  fi

  if echo "$status_text" | rg -q "RPC probe: ok"; then
    print_ok "RPC probe: ok"
  else
    print_warn "RPC probe 未通过（可能为瞬时状态），建议执行: bash scripts/gateway_stable_start.sh"
  fi
}

main() {
  print_info "开始 OpenClaw 体检..."
  echo ""

  print_info "1) 基础命令检查"
  check_cmd python3
  check_cmd bash
  check_cmd rg
  check_cmd npx
  check_cmd openclaw
  echo ""

  print_info "2) 工作区与脚本检查"
  check_workspace
  echo ""

  print_info "3) 关键环境变量检查"
  check_claude_api_key
  check_env WECHAT_APPID
  check_env WECHAT_APPSECRET
  check_gateway_token
  echo ""

  print_info "4) 技能库检查"
  check_skills_library
  check_runtime_skills
  echo ""

  print_info "5) Obsidian 配置检查"
  if [[ -n "$VAULT" ]]; then
    check_obsidian_bridge "$VAULT"
  else
    print_warn "未传 --vault，尝试自动发现 Vault..."
    local found=0
    while IFS= read -r candidate; do
      [[ -z "$candidate" ]] && continue
      found=1
      check_obsidian_bridge "$candidate"
    done < <(resolve_vault_candidates)
    if [[ "$found" -eq 0 ]]; then
      print_warn "未自动发现 Vault，请手动传入 --vault"
    fi
  fi
  echo ""

  print_info "6) 安全基线检查"
  check_security_baseline
  echo ""

  check_gateway_runtime
  echo ""

  print_info "体检完成: ✅ $ok_count | ⚠️ $warn_count | ❌ $err_count"
  if [[ "$err_count" -gt 0 ]]; then
    exit 2
  fi
}

main "$@"
