#!/usr/bin/env python3
"""
闲鱼自动发布脚本 - 基于Playwright
支持AI生成文案 + 自动发布商品
"""

import asyncio
import os
import json
import time
from typing import Dict, Optional, Sequence
from playwright.async_api import async_playwright, Page, Browser
from loguru import logger
from dotenv import load_dotenv
from xianyu_llm import XianyuLLM
from xianyu_publish_content import (
    build_publish_prompt,
    normalize_publish_content,
    select_cover_images,
)

load_dotenv()


class XianyuAutoPublisher:
    """闲鱼自动发布器"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.ai_client = XianyuLLM()
        
    async def init_browser(self, headless: bool = False):
        """初始化浏览器"""
        logger.info("初始化浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # 创建浏览器上下文（可以加载Cookie）
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        self.page = await context.new_page()
        logger.success("浏览器初始化完成")
        
    async def load_cookies(self, cookie_file: str = "data/xianyu_cookies.json"):
        """加载Cookie"""
        if not os.path.exists(cookie_file):
            logger.warning(f"Cookie文件不存在: {cookie_file}")
            return False
            
        try:
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            await self.page.context.add_cookies(cookies)
            logger.success("Cookie加载成功")
            return True
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return False

    async def _fill_contenteditable(self, selectors: Sequence[str], value: str, description: str) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector).first
            if await locator.count() == 0:
                continue
            try:
                await locator.click()
                await locator.fill(value)
                logger.success(f"{description}填写成功")
                return True
            except Exception:
                try:
                    await locator.click()
                    await self.page.keyboard.press("Meta+A")
                    await self.page.keyboard.press("Backspace")
                    await locator.type(value, delay=20)
                    logger.success(f"{description}填写成功")
                    return True
                except Exception as exc:
                    logger.debug(f"{description}选择器失败: {selector}, 错误: {exc}")
        return False

    async def _fill_input(self, selectors: Sequence[str], value: str, description: str) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector).first
            if await locator.count() == 0:
                continue
            try:
                await locator.click()
                await locator.fill(value)
                logger.success(f"{description}填写成功")
                return True
            except Exception as exc:
                logger.debug(f"{description}选择器失败: {selector}, 错误: {exc}")
        return False

    async def _click_first(self, selectors: Sequence[str], description: str) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector).first
            if await locator.count() == 0:
                continue
            try:
                await locator.click()
                logger.success(f"{description}点击成功")
                return True
            except Exception as exc:
                    logger.debug(f"{description}选择器失败: {selector}, 错误: {exc}")
        return False

    async def _select_option(
        self,
        container_selectors: Sequence[str],
        preferred_texts: Sequence[str],
        description: str,
    ) -> bool:
        opened = False
        for container_selector in container_selectors:
            container = self.page.locator(container_selector).first
            try:
                await container.click(timeout=3000)
                await asyncio.sleep(0.8)
                opened = True
                break
            except Exception as exc:
                logger.debug(f"{description}选择器失败: {container_selector}, 错误: {exc}")

        if not opened:
            fallback = self.page.locator('input[role="combobox"]').last
            try:
                await fallback.click(force=True, timeout=3000)
                await asyncio.sleep(0.8)
                opened = True
            except Exception as exc:
                logger.debug(f"{description}combobox兜底点击失败: {exc}")

        for text in preferred_texts:
            option_candidates = [
                self.page.get_by_role("option", name=text).first,
                self.page.locator(".ant-select-dropdown .ant-select-item-option").filter(has_text=text).first,
            ]
            for option in option_candidates:
                try:
                    await option.click(timeout=3000)
                    await asyncio.sleep(0.5)
                    logger.success(f"{description}选择成功: {text}")
                    return True
                except Exception as exc:
                    logger.debug(f"{description}选项点击失败: {text}, 错误: {exc}")

        await self.page.keyboard.press("Escape")
        return False

    async def wait_for_text_signals(self, texts: Sequence[str], timeout: float = 12.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            body_text = await self.page.evaluate(
                """
() => (document.body.innerText || '').replace(/\\s+/g, ' ').trim()
"""
            )
            if all(text in body_text for text in texts):
                return True
            await asyncio.sleep(0.5)
        return False

    async def _publish_button_enabled(self) -> bool:
        button = self.page.locator('button.publish-button--KBpTVopQ, button:has-text("发布")').first
        if await button.count() == 0:
            return False
        try:
            state = await button.evaluate(
                """
(el) => {
  const style = window.getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  return {
    disabledAttr: el.hasAttribute('disabled'),
    ariaDisabled: el.getAttribute('aria-disabled'),
    pointerEvents: style.pointerEvents,
    opacity: style.opacity,
    backgroundColor: style.backgroundColor,
    color: style.color,
    width: rect.width,
    height: rect.height,
  };
}
"""
            )
        except Exception:
            return not await button.is_disabled()

        if state["disabledAttr"] or state["ariaDisabled"] == "true":
            return False
        if state["pointerEvents"] == "none":
            return False
        if state["width"] == 0 or state["height"] == 0:
            return False
        return True

    async def _collect_publish_state(self) -> Dict[str, object]:
        return await self.page.evaluate(
            """
() => {
  const text = (el) => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
  const bodyText = text(document.body).slice(0, 8000);
  const imageSection = Array.from(document.querySelectorAll('.ant-form-item'))
    .find((el) => text(el).includes('宝贝图片'));
  const imageText = text(imageSection);
  const imageScope = imageSection || document.body;
  const imageCount = imageScope.querySelectorAll('img').length;
  const uploadingNodes = Array.from(imageScope.querySelectorAll('*'))
    .filter((el) => /上传中|处理中|图片检测|加载中|校验中|审核中|压缩中/.test(text(el)))
    .length;
  const busyIndicators = imageScope.querySelectorAll(
    '[class*="loading"], [class*="uploading"], [class*="progress"], [class*="spin"], [aria-busy="true"]'
  ).length;
  const publishButton = document.querySelector('button.publish-button--KBpTVopQ') || Array.from(document.querySelectorAll('button')).find((el) => text(el) === '发布');
  return {
    bodyText,
    imageText,
    imageCount,
    uploadingNodes,
    busyIndicators,
    hasAddFirstImage: imageText.includes('添加首图'),
    hasAddDetailImage: imageText.includes('添加细节图'),
    schedulePresent: bodyText.includes('预计工期'),
    pricingPresent: bodyText.includes('计价方式'),
    locationPresent: bodyText.includes('杭州之门') || bodyText.includes('宝贝所在地'),
    publishButtonText: text(publishButton),
  };
}
"""
        )

    async def wait_for_publish_ready(
        self,
        expected_images: int = 1,
        timeout: float = 45.0,
        stable_rounds: int = 3,
        post_ready_wait: float = 8.0,
    ) -> bool:
        elapsed = 0.0
        interval = 2.0
        ready_rounds = 0

        while elapsed < timeout:
            page_state = await self._collect_publish_state()
            body_text = str(page_state["bodyText"])
            upload_busy = any(token in body_text for token in ("上传中", "处理中", "图片检测", "加载中", "校验中", "审核中", "压缩中"))
            image_ready = bool(page_state["hasAddDetailImage"]) or int(page_state["imageCount"]) >= expected_images
            pending_indicators = int(page_state["uploadingNodes"]) > 0 or int(page_state["busyIndicators"]) > 0
            publish_ready = await self._publish_button_enabled()

            if publish_ready and image_ready and not upload_busy and not pending_indicators:
                ready_rounds += 1
                if ready_rounds >= stable_rounds:
                    if post_ready_wait > 0:
                        await asyncio.sleep(post_ready_wait)
                        page_state = await self._collect_publish_state()
                        body_text = str(page_state["bodyText"])
                        upload_busy = any(
                            token in body_text for token in ("上传中", "处理中", "图片检测", "加载中", "校验中", "审核中", "压缩中")
                        )
                        image_ready = bool(page_state["hasAddDetailImage"]) or int(page_state["imageCount"]) >= expected_images
                        pending_indicators = int(page_state["uploadingNodes"]) > 0 or int(page_state["busyIndicators"]) > 0
                        publish_ready = await self._publish_button_enabled()
                        if not (publish_ready and image_ready and not upload_busy and not pending_indicators):
                            ready_rounds = 0
                            continue
                    logger.success("发布按钮已进入稳定可发布状态")
                    return True
            else:
                ready_rounds = 0
                logger.debug(
                    "等待发布就绪: publish_ready={} image_ready={} upload_busy={} pending={} image_count={} image_text={}",
                    publish_ready,
                    image_ready,
                    upload_busy,
                    pending_indicators,
                    page_state["imageCount"],
                    str(page_state["imageText"])[:120],
                )

            await asyncio.sleep(interval)
            elapsed += interval

        logger.warning("等待发布按钮稳定可用超时")
        return False

    def _default_service_images(self) -> list:
        return select_cover_images([], workdir=os.getcwd())

    def resolve_publish_images(self, images: Optional[Sequence[str]] = None) -> list:
        return select_cover_images(list(images or []), workdir=os.getcwd())
    
    def generate_product_content(self, service_type: str) -> Dict[str, str]:
        """使用AI生成商品文案"""
        logger.info(f"生成商品文案: {service_type}")
        prompt = build_publish_prompt(service_type)
        
        try:
            result = normalize_publish_content(
                self.ai_client.complete_json(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的闲鱼服务型商品运营，擅长写清楚需求、规避审核风险、提升点击与转化。",
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
                ),
                service_type,
            )
            logger.success(f"文案生成成功: {result['title']}")
            return result
            
        except Exception as e:
            logger.error(f"AI生成文案失败: {e}")
            # 返回默认文案
            return normalize_publish_content({
                "title": f"{service_type} - 专业服务",
                "description": f"提供专业的{service_type}服务，经验丰富，质量保证。",
                "price": "99",
                "tags": [service_type, "专业", "靠谱"]
            }, service_type)
    
    async def publish_product(self, content: Dict[str, str], images: list = None):
        """发布商品到闲鱼"""
        logger.info("开始发布商品...")
        
        try:
            service_hint = str(content.get("service_type") or content.get("title") or "闲鱼服务")
            content = normalize_publish_content(content, service_hint)
            image_list = self.resolve_publish_images(images)

            # 1. 访问闲鱼发布页面
            logger.info("访问闲鱼发布页面...")
            await self.page.goto("https://www.goofish.com/publish", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 2. 检查是否需要登录
            if "login" in self.page.url.lower():
                logger.warning("需要登录，请扫码登录...")
                await asyncio.sleep(30)  # 等待用户扫码
            
            # 当前 goofish 发布页不展示单独标题框，主文案走富文本描述区。
            logger.info("填写描述...")
            description_parts = [content.get('title', '').strip(), content.get('description', '').strip()]
            description_value = "\n\n".join(part for part in description_parts if part)
            desc_ok = await self._fill_contenteditable(
                [
                    '[contenteditable="true"][data-placeholder*="描述"]',
                    'div.editor--MtHPS94K[contenteditable="true"]',
                    'div[contenteditable="true"]',
                ],
                description_value,
                "描述",
            )
            if not desc_ok:
                raise RuntimeError("无法定位发布页描述输入区")
            await asyncio.sleep(1)

            # 图片尽早上传，让平台处理与后续字段填写并行进行。
            if image_list:
                logger.info("上传封面图: 1张")
                upload_input = self.page.locator('input[type="file"][name="file"]').first
                if await upload_input.count() == 0:
                    raise RuntimeError("无法定位发布页图片上传控件")
                await upload_input.set_input_files(image_list)
                await asyncio.sleep(1)
            else:
                logger.warning("未找到可用封面图，发布按钮可能保持禁用")

            if not await self.wait_for_text_signals(["预计工期", "计价方式"], timeout=15.0):
                logger.warning("预计工期/计价方式字段出现较慢，继续尝试定位")

            schedule_ok = await self._select_option(
                [
                    '.ant-form-item:has(label[title="预计工期"]) .ant-select-selector',
                    '.ant-form-item:has-text("预计工期") .ant-select-selector',
                ],
                ["1-5天", "5-10天", "待议"],
                "预计工期",
            )
            if not schedule_ok:
                logger.warning("未能自动选择预计工期，发布按钮可能保持禁用")
            await asyncio.sleep(1)

            pricing_ok = await self._select_option(
                [
                    '.ant-form-item:has(label[title="计价方式"]) .ant-select-selector',
                    '.ant-form-item:has-text("计价方式") .ant-select-selector',
                ],
                ["元/次", "其他"],
                "计价方式",
            )
            if not pricing_ok:
                logger.warning("未能自动选择计价方式，发布按钮可能保持禁用")
            await asyncio.sleep(1)
            
            # 4. 填写价格
            logger.info("填写价格...")
            price_ok = await self._fill_input(
                [
                    'label[for="itemPriceDTO_priceInCent"] >> xpath=ancestor::div[contains(@class,"ant-form-item")]//input',
                    '.ant-form-item:has(label[title="价格"]) input',
                    'input[placeholder="0.00"]',
                ],
                str(content['price']),
                "价格",
            )
            if not price_ok:
                raise RuntimeError("无法定位发布页价格输入框")
            await asyncio.sleep(1)
            
            # 5. 默认走数字服务场景，切换到“无需邮寄”，避免物流字段干扰。
            await self._click_first(
                [
                    'label:has-text("无需邮寄")',
                    'span:has-text("无需邮寄")',
                    'input[type="radio"][value="3"]',
                ],
                "无需邮寄",
            )
            await asyncio.sleep(1)
            if image_list:
                await self.wait_for_publish_ready(expected_images=len(image_list), timeout=120.0)
            
            # 7. 截图预览
            logger.info("截图预览...")
            await self.page.screenshot(path="data/publish_preview.png")

            publish_ready = await self._publish_button_enabled()
            logger.info(f"发布按钮状态: {'可提交' if publish_ready else '仍禁用'}")
            
            # 8. 发布（需要用户确认）
            logger.warning("⚠️ 请手动点击发布按钮，或按Enter自动发布")
            user_input = input("输入'y'自动点击发布，其他键跳过: ")
            
            if user_input.lower() == 'y':
                publish_btn = await self.page.wait_for_selector('button.publish-button--KBpTVopQ, button:has-text("发布")', timeout=10000)
                await publish_btn.click()
                await asyncio.sleep(3)
                logger.success("✅ 商品发布成功！")
            else:
                logger.info("跳过自动发布，请手动操作")
            
            return True
            
        except Exception as e:
            logger.error(f"发布失败: {e}")
            await self.page.screenshot(path="data/publish_error.png")
            return False
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")


async def main():
    """主流程"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           闲鱼自动发布工具 - AI驱动                         ║
║              Powered by OpenClaw AI                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 1. 选择服务类型
    print("\n📋 请选择要发布的服务类型:")
    print("1. AI文案代写")
    print("2. PPT设计制作")
    print("3. 视频剪辑")
    print("4. Logo设计")
    print("5. 自定义")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    service_map = {
        "1": "AI文案代写",
        "2": "PPT设计制作",
        "3": "视频剪辑",
        "4": "Logo设计"
    }
    
    if choice == "5":
        service_type = input("请输入自定义服务类型: ").strip()
    else:
        service_type = service_map.get(choice, "AI文案代写")
    
    print(f"\n✅ 已选择: {service_type}")
    
    # 2. 初始化发布器
    publisher = XianyuAutoPublisher()
    
    try:
        # 3. 生成文案
        print("\n🤖 AI正在生成爆款文案...")
        content = publisher.generate_product_content(service_type)
        
        print("\n📝 生成的文案:")
        print(f"标题: {content['title']}")
        print(f"价格: ¥{content['price']}")
        print(f"描述:\n{content['description']}")
        print(f"标签: {', '.join(content['tags'])}")
        
        confirm = input("\n是否使用此文案？(y/n): ").strip().lower()
        if confirm != 'y':
            print("已取消发布")
            return
        
        # 4. 初始化浏览器
        print("\n🌐 启动浏览器...")
        await publisher.init_browser(headless=False)  # 非无头模式，方便调试
        
        # 5. 加载Cookie（可选）
        await publisher.load_cookies()
        
        # 6. 发布商品
        print("\n🚀 开始发布...")
        success = await publisher.publish_product(content)
        
        if success:
            print("\n✅ 发布流程完成！")
            print(f"预览截图: data/publish_preview.png")
        else:
            print("\n❌ 发布失败，请查看错误截图: data/publish_error.png")
        
        # 7. 等待用户确认关闭
        input("\n按Enter关闭浏览器...")
        
    finally:
        await publisher.close()


if __name__ == "__main__":
    asyncio.run(main())
