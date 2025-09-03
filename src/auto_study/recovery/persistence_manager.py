"""
状态持久化管理器

使用SQLite实现任务状态、用户会话和配置的持久化存储
"""

import sqlite3
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
from dataclasses import dataclass, asdict

from loguru import logger


@dataclass
class TaskStateData:
    """任务状态数据结构"""
    task_id: str
    task_type: str
    status: str
    progress: float
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    checkpoint_data: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    last_error: Optional[str] = None


@dataclass
class SessionData:
    """会话数据结构"""
    session_id: str
    user_id: str
    session_type: str
    status: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class ConfigData:
    """配置数据结构"""
    key: str
    value: str
    category: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None


class PersistenceManager:
    """状态持久化管理器"""
    
    def __init__(self, db_path: str = "data/auto_study.db", max_connections: int = 10):
        """
        初始化持久化管理器
        
        Args:
            db_path: SQLite数据库文件路径
            max_connections: 最大连接数
        """
        self.db_path = Path(db_path)
        self.max_connections = max_connections
        self._local = threading.local()
        self._lock = threading.Lock()
        
        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        logger.info(f"持久化管理器已初始化，数据库路径: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=30,
                isolation_level=None  # 自动提交模式
            )
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            self._local.connection.row_factory = sqlite3.Row
        
        return self._local.connection
    
    @contextmanager
    def _transaction(self):
        """事务上下文管理器"""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    
    def _init_database(self):
        """初始化数据库表结构"""
        with self._transaction() as conn:
            # 任务状态表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_states (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL DEFAULT 0,
                    data TEXT,
                    checkpoint_data TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 会话数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            # 配置数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 恢复日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recovery_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recovery_type TEXT NOT NULL,
                    task_id TEXT,
                    session_id TEXT,
                    status TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_states_type_status 
                ON task_states(task_type, status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_type 
                ON sessions(user_id, session_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_expires 
                ON sessions(expires_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recovery_logs_type_created 
                ON recovery_logs(recovery_type, created_at)
            """)
    
    # 任务状态管理
    def save_task_state(self, task_state: TaskStateData) -> bool:
        """保存任务状态"""
        try:
            with self._transaction() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO task_states 
                    (task_id, task_type, status, progress, data, checkpoint_data, 
                     retry_count, last_error, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_state.task_id,
                    task_state.task_type,
                    task_state.status,
                    task_state.progress,
                    json.dumps(task_state.data) if task_state.data else None,
                    json.dumps(task_state.checkpoint_data) if task_state.checkpoint_data else None,
                    task_state.retry_count,
                    task_state.last_error,
                    task_state.created_at.isoformat(),
                    task_state.updated_at.isoformat()
                ))
            
            logger.debug(f"任务状态已保存: {task_state.task_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存任务状态失败: {e}")
            return False
    
    def load_task_state(self, task_id: str) -> Optional[TaskStateData]:
        """加载任务状态"""
        try:
            conn = self._get_connection()
            row = conn.execute("""
                SELECT * FROM task_states WHERE task_id = ?
            """, (task_id,)).fetchone()
            
            if not row:
                return None
            
            return TaskStateData(
                task_id=row['task_id'],
                task_type=row['task_type'],
                status=row['status'],
                progress=row['progress'],
                data=json.loads(row['data']) if row['data'] else {},
                checkpoint_data=json.loads(row['checkpoint_data']) if row['checkpoint_data'] else None,
                retry_count=row['retry_count'],
                last_error=row['last_error'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
            
        except Exception as e:
            logger.error(f"加载任务状态失败 {task_id}: {e}")
            return None
    
    def get_tasks_by_status(self, status: str, task_type: Optional[str] = None) -> List[TaskStateData]:
        """根据状态获取任务列表"""
        try:
            conn = self._get_connection()
            
            if task_type:
                rows = conn.execute("""
                    SELECT * FROM task_states 
                    WHERE status = ? AND task_type = ?
                    ORDER BY updated_at DESC
                """, (status, task_type)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM task_states 
                    WHERE status = ?
                    ORDER BY updated_at DESC
                """, (status,)).fetchall()
            
            return [
                TaskStateData(
                    task_id=row['task_id'],
                    task_type=row['task_type'],
                    status=row['status'],
                    progress=row['progress'],
                    data=json.loads(row['data']) if row['data'] else {},
                    checkpoint_data=json.loads(row['checkpoint_data']) if row['checkpoint_data'] else None,
                    retry_count=row['retry_count'],
                    last_error=row['last_error'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ) for row in rows
            ]
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            return []
    
    def delete_task_state(self, task_id: str) -> bool:
        """删除任务状态"""
        try:
            with self._transaction() as conn:
                conn.execute("DELETE FROM task_states WHERE task_id = ?", (task_id,))
            
            logger.debug(f"任务状态已删除: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除任务状态失败 {task_id}: {e}")
            return False
    
    # 会话数据管理
    def save_session(self, session: SessionData) -> bool:
        """保存会话数据"""
        try:
            with self._transaction() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO sessions 
                    (session_id, user_id, session_type, status, data, 
                     created_at, updated_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id,
                    session.user_id,
                    session.session_type,
                    session.status,
                    json.dumps(session.data) if session.data else None,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    session.expires_at.isoformat() if session.expires_at else None
                ))
            
            logger.debug(f"会话数据已保存: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存会话数据失败: {e}")
            return False
    
    def load_session(self, session_id: str) -> Optional[SessionData]:
        """加载会话数据"""
        try:
            conn = self._get_connection()
            row = conn.execute("""
                SELECT * FROM sessions WHERE session_id = ?
            """, (session_id,)).fetchone()
            
            if not row:
                return None
            
            return SessionData(
                session_id=row['session_id'],
                user_id=row['user_id'],
                session_type=row['session_type'],
                status=row['status'],
                data=json.loads(row['data']) if row['data'] else {},
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None
            )
            
        except Exception as e:
            logger.error(f"加载会话数据失败 {session_id}: {e}")
            return None
    
    def get_active_sessions(self, user_id: Optional[str] = None) -> List[SessionData]:
        """获取活跃会话列表"""
        try:
            conn = self._get_connection()
            current_time = datetime.now()
            
            if user_id:
                rows = conn.execute("""
                    SELECT * FROM sessions 
                    WHERE user_id = ? AND status = 'active'
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY updated_at DESC
                """, (user_id, current_time.isoformat())).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM sessions 
                    WHERE status = 'active'
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY updated_at DESC
                """, (current_time.isoformat(),)).fetchall()
            
            return [
                SessionData(
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    session_type=row['session_type'],
                    status=row['status'],
                    data=json.loads(row['data']) if row['data'] else {},
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None
                ) for row in rows
            ]
            
        except Exception as e:
            logger.error(f"获取活跃会话失败: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        try:
            with self._transaction() as conn:
                current_time = datetime.now()
                cursor = conn.execute("""
                    DELETE FROM sessions 
                    WHERE expires_at IS NOT NULL AND expires_at <= ?
                """, (current_time.isoformat(),))
                
                deleted_count = cursor.rowcount
                logger.info(f"已清理 {deleted_count} 个过期会话")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0
    
    # 配置数据管理
    def save_config(self, config: ConfigData) -> bool:
        """保存配置数据"""
        try:
            with self._transaction() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO configurations 
                    (key, value, category, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    config.key,
                    config.value,
                    config.category,
                    config.description,
                    config.created_at.isoformat(),
                    config.updated_at.isoformat()
                ))
            
            logger.debug(f"配置已保存: {config.key}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def load_config(self, key: str) -> Optional[ConfigData]:
        """加载配置数据"""
        try:
            conn = self._get_connection()
            row = conn.execute("""
                SELECT * FROM configurations WHERE key = ?
            """, (key,)).fetchone()
            
            if not row:
                return None
            
            return ConfigData(
                key=row['key'],
                value=row['value'],
                category=row['category'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
            
        except Exception as e:
            logger.error(f"加载配置失败 {key}: {e}")
            return None
    
    def get_configs_by_category(self, category: str) -> Dict[str, str]:
        """根据分类获取配置"""
        try:
            conn = self._get_connection()
            rows = conn.execute("""
                SELECT key, value FROM configurations WHERE category = ?
                ORDER BY key
            """, (category,)).fetchall()
            
            return {row['key']: row['value'] for row in rows}
            
        except Exception as e:
            logger.error(f"获取配置分类失败 {category}: {e}")
            return {}
    
    # 恢复日志管理
    def log_recovery_event(self, recovery_type: str, task_id: Optional[str] = None, 
                          session_id: Optional[str] = None, status: str = "success", 
                          details: Optional[Dict[str, Any]] = None) -> bool:
        """记录恢复事件"""
        try:
            with self._transaction() as conn:
                conn.execute("""
                    INSERT INTO recovery_logs 
                    (recovery_type, task_id, session_id, status, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    recovery_type,
                    task_id,
                    session_id,
                    status,
                    json.dumps(details) if details else None,
                    datetime.now().isoformat()
                ))
            
            logger.debug(f"恢复事件已记录: {recovery_type}")
            return True
            
        except Exception as e:
            logger.error(f"记录恢复事件失败: {e}")
            return False
    
    def get_recovery_history(self, hours: int = 24, recovery_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取恢复历史"""
        try:
            conn = self._get_connection()
            since_time = datetime.now() - timedelta(hours=hours)
            
            if recovery_type:
                rows = conn.execute("""
                    SELECT * FROM recovery_logs 
                    WHERE recovery_type = ? AND created_at >= ?
                    ORDER BY created_at DESC
                """, (recovery_type, since_time.isoformat())).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM recovery_logs 
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                """, (since_time.isoformat(),)).fetchall()
            
            return [
                {
                    'id': row['id'],
                    'recovery_type': row['recovery_type'],
                    'task_id': row['task_id'],
                    'session_id': row['session_id'],
                    'status': row['status'],
                    'details': json.loads(row['details']) if row['details'] else None,
                    'created_at': row['created_at']
                } for row in rows
            ]
            
        except Exception as e:
            logger.error(f"获取恢复历史失败: {e}")
            return []
    
    # 数据库维护
    def vacuum_database(self) -> bool:
        """压缩数据库"""
        try:
            conn = self._get_connection()
            conn.execute("VACUUM")
            logger.info("数据库已压缩")
            return True
            
        except Exception as e:
            logger.error(f"数据库压缩失败: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            conn = self._get_connection()
            
            stats = {
                'db_size': self.db_path.stat().st_size if self.db_path.exists() else 0,
                'task_count': conn.execute("SELECT COUNT(*) FROM task_states").fetchone()[0],
                'session_count': conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                'config_count': conn.execute("SELECT COUNT(*) FROM configurations").fetchone()[0],
                'recovery_log_count': conn.execute("SELECT COUNT(*) FROM recovery_logs").fetchone()[0]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            import shutil
            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 使用文件复制进行备份
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"数据库已备份到: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
        
        logger.info("持久化管理器已关闭")