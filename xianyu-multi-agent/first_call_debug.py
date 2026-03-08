#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试第一次get_token调用失败的问题
复现业务代码中cookies从字符串到session.cookies.update()的完整流程
"""

import sys
import requests
from utils.xianyu_utils import trans_cookies, generate_device_id
from XianyuApis import XianyuApis


def debug_first_get_token_call(cookie_str: str):
    """
    完全模拟业务代码的cookie处理流程
    """
    print("=" * 80)
    print("调试第一次get_token调用失败问题")
    print("=" * 80)
    
    # 1. 模拟AccountManager.__init__()中的cookie处理
    print("\n--- 步骤1: 解析cookie字符串 ---")
    cookies_dict = trans_cookies(cookie_str)
    print(f"解析后cookies数量: {len(cookies_dict)}")
    print(f"解析后cookie键: {list(cookies_dict.keys())}")
    
    # 2. 获取关键信息
    print("\n--- 步骤2: 提取关键信息 ---")
    unb = cookies_dict.get('unb', '')
    _m_h5_tk = cookies_dict.get('_m_h5_tk', '')
    print(f"unb: {unb}")
    print(f"_m_h5_tk: {_m_h5_tk[:30]}..." if _m_h5_tk else "_m_h5_tk: 未找到")
    
    if not unb:
        print("❌ 缺少unb cookie，无法继续")
        return
        
    device_id = generate_device_id(unb)
    print(f"生成的device_id: {device_id}")
    
    # 3. 模拟XianyuApis初始化和cookie设置
    print("\n--- 步骤3: 初始化XianyuApis ---")
    xianyu = XianyuApis()
    
    print("\n--- 步骤4: cookies设置前的状态 ---")
    print(f"设置前session.cookies数量: {len(xianyu.session.cookies)}")
    print(f"设置前session.cookies: {[c.name for c in xianyu.session.cookies]}")
    
    # 4. 关键步骤：session.cookies.update()
    print("\n--- 步骤5: 执行session.cookies.update() ---")
    print("正在执行: xianyu.session.cookies.update(cookies_dict)")
    xianyu.session.cookies.update(cookies_dict)
    
    print(f"设置后session.cookies数量: {len(xianyu.session.cookies)}")
    print(f"设置后session.cookies: {[c.name for c in xianyu.session.cookies]}")
    
    # 5. 检查关键cookie的状态
    print("\n--- 步骤6: 检查关键cookie ---")
    session_m_h5_tk = xianyu.session.cookies.get('_m_h5_tk', '')
    session_unb = xianyu.session.cookies.get('unb', '')
    print(f"session中的_m_h5_tk: {session_m_h5_tk[:30]}..." if session_m_h5_tk else "session中的_m_h5_tk: 未找到")
    print(f"session中的unb: {session_unb}")
    
    # 6. 比较cookie变化
    print("\n--- 步骤7: 比较cookie变化 ---")
    print("原始cookie vs session中的cookie:")
    print(f"  _m_h5_tk 是否相同: {_m_h5_tk == session_m_h5_tk}")
    print(f"  unb 是否相同: {unb == session_unb}")
    
    if _m_h5_tk != session_m_h5_tk:
        print(f"  ⚠️  _m_h5_tk 发生了变化!")
        print(f"    原始: {_m_h5_tk}")
        print(f"    session: {session_m_h5_tk}")
    
    # 7. 立即调用get_token（模拟业务流程）
    print("\n--- 步骤8: 第一次调用get_token ---")
    print("正在调用 xianyu.get_token(device_id)...")
    result = xianyu.get_token(device_id)
    
    print("\n--- 结果分析 ---")
    if result and 'ret' in result:
        ret_values = result.get('ret', [])
        if any('SUCCESS::调用成功' in ret for ret in ret_values):
            print("✅ 第一次调用成功")
        else:
            print("❌ 第一次调用失败")
            print(f"错误信息: {ret_values}")
    else:
        print("❌ 调用返回None或格式异常")
    
    return result


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python first_call_debug.py \"cookie_string\"")
        return
    
    cookie_str = sys.argv[1]
    if not cookie_str:
        print("❌ Cookie字符串不能为空")
        return
    
    debug_first_get_token_call(cookie_str)


if __name__ == "__main__":
    main()