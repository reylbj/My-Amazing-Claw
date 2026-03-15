#!/usr/bin/env python3
"""
删除指定商品的所有消息记录
"""

import os
import sys
from loguru import logger
from context_manager import ChatContextManager

def delete_item_messages(item_id):
    """删除指定商品的所有消息记录"""
    
    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<level>{level: <8}</level> | {message}")
    
    # 初始化上下文管理器
    try:
        context_manager = ChatContextManager()
        logger.info(f"开始删除商品 {item_id} 的所有记录...")
        
        # 执行删除操作
        result = context_manager.delete_item_messages(item_id)
        
        if result:
            total_deleted = sum(result.values())
            if total_deleted > 0:
                logger.info(f"🎉 删除操作完成！共删除 {total_deleted} 条记录")
                return True
            else:
                logger.warning(f"⚠️ 未找到商品 {item_id} 的任何记录")
                return False
        else:
            logger.error(f"❌ 删除操作失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 删除操作异常: {e}")
        return False

def main():
    """主函数"""
    
    # 指定要删除的商品ID
    item_id = "936278262348"
    
    print(f"🗑️ 即将删除商品 {item_id} 的所有记录")
    print("包括：消息记录、会话信息、议价记录、评估记录等")
    print()
    
    # 确认操作
    confirm = input("确认删除吗？(输入 'yes' 确认): ").strip().lower()
    
    if confirm == 'yes':
        success = delete_item_messages(item_id)
        if success:
            print("\n✅ 删除完成！")
        else:
            print("\n❌ 删除失败，请检查日志")
    else:
        print("❌ 操作已取消")
        return False
    
    return True

if __name__ == "__main__":
    main() 