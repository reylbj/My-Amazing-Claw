#!/usr/bin/env python3
"""
配置迁移工具

将现有的单账号配置迁移到多账号系统，包括：
1. 环境变量配置迁移
2. 提示词文件迁移
3. 聊天历史数据迁移（如果需要）
"""

import os
import shutil
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from context_manager import ChatContextManager
from utils.xianyu_utils import trans_cookies


class ConfigMigrator:
    """配置迁移器"""
    
    def __init__(self):
        self.context_manager = ChatContextManager()
        self.backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        load_dotenv()  # 加载现有环境变量
        
        logger.info("配置迁移工具初始化完成")
    
    def check_migration_needed(self) -> bool:
        """
        检查是否需要迁移
        
        Returns:
            bool: 是否需要迁移
        """
        # 检查是否已有多账号数据
        try:
            accounts = self.context_manager.get_all_accounts()
            if accounts:
                logger.info(f"发现 {len(accounts)} 个已配置的账号，无需迁移")
                return False
            
            # 检查是否有旧的单账号配置
            cookies_str = os.getenv("COOKIES_STR")
            if cookies_str:
                logger.info("发现单账号配置，需要迁移")
                return True
            
            logger.info("未发现需要迁移的配置")
            return False
            
        except Exception as e:
            logger.error(f"检查迁移需求时出错: {e}")
            return False
    
    def backup_current_config(self):
        """备份当前配置"""
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            
            # 备份环境文件
            if os.path.exists('.env'):
                shutil.copy2('.env', os.path.join(self.backup_dir, '.env'))
                logger.info("已备份 .env 文件")
            
            # 备份提示词文件
            if os.path.exists('prompts'):
                shutil.copytree('prompts', os.path.join(self.backup_dir, 'prompts'))
                logger.info("已备份 prompts 目录")
            
            # 备份数据库文件
            if os.path.exists('data/chat_history.db'):
                shutil.copy2('data/chat_history.db', os.path.join(self.backup_dir, 'chat_history.db'))
                logger.info("已备份聊天历史数据库")
            
            logger.info(f"配置备份完成，备份目录: {self.backup_dir}")
            
        except Exception as e:
            logger.error(f"备份配置时出错: {e}")
            raise
    
    def migrate_single_account_config(self) -> bool:
        """
        迁移单账号配置到多账号系统
        
        Returns:
            bool: 迁移是否成功
        """
        try:
            # 从环境变量读取单账号配置
            cookies_str = os.getenv("COOKIES_STR")
            if not cookies_str:
                logger.warning("未找到 COOKIES_STR 环境变量")
                return False
            
            # 解析Cookie获取用户ID
            try:
                cookies = trans_cookies(cookies_str)
                user_id = cookies.get('unb')
                if not user_id:
                    logger.error("无法从Cookie中获取用户ID")
                    return False
            except Exception as e:
                logger.error(f"解析Cookie失败: {e}")
                return False
            
            # 生成默认账号名
            account_name = f"主账号_{user_id[:8]}"
            
            # 创建账号记录
            logger.info(f"创建账号: {account_name}")
            account_id = self.context_manager.create_account(
                account_name=account_name,
                cookies=cookies_str,
                user_id=user_id,
                seller_enabled=True,  # 默认启用卖家功能
                buyer_enabled=True    # 默认启用买家功能
            )
            
            if not account_id:
                logger.error("创建账号失败")
                return False
            
            # 迁移提示词配置
            self.migrate_prompts(account_id)
            
            logger.info(f"单账号配置迁移成功，账号ID: {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"迁移单账号配置时出错: {e}")
            return False
    
    def migrate_prompts(self, account_id: int):
        """
        迁移提示词文件到数据库
        
        Args:
            account_id: 账号ID
        """
        try:
            prompt_types = ['classify', 'price', 'tech', 'default']
            prompts_dir = 'prompts'
            
            if not os.path.exists(prompts_dir):
                logger.warning(f"提示词目录不存在: {prompts_dir}")
                return
            
            migrated_count = 0
            
            for prompt_type in prompt_types:
                prompt_file = os.path.join(prompts_dir, f"{prompt_type}_prompt.txt")
                
                if os.path.exists(prompt_file):
                    try:
                        with open(prompt_file, 'r', encoding='utf-8') as f:
                            prompt_content = f.read()
                        
                        if prompt_content.strip():
                            self.context_manager.save_account_prompt(
                                account_id, prompt_type, prompt_content
                            )
                            migrated_count += 1
                            logger.info(f"已迁移提示词: {prompt_type}")
                        
                    except Exception as e:
                        logger.warning(f"迁移提示词 {prompt_type} 时出错: {e}")
            
            logger.info(f"提示词迁移完成，共迁移 {migrated_count} 个提示词")
            
        except Exception as e:
            logger.error(f"迁移提示词时出错: {e}")
    
    def create_default_prompts_if_missing(self, account_id: int):
        """
        如果缺少提示词，创建默认提示词
        
        Args:
            account_id: 账号ID
        """
        try:
            existing_prompts = self.context_manager.get_account_prompts(account_id)
            
            default_prompts = {
                'classify': """你是一个智能消息分类器，需要判断用户消息的意图类型。

请将用户消息分类为以下类型之一：
- price: 价格相关（议价、询价、降价等）
- tech: 技术咨询（规格、参数、使用方法等）
- default: 其他一般性对话

只返回分类结果，不要其他内容。""",
                
                'price': """你是一个专业的闲鱼卖家，擅长价格谈判。

谈判原则：
1. 第一次议价：适当让步，但不超过10%
2. 多次议价：逐步降低让步幅度
3. 底线价格：不低于标价的80%
4. 语气友好但坚持原则

请根据商品信息和对话历史，生成合适的回复。""",
                
                'tech': """你是一个专业的商品技术顾问。

回复要求：
1. 专业准确地回答技术问题
2. 如果不确定，诚实说明
3. 提供实用的使用建议
4. 语言简洁易懂

请根据商品信息回答用户的技术咨询。""",
                
                'default': """你是一个友好的闲鱼卖家客服。

服务标准：
1. 语气热情友好
2. 回复及时准确  
3. 耐心解答疑问
4. 促进交易达成

请根据用户消息提供恰当的客服回复。"""
            }
            
            created_count = 0
            for prompt_type, prompt_content in default_prompts.items():
                if prompt_type not in existing_prompts:
                    self.context_manager.save_account_prompt(
                        account_id, prompt_type, prompt_content
                    )
                    created_count += 1
                    logger.info(f"创建默认提示词: {prompt_type}")
            
            if created_count > 0:
                logger.info(f"创建默认提示词完成，共创建 {created_count} 个")
            
        except Exception as e:
            logger.error(f"创建默认提示词时出错: {e}")
    
    def run_migration(self) -> bool:
        """
        运行完整的迁移流程
        
        Returns:
            bool: 迁移是否成功
        """
        try:
            logger.info("=" * 50)
            logger.info("开始配置迁移流程")
            logger.info("=" * 50)
            
            # 1. 检查是否需要迁移
            if not self.check_migration_needed():
                logger.info("无需迁移，退出")
                return True
            
            # 2. 备份当前配置
            logger.info("步骤 1: 备份当前配置")
            self.backup_current_config()
            
            # 3. 迁移单账号配置
            logger.info("步骤 2: 迁移单账号配置")
            success = self.migrate_single_account_config()
            
            if not success:
                logger.error("迁移失败")
                return False
            
            # 4. 获取迁移后的账号ID
            accounts = self.context_manager.get_all_accounts()
            if accounts:
                account_id = accounts[0]['id']
                
                # 5. 确保有完整的提示词配置
                logger.info("步骤 3: 检查并补充提示词配置")
                self.create_default_prompts_if_missing(account_id)
            
            logger.info("=" * 50)
            logger.info("配置迁移完成！")
            logger.info("=" * 50)
            
            self.print_migration_summary()
            return True
            
        except Exception as e:
            logger.error(f"迁移流程出错: {e}")
            return False
    
    def print_migration_summary(self):
        """打印迁移总结"""
        try:
            accounts = self.context_manager.get_all_accounts()
            
            print("\n" + "=" * 60)
            print("🎉 配置迁移总结")
            print("=" * 60)
            
            if accounts:
                account = accounts[0]
                print(f"✅ 账号名称: {account['account_name']}")
                print(f"✅ 用户ID: {account['user_id']}")
                print(f"✅ 卖家功能: {'启用' if account['seller_enabled'] else '禁用'}")
                print(f"✅ 买家功能: {'启用' if account['buyer_enabled'] else '禁用'}")
                
                prompts = self.context_manager.get_account_prompts(account['id'])
                print(f"✅ 提示词配置: {len(prompts)} 个")
                
                if prompts:
                    for prompt_type in prompts:
                        print(f"   - {prompt_type}: 已配置")
            
            print(f"\n📁 配置备份目录: {self.backup_dir}")
            print("\n🌐 下一步操作:")
            print("   1. 运行 python web_server.py 启动Web管理界面")
            print("   2. 访问 http://localhost:5002 进行配置管理")
            print("   3. 在Web界面中启动账号开始自动回复")
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            logger.error(f"打印迁移总结时出错: {e}")


def main():
    """主函数"""
    print("🐟多账号自动回复系统 - 配置迁移工具")
    print("=" * 60)
    
    try:
        migrator = ConfigMigrator()
        success = migrator.run_migration()
        
        if success:
            print("\n✅ 迁移成功完成！")
            return 0
        else:
            print("\n❌ 迁移失败，请查看日志了解详情")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断迁移")
        return 1
    except Exception as e:
        logger.error(f"迁移工具执行出错: {e}")
        print(f"\n❌ 迁移工具执行出错: {e}")
        return 1


if __name__ == '__main__':
    exit(main())