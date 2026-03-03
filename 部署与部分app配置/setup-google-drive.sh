#!/bin/bash

# Google Drive 配置向导
# 帮助用户快速配置 rclone 连接到 Google Drive

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Google Drive 配置向导 ===${NC}"
echo ""
echo "本向导将帮助你配置 rclone 连接到 Google Drive"
echo ""

# 检查 rclone 是否已安装
if ! command -v rclone &> /dev/null; then
    echo -e "${YELLOW}错误: rclone 未安装${NC}"
    exit 1
fi

echo -e "${BLUE}步骤 1/3: 启动 rclone 配置${NC}"
echo "即将打开 rclone 配置向导..."
echo ""
echo "请按照以下步骤操作："
echo "  1. 选择 'n' (New remote)"
echo "  2. 输入名称: gdrive"
echo "  3. 选择存储类型: drive (Google Drive)"
echo "  4. Client ID 和 Secret: 直接回车使用默认"
echo "  5. Scope: 选择 1 (Full access)"
echo "  6. Root folder ID: 直接回车"
echo "  7. Service account: 直接回车"
echo "  8. Advanced config: 选择 n"
echo "  9. Auto config: 选择 y (会打开浏览器)"
echo "  10. Team drive: 选择 n"
echo "  11. 确认配置: 选择 y"
echo "  12. 退出: 选择 q"
echo ""
read -p "按回车键继续..." dummy

rclone config

echo ""
echo -e "${BLUE}步骤 2/3: 验证配置${NC}"
echo "正在测试 Google Drive 连接..."
echo ""

if rclone lsd gdrive: &> /dev/null; then
    echo -e "${GREEN}✓ 连接成功！${NC}"
    echo ""
    echo "Google Drive 根目录内容："
    rclone lsd gdrive: | head -10
else
    echo -e "${YELLOW}⚠ 连接失败，请检查配置${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}步骤 3/3: 创建备份目录${NC}"
rclone mkdir gdrive:OpenClaw-Backups 2>/dev/null || true
echo -e "${GREEN}✓ 备份目录已创建${NC}"

echo ""
echo -e "${GREEN}=== 配置完成！===${NC}"
echo ""
echo "下一步操作："
echo "  1. 运行备份测试: ./google-drive-backup.sh"
echo "  2. 查看备份文件: rclone ls gdrive:OpenClaw-Backups/"
echo "  3. 配置定时备份: 参考 GoogleDrive配置指南.md"
echo ""
