#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的get_token方法测试脚本
使用方法: python test_get_token.py "your_cookie_string" "device_id"
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


def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
    """解析cookie字符串为字典"""
    cookies = {}
    for cookie in cookie_str.split("; "):
        try:
            parts = cookie.split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
        except:
            continue
    return cookies


def test_get_token(cookie_str: str, device_id: str = "test-device-123") -> Optional[dict]:
    """
    测试get_token方法
    
    Args:
        cookie_str: cookie字符串，格式如 "key1=value1; key2=value2; ..."
        device_id: 设备ID，默认为 "test-device-123"
    
    Returns:
        API响应的JSON数据或None
    """
    print(f"开始测试get_token方法...")
    print(f"使用设备ID: {device_id}")
    print(f"Cookie字符串长度: {len(cookie_str)}")
    
    # 创建session
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
    
    # 解析并设置cookies
    cookies_dict = parse_cookie_string(cookie_str)
    print(f"解析到的cookie数量: {len(cookies_dict)}")
    for key in cookies_dict.keys():
        session.cookies.set(key, cookies_dict[key])
    
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
    token = session.cookies.get('_m_h5_tk', '').split('_')[0] if session.cookies.get('_m_h5_tk') else ''
    print(f"从cookie中提取的token: {token[:20]}..." if token else "未找到_m_h5_tk cookie")
    
    # 生成签名
    sign = generate_sign(params['t'], token, data_val)
    params['sign'] = sign
    
    print(f"\n请求参数:")
    print(f"URL: https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/")
    print(f"Params: {json.dumps(params, indent=2, ensure_ascii=False)}")
    print(f"Data: {json.dumps(data, indent=2, ensure_ascii=False)}")
    
    try:
        # 发送请求
        print(f"\n发送请求...")
        response = requests.post(
            'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', 
            params=params, 
            data=data,
            cookies=session.cookies,
            headers=session.headers
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        # 检查是否有新的cookies
        if response.cookies:
            print(f"响应中的新cookies: {dict(response.cookies)}")
        
        # 解析响应
        try:
            res_json = response.json()
            print(f"\n响应JSON:")
            print(json.dumps(res_json, indent=2, ensure_ascii=False))
            
            # 分析响应
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                print(f"\n返回状态分析:")
                print(f"ret字段: {ret_value}")
                
                # 检查是否成功
                success = any('SUCCESS::调用成功' in str(ret) for ret in ret_value)
                print(f"调用是否成功: {success}")
                
                if success:
                    print("✅ Token获取成功!")
                else:
                    print("❌ Token获取失败")
                    
            return res_json
            
        except json.JSONDecodeError as e:
            print(f"❌ 响应不是有效的JSON格式: {e}")
            print(f"原始响应内容: {response.text[:500]}...")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return None


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_get_token.py \"cookie_string\" [device_id]")
        print("\n示例:")
        print("  python test_get_token.py \"_m_h5_tk=value1; cookie2=value2; ...\" \"my-device-123\"")
        return
    
    cookie_str = sys.argv[1]
    device_id = sys.argv[2] if len(sys.argv) > 2 else "test-device-123"
    
    if not cookie_str:
        print("❌ Cookie字符串不能为空")
        return
    
    print("="*60)
    print("开始测试get_token接口")
    print("="*60)
    
    result = test_get_token(cookie_str, device_id)
    
    print("\n" + "="*60)
    if result:
        print("测试完成，请查看上方输出结果")
    else:
        print("测试失败，请检查cookie和网络连接")
    print("="*60)


if __name__ == "__main__":
    main()