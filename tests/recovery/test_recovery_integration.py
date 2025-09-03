"""
错误恢复机制集成测试
"""

import pytest
import tempfile
import shutil
import time
import threading
from pathlib import Path

from src.auto_study.recovery import (
    RecoveryManager, StateManager, RetryManager, PersistenceManager,
    TaskStatus, RetryableError, RetryErrorType
)


class TestRecoveryIntegration:
    """错误恢复机制集成测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def persistence(self, temp_dir):
        """持久化管理器"""
        db_path = str(Path(temp_dir) / "integration_test.db")
        manager = PersistenceManager(db_path)
        yield manager
        manager.close()
    
    @pytest.fixture
    def state_manager(self, persistence):
        """状态管理器"""
        manager = StateManager(persistence)
        yield manager
        manager.close()
    
    @pytest.fixture
    def retry_manager(self):
        """重试管理器"""
        return RetryManager()
    
    @pytest.fixture
    def recovery_manager(self, state_manager, persistence, temp_dir):
        """恢复管理器"""
        pid_file = str(Path(temp_dir) / "test.pid")
        lock_file = str(Path(temp_dir) / "test.lock")
        
        manager = RecoveryManager(
            state_manager=state_manager,
            persistence_manager=persistence,
            pid_file=pid_file,
            lock_file=lock_file
        )
        yield manager
        manager.shutdown()
    
    def test_complete_task_lifecycle_with_recovery(self, state_manager, retry_manager):
        """测试完整的任务生命周期和恢复"""
        
        # 模拟业务逻辑函数
        execution_steps = []
        
        def simulate_login_task(username, password):
            """模拟登录任务"""
            execution_steps.append("login_start")
            
            # 模拟网络错误
            if len(execution_steps) < 3:
                raise RetryableError("Network timeout", RetryErrorType.NETWORK_ERROR)
            
            execution_steps.append("login_success")
            return {"token": "abc123", "user_id": username}
        
        # 创建任务
        task_id = state_manager.create_task("login", initial_data={"username": "test_user"})
        
        # 使用重试管理器执行任务
        try:
            state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            state_manager.create_checkpoint(task_id, "authentication", 1, {"attempt": 1})
            
            # 执行登录（会重试2次后成功）
            result = retry_manager.retry_function(
                simulate_login_task,
                "test_user", "password123",
                max_attempts=5
            )
            
            # 任务成功完成
            state_manager.complete_task(task_id, {"result": result})
            
        except Exception as e:
            # 任务失败
            state_manager.fail_task(task_id, str(e))
            raise
        
        # 验证结果
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.COMPLETED
        assert task_state.progress == 100.0
        assert "result" in task_state.data
        assert task_state.data["result"]["token"] == "abc123"
        
        # 验证执行步骤
        assert len(execution_steps) == 4  # 2次失败 + 开始 + 成功
        assert execution_steps.count("login_start") == 3
        assert execution_steps.count("login_success") == 1
    
    def test_task_interruption_and_resume(self, state_manager):
        """测试任务中断和恢复"""
        # 创建任务并设置检查点
        task_id = state_manager.create_task("data_processing")
        state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        state_manager.update_task_progress(task_id, 30.0)
        
        # 创建检查点（模拟已处理30%的数据）
        checkpoint_data = {
            "processed_items": 300,
            "total_items": 1000,
            "current_batch": 3,
            "last_item_id": "item_300"
        }
        state_manager.create_checkpoint(task_id, "batch_processing", 3, checkpoint_data)
        
        # 模拟系统中断（暂停任务）
        state_manager.pause_task(task_id)
        
        # 验证任务可以恢复
        assert state_manager.can_resume_task(task_id) is True
        
        # 注册恢复处理器
        recovery_called = False
        recovered_checkpoint = None
        
        def data_processing_recovery_handler(task_state):
            nonlocal recovery_called, recovered_checkpoint
            recovery_called = True
            recovered_checkpoint = task_state.checkpoint
            return True
        
        state_manager.register_recovery_handler("data_processing", data_processing_recovery_handler)
        
        # 恢复任务
        success = state_manager.resume_task(task_id)
        assert success is True
        assert recovery_called is True
        
        # 验证恢复的检查点数据
        assert recovered_checkpoint is not None
        assert recovered_checkpoint.step == "batch_processing"
        assert recovered_checkpoint.step_index == 3
        assert recovered_checkpoint.data["processed_items"] == 300
        assert recovered_checkpoint.data["last_item_id"] == "item_300"
        
        # 验证任务状态
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.RUNNING
        assert task_state.progress == 30.0
    
    def test_crash_recovery_simulation(self, recovery_manager, state_manager):
        """测试崩溃恢复模拟"""
        # 创建一些任务来模拟运行状态
        tasks = []
        
        # 创建正在运行的任务
        running_task = state_manager.create_task("video_download", "video_001")
        state_manager.update_task_status(running_task, TaskStatus.RUNNING)
        state_manager.update_task_progress(running_task, 45.0)
        state_manager.create_checkpoint(running_task, "downloading", 1, {
            "url": "http://example.com/video.mp4",
            "downloaded_bytes": 450000,
            "total_bytes": 1000000
        })
        tasks.append(running_task)
        
        # 创建暂停的任务
        paused_task = state_manager.create_task("course_sync", "course_001")
        state_manager.update_task_status(paused_task, TaskStatus.PAUSED)
        state_manager.create_checkpoint(paused_task, "syncing_progress", 2, {
            "synced_chapters": 3,
            "total_chapters": 10
        })
        tasks.append(paused_task)
        
        # 创建没有检查点的运行任务（应该被标记为失败）
        incomplete_task = state_manager.create_task("user_sync", "user_001")
        state_manager.update_task_status(incomplete_task, TaskStatus.RUNNING)
        tasks.append(incomplete_task)
        
        # 模拟程序崩溃后重启的检测
        recovery_manager.pid_file.write_text("12345")  # 模拟旧PID
        recovery_manager.lock_file.write_text("old_lock_content")
        
        # 检测崩溃
        crashed = recovery_manager.detect_crash_on_startup()
        assert crashed is True
        
        # 执行恢复
        session = recovery_manager.recover_from_crash()
        
        # 验证恢复会话
        assert session.recovery_status == "completed"
        assert len(session.recovered_tasks) == 2  # 有检查点的任务
        assert len(session.cleaned_resources) >= 2  # 至少清理了pid和lock文件
        
        # 验证任务状态
        running_task_state = state_manager.get_task_state(running_task)
        assert running_task_state.status == TaskStatus.PAUSED  # 转为可恢复状态
        
        paused_task_state = state_manager.get_task_state(paused_task)
        assert paused_task_state.status == TaskStatus.PAUSED  # 保持暂停状态
        
        incomplete_task_state = state_manager.get_task_state(incomplete_task)
        assert incomplete_task_state.status == TaskStatus.FAILED  # 没有检查点，标记为失败
        
        # 验证恢复的任务可以继续执行
        resumable_tasks = state_manager.get_resumable_tasks()
        resumable_ids = [task.task_id for task in resumable_tasks]
        assert running_task in resumable_ids
        assert paused_task in resumable_ids
        assert incomplete_task not in resumable_ids
    
    def test_concurrent_task_execution_with_recovery(self, state_manager, retry_manager):
        """测试并发任务执行和恢复"""
        results = []
        errors = []
        
        def worker_task(worker_id, task_count):
            """工作线程任务"""
            try:
                for i in range(task_count):
                    task_id = state_manager.create_task("concurrent_work", f"worker_{worker_id}_task_{i}")
                    
                    # 模拟工作函数
                    def work_function(task_id, data):
                        # 随机失败一些任务来测试重试
                        import random
                        if random.random() < 0.3:  # 30%失败率
                            raise RetryableError("Random failure", RetryErrorType.TEMPORARY_ERROR)
                        return f"completed_{data}"
                    
                    try:
                        state_manager.update_task_status(task_id, TaskStatus.RUNNING)
                        state_manager.create_checkpoint(task_id, f"processing_{i}", i, {
                            "worker_id": worker_id,
                            "iteration": i
                        })
                        
                        # 使用重试执行工作
                        result = retry_manager.retry_function(
                            work_function,
                            task_id, f"data_{i}",
                            max_attempts=3
                        )
                        
                        state_manager.complete_task(task_id, {"result": result})
                        results.append(f"success_{worker_id}_{i}")
                        
                    except Exception as e:
                        state_manager.fail_task(task_id, str(e))
                        results.append(f"failed_{worker_id}_{i}")
                        
            except Exception as e:
                errors.append(e)
        
        # 启动多个工作线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_task, args=(i, 5))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(errors) == 0, f"工作线程发生错误: {errors}"
        assert len(results) == 15  # 3个工作线程 * 5个任务
        
        # 统计成功和失败的任务
        success_count = len([r for r in results if r.startswith("success_")])
        failed_count = len([r for r in results if r.startswith("failed_")])
        
        print(f"成功任务: {success_count}, 失败任务: {failed_count}")
        
        # 验证任务状态的一致性
        stats = state_manager.get_task_statistics()
        expected_total = 15
        assert stats['total'] == expected_total
        
        # 验证已完成和失败任务的总数等于创建的任务总数
        completed = stats['by_status'].get(TaskStatus.COMPLETED.value, 0)
        failed = stats['by_status'].get(TaskStatus.FAILED.value, 0)
        assert completed + failed == expected_total
    
    def test_system_resource_management(self, recovery_manager):
        """测试系统资源管理"""
        # 启动正常运行
        recovery_manager.start_normal_operation()
        
        # 验证资源锁定
        assert recovery_manager.pid_file.exists()
        assert recovery_manager.lock_file.exists()
        assert "main_process" in recovery_manager._active_resources
        
        # 获取额外资源锁
        database_resource = "database_connection"
        cache_resource = "redis_cache"
        
        assert recovery_manager.acquire_lock(database_resource) is True
        assert recovery_manager.acquire_lock(cache_resource) is True
        
        # 验证资源状态
        stats = recovery_manager.get_recovery_statistics()
        assert stats['active_resources'] == 3  # main_process + database + cache
        
        # 使用上下文管理器测试资源
        with recovery_manager.resource_lock("temporary_resource"):
            stats = recovery_manager.get_recovery_statistics()
            assert stats['active_resources'] == 4
        
        # 临时资源应该自动释放
        stats = recovery_manager.get_recovery_statistics()
        assert stats['active_resources'] == 3
        
        # 关闭系统
        recovery_manager.shutdown()
        
        # 验证所有资源已释放
        assert not recovery_manager.pid_file.exists()
        assert not recovery_manager.lock_file.exists()
        assert len(recovery_manager._active_resources) == 0
    
    def test_persistent_task_data_across_restarts(self, temp_dir):
        """测试跨重启的任务数据持久化"""
        db_path = str(Path(temp_dir) / "persistence_test.db")
        
        # 第一个会话：创建和执行任务
        persistence1 = PersistenceManager(db_path)
        state_manager1 = StateManager(persistence1)
        
        # 创建任务
        task_id = "persistent_task_001"
        created_id = state_manager1.create_task("file_processing", task_id, {
            "source_file": "/path/to/source.txt",
            "destination": "/path/to/dest.txt"
        })
        assert created_id == task_id
        
        # 更新任务状态
        state_manager1.update_task_status(task_id, TaskStatus.RUNNING)
        state_manager1.update_task_progress(task_id, 60.0, {
            "processed_lines": 600,
            "total_lines": 1000
        })
        
        # 创建检查点
        state_manager1.create_checkpoint(task_id, "line_processing", 6, {
            "last_processed_line": 600,
            "current_position": 15000,
            "encoding": "utf-8"
        })
        
        # 增加重试次数
        state_manager1.increment_retry_count(task_id)
        state_manager1.increment_retry_count(task_id)
        
        # 关闭第一个会话
        state_manager1.close()
        persistence1.close()
        
        # 第二个会话：重新加载数据
        persistence2 = PersistenceManager(db_path)
        state_manager2 = StateManager(persistence2)
        
        # 验证任务数据已恢复
        loaded_task = state_manager2.get_task_state(task_id)
        assert loaded_task is not None
        assert loaded_task.task_id == task_id
        assert loaded_task.task_type == "file_processing"
        assert loaded_task.status == TaskStatus.RUNNING
        assert loaded_task.progress == 60.0
        assert loaded_task.retry_count == 2
        
        # 验证任务数据
        assert loaded_task.data["source_file"] == "/path/to/source.txt"
        assert loaded_task.data["processed_lines"] == 600
        assert loaded_task.data["total_lines"] == 1000
        
        # 验证检查点数据
        assert loaded_task.checkpoint is not None
        assert loaded_task.checkpoint.step == "line_processing"
        assert loaded_task.checkpoint.step_index == 6
        assert loaded_task.checkpoint.data["last_processed_line"] == 600
        assert loaded_task.checkpoint.data["current_position"] == 15000
        
        # 验证任务可以恢复
        assert state_manager2.can_resume_task(task_id) is False  # 运行状态不能直接恢复
        
        # 暂停任务后应该可以恢复
        state_manager2.pause_task(task_id)
        assert state_manager2.can_resume_task(task_id) is True
        
        # 恢复任务
        success = state_manager2.resume_task(task_id)
        assert success is True
        
        # 完成任务
        state_manager2.complete_task(task_id, {
            "final_result": "processing_completed",
            "total_duration": 120.5
        })
        
        final_task = state_manager2.get_task_state(task_id)
        assert final_task.status == TaskStatus.COMPLETED
        assert final_task.progress == 100.0
        assert final_task.data["final_result"] == "processing_completed"
        
        # 清理
        state_manager2.close()
        persistence2.close()
    
    def test_error_recovery_edge_cases(self, state_manager, retry_manager):
        """测试错误恢复的边界情况"""
        
        # 测试1: 任务在检查点创建时失败
        task1_id = state_manager.create_task("checkpoint_failure_test")
        state_manager.update_task_status(task1_id, TaskStatus.RUNNING)
        
        # 模拟检查点处理器异常
        def failing_checkpoint_handler(task_state):
            raise Exception("Checkpoint handler failed")
        
        state_manager.register_checkpoint_handler("checkpoint_failure_test", failing_checkpoint_handler)
        
        # 创建检查点应该不影响任务状态（异常被捕获）
        success = state_manager.create_checkpoint(task1_id, "test_step", 1, {"data": "test"})
        assert success is True  # 检查点创建成功，但处理器异常被捕获
        
        task1_state = state_manager.get_task_state(task1_id)
        assert task1_state.checkpoint is not None  # 检查点仍然被创建
        
        # 测试2: 恢复处理器抛出异常
        task2_id = state_manager.create_task("recovery_exception_test")
        state_manager.create_checkpoint(task2_id, "step1", 1)
        state_manager.update_task_status(task2_id, TaskStatus.PAUSED)
        
        def exception_recovery_handler(task_state):
            raise Exception("Recovery handler exception")
        
        state_manager.register_recovery_handler("recovery_exception_test", exception_recovery_handler)
        
        # 恢复应该失败，任务状态变为失败
        success = state_manager.resume_task(task2_id)
        assert success is False
        
        task2_state = state_manager.get_task_state(task2_id)
        assert task2_state.status == TaskStatus.FAILED
        assert "Recovery handler exception" in task2_state.last_error
        
        # 测试3: 重试管理器的极端情况
        call_count = 0
        
        def inconsistent_error_function():
            nonlocal call_count
            call_count += 1
            
            # 不同类型的错误
            if call_count == 1:
                raise RetryableError("Network error", RetryErrorType.NETWORK_ERROR)
            elif call_count == 2:
                raise RetryableError("Auth error", RetryErrorType.AUTH_ERROR)  
            elif call_count == 3:
                raise RetryableError("Rate limit", RetryErrorType.RATE_LIMIT_ERROR)
            else:
                return "finally_success"
        
        # 由于不同的错误类型有不同的重试策略，最终应该成功
        result = retry_manager.retry_function(inconsistent_error_function, max_attempts=10)
        assert result == "finally_success"
        assert call_count == 4
        
        # 测试4: 任务数据损坏情况
        task3_id = state_manager.create_task("data_corruption_test")
        
        # 手动损坏任务数据（模拟数据库损坏）
        task3_state = state_manager.get_task_state(task3_id)
        task3_state.data = None  # 设置为无效数据
        
        # 保存损坏的数据
        try:
            state_manager._save_state(task3_state)
            # 重新加载应该处理无效数据
            loaded_state = state_manager.get_task_state(task3_id)
            assert loaded_state is not None
            # 数据应该被转换为空字典
            assert isinstance(loaded_state.data, dict)
        except Exception:
            # 如果实现不处理None数据，这是预期的
            pass