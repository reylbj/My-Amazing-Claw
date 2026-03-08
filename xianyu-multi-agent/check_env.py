#!/usr/bin/env python3
"""
环境变量配置检查脚本
用于诊断.env文件配置问题
"""

import os
from dotenv import load_dotenv

def check_env_config():
    """检查环境变量配置"""
    print("🔍 环境变量配置检查")
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
    
    # 检查扣子相关配置
    print("📋 扣子(Coze)配置:")
    coze_api_key_raw = os.getenv("COZE_API_KEY", "")
    coze_bot_id_raw = os.getenv("COZE_BUYER_BOT_ID", "")
    coze_base_url_raw = os.getenv("COZE_BASE_URL", "https://api.coze.cn")
    
    coze_api_key = clean_env_var("COZE_API_KEY")
    coze_bot_id = clean_env_var("COZE_BUYER_BOT_ID")
    coze_base_url = clean_env_var("COZE_BASE_URL", "https://api.coze.cn")
    
    print(f"   COZE_API_KEY 原始值: '{coze_api_key_raw[:20]}...' (长度: {len(coze_api_key_raw)})")
    print(f"   COZE_API_KEY 清理后: '{coze_api_key[:10]}...{coze_api_key[-4:]}' (长度: {len(coze_api_key)})" if coze_api_key else "   COZE_API_KEY: ❌ 清理后为空")
    print(f"   COZE_BUYER_BOT_ID 原始值: '{coze_bot_id_raw[:20]}...' (长度: {len(coze_bot_id_raw)})")
    print(f"   COZE_BUYER_BOT_ID 清理后: '{coze_bot_id[:12]}...' (长度: {len(coze_bot_id)})" if coze_bot_id else "   COZE_BUYER_BOT_ID: ❌ 清理后为空")
    print(f"   COZE_BASE_URL 原始值: '{coze_base_url_raw}' (长度: {len(coze_base_url_raw)})")
    print(f"   COZE_BASE_URL 清理后: '{coze_base_url}' (长度: {len(coze_base_url)})")
    
    # 检查是否有问题
    api_key_has_issue = coze_api_key_raw != coze_api_key
    bot_id_has_issue = coze_bot_id_raw != coze_bot_id
    base_url_has_issue = coze_base_url_raw != coze_base_url
    
    if api_key_has_issue:
        print(f"   ⚠️  COZE_API_KEY 包含注释或特殊字符！")
    
    if bot_id_has_issue:
        print(f"   ⚠️  COZE_BUYER_BOT_ID 包含注释或特殊字符！")
    
    if base_url_has_issue:
        print(f"   ⚠️  COZE_BASE_URL 包含注释或特殊字符！")
        print(f"   建议修改 .env 文件，格式：COZE_BASE_URL={coze_base_url}")
    
    print()
    
    # 检查通义千问配置
    print("📋 通义千问配置:")
    api_key = os.getenv("API_KEY", "")
    model_base_url = os.getenv("MODEL_BASE_URL", "")
    model_name = os.getenv("MODEL_NAME", "")
    
    print(f"   API_KEY: '{api_key[:10]}...{api_key[-4:]}' (长度: {len(api_key)})" if api_key else "   API_KEY: ❌ 未设置")
    print(f"   MODEL_BASE_URL: '{model_base_url}'" if model_base_url else "   MODEL_BASE_URL: ❌ 未设置")
    print(f"   MODEL_NAME: '{model_name}'" if model_name else "   MODEL_NAME: ❌ 未设置")
    
    print()
    
    # 提供修复建议
    has_issues = False
    
    if not coze_api_key or not coze_bot_id:
        print("❌ 扣子配置不完整")
        has_issues = True
    
    if api_key_has_issue or bot_id_has_issue or base_url_has_issue:
        print("❌ 扣子配置格式有问题（包含注释或特殊字符）")
        has_issues = True
        
    if not api_key:
        print("❌ 通义千问API密钥未配置")
        has_issues = True
    
    if has_issues:
        print("\n🔧 修复建议:")
        print("1. 检查.env文件格式，确保没有多余空格和注释")
        print("2. 确保变量名和值之间用=连接，无空格")
        print("3. 不要在同一行添加注释（#号后的内容）")
        print("4. 正确的格式示例:")
        print("   COZE_API_KEY=pat_your_api_key_here")
        print("   COZE_BUYER_BOT_ID=7319498133556428806") 
        print("   COZE_BASE_URL=https://api.coze.cn")
        print("\n5. 错误的格式示例:")
        print("   COZE_BASE_URL=https://api.coze.cn            # 扣子API地址  ❌")
        print("   COZE_API_KEY = pat_your_api_key_here  ❌")
        print("\n6. 修复后请重新运行测试: python test_coze.py")
    else:
        print("✅ 配置检查通过！")
    
    return not has_issues

if __name__ == "__main__":
    check_env_config() 