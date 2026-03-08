#!/usr/bin/env python3
"""
闲鱼API自动抓包 - 使用Playwright记录发布流程的所有请求
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

class XianyuAPICapturer:
    """闲鱼API抓包器"""
    
    def __init__(self):
        self.cookie = self._load_cookie()
        self.captured_requests = []
        
    def _load_cookie(self) -> str:
        """从 .credentials 读取Cookie"""
        cred_path = Path(__file__).parent.parent / '.credentials'
        with open(cred_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('XIANYU_COOKIE='):
                    return line.split('=', 1)[1].strip()
        raise ValueError("❌ 未找到 XIANYU_COOKIE")
    
    def _parse_cookie(self) -> list:
        """解析Cookie字符串为Playwright格式"""
        cookies = []
        for item in self.cookie.split('; '):
            if '=' in item:
                name, value = item.split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.goofish.com',
                    'path': '/'
                })
        return cookies
    
    async def capture_publish_flow(self):
        """抓取发布流程的所有API请求"""
        print("🚀 启动Playwright浏览器...")
        
        async with async_playwright() as p:
            # 启动浏览器（有头模式，方便观察）
            browser = await p.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            )
            
            # 注入Cookie
            print("🔑 注入Cookie...")
            await context.add_cookies(self._parse_cookie())
            
            page = await context.new_page()
            
            # 监听所有网络请求
            async def handle_request(request):
                """记录请求"""
                url = request.url
                # 只记录API请求
                if any(keyword in url for keyword in ['api', 'mtop', 'h5api', 'gw.alicdn.com']):
                    req_data = {
                        'url': url,
                        'method': request.method,
                        'headers': request.headers,
                        'post_data': request.post_data if request.method == 'POST' else None
                    }
                    self.captured_requests.append(req_data)
                    print(f"📡 捕获请求: {request.method} {url[:80]}...")
            
            async def handle_response(response):
                """记录响应"""
                url = response.url
                if any(keyword in url for keyword in ['api', 'mtop', 'h5api', 'gw.alicdn.com']):
                    try:
                        body = await response.text()
                        # 找到对应的请求并添加响应
                        for req in self.captured_requests:
                            if req['url'] == url and 'response' not in req:
                                req['response'] = {
                                    'status': response.status,
                                    'headers': response.headers,
                                    'body': body[:1000]  # 只保存前1000字符
                                }
                                break
                        print(f"✅ 响应: {response.status} {url[:80]}...")
                    except:
                        pass
            
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # 访问发布页面
            print("\n📄 打开发布页面...")
            try:
                await page.goto('https://www.goofish.com/publish', wait_until='networkidle', timeout=30000)
                print("✅ 页面加载完成")
            except Exception as e:
                print(f"⚠️ 页面加载超时（正常，继续）: {e}")
            
            # 等待页面稳定
            await asyncio.sleep(3)
            
            print("\n🔍 等待60秒，观察页面并手动操作...")
            print("   你可以：")
            print("   1. 检查是否已登录")
            print("   2. 尝试填写发布表单")
            print("   3. 上传图片")
            print("   4. 点击发布按钮")
            print("   所有请求都会被自动记录\n")
            
            # 等待60秒让用户手动操作
            await asyncio.sleep(60)
            
            print("\n💾 保存抓包结果...")
            output_path = Path(__file__).parent.parent / 'logs' / 'xianyu_api_capture.json'
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.captured_requests, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 已保存 {len(self.captured_requests)} 个请求到: {output_path}")
            
            await browser.close()
            
            return self.captured_requests

async def main():
    print("=" * 60)
    print("闲鱼API自动抓包工具")
    print("=" * 60)
    print()
    
    try:
        capturer = XianyuAPICapturer()
        requests = await capturer.capture_publish_flow()
        
        print("\n" + "=" * 60)
        print(f"✅ 抓包完成！共捕获 {len(requests)} 个API请求")
        print("=" * 60)
        
        # 分析关键请求
        print("\n🔍 关键请求分析:")
        for req in requests:
            url = req['url']
            if 'upload' in url.lower() or 'image' in url.lower():
                print(f"📸 图片上传: {url}")
            elif 'publish' in url.lower() or 'submit' in url.lower():
                print(f"📝 商品发布: {url}")
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())
