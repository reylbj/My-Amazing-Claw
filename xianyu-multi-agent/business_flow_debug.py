#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整业务流程调试脚本 - 模拟实际的AccountManager初始化和get_token调用
使用方法: python business_flow_debug.py "your_cookie_string"
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
    """解析cookie字符串为字典 - 完全模拟业务代码"""
    cookies = {}
    for cookie in cookies_str.split("; "):
        try:
            parts = cookie.split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
        except:
            continue
    return cookies


def generate_device_id(user_id: str) -> str:
    """生成设备ID - 模拟业务代码"""
    import random
    
    # 字符集
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    result = []
    
    for i in range(36):
        if i in [8, 13, 18, 23]:
            result.append("-")
        elif i == 14:
            result.append("4")
        else:
            if i == 19:
                # 对于位置19，需要特殊处理
                rand_val = int(16 * random.random())
                result.append(chars[(rand_val & 0x3) | 0x8])
            else:
                rand_val = int(16 * random.random())
                result.append(chars[rand_val])
    
    return ''.join(result) + "-" + user_id


class MockXianyuApis:
    """模拟XianyuApis类的关键部分"""
    
    def __init__(self):
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
        self.session = requests.Session()
        self.session.headers.update({
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
        
    def clear_duplicate_cookies(self):
        """清理重复的cookies - 完全模拟业务代码"""
        # 创建一个新的CookieJar
        new_jar = requests.cookies.RequestsCookieJar()
        
        # 记录已经添加过的cookie名称
        added_cookies = set()
        
        # 按照cookies列表的逆序遍历（最新的通常在后面）
        cookie_list = list(self.session.cookies)
        cookie_list.reverse()
        
        for cookie in cookie_list:
            # 如果这个cookie名称还没有添加过，就添加到新jar中
            if cookie.name not in added_cookies:
                new_jar.set_cookie(cookie)
                added_cookies.add(cookie.name)
                
        # 替换session的cookies
        self.session.cookies = new_jar
        
    def hasLogin(self, retry_count=0):
        """模拟hasLogin方法 - 不实际调用，返回固定值"""
        print(f"    [hasLogin] 模拟调用，返回True")
        return True
        
    def get_token(self, device_id, retry_count=0, total_retry_count=0):
        """完全模拟业务代码的get_token方法"""
        import os
        print(f"\n=== get_token 调用 ===")
        print(f"device_id: {device_id}")
        print(f"retry_count: {retry_count}, total_retry_count: {total_retry_count}")
        
        max_retries = int(os.getenv('MAX_TOKEN_RETRIES', '15'))  # 默认最多重试15次
        
        if total_retry_count >= max_retries:
            print(f"❌ Token获取失败，已达到最大重试次数 {max_retries}次")
            return None  # 返回None而不是退出程序
            
        if retry_count >= 2:  # 每2次尝试重新登陆一次
            print(f"⚠️  获取token失败，尝试重新登陆")
            # 尝试通过hasLogin重新登录
            if self.hasLogin():
                print(f"✅ 重新登录成功，重新尝试获取token")
                return self.get_token(device_id, 0, total_retry_count + 1)  # 重置尝试次数，但增加总重试次数
            else:
                print(f"❌ 重新登录失败，Cookie已失效")
                return None  # 返回None而不是退出程序
                
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
        data_val = '{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"' + device_id + '"}'
        data = {
            'data': data_val,
        }
        
        # 简单获取token，信任cookies已清理干净
        _m_h5_tk = self.session.cookies.get('_m_h5_tk', '')
        token = _m_h5_tk.split('_')[0] if _m_h5_tk else ''
        
        print(f"从cookie获取的_m_h5_tk: {_m_h5_tk[:30]}..." if _m_h5_tk else "未找到_m_h5_tk")
        print(f"提取的token: {token[:20]}..." if token else "token为空")
        print(f"当前session.cookies数量: {len(self.session.cookies)}")
        print(f"cookie名称: {[c.name for c in self.session.cookies]}")
        
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        print(f"生成的签名: {sign}")
        
        try:
            response = self.session.post('https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', params=params, data=data)
            res_json = response.json()
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {json.dumps(res_json, indent=2, ensure_ascii=False)}")
            
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                # 检查ret是否包含成功信息
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    print(f"⚠️  Token API调用失败，错误信息: {ret_value}")
                    # 处理响应中的Set-Cookie
                    if 'Set-Cookie' in response.headers:
                        print(f"🔧 检测到Set-Cookie，更新cookie")
                        self.clear_duplicate_cookies()
                    time.sleep(0.5)
                    return self.get_token(device_id, retry_count + 1, total_retry_count)
                else:
                    print(f"✅ Token获取成功")
                    return res_json
            else:
                print(f"❌ Token API返回格式异常: {res_json}")
                return self.get_token(device_id, retry_count + 1, total_retry_count)
                
        except Exception as e:
            print(f"❌ Token API请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_token(device_id, retry_count + 1, total_retry_count)


class MockAccountManager:
    """模拟AccountManager的初始化流程"""
    
    def __init__(self, cookies_str: str):
        print(f"=== 开始模拟AccountManager初始化 ===")
        print(f"输入的cookies_str长度: {len(cookies_str)}")
        
        # 模拟account_config
        self.account_id = "test_account"
        self.account_name = "测试账号"
        self.cookies_str = cookies_str
        
        # 解析cookies
        self.cookies = trans_cookies(self.cookies_str)
        print(f"解析后的cookies数量: {len(self.cookies)}")
        print(f"解析后的cookie键: {list(self.cookies.keys())}")
        
        # 获取user_id
        self.myid = self.cookies.get('unb', '')
        print(f"提取的user_id (unb): {self.myid}")
        
        if not self.myid:
            print(f"❌ 未找到unb cookie，无法继续")
            return
            
        # 生成device_id
        self.device_id = generate_device_id(self.myid)
        print(f"生成的device_id: {self.device_id}")
        
        # 初始化XianyuApis
        print(f"\n--- 初始化XianyuApis ---")
        self.xianyu = MockXianyuApis()
        
        # 设置cookies到session
        print(f"设置cookies到session...")
        self.xianyu.session.cookies.update(self.cookies)
        print(f"设置后session.cookies数量: {len(self.xianyu.session.cookies)}")
        print(f"设置后cookie名称: {[c.name for c in self.xianyu.session.cookies]}")
        
        # 检查关键cookie是否存在
        _m_h5_tk = self.xianyu.session.cookies.get('_m_h5_tk', '')
        unb = self.xianyu.session.cookies.get('unb', '')
        print(f"关键cookie检查:")
        print(f"  _m_h5_tk: {_m_h5_tk[:30]}..." if _m_h5_tk else "  _m_h5_tk: 未找到")
        print(f"  unb: {unb}")
        
        print(f"=== AccountManager初始化完成 ===\n")
        
    def test_get_token(self):
        """测试get_token调用"""
        print(f"=== 开始测试get_token调用 ===")
        result = self.xianyu.get_token(self.device_id)
        
        if result:
            print(f"✅ get_token调用成功")
            print(f"返回结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ get_token调用失败")
            
        return result


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python business_flow_debug.py \"cookie_string\"")
        return
    
    cookie_str = sys.argv[1]
    
    if not cookie_str:
        print("❌ Cookie字符串不能为空")
        return
    
    print("="*80)
    print("开始完整业务流程调试")
    print("="*80)
    
    # 创建模拟的AccountManager
    account_manager = MockAccountManager(cookie_str)
    
    # 测试get_token调用
    if hasattr(account_manager, 'xianyu'):
        result = account_manager.test_get_token()
        
        print("\n" + "="*80)
        if result:
            print("✅ 业务流程测试成功")
        else:
            print("❌ 业务流程测试失败")
        print("="*80)
    else:
        print("❌ AccountManager初始化失败")


if __name__ == "__main__":
    main()