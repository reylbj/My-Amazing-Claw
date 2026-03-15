#!/usr/bin/env python3
"""
闲鱼Cookie有效性测试
"""
import os
import sys
import requests
from pathlib import Path

def parse_cookie(cookie):
    parsed = {}
    for item in cookie.split('; '):
        if '=' not in item:
            continue
        name, value = item.split('=', 1)
        parsed[name] = value
    return parsed

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
    parsed = parse_cookie(cookie)
    headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Origin': 'https://www.goofish.com',
        'Referer': 'https://www.goofish.com/'
    }
    
    test_url = 'https://passport.goofish.com/newlogin/hasLogin.do'
    params = {
        'appName': 'xianyu',
        'fromSite': '77',
    }
    data = {
        'hid': parsed.get('unb', ''),
        'ltl': 'true',
        'appName': 'xianyu',
        'appEntrance': 'web',
        '_csrf_token': parsed.get('XSRF-TOKEN', ''),
        'umidToken': '',
        'hsiz': parsed.get('cookie2', ''),
        'bizParams': 'taobaoBizLoginFrom=web',
        'mainPage': 'false',
        'isMobile': 'false',
        'lang': 'zh_CN',
        'returnUrl': '',
        'fromSite': '77',
        'isIframe': 'true',
        'documentReferer': 'https://www.goofish.com/',
        'defaultView': 'hasLogin',
        'umidTag': 'SERVER',
        'deviceId': parsed.get('cna', ''),
    }
    
    try:
        print("🔍 测试闲鱼Cookie有效性...")
        response = requests.post(test_url, headers=headers, params=params, data=data, timeout=10)
        
        if response.status_code == 200:
            payload = response.json()
            if payload.get('content', {}).get('success'):
                print("✅ Cookie有效！hasLogin接口返回成功")
                return True
            print(f"⚠️ hasLogin返回未登录: {payload}")
            return False
        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 网络或DNS错误，暂时无法判定Cookie有效性: {str(e)}")
        return None
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
    print(f"🧩 Cookie字段数: {len([item for item in cookie.split('; ') if '=' in item])}")
    print()
    
    # 测试有效性
    result = test_cookie(cookie)
    if result is True:
        print("\n✅ 闲鱼Cookie配置成功，可以正常使用！")
        sys.exit(0)
    if result is False:
        print("\n❌ Cookie可能已失效，请重新登录Chrome获取")
        sys.exit(1)
    print("\n⚠️ 当前环境无法连通闲鱼，未对Cookie有效性下结论")
    sys.exit(2)

if __name__ == '__main__':
    main()
