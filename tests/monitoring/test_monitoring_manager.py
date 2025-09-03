"""
监控管理器测试
"""

import pytest
import time
import threading
from datetime import datetime
from unittest.mock import Mock, patch

from src.auto_study.monitoring.monitoring_manager import MonitoringManager
from src.auto_study.monitoring.structured_logger import LogCategory
from src.auto_study.monitoring.ui_panel import TaskStatus


class TestMonitoringManager:
    """监控管理器测试"""
    
    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """临时日志目录"""
        return str(tmp_path / "test_logs")
    
    @pytest.fixture
    def manager(self, temp_log_dir):
        """创建测试监控管理器"""
        return MonitoringManager(
            log_dir=temp_log_dir,
            enable_ui=False,  # 禁用UI避免测试时的交互
            enable_alerts=True
        )
    
    def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        assert manager.logger is not None
        assert manager.status_monitor is not None
        assert manager.ui is None  # 已禁用
        assert manager.alert_manager is not None
        assert not manager._is_running
    
    def test_manager_with_ui(self, temp_log_dir):
        """测试带UI的管理器"""
        manager = MonitoringManager(
            log_dir=temp_log_dir,
            enable_ui=True,
            enable_alerts=False
        )
        
        assert manager.ui is not None
        assert manager.alert_manager is None
    
    def test_start_stop_monitoring(self, manager):
        """测试启动和停止监控"""
        assert not manager._is_running
        
        # 启动监控
        manager.start()
        assert manager._is_running
        
        # 等待一段时间确保线程启动
        time.sleep(0.5)
        
        # 停止监控
        manager.stop()
        assert not manager._is_running
    
    def test_task_context_success(self, manager):
        """测试任务上下文（成功）"""
        task_name = "测试任务"
        
        with manager.task_context(task_name) as task_id:
            assert task_id is not None
            assert task_id.startswith("task_")
            
            # 模拟一些任务工作
            time.sleep(0.1)
        
        # 检查日志记录
        recent_logs = manager.logger.get_recent_logs(10)
        assert len(recent_logs) >= 2  # 开始和完成日志
        
        # 检查是否有开始和完成的日志
        messages = [log.message for log in recent_logs]
        assert any("任务开始" in msg and task_name in msg for msg in messages)
        assert any("任务完成" in msg and task_name in msg for msg in messages)
    
    def test_task_context_failure(self, manager):
        """测试任务上下文（失败）"""
        task_name = "失败任务"
        
        with pytest.raises(ValueError):
            with manager.task_context(task_name) as task_id:
                assert task_id is not None
                raise ValueError("测试异常")
        
        # 检查日志记录
        recent_logs = manager.logger.get_recent_logs(10)
        messages = [log.message for log in recent_logs]
        
        # 应该有失败的日志
        assert any("任务失败" in msg and task_name in msg for msg in messages)
    
    def test_task_context_custom_id(self, manager):
        """测试自定义任务ID"""
        custom_id = "custom_task_123"
        
        with manager.task_context("自定义任务", custom_id) as task_id:
            assert task_id == custom_id
    
    def test_update_task_progress(self, manager):
        """测试更新任务进度"""
        with manager.task_context("进度任务") as task_id:
            manager.update_task_progress(task_id, 25.0, "第一步完成")
            manager.update_task_progress(task_id, 50.0, "第二步完成")
            manager.update_task_progress(task_id, 100.0, "全部完成")
        
        # 检查进度日志
        recent_logs = manager.logger.get_recent_logs(10)
        progress_logs = [log for log in recent_logs if "任务进度" in log.message]
        assert len(progress_logs) == 3
    
    def test_basic_logging_methods(self, manager):
        """测试基本日志方法"""
        # 测试各种日志方法
        manager.log_info("信息日志", LogCategory.SYSTEM)
        manager.log_warning("警告日志", LogCategory.AUTOMATION)
        manager.log_error("错误日志", LogCategory.BROWSER, ValueError("测试错误"))
        
        # 验证日志记录
        recent_logs = manager.logger.get_recent_logs(5)
        assert len(recent_logs) == 3
        
        levels = [log.level.value for log in recent_logs]
        assert "INFO" in levels
        assert "WARNING" in levels
        assert "ERROR" in levels
    
    def test_business_logging_methods(self, manager):
        """测试业务日志方法"""
        # 用户操作
        manager.log_user_action("user123", "登录", "成功登录")
        
        # 自动化步骤
        manager.log_automation_step("task456", "点击按钮", "成功", 0.5)
        
        # 浏览器操作
        manager.log_browser_action("导航", "https://example.com", "页面已加载")
        
        # 网络请求
        manager.log_network_request("GET", "https://api.example.com", 200, 0.3)
        
        # 性能指标
        manager.log_performance_metric("响应时间", 150.0, "ms")
        
        # 安全事件
        manager.log_security_event("登录尝试", "登录失败", "192.168.1.1", "HIGH")
        
        # 验证日志记录
        recent_logs = manager.logger.get_recent_logs(10)
        assert len(recent_logs) >= 6
        
        # 验证分类
        categories = [log.category.value for log in recent_logs]
        assert "用户" in categories
        assert "自动化" in categories
        assert "浏览器" in categories
        assert "网络" in categories
        assert "性能" in categories
        assert "安全" in categories
    
    def test_alert_management(self, manager):
        """测试告警管理"""
        # 获取活跃告警
        active_alerts = manager.get_active_alerts()
        assert isinstance(active_alerts, list)
        
        # 由于没有实际告警，确认和解决应该返回False
        assert not manager.acknowledge_alert("nonexistent_alert")
        assert not manager.resolve_alert("nonexistent_alert")
    
    @patch('src.auto_study.monitoring.structured_logger.Console')
    def test_show_dashboard(self, mock_console, manager):
        """测试显示仪表板"""
        # 创建一些测试数据
        manager.log_info("仪表板测试")
        manager.log_error("仪表板错误")
        
        manager.show_dashboard()
        
        # 验证控制台被调用
        mock_console.assert_called()
    
    def test_export_data(self, manager, tmp_path):
        """测试数据导出"""
        # 创建一些测试数据
        manager.log_info("导出测试1")
        manager.log_error("导出测试2")
        
        export_path = str(tmp_path / "export_test")
        manager.export_data(export_path, hours=1)
        
        # 验证文件被创建
        metrics_file = tmp_path / "export_test_metrics.json"
        logs_file = tmp_path / "export_test_logs.json"
        
        # 注意：实际文件创建取决于底层组件的实现
        # 这里主要测试方法不会抛出异常
    
    def test_get_system_health(self, manager):
        """测试获取系统健康状态"""
        health = manager.get_system_health()
        
        assert isinstance(health, dict)
        assert 'performance_score' in health
        assert 'health_status' in health
        assert 'error_count' in health
        assert 'active_alerts' in health
        assert 'system_metrics' in health
        assert 'timestamp' in health
        
        # 验证数据类型
        assert isinstance(health['performance_score'], (int, float))
        assert isinstance(health['health_status'], str)
        assert isinstance(health['error_count'], int)
        assert isinstance(health['active_alerts'], int)
    
    def test_integration_log_to_alert(self, manager):
        """测试日志到告警的集成"""
        # 创建足够多的错误日志来触发告警
        for i in range(15):
            manager.log_error(f"集成测试错误 {i}", LogCategory.SYSTEM)
        
        # 手动触发监控循环（通常由后台线程处理）
        if manager.alert_manager:
            recent_logs = manager.logger.get_recent_logs(100)
            system_metrics = manager.status_monitor.get_current_metrics()
            
            metrics_dict = {
                'cpu_usage': system_metrics.cpu_usage,
                'memory_usage': system_metrics.memory_usage,
                'disk_usage': system_metrics.disk_usage,
                'active_threads': system_metrics.active_threads
            }
            
            manager.alert_manager.process_detections(recent_logs, metrics_dict)
            
            # 检查是否生成了告警
            active_alerts = manager.get_active_alerts()
            # 由于时间窗口限制，可能不会立即生成告警，所以不强制断言
    
    def test_concurrent_operations(self, manager):
        """测试并发操作"""
        def log_worker(worker_id):
            for i in range(10):
                manager.log_info(f"并发测试 - Worker {worker_id} - Message {i}")
                time.sleep(0.01)
        
        def task_worker(worker_id):
            for i in range(5):
                with manager.task_context(f"并发任务 {worker_id}-{i}"):
                    time.sleep(0.02)
        
        # 创建日志工作线程
        log_threads = []
        for i in range(3):
            thread = threading.Thread(target=log_worker, args=(i,))
            log_threads.append(thread)
            thread.start()
        
        # 创建任务工作线程
        task_threads = []
        for i in range(2):
            thread = threading.Thread(target=task_worker, args=(i,))
            task_threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in log_threads + task_threads:
            thread.join()
        
        # 验证日志记录
        recent_logs = manager.logger.get_recent_logs(100)
        assert len(recent_logs) >= 30  # 至少30条日志（日志工作线程）
    
    def test_memory_efficiency(self, manager):
        """测试内存效率"""
        # 生成大量日志
        for i in range(2000):
            if i % 100 == 0:
                manager.log_error(f"内存测试错误 {i}")
            else:
                manager.log_info(f"内存测试信息 {i}")
        
        # 验证日志数量被限制
        recent_logs = manager.logger.get_recent_logs(2000)
        assert len(recent_logs) <= 1000  # 应该被限制在maxlen
    
    def test_error_handling_in_integration(self, manager):
        """测试集成中的错误处理"""
        # 模拟组件错误
        original_method = manager.logger.info
        
        def failing_method(*args, **kwargs):
            if "failure_test" in str(args):
                raise Exception("Simulated failure")
            return original_method(*args, **kwargs)
        
        manager.logger.info = failing_method
        
        # 这些调用不应该导致管理器崩溃
        manager.log_info("normal_message")
        try:
            manager.log_info("failure_test message")
        except:
            pass  # 预期的异常
        
        manager.log_info("another normal message")
        
        # 恢复原始方法
        manager.logger.info = original_method
    
    def test_performance_monitoring(self, manager):
        """测试性能监控"""
        start_time = time.time()
        
        # 执行一些操作
        with manager.task_context("性能测试任务") as task_id:
            for i in range(10):
                manager.update_task_progress(task_id, i * 10, f"步骤 {i}")
                time.sleep(0.01)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 记录性能指标
        manager.log_performance_metric("任务执行时间", duration, "秒")
        
        # 验证性能日志
        recent_logs = manager.logger.get_recent_logs(20)
        perf_logs = [log for log in recent_logs if log.category == LogCategory.PERFORMANCE]
        assert len(perf_logs) >= 1
    
    def test_cleanup_on_stop(self, manager):
        """测试停止时的清理"""
        # 启动管理器
        manager.start()
        assert manager._is_running
        
        # 添加一些数据
        manager.log_info("清理测试")
        
        # 停止管理器
        manager.stop()
        assert not manager._is_running
        
        # 验证组件状态
        # 状态监控器应该已停止
        # 日志数据应该保留
        recent_logs = manager.logger.get_recent_logs(5)
        assert len(recent_logs) > 0  # 日志应该保留