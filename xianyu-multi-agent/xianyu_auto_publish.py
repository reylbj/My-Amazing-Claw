#!/usr/bin/env python3
"""
闲鱼自动发布脚本 - 基于Playwright
支持AI生成文案 + 自动发布商品
"""

import asyncio
import os
import json
from typing import Dict, Optional
from playwright.async_api import async_playwright, Page, Browser
from openai import OpenAI
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class XianyuAutoPublisher:
    """闲鱼自动发布器"""
    
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
    
    def generate_product_content(self, service_type: str) -> Dict[str, str]:
        """使用AI生成商品文案"""
        logger.info(f"生成商品文案: {service_type}")
        
        prompt = f"""
你是一个闲鱼爆款文案专家。请为以下服务生成一个吸引人的闲鱼商品发布内容：

服务类型: {service_type}

要求:
1. 标题: 15-30字，吸引眼球，包含核心卖点
2. 描述: 200-500字，分段清晰，突出优势和案例
3. 价格: 给出合理的定价区间（元）
4. 标签: 3-5个相关标签

请以JSON格式返回:
{{
  "title": "标题",
  "description": "描述",
  "price": "价格",
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
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            # 提取JSON部分
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            logger.success(f"文案生成成功: {result['title']}")
            return result
            
        except Exception as e:
            logger.error(f"AI生成文案失败: {e}")
            # 返回默认文案
            return {
                "title": f"{service_type} - 专业服务",
                "description": f"提供专业的{service_type}服务，经验丰富，质量保证。",
                "price": "99",
                "tags": [service_type, "专业", "靠谱"]
            }
    
    async def publish_product(self, content: Dict[str, str], images: list = None):
        """发布商品到闲鱼"""
        logger.info("开始发布商品...")
        
        try:
            # 1. 访问闲鱼发布页面
            logger.info("访问闲鱼发布页面...")
            await self.page.goto("https://www.goofish.com/publish", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 2. 检查是否需要登录
            if "login" in self.page.url.lower():
                logger.warning("需要登录，请扫码登录...")
                await asyncio.sleep(30)  # 等待用户扫码
            
            # 3. 填写标题
            logger.info("填写标题...")
            title_input = await self.page.wait_for_selector('input[placeholder*="标题"]', timeout=10000)
            await title_input.fill(content['title'])
            await asyncio.sleep(1)
            
            # 4. 填写描述
            logger.info("填写描述...")
            desc_input = await self.page.wait_for_selector('textarea[placeholder*="描述"]', timeout=10000)
            await desc_input.fill(content['description'])
            await asyncio.sleep(1)
            
            # 5. 填写价格
            logger.info("填写价格...")
            price_input = await self.page.wait_for_selector('input[placeholder*="价格"]', timeout=10000)
            await price_input.fill(content['price'])
            await asyncio.sleep(1)
            
            # 6. 上传图片（如果有）
            if images:
                logger.info(f"上传图片: {len(images)}张")
                upload_input = await self.page.wait_for_selector('input[type="file"]', timeout=10000)
                for img in images:
                    await upload_input.set_input_files(img)
                    await asyncio.sleep(2)
            
            # 7. 添加标签
            if content.get('tags'):
                logger.info("添加标签...")
                for tag in content['tags'][:3]:  # 最多3个标签
                    try:
                        tag_input = await self.page.wait_for_selector('input[placeholder*="标签"]', timeout=5000)
                        await tag_input.fill(tag)
                        await asyncio.sleep(0.5)
                        await self.page.keyboard.press('Enter')
                    except:
                        pass
            
            # 8. 截图预览
            logger.info("截图预览...")
            await self.page.screenshot(path="data/publish_preview.png")
            
            # 9. 发布（需要用户确认）
            logger.warning("⚠️ 请手动点击发布按钮，或按Enter自动发布")
            user_input = input("输入'y'自动点击发布，其他键跳过: ")
            
            if user_input.lower() == 'y':
                publish_btn = await self.page.wait_for_selector('button:has-text("发布")', timeout=10000)
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
