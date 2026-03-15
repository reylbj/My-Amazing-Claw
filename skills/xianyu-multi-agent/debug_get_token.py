#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本：对比独立测试和业务代码的差异
使用方法: python debug_get_token.py "your_cookie_string" "device_id"
"""

import sys
import time
import json
import requests
import hashlib
from typing import Dict, Optional


def generate_sign(t: str, token: str, data: str) -> str:
    """生成签名"""
    app_key = "34839810"
    msg = f"{token}&{t}&{app_key}&{data}"
    
    # 使用MD5生成签名
    md5_hash = hashlib.md5()
    md5_hash.update(msg.encode('utf-8'))
    return md5_hash.hexdigest()


def trans_cookies(cookies_str: str) -> Dict[str, str]:
    """解析cookie字符串为字典 - 模拟业务代码的逻辑"""
    cookies = {}
    for cookie in cookies_str.split("; "):
        try:
            parts = cookie.split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
        except:
            continue
    return cookies


def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
    """解析cookie字符串为字典 - 独立测试的逻辑"""
    cookies = {}
    for cookie in cookie_str.split("; "):
        try:
            parts = cookie.split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
        except:
            continue
    return cookies


def clear_duplicate_cookies(session):
    """模拟业务代码的清理重复cookies逻辑"""
    # 创建一个新的CookieJar
    new_jar = requests.cookies.RequestsCookieJar()
    
    # 记录已经添加过的cookie名称
    added_cookies = set()
    
    # 按照cookies列表的逆序遍历（最新的通常在后面）
    cookie_list = list(session.cookies)
    cookie_list.reverse()
    
    for cookie in cookie_list:
        # 如果这个cookie名称还没有添加过，就添加到新jar中
        if cookie.name not in added_cookies:
            new_jar.set_cookie(cookie)
            added_cookies.add(cookie.name)
    
    # 替换session的cookies
    session.cookies = new_jar


def create_business_session(cookie_str: str):
    """模拟业务代码创建session的方式"""
    session = requests.Session()
    session.headers.update({
        'accept': 'application/json',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'origin': 'https://www.goofish.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.goofish.com/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    })
    
    # 使用业务代码的方式设置cookies
    cookies = trans_cookies(cookie_str)
    session.cookies.update(cookies)
    
    # 模拟业务代码可能调用的清理重复cookies
    clear_duplicate_cookies(session)
    
    return session


def create_test_session(cookie_str: str):
    """独立测试创建session的方式"""
    session = requests.Session()
    session.headers.update({
        'accept': 'application/json',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'origin': 'https://www.goofish.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.goofish.com/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    })
    
    # 使用独立测试的方式设置cookies
    cookies_dict = parse_cookie_string(cookie_str)
    for key, value in cookies_dict.items():
        session.cookies.set(key, value)
    
    return session


def test_get_token_with_session(session, device_id: str, method_name: str) -> Optional[dict]:
    """使用指定session测试get_token方法"""
    print(f"\n{'='*20} {method_name} {'='*20}")
    
    # 打印cookie状态
    print(f"Cookie数量: {len(session.cookies)}")
    cookie_names = [cookie.name for cookie in session.cookies]
    print(f"Cookie名称: {cookie_names}")
    
    # 检查关键cookie
    _m_h5_tk = session.cookies.get('_m_h5_tk', '')
    unb = session.cookies.get('unb', '')
    print(f"_m_h5_tk: {_m_h5_tk[:30]}..." if _m_h5_tk else "_m_h5_tk: 未找到")
    print(f"unb: {unb}")
    
    # 构造请求参数
    params = {
        'jsv': '2.7.2',
        'appKey': '34839810',
        't': str(int(time.time()) * 1000),
        'sign': '',
        'v': '1.0',
        'type': 'originaljson',
        'accountSite': 'xianyu',
        'dataType': 'json',
        'timeout': '20000',
        'api': 'mtop.taobao.idlemessage.pc.login.token',
        'sessionOption': 'AutoLoginOnly',
        'spm_cnt': 'a21ybx.im.0.0',
    }
    
    data_val = f'{{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"{device_id}"}}'
    data = {
        'data': data_val,
    }
    
    # 获取token
    token = _m_h5_tk.split('_')[0] if _m_h5_tk else ''
    print(f"提取的token: {token[:20]}..." if token else "提取的token: 空")
    
    # 生成签名
    sign = generate_sign(params['t'], token, data_val)
    params['sign'] = sign
    
    try:
        # 发送请求
        response = session.post(
            'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', 
            params=params, 
            data=data
        )
        
        print(f"响应状态码: {response.status_code}")
        
        # 解析响应
        try:
            res_json = response.json()
            ret_value = res_json.get('ret', [])
            success = any('SUCCESS::调用成功' in str(ret) for ret in ret_value)
            
            print(f"调用结果: {'✅ 成功' if success else '❌ 失败'}")
            print(f"ret字段: {ret_value}")
            
            if not success:
                print(f"完整响应: {json.dumps(res_json, indent=2, ensure_ascii=False)}")
                
            return res_json
            
        except json.JSONDecodeError as e:
            print(f"❌ 响应不是有效的JSON格式: {e}")
            print(f"原始响应: {response.text[:200]}...")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return None


def debug_get_token(cookie_str: str, device_id: str = "test-device-123"):
    """对比调试get_token方法"""
    print(f"开始对比调试get_token方法...")
    print(f"设备ID: {device_id}")
    print(f"Cookie字符串长度: {len(cookie_str)}")
    
    # 测试独立测试的方式
    test_session = create_test_session(cookie_str)
    test_result = test_get_token_with_session(test_session, device_id, "独立测试方式")
    
    # 测试业务代码的方式
    business_session = create_business_session(cookie_str)
    business_result = test_get_token_with_session(business_session, device_id, "业务代码方式")
    
    print(f"\n{'='*60}")
    print("对比结果:")
    
    test_success = test_result and any('SUCCESS::调用成功' in str(ret) for ret in test_result.get('ret', []))
    business_success = business_result and any('SUCCESS::调用成功' in str(ret) for ret in business_result.get('ret', []))
    
    print(f"独立测试方式: {'✅ 成功' if test_success else '❌ 失败'}")
    print(f"业务代码方式: {'✅ 成功' if business_success else '❌ 失败'}")
    
    if test_success != business_success:
        print(f"\n🔍 发现差异！原因可能是:")
        print(f"1. Cookie设置方式不同 (update vs set)")
        print(f"2. clear_duplicate_cookies方法的影响")
        print(f"3. Session创建和配置的细微差别")
        
        # 详细对比cookie状态
        print(f"\n详细Cookie对比:")
        print(f"独立测试Session cookies: {dict(test_session.cookies)}")
        print(f"业务代码Session cookies: {dict(business_session.cookies)}")
    else:
        print(f"\n✅ 两种方式结果一致")
    
    print("="*60)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python debug_get_token.py \"cookie_string\" [device_id]")
        return
    
    cookie_str = sys.argv[1]
    device_id = sys.argv[2] if len(sys.argv) > 2 else "test-device-123"
    
    if not cookie_str:
        print("❌ Cookie字符串不能为空")
        return
    
    debug_get_token(cookie_str, device_id)


if __name__ == "__main__":
    main()