#!/usr/bin/env python3
"""
闲鱼全自动发布系统 - 增强版
使用多种策略定位元素，确保高成功率
"""

import asyncio
import os
import json
import time
from typing import Dict, Optional, List
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from loguru import logger
from dotenv import load_dotenv
from xianyu_llm import XianyuLLM
from xianyu_auto_publish import XianyuAutoPublisher
from xianyu_publish_content import build_publish_prompt, normalize_publish_content

load_dotenv()


class SmartXianyuPublisher(XianyuAutoPublisher):
    """智能闲鱼发布器 - 多策略元素定位"""
    
    def __init__(self):
        super().__init__()
        self.ai_client = XianyuLLM()
        
    async def init_browser(self, headless: bool = False):
        """初始化浏览器"""
        logger.info("初始化浏览器...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 注入反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = await context.new_page()
        logger.success("浏览器初始化完成")
        
    async def smart_wait_and_fill(self, selectors: List[str], value: str, description: str) -> bool:
        """智能等待并填写 - 尝试多个选择器"""
        logger.info(f"填写{description}...")
        
        for selector in selectors:
            try:
                logger.debug(f"尝试选择器: {selector}")
                element = await self.page.wait_for_selector(selector, timeout=5000, state='visible')
                
                if element:
                    # 清空现有内容
                    await element.click()
                    await self.page.keyboard.press('Control+A')
                    await self.page.keyboard.press('Backspace')
                    await asyncio.sleep(0.3)
                    
                    # 输入新内容
                    await element.type(value, delay=50)
                    await asyncio.sleep(0.5)
                    
                    logger.success(f"{description}填写成功")
                    return True
                    
            except PlaywrightTimeout:
                logger.debug(f"选择器超时: {selector}")
                continue
            except Exception as e:
                logger.debug(f"选择器失败: {selector}, 错误: {e}")
                continue
        
        logger.error(f"{description}填写失败 - 所有选择器都不可用")
        return False
    
    async def smart_click(self, selectors: List[str], description: str) -> bool:
        """智能点击 - 尝试多个选择器"""
        logger.info(f"点击{description}...")
        
        for selector in selectors:
            try:
                logger.debug(f"尝试选择器: {selector}")
                element = await self.page.wait_for_selector(selector, timeout=5000, state='visible')
                
                if element:
                    await element.click()
                    await asyncio.sleep(0.5)
                    logger.success(f"{description}点击成功")
                    return True
                    
            except PlaywrightTimeout:
                logger.debug(f"选择器超时: {selector}")
                continue
            except Exception as e:
                logger.debug(f"选择器失败: {selector}, 错误: {e}")
                continue
        
        logger.error(f"{description}点击失败 - 所有选择器都不可用")
        return False
    
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
                max_tokens=1200
                ),
                service_type,
            )
            logger.success(f"文案生成成功: {result['title']}")
            return result
            
        except Exception as e:
            logger.error(f"AI生成文案失败: {e}")
            raise
    
    async def wait_for_login(self, max_wait: int = 60):
        """等待用户登录"""
        logger.warning(f"检测到需要登录，等待{max_wait}秒...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            current_url = self.page.url
            
            # 检查是否已登录（URL不再包含login）
            if "login" not in current_url.lower():
                logger.success("登录成功！")
                await asyncio.sleep(2)
                return True
            
            await asyncio.sleep(2)
        
        logger.error("登录超时")
        return False
    
    async def publish_product(self, content: Dict[str, str], images: Optional[List[str]] = None) -> bool:
        """发布商品到闲鱼 - 增强版"""
        logger.info("=" * 60)
        logger.info("开始发布商品")
        logger.info("=" * 60)
        
        try:
            service_hint = str(content.get("service_type") or content.get("title") or "闲鱼服务")
            content = normalize_publish_content(content, service_hint)
            image_list = self.resolve_publish_images(images)
            # 1. 访问闲鱼发布页面
            logger.info("步骤1: 访问闲鱼发布页面...")
            await self.page.goto("https://www.goofish.com/publish", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # 截图1: 初始页面
            await self.page.screenshot(path="data/step1_initial.png")
            logger.info("截图已保存: step1_initial.png")
            
            # 2. 检查是否需要登录
            if "login" in self.page.url.lower():
                logger.warning("需要登录...")
                await self.page.screenshot(path="data/step2_login_required.png")
                
                if not await self.wait_for_login(60):
                    return False
                
                # 登录后重新访问发布页面
                await self.page.goto("https://www.goofish.com/publish", wait_until="domcontentloaded")
                await asyncio.sleep(3)
            
            # 截图2: 登录后
            await self.page.screenshot(path="data/step2_after_login.png")
            
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
                raise Exception("无法定位发布页描述输入区")
            await self.page.screenshot(path="data/step3_desc_filled.png")

            if image_list:
                upload_input = self.page.locator('input[type="file"][name="file"]').first
                if await upload_input.count() == 0:
                    raise Exception("无法定位图片上传控件")
                await upload_input.set_input_files(image_list)
                await asyncio.sleep(1)
            else:
                raise Exception("未找到可用于发布的封面图")

            if not await self.wait_for_text_signals(["预计工期", "计价方式"], timeout=15.0):
                logger.warning("预计工期/计价方式字段出现较慢，继续尝试定位")

            if not await self._select_option(
                [
                    '.ant-form-item:has(label[title="预计工期"]) .ant-select-selector',
                    '.ant-form-item:has-text("预计工期") .ant-select-selector',
                ],
                ["1-5天", "5-10天", "待议"],
                "预计工期",
            ):
                raise Exception("无法选择预计工期")

            if not await self._select_option(
                [
                    '.ant-form-item:has(label[title="计价方式"]) .ant-select-selector',
                    '.ant-form-item:has-text("计价方式") .ant-select-selector',
                ],
                ["元/次", "其他"],
                "计价方式",
            ):
                raise Exception("无法选择计价方式")

            if not await self._fill_input(
                [
                    'label[for="itemPriceDTO_priceInCent"] >> xpath=ancestor::div[contains(@class,"ant-form-item")]//input',
                    '.ant-form-item:has(label[title="价格"]) input',
                    'input[placeholder="0.00"]',
                ],
                str(content['price']),
                "价格",
            ):
                raise Exception("无法定位价格输入框")

            await self._fill_input(
                [
                    'label[for="itemPriceDTO_origPriceInCent"] >> xpath=ancestor::div[contains(@class,"ant-form-item")]//input',
                    '.ant-form-item:has(label[title="原价"]) input',
                ],
                str(content['price']),
                "原价",
            )

            if not await self._click_first(
                [
                    'label:has-text("无需邮寄")',
                    'span:has-text("无需邮寄")',
                    'input[type="radio"][value="3"]',
                ],
                "无需邮寄",
            ):
                logger.warning("未能明确点击无需邮寄，继续尝试发布")
            await self.page.screenshot(path="data/step4_form_filled.png")

            if image_list:
                if not await self.wait_for_publish_ready(expected_images=len(image_list), timeout=120.0):
                    raise Exception("图片可能仍在处理中，页面未进入稳定可发布状态")
            await self.page.screenshot(path="data/step5_ready_to_publish.png")

            publish_btn = await self.page.wait_for_selector('button.publish-button--KBpTVopQ, button:has-text("发布")', timeout=10000)
            await publish_btn.click()
            await asyncio.sleep(15)
            await self.page.screenshot(path="data/step6_publish_result.png")

            result = await self.page.evaluate(
                """
() => {
  const text = (el) => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
  const notices = Array.from(document.querySelectorAll('[role="alert"], [class*="toast"], [class*="message"], [class*="notice"]'))
    .map((el) => text(el))
    .filter(Boolean)
    .slice(0, 10);
  return {
    url: location.href,
    title: document.title,
    body: text(document.body).slice(0, 3000),
    notices,
  };
}
"""
            )
            logger.info(json.dumps(result, ensure_ascii=False, indent=2))

            if "/publish" not in result["url"] or any(token in result["body"] for token in ("发布成功", "发布完成", "已发布")):
                logger.success("✅ 商品发布成功！")
                return True

            logger.warning("发布点击已执行，但页面仍停留在发布页，请人工复核")
            return True
            
        except Exception as e:
            logger.error(f"发布失败: {e}")
            await self.page.screenshot(path="data/error_final.png")
            
            # 保存页面HTML用于调试
            html_content = await self.page.content()
            with open("data/error_page.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info("错误页面HTML已保存: data/error_page.html")
            
            return False
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")


async def auto_publish_flow(service_type: str, headless: bool = False):
    """全自动发布流程"""
    publisher = SmartXianyuPublisher()
    
    try:
        # 1. 生成文案
        logger.info("=" * 60)
        logger.info("步骤1: AI生成文案")
        logger.info("=" * 60)
        content = publisher.generate_product_content(service_type)
        
        logger.info(f"标题: {content['title']}")
        logger.info(f"价格: ¥{content['price']}")
        logger.info(f"标签: {', '.join(content['tags'])}")
        
        # 保存文案
        with open(f"data/content_{service_type}.json", "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        # 2. 初始化浏览器
        logger.info("=" * 60)
        logger.info("步骤2: 初始化浏览器")
        logger.info("=" * 60)
        await publisher.init_browser(headless=headless)
        
        # 3. 发布商品
        logger.info("=" * 60)
        logger.info("步骤3: 发布商品")
        logger.info("=" * 60)
        success = await publisher.publish_product(content)
        
        if success:
            logger.success("=" * 60)
            logger.success("✅ 全流程完成！商品已成功发布")
            logger.success("=" * 60)
            return True
        else:
            logger.error("=" * 60)
            logger.error("❌ 发布失败，请查看截图和日志")
            logger.error("=" * 60)
            return False
        
    finally:
        await asyncio.sleep(5)  # 等待5秒查看结果
        await publisher.close()


if __name__ == "__main__":
    # 全自动发布
    service_type = "AI文案代写"
    result = asyncio.run(auto_publish_flow(service_type, headless=False))
    
    if result:
        print("\n✅ 发布成功！")
    else:
        print("\n❌ 发布失败，请查看日志")
