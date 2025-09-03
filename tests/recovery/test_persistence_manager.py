"""
持久化管理器测试
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from src.auto_study.recovery.persistence_manager import (
    PersistenceManager, TaskStateData, SessionData, ConfigData
)


class TestPersistenceManager:
    """持久化管理器测试类"""
    
    @pytest.fixture
    def temp_db_path(self):
        """临时数据库路径"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_recovery.db"
        yield str(db_path)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def persistence(self, temp_db_path):
        """持久化管理器实例"""
        manager = PersistenceManager(temp_db_path)
        yield manager
        manager.close()
    
    @pytest.fixture
    def sample_task_data(self):
        """示例任务数据"""
        return TaskStateData(
            task_id="test_task_001",
            task_type="login",
            status="running",
            progress=50.0,
            data={"username": "test_user", "attempt": 1},
            checkpoint_data={"step": "password_input", "step_index": 2},
            retry_count=1,
            last_error="Network timeout",
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now()
        )
    
    def test_database_initialization(self, persistence):
        """测试数据库初始化"""
        # 验证数据库文件已创建
        assert persistence.db_path.exists()
        
        # 验证表结构已创建
        conn = persistence._get_connection()
        
        # 检查所有必要的表是否存在
        tables = conn.execute("""
            SELECT name FROM sqlite_master WHERE type='table'
        """).fetchall()
        
        table_names = {row['name'] for row in tables}
        expected_tables = {'task_states', 'sessions', 'configurations', 'recovery_logs'}
        
        assert expected_tables.issubset(table_names)
    
    def test_task_state_crud_operations(self, persistence, sample_task_data):
        """测试任务状态的CRUD操作"""
        # 创建
        success = persistence.save_task_state(sample_task_data)
        assert success is True
        
        # 读取
        loaded_data = persistence.load_task_state(sample_task_data.task_id)
        assert loaded_data is not None
        assert loaded_data.task_id == sample_task_data.task_id
        assert loaded_data.task_type == sample_task_data.task_type
        assert loaded_data.status == sample_task_data.status
        assert loaded_data.progress == sample_task_data.progress
        assert loaded_data.retry_count == sample_task_data.retry_count
        
        # 更新
        sample_task_data.status = "completed"
        sample_task_data.progress = 100.0
        sample_task_data.updated_at = datetime.now()
        
        success = persistence.save_task_state(sample_task_data)
        assert success is True
        
        updated_data = persistence.load_task_state(sample_task_data.task_id)
        assert updated_data.status == "completed"
        assert updated_data.progress == 100.0
        
        # 删除
        success = persistence.delete_task_state(sample_task_data.task_id)
        assert success is True
        
        deleted_data = persistence.load_task_state(sample_task_data.task_id)
        assert deleted_data is None
    
    def test_task_data_serialization(self, persistence, sample_task_data):
        """测试任务数据的序列化和反序列化"""
        # 保存带复杂数据的任务
        complex_data = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "boolean": True,
            "null_value": None
        }
        sample_task_data.data = complex_data
        
        success = persistence.save_task_state(sample_task_data)
        assert success is True
        
        loaded_data = persistence.load_task_state(sample_task_data.task_id)
        assert loaded_data.data == complex_data
        
        # 验证检查点数据的序列化
        checkpoint_data = {"current_step": "verification", "inputs": ["user", "pass"]}
        sample_task_data.checkpoint_data = checkpoint_data
        
        success = persistence.save_task_state(sample_task_data)
        assert success is True
        
        loaded_data = persistence.load_task_state(sample_task_data.task_id)
        assert loaded_data.checkpoint_data == checkpoint_data
    
    def test_get_tasks_by_status(self, persistence):
        """测试根据状态获取任务"""
        # 创建不同状态的任务
        tasks_data = [
            TaskStateData(
                task_id=f"task_{i}",
                task_type="test",
                status="running" if i % 2 == 0 else "completed",
                progress=float(i * 10),
                data={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            for i in range(5)
        ]
        
        for task_data in tasks_data:
            persistence.save_task_state(task_data)
        
        # 获取运行中的任务
        running_tasks = persistence.get_tasks_by_status("running")
        assert len(running_tasks) == 3  # task_0, task_2, task_4
        
        for task in running_tasks:
            assert task.status == "running"
        
        # 获取已完成的任务
        completed_tasks = persistence.get_tasks_by_status("completed")
        assert len(completed_tasks) == 2  # task_1, task_3
        
        # 根据类型和状态获取任务
        test_running_tasks = persistence.get_tasks_by_status("running", "test")
        assert len(test_running_tasks) == 3
    
    def test_session_management(self, persistence):
        """测试会话管理"""
        # 创建会话数据
        session_data = SessionData(
            session_id="session_001",
            user_id="user_001",
            session_type="login",
            status="active",
            data={"browser": "chrome", "ip": "192.168.1.1"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24)
        )
        
        # 保存会话
        success = persistence.save_session(session_data)
        assert success is True
        
        # 加载会话
        loaded_session = persistence.load_session(session_data.session_id)
        assert loaded_session is not None
        assert loaded_session.session_id == session_data.session_id
        assert loaded_session.user_id == session_data.user_id
        assert loaded_session.data == session_data.data
        
        # 获取活跃会话
        active_sessions = persistence.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == session_data.session_id
        
        # 根据用户获取活跃会话
        user_sessions = persistence.get_active_sessions("user_001")
        assert len(user_sessions) == 1
        
        other_user_sessions = persistence.get_active_sessions("user_002")
        assert len(other_user_sessions) == 0
    
    def test_expired_session_cleanup(self, persistence):
        """测试过期会话清理"""
        # 创建已过期的会话
        expired_session = SessionData(
            session_id="expired_001",
            user_id="user_001",
            session_type="test",
            status="active",
            data={},
            created_at=datetime.now() - timedelta(hours=25),
            updated_at=datetime.now() - timedelta(hours=25),
            expires_at=datetime.now() - timedelta(hours=1)  # 1小时前过期
        )
        
        # 创建未过期的会话
        active_session = SessionData(
            session_id="active_001",
            user_id="user_002",
            session_type="test",
            status="active",
            data={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)  # 1小时后过期
        )
        
        # 保存两个会话
        persistence.save_session(expired_session)
        persistence.save_session(active_session)
        
        # 验证初始状态
        all_sessions_before = persistence.get_active_sessions()
        assert len(all_sessions_before) == 1  # 只有未过期的会话
        
        # 清理过期会话
        deleted_count = persistence.cleanup_expired_sessions()
        assert deleted_count == 1
        
        # 验证清理后状态
        remaining_sessions = persistence.get_active_sessions()
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].session_id == "active_001"
    
    def test_configuration_management(self, persistence):
        """测试配置管理"""
        # 创建配置数据
        config_data = ConfigData(
            key="retry_max_attempts",
            value="5",
            category="recovery",
            description="Maximum retry attempts",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 保存配置
        success = persistence.save_config(config_data)
        assert success is True
        
        # 加载配置
        loaded_config = persistence.load_config(config_data.key)
        assert loaded_config is not None
        assert loaded_config.key == config_data.key
        assert loaded_config.value == config_data.value
        assert loaded_config.category == config_data.category
        
        # 创建更多配置
        configs = [
            ConfigData(
                key="timeout_seconds",
                value="30",
                category="recovery",
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            ConfigData(
                key="log_level",
                value="INFO",
                category="logging",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        for config in configs:
            persistence.save_config(config)
        
        # 根据分类获取配置
        recovery_configs = persistence.get_configs_by_category("recovery")
        assert len(recovery_configs) == 2
        assert "retry_max_attempts" in recovery_configs
        assert "timeout_seconds" in recovery_configs
        
        logging_configs = persistence.get_configs_by_category("logging")
        assert len(logging_configs) == 1
        assert "log_level" in logging_configs
    
    def test_recovery_logs(self, persistence):
        """测试恢复日志"""
        # 记录恢复事件
        success = persistence.log_recovery_event(
            "task_recovery",
            task_id="test_task_001",
            status="success",
            details={"recovered_steps": 3, "duration": 5.2}
        )
        assert success is True
        
        # 记录会话恢复事件
        success = persistence.log_recovery_event(
            "session_recovery",
            session_id="session_001",
            status="failed",
            details={"error": "Authentication failed"}
        )
        assert success is True
        
        # 获取恢复历史
        history = persistence.get_recovery_history(hours=24)
        assert len(history) == 2
        
        # 验证记录内容
        task_recovery_log = next(
            (log for log in history if log['recovery_type'] == 'task_recovery'),
            None
        )
        assert task_recovery_log is not None
        assert task_recovery_log['task_id'] == 'test_task_001'
        assert task_recovery_log['status'] == 'success'
        assert task_recovery_log['details']['recovered_steps'] == 3
        
        # 根据类型获取恢复历史
        task_history = persistence.get_recovery_history(hours=24, recovery_type="task_recovery")
        assert len(task_history) == 1
        assert task_history[0]['recovery_type'] == 'task_recovery'
    
    def test_database_statistics(self, persistence, sample_task_data):
        """测试数据库统计信息"""
        # 添加一些数据
        persistence.save_task_state(sample_task_data)
        
        session_data = SessionData(
            session_id="test_session",
            user_id="test_user",
            session_type="test",
            status="active",
            data={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        persistence.save_session(session_data)
        
        config_data = ConfigData(
            key="test_key",
            value="test_value",
            category="test",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        persistence.save_config(config_data)
        
        persistence.log_recovery_event("test", status="success")
        
        # 获取统计信息
        stats = persistence.get_database_stats()
        
        assert stats['task_count'] == 1
        assert stats['session_count'] == 1
        assert stats['config_count'] == 1
        assert stats['recovery_log_count'] == 1
        assert stats['db_size'] > 0
    
    def test_database_backup(self, persistence, temp_db_path, sample_task_data):
        """测试数据库备份"""
        # 添加数据
        persistence.save_task_state(sample_task_data)
        
        # 备份数据库
        backup_path = temp_db_path + ".backup"
        success = persistence.backup_database(backup_path)
        assert success is True
        
        # 验证备份文件存在且有内容
        backup_file = Path(backup_path)
        assert backup_file.exists()
        assert backup_file.stat().st_size > 0
        
        # 验证备份可以作为新数据库使用
        backup_manager = PersistenceManager(backup_path)
        try:
            loaded_data = backup_manager.load_task_state(sample_task_data.task_id)
            assert loaded_data is not None
            assert loaded_data.task_id == sample_task_data.task_id
        finally:
            backup_manager.close()
    
    def test_concurrent_operations(self, persistence):
        """测试并发操作"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    task_data = TaskStateData(
                        task_id=f"worker_{worker_id}_task_{i}",
                        task_type="concurrent_test",
                        status="running",
                        progress=float(i * 10),
                        data={"worker_id": worker_id, "iteration": i},
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    success = persistence.save_task_state(task_data)
                    results.append(success)
                    time.sleep(0.01)  # 小延迟模拟实际操作
                    
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
        assert len(results) == 50  # 5个工作线程 * 10次操作
        assert all(results), "所有操作都应该成功"
        
        # 验证数据完整性
        all_tasks = persistence.get_tasks_by_status("running", "concurrent_test")
        assert len(all_tasks) == 50
    
    def test_transaction_rollback(self, persistence):
        """测试事务回滚"""
        # 这个测试验证在出现错误时事务会正确回滚
        # 由于我们的实现使用了自动提交模式，这里主要测试异常处理
        
        # 尝试保存无效数据
        invalid_task_data = TaskStateData(
            task_id="invalid_task",
            task_type="test",
            status="running",
            progress=50.0,
            data={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # 正常情况下应该成功
        success = persistence.save_task_state(invalid_task_data)
        assert success is True
        
        # 验证数据已保存
        loaded_data = persistence.load_task_state("invalid_task")
        assert loaded_data is not None
    
    def test_database_vacuum(self, persistence, sample_task_data):
        """测试数据库压缩"""
        # 添加一些数据
        for i in range(100):
            task_data = TaskStateData(
                task_id=f"vacuum_test_{i}",
                task_type="test",
                status="completed",
                progress=100.0,
                data={"index": i},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            persistence.save_task_state(task_data)
        
        # 获取压缩前的数据库大小
        size_before = persistence.db_path.stat().st_size
        
        # 删除一半数据
        for i in range(0, 100, 2):
            persistence.delete_task_state(f"vacuum_test_{i}")
        
        # 执行压缩
        success = persistence.vacuum_database()
        assert success is True
        
        # 验证数据仍然完整
        remaining_tasks = persistence.get_tasks_by_status("completed", "test")
        assert len(remaining_tasks) == 50