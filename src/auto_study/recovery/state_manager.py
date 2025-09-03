"""
状态管理器

管理任务状态，实现断点续传功能
"""

import uuid
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field

from loguru import logger

from .persistence_manager import PersistenceManager, TaskStateData


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"       # 待执行
    RUNNING = "running"       # 执行中
    PAUSED = "paused"         # 暂停
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    RECOVERING = "recovering" # 恢复中


@dataclass
class CheckpointData:
    """检查点数据"""
    step: str                           # 当前步骤
    step_index: int                     # 步骤索引
    data: Dict[str, Any] = field(default_factory=dict)  # 步骤数据
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    checkpoint: Optional[CheckpointData] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class StateManager:
    """状态管理器"""
    
    def __init__(self, persistence_manager: Optional[PersistenceManager] = None):
        """
        初始化状态管理器
        
        Args:
            persistence_manager: 持久化管理器
        """
        self.persistence = persistence_manager or PersistenceManager()
        self._states: Dict[str, TaskState] = {}
        self._lock = threading.RLock()
        self._checkpoint_handlers: Dict[str, Callable] = {}
        self._recovery_handlers: Dict[str, Callable] = {}
        
        # 加载现有的任务状态
        self._load_existing_states()
        
        logger.info("状态管理器已初始化")
    
    def _load_existing_states(self):
        """加载现有的任务状态"""
        try:
            # 加载未完成的任务
            for status in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value, 
                          TaskStatus.PAUSED.value, TaskStatus.RECOVERING.value]:
                task_data_list = self.persistence.get_tasks_by_status(status)
                
                for task_data in task_data_list:
                    task_state = self._convert_from_data(task_data)
                    self._states[task_state.task_id] = task_state
                    
            logger.info(f"已加载 {len(self._states)} 个现有任务状态")
            
        except Exception as e:
            logger.error(f"加载现有任务状态失败: {e}")
    
    def _convert_to_data(self, task_state: TaskState) -> TaskStateData:
        """将TaskState转换为TaskStateData"""
        checkpoint_data = None
        if task_state.checkpoint:
            checkpoint_data = {
                'step': task_state.checkpoint.step,
                'step_index': task_state.checkpoint.step_index,
                'data': task_state.checkpoint.data,
                'timestamp': task_state.checkpoint.timestamp.isoformat()
            }
        
        return TaskStateData(
            task_id=task_state.task_id,
            task_type=task_state.task_type,
            status=task_state.status.value,
            progress=task_state.progress,
            data=task_state.data,
            checkpoint_data=checkpoint_data,
            retry_count=task_state.retry_count,
            last_error=task_state.last_error,
            created_at=task_state.created_at,
            updated_at=task_state.updated_at
        )
    
    def _convert_from_data(self, task_data: TaskStateData) -> TaskState:
        """将TaskStateData转换为TaskState"""
        checkpoint = None
        if task_data.checkpoint_data:
            checkpoint = CheckpointData(
                step=task_data.checkpoint_data['step'],
                step_index=task_data.checkpoint_data['step_index'],
                data=task_data.checkpoint_data.get('data', {}),
                timestamp=datetime.fromisoformat(task_data.checkpoint_data['timestamp'])
            )
        
        return TaskState(
            task_id=task_data.task_id,
            task_type=task_data.task_type,
            status=TaskStatus(task_data.status),
            progress=task_data.progress,
            data=task_data.data,
            checkpoint=checkpoint,
            retry_count=task_data.retry_count,
            last_error=task_data.last_error,
            created_at=task_data.created_at,
            updated_at=task_data.updated_at
        )
    
    def create_task(self, task_type: str, task_id: Optional[str] = None, 
                   initial_data: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新任务
        
        Args:
            task_type: 任务类型
            task_id: 任务ID，如果不提供则自动生成
            initial_data: 初始数据
            
        Returns:
            任务ID
        """
        if not task_id:
            task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        
        with self._lock:
            if task_id in self._states:
                raise ValueError(f"任务ID已存在: {task_id}")
            
            task_state = TaskState(
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.PENDING,
                data=initial_data or {}
            )
            
            self._states[task_id] = task_state
            self._save_state(task_state)
            
        logger.info(f"已创建任务: {task_id} ({task_type})")
        return task_id
    
    def get_task_state(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态"""
        with self._lock:
            return self._states.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          error_message: Optional[str] = None) -> bool:
        """更新任务状态"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            old_status = task_state.status
            task_state.status = status
            task_state.updated_at = datetime.now()
            
            if error_message:
                task_state.last_error = error_message
                
            self._save_state(task_state)
            
            logger.info(f"任务状态已更新: {task_id} {old_status.value} -> {status.value}")
            return True
    
    def update_task_progress(self, task_id: str, progress: float, 
                           data_updates: Optional[Dict[str, Any]] = None) -> bool:
        """更新任务进度"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            task_state.progress = max(0.0, min(100.0, progress))
            task_state.updated_at = datetime.now()
            
            if data_updates:
                task_state.data.update(data_updates)
            
            self._save_state(task_state)
            
            logger.debug(f"任务进度已更新: {task_id} -> {progress}%")
            return True
    
    def create_checkpoint(self, task_id: str, step: str, step_index: int,
                         checkpoint_data: Optional[Dict[str, Any]] = None) -> bool:
        """创建检查点"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            task_state.checkpoint = CheckpointData(
                step=step,
                step_index=step_index,
                data=checkpoint_data or {},
                timestamp=datetime.now()
            )
            task_state.updated_at = datetime.now()
            
            self._save_state(task_state)
            
            # 调用检查点处理器
            handler = self._checkpoint_handlers.get(task_state.task_type)
            if handler:
                try:
                    handler(task_state)
                except Exception as e:
                    logger.error(f"检查点处理器执行失败 {task_id}: {e}")
            
            logger.info(f"检查点已创建: {task_id} -> {step} (索引: {step_index})")
            return True
    
    def can_resume_task(self, task_id: str) -> bool:
        """检查任务是否可以续传"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                return False
                
            # 只有暂停的任务和有检查点的失败任务可以续传
            return (task_state.status in [TaskStatus.PAUSED, TaskStatus.FAILED] and 
                   task_state.checkpoint is not None)
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务执行"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state or not self.can_resume_task(task_id):
                logger.warning(f"任务无法恢复: {task_id}")
                return False
            
            # 将状态设置为恢复中
            task_state.status = TaskStatus.RECOVERING
            task_state.updated_at = datetime.now()
            
            self._save_state(task_state)
            
            # 调用恢复处理器
            handler = self._recovery_handlers.get(task_state.task_type)
            if handler:
                try:
                    success = handler(task_state)
                    if success:
                        task_state.status = TaskStatus.RUNNING
                        self._save_state(task_state)
                        logger.info(f"任务已恢复执行: {task_id}")
                        return True
                    else:
                        task_state.status = TaskStatus.FAILED
                        task_state.last_error = "恢复处理器执行失败"
                        self._save_state(task_state)
                        return False
                except Exception as e:
                    logger.error(f"恢复处理器执行失败 {task_id}: {e}")
                    task_state.status = TaskStatus.FAILED
                    task_state.last_error = str(e)
                    self._save_state(task_state)
                    return False
            else:
                # 没有恢复处理器，直接设置为运行状态
                task_state.status = TaskStatus.RUNNING
                self._save_state(task_state)
                logger.info(f"任务已恢复执行: {task_id}")
                return True
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                logger.warning(f"任务不存在: {task_id}")
                return False
                
            if task_state.status != TaskStatus.RUNNING:
                logger.warning(f"只能暂停运行中的任务: {task_id}")
                return False
            
            task_state.status = TaskStatus.PAUSED
            task_state.updated_at = datetime.now()
            
            self._save_state(task_state)
            
            logger.info(f"任务已暂停: {task_id}")
            return True
    
    def complete_task(self, task_id: str, final_data: Optional[Dict[str, Any]] = None) -> bool:
        """完成任务"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            task_state.status = TaskStatus.COMPLETED
            task_state.progress = 100.0
            task_state.updated_at = datetime.now()
            
            if final_data:
                task_state.data.update(final_data)
            
            self._save_state(task_state)
            
            logger.info(f"任务已完成: {task_id}")
            return True
    
    def fail_task(self, task_id: str, error_message: str) -> bool:
        """标记任务失败"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            task_state.status = TaskStatus.FAILED
            task_state.last_error = error_message
            task_state.updated_at = datetime.now()
            
            self._save_state(task_state)
            
            logger.warning(f"任务已失败: {task_id} - {error_message}")
            return True
    
    def increment_retry_count(self, task_id: str) -> int:
        """增加重试次数"""
        with self._lock:
            task_state = self._states.get(task_id)
            if not task_state:
                logger.warning(f"任务不存在: {task_id}")
                return 0
            
            task_state.retry_count += 1
            task_state.updated_at = datetime.now()
            
            self._save_state(task_state)
            
            logger.debug(f"任务重试次数已增加: {task_id} -> {task_state.retry_count}")
            return task_state.retry_count
    
    def get_tasks_by_status(self, status: TaskStatus, task_type: Optional[str] = None) -> List[TaskState]:
        """根据状态获取任务列表"""
        with self._lock:
            tasks = []
            for task_state in self._states.values():
                if task_state.status == status:
                    if not task_type or task_state.task_type == task_type:
                        tasks.append(task_state)
            
            return sorted(tasks, key=lambda x: x.updated_at, reverse=True)
    
    def get_resumable_tasks(self, task_type: Optional[str] = None) -> List[TaskState]:
        """获取可恢复的任务列表"""
        resumable_tasks = []
        
        for status in [TaskStatus.PAUSED, TaskStatus.FAILED]:
            tasks = self.get_tasks_by_status(status, task_type)
            for task in tasks:
                if self.can_resume_task(task.task_id):
                    resumable_tasks.append(task)
        
        return resumable_tasks
    
    def clean_completed_tasks(self, keep_hours: int = 24) -> int:
        """清理已完成的任务"""
        with self._lock:
            current_time = datetime.now()
            cleaned_count = 0
            
            for task_id in list(self._states.keys()):
                task_state = self._states[task_id]
                if (task_state.status == TaskStatus.COMPLETED and 
                    (current_time - task_state.updated_at).total_seconds() > keep_hours * 3600):
                    
                    # 从内存中移除
                    del self._states[task_id]
                    
                    # 从持久化存储中删除
                    self.persistence.delete_task_state(task_id)
                    
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"已清理 {cleaned_count} 个已完成的任务")
            
            return cleaned_count
    
    def register_checkpoint_handler(self, task_type: str, handler: Callable[[TaskState], None]):
        """注册检查点处理器"""
        self._checkpoint_handlers[task_type] = handler
        logger.info(f"已注册检查点处理器: {task_type}")
    
    def register_recovery_handler(self, task_type: str, handler: Callable[[TaskState], bool]):
        """注册恢复处理器"""
        self._recovery_handlers[task_type] = handler
        logger.info(f"已注册恢复处理器: {task_type}")
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        with self._lock:
            stats = {
                'total': len(self._states),
                'by_status': {},
                'by_type': {},
                'resumable_count': 0
            }
            
            for task_state in self._states.values():
                # 按状态统计
                status_key = task_state.status.value
                stats['by_status'][status_key] = stats['by_status'].get(status_key, 0) + 1
                
                # 按类型统计
                type_key = task_state.task_type
                stats['by_type'][type_key] = stats['by_type'].get(type_key, 0) + 1
                
                # 可恢复任务统计
                if self.can_resume_task(task_state.task_id):
                    stats['resumable_count'] += 1
            
            return stats
    
    def _save_state(self, task_state: TaskState):
        """保存任务状态到持久化存储"""
        try:
            task_data = self._convert_to_data(task_state)
            self.persistence.save_task_state(task_data)
        except Exception as e:
            logger.error(f"保存任务状态失败 {task_state.task_id}: {e}")
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self._lock:
            if task_id not in self._states:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            # 从内存中移除
            del self._states[task_id]
            
            # 从持久化存储中删除
            self.persistence.delete_task_state(task_id)
            
            logger.info(f"任务已删除: {task_id}")
            return True
    
    def close(self):
        """关闭状态管理器"""
        self.persistence.close()
        logger.info("状态管理器已关闭")