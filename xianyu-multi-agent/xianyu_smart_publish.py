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
from openai import OpenAI
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class SmartXianyuPublisher:
    """智能闲鱼发布器 - 多策略元素定位"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.ai_client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL")
        )
        
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
        
        prompt = f"""
你是一个闲鱼爆款文案专家。请为以下服务生成一个吸引人的闲鱼商品发布内容：

服务类型: {service_type}

要求:
1. 标题: 20-30字，吸引眼球，包含核心卖点，用｜分隔关键词
2. 描述: 300-500字，使用emoji，分段清晰，突出优势和案例
3. 价格: 给出合理的起步价（元），要有吸引力，9.9-29.9之间
4. 标签: 3-5个相关标签

请以JSON格式返回:
{{
  "title": "标题",
  "description": "描述（包含emoji和换行）",
  "price": "价格数字",
  "tags": ["标签1", "标签2", "标签3"]
}}
"""
        
        try:
            response = self.ai_client.chat.completions.create(
                model=os.getenv("MODEL_NAME"),
                messages=[
                    {"role": "system", "content": "你是一个专业的闲鱼文案撰写专家，擅长写出高转化率的商品描述。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1200
            )
            
            content = response.choices[0].message.content
            
            # 提取JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # 清理控制字符
            import re
            content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
            
            result = json.loads(content)
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
    
    async def publish_product(self, content: Dict[str, str]) -> bool:
        """发布商品到闲鱼 - 增强版"""
        logger.info("=" * 60)
        logger.info("开始发布商品")
        logger.info("=" * 60)
        
        try:
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
            
            # 3. 填写标题 - 多种选择器策略
            title_selectors = [
                'input[placeholder*="标题"]',
                'input[placeholder*="title"]',
                'input[placeholder*="商品"]',
                'input[name="title"]',
                'input[id*="title"]',
                '.title-input input',
                '[data-spm*="title"] input',
                'textarea[placeholder*="标题"]'
            ]
            
            if not await self.smart_wait_and_fill(title_selectors, content['title'], "标题"):
                # 尝试通过页面分析找到输入框
                logger.warning("使用备用策略定位标题输入框...")
                all_inputs = await self.page.query_selector_all('input[type="text"], textarea')
                if all_inputs and len(all_inputs) > 0:
                    await all_inputs[0].fill(content['title'])
                    logger.success("标题填写成功（备用策略）")
                else:
                    raise Exception("无法定位标题输入框")
            
            await self.page.screenshot(path="data/step3_title_filled.png")
            
            # 4. 填写描述
            desc_selectors = [
                'textarea[placeholder*="描述"]',
                'textarea[placeholder*="详情"]',
                'textarea[placeholder*="description"]',
                'textarea[name="description"]',
                '.description-input textarea',
                '[data-spm*="desc"] textarea',
                'div[contenteditable="true"]'
            ]
            
            if not await self.smart_wait_and_fill(desc_selectors, content['description'], "描述"):
                # 备用策略
                logger.warning("使用备用策略定位描述输入框...")
                all_textareas = await self.page.query_selector_all('textarea')
                if all_textareas and len(all_textareas) > 0:
                    # 通常第二个textarea是描述
                    target_textarea = all_textareas[1] if len(all_textareas) > 1 else all_textareas[0]
                    await target_textarea.fill(content['description'])
                    logger.success("描述填写成功（备用策略）")
                else:
                    raise Exception("无法定位描述输入框")
            
            await self.page.screenshot(path="data/step4_desc_filled.png")
            
            # 5. 填写价格
            price_selectors = [
                'input[placeholder*="价格"]',
                'input[placeholder*="price"]',
                'input[name="price"]',
                'input[type="number"]',
                '.price-input input',
                '[data-spm*="price"] input'
            ]
            
            if not await self.smart_wait_and_fill(price_selectors, content['price'], "价格"):
                # 备用策略
                logger.warning("使用备用策略定位价格输入框...")
                all_number_inputs = await self.page.query_selector_all('input[type="number"]')
                if all_number_inputs and len(all_number_inputs) > 0:
                    await all_number_inputs[0].fill(content['price'])
                    logger.success("价格填写成功（备用策略）")
                else:
                    logger.warning("无法定位价格输入框，跳过")
            
            await self.page.screenshot(path="data/step5_price_filled.png")
            
            # 6. 添加标签（可选）
            logger.info("添加标签...")
            for i, tag in enumerate(content.get('tags', [])[:3]):
                tag_selectors = [
                    'input[placeholder*="标签"]',
                    'input[placeholder*="tag"]',
                    '.tag-input input'
                ]
                
                try:
                    for selector in tag_selectors:
                        try:
                            tag_input = await self.page.wait_for_selector(selector, timeout=3000)
                            if tag_input:
                                await tag_input.fill(tag)
                                await asyncio.sleep(0.3)
                                await self.page.keyboard.press('Enter')
                                logger.info(f"标签 {i+1} 添加成功: {tag}")
                                break
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"标签添加失败: {e}")
                    break
            
            await self.page.screenshot(path="data/step6_tags_added.png")
            
            # 7. 点击发布按钮
            logger.info("步骤7: 点击发布按钮...")
            publish_selectors = [
                'button:has-text("发布")',
                'button:has-text("立即发布")',
                'button:has-text("确认发布")',
                'button[type="submit"]',
                '.publish-btn',
                '.submit-btn',
                '[data-spm*="publish"]'
            ]
            
            if await self.smart_click(publish_selectors, "发布按钮"):
                await asyncio.sleep(3)
                await self.page.screenshot(path="data/step7_published.png")
                logger.success("✅ 商品发布成功！")
                return True
            else:
                logger.error("无法找到发布按钮")
                await self.page.screenshot(path="data/step7_publish_failed.png")
                return False
            
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
