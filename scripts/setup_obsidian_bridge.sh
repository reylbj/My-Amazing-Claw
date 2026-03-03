#!/usr/bin/env bash
# OpenClaw + Obsidian 半自动联动脚本
# 用法:
#   bash scripts/setup_obsidian_bridge.sh --vault "/path/to/ObsidianVault"
# 可选:
#   --workspace "/path/to/openclaw-workspace"
#   --skip-install

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_ok() { echo -e "${GREEN}✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_err() { echo -e "${RED}❌ $1${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"

VAULT_PATH=""
WORKSPACE_PATH="$DEFAULT_WORKSPACE"
SKIP_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault)
      VAULT_PATH="${2:-}"
      shift 2
      ;;
    --workspace)
      WORKSPACE_PATH="${2:-}"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    -h|--help)
      cat << 'EOF'
OpenClaw + Obsidian 半自动联动脚本

必填:
  --vault PATH         Obsidian 仓库根目录路径

可选:
  --workspace PATH     OpenClaw 工作区路径（默认: 当前仓库）
  --skip-install       跳过 skill 安装，仅创建软链接
EOF
      exit 0
      ;;
    *)
      print_err "未知参数: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$VAULT_PATH" ]]; then
  print_err "缺少 --vault 参数"
  exit 1
fi

if [[ ! -d "$VAULT_PATH" ]]; then
  print_err "Obsidian 仓库目录不存在: $VAULT_PATH"
  exit 1
fi

if [[ ! -d "$WORKSPACE_PATH" ]]; then
  print_err "OpenClaw 工作区不存在: $WORKSPACE_PATH"
  exit 1
fi

TARGET_DIR="$VAULT_PATH/OpenClaw配置"
mkdir -p "$TARGET_DIR"
print_ok "已确保目录存在: $TARGET_DIR"

link_file() {
  local src="$1"
  local dst="$2"
  if [[ -L "$dst" ]]; then
    rm -f "$dst"
  elif [[ -e "$dst" ]]; then
    local backup="${dst}.backup.$(date +%Y%m%d-%H%M%S)"
    mv "$dst" "$backup"
    print_warn "检测到已存在路径，已备份: $dst -> $backup"
  fi
  ln -s "$src" "$dst"
}

# 链接整个 workspace，方便统一访问
link_file "$WORKSPACE_PATH" "$TARGET_DIR/workspace"
print_ok "已创建软链接: $TARGET_DIR/workspace -> $WORKSPACE_PATH"

# 链接核心配置文件，便于在 Obsidian 里直接编辑
for file in SOUL.md AGENTS.md SKILLS.md TOOLS.md HEARTBEAT.md USER.md IDENTITY.md; do
  if [[ -f "$WORKSPACE_PATH/$file" ]]; then
    link_file "$WORKSPACE_PATH/$file" "$TARGET_DIR/$file"
    print_ok "已链接: $file"
  else
    print_warn "未找到文件，已跳过: $WORKSPACE_PATH/$file"
  fi
done

if [[ "$SKIP_INSTALL" -eq 1 ]]; then
  print_info "已跳过 skills 安装（--skip-install）"
  exit 0
fi

if ! command -v npx >/dev/null 2>&1; then
  print_warn "未检测到 npx，跳过 skills 安装"
  exit 0
fi

install_item() {
  local name="$1"
  print_info "安装: $name"
  if npx clawhub@latest install "$name"; then
    print_ok "安装成功: $name"
  elif npx clawhub install "$name"; then
    print_ok "安装成功: $name"
  else
    print_warn "安装失败，请手动检查: $name"
  fi
}

print_info "开始安装基础 skills / 扩展能力..."
install_item "obsidian"
install_item "find-skills"
install_item "proactive-agent-1-2-4"
install_item "https://github.com/runesleo/x-reader"
install_item "https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md"
install_item "https://raw.githubusercontent.com/browserwing/browserwing/main/INSTALL.md"

print_ok "OpenClaw + Obsidian 联动初始化完成"
print_info "建议下一步：在 Obsidian 的 OpenClaw配置 目录中创建或编辑 SOUL.md / AGENTS.md"
