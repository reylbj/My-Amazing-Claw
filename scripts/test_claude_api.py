#!/usr/bin/env python3
"""
测试 Claude API 调用
验证 api123 提供商的 Claude Sonnet 4.6 模型是否正常工作
"""

import requests
import json
import os

# Gateway 配置
GATEWAY_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
AUTH_TOKEN = os.environ.get("OPENCLAW_AUTH_TOKEN", "replace-with-your-gateway-token")

def test_claude_sonnet():
    """测试 Claude Sonnet 4.6 模型"""

    print("🧪 测试 Claude Sonnet 4.6 模型调用\n")

    # 构造请求
    url = f"{GATEWAY_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "api123/claude-sonnet-4-6",
        "messages": [
            {
                "role": "user",
                "content": "请用一句话介绍你自己，并说明你的模型版本。"
            }
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }

    print(f"📤 发送请求到: {url}")
    print(f"📦 模型: {payload['model']}\n")

    if AUTH_TOKEN == "replace-with-your-gateway-token":
        print("❌ 未设置 OPENCLAW_AUTH_TOKEN，请先导出网关认证令牌")
        return False

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)

        print(f"📊 响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            # 提取回复内容
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"\n✅ 模型响应成功!\n")
                print(f"💬 回复内容:\n{content}\n")

                # 显示使用统计
                if 'usage' in result:
                    usage = result['usage']
                    print(f"📈 Token 使用:")
                    print(f"   输入: {usage.get('prompt_tokens', 'N/A')}")
                    print(f"   输出: {usage.get('completion_tokens', 'N/A')}")
                    print(f"   总计: {usage.get('total_tokens', 'N/A')}")

                return True
            else:
                print(f"❌ 响应格式异常: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"❌ 请求失败")
            print(f"响应内容: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ 请求超时 (30秒)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确认 gateway 是否运行")
        print("提示: 运行 'openclaw gateway start' 启动 gateway")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        return False

def test_model_list():
    """测试获取模型列表"""

    print("\n" + "="*60)
    print("📋 获取可用模型列表\n")

    url = f"{GATEWAY_URL}/v1/models"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()

            if 'data' in result:
                models = result['data']
                print(f"✅ 找到 {len(models)} 个可用模型:\n")

                # 筛选 Claude 模型
                claude_models = [m for m in models if 'claude' in m.get('id', '').lower()]

                if claude_models:
                    print("🤖 Claude 模型:")
                    for model in claude_models:
                        print(f"   - {model.get('id', 'Unknown')}")

                # 筛选 Gemini 模型
                gemini_models = [m for m in models if 'gemini' in m.get('id', '').lower()]

                if gemini_models:
                    print("\n🤖 Gemini 模型:")
                    for model in gemini_models:
                        print(f"   - {model.get('id', 'Unknown')}")

                return True
            else:
                print(f"❌ 响应格式异常: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return False
        else:
            print(f"❌ 请求失败 (状态码: {response.status_code})")
            return False

    except Exception as e:
        print(f"❌ 获取模型列表失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("OpenClaw Gateway - Claude API 测试")
    print("="*60 + "\n")

    # 测试模型列表
    list_success = test_model_list()

    # 测试 Claude Sonnet 调用
    call_success = test_claude_sonnet()

    # 总结
    print("\n" + "="*60)
    print("📊 测试结果总结")
    print("="*60)
    print(f"模型列表获取: {'✅ 成功' if list_success else '❌ 失败'}")
    print(f"Claude Sonnet 4.6 调用: {'✅ 成功' if call_success else '❌ 失败'}")

    if list_success and call_success:
        print("\n🎉 所有测试通过! Claude Sonnet 4.6 已成功配置并可正常使用。")
    else:
        print("\n⚠️  部分测试失败，请检查配置。")
