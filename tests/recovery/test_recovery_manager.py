"""
恢复管理器测试
"""

import pytest
import tempfile
import shutil
import time
import os
import signal
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.auto_study.recovery.recovery_manager import RecoveryManager
from src.auto_study.recovery.state_manager import StateManager, TaskStatus
from src.auto_study.recovery.persistence_manager import PersistenceManager


class TestRecoveryManager:
    """恢复管理器测试类"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def temp_db_path(self, temp_dir):
        """临时数据库路径"""
        return str(Path(temp_dir) / "test_recovery.db")
    
    @pytest.fixture
    def pid_file_path(self, temp_dir):
        """PID文件路径"""
        return str(Path(temp_dir) / "test.pid")
    
    @pytest.fixture
    def lock_file_path(self, temp_dir):
        """锁文件路径"""
        return str(Path(temp_dir) / "test.lock")
    
    @pytest.fixture
    def persistence(self, temp_db_path):
        """持久化管理器"""
        manager = PersistenceManager(temp_db_path)
        yield manager
        manager.close()
    
    @pytest.fixture
    def state_manager(self, persistence):
        """状态管理器"""
        manager = StateManager(persistence)
        yield manager
        manager.close()
    
    @pytest.fixture
    def recovery_manager(self, state_manager, persistence, pid_file_path, lock_file_path):
        """恢复管理器"""
        manager = RecoveryManager(
            state_manager=state_manager,
            persistence_manager=persistence,
            pid_file=pid_file_path,
            lock_file=lock_file_path
        )
        yield manager
        manager.shutdown()
    
    def test_initialization(self, recovery_manager, pid_file_path, lock_file_path):
        """测试初始化"""
        assert recovery_manager.pid_file == Path(pid_file_path)
        assert recovery_manager.lock_file == Path(lock_file_path)
        assert recovery_manager._current_pid == os.getpid()
        assert not recovery_manager._is_shutting_down
        assert len(recovery_manager._active_resources) == 0
    
    @patch('src.auto_study.recovery.recovery_manager.psutil.Process')
    def test_detect_crash_no_pid_file(self, mock_process, recovery_manager):
        """测试检测崩溃 - 没有PID文件"""
        # PID文件不存在的情况
        result = recovery_manager.detect_crash_on_startup()
        assert result is False
    
    @patch('src.auto_study.recovery.recovery_manager.psutil.Process')
    def test_detect_crash_process_still_running(self, mock_process, recovery_manager):
        """测试检测崩溃 - 进程仍在运行"""
        # 创建PID文件
        recovery_manager.pid_file.write_text("12345")
        
        # 模拟进程仍在运行
        mock_proc = Mock()
        mock_proc.is_running.return_value = True
        mock_process.return_value = mock_proc
        
        result = recovery_manager.detect_crash_on_startup()
        assert result is False
    
    @patch('src.auto_study.recovery.recovery_manager.psutil.Process')
    def test_detect_crash_with_lock_file(self, mock_process, recovery_manager):
        """测试检测崩溃 - 有锁文件"""
        # 创建PID文件和锁文件
        recovery_manager.pid_file.write_text("12345")
        recovery_manager.lock_file.write_text("lock_content")
        
        # 模拟进程不存在
        mock_process.side_effect = Exception("Process not found")
        
        result = recovery_manager.detect_crash_on_startup()
        assert result is True
    
    @patch('src.auto_study.recovery.recovery_manager.psutil.Process')
    def test_detect_crash_with_incomplete_tasks(self, mock_process, recovery_manager):
        """测试检测崩溃 - 有未完成任务"""
        # 创建PID文件
        recovery_manager.pid_file.write_text("12345")
        
        # 模拟进程不存在
        mock_process.side_effect = Exception("Process not found")
        
        # 创建未完成的任务
        task_id = recovery_manager.state_manager.create_task("test_task")
        recovery_manager.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        
        result = recovery_manager.detect_crash_on_startup()
        assert result is True
    
    def test_start_recovery_session(self, recovery_manager):
        """测试启动恢复会话"""
        session = recovery_manager.start_recovery_session()
        
        assert session.session_id.startswith("recovery_")
        assert recovery_manager._current_pid in session.session_id
        assert session.process_info.pid == recovery_manager._current_pid
        assert session.process_info.name == Path(os.sys.argv[0]).name
        assert session.recovery_status == "started"
        assert len(session.recovered_tasks) == 0
        assert len(session.cleaned_resources) == 0
    
    def test_cleanup_residual_resources(self, recovery_manager):
        """测试清理残留资源"""
        # 创建一些残留文件
        recovery_manager.pid_file.write_text("old_pid")
        recovery_manager.lock_file.write_text("old_lock")
        
        # 创建临时文件
        temp_file = recovery_manager.pid_file.parent / "test.tmp"
        temp_file.write_text("temp content")
        
        session = recovery_manager.start_recovery_session()
        recovery_manager._cleanup_residual_resources(session)
        
        # 验证文件已清理
        assert not recovery_manager.pid_file.exists()
        assert not recovery_manager.lock_file.exists()
        
        # 验证清理记录
        assert "pid_file" in session.cleaned_resources
        assert "lock_file" in session.cleaned_resources
    
    def test_cleanup_handlers(self, recovery_manager):
        """测试清理处理器"""
        handler_called = False
        
        def cleanup_handler():
            nonlocal handler_called
            handler_called = True
        
        recovery_manager.register_cleanup_handler(cleanup_handler)
        
        session = recovery_manager.start_recovery_session()
        recovery_manager._cleanup_residual_resources(session)
        
        assert handler_called is True
        assert "cleanup_handler" in session.cleaned_resources
    
    def test_recover_incomplete_tasks_without_handlers(self, recovery_manager):
        """测试恢复未完成任务 - 没有恢复处理器"""
        # 创建运行中的任务（有检查点）
        task_id1 = recovery_manager.state_manager.create_task("resumable_task")
        recovery_manager.state_manager.update_task_status(task_id1, TaskStatus.RUNNING)
        recovery_manager.state_manager.create_checkpoint(task_id1, "step1", 1)
        
        # 创建运行中的任务（没有检查点）
        task_id2 = recovery_manager.state_manager.create_task("non_resumable_task")
        recovery_manager.state_manager.update_task_status(task_id2, TaskStatus.RUNNING)
        
        session = recovery_manager.start_recovery_session()
        recovery_manager._recover_incomplete_tasks(session)
        
        # 验证恢复结果
        task1_state = recovery_manager.state_manager.get_task_state(task_id1)
        assert task1_state.status == TaskStatus.PAUSED  # 有检查点，标记为可恢复
        
        task2_state = recovery_manager.state_manager.get_task_state(task_id2)
        assert task2_state.status == TaskStatus.FAILED   # 没有检查点，标记为失败
        
        assert task_id1 in session.recovered_tasks
        assert task_id2 not in session.recovered_tasks
    
    def test_recover_incomplete_tasks_with_handlers(self, recovery_manager):
        """测试恢复未完成任务 - 有恢复处理器"""
        handler_called = False
        received_task_state = None
        
        def recovery_handler(task_state):
            nonlocal handler_called, received_task_state
            handler_called = True
            received_task_state = task_state
            return True  # 恢复成功
        
        recovery_manager.register_recovery_handler("handled_task", recovery_handler)
        
        # 创建任务
        task_id = recovery_manager.state_manager.create_task("handled_task")
        recovery_manager.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        recovery_manager.state_manager.create_checkpoint(task_id, "step1", 1)
        
        session = recovery_manager.start_recovery_session()
        recovery_manager._recover_incomplete_tasks(session)
        
        # 验证处理器被调用
        assert handler_called is True
        assert received_task_state is not None
        assert received_task_state.task_id == task_id
        
        # 验证任务恢复成功
        assert task_id in session.recovered_tasks
    
    def test_recover_incomplete_tasks_handler_failure(self, recovery_manager):
        """测试恢复未完成任务 - 恢复处理器失败"""
        def failing_handler(task_state):
            return False  # 恢复失败
        
        recovery_manager.register_recovery_handler("failing_task", failing_handler)
        
        # 创建任务
        task_id = recovery_manager.state_manager.create_task("failing_task")
        recovery_manager.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        
        session = recovery_manager.start_recovery_session()
        recovery_manager._recover_incomplete_tasks(session)
        
        # 验证任务标记为失败
        task_state = recovery_manager.state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.FAILED
        assert task_id not in session.recovered_tasks
    
    def test_full_crash_recovery(self, recovery_manager):
        """测试完整崩溃恢复流程"""
        # 创建一些未完成的任务
        task_id1 = recovery_manager.state_manager.create_task("task1")
        recovery_manager.state_manager.update_task_status(task_id1, TaskStatus.RUNNING)
        recovery_manager.state_manager.create_checkpoint(task_id1, "step1", 1)
        
        task_id2 = recovery_manager.state_manager.create_task("task2")
        recovery_manager.state_manager.update_task_status(task_id2, TaskStatus.PAUSED)
        recovery_manager.state_manager.create_checkpoint(task_id2, "step2", 2)
        
        # 创建残留文件
        recovery_manager.pid_file.write_text("old_pid")
        recovery_manager.lock_file.write_text("old_lock")
        
        # 执行恢复
        session = recovery_manager.recover_from_crash()
        
        # 验证恢复结果
        assert session.recovery_status == "completed"
        assert len(session.recovered_tasks) == 2
        assert len(session.cleaned_resources) >= 2  # 至少清理了pid_file和lock_file
        
        # 验证文件已清理
        assert not recovery_manager.pid_file.exists()
        assert not recovery_manager.lock_file.exists()
    
    def test_resource_lock_management(self, recovery_manager):
        """测试资源锁管理"""
        resource_name = "test_resource"
        
        # 获取锁
        success = recovery_manager.acquire_lock(resource_name)
        assert success is True
        assert resource_name in recovery_manager._active_resources
        assert recovery_manager.lock_file.exists()
        
        # 尝试再次获取相同资源的锁（应该失败）
        success = recovery_manager.acquire_lock(resource_name)
        assert success is False
        
        # 释放锁
        success = recovery_manager.release_lock(resource_name)
        assert success is True
        assert resource_name not in recovery_manager._active_resources
        assert not recovery_manager.lock_file.exists()
        
        # 释放不存在的锁
        success = recovery_manager.release_lock("nonexistent")
        assert success is False
    
    def test_resource_lock_context_manager(self, recovery_manager):
        """测试资源锁上下文管理器"""
        resource_name = "context_resource"
        
        # 使用上下文管理器
        with recovery_manager.resource_lock(resource_name):
            assert resource_name in recovery_manager._active_resources
            assert recovery_manager.lock_file.exists()
        
        # 退出上下文后锁应该被释放
        assert resource_name not in recovery_manager._active_resources
        assert not recovery_manager.lock_file.exists()
    
    def test_resource_lock_context_manager_exception(self, recovery_manager):
        """测试资源锁上下文管理器异常处理"""
        resource_name = "exception_resource"
        
        # 在上下文中抛出异常
        with pytest.raises(ValueError):
            with recovery_manager.resource_lock(resource_name):
                assert resource_name in recovery_manager._active_resources
                raise ValueError("Test exception")
        
        # 即使发生异常，锁也应该被释放
        assert resource_name not in recovery_manager._active_resources
        assert not recovery_manager.lock_file.exists()
    
    def test_resource_lock_conflict(self, recovery_manager):
        """测试资源锁冲突"""
        resource_name = "conflict_resource"
        
        # 先获取锁
        recovery_manager.acquire_lock(resource_name)
        
        # 尝试在上下文管理器中获取相同的锁（应该失败）
        with pytest.raises(RuntimeError, match="无法获取资源锁"):
            with recovery_manager.resource_lock(resource_name):
                pass
    
    def test_start_normal_operation(self, recovery_manager):
        """测试启动正常运行模式"""
        recovery_manager.start_normal_operation()
        
        # 验证PID文件已创建
        assert recovery_manager.pid_file.exists()
        pid_content = recovery_manager.pid_file.read_text().strip()
        assert int(pid_content) == recovery_manager._current_pid
        
        # 验证主程序锁已获取
        assert "main_process" in recovery_manager._active_resources
        assert recovery_manager.lock_file.exists()
    
    def test_shutdown(self, recovery_manager):
        """测试优雅关闭"""
        shutdown_handler_called = False
        
        def shutdown_handler():
            nonlocal shutdown_handler_called
            shutdown_handler_called = True
        
        recovery_manager.register_shutdown_handler(shutdown_handler)
        
        # 启动正常运行模式
        recovery_manager.start_normal_operation()
        
        # 创建运行中的任务
        task_id = recovery_manager.state_manager.create_task("running_task")
        recovery_manager.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        
        # 执行关闭
        recovery_manager.shutdown()
        
        # 验证关闭状态
        assert recovery_manager._is_shutting_down is True
        assert shutdown_handler_called is True
        
        # 验证运行中的任务被暂停
        task_state = recovery_manager.state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.PAUSED
        
        # 验证文件清理
        assert not recovery_manager.pid_file.exists()
        assert not recovery_manager.lock_file.exists()
    
    @patch('signal.signal')
    def test_signal_handling(self, mock_signal, recovery_manager):
        """测试信号处理"""
        # 验证信号处理器已注册
        assert mock_signal.call_count >= 2
        
        # 查找SIGTERM和SIGINT的调用
        signal_calls = {call[0][0]: call[0][1] for call in mock_signal.call_args_list}
        
        assert signal.SIGTERM in signal_calls
        assert signal.SIGINT in signal_calls
        
        # 测试信号处理器
        handler = signal_calls[signal.SIGTERM]
        
        # 模拟接收信号（应该调用shutdown）
        with patch.object(recovery_manager, 'shutdown') as mock_shutdown:
            handler(signal.SIGTERM, None)
            mock_shutdown.assert_called_once()
    
    def test_force_recovery(self, recovery_manager):
        """测试强制恢复"""
        # 创建可恢复的任务
        task_id1 = recovery_manager.state_manager.create_task("force_test1")
        recovery_manager.state_manager.create_checkpoint(task_id1, "step1", 1)
        recovery_manager.state_manager.update_task_status(task_id1, TaskStatus.PAUSED)
        
        task_id2 = recovery_manager.state_manager.create_task("force_test2")
        recovery_manager.state_manager.create_checkpoint(task_id2, "step2", 2)
        recovery_manager.state_manager.update_task_status(task_id2, TaskStatus.FAILED)
        
        # 创建不可恢复的任务
        task_id3 = recovery_manager.state_manager.create_task("non_resumable")
        recovery_manager.state_manager.update_task_status(task_id3, TaskStatus.FAILED)  # 没有检查点
        
        # 强制恢复所有任务
        recovered_count = recovery_manager.force_recovery()
        
        assert recovered_count == 2  # 只有有检查点的任务被恢复
        
        # 验证任务状态
        task1_state = recovery_manager.state_manager.get_task_state(task_id1)
        assert task1_state.status == TaskStatus.RUNNING
        
        task2_state = recovery_manager.state_manager.get_task_state(task_id2)
        assert task2_state.status == TaskStatus.RUNNING
        
        task3_state = recovery_manager.state_manager.get_task_state(task_id3)
        assert task3_state.status == TaskStatus.FAILED  # 保持失败状态
    
    def test_force_recovery_specific_tasks(self, recovery_manager):
        """测试强制恢复指定任务"""
        # 创建可恢复的任务
        task_id1 = recovery_manager.state_manager.create_task("specific_test1")
        recovery_manager.state_manager.create_checkpoint(task_id1, "step1", 1)
        recovery_manager.state_manager.update_task_status(task_id1, TaskStatus.PAUSED)
        
        task_id2 = recovery_manager.state_manager.create_task("specific_test2")
        recovery_manager.state_manager.create_checkpoint(task_id2, "step2", 2)
        recovery_manager.state_manager.update_task_status(task_id2, TaskStatus.PAUSED)
        
        # 只恢复第一个任务
        recovered_count = recovery_manager.force_recovery([task_id1])
        
        assert recovered_count == 1
        
        # 验证只有指定任务被恢复
        task1_state = recovery_manager.state_manager.get_task_state(task_id1)
        assert task1_state.status == TaskStatus.RUNNING
        
        task2_state = recovery_manager.state_manager.get_task_state(task_id2)
        assert task2_state.status == TaskStatus.PAUSED  # 保持暂停状态
    
    def test_recovery_statistics(self, recovery_manager):
        """测试恢复统计"""
        # 启动正常运行模式以创建一些状态
        recovery_manager.start_normal_operation()
        
        # 注册一些处理器
        recovery_manager.register_recovery_handler("test_type", lambda x: True)
        recovery_manager.register_cleanup_handler(lambda: None)
        recovery_manager.register_shutdown_handler(lambda: None)
        
        # 记录恢复事件
        recovery_manager.persistence.log_recovery_event("test_recovery", status="success")
        
        stats = recovery_manager.get_recovery_statistics()
        
        # 验证统计信息
        assert 'current_pid' in stats
        assert 'pid_file_exists' in stats
        assert 'lock_file_exists' in stats
        assert 'active_resources' in stats
        assert 'registered_recovery_handlers' in stats
        assert 'registered_cleanup_handlers' in stats
        assert 'registered_shutdown_handlers' in stats
        assert 'recovery_events_7days' in stats
        assert 'is_shutting_down' in stats
        
        assert stats['current_pid'] == recovery_manager._current_pid
        assert stats['pid_file_exists'] is True
        assert stats['lock_file_exists'] is True
        assert stats['active_resources'] == 1  # main_process锁
        assert stats['registered_recovery_handlers'] == 1
        assert stats['registered_cleanup_handlers'] == 1
        assert stats['registered_shutdown_handlers'] == 1
        assert stats['recovery_events_7days'] >= 1
        assert stats['is_shutting_down'] is False
    
    def test_concurrent_resource_access(self, recovery_manager):
        """测试并发资源访问"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                resource_name = f"concurrent_resource_{worker_id}"
                
                # 尝试获取锁
                success = recovery_manager.acquire_lock(resource_name)
                results.append(f"acquire_{worker_id}_{success}")
                
                if success:
                    time.sleep(0.01)  # 短暂持有锁
                    
                    # 释放锁
                    release_success = recovery_manager.release_lock(resource_name)
                    results.append(f"release_{worker_id}_{release_success}")
                    
            except Exception as e:
                errors.append(e)
        
        # 启动多个工作线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(errors) == 0, f"发生错误: {errors}"
        assert len(results) == 20  # 每个线程2个结果
        
        # 验证所有获取锁的操作都成功
        acquire_results = [r for r in results if r.startswith("acquire_")]
        assert all("_True" in result for result in acquire_results)
        
        # 验证所有释放锁的操作都成功
        release_results = [r for r in results if r.startswith("release_")]
        assert all("_True" in result for result in release_results)
    
    def test_multiple_shutdown_calls(self, recovery_manager):
        """测试多次调用关闭"""
        recovery_manager.start_normal_operation()
        
        # 第一次关闭
        recovery_manager.shutdown()
        assert recovery_manager._is_shutting_down is True
        
        # 第二次关闭（应该安全地忽略）
        recovery_manager.shutdown()  # 不应该抛出异常
        assert recovery_manager._is_shutting_down is True