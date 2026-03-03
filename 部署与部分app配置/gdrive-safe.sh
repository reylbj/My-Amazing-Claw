#!/bin/bash

# Google Drive 权限控制脚本
# 用于安全地执行 Google Drive 操作，确保遵守权限规则

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查 rclone 是否已安装
if ! command -v rclone &> /dev/null; then
    echo -e "${RED}错误: rclone 未安装${NC}"
    exit 1
fi

# 检查远程是否配置
if ! rclone listremotes | grep -q "^gdrive:$"; then
    echo -e "${RED}错误: gdrive 远程未配置${NC}"
    echo "请先运行: ./setup-google-drive.sh"
    exit 1
fi

# 显示帮助信息
show_help() {
    echo -e "${GREEN}Google Drive 权限控制脚本${NC}"
    echo ""
    echo "用法: $0 <操作> [参数]"
    echo ""
    echo "允许的操作（无需批准）："
    echo "  list <路径>          列出目录内容"
    echo "  cat <文件路径>       查看文件内容"
    echo "  download <远程路径> <本地路径>  下载文件"
    echo "  tree <路径>          显示目录树"
    echo "  search <关键词>      搜索文件"
    echo ""
    echo "示例："
    echo "  $0 list petch/"
    echo "  $0 cat petch/README.md"
    echo "  $0 download petch/ ./local-petch/"
    echo "  $0 tree petch/"
    echo "  $0 search \"config.json\""
    echo ""
    echo "禁止的操作："
    echo "  - delete (删除文件)"
    echo "  - move (移动文件)"
    echo "  - rename (重命名文件)"
    echo "  - sync (同步，会删除文件)"
    echo ""
}

# 列出目录
list_directory() {
    local path="$1"
    echo -e "${GREEN}列出目录: gdrive:${path}${NC}"
    rclone lsd "gdrive:${path}" 2>/dev/null || echo "目录为空或不存在"
    echo ""
    echo "文件列表（前20个）："
    rclone ls "gdrive:${path}" --max-depth 1 | head -20
}

# 查看文件内容
cat_file() {
    local file="$1"
    echo -e "${GREEN}读取文件: gdrive:${file}${NC}"
    rclone cat "gdrive:${file}" 2>/dev/null || echo -e "${RED}文件不存在或无法读取${NC}"
}

# 下载文件
download_file() {
    local remote="$1"
    local local="$2"

    if [ -z "$local" ]; then
        echo -e "${RED}错误: 请指定本地路径${NC}"
        exit 1
    fi

    echo -e "${GREEN}下载: gdrive:${remote} -> ${local}${NC}"
    rclone copy "gdrive:${remote}" "${local}" --progress
    echo -e "${GREEN}下载完成${NC}"
}

# 显示目录树
show_tree() {
    local path="$1"
    echo -e "${GREEN}目录树: gdrive:${path}${NC}"
    rclone tree "gdrive:${path}" --max-depth 3
}

# 搜索文件
search_files() {
    local keyword="$1"
    echo -e "${GREEN}搜索关键词: ${keyword}${NC}"
    rclone ls "gdrive:" | grep -i "${keyword}" | head -20
}

# 禁止的操作
forbidden_operation() {
    local op="$1"
    echo -e "${RED}❌ 禁止操作: ${op}${NC}"
    echo ""
    echo "根据权限规则，以下操作被禁止："
    echo "  - 删除文件 (delete, purge)"
    echo "  - 移动文件 (move, moveto)"
    echo "  - 重命名文件 (rename)"
    echo "  - 同步操作 (sync)"
    echo ""
    echo "如需修改文件，请："
    echo "  1. 下载文件到本地"
    echo "  2. 在本地编辑"
    echo "  3. 请求 Ray 批准后上传"
    exit 1
}

# 主逻辑
case "$1" in
    list)
        list_directory "${2:-}"
        ;;
    cat)
        if [ -z "$2" ]; then
            echo -e "${RED}错误: 请指定文件路径${NC}"
            exit 1
        fi
        cat_file "$2"
        ;;
    download)
        download_file "$2" "$3"
        ;;
    tree)
        show_tree "${2:-}"
        ;;
    search)
        if [ -z "$2" ]; then
            echo -e "${RED}错误: 请指定搜索关键词${NC}"
            exit 1
        fi
        search_files "$2"
        ;;
    delete|purge|move|moveto|rename|sync)
        forbidden_operation "$1"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}错误: 未知操作 '$1'${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
