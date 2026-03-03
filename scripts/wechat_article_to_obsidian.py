#!/usr/bin/env python3
"""
读取微信公众号文章并保存到 Obsidian。

用法:
  python3 scripts/wechat_article_to_obsidian.py --url "https://mp.weixin.qq.com/s?..."
  python3 scripts/wechat_article_to_obsidian.py --url "..." --vault "/Users/xxx/Documents/Obsidian Vault"
"""

import argparse
import os
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Optional

import requests

REQUEST_TIMEOUT = 25
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class Article:
    title: str
    author: str
    published: str
    source_url: str
    content_markdown: str


def _clean_text(text: str) -> str:
    text = unescape(text or "")
    text = text.replace("\u200b", "")
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "_", name.strip())
    name = re.sub(r"\s+", " ", name)
    if not name:
        name = "未命名文章"
    return name[:max_len]


def _find_meta(html: str, key: str) -> str:
    pattern = rf'<meta[^>]+(?:property|name)=["\']{re.escape(key)}["\'][^>]+content=["\'](.*?)["\']'
    m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    return _clean_text(m.group(1)) if m else ""


def _strip_js_tail(value: str) -> str:
    text = _clean_text(value)
    # 清理微信页面中常见的脚本尾巴污染
    for marker in ["var msg_desc", "var msg_cdn_url", ".html(false);", ".html(true);"]:
        if marker in text:
            text = text.split(marker, 1)[0]
    return text.strip(" '\";\t\r\n")


def _find_js_var(html: str, var_name: str) -> str:
    # 适配多种形式:
    # var xx = '...';
    # var xx = "...";
    # var xx = htmlDecode("...").html(false);
    patterns = [
        rf'var\s+{re.escape(var_name)}\s*=\s*htmlDecode\(\s*["\'](.*?)["\']\s*\)\s*(?:\.html\([^)]*\))?\s*;',
        rf'var\s+{re.escape(var_name)}\s*=\s*["\'](.*?)["\']\s*(?:\.html\([^)]*\))?\s*;',
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            value = _strip_js_tail(m.group(1))
            if value:
                return value
    return ""


def _extract_div_by_id(html: str, target_id: str) -> str:
    open_tag_pattern = rf'<div\b[^>]*\bid=["\']{re.escape(target_id)}["\'][^>]*>'
    open_match = re.search(open_tag_pattern, html, re.IGNORECASE)
    if not open_match:
        return ""

    cursor = open_match.end()
    depth = 1
    token_pattern = re.compile(r"<div\b[^>]*>|</div>", re.IGNORECASE)
    for token in token_pattern.finditer(html, cursor):
        token_text = token.group(0).lower()
        if token_text.startswith("<div"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return html[cursor:token.start()]
    return ""


def _replace_links(fragment: str) -> str:
    def repl(match):
        href = _clean_text(match.group(1))
        text = _clean_text(re.sub(r"<[^>]+>", "", match.group(2)))
        if not href:
            return text
        if not text:
            text = href
        return f"[{text}]({href})"

    return re.sub(
        r'<a\b[^>]*href=["\'](.*?)["\'][^>]*>(.*?)</a>',
        repl,
        fragment,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _replace_images(fragment: str) -> str:
    def repl(match):
        tag = match.group(0)
        src_match = re.search(r'(?:data-src|src)=["\'](.*?)["\']', tag, re.IGNORECASE)
        alt_match = re.search(r'alt=["\'](.*?)["\']', tag, re.IGNORECASE)
        src = _clean_text(src_match.group(1) if src_match else "")
        alt = _clean_text(alt_match.group(1) if alt_match else "")
        if not src:
            return ""
        return f"\n![{alt}]({src})\n"

    return re.sub(r"<img\b[^>]*>", repl, fragment, flags=re.IGNORECASE)


def _html_to_markdown(fragment: str) -> str:
    text = fragment
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)

    text = _replace_images(text)
    text = _replace_links(text)

    # 基础结构转换
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\b[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li\b[^>]*>", "- ", text, flags=re.IGNORECASE)

    # 标题与强调
    text = re.sub(r"<h1\b[^>]*>(.*?)</h1>", r"# \1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h2\b[^>]*>(.*?)</h2>", r"## \1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<h3\b[^>]*>(.*?)</h3>", r"### \1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(em|i)\b[^>]*>(.*?)</\1>", r"*\2*", text, flags=re.IGNORECASE | re.DOTALL)

    # 剩余标签清理
    text = re.sub(r"<[^>]+>", "", text)
    return _clean_text(text)


def _parse_publish_time(html: str) -> str:
    publish = _find_js_var(html, "publish_time")
    if publish:
        return publish

    ct = _find_js_var(html, "ct")
    if ct and ct.isdigit():
        try:
            return datetime.fromtimestamp(int(ct)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""
    return ""


def parse_wechat_article(html: str, source_url: str) -> Article:
    title = _find_meta(html, "og:title") or _find_js_var(html, "msg_title") or "未命名公众号文章"
    author = (
        _find_meta(html, "og:article:author")
        or _find_js_var(html, "nickname")
        or _find_meta(html, "author")
        or "未知作者"
    )
    published = _parse_publish_time(html) or "未知时间"

    content_html = _extract_div_by_id(html, "js_content")
    if not content_html:
        raise ValueError("未找到公众号正文区块（js_content），可能需要登录态或链接不可直接解析")

    content_markdown = _html_to_markdown(content_html)
    if not content_markdown:
        raise ValueError("正文提取结果为空，可能是防爬页面或内容加载失败")

    return Article(
        title=title,
        author=author,
        published=published,
        source_url=source_url,
        content_markdown=content_markdown,
    )


def _detect_default_vault() -> Optional[Path]:
    env_value = (Path.home() / ".openclaw" / "obsidian_vault_path.txt")
    if env_value.exists():
        custom = Path(env_value.read_text(encoding="utf-8").strip()).expanduser()
        if custom.exists() and custom.is_dir():
            return custom

    direct = Path.home() / "Documents" / "Obsidian Vault"
    if direct.exists() and direct.is_dir():
        return direct

    obsidian_env = Path((os.environ.get("OBSIDIAN_VAULT", "") or "").strip()).expanduser()
    if str(obsidian_env) != "." and obsidian_env.exists() and obsidian_env.is_dir():
        return obsidian_env

    return None


def _resolve_vault(vault_arg: Optional[str]) -> Path:
    if vault_arg:
        vault_path = Path(vault_arg).expanduser()
    else:
        detected = _detect_default_vault()
        if not detected:
            raise ValueError("未检测到默认 Obsidian Vault，请通过 --vault 指定路径")
        vault_path = detected

    if not vault_path.exists() or not vault_path.is_dir():
        raise ValueError(f"Vault 路径不存在: {vault_path}")
    return vault_path


def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()
    # 微信常见风控页提示，给出清晰错误
    if "环境异常" in resp.text and "微信公众平台" in resp.text:
        raise ValueError("命中微信风控页面，建议改用 x-reader / Agent Reach 或登录态浏览器抓取")
    return resp.text


def save_to_obsidian(article: Article, vault_path: Path, folder: str) -> Path:
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    out_dir = vault_path / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{date_prefix}_{_sanitize_filename(article.title)}.md"
    path = out_dir / filename

    body = (
        f"---\n"
        f'title: "{article.title}"\n'
        f'type: "wechat_article"\n'
        f'author: "{article.author}"\n'
        f'published: "{article.published}"\n'
        f'source: "{article.source_url}"\n'
        f'captured_at: "{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"\n'
        f"tags: [wechat, clipping]\n"
        f"---\n\n"
        f"# {article.title}\n\n"
        f"> 来源: [{article.source_url}]({article.source_url})\n"
        f"> 作者: {article.author}\n"
        f"> 发布时间: {article.published}\n\n"
        f"{article.content_markdown}\n"
    )

    path.write_text(body, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="读取公众号文章并保存到 Obsidian")
    parser.add_argument("--url", required=False, help="公众号文章链接（mp.weixin.qq.com/s?...）")
    parser.add_argument("--html-file", required=False, help="本地HTML文件路径（用于离线导入）")
    parser.add_argument("--source-url", required=False, help="离线导入时指定原始链接")
    parser.add_argument("--vault", required=False, help="Obsidian Vault 路径")
    parser.add_argument(
        "--folder",
        default="收件箱/公众号",
        help="Vault 内保存目录（默认: 收件箱/公众号）",
    )
    args = parser.parse_args()

    if not args.url and not args.html_file:
        raise ValueError("请提供 --url 或 --html-file")

    vault = _resolve_vault(args.vault)
    if args.html_file:
        html_path = Path(args.html_file).expanduser()
        if not html_path.exists():
            raise ValueError(f"HTML 文件不存在: {html_path}")
        html = html_path.read_text(encoding="utf-8")
        source = args.source_url or args.url or "about:local-html"
    else:
        html = fetch_html(args.url)
        source = args.url

    article = parse_wechat_article(html, source)
    path = save_to_obsidian(article, vault, args.folder)
    print(f"✅ 已保存到 Obsidian: {path}")
    print(f"标题: {article.title}")
    print(f"作者: {article.author}")
    print(f"发布时间: {article.published}")


if __name__ == "__main__":
    main()
