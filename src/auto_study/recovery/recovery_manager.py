"""
恢复管理器

实现崩溃恢复功能，包括启动时检测异常退出、恢复未完成任务和清理残留资源
"""

import os
import sys
import signal
import atexit
import psutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from contextlib import contextmanager

from loguru import logger

from .state_manager import StateManager, TaskState, TaskStatus
from .persistence_manager import PersistenceManager


@dataclass
class ProcessInfo:
    """进程信息"""
    pid: int
    name: str
    cmdline: List[str]
    started_at: datetime
    working_dir: str
    status: str = "running"


@dataclass
class RecoverySession:
    """恢复会话"""
    session_id: str
    started_at: datetime
    process_info: ProcessInfo
    recovered_tasks: List[str] = field(default_factory=list)
    cleaned_resources: List[str] = field(default_factory=list)
    recovery_status: str = "started"
    error_message: Optional[str] = None


class RecoveryManager:
    """恢复管理器"""
    
    def __init__(self, 
                 state_manager: Optional[StateManager] = None,
                 persistence_manager: Optional[PersistenceManager] = None,
                 pid_file: str = "data/auto_study.pid",
                 lock_file: str = "data/auto_study.lock"):
        """
        初始化恢复管理器
        
        Args:
            state_manager: 状态管理器
            persistence_manager: 持久化管理器
            pid_file: PID文件路径
            lock_file: 锁文件路径
        """
        self.state_manager = state_manager or StateManager()
        self.persistence = persistence_manager or PersistenceManager()
        self.pid_file = Path(pid_file)
        self.lock_file = Path(lock_file)
        
        # 确保目录存在
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._current_pid = os.getpid()
        self._recovery_handlers: Dict[str, Callable] = {}
        self._cleanup_handlers: List[Callable] = []
        self._shutdown_handlers: List[Callable] = []
        self._lock = threading.RLock()
        self._is_shutting_down = False
        self._active_resources: Set[str] = set()
        
        # 注册退出处理器
        atexit.register(self._cleanup_on_exit)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        logger.info(f"恢复管理器已初始化, PID: {self._current_pid}")
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}, 开始优雅关闭")
        self.shutdown()
    
    def _cleanup_on_exit(self):
        """退出时的清理操作"""
        if not self._is_shutting_down:
            self.shutdown()
    
    def detect_crash_on_startup(self) -> bool:
        """启动时检测是否发生了崩溃"""
        try:
            # 检查PID文件是否存在
            if not self.pid_file.exists():
                logger.info("没有发现PID文件，正常启动")
                return False
            
            # 读取PID文件
            old_pid = int(self.pid_file.read_text().strip())
            logger.info(f"发现PID文件，上次进程ID: {old_pid}")
            
            # 检查进程是否还在运行
            if self._is_process_running(old_pid):
                logger.warning(f"检测到进程 {old_pid} 仍在运行，可能存在多个实例")
                return False
            
            # 检查锁文件
            if self.lock_file.exists():
                logger.warning("发现锁文件，上次程序可能异常退出")
                return True
            
            # 检查是否有未完成的任务
            incomplete_tasks = self._get_incomplete_tasks()
            if incomplete_tasks:
                logger.warning(f"发现 {len(incomplete_tasks)} 个未完成的任务，可能发生了崩溃")
                return True
            
            logger.info("未检测到崩溃，正常启动")
            return False
            
        except Exception as e:
            logger.error(f"检测崩溃时发生错误: {e}")
            return False
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否正在运行"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _get_incomplete_tasks(self) -> List[TaskState]:
        """获取未完成的任务"""
        incomplete_tasks = []
        
        for status in [TaskStatus.RUNNING, TaskStatus.PAUSED, TaskStatus.RECOVERING]:
            tasks = self.state_manager.get_tasks_by_status(status)
            incomplete_tasks.extend(tasks)
        
        return incomplete_tasks
    
    def start_recovery_session(self) -> RecoverySession:
        """启动恢复会话"""
        session_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._current_pid}"
        
        process_info = ProcessInfo(
            pid=self._current_pid,
            name=Path(sys.argv[0]).name,
            cmdline=sys.argv,
            started_at=datetime.now(),
            working_dir=os.getcwd()
        )
        
        session = RecoverySession(
            session_id=session_id,
            started_at=datetime.now(),
            process_info=process_info
        )
        
        # 记录恢复会话
        self.persistence.log_recovery_event(
            "session_started",
            details={
                'session_id': session_id,
                'pid': self._current_pid,
                'cmdline': sys.argv
            }
        )
        
        logger.info(f"恢复会话已启动: {session_id}")
        return session
    
    def recover_from_crash(self) -> RecoverySession:
        """从崩溃中恢复"""
        logger.info("开始崩溃恢复流程")
        
        session = self.start_recovery_session()
        
        try:
            # 1. 清理残留资源
            self._cleanup_residual_resources(session)
            
            # 2. 恢复未完成的任务
            self._recover_incomplete_tasks(session)
            
            # 3. 验证恢复状态
            self._validate_recovery(session)
            
            session.recovery_status = "completed"
            
            # 记录恢复完成
            self.persistence.log_recovery_event(
                "crash_recovery_completed",
                details={
                    'session_id': session.session_id,
                    'recovered_tasks': len(session.recovered_tasks),
                    'cleaned_resources': len(session.cleaned_resources)
                }
            )
            
            logger.info(f"崩溃恢复完成: 恢复了 {len(session.recovered_tasks)} 个任务")
            
        except Exception as e:
            session.recovery_status = "failed"
            session.error_message = str(e)
            
            logger.error(f"崩溃恢复失败: {e}")
            
            # 记录恢复失败
            self.persistence.log_recovery_event(
                "crash_recovery_failed",
                details={
                    'session_id': session.session_id,
                    'error': str(e)
                },
                status="failed"
            )
        
        return session
    
    def _cleanup_residual_resources(self, session: RecoverySession):
        """清理残留资源"""
        logger.info("开始清理残留资源")
        
        # 清理PID文件
        if self.pid_file.exists():
            self.pid_file.unlink()
            session.cleaned_resources.append("pid_file")
            logger.debug("已清理PID文件")
        
        # 清理锁文件
        if self.lock_file.exists():
            self.lock_file.unlink()
            session.cleaned_resources.append("lock_file")
            logger.debug("已清理锁文件")
        
        # 清理临时文件
        temp_patterns = [
            "data/*.tmp",
            "data/*.temp",
            "logs/*.tmp",
            "cache/*"
        ]
        
        for pattern in temp_patterns:
            try:
                for temp_file in Path(".").glob(pattern):
                    if temp_file.is_file():
                        temp_file.unlink()
                        session.cleaned_resources.append(str(temp_file))
                        logger.debug(f"已清理临时文件: {temp_file}")
            except Exception as e:
                logger.warning(f"清理临时文件失败 {pattern}: {e}")
        
        # 调用注册的清理处理器
        for cleanup_handler in self._cleanup_handlers:
            try:
                cleanup_handler()
                session.cleaned_resources.append(cleanup_handler.__name__)
            except Exception as e:
                logger.error(f"清理处理器执行失败 {cleanup_handler.__name__}: {e}")
        
        logger.info(f"资源清理完成，共清理 {len(session.cleaned_resources)} 项资源")
    
    def _recover_incomplete_tasks(self, session: RecoverySession):
        """恢复未完成的任务"""
        logger.info("开始恢复未完成的任务")
        
        incomplete_tasks = self._get_incomplete_tasks()
        
        for task in incomplete_tasks:
            try:
                # 根据任务状态决定恢复策略
                if task.status == TaskStatus.RUNNING:
                    # 运行中的任务标记为恢复中
                    self.state_manager.update_task_status(task.task_id, TaskStatus.RECOVERING)
                    logger.info(f"任务 {task.task_id} 状态已更新为恢复中")
                
                # 调用任务类型对应的恢复处理器
                recovery_handler = self._recovery_handlers.get(task.task_type)
                if recovery_handler:
                    success = recovery_handler(task)
                    if success:
                        session.recovered_tasks.append(task.task_id)
                        logger.info(f"任务 {task.task_id} 恢复成功")
                    else:
                        self.state_manager.fail_task(task.task_id, "恢复处理器执行失败")
                        logger.warning(f"任务 {task.task_id} 恢复失败")
                else:
                    # 没有恢复处理器，根据是否有检查点决定处理方式
                    if self.state_manager.can_resume_task(task.task_id):
                        # 有检查点，标记为可恢复
                        self.state_manager.update_task_status(task.task_id, TaskStatus.PAUSED)
                        session.recovered_tasks.append(task.task_id)
                        logger.info(f"任务 {task.task_id} 标记为可恢复")
                    else:
                        # 没有检查点，标记为失败
                        self.state_manager.fail_task(task.task_id, "崩溃时无检查点，无法恢复")
                        logger.warning(f"任务 {task.task_id} 无法恢复，已标记为失败")
                
            except Exception as e:
                logger.error(f"恢复任务 {task.task_id} 时发生错误: {e}")
                self.state_manager.fail_task(task.task_id, f"恢复时发生错误: {e}")
        
        logger.info(f"任务恢复完成，成功恢复 {len(session.recovered_tasks)} 个任务")
    
    def _validate_recovery(self, session: RecoverySession):
        """验证恢复状态"""
        logger.info("开始验证恢复状态")
        
        # 检查系统资源状态
        try:
            current_process = psutil.Process()
            memory_usage = current_process.memory_info().rss / 1024 / 1024  # MB
            cpu_usage = current_process.cpu_percent()
            
            logger.info(f"恢复后系统状态 - 内存使用: {memory_usage:.1f}MB, CPU使用: {cpu_usage:.1f}%")
        except Exception as e:
            logger.warning(f"获取系统状态失败: {e}")
        
        # 检查数据库状态
        try:
            db_stats = self.persistence.get_database_stats()
            logger.info(f"数据库状态: {db_stats}")
        except Exception as e:
            logger.warning(f"获取数据库状态失败: {e}")
        
        # 检查任务统计
        try:
            task_stats = self.state_manager.get_task_statistics()
            logger.info(f"任务统计: {task_stats}")
        except Exception as e:
            logger.warning(f"获取任务统计失败: {e}")
        
        logger.info("恢复状态验证完成")
    
    def register_recovery_handler(self, task_type: str, handler: Callable[[TaskState], bool]):
        """注册任务恢复处理器"""
        self._recovery_handlers[task_type] = handler
        logger.info(f"已注册恢复处理器: {task_type}")
    
    def register_cleanup_handler(self, handler: Callable[[], None]):
        """注册资源清理处理器"""
        self._cleanup_handlers.append(handler)
        logger.info(f"已注册清理处理器: {handler.__name__}")
    
    def register_shutdown_handler(self, handler: Callable[[], None]):
        """注册关闭处理器"""
        self._shutdown_handlers.append(handler)
        logger.info(f"已注册关闭处理器: {handler.__name__}")
    
    def acquire_lock(self, resource_name: str) -> bool:
        """获取资源锁"""
        with self._lock:
            if resource_name in self._active_resources:
                return False
            
            self._active_resources.add(resource_name)
            
            # 写入锁文件
            try:
                self.lock_file.write_text(f"{self._current_pid}\n{datetime.now().isoformat()}")
                logger.debug(f"已获取资源锁: {resource_name}")
                return True
            except Exception as e:
                logger.error(f"写入锁文件失败: {e}")
                self._active_resources.discard(resource_name)
                return False
    
    def release_lock(self, resource_name: str) -> bool:
        """释放资源锁"""
        with self._lock:
            if resource_name not in self._active_resources:
                return False
            
            self._active_resources.discard(resource_name)
            
            # 如果没有活跃资源，删除锁文件
            if not self._active_resources and self.lock_file.exists():
                try:
                    self.lock_file.unlink()
                    logger.debug(f"已释放资源锁: {resource_name}")
                except Exception as e:
                    logger.error(f"删除锁文件失败: {e}")
                    return False
            
            return True
    
    @contextmanager
    def resource_lock(self, resource_name: str):
        """资源锁上下文管理器"""
        acquired = self.acquire_lock(resource_name)
        if not acquired:
            raise RuntimeError(f"无法获取资源锁: {resource_name}")
        
        try:
            yield
        finally:
            self.release_lock(resource_name)
    
    def start_normal_operation(self):
        """启动正常运行模式"""
        try:
            # 写入PID文件
            self.pid_file.write_text(str(self._current_pid))
            
            # 获取主程序锁
            self.acquire_lock("main_process")
            
            logger.info("正常运行模式已启动")
            
        except Exception as e:
            logger.error(f"启动正常运行模式失败: {e}")
            raise
    
    def shutdown(self):
        """优雅关闭"""
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        logger.info("开始优雅关闭")
        
        try:
            # 调用关闭处理器
            for shutdown_handler in self._shutdown_handlers:
                try:
                    shutdown_handler()
                    logger.debug(f"关闭处理器执行完成: {shutdown_handler.__name__}")
                except Exception as e:
                    logger.error(f"关闭处理器执行失败 {shutdown_handler.__name__}: {e}")
            
            # 保存所有运行中的任务状态
            running_tasks = self.state_manager.get_tasks_by_status(TaskStatus.RUNNING)
            for task in running_tasks:
                self.state_manager.update_task_status(task.task_id, TaskStatus.PAUSED)
                logger.info(f"运行中任务已暂停: {task.task_id}")
            
            # 释放所有资源锁
            with self._lock:
                for resource_name in list(self._active_resources):
                    self.release_lock(resource_name)
            
            # 清理PID文件
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            # 关闭组件
            self.state_manager.close()
            self.persistence.close()
            
            logger.info("优雅关闭完成")
            
        except Exception as e:
            logger.error(f"优雅关闭时发生错误: {e}")
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        try:
            # 获取恢复历史
            recovery_history = self.persistence.get_recovery_history(hours=168)  # 7天
            
            stats = {
                'current_pid': self._current_pid,
                'pid_file_exists': self.pid_file.exists(),
                'lock_file_exists': self.lock_file.exists(),
                'active_resources': len(self._active_resources),
                'registered_recovery_handlers': len(self._recovery_handlers),
                'registered_cleanup_handlers': len(self._cleanup_handlers),
                'registered_shutdown_handlers': len(self._shutdown_handlers),
                'recovery_events_7days': len(recovery_history),
                'is_shutting_down': self._is_shutting_down
            }
            
            # 按类型统计恢复事件
            event_types = {}
            for event in recovery_history:
                event_type = event['recovery_type']
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            stats['recovery_events_by_type'] = event_types
            
            return stats
            
        except Exception as e:
            logger.error(f"获取恢复统计失败: {e}")
            return {'error': str(e)}
    
    def force_recovery(self, task_ids: Optional[List[str]] = None) -> int:
        """强制恢复指定任务"""
        logger.info(f"开始强制恢复任务: {task_ids or '全部未完成任务'}")
        
        if task_ids:
            tasks = [self.state_manager.get_task_state(task_id) 
                    for task_id in task_ids 
                    if self.state_manager.get_task_state(task_id)]
        else:
            tasks = self._get_incomplete_tasks()
        
        recovered_count = 0
        
        for task in tasks:
            if task and self.state_manager.can_resume_task(task.task_id):
                success = self.state_manager.resume_task(task.task_id)
                if success:
                    recovered_count += 1
                    logger.info(f"任务强制恢复成功: {task.task_id}")
                else:
                    logger.warning(f"任务强制恢复失败: {task.task_id}")
        
        logger.info(f"强制恢复完成，成功恢复 {recovered_count} 个任务")
        return recovered_count