#!/bin/bash

# WhatsApp 配置脚本
# 使用方法：在终端运行 bash /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置/whatsapp-setup.sh

echo "=========================================="
echo "OpenClaw WhatsApp 配置向导"
echo "=========================================="
echo ""
echo "步骤说明："
echo "1. 运行配置命令后会生成二维码"
echo "2. 用手机打开 WhatsApp"
echo "3. 点击 设置 -> 已连接的设备 -> 关联设备"
echo "4. 扫描终端显示的二维码"
echo "5. 在手机上确认关联"
echo "6. 输入你的手机号（国际格式，如：+8613800138000）"
echo ""
echo "按回车键开始配置..."
read

# 设置PATH
export PATH=~/.npm-global/bin:$PATH

# 启动配置
openclaw configure
