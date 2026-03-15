#!/usr/bin/env python3
"""
微信公众号草稿箱接口
优先从 .credentials 文件读取凭证，其次从环境变量
"""

import os
import re
import requests
from pathlib import Path

REQUEST_TIMEOUT_SECONDS = 20


def _load_credentials_from_file():
    """从 .credentials 文件加载凭证"""
    cred_file = Path(__file__).parent.parent / ".credentials"
    if not cred_file.exists():
        return None, None
    
    appid = None
    appsecret = None
    with open(cred_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if key == 'WECHAT_APPID':
                    appid = value
                elif key == 'WECHAT_APPSECRET':
                    appsecret = value
    return appid, appsecret


def _get_wechat_credentials():
    # 优先从 .credentials 文件读取
    appid, appsecret = _load_credentials_from_file()
    
    # 如果文件中没有，再从环境变量读取
    if not appid:
        appid = os.environ.get("WECHAT_APPID")
    if not appsecret:
        appsecret = os.environ.get("WECHAT_APPSECRET")
    
    if not appid or not appsecret:
        raise ValueError("请在 .credentials 文件或环境变量中设置 WECHAT_APPID 和 WECHAT_APPSECRET")
    return appid, appsecret


def _format_bold(text: str) -> str:
    """将 **bold** 转换为 <strong>bold</strong>。"""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def convert_md_to_html(md: str) -> str:
    """简单 Markdown → 微信公众号 HTML 转换。"""
    html = '<section style="font-size:16px;line-height:1.8;color:#333;">\n'
    for line in md.splitlines():
        line = line.strip()
        if not line:
            html += "<p><br></p>\n"
        elif line.startswith("### "):
            html += f'<h3 style="font-size:18px;font-weight:bold;margin:15px 0;">{line[4:]}</h3>\n'
        elif line.startswith("## "):
            html += f'<h2 style="font-size:20px;font-weight:bold;margin:18px 0;">{line[3:]}</h2>\n'
        elif line.startswith("# "):
            html += f'<h1 style="font-size:24px;font-weight:bold;margin:20px 0;">{line[2:]}</h1>\n'
        elif line.startswith("- ") or line.startswith("* "):
            txt = _format_bold(line[2:])
            html += f'<li style="margin:5px 0;">{txt}</li>\n'
        elif line.startswith("---"):
            html += '<hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;">\n'
        else:
            txt = _format_bold(line)
            html += f'<p style="margin:10px 0;">{txt}</p>\n'
    html += "</section>"
    return html

def get_access_token():
    appid, appsecret = _get_wechat_credentials()
    url = "https://api.weixin.qq.com/cgi-bin/token"
    resp = requests.get(
        url,
        params={
            "grant_type": "client_credential",
            "appid": appid,
            "secret": appsecret,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    ).json()
    if "errcode" in resp:
        raise Exception(f"获取Token失败: {resp}")
    return resp["access_token"]

def push_draft(title: str, content: str, author: str = "", digest: str = "", thumb_media_id: str = ""):
    """推送文章到草稿箱

    Args:
        title: 文章标题（最大64字节）
        content: 文章内容（HTML格式）
        author: 作者名
        digest: 摘要（最大54字节，默认取标题前50字符）
        thumb_media_id: 封面图media_id（必填，可从素材库获取）
    """
    import json

    token = get_access_token()
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"

    # 如果没有提供封面图，使用默认的
    if not thumb_media_id:
        thumb_media_id = "d59as12_SarRDV5X0i_Gfieuz-9y2MnIe5UqdgrqkdjrYuNSfCJ3sjZ5TQf0_6h-"

    # 截断标题和摘要至限制长度
    title_bytes = title.encode('utf-8')
    if len(title_bytes) > 64:
        while len(title.encode('utf-8')) > 64:
            title = title[:-1]

    if not digest:
        digest = title[:18]  # 约54字节
    digest_bytes = digest.encode('utf-8')
    if len(digest_bytes) > 54:
        while len(digest.encode('utf-8')) > 54:
            digest = digest[:-1]

    payload = {
        "articles": [{
            "title": title,
            "author": author or "RaysPianoLive",
            "digest": digest,
            "content": content,
            "content_source_url": "",
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }]
    }

    # 关键：使用ensure_ascii=False避免中文被转义为Unicode
    resp = requests.post(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
        timeout=REQUEST_TIMEOUT_SECONDS
    ).json()

    if "errcode" in resp and resp["errcode"] != 0:
        raise Exception(f"推送草稿失败: {resp}")
    return resp.get("media_id", "")

def test_connection():
    """测试连接是否正常"""
    try:
        _ = get_access_token()
        print("✅ 连接成功，公众号凭证可用")
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(description="推送文章到微信公众号草稿箱")
    parser.add_argument("--title",   required=False, help="文章标题")
    parser.add_argument("--content", required=False, help="文章内容（Markdown或HTML）")
    parser.add_argument("--digest",  required=False, default="", help="文章摘要")
    parser.add_argument("--author",  required=False, default="RaysPianoLive", help="作者")
    parser.add_argument("--file",    required=False, help="从Markdown文件读取内容")
    parser.add_argument("--test",    action="store_true", help="仅测试连接")
    args = parser.parse_args()

    if args.test:
        test_connection()
        sys.exit(0)

    # 从文件读取内容
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            content_raw = f.read()
        
        # 检测是否为HTML（如果包含<section>或<p>标签则认为是HTML）
        is_html = '<section' in content_raw or '<p style=' in content_raw or content_raw.strip().startswith('<')
        
        if is_html:
            # 直接使用HTML内容，不转换
            args.content = content_raw
            # 从HTML中提取标题（如果有<h1>标签）
            if not args.title:
                import re
                h1_match = re.search(r'<h1[^>]*>(.+?)</h1>', content_raw)
                if h1_match:
                    args.title = re.sub(r'<[^>]+>', '', h1_match.group(1))  # 去除HTML标签
        else:
            # Markdown内容，需要转换
            if not args.title:
                # 从第一行 # 标题提取
                for line in content_raw.splitlines():
                    if line.startswith("# "):
                        args.title = line[2:].strip()
                        break
            args.content = convert_md_to_html(content_raw)

    if not args.title or not args.content:
        print("❌ 需要 --title 和 --content（或 --file）")
        sys.exit(1)

    try:
        media_id = push_draft(
            title=args.title,
            content=args.content,
            author=args.author,
            digest=args.digest or args.title[:18]
        )
        print(f"✅ 推送成功！Media ID: {media_id}")
        print(f"标题：{args.title}")
    except Exception as e:
        print(f"❌ 推送失败: {e}")
        sys.exit(1)
