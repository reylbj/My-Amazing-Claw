#!/usr/bin/env python3
"""
模拟WhatsApp选题交互并推送到微信草稿箱
验证完整工作流：选题生成 → 用户选择 → 文章生成 → 推送草稿箱
"""

import sys
import re
from datetime import datetime
from pathlib import Path

from wechat_draft import push_draft

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = WORKSPACE_DIR / "验证输出"

# 模拟选题列表（从今日选题文件读取）
TOPICS = {
    "1": {
        "title": "用户正在批量逃离ChatGPT，Claude迎来最大流量窗口",
        "file": str(OUTPUT_DIR / "文章_选题1_AI产品信任危机.md"),
        "digest": "这波迁移的背后，不只是功能差异，更是信任危机——AI产品的护城河到底是什么？"
    },
    "2": {
        "title": "AI Agent开始替代真实客服了：14.ai的商业模式值得研究",
        "file": str(OUTPUT_DIR / "文章_选题2_AI_Agent替代岗位.md"),
        "digest": "不是PPT里的未来，是正在发生的岗位替代——创业者该怎么看这个机会？"
    },
    "3": {
        "title": "人形机器人关节公司年营收翻倍，C+轮融资到手",
        "file": str(OUTPUT_DIR / "文章_选题3_机器人产业链.md"),
        "digest": "不是遥远的科幻，是已经有商业订单的硬科技赛道，这条产业链值得提前看"
    }
}

def _format_bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

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

def simulate_whatsapp_workflow(choice):
    """模拟WhatsApp选择选题并推送到草稿箱"""

    if choice not in TOPICS:
        print(f"❌ 无效选择：{choice}")
        print(f"请选择 1-{len(TOPICS)} 之间的数字")
        return False

    topic = TOPICS[choice]
    print(f"\n{'='*60}")
    print(f"📱 模拟WhatsApp输入：{choice}")
    print(f"{'='*60}")
    print(f"✅ 已选择选题{choice}：{topic['title']}")
    print(f"\n正在读取文章内容...")

    # 读取文章内容
    try:
        with open(topic['file'], 'r', encoding='utf-8') as f:
            md_content = f.read()

        print(f"✅ 文章内容已读取（{len(md_content)} 字符）")

        # 转换为HTML
        print(f"\n正在转换为微信公众号格式...")
        html_content = convert_md_to_html(md_content)

        # 推送到草稿箱
        print(f"\n正在推送到微信公众号草稿箱...")
        print(f"标题：{topic['title']}")
        print(f"摘要：{topic['digest']}")
        print("-" * 60)

        media_id = push_draft(
            title=topic['title'],
            content=html_content,
            author="RaysPianoLive",
            digest=topic['digest']
        )

        print(f"\n{'='*60}")
        print(f"✅ 推送成功！")
        print(f"{'='*60}")
        print(f"Media ID: {media_id}")
        print(f"\n📱 WhatsApp通知：")
        print(f"   草稿箱已更新")
        print(f"   选题：{topic['title']}")
        print(f"   请登录微信公众平台查看：https://mp.weixin.qq.com")
        print(f"{'='*60}\n")

        return True

    except FileNotFoundError:
        print(f"❌ 文章文件不存在：{topic['file']}")
        return False
    except Exception as e:
        print(f"❌ 推送失败：{e}")
        print("\n可能的原因：")
        print("1. 环境变量 WECHAT_APPID 和 WECHAT_APPSECRET 未设置")
        print("2. 公众号不是认证服务号")
        print("3. IP白名单配置有误")
        return False

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print("\n" + "="*60)
    print("🦞 OpenClaw 选题工作流验证")
    print("="*60)
    print(f"\n📝 今日选题（{today}）\n")

    for key, topic in TOPICS.items():
        print(f"{key}. {topic['title']}")
        print(f"   {topic['digest']}\n")

    print("-" * 60)
    print("模拟场景：用户在WhatsApp输入选题编号")
    print("-" * 60)

    # 如果有命令行参数，使用参数
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        # 否则提示用户输入
        choice = input("\n请输入选题编号（1-3）：").strip()

    success = simulate_whatsapp_workflow(choice)

    if success:
        print("\n✅ 工作流验证成功！")
        print("\n完整流程：")
        print("1. ✅ 生成今日选题（3个不同主题）")
        print("2. ✅ 用户在WhatsApp输入选择")
        print("3. ✅ 读取对应文章内容")
        print("4. ✅ 转换为微信公众号HTML格式")
        print("5. ✅ 推送到微信公众号草稿箱")
        print("6. ✅ WhatsApp通知用户")
    else:
        print("\n❌ 工作流验证失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
