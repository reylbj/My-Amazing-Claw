#!/usr/bin/env python3
"""
WhatsApp消息处理主程序
监听用户选择选题编号，自动生成文章并推送到微信草稿箱
"""

import sys
import os
import re
import glob
from pathlib import Path

from wechat_draft import push_draft

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = WORKSPACE_DIR / "验证输出"


def _format_bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

# 今日选题映射（从验证输出目录读取）
def load_today_topics():
    """动态加载今日选题"""

    # 查找今日选题文件
    topics = {}
    for i in range(1, 16):  # 支持1-15个选题
        file_path = str(OUTPUT_DIR / f"文章_选题{i}_*.md")
        matches = sorted(glob.glob(file_path))
        if matches:
            # 从文件名提取标题
            filename = os.path.basename(matches[0])
            title = filename.replace(f"文章_选题{i}_", "").replace(".md", "")
            topics[str(i)] = {
                "title": title,
                "file": matches[0],
                "digest": ""  # 从文件内容提取
            }

    # 如果没有找到，使用默认的3个选题
    if not topics:
        topics = {
            "1": {
                "title": "用户正在批量逃离ChatGPT,Claude迎来最大流量窗口",
                "file": str(OUTPUT_DIR / "文章_选题1_AI产品信任危机.md"),
                "digest": "这波迁移的背后,不只是功能差异,更是信任危机——AI产品的护城河到底是什么?"
            },
            "2": {
                "title": "AI Agent开始替代真实客服了:14.ai的商业模式值得研究",
                "file": str(OUTPUT_DIR / "文章_选题2_AI_Agent替代岗位.md"),
                "digest": "不是PPT里的未来,是正在发生的岗位替代——创业者该怎么看这个机会?"
            },
            "3": {
                "title": "人形机器人关节公司年营收翻倍,C+轮融资到手",
                "file": str(OUTPUT_DIR / "文章_选题3_机器人产业链.md"),
                "digest": "不是遥远的科幻,是已经有商业订单的硬科技赛道,这条产业链值得提前看"
            }
        }

    return topics

def convert_md_to_html(md_content):
    """将Markdown转换为微信公众号HTML格式"""
    html = '<section style="font-size: 16px; line-height: 1.8; color: #333;">\n'

    lines = md_content.split('\n')
    in_list = False

    for line in lines:
        line = line.strip()

        if not line:
            if in_list:
                html += '</ul>\n'
                in_list = False
            html += '<p><br></p>\n'
            continue

        # 标题
        if line.startswith('# '):
            html += f'<h1 style="font-size: 24px; font-weight: bold; margin: 20px 0;">{line[2:]}</h1>\n'
        elif line.startswith('## '):
            html += f'<h2 style="font-size: 20px; font-weight: bold; margin: 18px 0; color: #2c3e50;">{line[3:]}</h2>\n'
        elif line.startswith('### '):
            html += f'<h3 style="font-size: 18px; font-weight: bold; margin: 15px 0; color: #34495e;">{line[4:]}</h3>\n'

        # 列表
        elif line.startswith('- ') or line.startswith('* '):
            if not in_list:
                html += '<ul style="margin: 10px 0; padding-left: 20px;">\n'
                in_list = True
            content = _format_bold(line[2:])
            html += f'<li style="margin: 5px 0;">{content}</li>\n'

        # 分隔线
        elif line.startswith('---'):
            if in_list:
                html += '</ul>\n'
                in_list = False
            html += '<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">\n'

        # 普通段落
        else:
            if in_list:
                html += '</ul>\n'
                in_list = False

            # 处理加粗
            content = _format_bold(line)
            html += f'<p style="margin: 10px 0;">{content}</p>\n'

    if in_list:
        html += '</ul>\n'

    html += '</section>'
    return html

def handle_topic_selection(choice):
    """处理用户选择的选题编号"""

    topics = load_today_topics()

    # 验证选择
    if choice not in topics:
        return {
            "success": False,
            "message": f"❌ 无效选择: {choice}\n请选择 1-{len(topics)} 之间的数字"
        }

    topic = topics[choice]

    # 读取文章内容
    try:
        if not os.path.exists(topic['file']):
            return {
                "success": False,
                "message": f"❌ 文章文件不存在: {topic['file']}\n请先生成选题{choice}的文章内容"
            }

        with open(topic['file'], 'r', encoding='utf-8') as f:
            md_content = f.read()

        # 转换为HTML
        html_content = convert_md_to_html(md_content)

        # 推送到草稿箱
        media_id = push_draft(
            title=topic['title'],
            content=html_content,
            author="RaysPianoLive",
            digest=topic['digest'] or topic['title'][:18]
        )

        return {
            "success": True,
            "message": f"✅ 草稿箱已更新\n选题: {topic['title']}\n请登录 https://mp.weixin.qq.com 查看",
            "media_id": media_id,
            "title": topic['title']
        }

    except FileNotFoundError:
        return {
            "success": False,
            "message": f"❌ 文章文件不存在: {topic['file']}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ 推送失败: {str(e)}\n\n可能原因:\n1. 环境变量未设置\n2. 公众号权限不足\n3. 网络连接问题"
        }

def parse_message(message):
    """解析WhatsApp消息，识别选题编号"""

    # 去除空格和特殊字符
    message = message.strip()

    # 匹配纯数字
    if re.match(r'^\d+$', message):
        return message

    # 匹配"选题1"、"1号"等格式
    match = re.search(r'(\d+)', message)
    if match:
        return match.group(1)

    return None

def main():
    """主函数 - 处理命令行输入或作为模块导入"""

    if len(sys.argv) > 1:
        # 命令行模式
        user_input = sys.argv[1]
    else:
        # 交互模式
        print("WhatsApp Bot - 选题处理程序")
        print("输入选题编号(1-15)或输入'exit'退出")
        user_input = input("> ").strip()

        if user_input.lower() == 'exit':
            sys.exit(0)

    # 解析消息
    choice = parse_message(user_input)

    if not choice:
        print(f"❌ 无法识别的输入: {user_input}")
        print("请输入选题编号(1-15)")
        sys.exit(1)

    # 处理选题
    if not os.environ.get("WECHAT_APPID") or not os.environ.get("WECHAT_APPSECRET"):
        print("❌ 未检测到公众号凭证，请先设置环境变量 WECHAT_APPID 和 WECHAT_APPSECRET")
        sys.exit(1)

    result = handle_topic_selection(choice)

    print(result['message'])

    if result['success']:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
