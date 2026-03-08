#!/usr/bin/env python3
"""
OpenClaw集成脚本 - 闲鱼自动发布
可以从OpenClaw直接调用
"""

import sys
import os
import asyncio
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'xianyu-multi-agent'))

from xianyu_auto_publish import XianyuAutoPublisher


async def publish_from_openclaw(service_type: str, custom_content: dict = None):
    """
    从OpenClaw调用的发布函数
    
    Args:
        service_type: 服务类型
        custom_content: 自定义内容（可选）
    """
    publisher = XianyuAutoPublisher()
    
    try:
        # 生成或使用自定义文案
        if custom_content:
            content = custom_content
        else:
            content = publisher.generate_product_content(service_type)
        
        print(f"📝 文案: {content['title']}")
        
        # 初始化浏览器
        await publisher.init_browser(headless=False)
        await publisher.load_cookies()
        
        # 发布
        success = await publisher.publish_product(content)
        
        return {
            "success": success,
            "content": content
        }
        
    finally:
        await publisher.close()


if __name__ == "__main__":
    # 命令行调用示例
    # python3 scripts/xianyu_publish_wrapper.py "AI文案代写"
    
    if len(sys.argv) < 2:
        print("用法: python3 xianyu_publish_wrapper.py <服务类型>")
        sys.exit(1)
    
    service_type = sys.argv[1]
    result = asyncio.run(publish_from_openclaw(service_type))
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
