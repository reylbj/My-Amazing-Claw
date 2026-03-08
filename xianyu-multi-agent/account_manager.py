import asyncio
import os
import time
from typing import Dict, Optional
from loguru import logger
from XianyuAgent import XianyuReplyBot
from context_manager import ChatContextManager
from BuyerAgent import BuyerAgentSystem
from utils.xianyu_utils import trans_cookies, generate_device_id
from XianyuApis import XianyuApis


class AccountManager:
    """单个账号的管理器，基于原有的XianyuLive类改造"""
    
    def __init__(self, account_config: Dict):
        """
        初始化账号管理器
        
        Args:
            account_config: 账号配置信息，包含cookies, user_id等
        """
        self.account_id = account_config['id']
        self.account_name = account_config['account_name']
        self.cookies_str = account_config['cookies']
        self.user_id = account_config['user_id']
        self.seller_enabled = account_config.get('seller_enabled', True)
        self.buyer_enabled = account_config.get('buyer_enabled', True)
        
        # 初始化核心组件
        self.xianyu = XianyuApis()
        self.base_url = 'wss://wss-goofish.dingtalk.com/'
        self.cookies = trans_cookies(self.cookies_str)
        
        logger.debug(f"🔍 [DEBUG] AccountManager初始化 - 解析cookie数量: {len(self.cookies)}")
        logger.debug(f"🔍 [DEBUG] AccountManager初始化 - cookie键: {list(self.cookies.keys())}")
        
        # 修复：手动设置cookie以确保正确的域名属性
        from http.cookiejar import Cookie
        for name, value in self.cookies.items():
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
            self.xianyu.session.cookies.set_cookie(cookie)
        
        logger.debug(f"🔍 [DEBUG] AccountManager初始化 - session.cookies数量: {len(self.xianyu.session.cookies)}")
        cookie_names = [cookie.name for cookie in self.xianyu.session.cookies]
        logger.debug(f"🔍 [DEBUG] AccountManager初始化 - session cookie名称: {cookie_names}")
        
        self.myid = self.cookies['unb']
        self.device_id = generate_device_id(self.myid)
        
        # 为每个账号创建独立的上下文管理器
        self.context_manager = ChatContextManager(db_path=f"data/chat_history_{self.account_id}.db")
        
        # 初始化AI系统
        self.seller_bot = None
        self.buyer_agent = None
        
        # 运行状态
        self.is_running = False
        self.ws = None
        self.heartbeat_task = None
        self.token_refresh_task = None
        
        # 配置参数（从环境变量读取，支持账号级别覆盖）
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "15"))
        self.heartbeat_timeout = int(os.getenv("HEARTBEAT_TIMEOUT", "5"))
        self.last_heartbeat_time = 0
        self.last_heartbeat_response = 0
        
        self.token_refresh_interval = int(os.getenv("TOKEN_REFRESH_INTERVAL", "3600"))
        self.token_retry_interval = int(os.getenv("TOKEN_RETRY_INTERVAL", "300"))
        self.last_token_refresh_time = 0
        self.current_token = None
        self.connection_restart_flag = False
        
        # 人工接管相关
        self.manual_mode_conversations = set()
        self.manual_mode_timeout = int(os.getenv("MANUAL_MODE_TIMEOUT", "3600"))
        self.manual_mode_timestamps = {}
        
        self.message_expire_time = int(os.getenv("MESSAGE_EXPIRE_TIME", "300000"))
        self.toggle_keywords = os.getenv("TOGGLE_KEYWORDS", "。")
        
        logger.info(f"账号管理器初始化完成: {self.account_name} (ID: {self.account_id})")
    
    def initialize_ai_agents(self, prompts: Dict[str, str]):
        """
        初始化AI代理，使用账号特定的提示词
        
        Args:
            prompts: 账号的提示词配置
        """
        try:
            if self.seller_enabled:
                self.seller_bot = XianyuReplyBot()
                # 如果有自定义提示词，则更新
                if prompts:
                    self.seller_bot.update_prompts(prompts)
                logger.info(f"账号 {self.account_name} 的卖家AI已初始化")
            
            if self.buyer_enabled:
                self.buyer_agent = BuyerAgentSystem()
                logger.info(f"账号 {self.account_name} 的买家AI已初始化")
                
        except Exception as e:
            logger.error(f"初始化AI代理时出错 (账号: {self.account_name}): {e}")
    
    async def start(self):
        """启动账号监听"""
        if self.is_running:
            logger.warning(f"账号 {self.account_name} 已经在运行中")
            return
        
        self.is_running = True
        logger.info(f"启动账号监听: {self.account_name}")
        
        # 更新账号状态
        self.context_manager.update_account_status(
            self.account_id, 
            is_running=True,
            connection_status='connecting'
        )
        
        try:
            await self.main_loop()
        except Exception as e:
            logger.error(f"账号 {self.account_name} 运行出错: {e}")
            self.context_manager.update_account_status(
                self.account_id,
                is_running=False,
                connection_status='error',
                last_error=str(e)
            )
        finally:
            self.is_running = False
    
    async def stop(self):
        """停止账号监听"""
        logger.info(f"停止账号监听: {self.account_name}")
        self.is_running = False
        
        # 取消异步任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.token_refresh_task:
            self.token_refresh_task.cancel()
        
        # 关闭WebSocket连接
        if self.ws:
            await self.ws.close()
        
        # 更新账号状态
        self.context_manager.update_account_status(
            self.account_id,
            is_running=False,
            connection_status='stopped'
        )
    
    async def main_loop(self):
        """主循环，基于原有的XianyuLive.main()方法"""
        import websockets
        import json
        import time
        
        while self.is_running:
            try:
                # 重置连接重启标志
                self.connection_restart_flag = False
                
                headers = {
                    "Cookie": self.cookies_str,
                    "Host": "wss-goofish.dingtalk.com",
                    "Connection": "Upgrade",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "Origin": "https://www.goofish.com",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                }

                try:
                    async with websockets.connect(
                        self.base_url, 
                        extra_headers=headers,
                        timeout=30,  # 30秒连接超时
                        ping_interval=60,  # 60秒ping间隔
                        ping_timeout=20    # 20秒ping超时
                    ) as websocket:
                        self.ws = websocket
                        await self.init(websocket)
                        
                        # 更新连接状态
                        self.context_manager.update_account_status(
                            self.account_id,
                            connection_status='connected'
                        )
                        
                        # 初始化心跳时间
                        self.last_heartbeat_time = time.time()
                        self.last_heartbeat_response = time.time()
                        
                        # 启动心跳任务
                        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(websocket))
                        
                        # 启动token刷新任务
                        self.token_refresh_task = asyncio.create_task(self.token_refresh_loop())
                        
                        async for message in websocket:
                            if not self.is_running:
                                break
                                
                            try:
                                # 检查是否需要重启连接
                                if self.connection_restart_flag:
                                    logger.info(f"账号 {self.account_name} 检测到连接重启标志，准备重新建立连接...")
                                    break
                                    
                                # 增加调试：记录接收到的消息
                                logger.debug(f"账号 {self.account_name} 🔔 收到WebSocket消息")
                                    
                                message_data = json.loads(message)
                                
                                # 处理心跳响应
                                if await self.handle_heartbeat_response(message_data):
                                    continue
                                
                                # 发送通用ACK响应
                                if "headers" in message_data and "mid" in message_data["headers"]:
                                    ack = {
                                        "code": 200,
                                        "headers": {
                                            "mid": message_data["headers"]["mid"],
                                            "sid": message_data["headers"].get("sid", "")
                                        }
                                    }
                                # 复制其他可能的header字段
                                for key in ["app-key", "ua", "dt"]:
                                    if key in message_data["headers"]:
                                        ack["headers"][key] = message_data["headers"][key]
                                await websocket.send(json.dumps(ack))
                                
                                # 处理其他消息
                                await self.handle_message(message_data, websocket)
                                    
                            except json.JSONDecodeError:
                                logger.error(f"账号 {self.account_name} 消息解析失败")
                            except Exception as e:
                                logger.error(f"账号 {self.account_name} 处理消息时发生错误: {str(e)}")

                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"账号 {self.account_name} WebSocket连接已关闭")
                    
                except asyncio.CancelledError:
                    logger.info(f"账号 {self.account_name} 连接被取消")
                    break  # 账号被停止，退出循环
                    
                except OSError as e:
                    logger.error(f"账号 {self.account_name} 网络连接错误: {e}")
                    self.context_manager.update_account_status(
                        self.account_id,
                        connection_status='error',
                        last_error=f'网络错误: {str(e)}'
                    )
                    
                except Exception as e:
                    logger.error(f"账号 {self.account_name} 连接发生错误: {e}")
                    self.context_manager.update_account_status(
                        self.account_id,
                        connection_status='error',
                        last_error=str(e)
                    )
                
            finally:
                # 清理任务
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await asyncio.wait_for(self.heartbeat_task, timeout=2.0)
                    except asyncio.CancelledError:
                        pass
                    except asyncio.TimeoutError:
                        logger.warning(f"账号 {self.account_name} 心跳任务取消超时")
                    except Exception:
                        pass  # 忽略其他异常
                        
                if self.token_refresh_task:
                    self.token_refresh_task.cancel()
                    try:
                        await asyncio.wait_for(self.token_refresh_task, timeout=2.0)
                    except asyncio.CancelledError:
                        pass
                    except asyncio.TimeoutError:
                        logger.warning(f"账号 {self.account_name} token刷新任务取消超时")
                    except Exception:
                        pass  # 忽略其他异常
                
                # 如果是主动重启，立即重连；否则等待5秒
                if self.connection_restart_flag and self.is_running:
                    logger.info(f"账号 {self.account_name} 主动重启连接，立即重连...")
                elif self.is_running:
                    logger.info(f"账号 {self.account_name} 等待5秒后重连...")
                    await asyncio.sleep(5)
    
    # 以下方法从原有的XianyuLive类复制并适配
    async def refresh_token(self):
        """刷新token"""
        try:
            logger.info(f"账号 {self.account_name} 开始刷新token...")
            
            token_result = self.xianyu.get_token(self.device_id)
            
            # 检查token获取是否失败
            if token_result is None:
                logger.error(f"账号 {self.account_name} Token获取失败，Cookie已过期或达到重试限制")
                # 设置账号状态为未连接
                self.context_manager.update_account_status(self.account_id, connection_status='disconnected', last_error='认证失败，请更新Cookie')
                # 停止账号运行
                await self.stop()
                return None
                
            if 'data' in token_result and 'accessToken' in token_result['data']:
                new_token = token_result['data']['accessToken']
                self.current_token = new_token
                self.last_token_refresh_time = time.time()
                logger.info(f"账号 {self.account_name} Token刷新成功")
                return new_token
            else:
                logger.error(f"账号 {self.account_name} Token刷新失败: {token_result}")
                return None
                
        except Exception as e:
            logger.error(f"账号 {self.account_name} Token刷新异常: {str(e)}")
            return None
    
    async def token_refresh_loop(self):
        """Token刷新循环"""
        import time
        
        while self.is_running:
            try:
                current_time = time.time()
                
                if current_time - self.last_token_refresh_time >= self.token_refresh_interval:
                    logger.info(f"账号 {self.account_name} Token即将过期，准备刷新...")
                    
                    new_token = await self.refresh_token()
                    if new_token:
                        logger.info(f"账号 {self.account_name} Token刷新成功，准备重新建立连接...")
                        self.connection_restart_flag = True
                        if self.ws:
                            await self.ws.close()
                        break
                    else:
                        logger.error(f"账号 {self.account_name} Token刷新失败，将在{self.token_retry_interval // 60}分钟后重试")
                        await asyncio.sleep(self.token_retry_interval)
                        continue
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"账号 {self.account_name} Token刷新循环出错: {e}")
                await asyncio.sleep(60)
    
    async def init(self, ws):
        """初始化WebSocket连接"""
        import time
        import json
        from utils.xianyu_utils import generate_mid
        
        # 如果没有token或者token过期，获取新token
        if not self.current_token or (time.time() - self.last_token_refresh_time) >= self.token_refresh_interval:
            logger.info(f"账号 {self.account_name} 获取初始token...")
            await self.refresh_token()
        
        if not self.current_token:
            logger.error(f"账号 {self.account_name} 无法获取有效token，初始化失败")
            raise Exception("Token获取失败")
            
        msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "444e9908a51d1cb236a27862abc769c9",
                "token": self.current_token,
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) DingWeb/2.1.5 IMPaaS DingWeb/2.1.5",
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self.device_id,
                "mid": generate_mid()
            }
        }
        await ws.send(json.dumps(msg))
        await asyncio.sleep(1)
        
        msg = {"lwp": "/r/SyncStatus/ackDiff", "headers": {"mid": "5701741704675979 0"}, "body": [
            {"pipeline": "sync", "tooLong2Tag": "PNM,1", "channel": "sync", "topic": "sync", "highPts": 0,
             "pts": int(time.time() * 1000) * 1000, "seq": 0, "timestamp": int(time.time() * 1000)}]}
        await ws.send(json.dumps(msg))
        logger.info(f'账号 {self.account_name} 连接注册完成')
    
    async def heartbeat_loop(self, ws):
        """心跳维护循环"""
        import time
        
        while self.is_running:
            try:
                current_time = time.time()
                
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    await self.send_heartbeat(ws)
                
                if (current_time - self.last_heartbeat_response) > (self.heartbeat_interval + self.heartbeat_timeout):
                    logger.warning(f"账号 {self.account_name} 心跳响应超时，可能连接已断开")
                    break
                
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"账号 {self.account_name} 心跳循环出错: {e}")
                break
    
    async def send_heartbeat(self, ws):
        """发送心跳包"""
        import time
        import json
        from utils.xianyu_utils import generate_mid
        
        try:
            heartbeat_mid = generate_mid()
            heartbeat_msg = {
                "lwp": "/!",
                "headers": {
                    "mid": heartbeat_mid
                }
            }
            await ws.send(json.dumps(heartbeat_msg))
            self.last_heartbeat_time = time.time()
            logger.debug(f"账号 {self.account_name} 心跳包已发送")
            return heartbeat_mid
        except Exception as e:
            logger.error(f"账号 {self.account_name} 发送心跳包失败: {e}")
            raise
    
    async def handle_heartbeat_response(self, message_data):
        """处理心跳响应"""
        import time
        
        try:
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self.last_heartbeat_response = time.time()
                logger.debug(f"账号 {self.account_name} 收到心跳响应")
                return True
        except Exception as e:
            logger.error(f"账号 {self.account_name} 处理心跳响应出错: {e}")
        return False
    
    def is_chat_message(self, message):
        """判断是否为用户聊天消息"""
        try:
            return (
                isinstance(message, dict) 
                and "1" in message 
                and isinstance(message["1"], dict)  # 确保是字典类型
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)  # 确保是字典类型
                and "reminderContent" in message["1"]["10"]
            )
        except Exception:
            return False

    def is_sync_package(self, message_data):
        """判断是否为同步包消息"""
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False

    def is_typing_status(self, message):
        """判断是否为用户正在输入状态消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], list)
                and len(message["1"]) > 0
                and isinstance(message["1"][0], dict)
                and "1" in message["1"][0]
                and isinstance(message["1"][0]["1"], str)
                and "@goofish" in message["1"][0]["1"]
            )
        except Exception:
            return False

    async def handle_message(self, message_data, websocket):
        """处理消息，基于单账号版本的逻辑"""
        try:
            import json
            import base64
            from utils.xianyu_utils import decrypt
            
            # 如果不是同步包消息，直接返回
            if not self.is_sync_package(message_data):
                return

            # 获取并解密数据
            sync_data = message_data["body"]["syncPushPackage"]["data"][0]
            
            # 检查是否有必要的字段
            if "data" not in sync_data:
                logger.debug(f"账号 {self.account_name} 同步包中无data字段")
                return

            # 解密数据
            try:
                data = sync_data["data"]
                try:
                    data = base64.b64decode(data).decode("utf-8")
                    data = json.loads(data)
                    # logger.info(f"账号 {self.account_name} 无需解密 message: {data}")
                    return
                except Exception as e:
                    # logger.info(f'账号 {self.account_name} 加密数据: {data}')
                    decrypted_data = decrypt(data)
                    message = json.loads(decrypted_data)
            except Exception as e:
                logger.error(f"账号 {self.account_name} 消息解密失败: {e}")
                return

            try:
                # 判断是否为订单消息,需要自行编写付款后的逻辑
                if message['3']['redReminder'] == '等待买家付款':
                    user_id = message['1'].split('@')[0]
                    user_url = f'https://www.goofish.com/personal?userId={user_id}'
                    logger.info(f'账号 {self.account_name} 等待买家 {user_url} 付款')
                    return
                elif message['3']['redReminder'] == '交易关闭':
                    user_id = message['1'].split('@')[0]
                    user_url = f'https://www.goofish.com/personal?userId={user_id}'
                    logger.info(f'账号 {self.account_name} 买家 {user_url} 交易关闭')
                    return
                elif message['3']['redReminder'] == '等待卖家发货':
                    user_id = message['1'].split('@')[0]
                    user_url = f'https://www.goofish.com/personal?userId={user_id}'
                    logger.info(f'账号 {self.account_name} 交易成功 {user_url} 等待卖家发货')
                    return
            except:
                pass

            # 判断消息类型
            if self.is_typing_status(message):
                logger.debug(f"账号 {self.account_name} 用户正在输入")
                return
            elif not self.is_chat_message(message):
                logger.debug(f"账号 {self.account_name} 其他非聊天消息")
                return

            # 处理聊天消息
            create_time = int(message["1"]["5"])
            send_user_name = message["1"]["10"]["reminderTitle"]
            send_user_id = message["1"]["10"]["senderUserId"]
            send_message = message["1"]["10"]["reminderContent"]
            
            # 时效性验证（过滤5分钟前消息）
            if (time.time() * 1000 - create_time) > self.message_expire_time:
                logger.debug(f"账号 {self.account_name} 过期消息丢弃")
                return
                
            # 获取商品ID和会话ID
            url_info = message["1"]["10"]["reminderUrl"]
            item_id = url_info.split("itemId=")[1].split("&")[0] if "itemId=" in url_info else None
            chat_id = message["1"]["2"].split('@')[0]
            
            # 📨 基本消息信息
            logger.info(f"账号 {self.account_name} 📨 用户: {send_user_name} (ID: {send_user_id}), 商品: {item_id}, 会话: {chat_id}")
            logger.info(f"账号 {self.account_name} 📨 消息: {send_message}")
            
            if not item_id:
                logger.warning(f"账号 {self.account_name} 无法获取商品ID")
                return
            # 检查是否为卖家（自己）发送的控制命令
            if send_user_id == self.myid:
                logger.debug(f"账号 {self.account_name} 检测到卖家消息，检查是否为控制命令")
                
                # 检查切换命令
                if self.check_toggle_keywords(send_message):
                    mode = self.toggle_manual_mode(chat_id)
                    if mode == "manual":
                        logger.info(f"账号 {self.account_name} 🔴 已接管会话 {chat_id} (商品: {item_id})")
                    else:
                        logger.info(f"账号 {self.account_name} 🟢 已恢复会话 {chat_id} 的自动回复 (商品: {item_id})")
                    return
                
                # 记录卖家人工回复
                self.context_manager.add_message_by_chat(chat_id, self.myid, item_id, "assistant", send_message)
                logger.info(f"账号 {self.account_name} 卖家人工回复 (会话: {chat_id}, 商品: {item_id}): {send_message}")
                return
            
            # 6. 添加用户消息到上下文
            self.context_manager.add_message_by_chat(chat_id, send_user_id, item_id, "user", send_message)
            
            # 7. 检查是否处于人工接管模式
            if self.is_manual_mode(chat_id):
                logger.info(f"账号 {self.account_name} 🔴 会话 {chat_id} 处于人工接管模式，跳过自动回复")
                return
                
            # 8. 检查是否为系统消息
            if self.is_system_message(message):
                logger.debug(f"账号 {self.account_name} 系统消息，跳过处理")
                return
                
            # 9. 获取商品信息
            item_info = self.context_manager.get_item_info(item_id)
            if not item_info:
                logger.info(f"账号 {self.account_name} 从API获取商品信息: {item_id}")
                api_result = self.xianyu.get_item_info(item_id)
                if 'data' in api_result and 'itemDO' in api_result['data']:
                    item_info = api_result['data']['itemDO']
                    self.context_manager.save_item_info(item_id, item_info)
                else:
                    logger.warning(f"账号 {self.account_name} 获取商品信息失败: {api_result}")
                    return
            
            # 10. 角色判断
            is_my_product = True  # 默认当作卖家处理
            track_seller_id = str(self.myid)
            
            if 'trackParams' in item_info and 'sellerId' in item_info['trackParams']:
                track_seller_id = str(item_info['trackParams']['sellerId'])
                is_my_product = track_seller_id == str(self.myid)
                logger.info(f"账号 {self.account_name} 🎭 sellerId: {track_seller_id}, 我的ID: {self.myid}")
                logger.info(f"账号 {self.account_name} 🎭 {'✅ 卖家模式' if is_my_product else '❌ 买家模式'}")
            
            # 11. 检查账号功能是否启用
            if is_my_product and not self.seller_enabled:
                logger.info(f"账号 {self.account_name} 卖家功能未启用，跳过回复")
                return
            elif not is_my_product and not self.buyer_enabled:
                logger.info(f"账号 {self.account_name} 买家功能未启用，跳过回复") 
                return
            
            # 12. 创建或更新会话信息
            role = "seller" if is_my_product else "buyer"
            self.context_manager.create_or_update_chat_session(
                chat_id, role, item_id,
                seller_id=track_seller_id,
                buyer_id=self.myid if not is_my_product else send_user_id
            )
            
            session_info = self.context_manager.get_chat_session(chat_id)
            context = self.context_manager.get_context_by_chat(chat_id)
            
            # 确保session_info包含chat_id
            if session_info:
                session_info['chat_id'] = chat_id
            else:
                session_info = {'chat_id': chat_id, 'item_id': item_id, 'stage': 'inquiry'}
            
            # 13. 生成AI回复
            if is_my_product:
                # 🛍️ 卖家模式
                logger.info(f"账号 {self.account_name} 🛍️ 卖家模式: 使用卖家AI系统")
                
                if not self.seller_bot:
                    logger.error(f"账号 {self.account_name} 卖家AI未初始化")
                    return
                    
                item_description = f"{item_info['desc']};当前商品售卖价格为:{str(item_info['soldPrice'])}"
                
                # 生成卖家回复
                bot_reply = self.seller_bot.generate_reply(
                    send_message,
                    item_description, 
                    context=context
                )
                
                # 检查是否为价格意图，如果是则增加议价次数
                if hasattr(self.seller_bot, 'last_intent') and self.seller_bot.last_intent == "price":
                    self.context_manager.increment_bargain_count_by_chat(chat_id)
                    bargain_count = self.context_manager.get_bargain_count_by_chat(chat_id)
                    logger.info(f"账号 {self.account_name} 用户 {send_user_name} 对商品 {item_id} 的议价次数: {bargain_count}")
                
                response_info = {
                    'message': bot_reply,
                    'response_type': 'seller_reply',
                    'agent_used': 'XianyuReplyBot'
                }
                
            else:
                # 🛒 买家模式  
                logger.info(f"账号 {self.account_name} 🛒 买家模式: 启用买家AI Agent系统")
                
                if not self.buyer_agent:
                    logger.error(f"账号 {self.account_name} 买家AI未初始化")
                    return
                    
                # 检查是否最近发送过类似消息（避免重复）
                message_type = self._classify_buyer_message_type(send_message)
                
                if self.context_manager.check_message_sent_recently(chat_id, message_type, hours=0.5):
                    logger.info(f"账号 {self.account_name} 🚫 买家AI: 最近已发送过{message_type}类型消息，跳过回复避免重复")
                    return
                
                # 生成买家回复
                response_info = self.buyer_agent.generate_buyer_response(
                    send_message, item_info, context, session_info
                )
                
                # TODO: 实现买家相关的数据保存逻辑
            
            # 14. 处理回复消息
            if isinstance(response_info.get('message'), dict):
                # BuyerDecisionAgent返回字典
                bot_reply = response_info['message'].get('message', response_info['message'])
            else:
                # 其他Agent返回字符串
                bot_reply = response_info['message']
            
            # 15. 添加机器人回复到上下文
            self.context_manager.add_message_by_chat(chat_id, self.myid, item_id, "assistant", bot_reply)
            
            logger.info(f"账号 {self.account_name} 🤖 AI回复 ({response_info.get('agent_used', 'Unknown')}): {bot_reply}")
            
            # 16. 发送回复消息
            await self.send_msg(websocket, chat_id, send_user_id, bot_reply)
            
        except Exception as e:
            logger.error(f"账号 {self.account_name} 处理消息时发生错误: {str(e)}")
            logger.debug(f"账号 {self.account_name} 原始消息: {message_data}")
            
    # 添加辅助方法
    def check_toggle_keywords(self, message):
        """检查是否包含切换关键词"""
        return self.toggle_keywords in message
        
    def toggle_manual_mode(self, chat_id):
        """切换手动模式"""
        import time
        
        if chat_id in self.manual_mode_conversations:
            self.manual_mode_conversations.remove(chat_id)
            if chat_id in self.manual_mode_timestamps:
                del self.manual_mode_timestamps[chat_id]
            return "auto"
        else:
            self.manual_mode_conversations.add(chat_id)
            self.manual_mode_timestamps[chat_id] = time.time()
            return "manual"
    
    def is_manual_mode(self, chat_id):
        """检查是否处于手动模式"""
        import time
        
        if chat_id not in self.manual_mode_conversations:
            return False
            
        # 检查是否超时
        if chat_id in self.manual_mode_timestamps:
            elapsed = time.time() - self.manual_mode_timestamps[chat_id] 
            if elapsed > self.manual_mode_timeout:
                logger.info(f"账号 {self.account_name} 会话 {chat_id} 手动模式超时，自动恢复")
                self.manual_mode_conversations.remove(chat_id)
                del self.manual_mode_timestamps[chat_id]
                return False
        
        return True
    
    def is_system_message(self, message):
        """检查是否为系统消息"""
        try:
            body = message.get("body", {})
            if "ImPushConst" in body:
                im_data = body["ImPushConst"]
                system_indicators = ['系统', 'System', 'system', 'auto', '自动']
                user_name = im_data.get('userName', '')
                return any(indicator in user_name for indicator in system_indicators)
        except:
            pass
        return False
    
    def _classify_buyer_message_type(self, message):
        """分类买家消息类型"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['价格', '多少钱', '便宜', '降价', 'price']):
            return 'price_inquiry'
        elif any(word in message_lower for word in ['质量', '怎么样', '好吗', '质量', 'condition']):
            return 'quality_inquiry'
        elif any(word in message_lower for word in ['可以', '要了', '买了', '成交']):
            return 'purchase_decision'
        else:
            return 'general_inquiry'
    
    async def send_msg(self, websocket, chat_id, to_user_id, message):
        """发送消息 - 使用单账号版本的格式"""
        try:
            import json
            import base64
            from utils.xianyu_utils import generate_mid, generate_uuid
            
            text = {
                "contentType": 1,
                "text": {
                    "text": message
                }
            }
            text_base64 = str(base64.b64encode(json.dumps(text).encode('utf-8')), 'utf-8')
            msg = {
                "lwp": "/r/MessageSend/sendByReceiverScope",
                "headers": {
                    "mid": generate_mid()
                },
                "body": [
                    {
                        "uuid": generate_uuid(),
                        "cid": f"{chat_id}@goofish",
                        "conversationType": 1,
                        "content": {
                            "contentType": 101,
                            "custom": {
                                "type": 1,
                                "data": text_base64
                            }
                        },
                        "redPointPolicy": 0,
                        "extension": {
                            "extJson": "{}"
                        },
                        "ctx": {
                            "appVersion": "1.0",
                            "platform": "web"
                        },
                        "mtags": {},
                        "msgReadStatusSetting": 1
                    },
                    {
                        "actualReceivers": [
                            f"{to_user_id}@goofish",
                            f"{self.myid}@goofish"
                        ]
                    }
                ]
            }
            
            await websocket.send(json.dumps(msg))
            logger.info(f"账号 {self.account_name} ✅ 消息已发送到 {to_user_id}: {message}")
            
        except Exception as e:
            logger.error(f"账号 {self.account_name} 发送消息失败: {e}")
            # 如果是WebSocket连接问题，可能需要重连
            if "ConnectionClosed" in str(e) or "hostNotFound" in str(e):
                logger.warning(f"账号 {self.account_name} WebSocket连接可能有问题，设置重连标志")
                self.connection_restart_flag = True
    
    def get_status(self) -> Dict:
        """获取账号当前状态"""
        return {
            'account_id': self.account_id,
            'account_name': self.account_name,
            'is_running': self.is_running,
            'seller_enabled': self.seller_enabled,
            'buyer_enabled': self.buyer_enabled,
            'connection_status': 'connected' if self.ws and not self.ws.closed else 'disconnected'
        }