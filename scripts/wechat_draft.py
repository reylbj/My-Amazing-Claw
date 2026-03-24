#!/usr/bin/env python3
"""
Publish article drafts to the WeChat Official Account draft box.

The script keeps the original CLI and public helper names stable so existing
automation can continue to call it without changes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests


REQUEST_TIMEOUT_SECONDS = 20
FALLBACK_AUTHOR = "OpenClaw"
DEFAULT_THUMB_MEDIA_ID = "d59as12_SarRDV5X0i_Gfieuz-9y2MnIe5UqdgrqkdjrYuNSfCJ3sjZ5TQf0_6h-"
MAX_TITLE_BYTES = 64
MAX_DIGEST_BYTES = 54


def credentials_file() -> Path:
    return Path(__file__).resolve().parent.parent / ".credentials"


def _load_credential_value(name: str) -> str | None:
    """Read a single KEY=VALUE entry from `.credentials` when available."""
    path = credentials_file()
    if not path.exists():
        return None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key == name:
            return value
    return None


def _load_credentials_from_file() -> tuple[str | None, str | None]:
    """Read WeChat credentials from a flat KEY=VALUE file when available."""
    return _load_credential_value("WECHAT_APPID"), _load_credential_value("WECHAT_APPSECRET")


def resolve_default_author() -> str:
    """Prefer caller/environment config over a repository hard-coded identity."""
    for key in ("WECHAT_AUTHOR", "WECHAT_DEFAULT_AUTHOR"):
        value = _load_credential_value(key) or os.environ.get(key)
        if value:
            return value
    return FALLBACK_AUTHOR


def _get_wechat_credentials() -> tuple[str, str]:
    """Resolve credentials from `.credentials` first, then fall back to env vars."""
    appid, appsecret = _load_credentials_from_file()
    appid = appid or os.environ.get("WECHAT_APPID")
    appsecret = appsecret or os.environ.get("WECHAT_APPSECRET")
    if not appid or not appsecret:
        raise ValueError("请在 .credentials 文件或环境变量中设置 WECHAT_APPID 和 WECHAT_APPSECRET")
    return appid, appsecret


def _format_bold(text: str) -> str:
    """Convert the small markdown subset that the script supports inline."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def convert_md_to_html(md: str) -> str:
    """Convert a narrow markdown subset into WeChat-friendly HTML blocks."""
    html_lines = ['<section style="font-size:16px;line-height:1.8;color:#333;">']
    for raw_line in md.splitlines():
        line = raw_line.strip()
        if not line:
            html_lines.append("<p><br></p>")
            continue
        if line.startswith("### "):
            html_lines.append(
                f'<h3 style="font-size:18px;font-weight:bold;margin:15px 0;">{line[4:]}</h3>'
            )
            continue
        if line.startswith("## "):
            html_lines.append(
                f'<h2 style="font-size:20px;font-weight:bold;margin:18px 0;">{line[3:]}</h2>'
            )
            continue
        if line.startswith("# "):
            html_lines.append(
                f'<h1 style="font-size:24px;font-weight:bold;margin:20px 0;">{line[2:]}</h1>'
            )
            continue
        if line.startswith(("- ", "* ")):
            html_lines.append(f'<li style="margin:5px 0;">{_format_bold(line[2:])}</li>')
            continue
        if line.startswith("---"):
            html_lines.append(
                '<hr style="border:none;border-top:1px solid #e0e0e0;margin:20px 0;">'
            )
            continue
        html_lines.append(f'<p style="margin:10px 0;">{_format_bold(line)}</p>')
    html_lines.append("</section>")
    return "\n".join(html_lines)


def trim_utf8_bytes(text: str, max_bytes: int) -> str:
    """Trim UTF-8 text safely without cutting a multibyte character in half."""
    value = text
    while len(value.encode("utf-8")) > max_bytes:
        value = value[:-1]
    return value


def get_access_token() -> str:
    """Fetch a short-lived access token for the draft API."""
    appid, appsecret = _get_wechat_credentials()
    response = requests.get(
        "https://api.weixin.qq.com/cgi-bin/token",
        params={
            "grant_type": "client_credential",
            "appid": appid,
            "secret": appsecret,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    ).json()
    if "errcode" in response:
        raise RuntimeError(f"获取Token失败: {response}")
    return response["access_token"]


def build_draft_payload(
    *,
    title: str,
    content: str,
    author: str,
    digest: str,
    thumb_media_id: str,
) -> dict:
    """Build the exact payload shape expected by the draft endpoint."""
    safe_title = trim_utf8_bytes(title, MAX_TITLE_BYTES)
    safe_digest = trim_utf8_bytes(digest or safe_title[:18], MAX_DIGEST_BYTES)
    return {
        "articles": [
            {
                "title": safe_title,
                "author": author or resolve_default_author(),
                "digest": safe_digest,
                "content": content,
                "content_source_url": "",
                "thumb_media_id": thumb_media_id or DEFAULT_THUMB_MEDIA_ID,
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
            }
        ]
    }


def push_draft(
    title: str,
    content: str,
    author: str = "",
    digest: str = "",
    thumb_media_id: str = "",
) -> str:
    """
    Push an article into the draft box and return the generated media id.

    The API accepts HTML content only, so markdown callers must convert their
    content before calling this function.
    """

    token = get_access_token()
    payload = build_draft_payload(
        title=title,
        content=content,
        author=author,
        digest=digest,
        thumb_media_id=thumb_media_id,
    )
    response = requests.post(
        f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    ).json()
    if response.get("errcode", 0) != 0:
        raise RuntimeError(f"推送草稿失败: {response}")
    return response.get("media_id", "")


def test_connection() -> bool:
    """Run a lightweight credential check for manual troubleshooting."""
    try:
        get_access_token()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 连接失败: {exc}")
        return False
    print("✅ 连接成功，公众号凭证可用")
    return True


def detect_html_content(content: str) -> bool:
    """Use the original permissive heuristic to preserve existing behavior."""
    stripped = content.strip()
    return "<section" in content or "<p style=" in content or stripped.startswith("<")


def extract_title_from_markdown(content: str) -> str | None:
    """Use the first markdown H1 as the article title when possible."""
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def extract_title_from_html(content: str) -> str | None:
    """Use the first H1 tag as the article title when possible."""
    match = re.search(r"<h1[^>]*>(.+?)</h1>", content)
    if not match:
        return None
    return re.sub(r"<[^>]+>", "", match.group(1)).strip()


def load_content_from_file(path: str) -> tuple[str | None, str]:
    """Load a markdown or HTML file and normalize it into HTML output."""
    raw = Path(path).read_text(encoding="utf-8")
    if detect_html_content(raw):
        return extract_title_from_html(raw), raw
    return extract_title_from_markdown(raw), convert_md_to_html(raw)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="推送文章到微信公众号草稿箱")
    parser.add_argument("--title", required=False, help="文章标题")
    parser.add_argument("--content", required=False, help="文章内容（Markdown或HTML）")
    parser.add_argument("--digest", required=False, default="", help="文章摘要")
    parser.add_argument("--author", required=False, default="", help="作者")
    parser.add_argument("--file", required=False, help="从Markdown文件读取内容")
    parser.add_argument("--test", action="store_true", help="仅测试连接")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.test:
        return 0 if test_connection() else 1

    if args.file:
        inferred_title, rendered_content = load_content_from_file(args.file)
        args.title = args.title or inferred_title
        args.content = rendered_content

    if not args.title or not args.content:
        print("❌ 需要 --title 和 --content（或 --file）")
        return 1

    try:
        media_id = push_draft(
            title=args.title,
            content=args.content,
            author=args.author,
            digest=args.digest or args.title[:18],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"❌ 推送失败: {exc}")
        return 1

    print(f"✅ 推送成功！Media ID: {media_id}")
    print(f"标题：{args.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
