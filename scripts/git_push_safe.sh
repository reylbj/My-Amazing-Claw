#!/bin/bash
# Git Push Safe - 绕过中文路径mmap问题

set -e

REPO_DIR="/Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace"
TEMP_DIR="/tmp/openclaw-git-safe-$$"

echo "=== Git Push Safe - 绕过中文路径问题 ==="
echo ""

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
git --git-dir="$TEMP_DIR/.git" --work-tree="$REPO_DIR" push origin main

# 4. 同步.git回原目录
echo "4. 同步.git回原目录..."
rsync -a --delete "$TEMP_DIR/.git/" "$REPO_DIR/.git/"

# 5. 清理临时目录
echo "5. 清理临时目录..."
rm -rf "$TEMP_DIR"

echo ""
echo "✅ Git push 完成！"
