"""
错误恢复机制模块

提供断点续传、自动重试、崩溃恢复和状态持久化功能
"""

from .state_manager import StateManager, TaskState, TaskStatus
from .retry_manager import RetryManager, RetryStrategy, RetryableError
from .recovery_manager import RecoveryManager, RecoverySession
from .persistence_manager import PersistenceManager

__all__ = [
    'StateManager',
    'TaskState', 
    'TaskStatus',
    'RetryManager',
    'RetryStrategy',
    'RetryableError',
    'RecoveryManager',
    'RecoverySession',
    'PersistenceManager'
]