import asyncio
import os
from typing import Dict, List, Optional
from loguru import logger
from context_manager import ChatContextManager
from account_manager import AccountManager


class MultiAccountManager:
    """多账号管理器，负责协调和管理多个闲鱼账号"""
    
    def __init__(self):
        self.context_manager = ChatContextManager()
        self.account_managers: Dict[int, AccountManager] = {}  # account_id -> AccountManager
        self.running_tasks: Dict[int, asyncio.Task] = {}  # account_id -> Task
        self.account_retry_counts: Dict[int, int] = {}  # account_id -> retry_count
        self.account_last_failure: Dict[int, float] = {}  # account_id -> last_failure_time
        self.is_running = False
        
        logger.info("多账号管理器初始化完成")
    
    async def initialize(self):
        """初始化多账号系统，加载所有启用的账号"""
        try:
            accounts = self.context_manager.get_all_accounts()
            active_accounts = [acc for acc in accounts if acc['status'] == 'active']
            
            logger.info(f"发现 {len(active_accounts)} 个启用的账号")
            
            for account_config in active_accounts:
                await self.add_account(account_config)
            
            logger.info("多账号系统初始化完成")
            
        except Exception as e:
            logger.error(f"初始化多账号系统时出错: {e}")
            raise
    
    async def add_account(self, account_config: Dict) -> bool:
        """
        添加一个账号到管理器
        
        Args:
            account_config: 账号配置信息
            
        Returns:
            bool: 是否添加成功
        """
        try:
            account_id = account_config['id']
            
            if account_id in self.account_managers:
                logger.warning(f"账号 {account_config['account_name']} 已存在，跳过添加")
                return False
            
            # 确保account_config包含所需的字段
            if 'cookies' not in account_config:
                account_config['cookies'] = account_config.get('cookies', '')
            
            # 创建账号管理器
            account_manager = AccountManager(account_config)
            
            # 加载账号的提示词配置
            prompts = self.context_manager.get_account_prompts(account_id)
            if prompts:
                account_manager.initialize_ai_agents(prompts)
                logger.info(f"账号 {account_config['account_name']} 已加载自定义提示词")
            else:
                # 使用默认提示词
                account_manager.initialize_ai_agents({})
                logger.info(f"账号 {account_config['account_name']} 使用默认提示词")
            
            self.account_managers[account_id] = account_manager
            logger.info(f"账号 {account_config['account_name']} 已添加到管理器")
            
            return True
            
        except Exception as e:
            logger.error(f"添加账号时出错: {e}")
            return False
    
    async def remove_account(self, account_id: int) -> bool:
        """
        从管理器中移除账号
        
        Args:
            account_id: 账号ID
            
        Returns:
            bool: 是否移除成功
        """
        try:
            if account_id not in self.account_managers:
                logger.warning(f"要移除的账号不存在: ID {account_id}")
                return False
            
            # 先停止账号
            await self.stop_account(account_id)
            
            # 移除账号管理器
            account_manager = self.account_managers.pop(account_id)
            logger.info(f"账号 {account_manager.account_name} 已从管理器中移除")
            
            return True
            
        except Exception as e:
            logger.error(f"移除账号时出错: {e}")
            return False
    
    async def start_account(self, account_id: int) -> bool:
        """
        启动指定账号
        
        Args:
            account_id: 账号ID
            
        Returns:
            bool: 是否启动成功
        """
        try:
            if account_id not in self.account_managers:
                logger.error(f"账号不存在: ID {account_id}")
                return False
            
            if account_id in self.running_tasks:
                logger.warning(f"账号 ID {account_id} 已经在运行中")
                return False
            
            account_manager = self.account_managers[account_id]
            
            # 创建并启动异步任务
            task = asyncio.create_task(account_manager.start())
            self.running_tasks[account_id] = task
            
            logger.info(f"账号 {account_manager.account_name} 启动任务已创建")
            
            # 如果启动成功，重置重试计数
            def reset_retry_count_on_success():
                # 等待一段时间后检查是否成功运行，如果是则重置计数
                async def check_and_reset():
                    await asyncio.sleep(60)  # 等待60秒
                    if account_id in self.running_tasks and not self.running_tasks[account_id].done():
                        # 任务仍在运行，说明连接成功
                        if account_id in self.account_retry_counts:
                            del self.account_retry_counts[account_id]
                        if account_id in self.account_last_failure:
                            del self.account_last_failure[account_id]
                        logger.info(f"账号 {account_manager.account_name} 连接稳定，重置重试计数")
                
                asyncio.create_task(check_and_reset())
            
            reset_retry_count_on_success()
            return True
            
        except Exception as e:
            logger.error(f"启动账号时出错: {e}")
            return False
    
    async def stop_account(self, account_id: int) -> bool:
        """
        停止指定账号
        
        Args:
            account_id: 账号ID
            
        Returns:
            bool: 是否停止成功
        """
        try:
            if account_id not in self.account_managers:
                logger.error(f"账号不存在: ID {account_id}")
                return False
            
            account_manager = self.account_managers[account_id]
            
            # 先取消并移除任务
            if account_id in self.running_tasks:
                task = self.running_tasks.pop(account_id)
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=5.0)
                    except asyncio.CancelledError:
                        pass
                    except asyncio.TimeoutError:
                        logger.warning(f"账号 {account_manager.account_name} 任务取消超时")
                    except Exception as e:
                        logger.debug(f"取消任务时的异常: {e}")
            
            # 然后停止账号管理器（这会处理WebSocket连接的清理）
            try:
                await account_manager.stop()
            except Exception as e:
                logger.debug(f"停止账号管理器时的异常: {e}")
            
            logger.info(f"账号 {account_manager.account_name} 已停止")
            return True
            
        except Exception as e:
            logger.error(f"停止账号时出错: {e}")
            return False
    
    async def start_all_accounts(self):
        """启动所有启用的账号"""
        try:
            accounts = self.context_manager.get_all_accounts()
            active_accounts = [acc for acc in accounts if acc['status'] == 'active']
            
            for account in active_accounts:
                if account['id'] not in self.running_tasks:
                    await self.start_account(account['id'])
            
            logger.info(f"已启动 {len(active_accounts)} 个账号")
            
        except Exception as e:
            logger.error(f"启动所有账号时出错: {e}")
    
    async def stop_all_accounts(self):
        """停止所有运行中的账号"""
        try:
            account_ids = list(self.running_tasks.keys())
            
            for account_id in account_ids:
                await self.stop_account(account_id)
            
            logger.info(f"已停止 {len(account_ids)} 个账号")
            
        except Exception as e:
            logger.error(f"停止所有账号时出错: {e}")
    
    async def reload_account_config(self, account_id: int) -> bool:
        """
        重新加载账号配置（包括提示词）
        
        Args:
            account_id: 账号ID
            
        Returns:
            bool: 是否重新加载成功
        """
        try:
            if account_id not in self.account_managers:
                logger.error(f"账号不存在: ID {account_id}")
                return False
            
            account_manager = self.account_managers[account_id]
            
            # 重新加载提示词
            prompts = self.context_manager.get_account_prompts(account_id)
            account_manager.initialize_ai_agents(prompts)
            
            logger.info(f"账号 {account_manager.account_name} 配置已重新加载")
            return True
            
        except Exception as e:
            logger.error(f"重新加载账号配置时出错: {e}")
            return False
    
    def get_account_status(self, account_id: int) -> Optional[Dict]:
        """
        获取指定账号的状态
        
        Args:
            account_id: 账号ID
            
        Returns:
            Dict: 账号状态信息
        """
        try:
            if account_id not in self.account_managers:
                return None
            
            account_manager = self.account_managers[account_id]
            status = account_manager.get_status()
            
            # 添加任务状态
            status['has_task'] = account_id in self.running_tasks
            if account_id in self.running_tasks:
                task = self.running_tasks[account_id]
                status['task_done'] = task.done()
                if task.done():
                    try:
                        if task.exception():
                            status['task_exception'] = str(task.exception())
                    except asyncio.CancelledError:
                        status['task_cancelled'] = True
                    except Exception as e:
                        status['task_exception'] = str(e)
            
            return status
            
        except Exception as e:
            logger.error(f"获取账号状态时出错: {e}")
            return None
    
    def get_all_account_status(self) -> List[Dict]:
        """获取所有账号的状态"""
        try:
            statuses = []
            
            for account_id in self.account_managers:
                status = self.get_account_status(account_id)
                if status:
                    statuses.append(status)
            
            return statuses
            
        except Exception as e:
            logger.error(f"获取所有账号状态时出错: {e}")
            return []
    
    async def run(self):
        """运行多账号管理器的主循环"""
        try:
            self.is_running = True
            logger.info("多账号管理器开始运行")
            
            # 初始化账号管理器（不自动启动账号，等用户手动启动）
            await self.initialize()
            logger.info("多账号管理器初始化完成，等待用户启动账号")
            
            # 主监控循环
            while self.is_running:
                try:
                    # 检查任务状态，重启失败的任务
                    await self._monitor_tasks()
                    
                    # 等待一段时间再次检查
                    await asyncio.sleep(30)  # 每30秒检查一次
                    
                except Exception as e:
                    logger.error(f"监控循环中发生错误: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"多账号管理器运行出错: {e}")
        finally:
            await self.stop_all_accounts()
            self.is_running = False
            logger.info("多账号管理器已停止")
    
    async def _monitor_tasks(self):
        """监控所有账号任务，重启失败的任务"""
        try:
            failed_tasks = []
            
            for account_id, task in self.running_tasks.items():
                if task.done():
                    if task.exception():
                        logger.error(f"账号 ID {account_id} 任务异常结束: {task.exception()}")
                        # 更新账号状态
                        self.context_manager.update_account_status(
                            account_id,
                            is_running=False,
                            connection_status='error',
                            last_error=str(task.exception())
                        )
                    else:
                        logger.info(f"账号 ID {account_id} 任务正常结束")
                    
                    failed_tasks.append(account_id)
            
            # 清理失败的任务
            for account_id in failed_tasks:
                task = self.running_tasks.pop(account_id, None)
                if task and not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=2.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                        pass  # 忽略清理过程中的异常
            
            # 重启失败的账号（如果账号仍然是启用状态）
            if failed_tasks:
                import time
                accounts = self.context_manager.get_all_accounts()
                for account in accounts:
                    if (account['id'] in failed_tasks and 
                        account['status'] == 'active' and
                        account['id'] in self.account_managers):
                        
                        account_id = account['id']
                        current_time = time.time()
                        
                        # 增加重试计数
                        self.account_retry_counts[account_id] = self.account_retry_counts.get(account_id, 0) + 1
                        self.account_last_failure[account_id] = current_time
                        
                        retry_count = self.account_retry_counts[account_id]
                        
                        # 如果重试次数超过5次，延长等待时间
                        if retry_count > 5:
                            # 指数退避：等待时间 = min(2^(retry_count-5) * 60, 1800)，最长30分钟
                            wait_time = min(2 ** (retry_count - 5) * 60, 1800)
                            logger.info(f"账号 {account['account_name']} 重试次数过多({retry_count}次)，等待 {wait_time//60} 分钟后重试")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.info(f"尝试重启失败的账号: {account['account_name']} (第{retry_count}次重试)")
                            await asyncio.sleep(5)  # 等待5秒再重启
                        
                        await self.start_account(account_id)
                        
        except Exception as e:
            logger.error(f"监控任务时出错: {e}")
    
    async def shutdown(self):
        """优雅关闭多账号管理器"""
        logger.info("正在关闭多账号管理器...")
        self.is_running = False
        
        # 等待所有运行中的任务完成或超时
        if self.running_tasks:
            logger.info(f"等待 {len(self.running_tasks)} 个任务完成...")
            tasks = list(self.running_tasks.values())
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("任务完成超时，强制取消剩余任务")
                for task in tasks:
                    if not task.done():
                        task.cancel()
                # 再给2秒时间处理取消
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=2.0)
                except Exception:
                    pass  # 忽略取消过程中的异常
            except Exception as e:
                logger.error(f"关闭任务时发生异常: {e}")
        
        await self.stop_all_accounts()
        self.running_tasks.clear()
        self.account_managers.clear()
        logger.info("多账号管理器已关闭")


# 全局多账号管理器实例
multi_account_manager = MultiAccountManager()