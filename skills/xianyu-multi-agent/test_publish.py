#!/usr/bin/env python3
"""
闲鱼全自动发布 - 测试版
使用预设文案，专注测试发布流程
"""

import asyncio
import os
from xianyu_smart_publish import SmartXianyuPublisher
from loguru import logger


async def test_publish():
    """测试发布流程 - 使用预设文案"""
    
    # 使用之前生成的优质文案
    content = {
        "title": "AI文案代写｜小红书种草｜公众号爆文｜10分钟交稿",
        "description": """✨ 专业AI文案服务，让你的内容脱颖而出！

📝 服务范围：
• 小红书种草笔记/爆款标题
• 公众号推文/热点追踪
• 电商详情页/产品卖点提炼
• 短视频脚本/直播话术
• 品牌slogan/广告文案

💡 为什么选我？
✅ 10分钟极速交稿，急稿优先
✅ 不满意免费改到满意为止
✅ 已服务500+客户，好评率99%
✅ 懂平台规则，避免违规风险
✅ 提供3个版本供选择

🔥 真实案例：
某美妆博主用我的文案，单篇笔记涨粉2000+
某餐饮店用我的推文，当天到店量翻3倍

💰 价格透明：
基础文案 9.9元起
爆款定制 29.9元起
批量套餐更优惠

⚡ 下单流程：
1️⃣ 告诉我需求和行业
2️⃣ 10分钟内发初稿
3️⃣ 免费修改直到满意

🎁 限时福利：前10名下单送小红书标题优化！

私信秒回，随时咨询不收费~""",
        "price": "9.9",
        "tags": ["AI文案", "小红书代写", "公众号文案", "爆款标题", "文案策划"]
    }
    
    logger.info("=" * 60)
    logger.info("使用预设文案进行测试")
    logger.info("=" * 60)
    logger.info(f"标题: {content['title']}")
    logger.info(f"价格: ¥{content['price']}")
    
    publisher = SmartXianyuPublisher()
    
    try:
        # 初始化浏览器
        await publisher.init_browser(headless=False)
        
        # 发布商品
        success = await publisher.publish_product(content)
        
        if success:
            logger.success("=" * 60)
            logger.success("✅ 发布成功！")
            logger.success("=" * 60)
        else:
            logger.error("=" * 60)
            logger.error("❌ 发布失败")
            logger.error("=" * 60)
        
        return success
        
    finally:
        await asyncio.sleep(5)
        await publisher.close()


if __name__ == "__main__":
    result = asyncio.run(test_publish())
    exit(0 if result else 1)
