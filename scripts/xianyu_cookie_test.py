#!/usr/bin/env python3
"""
闲鱼Cookie有效性测试
"""
import os
import sys
import requests
from pathlib import Path

def load_xianyu_cookie():
    """从 .credentials 读取闲鱼Cookie"""
    cred_path = Path(__file__).parent.parent / '.credentials'
    
    if not cred_path.exists():
        print("❌ .credentials 文件不存在")
        return None
    
    with open(cred_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('XIANYU_COOKIE='):
                cookie = line.split('=', 1)[1].strip()
                return cookie
    
    print("❌ 未找到 XIANYU_COOKIE")
    return None

def test_cookie(cookie):
    """测试Cookie有效性"""
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': 'https://www.xianyu.com/'
    }
    
    # 测试方法：访问闲鱼首页，检查是否包含登录态标识
    test_url = 'https://www.xianyu.com/'
    
    try:
        print("🔍 测试闲鱼Cookie有效性...")
        response = requests.get(test_url, headers=headers, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            html = response.text
            
            # 检查关键登录态标识
            if 'tracknick' in cookie and ('unb=' in cookie or 't=' in cookie):
                # Cookie包含必要字段
                if '登录' not in html or 'isLogin":true' in html or 'userId' in html:
                    print("✅ Cookie有效！包含登录态标识")
                    
                    # 尝试提取用户昵称
                    if 'tracknick=' in cookie:
                        nick = cookie.split('tracknick=')[1].split(';')[0]
                        print(f"👤 用户昵称: {nick}")
                    
                    return True
                else:
                    print("⚠️ Cookie可能已失效，页面显示未登录")
                    return False
            else:
                print("❌ Cookie缺少必要字段（tracknick/unb/t）")
                return False
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def main():
    print("=" * 50)
    print("闲鱼Cookie有效性测试")
    print("=" * 50)
    
    # 读取Cookie
    cookie = load_xianyu_cookie()
    if not cookie:
        sys.exit(1)
    
    print(f"📝 Cookie长度: {len(cookie)} 字符")
    print(f"🔑 Cookie前50字符: {cookie[:50]}...")
    print()
    
    # 测试有效性
    if test_cookie(cookie):
        print("\n✅ 闲鱼Cookie配置成功，可以正常使用！")
        sys.exit(0)
    else:
        print("\n❌ Cookie可能已失效，请重新登录Chrome获取")
        sys.exit(1)

if __name__ == '__main__':
    main()
