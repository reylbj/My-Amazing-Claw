from http.cookiejar import Cookie
import time
import os
import re
import sys

import requests
from loguru import logger
from utils.xianyu_utils import generate_sign


class XianyuApis:
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

    @staticmethod
    def _cookie_names(cookie_jar):
        return [cookie.name for cookie in cookie_jar]

    @staticmethod
    def _value_state(name, value):
        if not value:
            return f"🔍 [DEBUG] {name}: 未找到"
        return f"🔍 [DEBUG] {name}: 已设置(len={len(value)})"

    @staticmethod
    def _response_summary(res_json):
        if not isinstance(res_json, dict):
            return {"type": type(res_json).__name__}
        data = res_json.get("data")
        return {
            "api": res_json.get("api"),
            "ret": res_json.get("ret"),
            "has_data": isinstance(data, dict),
            "has_access_token": isinstance(data, dict) and bool(data.get("accessToken")),
            "has_refresh_token": isinstance(data, dict) and bool(data.get("refreshToken")),
        }
        
    def clear_duplicate_cookies(self):
        """清理重复的cookies"""
        logger.warning(f"🔍 [DEBUG] clear_duplicate_cookies调用 - 清理前cookie数量: {len(self.session.cookies)}")
        before_cookies = self._cookie_names(self.session.cookies)
        logger.warning(f"🔍 [DEBUG] 清理前cookie名称: {before_cookies}")
        
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
                logger.warning(f"🔍 [DEBUG] 保留cookie: {cookie.name}")
            else:
                logger.warning(f"🔍 [DEBUG] 删除重复cookie: {cookie.name}")
                
        # 替换session的cookies
        self.session.cookies = new_jar
        
        logger.warning(f"🔍 [DEBUG] 清理后cookie数量: {len(self.session.cookies)}")
        after_cookies = self._cookie_names(self.session.cookies)
        logger.warning(f"🔍 [DEBUG] 清理后cookie名称: {after_cookies}")
        
        # 更新完cookies后，更新.env文件
        self.update_env_cookies()
        
    def update_env_cookies(self):
        """更新.env文件中的COOKIES_STR"""
        try:
            # 获取当前cookies的字符串形式
            cookie_str = '; '.join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])
            
            # 读取.env文件
            env_path = os.path.join(os.getcwd(), '.env')
            if not os.path.exists(env_path):
                logger.warning(".env文件不存在，无法更新COOKIES_STR")
                return
                
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
                
            # 使用正则表达式替换COOKIES_STR的值
            if 'COOKIES_STR=' in env_content:
                new_env_content = re.sub(
                    r'COOKIES_STR=.*', 
                    f'COOKIES_STR={cookie_str}',
                    env_content
                )
                
                # 写回.env文件
                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write(new_env_content)
                    
                logger.debug("已更新.env文件中的COOKIES_STR")
            else:
                logger.warning(".env文件中未找到COOKIES_STR配置项")
        except Exception as e:
            logger.warning(f"更新.env文件失败: {str(e)}")
        
    def hasLogin(self, retry_count=0):
        """调用hasLogin.do接口进行登录状态检查"""
        logger.warning(f"🔍 [DEBUG] hasLogin调用 - retry_count: {retry_count}")
        
        if retry_count >= 2:
            logger.error("Login检查失败，重试次数过多")
            return False
            
        try:
            url = 'https://passport.goofish.com/newlogin/hasLogin.do'
            params = {
                'appName': 'xianyu',
                'fromSite': '77'
            }
            data = {
                'hid': self.session.cookies.get('unb', ''),
                'ltl': 'true',
                'appName': 'xianyu',
                'appEntrance': 'web',
                '_csrf_token': self.session.cookies.get('XSRF-TOKEN', ''),
                'umidToken': '',
                'hsiz': self.session.cookies.get('cookie2', ''),
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
                'deviceId': self.session.cookies.get('cna', '')
            }
            
            logger.warning(f"🔍 [DEBUG] hasLogin请求前cookie数量: {len(self.session.cookies)}")
            
            response = self.session.post(url, params=params, data=data)
            res_json = response.json()
            # logger.debug(f'res_json: {res_json}')
            # 打印响应和 Cookie
            logger.warning(f'🔍 [DEBUG] hasLogin response: {response}')
            logger.warning(f'🔍 [DEBUG] hasLogin response cookie名称: {self._cookie_names(self.session.cookies)}')
            
            if res_json.get('content', {}).get('success'):
                logger.warning("🔍 [DEBUG] Login成功")
                # 清理和更新cookies
                logger.warning("🔍 [DEBUG] hasLogin成功后调用clear_duplicate_cookies")
                self.clear_duplicate_cookies()
                return True
            else:
                logger.warning(f"🔍 [DEBUG] Login失败: {res_json}")
                time.sleep(0.5)
                return self.hasLogin(retry_count + 1)
                
        except Exception as e:
            logger.error(f"🔍 [DEBUG] Login请求异常: {str(e)}")
            time.sleep(0.5)
            return self.hasLogin(retry_count + 1)

    def get_token(self, device_id, retry_count=0, total_retry_count=0):
        import os
        import time
        import json
        
        logger.warning(f"🔍 [DEBUG] get_token调用 - device_id: {device_id}")
        logger.warning(f"🔍 [DEBUG] retry_count: {retry_count}, total_retry_count: {total_retry_count}")
        
        # 打印当前cookie状态
        logger.warning(f"🔍 [DEBUG] 当前session.cookies数量: {len(self.session.cookies)}")
        cookie_names = self._cookie_names(self.session.cookies)
        logger.warning(f"🔍 [DEBUG] cookie名称: {cookie_names}")
        
        # 检查关键cookie
        _m_h5_tk = self.session.cookies.get('_m_h5_tk', '')
        unb = self.session.cookies.get('unb', '')
        logger.warning(self._value_state("_m_h5_tk", _m_h5_tk))
        logger.warning(self._value_state("unb", unb))
        
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
        logger.warning(self._value_state("token", token))
        
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        logger.warning(f"🔍 [DEBUG] 生成签名成功(len={len(sign)})")
        logger.warning(f"🔍 [DEBUG] token请求目标: {params['api']}")
        
        try:
            logger.warning(f"🔍 [DEBUG] 开始发送HTTP请求...")
            response = self.session.post('https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/', params=params, data=data)
            logger.warning(f"🔍 [DEBUG] 响应状态码: {response.status_code}")
            logger.warning(f"🔍 [DEBUG] 响应头: {dict(response.headers)}")
            
            res_json = response.json()
            logger.warning(f"🔍 [DEBUG] 响应摘要: {json.dumps(self._response_summary(res_json), ensure_ascii=False)}")
            
            # 打印响应和 Cookie
            logger.warning(f'🔍 [DEBUG] response: {response}')
            logger.warning(f'🔍 [DEBUG] response cookie名称: {self._cookie_names(self.session.cookies)}')
            
            # 检查是否触发风控
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                logger.warning(f"🔍 [DEBUG] ret字段: {ret_value}")
                
                # 检查是否被风控
                if any('FAIL_SYS_USER_VALIDATE' in ret or 'RGV587_ERROR' in ret for ret in ret_value):
                    logger.error(f"🚨 账号被风控！请等待一段时间或更新Cookie")
                    logger.error(f"🚨 风控错误: {ret_value}")
                    if 'bxpunish' in response.headers:
                        logger.error(f"🚨 bxpunish标志: {response.headers.get('bxpunish')}")
                    # 风控情况下不再重试，直接返回None
                    return None
                
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

    def get_item_info(self, item_id, retry_count=0):
        """获取商品信息，自动处理token失效的情况"""
        if retry_count >= 3:  # 最多重试3次
            logger.error("获取商品信息失败，重试次数过多")
            return {"error": "获取商品信息失败，重试次数过多"}
            
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
            'api': 'mtop.taobao.idle.pc.detail',
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }
        
        data_val = '{"itemId":"' + item_id + '"}'
        data = {
            'data': data_val,
        }
        
        # 简单获取token，信任cookies已清理干净
        token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
        
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign
        
        try:
            response = self.session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/', 
                params=params, 
                data=data
            )
            
            res_json = response.json()
            # 检查返回状态
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                # 检查ret是否包含成功信息
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"商品信息API调用失败，错误信息: {ret_value}")
                    # 处理响应中的Set-Cookie
                    if 'Set-Cookie' in response.headers:
                        logger.debug("检测到Set-Cookie，更新cookie")
                        self.clear_duplicate_cookies()
                    time.sleep(0.5)
                    return self.get_item_info(item_id, retry_count + 1)
                else:
                    logger.debug(f"商品信息获取成功: {item_id}")
                    return res_json
            else:
                logger.error(f"商品信息API返回格式异常: {res_json}")
                return self.get_item_info(item_id, retry_count + 1)
                
        except Exception as e:
            logger.error(f"商品信息API请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_item_info(item_id, retry_count + 1)
