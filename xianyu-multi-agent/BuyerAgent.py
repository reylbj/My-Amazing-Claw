import re
import os
import json
import requests
from typing import List, Dict
from openai import OpenAI
from loguru import logger


class CozeClient:
    """扣子(Coze)API客户端"""
    
    def _clean_env_var(self, var_name, default=""):
        """清理环境变量：移除注释、空格和特殊字符"""
        raw_value = os.getenv(var_name, default)
        if not raw_value:
            return ""
        
        # 移除#注释（包括中文注释）
        cleaned_value = raw_value.split('#')[0].strip()
        
        # 移除可能的引号
        if cleaned_value.startswith('"') and cleaned_value.endswith('"'):
            cleaned_value = cleaned_value[1:-1]
        if cleaned_value.startswith("'") and cleaned_value.endswith("'"):
            cleaned_value = cleaned_value[1:-1]
        
        # 最终清理
        return cleaned_value.strip()
    
    def __init__(self):
        # 清理环境变量：移除注释和多余空格
        self.api_key = self._clean_env_var("COZE_API_KEY")
        self.base_url = self._clean_env_var("COZE_BASE_URL", "https://api.coze.cn")
        self.buyer_bot_id = self._clean_env_var("COZE_BUYER_BOT_ID")
        
        if not self.api_key or not self.buyer_bot_id:
            logger.warning("扣子API配置不完整，将使用备用的OpenAI客户端")
            self.fallback_client = OpenAI(
                api_key=os.getenv("API_KEY"),
                base_url=os.getenv("MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            )
        else:
            self.fallback_client = None
            logger.info(f"扣子API已配置，买家智能体ID: {self.buyer_bot_id}")
    
    def set_bot_variables(self, conversation_context=None):
        """设置Bot变量，将商品信息传递给智能体"""
        if not self.api_key or not self.buyer_bot_id:
            logger.warning("扣子API未配置，无法设置变量")
            return False
        
        # 🔧 从conversation_context中提取商品信息
        if not conversation_context or 'item_info' not in conversation_context:
            logger.warning("没有商品信息，跳过变量设置")
            return False
        
        item_info = conversation_context['item_info']
        
        # 🔧 从实际数据结构中提取商品信息
        title = item_info.get('title', '未知商品')
        sold_price = item_info.get('soldPrice', 0)
        desc = item_info.get('desc', '暂无描述')
        
        # 获取卖家信息（从shareData中解析）
        seller_nick = '未知卖家'
        try:
            import json
            share_info = item_info.get('shareData', {}).get('shareInfoJsonString', '{}')
            share_data = json.loads(share_info)
            seller_nick = share_data.get('contentParams', {}).get('headerParams', {}).get('title', '未知卖家')
        except:
            pass
        
        # 获取商品图片
        images = []
        image_infos = item_info.get('imageInfos', [])
        for img_info in image_infos:
            if img_info.get('url'):
                images.append(img_info['url'])
        
        # 构造变量数据
        variables = []
        variables.append({
            "keyword": "goods_title",
            "value": title
        })
        variables.append({
            "keyword": "goods_price",
            "value": str(sold_price)
        })
        variables.append({
            "keyword": "goods_desc",
            "value": desc
        })
        variables.append({
            "keyword": "goods_images",
            "value": json.dumps(images[:3] if images else [], ensure_ascii=False)
        })
        variables.append({
            "keyword": "seller_name",
            "value": seller_nick
        })

            # "goods_title": title,
            # "goods_price": str(sold_price),
            # "goods_desc": desc,
            # "goods_images": images[:3] if images else [],
            # "seller_name": seller_nick
        
        
        # 🔧 生成会话标识
        user_id = "buyer_user"
        if conversation_context:
            item_id = conversation_context.get('item_id', 'unknown')
            user_id = f"buyer_{item_id}"
        
        # 调用设置变量API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # 🔧 根据扣子API v3文档设置变量 - 修正API端点
            api_url = f"{self.base_url}/v1/variables"
            
            data = {
                "bot_id": self.buyer_bot_id,
                "connector_uid": user_id,
                "data": variables
            }
            
            logger.info(f"🔧 设置Bot变量: {variables}")
            logger.info(f"🔧 API URL: {api_url}")
            
            response = requests.put(
                api_url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            logger.info(f"🔧 响应状态码: {response.status_code}")
            logger.info(f"🔧 响应内容: {response.text}")
            
            if response.status_code == 200:
                logger.info("✅ Bot变量设置成功")
                return True
            else:
                logger.error(f"❌ 设置Bot变量失败: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 设置Bot变量网络异常: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 设置Bot变量异常: {e}")
            return False
    
    def chat_with_bot(self, messages, bot_id=None, stream=True, conversation_context=None):
        """与扣子智能体对话（使用v3 API + 流式响应）"""
        if not self.api_key or not self.buyer_bot_id:
            logger.warning("扣子API未配置，使用OpenAI fallback")
            return self._fallback_chat(messages)
        
        # 🔧 首先设置Bot变量（商品信息）
        if conversation_context:
            self.set_bot_variables(conversation_context)
        
        bot_id = bot_id or self.buyer_bot_id
        
        # 构建扣子v3 API请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json"
        }
        
        # 🔧 如果请求流式响应，添加特殊的头部（根据扣子API文档）
        if stream:
            headers["Accept"] = "text/event-stream"
            headers["Cache-Control"] = "no-cache"
        
        # 🔧 生成固定的conversation_id，用于单个商品会话的完整上下文
        if conversation_context:
            item_id = conversation_context.get('item_id', 'unknown')
            chat_id = conversation_context.get('chat_id', 'unknown')
            conversation_id = f"buyer_{item_id}_{hash(chat_id) % 1000}"
        else:
            conversation_id = f"buyer_{hash(str(messages)) % 10000}"
        
        # 📚 准备历史对话记录 - 现在不需要传递商品信息，直接传递用户消息
        additional_messages = []
        
        # 🔧 添加调试打印，查看传入的数据
        logger.info(f"🔍 调试信息 - conversation_context: {conversation_context}")
        
        # 🔧 注释掉历史消息逻辑，避免传递过多上下文导致API调用成本过高
        # 从conversation_context获取完整的历史对话
        if conversation_context and 'chat_history' in conversation_context:
            chat_history = conversation_context['chat_history']
            logger.info(f"🔍 调试信息 - chat_history长度: {len(chat_history) if chat_history else 0}")
            
            # 转换为扣子API格式，最多100条
            for msg in chat_history[-100:]:  # 限制最多100条历史消息
                if msg["role"] == "user":
                    # 买家消息
                    additional_messages.append({
                        "role": "user",
                        "content": msg["content"],
                        "content_type": "text"
                    })
                elif msg["role"] == "assistant":
                    # 卖家回复（作为assistant消息）
                    additional_messages.append({
                        "role": "assistant", 
                        "content": msg["content"],
                        "content_type": "text"
                    })
                # 忽略system消息，让智能体自己处理角色设定
        
        # 📝 从conversation_context获取当前真实的用户消息（而不是系统内部消息）
        current_user_message = ""
        if conversation_context and 'current_message' in conversation_context:
            current_user_message = conversation_context['current_message']
            logger.info(f"🔍 调试信息 - current_user_message: {current_user_message}")
        
        # 🔧 现在只需要传递简单的用户消息，商品信息已通过变量设置
        if current_user_message and current_user_message != "请生成一个自然的买家回复":
            additional_messages.append({
                "role": "user", 
                "content": current_user_message,
                "content_type": "text"
            })
        else:
            # 默认消息
            additional_messages.append({
                "role": "user",
                "content": "嗯，我想了解一下这个商品",
                "content_type": "text"
            })
        
        logger.info(f"🔍 调试信息 - 最终additional_messages数量: {len(additional_messages)}")
        
        # v3 API 数据格式 - 使用conversation_id作为查询参数
        # 🔧 根据扣子API文档，必须包含user_id字段
        user_id = "buyer_user"  # 买家AI系统的用户标识
        if conversation_context:
            item_id = conversation_context.get('item_id', 'unknown')
            user_id = f"buyer_{item_id}"  # 为每个商品创建独立的用户ID
        
        data = {
            "bot_id": bot_id,
            "user_id": user_id,  # 🔧 添加必需的user_id参数
            "stream": stream,
            "additional_messages": additional_messages,
            "auto_save_history": True,
        }
        
        logger.debug(f"🔄 扣子会话ID: {conversation_id}, 流式响应: {stream}")
        logger.debug(f"📚 历史消息数量: {len(additional_messages)}")
        
        try:
            # 完整的API URL - 根据官方文档，conversation_id可能通过请求体传递
            api_url = f"{self.base_url}/v3/chat"
            
            # 🔧 如果有conversation_id，添加到请求体中（而不是查询参数）
            if conversation_context:
                data["conversation_id"] = conversation_id
            logger.debug(f"🔗 扣子API请求: {api_url}")
            logger.debug(f"📤 请求头: {headers}")
            logger.debug(f"📤 请求体: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=30,  # 🔧 增加超时时间，给流式响应更多时间
                stream=stream
            )
            
            logger.debug(f"📥 响应状态码: {response.status_code}")
            logger.debug(f"📥 响应头: {dict(response.headers)}")
            
            if response.status_code == 200:
                # 🔧 根据响应头的Content-Type来判断是否为流式响应，而不是根据请求参数
                content_type = response.headers.get('Content-Type', '')
                is_stream_response = 'text/event-stream' in content_type or 'application/stream' in content_type
                
                if is_stream_response:
                    # 实际收到流式响应
                    logger.debug("🌊 检测到流式响应，开始处理")
                    return self._handle_stream_response(response)
                else:
                    # 实际收到JSON响应（即使我们请求了流式）
                    logger.debug(f"📦 检测到JSON响应(Content-Type: {content_type})，按JSON处理")
                    try:
                        result = response.json()
                        logger.debug(f"📥 JSON响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        return self._parse_v3_response(result)
                    except json.JSONDecodeError as e:
                        logger.error(f"解析响应JSON失败: {e}")
                        logger.error(f"原始响应: {response.text[:500]}...")
                        return self._fallback_chat(messages)
            else:
                logger.error(f"扣子API请求失败: {response.status_code}")
                logger.error(f"错误响应: {response.text}")
                return self._fallback_chat(messages)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"扣子API网络请求异常: {e}")
            return self._fallback_chat(messages)
        except Exception as e:
            logger.error(f"调用扣子API异常: {e}")
            return self._fallback_chat(messages)
    
    def _handle_stream_response(self, response):
        """处理流式响应 - 根据官方v3文档格式"""
        content_parts = []
        
        try:
            current_event = None
            json_buffer = ""
            line_count = 0
            max_lines = 1000
            
            # 添加超时处理
            import time
            start_time = time.time()
            timeout_seconds = 60
            
            logger.debug("🌊 开始处理扣子流式响应")
            
            for line in response.iter_lines(decode_unicode=True):
                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    logger.warning(f"⏰ 流式响应超时({timeout_seconds}秒)，强制结束")
                    break
                    
                line_count += 1
                if line_count > max_lines:
                    logger.warning(f"流式响应行数超过限制({max_lines})，强制结束")
                    break
                    
                if not line:
                    continue
                    
                logger.debug(f"📥 收到SSE行[{line_count}]: {line[:100]}...")
                
                # 处理SSE格式的事件行
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    logger.debug(f"🎯 事件类型: {current_event}")
                    continue
                
                # 处理SSE格式的数据行
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    
                    # 跳过结束标记
                    if data_str == '"[DONE]"' or data_str == "[DONE]":
                        logger.debug("🏁 收到结束标记，流式响应完成")
                        break
                    
                    # 🔧 重新设计JSON处理：每次都尝试单独解析，不累积
                    try:
                        data = json.loads(data_str)
                        logger.debug(f"📦 解析JSON成功: {data.get('type', 'unknown')} - {data.get('content', '')[:50]}...")
                        
                        # 🔧 处理answer类型的内容
                        if data.get("type") == "answer":
                            content = data.get("content", "")
                            if content:
                                # 🔧 修复UTF-8编码问题
                                try:
                                    # 如果内容被错误编码，尝试修复
                                    if isinstance(content, str) and any(ord(c) > 127 for c in content):
                                        content = content.encode('latin1').decode('utf-8')
                                except:
                                    pass  # 如果修复失败，使用原内容
                                
                                if current_event == "conversation.message.delta":
                                    # 增量内容，直接添加
                                    content_parts.append(content)
                                    logger.debug(f"📝 收到流式内容[{len(content_parts)}]: {content}")
                                elif current_event == "conversation.message.completed":
                                    # 完整内容，检查是否需要替换
                                    current_total = "".join(content_parts)
                                    if len(content) > len(current_total):
                                        logger.debug(f"📝 收到完整内容，替换片段: {content}")
                                        content_parts = [content]
                                    else:
                                        logger.debug(f"📝 确认消息完成: {content[:50]}...")
                        
                        # 对话完成事件
                        if current_event == "conversation.chat.completed":
                            logger.debug("🎉 扣子对话完成")
                            break
                            
                        # 错误事件
                        elif current_event == "error":
                            error_msg = data.get("error_information", {}).get("msg", "未知错误")
                            logger.error(f"❌ 扣子API返回错误: {error_msg}")
                            return "嗯，我想想"
                            
                    except json.JSONDecodeError as e:
                        # 🔧 JSON解析失败，可能是分包数据，保存到缓冲区
                        if json_buffer:
                            # 如果缓冲区有内容，尝试合并
                            combined_data = json_buffer + data_str
                        else:
                            combined_data = data_str
                        
                        try:
                            data = json.loads(combined_data)
                            json_buffer = ""  # 清空缓冲区
                            
                            logger.debug(f"📦 合并后解析JSON成功: {data.get('type', 'unknown')} - {data.get('content', '')[:50]}...")
                            
                            # 处理answer类型的内容
                            if data.get("type") == "answer":
                                content = data.get("content", "")
                                if content:
                                    # 修复UTF-8编码问题
                                    try:
                                        if isinstance(content, str) and any(ord(c) > 127 for c in content):
                                            content = content.encode('latin1').decode('utf-8')
                                    except:
                                        pass
                                    
                                    if current_event == "conversation.message.delta":
                                        content_parts.append(content)
                                        logger.debug(f"📝 从缓冲区收到流式内容[{len(content_parts)}]: {content}")
                                    elif current_event == "conversation.message.completed":
                                        current_total = "".join(content_parts)
                                        if len(content) > len(current_total):
                                            logger.debug(f"📝 从缓冲区收到完整内容，替换片段: {content}")
                                            content_parts = [content]
                                        else:
                                            logger.debug(f"📝 从缓冲区确认消息完成: {content[:50]}...")
                        except json.JSONDecodeError:
                            # 仍然解析失败，保存到缓冲区
                            json_buffer = combined_data
                            logger.debug(f"⏳ JSON仍然解析失败，保存到缓冲区[大小: {len(json_buffer)}]")
                            
                            # 🔧 如果缓冲区过大，尝试提取内容
                            if len(json_buffer) > 2000:
                                logger.warning("JSON缓冲区过大，尝试提取内容")
                                # 尝试从缓冲区中提取中文内容
                                import re
                                # 查找中文内容的模式
                                chinese_pattern = r'[\u4e00-\u9fa5]+'
                                matches = re.findall(chinese_pattern, json_buffer)
                                if matches:
                                    extracted_content = "".join(matches)
                                    if len(extracted_content) > len("".join(content_parts)):
                                        logger.debug(f"📝 从大缓冲区提取中文内容: {extracted_content}")
                                        content_parts = [extracted_content]
                                json_buffer = ""  # 清空缓冲区
                        continue
                
                # 🔧 处理非标准格式的数据行（可能是JSON片段）
                elif line and not line.startswith("event:"):
                    # 检查是否包含中文内容
                    import re
                    chinese_pattern = r'[\u4e00-\u9fa5]+'
                    matches = re.findall(chinese_pattern, line)
                    if matches:
                        # 直接提取中文内容
                        extracted_content = "".join(matches)
                        content_parts.append(extracted_content)
                        logger.debug(f"📝 从非标准行提取中文内容[{len(content_parts)}]: {extracted_content}")
                    else:
                        # 添加到缓冲区
                        json_buffer += line
                        logger.debug(f"📥 收到非标准数据行，添加到缓冲区: {line[:50]}...")
            
            # 🔧 处理最后的缓冲区内容
            if json_buffer.strip():
                logger.debug(f"🔧 处理最终缓冲区内容[长度: {len(json_buffer)}]")
                logger.debug(f"🔧 缓冲区原始内容: {json_buffer}")
                
                # 🔧 改进中文内容提取逻辑
                import re
                
                # 1. 首先尝试标准JSON解析
                try:
                    # 尝试多种方式修复JSON
                    attempts = [
                        json_buffer,
                        json_buffer.rstrip(','),
                        json_buffer + '"}',
                        json_buffer.split('\n')[0] if '\n' in json_buffer else json_buffer
                    ]
                    
                    for attempt in attempts:
                        try:
                            data = json.loads(attempt)
                            if data.get("type") == "answer" and data.get("content"):
                                content = data.get("content")
                                # 修复UTF-8编码
                                try:
                                    if isinstance(content, str) and any(ord(c) > 127 for c in content):
                                        content = content.encode('latin1').decode('utf-8')
                                except:
                                    pass
                                
                                current_total = "".join(content_parts)
                                if len(content) > len(current_total):
                                    logger.debug(f"📝 从最终缓冲区JSON解析获取完整内容: {content}")
                                    content_parts = [content]
                                    break
                        except:
                            continue
                    else:
                        # JSON解析都失败，使用文本提取
                        raise ValueError("JSON解析失败，使用文本提取")
                        
                except:
                    # 2. JSON解析失败，使用更智能的文本提取
                    logger.debug("🔧 JSON解析失败，使用智能文本提取")
                    
                    # 🔧 先检查是否已经有足够的内容
                    current_total = "".join(content_parts)
                    if len(current_total) > 10:  # 如果已经有足够内容，不要被缓冲区覆盖
                        logger.debug(f"📝 已有足够内容，跳过缓冲区提取: {current_total}")
                    else:
                        # 提取所有中文内容，但排除JSON语法字符
                        # 🔧 修复正则表达式，排除引号等JSON语法字符
                        chinese_pattern = r'[\u4e00-\u9fa5，。？！、；：（）【】《》〈〉「」『』〔〕]+'
                        matches = re.findall(chinese_pattern, json_buffer)
                        
                        logger.debug(f"📝 从缓冲区提取到的中文片段: {matches}")
                        
                        if matches:
                            # 合并所有中文片段
                            extracted_content = "".join(matches)
                            
                            # 清理和格式化内容
                            extracted_content = re.sub(r'[，。？！]+$', '', extracted_content)  # 移除末尾标点
                            extracted_content = re.sub(r'，+', '，', extracted_content)  # 合并多个逗号
                            extracted_content = re.sub(r'。+', '。', extracted_content)  # 合并多个句号
                            
                            # 如果内容不以标点结尾，尝试添加合适的标点
                            if extracted_content and not extracted_content[-1] in '。？！':
                                # 根据内容类型添加合适的标点
                                if '吗' in extracted_content or '呢' in extracted_content or '如何' in extracted_content:
                                    extracted_content += '？'
                                else:
                                    extracted_content += '。'
                            
                            # 只有当提取的内容比现有内容更长且有意义时才替换
                            if len(extracted_content) > len(current_total) and len(extracted_content) > 5:
                                logger.debug(f"📝 从最终缓冲区文本提取获取内容: {extracted_content}")
                                content_parts = [extracted_content]
                            else:
                                logger.debug(f"📝 提取的内容不够长或不够好: {extracted_content} (长度: {len(extracted_content)})")
                        else:
                            logger.debug("📝 没有从缓冲区提取到中文内容")
                        
                        # 3. 如果还是没有足够内容，尝试更宽松的提取
                        if not content_parts or len("".join(content_parts)) < 10:
                            logger.debug("📝 尝试更宽松的内容提取")
                            # 🔧 更严格的宽松模式，避免提取JSON语法字符
                            loose_pattern = r'[\u4e00-\u9fa5a-zA-Z0-9，。？！、；：（）【】《》〈〉「」『』〔〕\s]+[\u4e00-\u9fa5]+'
                            loose_matches = re.findall(loose_pattern, json_buffer)
                            
                            logger.debug(f"📝 宽松模式提取到的片段: {loose_matches}")
                            
                            if loose_matches:
                                # 过滤掉纯英文或数字的片段，保留包含中文的片段
                                chinese_fragments = []
                                for match in loose_matches:
                                    # 确保片段包含足够的中文字符
                                    chinese_count = len(re.findall(r'[\u4e00-\u9fa5]', match))
                                    if chinese_count >= 3:  # 至少3个中文字符
                                        clean_match = re.sub(r'["\'\{\}\[\],:]+', '', match)  # 移除JSON语法字符
                                        if clean_match.strip():
                                            chinese_fragments.append(clean_match.strip())
                                
                                logger.debug(f"📝 过滤后的中文片段: {chinese_fragments}")
                                
                                if chinese_fragments:
                                    extracted_content = "".join(chinese_fragments)
                                    extracted_content = re.sub(r'\s+', '', extracted_content)  # 移除空格
                                    
                                    if len(extracted_content) > len("".join(content_parts)) and len(extracted_content) > 5:
                                        logger.debug(f"📝 从最终缓冲区宽松提取获取内容: {extracted_content}")
                                        content_parts = [extracted_content]
                                    else:
                                        logger.debug(f"📝 宽松提取的内容不够好: {extracted_content}")
                                else:
                                    logger.debug("📝 宽松模式没有提取到有效内容")
                            else:
                                logger.debug("📝 宽松模式没有匹配到任何内容")
            
            # 合并所有内容片段
            full_content = "".join(content_parts)
            logger.debug(f"🔗 合并后的完整内容[{len(content_parts)}片段]: {full_content}")
            
            if full_content:
                logger.debug(f"✅ 扣子流式回复完整内容: {full_content}")
                return self._clean_response(full_content)
            else:
                logger.warning("⚠️ 扣子流式响应无内容")
                return "嗯，我想想"
            
        except Exception as e:
            logger.error(f"❌ 处理扣子流式响应失败: {e}")
            logger.debug(f"🔍 异常时已收集的内容片段: {content_parts}")
            # 即使出错，也尝试返回已收集的内容
            if content_parts:
                full_content = "".join(content_parts)
                logger.debug(f"🔄 返回部分内容: {full_content}")
                return self._clean_response(full_content)
            return "嗯，我想想"
    
    def _parse_v3_response(self, result):
        """解析v3 API的非流式响应 - 根据官方文档格式"""
        try:
            # 检查响应代码
            code = result.get("code")
            msg = result.get("msg", "")
            
            if code == 0:
                # 成功响应
                data = result.get("data", {})
                
                # 检查对话状态
                status = data.get("status")
                if status == "completed":
                    # 获取消息列表
                    messages = data.get("messages", [])
                    
                    # 查找answer类型的消息
                    for message in messages:
                        if message.get("type") == "answer":
                            content = message.get("content", "")
                            if content:
                                logger.debug(f"扣子v3非流式回复: {content}")
                                return self._clean_response(content)
                    
                    logger.warning("扣子v3响应中未找到answer类型消息")
                    return "嗯，我想想"
                    
                elif status == "in_progress":
                    logger.warning("扣子对话仍在进行中（非流式模式异常）")
                    return "嗯，我想想"
                    
                else:
                    logger.warning(f"扣子对话状态异常: {status}")
                    return "嗯，我想想"
                    
            else:
                # 错误响应
                logger.error(f"扣子v3 API返回错误 - 代码: {code}, 消息: {msg}")
                
                # 检查是否有详细错误信息
                if "data" in result:
                    error_info = result["data"].get("error_information", {})
                    error_type = error_info.get("type", "unknown")
                    error_code = error_info.get("code", "unknown")
                    error_msg = error_info.get("msg", "未知错误")
                    logger.error(f"扣子详细错误 - 类型: {error_type}, 代码: {error_code}, 消息: {error_msg}")
                
                return "嗯，我想想"
                
        except Exception as e:
            logger.error(f"解析扣子v3响应失败: {e}")
            return "嗯，我想想"
    
    def _fallback_chat(self, messages):
        """fallback到OpenAI客户端"""
        if not self.fallback_client:
            return "嗯，我想想"
        
        try:
            response = self.fallback_client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "qwen-max"),
                messages=messages,
                temperature=0.8,
                max_tokens=200,
                top_p=0.8
            )
            content = response.choices[0].message.content
            return self._clean_response(content)
        except Exception as e:
            logger.error(f"Fallback OpenAI调用失败: {e}")
            return "嗯，我想想"
    
    def _clean_response(self, content):
        """清理响应内容"""
        if not content:
            return "嗯，我想想"
            
        content = content.strip()
        
        # 移除开头和结尾的引号
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        if content.startswith("'") and content.endswith("'"):
            content = content[1:-1]
        
        # 移除多余的空格和换行，但保留基本的句子结构
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # 🔧 调整截断逻辑，允许更长的回复，但仍然保持合理长度
        max_length = 150  # 增加最大长度限制
        if len(content) > max_length:
            # 尝试在句号、问号、感叹号处截断
            for i in range(max_length - 10, min(len(content), max_length + 20)):
                if content[i] in '。？！':
                    content = content[:i+1]
                    break
            else:
                # 如果找不到合适的截断点，在最大长度处截断并添加省略号
                content = content[:max_length-3] + "..."
        
        return content.strip() or "嗯，我想想"


class BuyerAgentSystem:
    """买家AI系统主控制器"""
    
    def __init__(self):
        # 初始化扣子客户端（买家专用）
        self.coze_client = CozeClient()
        
        # 初始化OpenAI客户端（作为备用）
        self.openai_client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )
        
        # 买家配置
        self.config = {
            'max_budget': float(os.getenv("BUYER_MAX_BUDGET", "5000")),
            'target_discount': float(os.getenv("BUYER_TARGET_DISCOUNT", "0.8")),
            'max_bargain_rounds': int(os.getenv("BUYER_MAX_ROUNDS", "3")),
            'patience_level': int(os.getenv("BUYER_PATIENCE", "2"))
        }
        
        # 初始化各专家Agent（使用扣子客户端）
        self.agents = {
            'inquiry': BuyerInquiryAgent(self.coze_client),
            'bargain': BuyerBargainAgent(self.coze_client, self.config),
            'evaluate': BuyerEvaluationAgent(self.coze_client),
            'decision': BuyerDecisionAgent(self.coze_client, self.config)
        }
        
        self.router = BuyerIntentRouter()
        
        # 记录各会话的对话轮次，避免过度回复
        self.chat_rounds = {}
        
        logger.info("🛒 买家AI系统已初始化 - 使用扣子智能体")
    
    def _should_skip_response(self, chat_id, seller_message, context):
        """判断是否应该跳过回复（避免过度对话）"""
        # 如果对话轮次太多，偶尔跳过回复
        rounds = len(context)
        
        # 超过15轮对话，10%概率跳过（降低沉默概率）
        if rounds > 15:
            import random
            if random.random() < 0.1:
                logger.info(f"🤐 买家AI: 对话轮次较多({rounds}轮)，偶尔保持沉默更自然")
                return True
        
        # 如果卖家消息很短（可能是敷衍），偶尔不回复（降低概率）
        if len(seller_message.strip()) < 3:
            import random
            if random.random() < 0.15:
                logger.info(f"🤐 买家AI: 卖家回复过于简短，保持沉默")
                return True
                
        return False
    
    def generate_buyer_response(self, seller_message, item_info, context, session_info):
        """生成买家回复"""
        try:
            chat_id = session_info.get('item_id', 'unknown')
            
            # # 检查是否应该跳过回复
            # if self._should_skip_response(chat_id, seller_message, context):
            #     return {
            #         'message': None,  # 返回None表示跳过回复
            #         'response_type': 'skip',
            #         'agent_used': 'skip',
            #         'seller_intent': 'skip',
            #         'stage': session_info.get('stage', 'inquiry')
            #     }
            
            # 1. 分析卖家回复意图
            seller_intent = self.router.classify_seller_response(seller_message)
            
            # 2. 根据会话阶段和卖家意图选择策略
            stage = session_info.get('stage', 'inquiry')
            
            logger.info(f"🛒 买家AI: 当前阶段={stage}, 卖家意图={seller_intent}")
            
            # 3. 智能选择合适的Agent
            if seller_intent == 'accept_offer':
                agent = self.agents['decision'] 
                response_type = 'decision'
            elif seller_intent in ['price_response', 'price_reject'] or '元' in seller_message:
                agent = self.agents['bargain']
                response_type = 'bargain'
            elif stage == 'inquiry' or len(context) < 4:  # 前几轮主要问询
                agent = self.agents['inquiry']
                response_type = 'inquiry'
            else:
                # 根据对话进度智能选择
                import random
                if random.random() < 0.7:  # 70%概率继续问询
                    agent = self.agents['inquiry']
                    response_type = 'inquiry'
                else:  # 30%概率开始议价
                    agent = self.agents['bargain']
                    response_type = 'bargain'
            
            # 4. 生成回复
            response = agent.generate(seller_message, item_info, context, session_info)
            
            return {
                'message': response,
                'response_type': response_type,
                'agent_used': agent.__class__.__name__,
                'seller_intent': seller_intent,
                'stage': stage
            }
            
        except Exception as e:
            logger.error(f"买家AI生成回复时出错: {e}")
            return {
                'message': "嗯嗯，我想想",  # 更自然的fallback
                'response_type': 'fallback',
                'agent_used': 'fallback',
                'seller_intent': 'unknown',
                'stage': 'inquiry'
            }


class BuyerIntentRouter:
    """买家意图路由器 - 分析卖家回复类型"""
    
    def __init__(self):
        self.seller_patterns = {
            'product_intro': {
                'keywords': ['成色', '全新', '九成新', '功能正常', '无磕碰', '原装', '配件齐全'],
                'patterns': [r'这个.{0,5}(很好|不错|完美)', r'(没有|无).{0,5}问题']
            },
            'price_response': {
                'keywords': ['最低', '底价', '优惠', '便宜', '折扣', '包邮'],
                'patterns': [r'\d+元', r'可以.{0,5}\d+', r'给你.{0,5}\d+']
            },
            'price_reject': {
                'keywords': ['不能再少', '已经很便宜', '亏本', '成本价', '不议价'],
                'patterns': [r'不能.{0,5}(少|便宜)', r'已经.{0,5}(最低|底价)']
            },
            'shipping_info': {
                'keywords': ['发货', '快递', '包邮', '邮费', '物流'],
                'patterns': [r'(今天|明天|\d+天).{0,5}发货']
            },
            'accept_offer': {
                'keywords': ['成交', '可以', '好的', '同意', '拍下'],
                'patterns': [r'(好|行|可以).{0,5}(的|了|吧)', r'就这个价']
            }
        }
    
    def classify_seller_response(self, seller_message):
        """分类卖家回复"""
        text_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', seller_message)
        
        for intent, rules in self.seller_patterns.items():
            # 关键词匹配
            if any(kw in text_clean for kw in rules['keywords']):
                return intent
            
            # 正则匹配
            for pattern in rules['patterns']:
                if re.search(pattern, text_clean):
                    return intent
        
        return 'general'


class BaseBuyerAgent:
    """买家Agent基类"""
    
    def __init__(self, coze_client):
        self.coze_client = coze_client
    
    def _call_llm(self, messages, temperature=0.8, conversation_context=None):
        """调用LLM（优先使用扣子，fallback到OpenAI）"""
        try:
            # 优先使用扣子智能体，传递会话上下文
            content = self.coze_client.chat_with_bot(
                messages, 
                conversation_context=conversation_context
            )
            
            if content and content != "嗯，我想想":
                logger.debug(f"扣子智能体回复: {content}")
                return content
            else:
                logger.warning("扣子智能体回复为空或默认值，使用fallback")
                return content
                
        except Exception as e:
            logger.error(f"调用扣子智能体失败: {e}")
            return "嗯，我想想"


class BuyerInquiryAgent(BaseBuyerAgent):
    """买家问询专家 - 负责询问商品详情"""
    
    def __init__(self, coze_client):
        super().__init__(coze_client)
        self.system_prompt = self._load_prompt('buyer_inquiry_prompt.txt')
        # 已询问的话题，避免重复
        self.asked_topics = {}
    
    def _load_prompt(self, filename):
        """加载提示词文件"""
        try:
            prompt_path = os.path.join('prompts', filename)
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"加载提示词文件失败 {filename}: {e}")
        
        # 默认提示词
        return """你是一个真实的买家，对商品感兴趣但很谨慎。说话风格：
1. 自然随意，像普通人聊天
2. 有点担心被坑，但不会直说
3. 会用一些口语化表达
4. 不会一次问很多问题

记住：你是真人，不是客服机器人！语气要自然、随性一些。"""
    
    def _get_asked_topics(self, chat_id, context):
        """获取已经询问过的话题"""
        asked_topics = set()
        
        # 从对话历史中分析已问过的问题
        for msg in context:
            if msg['role'] == 'user':  # 我方（买家）发的消息
                content = msg['content'].lower()
                if any(word in content for word in ['成色', '新旧', '使用', '磨损']):
                    asked_topics.add('condition')
                if any(word in content for word in ['包邮', '发货', '快递', '物流']):
                    asked_topics.add('shipping')
                if any(word in content for word in ['配件', '包装', '齐全', '原装']):
                    asked_topics.add('accessories')
                if any(word in content for word in ['问题', '毛病', '坏']):
                    asked_topics.add('issues')
                if any(word in content for word in ['验货', '当面', '检查']):
                    asked_topics.add('inspection')
                    
        return asked_topics
    
    def _choose_next_question(self, asked_topics, seller_message, current_price):
        """选择下一个要问的问题"""
        # 可问的话题优先级
        available_topics = {
            'condition': ['东西成色怎么样？', '用了多久了？', '有没有磨损？'],
            'issues': ['功能都正常吗？', '有什么毛病不？', '用着有问题吗？'],
            'shipping': ['包邮吗？', '什么时候能发货？', '用什么快递？'],
            'accessories': ['配件齐全吗？', '包装还在不？', '说明书这些有吗？'],
            'inspection': ['支持验货吗？', '可以当面交易吗？', '能先看看货吗？']
        }
        
        # 根据价格调整问题优先级
        if current_price > 500:
            priority_topics = ['condition', 'issues', 'accessories', 'shipping', 'inspection']
        else:
            priority_topics = ['condition', 'issues', 'shipping']
            
        # 选择还没问过的最高优先级话题
        for topic in priority_topics:
            if topic not in asked_topics and topic in available_topics:
                import random
                return random.choice(available_topics[topic])
                
        # 如果都问过了，根据卖家回复生成自然回应
        natural_responses = [
            '看起来不错啊', '嗯嗯，明白了', '好的好的', 
            '那还行', '了解了', '这样啊'
        ]
        import random
        return random.choice(natural_responses)
    
    def generate(self, seller_message, item_info, context, session_info):
        current_price = float(item_info.get('soldPrice', 0))
        chat_id = session_info.get('item_id', 'unknown')  # 使用item_id作为chat标识
        
        # 获取已询问的话题
        asked_topics = self._get_asked_topics(chat_id, context)
        
        # 智能选择下一个问题
        next_question = self._choose_next_question(asked_topics, seller_message, current_price)
        
        # 简化系统提示，让扣子智能体自己处理角色和对话
        # 历史对话记录已通过additional_messages传递，无需在这里重复
        messages = [
            {"role": "user", "content": seller_message}  # 直接传递卖家的真实消息
        ]
        
        # 🔧 传递会话上下文，确保扣子智能体能记住对话历史和商品信息
        conversation_context = {
            'item_id': session_info.get('item_id', 'unknown'),
            'chat_id': session_info.get('chat_id', session_info.get('item_id', 'unknown')),
            'chat_history': context,  # 传递完整的历史对话记录
            'current_message': seller_message,  # 传递当前真实的卖家消息
            'item_info': item_info  # 🔧 传递商品信息给扣子智能体
        }
        
        return self._call_llm(messages, temperature=0.8, conversation_context=conversation_context)


class BuyerBargainAgent(BaseBuyerAgent):
    """买家议价专家 - 负责价格谈判"""
    
    def __init__(self, coze_client, config):
        super().__init__(coze_client)
        self.config = config
        self.system_prompt = self._load_prompt('buyer_bargain_prompt.txt')
    
    def _load_prompt(self, filename):
        """加载提示词文件"""
        try:
            prompt_path = os.path.join('prompts', filename)
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"加载提示词文件失败 {filename}: {e}")
        
        # 默认提示词
        return """你是个真实买家，在跟卖家谈价钱。你的特点：
1. 会讲价但不会太过分
2. 表现出真心想买的样子
3. 语气自然，像普通人聊天
4. 有自己的底线，不会无底线压价

记住：谈价要有理有据，态度要诚恳！"""
    
    def _generate_natural_bargain(self, current_price, target_price, bargain_rounds, seller_message):
        """生成自然的议价话术"""
        import random
        
        # 分析卖家回复态度
        seller_lower = seller_message.lower()
        is_firm_rejection = any(word in seller_lower for word in ['不能', '不行', '最低', '底价', '亏本'])
        is_flexible = any(word in seller_lower for word in ['可以', '商量', '考虑', '看看'])
        
        # 自然议价表达方式
        bargain_styles = {
            1: [  # 第一轮，试探性
                f"这个能{target_price:.0f}拿不？",
                f"老板，{target_price:.0f}块怎么样？",
                f"能便宜点不？{target_price:.0f}块可以吗？",
                f"{target_price:.0f}块成交如何？"
            ],
            2: [  # 第二轮，显示诚意
                f"真心想要，{target_price:.0f}块行吗？",
                f"加点到{target_price:.0f}，马上转账",
                f"诚心要，{target_price:.0f}块可以的话现在就买",
                f"最高{target_price:.0f}了，现金秒"
            ],
            3: [  # 第三轮，最后机会
                f"最后价了，{target_price:.0f}块要不？",
                f"真的很想要，{target_price:.0f}块成不？",
                f"就{target_price:.0f}了，不行我就看别的了",
                f"给个痛快话，{target_price:.0f}块要不要？"
            ]
        }
        
        # 回应卖家态度的前缀
        response_prefixes = []
        if is_firm_rejection:
            response_prefixes = ["我理解，但是", "这样啊，那", "嗯，不过", "好吧，"]
        elif is_flexible:
            response_prefixes = ["那太好了，", "是这样啊，", "可以商量就好，", ""]
        else:
            response_prefixes = ["嗯，", "这样，", "那", ""]
            
        # 选择合适的议价话术
        round_key = min(bargain_rounds + 1, 3)
        bargain_text = random.choice(bargain_styles.get(round_key, bargain_styles[3]))
        prefix = random.choice(response_prefixes)
        
        return f"{prefix}{bargain_text}"
    
    def generate(self, seller_message, item_info, context, session_info):
        current_price = float(item_info.get('soldPrice', 0))
        
        # 计算议价轮次
        bargain_rounds = self._count_bargain_rounds(context)
        max_rounds = self.config['max_bargain_rounds']
        
        # 动态调整目标价格（更真实）
        base_discount = self.config['target_discount']
        if bargain_rounds == 0:
            target_price = current_price * 0.7  # 首次大胆点
        elif bargain_rounds == 1:
            target_price = current_price * 0.75  # 稍微提高
        elif bargain_rounds == 2:
            target_price = current_price * 0.8   # 接近底线
        else:
            target_price = current_price * 0.85  # 最后价格
        
        # 如果超过最大轮次，决定是否接受
        if bargain_rounds >= max_rounds:
            if current_price <= self.config['max_budget']:
                accept_responses = [
                    "算了，就这个价吧，要了",
                    "行吧，就按你说的",
                    "好，这个价格我要了", 
                    "成交，现在付款"
                ]
                import random
                return random.choice(accept_responses)
            else:
                decline_responses = [
                    "算了，超预算了，谢谢啊",
                    "价格有点高，我再看看其他的",
                    "好吧，那我考虑下，谢谢",
                    "不好意思，预算不够"
                ]
                import random
                return random.choice(decline_responses)
        
        # 生成自然议价话术
        natural_bargain = self._generate_natural_bargain(
            current_price, target_price, bargain_rounds, seller_message
        )
        
        # 简化系统提示，让扣子智能体自己处理议价对话
        # 历史对话记录已通过additional_messages传递，扣子智能体会理解议价上下文
        messages = [
            {"role": "user", "content": seller_message}  # 直接传递卖家的真实消息
        ]
        
        # 🔧 传递会话上下文，确保扣子智能体能记住对话历史和商品信息
        conversation_context = {
            'item_id': session_info.get('item_id', 'unknown'),
            'chat_id': session_info.get('chat_id', session_info.get('item_id', 'unknown')),
            'chat_history': context,  # 传递完整的历史对话记录
            'current_message': seller_message,  # 传递当前真实的卖家消息
            'item_info': item_info  # 🔧 传递商品信息给扣子智能体
        }
        
        return self._call_llm(messages, temperature=0.9, conversation_context=conversation_context)
    
    def _count_bargain_rounds(self, context):
        """统计议价轮次"""
        count = 0
        for msg in context:
            if msg['role'] == 'user' and ('元' in msg['content'] or '价格' in msg['content'] or '便宜' in msg['content']):
                count += 1
        return count


class BuyerEvaluationAgent(BaseBuyerAgent):
    """买家评估专家 - 评估商品和卖家"""
    
    def __init__(self, coze_client):
        super().__init__(coze_client)
    
    def generate(self, seller_message, item_info, context, session_info):
        """评估商品价值和购买建议"""
        current_price = float(item_info.get('soldPrice', 0))
        
        # 简单的评估逻辑
        evaluation = {
            'condition_score': 7.0,  # 成色评分
            'price_score': 6.0,      # 价格评分  
            'seller_score': 7.0,     # 卖家评分
            'overall_score': 6.7     # 综合评分
        }
        
        # 基于关键词调整评分
        if any(word in seller_message for word in ['全新', '未拆封', '没用过']):
            evaluation['condition_score'] = 9.0
        elif any(word in seller_message for word in ['九成新', '几乎全新']):
            evaluation['condition_score'] = 8.0
        elif any(word in seller_message for word in ['有使用痕迹', '正常使用']):
            evaluation['condition_score'] = 6.0
            
        if current_price < 100:
            evaluation['price_score'] = 8.0
        elif current_price < 500:
            evaluation['price_score'] = 7.0
        else:
            evaluation['price_score'] = 5.0
            
        evaluation['overall_score'] = (
            evaluation['condition_score'] * 0.4 + 
            evaluation['price_score'] * 0.4 + 
            evaluation['seller_score'] * 0.2
        )
        
        return evaluation


class BuyerDecisionAgent(BaseBuyerAgent):
    """买家决策专家 - 最终购买决策"""
    
    def __init__(self, coze_client, config):
        super().__init__(coze_client)
        self.config = config
        self.system_prompt = self._load_prompt('buyer_decision_prompt.txt')
    
    def _load_prompt(self, filename):
        """加载提示词文件"""
        try:
            prompt_path = os.path.join('prompts', filename)
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"加载提示词文件失败 {filename}: {e}")
        
        # 默认提示词
        return """你是个普通买家，要做最终决定。特点：
1. 不会冲动，会理性考虑
2. 预算有限，不会乱花钱  
3. 语气自然随意
4. 决定了就干脆，不拖泥带水

记住：你是真人，决策要果断！"""
    
    def generate(self, seller_message, item_info, context, session_info):
        current_price = float(item_info.get('soldPrice', 0))
        max_budget = self.config['max_budget']
        
        # 分析卖家回复，判断是否达成交易意向
        seller_lower = seller_message.lower()
        is_agreement = any(word in seller_lower for word in ['可以', '好的', '成交', '行', '同意'])
        is_final_offer = any(word in seller_lower for word in ['最低', '底价', '不能再少'])
        
        # 自然决策回复
        if is_agreement and current_price <= max_budget:
            # 卖家同意价格且在预算内
            accept_responses = [
                "好嘞，那就这样，怎么付款？",
                "成交！现在转账还是货到付款？", 
                "行，那我现在就买了",
                "好的好的，支付宝还是微信？"
            ]
            import random
            decision_text = random.choice(accept_responses)
            decision_type = 'accept'
        elif current_price > max_budget:
            # 超预算了
            reject_responses = [
                "算了，超预算了，谢谢啊",
                "价格有点高，我再看看",  
                "不好意思，预算不够",
                "太贵了，我考虑下别的"
            ]
            import random
            decision_text = random.choice(reject_responses)
            decision_type = 'reject'
        elif is_final_offer:
            # 卖家报最终价，需要决定
            if current_price <= max_budget * 1.1:  # 稍微超预算可以接受
                consider_responses = [
                    "嗯...让我想想",
                    "这个价格我考虑一下",
                    "有点贵，我再想想", 
                    "容我考虑考虑"
                ]
                import random
                decision_text = random.choice(consider_responses)
                decision_type = 'consider'
            else:
                reject_responses = [
                    "算了，真的超预算了",
                    "不行，太贵了",
                    "还是算了吧，谢谢",
                    "价格确实接受不了"
                ]
                import random
                decision_text = random.choice(reject_responses)
                decision_type = 'reject'
        else:
            # 默认情况，继续考虑
            neutral_responses = [
                "嗯，我想想",
                "让我考虑一下",
                "这样啊，我想想",
                "好，我考虑考虑"
            ]
            import random
            decision_text = random.choice(neutral_responses)
            decision_type = 'consider'
        
        return {
            'message': decision_text,
            'decision': decision_type,
            'price': current_price,
            'within_budget': current_price <= max_budget
        }
    
    def _analyze_decision(self, decision_text):
        """分析决策类型"""
        if any(word in decision_text for word in ['买了', '要了', '拍下', '成交', '付款', '转账']):
            return 'accept'
        elif any(word in decision_text for word in ['不要', '算了', '放弃', '太贵', '超预算']):
            return 'reject' 
        else:
            return 'consider' 