#!/usr/bin/env python3
"""
扣子买家AI配置测试脚本
用于验证扣子API配置是否正确
"""

import os
import sys
from dotenv import load_dotenv
from loguru import logger
from BuyerAgent import CozeClient

def test_coze_config():
    """测试扣子配置"""
    print("🤖 扣子买家AI配置测试")
    print("=" * 50)
    
    # 加载环境变量
    load_dotenv()
    
    def clean_env_var(var_name, default=""):
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
    
    # 检查必要的环境变量（清理空格和注释）
    api_key = clean_env_var("COZE_API_KEY")
    bot_id = clean_env_var("COZE_BUYER_BOT_ID")
    base_url = clean_env_var("COZE_BASE_URL", "https://api.coze.cn")
    
    print(f"📡 API地址: {base_url}")
    print(f"🔑 API密钥: {'✅ 已配置 (' + api_key[:8] + '...)' if api_key else '❌ 未配置'}")
    print(f"🤖 智能体ID: {'✅ 已配置 (' + bot_id[:12] + '...)' if bot_id else '❌ 未配置'}")
    print()
    
    # 调试信息
    if api_key and bot_id:
        print("🔧 调试信息:")
        print(f"   API密钥长度: {len(api_key)} 字符")
        print(f"   智能体ID长度: {len(bot_id)} 字符")
        print(f"   API地址长度: {len(base_url)} 字符")
        print()
    
    if not api_key or not bot_id:
        print("❌ 扣子配置不完整")
        print("请在.env文件中配置COZE_API_KEY和COZE_BUYER_BOT_ID")
        print("详细配置说明请查看: COZE_BUYER_SETUP.md")
        return False
    
    # 初始化扣子客户端
    try:
        print("🔄 正在初始化扣子客户端...")
        coze_client = CozeClient()
        
        # 测试对话
        print("🔄 正在测试扣子智能体对话（v3 API + 流式响应）...")
        
        # 模拟会话上下文，包含历史对话记录
        test_conversation_context = {
            'item_id': '12345',
            'chat_id': 'test_chat_001',
            'chat_history': [
                {"role": "user", "content": "嗯，东西成色怎么样？"},
                {"role": "assistant", "content": "这个商品九成新，功能都正常"},
                {"role": "user", "content": "那包邮吗？"}
            ],
            'current_message': "包邮的，顺丰快递发货"  # 当前卖家的真实回复
        }
        
        # 简化测试消息，直接传递卖家的真实消息
        test_messages = [
            {
                "role": "user",
                "content": "包邮的，顺丰快递发货"  # 卖家的真实回复
            }
        ]
        
        # 测试会话管理
        expected_conversation_id = f"buyer_12345_{hash('test_chat_001') % 1000}"
        print(f"🔗 预期会话ID: {expected_conversation_id}")
        print(f"📡 使用v3 API端点: {coze_client.base_url}/v3/chat?conversation_id={expected_conversation_id}")
        print(f"🌊 启用流式响应: True")
        print(f"📚 历史消息数量: {len(test_conversation_context['chat_history'])}")
        
        response = coze_client.chat_with_bot(
            test_messages, 
            conversation_context=test_conversation_context,
            stream=True  # 明确启用流式响应
        )
        
        if response and response != "嗯，我想想":
            print(f"✅ 扣子智能体测试成功！")
            print(f"📝 测试回复: {response}")
            print(f"🔗 会话管理: 使用conversation_id管理单个商品的完整对话上下文")
            print()
            print("🎉 扣子买家AI配置正确，系统将使用扣子智能体")
            return True
        else:
            print(f"⚠️ 扣子智能体回复异常: {response}")
            print("系统将使用通义千问作为fallback")
            return False
            
    except Exception as e:
        print(f"❌ 扣子测试失败: {e}")
        print("系统将使用通义千问作为fallback")
        return False

def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<level>{level: <8}</level> | {message}")
    
    success = test_coze_config()
    
    print()
    print("=" * 50)
    if success:
        print("✅ 测试完成 - 扣子配置正确")
        print("现在可以运行 python main.py 开始使用")
    else:
        print("⚠️ 测试完成 - 扣子配置有问题") 
        print("系统会自动使用通义千问，买家AI功能不受影响")
        print("如需优化体验，请参考 COZE_BUYER_SETUP.md 配置扣子")

if __name__ == "__main__":
    main() 