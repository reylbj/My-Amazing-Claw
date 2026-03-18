#!/usr/bin/env python3
"""
小红书笔记发布脚本 - 增强版
支持直接发布（本地签名）和通过 API 服务发布两种方式

使用方法:
    # 直接发布（使用本地签名）
    python publish_xhs.py --title "标题" --desc "描述" --images cover.png card_1.png
    
    # 通过 API 服务发布
    python publish_xhs.py --title "标题" --desc "描述" --images cover.png card_1.png --api-mode

环境变量:
    在同目录或项目根目录下创建 .env 文件，配置：
    
    # 必需：小红书 Cookie
    XHS_COOKIE=your_cookie_string_here
    
    # 可选：API 服务地址（使用 --api-mode 时需要）
    XHS_API_URL=http://localhost:5005

依赖安装:
    pip install xhs python-dotenv requests
"""

import argparse
import asyncio
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import requests
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请运行: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


MAX_IMAGE_COUNT = 8


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def openclaw_publish_script() -> Path:
    return workspace_root() / "scripts" / "xiaohongshu_send.py"


def default_browser_profile_dir() -> Path:
    return Path.home() / "xhs_workspace" / "xiaohongshu-send" / "profile-persistent"


def default_browser_cookies_path() -> Path:
    return Path.home() / "xhs_workspace" / "xiaohongshu-send" / "data" / "cookies.json"


def load_browser_cookies(path: Path) -> list[dict[str, Any]]:
    with path.open('r', encoding='utf-8') as handle:
        raw = json.load(handle)
    if not isinstance(raw, list):
        raise ValueError(f"Cookie 文件格式不正确: {path}")
    return raw


def build_note_body(desc: str, tags: Optional[List[str]]) -> str:
    body = (desc or '').strip()
    if body and '#' in body:
        return body

    normalized_tags = [tag.strip().lstrip('#') for tag in (tags or []) if tag and tag.strip()]
    if normalized_tags:
        suffix = ' '.join(f"#{tag}" for tag in normalized_tags[:10])
        return f"{body}\n\n{suffix}".strip()
    return body


def load_payload_file(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as handle:
        raw = json.load(handle)

    title = raw.get('title') or ''
    desc = raw.get('desc')
    if desc is None:
        desc = raw.get('content') or raw.get('description') or ''
    images = raw.get('images') or raw.get('image_urls') or []
    tags = raw.get('topics') or raw.get('tags') or []

    is_private = bool(raw.get('is_private', False))
    visibility = raw.get('visibility')
    if visibility == '仅自己可见':
        is_private = True
    elif visibility == '公开可见':
        is_private = False

    return {
        'title': title,
        'desc': desc,
        'images': images,
        'tags': tags,
        'is_private': is_private,
    }


def load_cookie() -> str:
    """从 .env 文件加载 Cookie"""
    # 尝试从多个位置加载 .env
    env_paths = [
        Path.cwd() / '.env',
        Path(__file__).parent.parent / '.env',
        Path(__file__).parent.parent.parent / '.env',
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            if load_dotenv:
                load_dotenv(env_path)
            break
    
    cookie = os.getenv('XHS_COOKIE')
    if not cookie:
        print("❌ 错误: 未找到 XHS_COOKIE 环境变量")
        print("请创建 .env 文件，添加以下内容：")
        print("XHS_COOKIE=your_cookie_string_here")
        print("\nCookie 获取方式：")
        print("1. 在浏览器中登录小红书（https://www.xiaohongshu.com）")
        print("2. 打开开发者工具（F12）")
        print("3. 在 Network 标签中查看任意请求的 Cookie 头")
        print("4. 复制完整的 cookie 字符串")
        sys.exit(1)
    
    return cookie


def parse_cookie(cookie_string: str) -> Dict[str, str]:
    """解析 Cookie 字符串为字典"""
    cookies = {}
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies


def validate_cookie(cookie_string: str) -> bool:
    """验证 Cookie 是否包含必要的字段"""
    cookies = parse_cookie(cookie_string)
    
    # 检查必需的 cookie 字段
    required_fields = ['a1', 'web_session']
    missing = [f for f in required_fields if f not in cookies]
    
    if missing:
        print(f"⚠️ Cookie 可能不完整，缺少字段: {', '.join(missing)}")
        print("这可能导致签名失败，请确保 Cookie 包含 a1 和 web_session 字段")
        return False
    
    return True


def get_api_url() -> str:
    """获取 API 服务地址"""
    return os.getenv('XHS_API_URL', 'http://localhost:5005')


def validate_images(image_paths: List[str]) -> List[str]:
    """验证图片文件是否存在"""
    if len(image_paths) > MAX_IMAGE_COUNT:
        print(f"❌ 错误: 小红书单次最多发布 {MAX_IMAGE_COUNT} 张图片，当前 {len(image_paths)} 张")
        sys.exit(1)

    valid_images = []
    for path in image_paths:
        if os.path.exists(path):
            valid_images.append(os.path.abspath(path))
        else:
            print(f"⚠️ 警告: 图片不存在 - {path}")
    
    if not valid_images:
        print("❌ 错误: 没有有效的图片文件")
        sys.exit(1)
    
    return valid_images


class McpPublisher:
    """MCP 发布模式：复用 OpenClaw 当前小红书发布链路。"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def init_client(self):
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
        except requests.RequestException as exc:
            print(f"❌ MCP 服务不可达: {exc}")
            print("请先启动可见或无头的小红书 MCP 服务")
            sys.exit(1)

        if resp.status_code != 200:
            print(f"❌ MCP 健康检查失败: HTTP {resp.status_code}")
            sys.exit(1)

    def publish(self, title: str, desc: str, images: List[str],
                is_private: bool = False, post_time: str = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        if post_time:
            print("❌ MCP 模式暂不支持本脚本内的定时发布参数")
            raise SystemExit(1)

        payload = {
            "title": title,
            "desc": desc,
            "content": desc,
            "topics": tags or [],
            "type": "normal",
            "is_private": is_private,
            "images": images,
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            payload_path = handle.name

        cmd = [
            "python3",
            str(openclaw_publish_script()),
            "publish",
            "--payload",
            payload_path,
            "--base-url",
            self.base_url,
            "--timeout",
            "600",
        ]
        try:
            result = subprocess.run(cmd, text=True, capture_output=True, check=False)
            if result.stdout.strip():
                print(result.stdout.rstrip())
            if result.stderr.strip():
                print(result.stderr.rstrip(), file=sys.stderr)
            if result.returncode != 0:
                raise RuntimeError("MCP 发布失败")
            return json.loads(result.stdout)
        finally:
            try:
                os.unlink(payload_path)
            except OSError:
                pass


class BrowserPublisher:
    """浏览器发布模式：使用固定复用的本地 Chrome profile 走可视化图文发布。"""

    def __init__(
        self,
        profile_dir: str,
        cookies_path: Optional[str] = None,
        headless: bool = False,
        hold_seconds: int = 5,
    ):
        self.profile_dir = Path(profile_dir).expanduser()
        self.cookies_path = Path(cookies_path).expanduser() if cookies_path else None
        self.headless = headless
        self.hold_seconds = hold_seconds

    def init_client(self):
        try:
            from playwright.async_api import async_playwright  # noqa: F401
        except ImportError:
            print("❌ 错误: 缺少 playwright 依赖")
            print("请运行: pip install playwright && playwright install chrome")
            sys.exit(1)

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        if self.cookies_path and not self.cookies_path.exists():
            print(f"❌ 错误: Cookie 文件不存在: {self.cookies_path}")
            sys.exit(1)

    async def _choose_image_tab(self, page) -> None:
        tabs = page.locator('.header-tabs .creator-tab')
        count = await tabs.count()
        for index in range(count):
            tab = tabs.nth(index)
            text = (await tab.inner_text()).strip()
            if text != '上传图文':
                continue
            box = await tab.bounding_box()
            if box and box['x'] >= 0 and box['y'] >= 0:
                await tab.click(force=True)
                await page.wait_for_function(
                    "() => document.body.innerText.includes('上传图片，或写文字生成图片')",
                    timeout=15000,
                )
                return
        raise RuntimeError("未找到可见的“上传图文”入口")

    async def _open_publish_page(self, page, context) -> None:
        print("  -> 打开创作中心")
        if self.cookies_path:
            await context.add_cookies(load_browser_cookies(self.cookies_path))

        await page.goto(
            'https://creator.xiaohongshu.com/publish/publish?source=official',
            wait_until='networkidle',
            timeout=60000,
        )
        if 'login' in page.url:
            raise RuntimeError("进入了登录页，请先更新 ~/xhs_workspace/xiaohongshu-send/data/cookies.json")

    async def _upload_images(self, page, images: List[str]) -> None:
        print("  -> 上传图片")
        upload_button = page.get_by_role('button', name='上传图片')
        async with page.expect_file_chooser() as chooser_info:
            await upload_button.click(force=True)
        chooser = await chooser_info.value
        await chooser.set_files(images)

        wait_timeout = max(90000, len(images) * 15000)
        await page.locator('input[placeholder="填写标题会有更多赞哦"]').first.wait_for(
            state='visible',
            timeout=wait_timeout,
        )
        await page.locator('div.tiptap.ProseMirror[contenteditable="true"]').first.wait_for(
            state='visible',
            timeout=wait_timeout,
        )

    async def _fill_content(self, page, title: str, body: str) -> None:
        print("  -> 填写标题和正文")
        title_input = page.locator('input[placeholder="填写标题会有更多赞哦"]').first
        await title_input.fill(title[:20])

        editor = page.locator('div.tiptap.ProseMirror[contenteditable="true"]').first
        await editor.click()
        await page.keyboard.press('Meta+A')
        await page.keyboard.press('Backspace')
        await page.keyboard.insert_text(body)

    async def _set_visibility(self, page, is_private: bool) -> None:
        if not is_private:
            return

        print("  -> 设置可见范围为仅自己可见")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(500)
        select = page.locator('.permission-card-select').first
        current = page.locator('.permission-card-select .d-select-description').first
        current_text = ((await current.inner_text()).strip()) if await current.count() else ''
        if current_text == '仅自己可见':
            return

        await select.click(force=True)
        await page.wait_for_timeout(500)
        await page.evaluate(
            """() => {
                const names = [...document.querySelectorAll('.custom-option .name')];
                const target = names.find((node) => node.textContent && node.textContent.trim() === '仅自己可见');
                if (!target) throw new Error('未找到“仅自己可见”选项');
                target.click();
            }"""
        )
        await page.wait_for_function(
            "() => document.body.innerText.includes('仅自己可见')",
            timeout=5000,
        )

    async def _click_publish(self, page) -> Dict[str, Any]:
        print("  -> 点击发布")
        publish_responses: list[tuple[int, str]] = []

        def handle_response(resp):
            if resp.request.method != 'POST':
                return
            lowered = resp.url.lower()
            if any(key in lowered for key in ('publish', 'note', 'image', 'save')):
                publish_responses.append((resp.status, resp.url))

        page.on('response', handle_response)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        publish_button = page.get_by_role('button', name='发布').last
        button_state = await publish_button.evaluate(
            """el => ({
                disabled: !!el.disabled,
                className: el.className,
                text: (el.textContent || '').trim(),
                rect: (() => {
                    const box = el.getBoundingClientRect();
                    return {x: box.x, y: box.y, width: box.width, height: box.height};
                })(),
            })"""
        )
        print(f"    发布按钮状态: {button_state}")
        await publish_button.scroll_into_view_if_needed()
        await page.wait_for_timeout(2000)
        await publish_button.hover()
        await page.wait_for_timeout(1000)
        await publish_button.click()

        start_url = page.url
        last_url = start_url
        for _ in range(120):
            await page.wait_for_timeout(1000)
            body = await page.locator('body').inner_text()
            if page.url != last_url:
                print(f"    页面变化: {last_url} -> {page.url}")
                last_url = page.url
            if '发布成功' in body or '已发布' in body:
                return {'status': 'success', 'url': page.url}
            if '验证码' in body or '登录' in page.url:
                raise RuntimeError("发布时触发了登录/验证，请检查 Cookie 或手动过一次验证")
            if publish_responses and any(status < 400 for status, _ in publish_responses):
                return {'status': 'success', 'url': page.url}
        if publish_responses:
            formatted = ', '.join(f"{status} {url}" for status, url in publish_responses[-8:])
            raise RuntimeError(f"点击发布后未观察到成功提示，最近回执: {formatted}")
        raise RuntimeError(f"点击发布后未观察到成功提示或发布接口回执，停留页面: {last_url}（起始页: {start_url}）")

    async def _publish_async(
        self,
        title: str,
        desc: str,
        images: List[str],
        is_private: bool = False,
        post_time: str = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if post_time:
            raise RuntimeError("浏览器模式暂不支持定时发布")

        from playwright.async_api import async_playwright

        note_body = build_note_body(desc, tags)
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                channel='chrome',
                headless=self.headless,
                viewport={'width': 1440, 'height': 1600},
                args=['--disable-blink-features=AutomationControlled'],
            )
            page = context.pages[0] if context.pages else await context.new_page()

            try:
                await self._open_publish_page(page, context)
                await self._choose_image_tab(page)
                await self._upload_images(page, images)
                await self._fill_content(page, title, note_body)
                await self._set_visibility(page, is_private)
                result = await self._click_publish(page)
                print("\n✨ 笔记发布流程已提交")
                print(f"  🔗 当前页面: {result.get('url', page.url)}")
                return result
            except Exception:
                error_shot = Path('/tmp/xhs_browser_publish_error.png')
                await page.screenshot(path=str(error_shot), full_page=True)
                print(f"📸 失败截图: {error_shot}")
                raise
            finally:
                await page.wait_for_timeout(max(self.hold_seconds, 1) * 1000)
                await context.close()

    def publish(
        self,
        title: str,
        desc: str,
        images: List[str],
        is_private: bool = False,
        post_time: str = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        print(f"\n🚀 准备发布笔记（浏览器模式）...")
        print(f"  📌 标题: {title}")
        print(f"  📝 描述: {desc[:50]}..." if len(desc) > 50 else f"  📝 描述: {desc}")
        print(f"  🖼️ 图片数量: {len(images)}")
        print(f"  📂 Profile: {self.profile_dir}")
        if self.cookies_path:
            print(f"  🍪 Cookie: {self.cookies_path}")

        return asyncio.run(
            self._publish_async(
                title=title,
                desc=desc,
                images=images,
                is_private=is_private,
                post_time=post_time,
                tags=tags,
            )
        )


class LocalPublisher:
    """本地发布模式：直接使用 xhs 库"""
    
    def __init__(self, cookie: str):
        self.cookie = cookie
        self.client = None
        
    def init_client(self):
        """初始化 xhs 客户端"""
        try:
            from xhs import XhsClient
            from xhs.help import sign as local_sign
        except ImportError:
            print("❌ 错误: 缺少 xhs 库")
            print("请运行: pip install xhs")
            sys.exit(1)
        
        # 解析 a1 值
        cookies = parse_cookie(self.cookie)
        a1 = cookies.get('a1', '')
        
        def sign_func(uri, data=None, a1_param="", web_session=""):
            # 使用 cookie 中的 a1 值
            return local_sign(uri, data, a1=a1 or a1_param)
        
        self.client = XhsClient(cookie=self.cookie, sign=sign_func)
        
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取当前登录用户信息"""
        try:
            info = self.client.get_self_info()
            print(f"👤 当前用户: {info.get('nickname', '未知')}")
            return info
        except Exception as e:
            print(f"⚠️ 无法获取用户信息: {e}")
            return None
    
    def publish(self, title: str, desc: str, images: List[str],
                is_private: bool = False, post_time: str = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """发布图文笔记"""
        print(f"\n🚀 准备发布笔记（本地模式）...")
        print(f"  📌 标题: {title}")
        print(f"  📝 描述: {desc[:50]}..." if len(desc) > 50 else f"  📝 描述: {desc}")
        print(f"  🖼️ 图片数量: {len(images)}")
        
        try:
            result = self.client.create_image_note(
                title=title,
                desc=desc,
                files=images,
                is_private=is_private,
                post_time=post_time
            )
            
            print("\n✨ 笔记发布成功！")
            if isinstance(result, dict):
                note_id = result.get('note_id') or result.get('id')
                if note_id:
                    print(f"  📎 笔记ID: {note_id}")
                    print(f"  🔗 链接: https://www.xiaohongshu.com/explore/{note_id}")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ 发布失败: {error_msg}")
            
            # 提供具体的错误排查建议
            if 'sign' in error_msg.lower() or 'signature' in error_msg.lower():
                print("\n💡 签名错误排查建议：")
                print("1. 确保 Cookie 包含有效的 a1 和 web_session 字段")
                print("2. Cookie 可能已过期，请重新获取")
                print("3. 尝试使用 --api-mode 通过 API 服务发布")
            elif 'cookie' in error_msg.lower():
                print("\n💡 Cookie 错误排查建议：")
                print("1. 确保 Cookie 格式正确")
                print("2. Cookie 可能已过期，请重新获取")
                print("3. 确保 Cookie 来自已登录的小红书网页版")
            
            raise


class ApiPublisher:
    """API 发布模式：通过 xhs-api 服务发布"""
    
    def __init__(self, cookie: str, api_url: str = None):
        self.cookie = cookie
        self.api_url = api_url or get_api_url()
        self.session_id = 'md2redbook_session'
        
    def init_client(self):
        """初始化 API 客户端"""
        print(f"📡 连接 API 服务: {self.api_url}")
        
        # 健康检查
        try:
            resp = requests.get(f"{self.api_url}/health", timeout=5)
            if resp.status_code != 200:
                raise Exception("API 服务不可用")
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到 API 服务: {e}")
            print(f"\n💡 请确保 xhs-api 服务已启动：")
            print(f"   cd xhs-api && python app_full.py")
            sys.exit(1)
        
        # 初始化 session
        try:
            resp = requests.post(
                f"{self.api_url}/init",
                json={
                    "session_id": self.session_id,
                    "cookie": self.cookie
                },
                timeout=30
            )
            result = resp.json()
            
            if resp.status_code == 200 and result.get('status') == 'success':
                print(f"✅ API 初始化成功")
                user_info = result.get('user_info', {})
                if user_info:
                    print(f"👤 当前用户: {user_info.get('nickname', '未知')}")
            elif result.get('status') == 'warning':
                print(f"⚠️ {result.get('message')}")
            else:
                raise Exception(result.get('error', '初始化失败'))
                
        except Exception as e:
            print(f"❌ API 初始化失败: {e}")
            sys.exit(1)
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取当前登录用户信息"""
        try:
            resp = requests.post(
                f"{self.api_url}/user/info",
                json={"session_id": self.session_id},
                timeout=10
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get('status') == 'success':
                    info = result.get('user_info', {})
                    print(f"👤 当前用户: {info.get('nickname', '未知')}")
                    return info
            return None
        except Exception as e:
            print(f"⚠️ 无法获取用户信息: {e}")
            return None
    
    def publish(self, title: str, desc: str, images: List[str],
                is_private: bool = False, post_time: str = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """发布图文笔记"""
        print(f"\n🚀 准备发布笔记（API 模式）...")
        print(f"  📌 标题: {title}")
        print(f"  📝 描述: {desc[:50]}..." if len(desc) > 50 else f"  📝 描述: {desc}")
        print(f"  🖼️ 图片数量: {len(images)}")
        
        try:
            payload = {
                "session_id": self.session_id,
                "title": title,
                "desc": desc,
                "files": images,
                "is_private": is_private
            }
            if post_time:
                payload["post_time"] = post_time
            
            resp = requests.post(
                f"{self.api_url}/publish/image",
                json=payload,
                timeout=120
            )
            result = resp.json()
            
            if resp.status_code == 200 and result.get('status') == 'success':
                print("\n✨ 笔记发布成功！")
                publish_result = result.get('result', {})
                if isinstance(publish_result, dict):
                    note_id = publish_result.get('note_id') or publish_result.get('id')
                    if note_id:
                        print(f"  📎 笔记ID: {note_id}")
                        print(f"  🔗 链接: https://www.xiaohongshu.com/explore/{note_id}")
                return publish_result
            else:
                raise Exception(result.get('error', '发布失败'))
                
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ 发布失败: {error_msg}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description='将图片发布为小红书笔记',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 基本用法
  python publish_xhs.py -t "我的标题" -d "正文内容" -i cover.png card_1.png card_2.png
  
  # 使用 API 模式
  python publish_xhs.py -t "我的标题" -d "正文内容" -i *.png --api-mode
  
  # 设为私密笔记
  python publish_xhs.py -t "我的标题" -d "正文内容" -i *.png --private
  
  # 定时发布
  python publish_xhs.py -t "我的标题" -d "正文内容" -i *.png --post-time "2024-12-01 10:00:00"
'''
    )
    parser.add_argument(
        '--payload',
        help='直接读取 payload JSON（包含 title/desc 或 content/images/topics/is_private）'
    )
    parser.add_argument(
        '--title', '-t',
        help='笔记标题（不超过20字）'
    )
    parser.add_argument(
        '--desc', '-d',
        default='',
        help='笔记描述/正文内容'
    )
    parser.add_argument(
        '--images', '-i',
        nargs='+',
        help='图片文件路径（可以多个）'
    )
    parser.add_argument(
        '--private',
        action='store_true',
        help='是否设为私密笔记'
    )
    parser.add_argument(
        '--post-time',
        default=None,
        help='定时发布时间（格式：2024-01-01 12:00:00）'
    )
    parser.add_argument(
        '--api-mode',
        action='store_true',
        help='使用 API 模式发布（需要 xhs-api 服务运行）'
    )
    parser.add_argument(
        '--api-url',
        default=None,
        help='API 服务地址（默认: http://localhost:5005）'
    )
    parser.add_argument(
        '--mcp-mode',
        action='store_true',
        help='使用 OpenClaw 当前的小红书 MCP 发布链路'
    )
    parser.add_argument(
        '--browser-mode',
        action='store_true',
        help='使用固定复用的本地 Chrome profile 走可视化浏览器发布链路'
    )
    parser.add_argument(
        '--mcp-base-url',
        default='http://127.0.0.1:18060',
        help='MCP 服务地址（默认: http://127.0.0.1:18060）'
    )
    parser.add_argument(
        '--browser-profile-dir',
        default=str(default_browser_profile_dir()),
        help='浏览器模式使用的固定 profile 目录'
    )
    parser.add_argument(
        '--cookies-path',
        default=str(default_browser_cookies_path()),
        help='浏览器模式使用的 Cookie JSON 文件路径'
    )
    parser.add_argument(
        '--browser-headless',
        action='store_true',
        help='浏览器模式下使用无头 Chrome（默认关闭，便于本地观察）'
    )
    parser.add_argument(
        '--hold-seconds',
        type=int,
        default=5,
        help='浏览器模式结束前保留窗口的秒数，默认 5'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅验证，不实际发布'
    )
    
    args = parser.parse_args()
    
    title = args.title
    desc = args.desc
    images = args.images
    tags: List[str] = []
    is_private = args.private

    if args.payload:
        payload = load_payload_file(args.payload)
        title = payload['title']
        desc = payload['desc']
        images = payload['images']
        tags = payload['tags']
        is_private = payload['is_private']

    if not title:
        print("❌ 错误: 需要提供 --title 或 --payload")
        sys.exit(1)
    if not images:
        print("❌ 错误: 需要提供 --images 或在 --payload 中包含 images")
        sys.exit(1)

    # 验证标题长度
    if len(title) > 20:
        print(f"⚠️ 警告: 标题超过20字，将被截断")
        title = title[:20]
    
    # 验证图片
    valid_images = validate_images(images)
    
    if args.dry_run:
        print("\n🔍 验证模式 - 不会实际发布")
        print(f"  📌 标题: {title}")
        print(f"  📝 描述: {desc}")
        print(f"  🖼️ 图片: {valid_images}")
        print(f"  🏷️ 标签: {tags}")
        print(f"  🔒 私密: {is_private}")
        print(f"  ⏰ 定时: {args.post_time or '立即发布'}")
        if args.browser_mode:
            mode_name = f"Browser ({args.browser_profile_dir})"
        elif args.mcp_mode:
            mode_name = f"MCP ({args.mcp_base_url})"
        else:
            mode_name = 'API' if args.api_mode else '本地'
        print(f"  📡 模式: {mode_name}")
        print("\n✅ 验证通过，可以发布")
        return

    if args.browser_mode:
        publisher = BrowserPublisher(
            profile_dir=args.browser_profile_dir,
            cookies_path=args.cookies_path,
            headless=args.browser_headless,
            hold_seconds=args.hold_seconds,
        )
    elif args.mcp_mode:
        publisher = McpPublisher(args.mcp_base_url)
    else:
        # 加载 Cookie
        cookie = load_cookie()
        # 验证 Cookie 格式
        validate_cookie(cookie)

        # 选择发布方式
        if args.api_mode:
            publisher = ApiPublisher(cookie, args.api_url)
        else:
            publisher = LocalPublisher(cookie)
    
    # 初始化客户端
    publisher.init_client()
    
    # 发布笔记
    try:
        publisher.publish(
            title=title,
            desc=desc,
            images=valid_images,
            is_private=is_private,
            post_time=args.post_time,
            tags=tags
        )
    except Exception as e:
        print(f"\n❌ 发布失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
