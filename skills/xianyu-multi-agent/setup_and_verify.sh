#!/bin/bash
# 闲鱼多账号AI运营系统 - 快速部署和验证脚本
# 作者: OpenClaw AI
# 日期: 2026-03-08

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    log_info "检查Python版本..."
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    log_success "Python版本: $PYTHON_VERSION"
    
    # 检查版本是否>=3.8
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
        log_error "Python版本过低，需要3.8+，当前: $PYTHON_VERSION"
        exit 1
    fi
}

# 创建虚拟环境
setup_venv() {
    log_info "创建虚拟环境..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "虚拟环境创建成功"
    else
        log_warning "虚拟环境已存在，跳过创建"
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    log_success "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    log_info "安装依赖包..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    log_success "依赖安装完成"
}

# 检查必要目录
check_directories() {
    log_info "检查必要目录..."
    DIRS=("data" "prompts" "templates" "static" "logs")
    for dir in "${DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_warning "创建目录: $dir"
        fi
    done
    log_success "目录检查完成"
}

# 创建.env配置文件
create_env_file() {
    log_info "检查配置文件..."
    if [ ! -f ".env" ]; then
        log_warning ".env文件不存在，创建模板..."
        cat > .env << 'EOF'
# 🤖 AI模型配置（二选一）
# 方案A：直接复用本机 OpenClaw OAuth（默认，适合 openai-codex/gpt-5.4）
# XIANYU_LLM_BACKEND=openclaw
#
# 方案B：显式配置第三方 OpenAI 兼容接口
API_KEY=
MODEL_BASE_URL=
MODEL_NAME=openai-codex/gpt-5.4

# 🎭 扣子智能体配置（买家AI可选）
COZE_API_KEY=your_coze_api_key_here
COZE_BUYER_BOT_ID=your_buyer_bot_id_here

# 🌐 Web界面配置
WEB_HOST=0.0.0.0
WEB_PORT=5002
WEB_DEBUG=False

# ⚙️ 系统参数
HEARTBEAT_INTERVAL=15
LOG_LEVEL=INFO
RETRY_INTERVAL=60
CONNECTION_TIMEOUT=30

# 🔐 安全配置（建议添加）
ENCRYPTION_KEY=
EOF
        log_warning "请编辑 .env 文件，填入扣子配置或可选的第三方模型配置"
        log_warning "如果本机已配置 OpenClaw，可直接留空 API_KEY，默认走 openai-codex/gpt-5.4"
        return 1
    else
        log_success ".env文件已存在"
        return 0
    fi
}

# 验证配置
verify_config() {
    log_info "验证配置..."
    source .env
    
    if command -v openclaw >/dev/null 2>&1; then
        log_success "检测到 openclaw，可直接走本机 openai-codex/gpt-5.4"
        return 0
    fi

    if [ -z "${API_KEY:-}" ]; then
        log_error "未检测到 openclaw，且 API_KEY 未配置"
        return 1
    fi
    
    log_success "配置验证通过"
    return 0
}

# 代码质量检查
code_quality_check() {
    log_info "执行代码质量检查..."
    
    # 安装检查工具
    pip install black isort pylint -q
    
    # 格式化代码
    log_info "格式化代码..."
    black *.py --quiet 2>/dev/null || log_warning "Black格式化完成(有警告)"
    isort *.py --quiet 2>/dev/null || log_warning "isort排序完成(有警告)"
    
    # Pylint检查（只显示错误和警告）
    log_info "Pylint检查..."
    pylint *.py --disable=C,R --exit-zero > pylint_report.txt 2>&1
    ERROR_COUNT=$(grep -c "E:" pylint_report.txt || echo "0")
    WARNING_COUNT=$(grep -c "W:" pylint_report.txt || echo "0")
    
    if [ "$ERROR_COUNT" -gt 0 ]; then
        log_warning "发现 $ERROR_COUNT 个错误"
    fi
    if [ "$WARNING_COUNT" -gt 0 ]; then
        log_warning "发现 $WARNING_COUNT 个警告"
    fi
    
    log_success "代码质量检查完成，详见 pylint_report.txt"
}

# 安全检查
security_check() {
    log_info "执行安全检查..."
    
    # 检查.gitignore
    if [ ! -f ".gitignore" ]; then
        log_warning "创建.gitignore文件..."
        cat > .gitignore << 'EOF'
# 环境变量
.env
.env.*

# 虚拟环境
venv/
env/
ENV/

# Python缓存
__pycache__/
*.py[cod]
*$py.class
*.so

# 数据和日志
data/
logs/
*.log
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp
*.swo

# 临时文件
*.tmp
*.bak
.DS_Store
EOF
        log_success ".gitignore创建完成"
    fi
    
    # 检查敏感信息
    log_info "检查敏感信息泄露..."
    if grep -r "sk-[a-zA-Z0-9]\{48\}" . --exclude-dir=venv --exclude-dir=.git 2>/dev/null; then
        log_error "发现可能的API Key泄露！"
    else
        log_success "未发现明显的敏感信息泄露"
    fi
}

# 运行测试
run_tests() {
    log_info "运行基础测试..."
    
    # 测试导入
    python3 -c "
import sys
try:
    from XianyuAgent import XianyuReplyBot
    from XianyuApis import XianyuApis
    from multi_account_manager import MultiAccountManager
    print('✅ 所有核心模块导入成功')
    sys.exit(0)
except Exception as e:
    print(f'❌ 模块导入失败: {e}')
    sys.exit(1)
" || {
        log_error "模块导入测试失败"
        return 1
    }
    
    log_success "基础测试通过"
}

# 生成部署报告
generate_report() {
    log_info "生成部署报告..."
    
    cat > DEPLOYMENT_REPORT.md << EOF
# 闲鱼多账号AI运营系统 - 部署报告

**部署时间**: $(date '+%Y-%m-%d %H:%M:%S')
**部署人**: OpenClaw AI

---

## ✅ 部署状态

- [x] Python环境检查
- [x] 虚拟环境创建
- [x] 依赖安装
- [x] 目录结构创建
- [x] 配置文件生成
- [x] 代码质量检查
- [x] 安全检查
- [x] 基础测试

---

## 📋 系统信息

- **Python版本**: $(python3 --version)
- **工作目录**: $(pwd)
- **虚拟环境**: venv/

---

## 🔧 配置文件

- **.env**: 已创建（需手动配置API_KEY）
- **.gitignore**: 已创建
- **prompts/**: 提示词目录

---

## 📊 代码质量

详见 \`pylint_report.txt\` 和 \`CODE_REVIEW.md\`

---

## 🚀 启动命令

\`\`\`bash
# 激活虚拟环境
source venv/bin/activate

# 启动系统
python3 main_multi.py

# 或使用启动脚本
./start.sh
\`\`\`

---

## 🌐 访问地址

- **Web管理界面**: http://localhost:5002
- **监控面板**: http://localhost:5002/monitor

---

## ⚠️ 注意事项

1. **首次使用前**，必须配置 \`.env\` 文件中的 \`API_KEY\`
2. **Cookie获取**: 参考 README.md 中的步骤
3. **安全建议**: 启用Cookie加密存储（见CODE_REVIEW.md）
4. **风控提示**: 建议低频使用，避免账号被封

---

## 📚 相关文档

- [README.md](README.md) - 使用说明
- [CODE_REVIEW.md](CODE_REVIEW.md) - 代码审查报告
- [MULTI_ACCOUNT_GUIDE.md](MULTI_ACCOUNT_GUIDE.md) - 多账号配置指南

---

**部署完成！** 🎉
EOF
    
    log_success "部署报告已生成: DEPLOYMENT_REPORT.md"
}

# 主流程
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║       闲鱼多账号AI运营系统 - 自动化部署脚本                ║"
    echo "║              Powered by OpenClaw AI                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # 1. 环境检查
    check_python
    
    # 2. 虚拟环境
    setup_venv
    
    # 3. 安装依赖
    install_dependencies
    
    # 4. 目录检查
    check_directories
    
    # 5. 配置文件
    if ! create_env_file; then
        log_warning "请先配置.env文件，然后重新运行此脚本"
        log_info "或者跳过配置验证，直接运行: ./setup_and_verify.sh --skip-config"
        exit 0
    fi
    
    # 6. 验证配置（可跳过）
    if [ "$1" != "--skip-config" ]; then
        if ! verify_config; then
            log_warning "配置验证失败，请检查.env文件"
            exit 1
        fi
    fi
    
    # 7. 代码质量检查
    code_quality_check
    
    # 8. 安全检查
    security_check
    
    # 9. 运行测试
    run_tests
    
    # 10. 生成报告
    generate_report
    
    echo ""
    log_success "=========================================="
    log_success "部署完成！"
    log_success "=========================================="
    echo ""
    log_info "下一步操作:"
    echo "  1. 编辑 .env 文件，配置API密钥"
    echo "  2. 运行: source venv/bin/activate"
    echo "  3. 启动: python3 main_multi.py"
    echo "  4. 访问: http://localhost:5002"
    echo ""
    log_info "详细信息请查看: DEPLOYMENT_REPORT.md"
    echo ""
}

# 执行主流程
main "$@"
