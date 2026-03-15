#!/usr/bin/env python3
"""
🐟多账号自动回复系统 - 主程序

支持多账号并行运行，提供Web管理界面
"""

import asyncio
import signal
import sys
import os
from loguru import logger
from dotenv import load_dotenv
from multi_account_manager import multi_account_manager
from web_server import run_flask_app
import threading


class MultiAccountSystem:
    """多账号系统主控制器"""
    
    def __init__(self):
        self.web_thread = None
        self.shutdown_event = None
        self.loop = None
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备关闭系统...")
            if self.shutdown_event and self.loop:
                # 安全地设置shutdown事件
                self.loop.call_soon_threadsafe(self.shutdown_event.set)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start_web_server(self):
        """在独立线程中启动Web服务器"""
        def run_web():
            try:
                host = os.getenv('WEB_HOST', '0.0.0.0')
                port = int(os.getenv('WEB_PORT', '5002'))
                debug = os.getenv('WEB_DEBUG', 'False').lower() == 'true'
                
                logger.info(f"启动Web管理界面: http://{host}:{port}")
                run_flask_app(host=host, port=port, debug=debug)
                
            except Exception as e:
                logger.error(f"Web服务器启动失败: {e}")
        
        self.web_thread = threading.Thread(target=run_web, daemon=True)
        self.web_thread.start()
        logger.info("Web服务器线程已启动")
    
    async def run(self):
        """运行主系统"""
        try:
            # 获取当前事件循环
            self.loop = asyncio.get_event_loop()
            self.shutdown_event = asyncio.Event()
            
            logger.info("=" * 60)
            logger.info("🚀 🐟多账号自动回复系统启动")
            logger.info("=" * 60)
            
            # 设置信号处理
            self.setup_signal_handlers()
            
            # 启动Web服务器
            self.start_web_server()
            
            # 运行多账号管理器
            logger.info("启动多账号管理器...")
            manager_task = asyncio.create_task(multi_account_manager.run())
            
            # 等待关闭信号
            await self.shutdown_event.wait()
            
            logger.info("开始关闭系统...")
            
            # 关闭多账号管理器
            await multi_account_manager.shutdown()
            
            # 取消管理器任务
            if not manager_task.done():
                manager_task.cancel()
                try:
                    await asyncio.wait_for(manager_task, timeout=5.0)
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    logger.warning("管理器任务取消超时")
            
            logger.info("系统已安全关闭")
            
        except Exception as e:
            logger.error(f"系统运行出错: {e}")
            raise


def check_dependencies():
    """检查依赖和配置"""
    try:
        # 检查必要的目录
        directories = ['data', 'prompts', 'templates', 'static']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"创建目录: {directory}")
        
        # 检查环境文件
        if not os.path.exists('.env'):
            logger.warning("未找到 .env 配置文件")
            logger.info("请参考 .env.example 创建配置文件")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"检查依赖时出错: {e}")
        return False


def show_startup_info():
    """显示启动信息"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              🐟多账号自动回复系统 v2.0                     ║
║                Multi-Account Auto-Reply System               ║
╚══════════════════════════════════════════════════════════════╝

🌟 新特性:
  ✅ 多账号并行运行
  ✅ Web可视化管理界面  
  ✅ 账号级别的配置管理
  ✅ 实时状态监控
  ✅ 买家&卖家双模式

🌐 管理界面: http://localhost:5002
📚 使用说明: 查看 README.md

""")


async def main():
    """主函数"""
    try:
        # 加载环境变量
        load_dotenv()
        
        # 配置日志
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.remove()  # 移除默认handler
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        logger.info(f"日志级别设置为: {log_level}")
        
        # 显示启动信息
        show_startup_info()
        
        # 检查依赖
        if not check_dependencies():
            logger.error("依赖检查失败，程序退出")
            return 1
        
        # 检查是否需要配置迁移
        from migrate_config import ConfigMigrator
        migrator = ConfigMigrator()
        if migrator.check_migration_needed():
            logger.warning("检测到需要配置迁移，请先运行: python migrate_config.py")
            return 1
        
        # 创建并运行系统
        system = MultiAccountSystem()
        await system.run()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"程序启动失败: {e}")
        sys.exit(1)