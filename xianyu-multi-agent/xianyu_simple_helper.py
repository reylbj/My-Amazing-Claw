#!/usr/bin/env python3
"""
闲鱼发布助手 - 简化版
生成文案后，你手动复制粘贴到闲鱼发布页面
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def generate_xianyu_content(service_type: str) -> dict:
    """生成闲鱼商品文案"""
    
    client = OpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL")
    )
    
    prompt = f"""
你是一个闲鱼爆款文案专家。请为以下服务生成一个吸引人的闲鱼商品发布内容：

服务类型: {service_type}

要求:
1. 标题: 15-30字，吸引眼球，包含核心卖点，用｜分隔关键词
2. 描述: 200-500字，使用emoji，分段清晰，突出优势和案例
3. 价格: 给出合理的起步价（元），要有吸引力
4. 标签: 3-5个相关标签

请以JSON格式返回:
{{
  "title": "标题",
  "description": "描述（包含emoji和换行）",
  "price": "价格数字",
  "tags": ["标签1", "标签2", "标签3"]
}}
"""
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),
            messages=[
                {"role": "system", "content": "你是一个专业的闲鱼文案撰写专家，擅长写出高转化率的商品描述。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        
        # 提取JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        result = json.loads(content)
        return result
        
    except Exception as e:
        print(f"❌ AI生成失败: {e}")
        return None


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           闲鱼发布助手 - AI文案生成                         ║
║              Powered by OpenClaw AI                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 选择服务类型
    print("\n📋 请选择要发布的服务类型:")
    print("1. AI文案代写")
    print("2. PPT设计制作")
    print("3. 视频剪辑")
    print("4. Logo设计")
    print("5. 自定义")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    service_map = {
        "1": "AI文案代写",
        "2": "PPT设计制作",
        "3": "视频剪辑",
        "4": "Logo设计"
    }
    
    if choice == "5":
        service_type = input("请输入自定义服务类型: ").strip()
    else:
        service_type = service_map.get(choice, "AI文案代写")
    
    print(f"\n✅ 已选择: {service_type}")
    print("\n🤖 AI正在生成爆款文案...\n")
    
    # 生成文案
    content = generate_xianyu_content(service_type)
    
    if not content:
        print("生成失败，请重试")
        return
    
    # 显示文案
    print("=" * 60)
    print("📝 生成的文案（请复制到闲鱼发布页面）")
    print("=" * 60)
    
    print(f"\n【标题】（复制下面这行）")
    print(content['title'])
    
    print(f"\n【价格】")
    print(f"¥{content['price']}")
    
    print(f"\n【描述】（复制下面所有内容）")
    print(content['description'])
    
    print(f"\n【标签】（逐个添加）")
    for i, tag in enumerate(content['tags'], 1):
        print(f"{i}. {tag}")
    
    print("\n" + "=" * 60)
    
    # 保存到文件
    output_file = f"data/xianyu_content_{service_type}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 文案已保存到: {output_file}")
    
    # 操作指南
    print("\n📖 发布步骤:")
    print("1. 打开闲鱼APP或网页版 https://www.goofish.com/publish")
    print("2. 点击【发布】按钮")
    print("3. 复制上面的【标题】粘贴到标题栏")
    print("4. 复制上面的【描述】粘贴到描述栏")
    print("5. 填写价格（建议起步价）")
    print("6. 添加标签（逐个输入）")
    print("7. 上传图片（可选）")
    print("8. 点击发布")
    
    print("\n✅ 完成！")


if __name__ == "__main__":
    main()
