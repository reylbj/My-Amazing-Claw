import sqlite3
import os
import json
from datetime import datetime, timedelta
from loguru import logger


class ChatContextManager:
    """
    聊天上下文管理器
    
    负责存储和检索用户与商品之间的对话历史，使用SQLite数据库进行持久化存储。
    支持按会话ID检索对话历史，以及议价次数统计。
    """
    
    def __init__(self, max_history=100, db_path="data/chat_history.db"):
        """
        初始化聊天上下文管理器
        
        Args:
            max_history: 每个对话保留的最大消息数
            db_path: SQLite数据库文件路径
        """
        self.max_history = max_history
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """初始化数据库表结构"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建消息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            chat_id TEXT
        )
        ''')
        
        # 检查是否需要添加chat_id字段（兼容旧数据库）
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'chat_id' not in columns:
            cursor.execute('ALTER TABLE messages ADD COLUMN chat_id TEXT')
            logger.info("已为messages表添加chat_id字段")
        
        # 创建索引以加速查询
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_item ON messages (user_id, item_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chat_id ON messages (chat_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON messages (timestamp)
        ''')
        
        # 创建基于会话ID的议价次数表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_bargain_counts (
            chat_id TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建商品信息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            item_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            price REAL,
            description TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 新增：会话角色管理表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            chat_id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            item_id TEXT NOT NULL,
            seller_id TEXT,
            buyer_id TEXT,
            status TEXT DEFAULT 'active',
            stage TEXT DEFAULT 'inquiry',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 新增：买家决策记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS buyer_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            target_price REAL,
            max_price REAL,
            current_offer REAL,
            decision_status TEXT DEFAULT 'interested',
            decision_reason TEXT,
            confidence_score REAL DEFAULT 0.5,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 新增：商品评估记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_evaluations (
            item_id TEXT PRIMARY KEY,
            condition_score REAL DEFAULT 7.0,
            price_score REAL DEFAULT 6.0,
            seller_score REAL DEFAULT 7.0,
            interest_level INTEGER DEFAULT 3,
            market_price REAL,
            evaluation_notes TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 新增：买家消息历史表（避免重复）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS buyer_message_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            message_type TEXT NOT NULL,
            message_content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 多账号管理相关表
        # 账号管理表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT UNIQUE NOT NULL,
            cookies TEXT NOT NULL,
            user_id TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            seller_enabled BOOLEAN DEFAULT 1,
            buyer_enabled BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 提示词配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            prompt_type TEXT NOT NULL,
            prompt_content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
            UNIQUE(account_id, prompt_type)
        )
        ''')
        
        # 账号运行状态表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS account_status (
            account_id INTEGER PRIMARY KEY,
            is_running BOOLEAN DEFAULT 0,
            last_activity DATETIME,
            connection_status TEXT DEFAULT 'disconnected',
            error_count INTEGER DEFAULT 0,
            last_error TEXT,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        ''')
        
        # 为新表创建索引
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_account_name ON accounts (account_name)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_account_prompts_type ON account_prompts (account_id, prompt_type)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"聊天历史数据库初始化完成: {self.db_path}")
        

            
    def save_item_info(self, item_id, item_data):
        """
        保存商品信息到数据库
        
        Args:
            item_id: 商品ID
            item_data: 商品信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 从商品数据中提取有用信息
            price = float(item_data.get('soldPrice', 0))
            description = item_data.get('desc', '')
            
            # 将整个商品数据转换为JSON字符串
            data_json = json.dumps(item_data, ensure_ascii=False)
            
            cursor.execute(
                """
                INSERT INTO items (item_id, data, price, description, last_updated) 
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(item_id) 
                DO UPDATE SET data = ?, price = ?, description = ?, last_updated = ?
                """,
                (
                    item_id, data_json, price, description, datetime.now().isoformat(),
                    data_json, price, description, datetime.now().isoformat()
                )
            )
            
            conn.commit()
            logger.debug(f"商品信息已保存: {item_id}")
        except Exception as e:
            logger.error(f"保存商品信息时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_item_info(self, item_id):
        """
        从数据库获取商品信息
        
        Args:
            item_id: 商品ID
            
        Returns:
            dict: 商品信息字典，如果不存在返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT data FROM items WHERE item_id = ?",
                (item_id,)
            )
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None
        except Exception as e:
            logger.error(f"获取商品信息时出错: {e}")
            return None
        finally:
            conn.close()

    def add_message_by_chat(self, chat_id, user_id, item_id, role, content):
        """
        基于会话ID添加新消息到对话历史
        
        Args:
            chat_id: 会话ID
            user_id: 用户ID (用户消息存真实user_id，助手消息存卖家ID)
            item_id: 商品ID
            role: 消息角色 (user/assistant)
            content: 消息内容
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 插入新消息，使用chat_id作为额外标识
            cursor.execute(
                "INSERT INTO messages (user_id, item_id, role, content, timestamp, chat_id) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, item_id, role, content, datetime.now().isoformat(), chat_id)
            )
            
            # 检查是否需要清理旧消息（基于chat_id）
            cursor.execute(
                """
                SELECT id FROM messages 
                WHERE chat_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?, 1
                """, 
                (chat_id, self.max_history)
            )
            
            oldest_to_keep = cursor.fetchone()
            if oldest_to_keep:
                cursor.execute(
                    "DELETE FROM messages WHERE chat_id = ? AND id < ?",
                    (chat_id, oldest_to_keep[0])
                )
            
            conn.commit()
        except Exception as e:
            logger.error(f"添加消息到数据库时出错: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_context_by_chat(self, chat_id):
        """
        基于会话ID获取对话历史
        
        Args:
            chat_id: 会话ID
            
        Returns:
            list: 包含对话历史的列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT role, content FROM messages 
                WHERE chat_id = ? 
                ORDER BY timestamp ASC
                LIMIT ?
                """, 
                (chat_id, self.max_history)
            )
            
            messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
            
            # 获取议价次数并添加到上下文中
            bargain_count = self.get_bargain_count_by_chat(chat_id)
            if bargain_count > 0:
                messages.append({
                    "role": "system", 
                    "content": f"议价次数: {bargain_count}"
                })
            
        except Exception as e:
            logger.error(f"获取对话历史时出错: {e}")
            messages = []
        finally:
            conn.close()
        
        return messages

    def increment_bargain_count_by_chat(self, chat_id):
        """
        基于会话ID增加议价次数
        
        Args:
            chat_id: 会话ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 使用UPSERT语法直接基于chat_id增加议价次数
            cursor.execute(
                """
                INSERT INTO chat_bargain_counts (chat_id, count, last_updated)
                VALUES (?, 1, ?)
                ON CONFLICT(chat_id) 
                DO UPDATE SET count = count + 1, last_updated = ?
                """,
                (chat_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
            
            conn.commit()
            logger.debug(f"会话 {chat_id} 议价次数已增加")
        except Exception as e:
            logger.error(f"增加议价次数时出错: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_bargain_count_by_chat(self, chat_id):
        """
        基于会话ID获取议价次数
        
        Args:
            chat_id: 会话ID
            
        Returns:
            int: 议价次数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT count FROM chat_bargain_counts WHERE chat_id = ?",
                (chat_id,)
            )
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"获取议价次数时出错: {e}")
            return 0
        finally:
            conn.close()

    # =================== 买家AI系统相关方法 ===================
    
    def create_or_update_chat_session(self, chat_id, role, item_id, seller_id=None, buyer_id=None):
        """创建或更新会话信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO chat_sessions (chat_id, role, item_id, seller_id, buyer_id, last_activity)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id)
                DO UPDATE SET last_activity = ?, role = ?
                """,
                (chat_id, role, item_id, seller_id, buyer_id, datetime.now().isoformat(),
                 datetime.now().isoformat(), role)
            )
            conn.commit()
            logger.debug(f"会话信息已更新: {chat_id} - {role}")
        except Exception as e:
            logger.error(f"更新会话信息时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_chat_session(self, chat_id):
        """获取会话信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT role, item_id, seller_id, buyer_id, status, stage FROM chat_sessions WHERE chat_id = ?",
                (chat_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'role': result[0],
                    'item_id': result[1], 
                    'seller_id': result[2],
                    'buyer_id': result[3],
                    'status': result[4],
                    'stage': result[5]
                }
            return None
        except Exception as e:
            logger.error(f"获取会话信息时出错: {e}")
            return None
        finally:
            conn.close()
    
    def update_session_stage(self, chat_id, stage):
        """更新会话阶段"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE chat_sessions SET stage = ?, last_activity = ? WHERE chat_id = ?",
                (stage, datetime.now().isoformat(), chat_id)
            )
            conn.commit()
            logger.debug(f"会话阶段已更新: {chat_id} -> {stage}")
        except Exception as e:
            logger.error(f"更新会话阶段时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_buyer_decision(self, chat_id, target_price=None, max_price=None, current_offer=None, 
                           decision_status='interested', decision_reason='', confidence_score=0.5):
        """保存买家决策"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO buyer_decisions (chat_id, target_price, max_price, current_offer, 
                                           decision_status, decision_reason, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (chat_id, target_price, max_price, current_offer, decision_status, decision_reason, confidence_score)
            )
            conn.commit()
            logger.debug(f"买家决策已保存: {chat_id} - {decision_status}")
        except Exception as e:
            logger.error(f"保存买家决策时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_latest_buyer_decision(self, chat_id):
        """获取最新的买家决策"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT target_price, max_price, current_offer, decision_status, 
                       decision_reason, confidence_score
                FROM buyer_decisions 
                WHERE chat_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                (chat_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'target_price': result[0],
                    'max_price': result[1],
                    'current_offer': result[2],
                    'decision_status': result[3],
                    'decision_reason': result[4],
                    'confidence_score': result[5]
                }
            return None
        except Exception as e:
            logger.error(f"获取买家决策时出错: {e}")
            return None
        finally:
            conn.close()
    
    def save_product_evaluation(self, item_id, condition_score=7.0, price_score=6.0, 
                               seller_score=7.0, interest_level=3, market_price=None, notes=''):
        """保存商品评估"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO product_evaluations (item_id, condition_score, price_score, seller_score,
                                                interest_level, market_price, evaluation_notes, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id)
                DO UPDATE SET condition_score = ?, price_score = ?, seller_score = ?,
                             interest_level = ?, market_price = ?, evaluation_notes = ?, last_updated = ?
                """,
                (item_id, condition_score, price_score, seller_score, interest_level, market_price, notes,
                 datetime.now().isoformat(), condition_score, price_score, seller_score, interest_level,
                 market_price, notes, datetime.now().isoformat())
            )
            conn.commit()
            logger.debug(f"商品评估已保存: {item_id}")
        except Exception as e:
            logger.error(f"保存商品评估时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_product_evaluation(self, item_id):
        """获取商品评估"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT condition_score, price_score, seller_score, interest_level, 
                       market_price, evaluation_notes
                FROM product_evaluations 
                WHERE item_id = ?
                """,
                (item_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'condition_score': result[0],
                    'price_score': result[1],
                    'seller_score': result[2],
                    'interest_level': result[3],
                    'market_price': result[4],
                    'evaluation_notes': result[5]
                }
            return None
        except Exception as e:
            logger.error(f"获取商品评估时出错: {e}")
            return None
        finally:
            conn.close()
    
    def check_message_sent_recently(self, chat_id, message_type, hours=1):
        """检查是否最近发送过类似消息（避免重复）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 计算时间阈值
            time_threshold = datetime.now() - timedelta(hours=hours)
            
            cursor.execute(
                """
                SELECT COUNT(*) FROM buyer_message_history 
                WHERE chat_id = ? AND message_type = ? AND created_at > ?
                """,
                (chat_id, message_type, time_threshold.isoformat())
            )
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            logger.error(f"检查消息历史时出错: {e}")
            return False
        finally:
            conn.close()
    
    def save_buyer_message_history(self, chat_id, message_type, message_content):
        """保存买家消息历史（避免重复发送）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO buyer_message_history (chat_id, message_type, message_content) VALUES (?, ?, ?)",
                (chat_id, message_type, message_content)
            )
            conn.commit()
            logger.debug(f"买家消息历史已保存: {chat_id} - {message_type}")
        except Exception as e:
            logger.error(f"保存买家消息历史时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def delete_item_messages(self, item_id):
        """
        删除指定商品的所有相关记录
        
        Args:
            item_id: 商品ID
            
        Returns:
            dict: 删除结果统计
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        delete_stats = {
            'messages': 0,
            'chat_sessions': 0,
            'chat_bargain_counts': 0,
            'buyer_decisions': 0,
            'product_evaluations': 0,
            'buyer_message_history': 0,
            'items': 0
        }
        
        try:
            # 1. 先获取该商品相关的chat_id列表，用于删除相关记录
            cursor.execute("SELECT DISTINCT chat_id FROM messages WHERE item_id = ?", (item_id,))
            chat_ids = [row[0] for row in cursor.fetchall() if row[0]]
            
            # 2. 删除消息记录
            cursor.execute("SELECT COUNT(*) FROM messages WHERE item_id = ?", (item_id,))
            delete_stats['messages'] = cursor.fetchone()[0]
            cursor.execute("DELETE FROM messages WHERE item_id = ?", (item_id,))
            
            # 3. 删除会话记录
            cursor.execute("SELECT COUNT(*) FROM chat_sessions WHERE item_id = ?", (item_id,))
            delete_stats['chat_sessions'] = cursor.fetchone()[0]
            cursor.execute("DELETE FROM chat_sessions WHERE item_id = ?", (item_id,))
            
            # 4. 删除议价次数记录
            if chat_ids:
                placeholders = ','.join('?' * len(chat_ids))
                cursor.execute(f"SELECT COUNT(*) FROM chat_bargain_counts WHERE chat_id IN ({placeholders})", chat_ids)
                delete_stats['chat_bargain_counts'] = cursor.fetchone()[0]
                cursor.execute(f"DELETE FROM chat_bargain_counts WHERE chat_id IN ({placeholders})", chat_ids)
                
                # 5. 删除买家决策记录
                cursor.execute(f"SELECT COUNT(*) FROM buyer_decisions WHERE chat_id IN ({placeholders})", chat_ids)
                delete_stats['buyer_decisions'] = cursor.fetchone()[0]
                cursor.execute(f"DELETE FROM buyer_decisions WHERE chat_id IN ({placeholders})", chat_ids)
                
                # 6. 删除买家消息历史记录
                cursor.execute(f"SELECT COUNT(*) FROM buyer_message_history WHERE chat_id IN ({placeholders})", chat_ids)
                delete_stats['buyer_message_history'] = cursor.fetchone()[0]
                cursor.execute(f"DELETE FROM buyer_message_history WHERE chat_id IN ({placeholders})", chat_ids)
            
            # 7. 删除商品评估记录
            cursor.execute("SELECT COUNT(*) FROM product_evaluations WHERE item_id = ?", (item_id,))
            delete_stats['product_evaluations'] = cursor.fetchone()[0]
            cursor.execute("DELETE FROM product_evaluations WHERE item_id = ?", (item_id,))
            
            # 8. 删除商品信息记录
            cursor.execute("SELECT COUNT(*) FROM items WHERE item_id = ?", (item_id,))
            delete_stats['items'] = cursor.fetchone()[0]
            cursor.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
            
            conn.commit()
            
            total_deleted = sum(delete_stats.values())
            logger.info(f"✅ 商品 {item_id} 的所有记录已删除:")
            for table, count in delete_stats.items():
                if count > 0:
                    logger.info(f"   - {table}: {count} 条记录")
            logger.info(f"   - 总计: {total_deleted} 条记录")
            
            return delete_stats
            
        except Exception as e:
            logger.error(f"删除商品记录时出错: {e}")
            conn.rollback()
            return None
        finally:
            conn.close() 

    # =================== 多账号管理相关方法 ===================
    
    def create_account(self, account_name, cookies, user_id, seller_enabled=True, buyer_enabled=True):
        """创建新账号"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO accounts (account_name, cookies, user_id, seller_enabled, buyer_enabled, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (account_name, cookies, user_id, seller_enabled, buyer_enabled, datetime.now().isoformat())
            )
            account_id = cursor.lastrowid
            
            # 创建账号状态记录
            cursor.execute(
                "INSERT INTO account_status (account_id) VALUES (?)",
                (account_id,)
            )
            
            conn.commit()
            logger.info(f"账号已创建: {account_name} (ID: {account_id})")
            return account_id
        except sqlite3.IntegrityError as e:
            logger.error(f"创建账号失败，账号名已存在: {account_name}")
            return None
        except Exception as e:
            logger.error(f"创建账号时出错: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_account_by_id(self, account_id):
        """根据ID获取账号信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT id, account_name, cookies, user_id, status, seller_enabled, buyer_enabled, created_at
                FROM accounts WHERE id = ?
                """,
                (account_id,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'account_name': result[1],
                    'cookies': result[2],
                    'user_id': result[3],
                    'status': result[4],
                    'seller_enabled': bool(result[5]),
                    'buyer_enabled': bool(result[6]),
                    'created_at': result[7]
                }
            return None
        except Exception as e:
            logger.error(f"获取账号信息时出错: {e}")
            return None
        finally:
            conn.close()
    
    def get_all_accounts(self):
        """获取所有账号列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT a.id, a.account_name, a.user_id, a.status, a.seller_enabled, a.buyer_enabled,
                       a.cookies, s.is_running, s.connection_status, s.last_activity, s.error_count
                FROM accounts a
                LEFT JOIN account_status s ON a.id = s.account_id
                ORDER BY a.created_at DESC
                """
            )
            results = cursor.fetchall()
            accounts = []
            for row in results:
                accounts.append({
                    'id': row[0],
                    'account_name': row[1],
                    'user_id': row[2],
                    'status': row[3],
                    'seller_enabled': bool(row[4]),
                    'buyer_enabled': bool(row[5]),
                    'cookies': row[6],  # 添加cookies字段
                    'is_running': bool(row[7]) if row[7] is not None else False,
                    'connection_status': row[8] if row[8] else 'disconnected',
                    'last_activity': row[9],
                    'error_count': row[10] if row[10] else 0
                })
            return accounts
        except Exception as e:
            logger.error(f"获取账号列表时出错: {e}")
            return []
        finally:
            conn.close()
    
    def update_account(self, account_id, **kwargs):
        """更新账号信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 构建更新SQL
            update_fields = []
            values = []
            for field, value in kwargs.items():
                if field in ['account_name', 'cookies', 'user_id', 'status', 'seller_enabled', 'buyer_enabled']:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return False
            
            update_fields.append("last_updated = ?")
            values.append(datetime.now().isoformat())
            values.append(account_id)
            
            sql = f"UPDATE accounts SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, values)
            
            conn.commit()
            logger.info(f"账号已更新: ID {account_id}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"更新账号时出错: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_account(self, account_id):
        """删除账号（级联删除相关数据）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取账号名用于日志
            cursor.execute("SELECT account_name FROM accounts WHERE id = ?", (account_id,))
            result = cursor.fetchone()
            if not result:
                logger.warning(f"要删除的账号不存在: ID {account_id}")
                return False
            
            account_name = result[0]
            
            # 删除账号（外键约束会自动级联删除相关记录）
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            
            conn.commit()
            logger.info(f"账号已删除: {account_name} (ID: {account_id})")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除账号时出错: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def save_account_prompt(self, account_id, prompt_type, prompt_content):
        """保存账号的提示词配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO account_prompts (account_id, prompt_type, prompt_content, last_updated)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_id, prompt_type)
                DO UPDATE SET prompt_content = excluded.prompt_content, last_updated = excluded.last_updated
                """,
                (account_id, prompt_type, prompt_content, datetime.now().isoformat())
            )
            conn.commit()
            logger.debug(f"提示词已保存: 账号 {account_id}, 类型 {prompt_type}")
        except Exception as e:
            logger.error(f"保存提示词时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_account_prompts(self, account_id):
        """获取账号的所有提示词配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT prompt_type, prompt_content FROM account_prompts WHERE account_id = ?",
                (account_id,)
            )
            results = cursor.fetchall()
            prompts = {prompt_type: prompt_content for prompt_type, prompt_content in results}
            return prompts
        except Exception as e:
            logger.error(f"获取提示词时出错: {e}")
            return {}
        finally:
            conn.close()
    
    def update_account_status(self, account_id, is_running=None, connection_status=None, last_error=None):
        """更新账号运行状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 首先检查记录是否存在
            cursor.execute("SELECT account_id FROM account_status WHERE account_id = ?", (account_id,))
            exists = cursor.fetchone() is not None
            
            current_time = datetime.now().isoformat()
            
            if exists:
                # 更新现有记录
                update_parts = ["last_activity = ?"]
                values = [current_time]
                
                if is_running is not None:
                    update_parts.append("is_running = ?")
                    values.append(is_running)
                
                if connection_status is not None:
                    update_parts.append("connection_status = ?")
                    values.append(connection_status)
                
                if last_error is not None:
                    update_parts.append("last_error = ?")
                    update_parts.append("error_count = error_count + 1")
                    values.append(last_error)
                
                values.append(account_id)  # 用于WHERE子句
                
                sql = f"UPDATE account_status SET {', '.join(update_parts)} WHERE account_id = ?"
                cursor.execute(sql, values)
            else:
                # 插入新记录
                sql = """
                INSERT INTO account_status (account_id, is_running, connection_status, last_error, last_activity, error_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                values = [
                    account_id,
                    is_running if is_running is not None else False,
                    connection_status if connection_status is not None else 'inactive',
                    last_error if last_error is not None else None,
                    current_time,
                    1 if last_error is not None else 0
                ]
                cursor.execute(sql, values)
            
            conn.commit()
        except Exception as e:
            logger.error(f"更新账号状态时出错: {e}")
            logger.error(f"参数: account_id={account_id}, is_running={is_running}, connection_status={connection_status}, last_error={last_error}")
            conn.rollback()
        finally:
            conn.close() 