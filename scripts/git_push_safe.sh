#!/bin/bash
# Git Push Safe - 通过临时 .git 工作区规避路径兼容问题

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMP_DIR="/tmp/openclaw-git-safe-$$"
BRANCH="${1:-$(git -C "$REPO_DIR" branch --show-current)}"

cleanup() {
  if [[ -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}

trap cleanup EXIT

echo "=== Git Push Safe - 绕过中文路径问题 ==="
echo ""

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "❌ 未找到仓库 .git 目录: $REPO_DIR"
  exit 1
fi

if [[ -z "$BRANCH" ]]; then
  echo "❌ 未识别到当前分支，请显式传入分支名"
  exit 1
fi

# 1. 创建临时目录
echo "1. 创建临时工作区..."
mkdir -p "$TEMP_DIR"

# 2. 复制.git目录到临时位置
echo "2. 复制.git到临时位置..."
cp -R "$REPO_DIR/.git" "$TEMP_DIR/"

# 3. 在临时目录执行git操作
echo "3. 在临时目录执行git push..."
cd "$TEMP_DIR"

# 设置work-tree指向原目录
git --git-dir="$TEMP_DIR/.git" --work-tree="$REPO_DIR" push origin "$BRANCH"

# 4. 同步.git回原目录
echo "4. 同步.git回原目录..."
rsync -a --delete "$TEMP_DIR/.git/" "$REPO_DIR/.git/"

# 5. 清理临时目录
echo "5. 清理临时目录..."
cleanup

echo ""
echo "✅ Git push 完成！"
