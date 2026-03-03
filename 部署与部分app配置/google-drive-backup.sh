#!/bin/bash

# Google Drive 自动备份脚本
# 用于备份 OpenClaw 配置文件和重要数据到 Google Drive

set -e

# 配置变量
BACKUP_NAME="openclaw-backup-$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="/tmp/${BACKUP_NAME}"
RCLONE_REMOTE="gdrive"
REMOTE_PATH="OpenClaw-Backups"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== OpenClaw Google Drive 备份工具 ===${NC}"
echo "备份时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查 rclone 是否已安装
if ! command -v rclone &> /dev/null; then
    echo -e "${RED}错误: rclone 未安装${NC}"
    echo "请先运行: curl https://rclone.org/install.sh | sudo bash"
    exit 1
fi

# 检查 rclone 配置
if ! rclone listremotes | grep -q "^${RCLONE_REMOTE}:$"; then
    echo -e "${YELLOW}警告: rclone 远程 '${RCLONE_REMOTE}' 未配置${NC}"
    echo "请先运行: rclone config"
    echo "选择 'Google Drive' 并按照提示完成配置"
    exit 1
fi

# 创建临时备份目录
echo -e "${GREEN}[1/5] 创建备份目录...${NC}"
mkdir -p "${BACKUP_DIR}"

# 备份 OpenClaw 配置文件
echo -e "${GREEN}[2/5] 备份配置文件...${NC}"
if [ -d "$HOME/.openclaw" ]; then
    cp -r "$HOME/.openclaw" "${BACKUP_DIR}/openclaw-config"
    echo "  ✓ 已备份 ~/.openclaw"
else
    echo -e "${YELLOW}  ⚠ ~/.openclaw 目录不存在${NC}"
fi

# 备份工作区
echo -e "${GREEN}[3/5] 备份工作区...${NC}"
WORKSPACE_DIR="$HOME/Desktop/家养小龙虾🦞/openclaw-workspace"
if [ -d "${WORKSPACE_DIR}" ]; then
    cp -r "${WORKSPACE_DIR}" "${BACKUP_DIR}/openclaw-workspace"
    echo "  ✓ 已备份工作区"
else
    echo -e "${YELLOW}  ⚠ 工作区目录不存在${NC}"
fi

# 创建备份信息文件
echo -e "${GREEN}[4/5] 创建备份信息...${NC}"
cat > "${BACKUP_DIR}/backup-info.txt" << EOF
OpenClaw 备份信息
================

备份时间: $(date '+%Y-%m-%d %H:%M:%S')
主机名: $(hostname)
用户: $(whoami)
系统: $(uname -s) $(uname -r)
OpenClaw 版本: $(openclaw --version 2>/dev/null || echo "未知")

备份内容:
- OpenClaw 配置目录 (~/.openclaw)
- 工作区目录 (openclaw-workspace)
- 配置文件和会话数据

恢复方法:
1. 解压备份文件
2. 复制 openclaw-config 到 ~/.openclaw
3. 复制 openclaw-workspace 到目标位置
4. 运行 openclaw gateway restart
EOF

echo "  ✓ 已创建备份信息文件"

# 压缩备份
echo -e "${GREEN}[5/5] 压缩并上传到 Google Drive...${NC}"
cd /tmp
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
echo "  ✓ 已压缩备份文件"

# 上传到 Google Drive
echo "  → 正在上传到 Google Drive..."
rclone copy "${BACKUP_NAME}.tar.gz" "${RCLONE_REMOTE}:${REMOTE_PATH}/" --progress

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ 上传成功！${NC}"
    echo ""
    echo -e "${GREEN}备份完成！${NC}"
    echo "备份文件: ${BACKUP_NAME}.tar.gz"
    echo "远程路径: ${RCLONE_REMOTE}:${REMOTE_PATH}/${BACKUP_NAME}.tar.gz"

    # 清理本地临时文件
    rm -rf "${BACKUP_DIR}"
    rm -f "${BACKUP_NAME}.tar.gz"
    echo "已清理本地临时文件"
else
    echo -e "${RED}  ✗ 上传失败${NC}"
    echo "本地备份保存在: /tmp/${BACKUP_NAME}.tar.gz"
    exit 1
fi

# 显示 Google Drive 中的备份列表
echo ""
echo -e "${GREEN}=== Google Drive 备份列表 ===${NC}"
rclone ls "${RCLONE_REMOTE}:${REMOTE_PATH}/" | tail -10

echo ""
echo -e "${GREEN}备份任务完成！${NC}"
