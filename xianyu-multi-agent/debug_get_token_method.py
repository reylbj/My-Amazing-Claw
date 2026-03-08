#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加详细日志的get_token方法 - 用于替换原方法进行调试
复制这个方法替换XianyuApis.py中的get_token方法来调试
"""

def get_token_debug(self, device_id, retry_count=0, total_retry_count=0):
    import os
    import time
    import json
    from loguru import logger
    from utils.xianyu_utils import generate_sign
    
    logger.warning(f"🔍 [DEBUG] get_token调用 - device_id: {device_id}")
    logger.warning(f"🔍 [DEBUG] retry_count: {retry_count}, total_retry_count: {total_retry_count}")
    
    # 打印当前cookie状态
    logger.warning(f"🔍 [DEBUG] 当前session.cookies数量: {len(self.session.cookies)}")
    cookie_names = [cookie.name for cookie in self.session.cookies]
    logger.warning(f"🔍 [DEBUG] cookie名称: {cookie_names}")
    
    # 检查关键cookie
    _m_h5_tk = self.session.cookies.get('_m_h5_tk', '')
    unb = self.session.cookies.get('unb', '')
    logger.warning(f"🔍 [DEBUG] _m_h5_tk: {_m_h5_tk[:30]}..." if _m_h5_tk else "🔍 [DEBUG] _m_h5_tk: 未找到")
    logger.warning(f"🔍 [DEBUG] unb: {unb}")
    
    max_retries = int(os.getenv('MAX_TOKEN_RETRIES', '15'))  # 默认最多重试15次
    
    if total_retry_count >= max_retries:
        logger.error(f"Token获取失败，已达到最大重试次数 {max_retries}次")
        return None  # 返回None而不是退出程序
        
    if retry_count >= 2:  # 每2次尝试重新登陆一次
        logger.warning("获取token失败，尝试重新登陆")
        # 尝试通过hasLogin重新登录
        if self.hasLogin():
            logger.info("重新登录成功，重新尝试获取token")
            return self.get_token(device_id, 0, total_retry_count + 1)  # 重置尝试次数，但增加总重试次数
        else:
            logger.error("重新登录失败，Cookie已失效")
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
    token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
    logger.warning(f"🔍 [DEBUG] 提取的token: {token[:20]}..." if token else "🔍 [DEBUG] 提取的token: 空")
    
    sign = generate_sign(params['t'], token, data_val)
    params['sign'] = sign
    logger.warning(f"🔍 [DEBUG] 生成的签名: {sign}")
    logger.warning(f"🔍 [DEBUG] 请求参数: {json.dumps(params, ensure_ascii=False)}")
    logger.warning(f"🔍 [DEBUG] 请求数据: {json.dumps(data, ensure_ascii=False)}")
    
    try:
        logger.warning(f"🔍 [DEBUG] 开始发送HTTP请求...")
        response = self.session.post('https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', params=params, data=data)
        logger.warning(f"🔍 [DEBUG] 响应状态码: {response.status_code}")
        logger.warning(f"🔍 [DEBUG] 响应头: {dict(response.headers)}")
        
        res_json = response.json()
        logger.warning(f"🔍 [DEBUG] 响应JSON: {json.dumps(res_json, indent=2, ensure_ascii=False)}")
        
        # 打印响应和 Cookie
        logger.warning(f'🔍 [DEBUG] response: {response}')
        logger.warning(f'🔍 [DEBUG] response.cookies: {self.session.cookies}')
        
        if isinstance(res_json, dict):
            ret_value = res_json.get('ret', [])
            logger.warning(f"🔍 [DEBUG] ret字段: {ret_value}")
            
            # 检查ret是否包含成功信息
            if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                logger.warning(f"🔍 [DEBUG] Token API调用失败，错误信息: {ret_value}")
                # 处理响应中的Set-Cookie
                if 'Set-Cookie' in response.headers:
                    logger.warning("🔍 [DEBUG] 检测到Set-Cookie，更新cookie")
                    self.clear_duplicate_cookies()
                    logger.warning(f"🔍 [DEBUG] 清理后cookie数量: {len(self.session.cookies)}")
                time.sleep(0.5)
                return self.get_token(device_id, retry_count + 1, total_retry_count)
            else:
                logger.info("✅ Token获取成功")
                return res_json
        else:
            logger.error(f"🔍 [DEBUG] Token API返回格式异常: {res_json}")
            return self.get_token(device_id, retry_count + 1, total_retry_count)
            
    except Exception as e:
        logger.error(f"🔍 [DEBUG] Token API请求异常: {str(e)}")
        import traceback
        logger.error(f"🔍 [DEBUG] 完整异常信息: {traceback.format_exc()}")
        time.sleep(0.5)
        return self.get_token(device_id, retry_count + 1, total_retry_count)