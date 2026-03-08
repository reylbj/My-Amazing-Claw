#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深入分析session.cookies.update()对cookie的影响
检查domain、path等属性是否影响cookie发送
"""

import sys
import requests
from http.cookiejar import Cookie
from utils.xianyu_utils import trans_cookies


def analyze_cookie_update_behavior(cookie_str: str):
    """
    深入分析session.cookies.update()的行为
    """
    print("=" * 80)
    print("深入分析session.cookies.update()对cookie的影响")
    print("=" * 80)
    
    # 1. 解析原始cookie
    print("\n--- 步骤1: 解析原始cookie字符串 ---")
    cookies_dict = trans_cookies(cookie_str)
    print(f"解析结果: {len(cookies_dict)} 个cookies")
    
    for name, value in cookies_dict.items():
        print(f"  {name}: {value[:30]}..." if len(value) > 30 else f"  {name}: {value}")
    
    # 2. 创建session并检查update前的状态
    print("\n--- 步骤2: 创建session ---")
    session = requests.Session()
    print(f"初始session.cookies数量: {len(session.cookies)}")
    
    # 3. 执行update操作
    print("\n--- 步骤3: 执行session.cookies.update() ---")
    session.cookies.update(cookies_dict)
    print(f"update后session.cookies数量: {len(session.cookies)}")
    
    # 4. 详细检查每个cookie的属性
    print("\n--- 步骤4: 检查cookie详细属性 ---")
    for cookie in session.cookies:
        print(f"\nCookie: {cookie.name}")
        print(f"  value: {cookie.value[:30]}..." if len(cookie.value) > 30 else f"  value: {cookie.value}")
        print(f"  domain: {cookie.domain}")
        print(f"  path: {cookie.path}")
        print(f"  secure: {cookie.secure}")
        print(f"  expires: {cookie.expires}")
        print(f"  version: {cookie.version}")
        print(f"  port: {cookie.port}")
        print(f"  rest: {cookie.rest}")
    
    # 5. 测试cookie是否会被发送到目标域
    print("\n--- 步骤5: 测试cookie发送规则 ---")
    target_url = "https://h5api.m.goofish.com/"
    
    # 创建一个测试请求，看看哪些cookie会被包含
    req = requests.Request('GET', target_url)
    prepped = session.prepare_request(req)
    
    print(f"发送到 {target_url} 的cookie:")
    if 'Cookie' in prepped.headers:
        cookie_header = prepped.headers['Cookie']
        print(f"  Cookie header: {cookie_header}")
        
        # 分析哪些cookie被包含
        sent_cookies = {}
        for cookie_pair in cookie_header.split('; '):
            if '=' in cookie_pair:
                name, value = cookie_pair.split('=', 1)
                sent_cookies[name] = value
        
        print(f"  发送的cookie数量: {len(sent_cookies)}")
        for name, value in sent_cookies.items():
            print(f"    {name}: {value[:20]}..." if len(value) > 20 else f"    {name}: {value}")
            
        # 检查关键cookie是否被发送
        key_cookies = ['_m_h5_tk', 'unb', 'XSRF-TOKEN', 'cookie2']
        print(f"\n  关键cookie发送状态:")
        for key_cookie in key_cookies:
            if key_cookie in sent_cookies:
                print(f"    ✅ {key_cookie}: 已发送")
            else:
                original_value = cookies_dict.get(key_cookie, '')
                if original_value:
                    print(f"    ❌ {key_cookie}: 未发送 (原始值存在: {original_value[:20]}...)")
                else:
                    print(f"    ⚪ {key_cookie}: 未发送 (原始值不存在)")
    else:
        print("  ❌ 没有Cookie header被设置!")
    
    # 6. 手动设置cookie测试
    print("\n--- 步骤6: 测试手动设置cookie ---")
    session2 = requests.Session()
    
    # 手动为关键域设置cookie
    for name, value in cookies_dict.items():
        # 为goofish.com域设置cookie
        cookie = Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain='.goofish.com',
            domain_specified=True,
            domain_initial_dot=True,
            path='/',
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={}
        )
        session2.cookies.set_cookie(cookie)
    
    print(f"手动设置后session2.cookies数量: {len(session2.cookies)}")
    
    # 测试手动设置的cookie发送
    req2 = requests.Request('GET', target_url)
    prepped2 = session2.prepare_request(req2)
    
    if 'Cookie' in prepped2.headers:
        cookie_header2 = prepped2.headers['Cookie']
        print(f"手动设置后发送的Cookie header: {cookie_header2[:100]}...")
        
        sent_cookies2 = {}
        for cookie_pair in cookie_header2.split('; '):
            if '=' in cookie_pair:
                name, value = cookie_pair.split('=', 1)
                sent_cookies2[name] = value
        
        print(f"手动设置后发送的cookie数量: {len(sent_cookies2)}")
        
        print(f"\n比较两种方式的差异:")
        print(f"  update()方式发送数量: {len(sent_cookies) if 'sent_cookies' in locals() else 0}")
        print(f"  手动设置发送数量: {len(sent_cookies2)}")
    
    return session, session2


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python cookie_update_analysis.py \"cookie_string\"")
        return
    
    cookie_str = sys.argv[1]
    if not cookie_str:
        print("❌ Cookie字符串不能为空")
        return
    
    analyze_cookie_update_behavior(cookie_str)


if __name__ == "__main__":
    main()