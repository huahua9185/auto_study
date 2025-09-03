"""
状态管理器测试
"""

import pytest
import tempfile
import shutil
import time
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.auto_study.recovery.state_manager import (
    StateManager, TaskState, TaskStatus, CheckpointData
)
from src.auto_study.recovery.persistence_manager import PersistenceManager


class TestStateManager:
    """状态管理器测试类"""
    
    @pytest.fixture
    def temp_db_path(self):
        """临时数据库路径"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_state.db"
        yield str(db_path)
        shutil.rmtree(temp_dir)
    
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
    
    def test_create_task(self, state_manager):
        """测试创建任务"""
        # 测试自动生成ID的任务创建
        task_id = state_manager.create_task("login", initial_data={"username": "test"})
        
        assert task_id.startswith("login_")
        assert len(task_id) > len("login_")
        
        # 验证任务状态
        task_state = state_manager.get_task_state(task_id)
        assert task_state is not None
        assert task_state.task_id == task_id
        assert task_state.task_type == "login"
        assert task_state.status == TaskStatus.PENDING
        assert task_state.progress == 0.0
        assert task_state.data == {"username": "test"}
        assert task_state.retry_count == 0
        
        # 测试指定ID的任务创建
        custom_task_id = "custom_task_001"
        created_id = state_manager.create_task("custom", custom_task_id)
        assert created_id == custom_task_id
        
        task_state = state_manager.get_task_state(custom_task_id)
        assert task_state is not None
        assert task_state.task_id == custom_task_id
    
    def test_duplicate_task_id(self, state_manager):
        """测试重复任务ID处理"""
        task_id = "duplicate_test"
        
        # 创建第一个任务
        state_manager.create_task("test", task_id)
        
        # 尝试创建相同ID的任务应该抛出异常
        with pytest.raises(ValueError, match="任务ID已存在"):
            state_manager.create_task("test", task_id)
    
    def test_task_status_updates(self, state_manager):
        """测试任务状态更新"""
        task_id = state_manager.create_task("status_test")
        
        # 更新为运行状态
        success = state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.RUNNING
        
        # 更新为失败状态并设置错误信息
        error_msg = "Network connection failed"
        success = state_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.FAILED
        assert task_state.last_error == error_msg
        
        # 测试不存在的任务
        success = state_manager.update_task_status("nonexistent", TaskStatus.COMPLETED)
        assert success is False
    
    def test_task_progress_updates(self, state_manager):
        """测试任务进度更新"""
        task_id = state_manager.create_task("progress_test")
        
        # 更新进度
        success = state_manager.update_task_progress(task_id, 25.5)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.progress == 25.5
        
        # 更新进度和数据
        data_updates = {"current_step": "authentication", "attempts": 1}
        success = state_manager.update_task_progress(task_id, 50.0, data_updates)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.progress == 50.0
        assert task_state.data["current_step"] == "authentication"
        assert task_state.data["attempts"] == 1
        
        # 测试进度范围限制
        state_manager.update_task_progress(task_id, -10)  # 应该被限制为0
        task_state = state_manager.get_task_state(task_id)
        assert task_state.progress == 0.0
        
        state_manager.update_task_progress(task_id, 150)  # 应该被限制为100
        task_state = state_manager.get_task_state(task_id)
        assert task_state.progress == 100.0
    
    def test_checkpoint_management(self, state_manager):
        """测试检查点管理"""
        task_id = state_manager.create_task("checkpoint_test")
        
        # 创建检查点
        checkpoint_data = {"form_data": {"username": "test", "password": "***"}}
        success = state_manager.create_checkpoint(task_id, "login_form", 1, checkpoint_data)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.checkpoint is not None
        assert task_state.checkpoint.step == "login_form"
        assert task_state.checkpoint.step_index == 1
        assert task_state.checkpoint.data == checkpoint_data
        
        # 更新检查点
        new_checkpoint_data = {"verification_code": "123456"}
        success = state_manager.create_checkpoint(task_id, "verification", 2, new_checkpoint_data)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.checkpoint.step == "verification"
        assert task_state.checkpoint.step_index == 2
        assert task_state.checkpoint.data == new_checkpoint_data
    
    def test_checkpoint_handlers(self, state_manager):
        """测试检查点处理器"""
        handler_called = False
        checkpoint_received = None
        
        def checkpoint_handler(task_state):
            nonlocal handler_called, checkpoint_received
            handler_called = True
            checkpoint_received = task_state.checkpoint
        
        # 注册检查点处理器
        state_manager.register_checkpoint_handler("handler_test", checkpoint_handler)
        
        # 创建任务并设置检查点
        task_id = state_manager.create_task("handler_test")
        state_manager.create_checkpoint(task_id, "test_step", 1, {"data": "test"})
        
        # 验证处理器被调用
        assert handler_called is True
        assert checkpoint_received is not None
        assert checkpoint_received.step == "test_step"
        assert checkpoint_received.data == {"data": "test"}
    
    def test_task_resume_capability(self, state_manager):
        """测试任务恢复能力检查"""
        # 创建任务
        task_id = state_manager.create_task("resume_test")
        
        # 没有检查点的任务不能恢复
        assert state_manager.can_resume_task(task_id) is False
        
        # 创建检查点
        state_manager.create_checkpoint(task_id, "step1", 1, {"progress": "partial"})
        
        # 仍然不能恢复，因为状态不是PAUSED或FAILED
        assert state_manager.can_resume_task(task_id) is False
        
        # 设置为暂停状态
        state_manager.update_task_status(task_id, TaskStatus.PAUSED)
        assert state_manager.can_resume_task(task_id) is True
        
        # 设置为失败状态
        state_manager.update_task_status(task_id, TaskStatus.FAILED)
        assert state_manager.can_resume_task(task_id) is True
        
        # 设置为完成状态
        state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
        assert state_manager.can_resume_task(task_id) is False
    
    def test_task_resume(self, state_manager):
        """测试任务恢复"""
        # 创建可恢复的任务
        task_id = state_manager.create_task("resume_test")
        state_manager.create_checkpoint(task_id, "interrupted_step", 2)
        state_manager.update_task_status(task_id, TaskStatus.PAUSED)
        
        # 没有恢复处理器的情况
        success = state_manager.resume_task(task_id)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.RUNNING
        
        # 重置为暂停状态测试恢复处理器
        state_manager.update_task_status(task_id, TaskStatus.PAUSED)
        
        handler_called = False
        
        def recovery_handler(task_state):
            nonlocal handler_called
            handler_called = True
            return True  # 成功恢复
        
        state_manager.register_recovery_handler("resume_test", recovery_handler)
        
        success = state_manager.resume_task(task_id)
        assert success is True
        assert handler_called is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.RUNNING
    
    def test_task_resume_failure(self, state_manager):
        """测试任务恢复失败"""
        # 创建任务
        task_id = state_manager.create_task("resume_fail_test")
        state_manager.create_checkpoint(task_id, "test_step", 1)
        state_manager.update_task_status(task_id, TaskStatus.PAUSED)
        
        # 注册总是失败的恢复处理器
        def failing_recovery_handler(task_state):
            return False
        
        state_manager.register_recovery_handler("resume_fail_test", failing_recovery_handler)
        
        success = state_manager.resume_task(task_id)
        assert success is False
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.FAILED
    
    def test_task_pause(self, state_manager):
        """测试任务暂停"""
        task_id = state_manager.create_task("pause_test")
        state_manager.update_task_status(task_id, TaskStatus.RUNNING)
        
        # 暂停运行中的任务
        success = state_manager.pause_task(task_id)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.PAUSED
        
        # 尝试暂停非运行中的任务应该失败
        success = state_manager.pause_task(task_id)
        assert success is False
    
    def test_task_completion(self, state_manager):
        """测试任务完成"""
        task_id = state_manager.create_task("complete_test")
        
        # 完成任务
        final_data = {"result": "success", "duration": 123.45}
        success = state_manager.complete_task(task_id, final_data)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.COMPLETED
        assert task_state.progress == 100.0
        assert task_state.data["result"] == "success"
        assert task_state.data["duration"] == 123.45
    
    def test_task_failure(self, state_manager):
        """测试任务失败"""
        task_id = state_manager.create_task("fail_test")
        
        error_message = "Authentication failed after 3 attempts"
        success = state_manager.fail_task(task_id, error_message)
        assert success is True
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.status == TaskStatus.FAILED
        assert task_state.last_error == error_message
    
    def test_retry_count_management(self, state_manager):
        """测试重试次数管理"""
        task_id = state_manager.create_task("retry_test")
        
        # 初始重试次数为0
        task_state = state_manager.get_task_state(task_id)
        assert task_state.retry_count == 0
        
        # 增加重试次数
        count = state_manager.increment_retry_count(task_id)
        assert count == 1
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.retry_count == 1
        
        # 再次增加
        count = state_manager.increment_retry_count(task_id)
        assert count == 2
        
        task_state = state_manager.get_task_state(task_id)
        assert task_state.retry_count == 2
    
    def test_get_tasks_by_status(self, state_manager):
        """测试根据状态获取任务"""
        # 创建不同状态和类型的任务
        task_ids = []
        
        # 运行中的任务
        for i in range(3):
            task_id = state_manager.create_task("type_a", f"running_a_{i}")
            state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            task_ids.append(task_id)
        
        # 运行中的不同类型任务
        for i in range(2):
            task_id = state_manager.create_task("type_b", f"running_b_{i}")
            state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            task_ids.append(task_id)
        
        # 已完成的任务
        for i in range(2):
            task_id = state_manager.create_task("type_a", f"completed_a_{i}")
            state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
            task_ids.append(task_id)
        
        # 获取所有运行中的任务
        running_tasks = state_manager.get_tasks_by_status(TaskStatus.RUNNING)
        assert len(running_tasks) == 5
        
        # 获取特定类型的运行中任务
        running_type_a = state_manager.get_tasks_by_status(TaskStatus.RUNNING, "type_a")
        assert len(running_type_a) == 3
        
        running_type_b = state_manager.get_tasks_by_status(TaskStatus.RUNNING, "type_b")
        assert len(running_type_b) == 2
        
        # 获取已完成的任务
        completed_tasks = state_manager.get_tasks_by_status(TaskStatus.COMPLETED)
        assert len(completed_tasks) == 2
    
    def test_get_resumable_tasks(self, state_manager):
        """测试获取可恢复任务"""
        # 创建不同状态的任务
        resumable_task_id = state_manager.create_task("resumable", "resumable_001")
        state_manager.create_checkpoint(resumable_task_id, "step1", 1)
        state_manager.update_task_status(resumable_task_id, TaskStatus.PAUSED)
        
        failed_resumable_id = state_manager.create_task("resumable", "failed_resumable_001")
        state_manager.create_checkpoint(failed_resumable_id, "step2", 2)
        state_manager.update_task_status(failed_resumable_id, TaskStatus.FAILED)
        
        # 没有检查点的暂停任务
        non_resumable_id = state_manager.create_task("non_resumable", "non_resumable_001")
        state_manager.update_task_status(non_resumable_id, TaskStatus.PAUSED)
        
        # 已完成的任务（即使有检查点也不可恢复）
        completed_id = state_manager.create_task("completed", "completed_001")
        state_manager.create_checkpoint(completed_id, "final_step", 3)
        state_manager.update_task_status(completed_id, TaskStatus.COMPLETED)
        
        # 获取所有可恢复的任务
        resumable_tasks = state_manager.get_resumable_tasks()
        resumable_ids = [task.task_id for task in resumable_tasks]
        
        assert len(resumable_tasks) == 2
        assert resumable_task_id in resumable_ids
        assert failed_resumable_id in resumable_ids
        assert non_resumable_id not in resumable_ids
        assert completed_id not in resumable_ids
        
        # 根据类型获取可恢复的任务
        resumable_type_tasks = state_manager.get_resumable_tasks("resumable")
        assert len(resumable_type_tasks) == 2
    
    def test_clean_completed_tasks(self, state_manager):
        """测试清理已完成任务"""
        # 创建已完成的任务（最近完成的）
        recent_completed = state_manager.create_task("recent_completed")
        state_manager.update_task_status(recent_completed, TaskStatus.COMPLETED)
        
        # 模拟旧的已完成任务
        old_completed = state_manager.create_task("old_completed")
        state_manager.update_task_status(old_completed, TaskStatus.COMPLETED)
        
        # 手动设置旧任务的更新时间
        old_task_state = state_manager.get_task_state(old_completed)
        old_task_state.updated_at = datetime.now() - timedelta(hours=25)  # 25小时前
        state_manager._save_state(old_task_state)
        
        # 创建运行中的任务（不应被清理）
        running_task = state_manager.create_task("running_task")
        state_manager.update_task_status(running_task, TaskStatus.RUNNING)
        
        # 执行清理（保留24小时内的任务）
        cleaned_count = state_manager.clean_completed_tasks(keep_hours=24)
        assert cleaned_count == 1
        
        # 验证清理结果
        assert state_manager.get_task_state(recent_completed) is not None
        assert state_manager.get_task_state(old_completed) is None
        assert state_manager.get_task_state(running_task) is not None
    
    def test_task_statistics(self, state_manager):
        """测试任务统计"""
        # 创建各种状态和类型的任务
        tasks_config = [
            ("type_a", TaskStatus.RUNNING, 3),
            ("type_a", TaskStatus.COMPLETED, 2),
            ("type_b", TaskStatus.PENDING, 1),
            ("type_b", TaskStatus.FAILED, 1),
        ]
        
        total_tasks = 0
        for task_type, status, count in tasks_config:
            for i in range(count):
                task_id = state_manager.create_task(task_type, f"{task_type}_{status.value}_{i}")
                state_manager.update_task_status(task_id, status)
                total_tasks += 1
        
        # 创建可恢复的任务
        resumable_id = state_manager.create_task("resumable_type")
        state_manager.create_checkpoint(resumable_id, "step1", 1)
        state_manager.update_task_status(resumable_id, TaskStatus.PAUSED)
        total_tasks += 1
        
        # 获取统计信息
        stats = state_manager.get_task_statistics()
        
        assert stats['total'] == total_tasks
        assert stats['by_status'][TaskStatus.RUNNING.value] == 3
        assert stats['by_status'][TaskStatus.COMPLETED.value] == 2
        assert stats['by_status'][TaskStatus.PENDING.value] == 1
        assert stats['by_status'][TaskStatus.FAILED.value] == 1
        assert stats['by_status'][TaskStatus.PAUSED.value] == 1
        
        assert stats['by_type']['type_a'] == 5
        assert stats['by_type']['type_b'] == 2
        assert stats['by_type']['resumable_type'] == 1
        
        assert stats['resumable_count'] == 1
    
    def test_concurrent_operations(self, state_manager):
        """测试并发操作"""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    # 创建任务
                    task_id = state_manager.create_task("concurrent", f"worker_{worker_id}_{i}")
                    results.append(f"created_{task_id}")
                    
                    # 更新状态
                    state_manager.update_task_status(task_id, TaskStatus.RUNNING)
                    
                    # 更新进度
                    state_manager.update_task_progress(task_id, i * 10)
                    
                    # 创建检查点
                    state_manager.create_checkpoint(task_id, f"step_{i}", i)
                    
                    time.sleep(0.001)  # 小延迟
                    
            except Exception as e:
                errors.append(e)
        
        # 启动多个工作线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(errors) == 0, f"发生错误: {errors}"
        assert len(results) == 50
        
        # 验证任务状态
        all_tasks = state_manager.get_tasks_by_status(TaskStatus.RUNNING, "concurrent")
        assert len(all_tasks) == 50
        
        # 验证所有任务都有检查点
        for task in all_tasks:
            assert task.checkpoint is not None
    
    def test_task_deletion(self, state_manager):
        """测试任务删除"""
        # 创建任务
        task_id = state_manager.create_task("delete_test")
        
        # 验证任务存在
        assert state_manager.get_task_state(task_id) is not None
        
        # 删除任务
        success = state_manager.delete_task(task_id)
        assert success is True
        
        # 验证任务已删除
        assert state_manager.get_task_state(task_id) is None
        
        # 删除不存在的任务
        success = state_manager.delete_task("nonexistent")
        assert success is False
    
    def test_persistence_integration(self, temp_db_path):
        """测试持久化集成"""
        # 创建第一个状态管理器实例
        persistence1 = PersistenceManager(temp_db_path)
        manager1 = StateManager(persistence1)
        
        try:
            # 创建一些任务
            task1_id = manager1.create_task("persistent_test", "task1")
            manager1.update_task_status(task1_id, TaskStatus.RUNNING)
            manager1.create_checkpoint(task1_id, "step1", 1, {"data": "test"})
            
            task2_id = manager1.create_task("persistent_test", "task2")
            manager1.update_task_status(task2_id, TaskStatus.PAUSED)
            
            # 关闭第一个管理器
            manager1.close()
            persistence1.close()
            
            # 创建第二个管理器实例，应该加载之前的状态
            persistence2 = PersistenceManager(temp_db_path)
            manager2 = StateManager(persistence2)
            
            try:
                # 验证任务已加载
                loaded_task1 = manager2.get_task_state(task1_id)
                assert loaded_task1 is not None
                assert loaded_task1.status == TaskStatus.RUNNING
                assert loaded_task1.checkpoint is not None
                assert loaded_task1.checkpoint.step == "step1"
                assert loaded_task1.checkpoint.data == {"data": "test"}
                
                loaded_task2 = manager2.get_task_state(task2_id)
                assert loaded_task2 is not None
                assert loaded_task2.status == TaskStatus.PAUSED
                
                # 验证统计信息
                stats = manager2.get_task_statistics()
                assert stats['total'] == 2
                
            finally:
                manager2.close()
                persistence2.close()
                
        finally:
            # 确保资源清理
            try:
                manager1.close()
                persistence1.close()
            except:
                pass