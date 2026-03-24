#!/bin/bash
# OpenClaw 一键安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印横幅
print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
   ___                   ____ _
  / _ \ _ __   ___ _ __ / ___| | __ ___      __
 | | | | '_ \ / _ \ '_ \| |   | |/ _` \ \ /\ / /
 | |_| | |_) |  __/ | | | |___| | (_| |\ V  V /
  \___/| .__/ \___|_| |_|\____|_|\__,_| \_/\_/
       |_|

EOF
    echo -e "${GREEN}🦞 OpenClaw 安装向导${NC}"
    echo -e "${GREEN}解放双手，但绝不越过安全底线${NC}"
    echo ""
}

# 打印消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    else
        OS="unknown"
    fi
}

# 检查 Python
check_python() {
    print_step "步骤 1/6: 检查 Python 环境"

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

        if [ "$PYTHON_MAJOR" -gt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; }; then
            print_success "Python $PYTHON_VERSION 已安装"
            return 0
        else
            print_error "Python 版本过低 ($PYTHON_VERSION)，需要 3.8+"
            return 1
        fi
    else
        print_error "未找到 Python 3"
        print_info "请访问 https://www.python.org/downloads/ 安装 Python 3.8+"
        return 1
    fi
}

# 安装依赖
install_dependencies() {
    print_step "步骤 2/6: 安装依赖包"

    print_info "检查 pip..."
    if ! command -v pip3 &> /dev/null; then
        print_warning "pip3 未找到，尝试安装..."
        python3 -m ensurepip --upgrade
    fi

    print_info "安装 PyYAML..."
    if python3 -c "import yaml" 2>/dev/null; then
        print_success "PyYAML 已安装"
    else
        pip3 install pyyaml --quiet --user
        print_success "PyYAML 安装完成"
    fi
}

# 创建目录结构
create_directories() {
    print_step "步骤 3/6: 创建目录结构"

    OPENCLAW_HOME="$HOME/.openclaw"

    directories=(
        "$OPENCLAW_HOME/config"
        "$OPENCLAW_HOME/logs"
        "$OPENCLAW_HOME/state"
        "$OPENCLAW_HOME/reports/daily"
        "$OPENCLAW_HOME/reports/weekly"
        "$OPENCLAW_HOME/cache"
        "$OPENCLAW_HOME/backups"
    )

    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_info "创建: $dir"
        fi
    done

    print_success "目录结构创建完成"
}

# 复制配置文件
copy_configs() {
    print_step "步骤 4/6: 配置文件设置"

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
    OPENCLAW_HOME="$HOME/.openclaw"

    # 复制 API 配置
    if [ ! -f "$OPENCLAW_HOME/config/api_config.yaml" ]; then
        if [ -f "$WORKSPACE_DIR/config/api_config.yaml" ]; then
            cp "$WORKSPACE_DIR/config/api_config.yaml" "$OPENCLAW_HOME/config/"
            print_success "API 配置文件已复制"
        fi
    else
        print_info "API 配置文件已存在，跳过"
    fi

    # 复制 HEARTBEAT
    if [ ! -f "$OPENCLAW_HOME/config/HEARTBEAT.md" ]; then
        if [ -f "$WORKSPACE_DIR/HEARTBEAT.md" ]; then
            cp "$WORKSPACE_DIR/HEARTBEAT.md" "$OPENCLAW_HOME/config/"
            print_success "HEARTBEAT 配置已复制"
        fi
    else
        print_info "HEARTBEAT 配置已存在，跳过"
    fi
}

# 设置 API 密钥
setup_api_key() {
    print_step "步骤 5/6: 设置 API 密钥"

    API_KEY_VALUE="${CLAUDE_API_KEY:-${GEMINI_API_KEY:-}}"
    API_KEY_NAME=""
    if [ -n "${CLAUDE_API_KEY:-}" ]; then
        API_KEY_NAME="CLAUDE_API_KEY"
    elif [ -n "${GEMINI_API_KEY:-}" ]; then
        API_KEY_NAME="GEMINI_API_KEY"
    fi

    if [ -n "$API_KEY_VALUE" ]; then
        MASKED_KEY="${API_KEY_VALUE:0:8}...${API_KEY_VALUE: -4}"
        print_success "API 密钥已设置 (${API_KEY_NAME}): $MASKED_KEY"
        return 0
    fi

    print_warning "未检测到 CLAUDE_API_KEY 环境变量"
    echo ""
    echo "请选择设置方式："
    echo "  1) 现在输入 API 密钥（临时，仅本次会话）"
    echo "  2) 稍后手动设置"
    echo ""
    read -p "请选择 [1/2]: " choice

    case $choice in
        1)
            echo ""
            read -s -p "请输入 Claude API 密钥: " api_key
            echo ""
            if [ -n "$api_key" ]; then
                export CLAUDE_API_KEY="$api_key"
                print_success "API 密钥已设置（临时）"
                echo ""
                print_info "要永久设置，请手动把占位符替换成真实值后写入 shell 配置文件："

                if [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
                    echo "  echo 'export CLAUDE_API_KEY=\"your-api-key-here\"' >> ~/.zshrc"
                    echo "  source ~/.zshrc"
                else
                    echo "  echo 'export CLAUDE_API_KEY=\"your-api-key-here\"' >> ~/.bashrc"
                    echo "  source ~/.bashrc"
                fi
            fi
            ;;
        2)
            print_info "请稍后手动设置 API 密钥"
            ;;
    esac
}

# 测试安装
test_installation() {
    print_step "步骤 6/6: 测试安装"

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    print_info "测试配额监控脚本..."
    if python3 "$SCRIPT_DIR/quota_monitor.py" --status 2>/dev/null; then
        print_success "配额监控脚本正常"
    else
        print_warning "配额监控脚本测试失败（可能是正常的，如果还未使用）"
    fi

    print_info "测试智能路由脚本..."
    if python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from smart_router import SmartRouter; print('OK')" 2>/dev/null | grep -q "OK"; then
        print_success "智能路由脚本正常"
    else
        print_warning "智能路由脚本测试失败"
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 OpenClaw 安装完成！${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    print_info "下一步操作："
    echo ""
    echo "1. 设置 API 密钥（如果还未设置）："
    echo "   export CLAUDE_API_KEY='your-api-key-here'"
    echo ""
    echo "2. 查看配额状态："
    echo "   ./scripts/openclaw.sh status"
    echo ""
    echo "3. 运行示例："
    echo "   python3 examples/basic_usage.py"
    echo ""
    echo "4. 查看文档："
    echo "   cat README.md"
    echo "   cat QUICK_REFERENCE.md"
    echo ""

    print_info "常用命令："
    echo "   ./scripts/openclaw.sh help      # 查看帮助"
    echo "   ./scripts/openclaw.sh status    # 查看配额"
    echo "   ./scripts/openclaw.sh report    # 生成报告"
    echo ""

    print_info "配置文件位置："
    echo "   ~/.openclaw/config/api_config.yaml    # API 配置"
    echo "   ~/.openclaw/config/HEARTBEAT.md       # 安全约束"
    echo ""

    print_success "祝使用愉快！🦞"
    echo ""
}

# 主函数
main() {
    print_banner

    # 检测操作系统
    detect_os
    print_info "操作系统: $OS"

    # 执行安装步骤
    if ! check_python; then
        print_error "安装失败：Python 环境不满足要求"
        exit 1
    fi

    install_dependencies
    create_directories
    copy_configs
    setup_api_key
    test_installation
    show_completion
}

# 运行主函数
main
