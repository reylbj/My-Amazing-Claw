#!/bin/bash
# OpenClaw 快速启动脚本
# 用于初始化环境、检查配额、启动监控

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置路径
OPENCLAW_HOME="$HOME/.openclaw"
CONFIG_DIR="$OPENCLAW_HOME/config"
LOGS_DIR="$OPENCLAW_HOME/logs"
STATE_DIR="$OPENCLAW_HOME/state"
REPORTS_DIR="$OPENCLAW_HOME/reports"
CACHE_DIR="$OPENCLAW_HOME/cache"
BACKUPS_DIR="$OPENCLAW_HOME/backups"

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

# 打印带颜色的消息
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

# 打印横幅
print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
   ___                   ____ _
  / _ \ _ __   ___ _ __ / ___| | __ ___      __
 | | | | '_ \ / _ \ '_ \| |   | |/ _` \ \ /\ / /
 | |_| | |_) |  __/ | | | |___| | (_| |\ V  V /
  \___/| .__/ \___|_| |_|\____|_|\__,_| \_/\_/
       |_|
EOF
    echo -e "${NC}"
    echo -e "${GREEN}🦞 解放双手，但绝不越过安全底线${NC}"
    echo ""
}

# 检查 Python 环境
check_python() {
    print_info "检查 Python 环境..."

    if ! command -v python3 &> /dev/null; then
        print_error "未找到 Python 3，请先安装 Python 3.8+"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 版本: $PYTHON_VERSION"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖包..."

    # 检查 PyYAML
    if ! python3 -c "import yaml" 2>/dev/null; then
        print_warning "未安装 PyYAML，正在安装..."
        pip3 install pyyaml --quiet --user
    fi

    print_success "依赖检查完成"
}

# 初始化目录结构
init_directories() {
    print_info "初始化目录结构..."

    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$STATE_DIR"
    mkdir -p "$REPORTS_DIR/daily"
    mkdir -p "$REPORTS_DIR/weekly"
    mkdir -p "$CACHE_DIR"
    mkdir -p "$BACKUPS_DIR"

    print_success "目录结构创建完成"
}

# 复制配置文件
setup_config() {
    print_info "设置配置文件..."

    # 复制 API 配置
    if [ ! -f "$CONFIG_DIR/api_config.yaml" ]; then
        if [ -f "$WORKSPACE_DIR/config/api_config.yaml" ]; then
            cp "$WORKSPACE_DIR/config/api_config.yaml" "$CONFIG_DIR/"
            print_success "API 配置文件已复制"
        else
            print_warning "未找到 API 配置文件模板"
        fi
    else
        print_info "API 配置文件已存在，跳过"
    fi

    # 复制 HEARTBEAT 配置
    if [ ! -f "$CONFIG_DIR/HEARTBEAT.md" ]; then
        if [ -f "$WORKSPACE_DIR/HEARTBEAT.md" ]; then
            cp "$WORKSPACE_DIR/HEARTBEAT.md" "$CONFIG_DIR/"
            print_success "HEARTBEAT 配置已复制"
        fi
    fi
}

# 检查 API 密钥
check_api_key() {
    print_info "检查 API 密钥..."

    API_KEY_VALUE="${CLAUDE_API_KEY:-${GEMINI_API_KEY:-}}"
    API_KEY_NAME=""
    if [ -n "${CLAUDE_API_KEY:-}" ]; then
        API_KEY_NAME="CLAUDE_API_KEY"
    elif [ -n "${GEMINI_API_KEY:-}" ]; then
        API_KEY_NAME="GEMINI_API_KEY"
    fi

    if [ -z "$API_KEY_VALUE" ]; then
        print_warning "未设置 CLAUDE_API_KEY 环境变量"
        echo ""
        echo "请设置 API 密钥："
        echo "  export CLAUDE_API_KEY='your-api-key-here'"
        echo ""
        echo "或添加到 ~/.bashrc 或 ~/.zshrc："
        echo "  echo 'export CLAUDE_API_KEY=\"your-api-key-here\"' >> ~/.bashrc"
        echo ""
        return 1
    else
        # 隐藏部分密钥
        MASKED_KEY="${API_KEY_VALUE:0:8}...${API_KEY_VALUE: -4}"
        print_success "API 密钥已设置 (${API_KEY_NAME}): $MASKED_KEY"
    fi
}

# 显示配额状态
show_quota_status() {
    print_info "获取配额状态..."
    echo ""

    if [ -f "$SCRIPT_DIR/quota_monitor.py" ]; then
        python3 "$SCRIPT_DIR/quota_monitor.py" --status
    else
        print_warning "配额监控脚本不存在"
    fi
}

# 生成每日报告
generate_report() {
    print_info "生成每日报告..."

    if [ -f "$SCRIPT_DIR/quota_monitor.py" ]; then
        python3 "$SCRIPT_DIR/quota_monitor.py" --report
    else
        print_warning "配额监控脚本不存在"
    fi
}

# 测试路由器
test_router() {
    print_info "测试智能路由器..."
    echo ""

    if [ -f "$SCRIPT_DIR/smart_router.py" ]; then
        python3 "$SCRIPT_DIR/smart_router.py"
    else
        print_warning "智能路由器脚本不存在"
    fi
}

# 清理旧数据
cleanup() {
    print_info "清理旧数据..."

    # 清理 30 天前的临时文件
    if [ -d "$CACHE_DIR" ]; then
        find "$CACHE_DIR" -type f -mtime +30 -delete 2>/dev/null || true
        print_success "已清理 30 天前的缓存文件"
    fi

    # 清理 90 天前的日志
    if [ -d "$LOGS_DIR" ]; then
        find "$LOGS_DIR" -type f -mtime +90 -delete 2>/dev/null || true
        print_success "已清理 90 天前的日志文件"
    fi
}

# 抓取AI资讯
fetch_ai_news() {
    print_info "抓取今日AI资讯..."
    if [ -f "$SCRIPT_DIR/fetch_ai_news.py" ]; then
        python3 "$SCRIPT_DIR/fetch_ai_news.py"
    else
        print_warning "AI资讯抓取脚本不存在"
    fi
}

# 生成今日选题（抓取资讯后触发）
generate_topics() {
    print_info "生成今日选题..."
    TODAY=$(date +%Y-%m-%d)
    BRIEFING_FILE="$WORKSPACE_DIR/验证输出/ai_briefing_${TODAY}.txt"

    if [ -f "$BRIEFING_FILE" ]; then
        print_success "已有今日资讯简报，可供选题官使用"
        cat "$BRIEFING_FILE"
    else
        print_warning "未找到今日资讯简报，请先运行: $0 news"
    fi
}

# 导入公众号文章到 Obsidian
import_wechat_article() {
    local article_url="${1:-}"
    local vault_path="${2:-}"

    if [ -z "$article_url" ]; then
        print_error "缺少公众号文章链接"
        echo "用法: $0 wx <公众号链接> [ObsidianVault路径]"
        return 1
    fi

    if [ ! -f "$SCRIPT_DIR/wechat_article_to_obsidian.py" ]; then
        print_error "脚本不存在: $SCRIPT_DIR/wechat_article_to_obsidian.py"
        return 1
    fi

    print_info "开始读取公众号文章并保存到 Obsidian..."
    if [ -n "$vault_path" ]; then
        python3 "$SCRIPT_DIR/wechat_article_to_obsidian.py" --url "$article_url" --vault "$vault_path"
    else
        python3 "$SCRIPT_DIR/wechat_article_to_obsidian.py" --url "$article_url"
    fi
}

# 显示帮助信息
show_help() {
    cat << EOF
OpenClaw 管理工具

用法: $0 [命令]

命令:
  init        初始化 OpenClaw 环境
  gateway     稳定启动网关（固化 Node 22 + 重启 + 验活）
  status      显示当前配额状态
  report      生成每日使用报告
  test        测试智能路由器
  security    执行安全基线检查（可选 fix）
  news        抓取今日AI资讯（用于选题）
  topics      显示今日选题简报
  wx          读取公众号文章并保存到 Obsidian
  cleanup     清理旧数据
  check       检查环境和配置
  help        显示此帮助信息

示例:
  $0 init          # 首次使用时初始化环境
  $0 gateway       # 稳定启动网关并验活（推荐日常入口）
  $0 status        # 查看配额使用情况
  $0 report        # 生成今日使用报告
  $0 security      # 执行安全基线检查
  $0 security fix  # 执行检查并收敛关键权限
  $0 wx "https://mp.weixin.qq.com/s?__biz=..." "/Users/a8/Documents/Obsidian Vault"

环境变量:
  CLAUDE_API_KEY   Claude API 密钥（推荐）
  GEMINI_API_KEY   Gemini API 密钥（兼容）

配置文件:
  ~/.openclaw/config/api_config.yaml    API 配置
  ~/.openclaw/config/HEARTBEAT.md       安全约束配置

日志和报告:
  ~/.openclaw/logs/                     日志目录
  ~/.openclaw/reports/                  报告目录
  ~/.openclaw/state/                    状态文件

EOF
}

# 完整检查
full_check() {
    print_banner
    check_python
    check_dependencies
    check_api_key || true
    echo ""
    print_info "环境检查完成"
}

run_security_baseline() {
    local mode="${1:-check}"
    if [[ -x "$SCRIPT_DIR/security_baseline.sh" ]]; then
        bash "$SCRIPT_DIR/security_baseline.sh" "$mode"
    else
        print_warning "安全基线脚本不存在或不可执行: $SCRIPT_DIR/security_baseline.sh"
        return 1
    fi
}

run_gateway_stable_start() {
    local script="$SCRIPT_DIR/gateway_stable_start.sh"
    if [[ -x "$script" ]]; then
        bash "$script"
    else
        print_warning "网关稳定启动脚本不存在或不可执行: $script"
        return 1
    fi
}

# 初始化
init_openclaw() {
    print_banner
    print_info "开始初始化 OpenClaw..."
    echo ""

    check_python
    check_dependencies
    init_directories
    setup_config
    check_api_key || true

    echo ""
    print_success "OpenClaw 初始化完成！"
    echo ""
    print_info "下一步："
    echo "  1. 设置 API 密钥: export CLAUDE_API_KEY='your-key'"
    echo "  2. 查看配额状态: $0 status"
    echo "  3. 查看帮助: $0 help"
    echo ""
}

# 主函数
main() {
    case "${1:-help}" in
        init)
            init_openclaw
            ;;
        status)
            show_quota_status
            ;;
        gateway)
            run_gateway_stable_start
            ;;
        report)
            generate_report
            ;;
        test)
            test_router
            ;;
        security)
            run_security_baseline "${2:-check}"
            ;;
        cleanup)
            cleanup
            ;;
        news)
            fetch_ai_news
            ;;
        topics)
            generate_topics
            ;;
        wx|wechat)
            import_wechat_article "${2:-}" "${3:-}"
            ;;
        check)
            full_check
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
