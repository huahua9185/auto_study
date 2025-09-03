"""
结构化日志系统测试
"""

import pytest
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.auto_study.monitoring.structured_logger import (
    StructuredLogger, LogLevel, LogCategory, LogContext, LogEntry
)


class TestStructuredLogger:
    """结构化日志测试"""
    
    @pytest.fixture
    def temp_log_dir(self, tmp_path):
        """临时日志目录"""
        return str(tmp_path / "test_logs")
    
    @pytest.fixture
    def logger(self, temp_log_dir):
        """创建测试日志器"""
        return StructuredLogger(log_dir=temp_log_dir)
    
    def test_logger_initialization(self, logger, temp_log_dir):
        """测试日志器初始化"""
        assert logger.log_dir == Path(temp_log_dir)
        assert logger.log_dir.exists()
        assert len(logger.recent_logs) == 0
        assert len(logger.log_stats) == 0
    
    def test_basic_logging_levels(self, logger):
        """测试基本日志级别"""
        # 测试各个级别的日志
        logger.debug("Debug message", LogCategory.SYSTEM)
        logger.info("Info message", LogCategory.AUTOMATION)
        logger.warning("Warning message", LogCategory.BROWSER)
        logger.error("Error message", LogCategory.NETWORK)
        logger.critical("Critical message", LogCategory.SECURITY)
        
        # 检查日志统计
        assert logger.log_stats['DEBUG'] >= 1
        assert logger.log_stats['INFO'] >= 1
        assert logger.log_stats['WARNING'] >= 1
        assert logger.log_stats['ERROR'] >= 1
        assert logger.log_stats['CRITICAL'] >= 1
        
        # 检查最近日志
        assert len(logger.recent_logs) == 5
    
    def test_log_with_context(self, logger):
        """测试带上下文的日志"""
        context = LogContext(
            user_id="test_user",
            session_id="test_session",
            task_id="test_task"
        )
        
        logger.info("Context message", LogCategory.USER, context)
        
        recent_log = logger.recent_logs[-1]
        assert recent_log.context.user_id == "test_user"
        assert recent_log.context.session_id == "test_session"
        assert recent_log.context.task_id == "test_task"
    
    def test_log_with_exception(self, logger):
        """测试带异常的日志"""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            logger.error("Error with exception", LogCategory.SYSTEM, exception=e)
        
        recent_log = logger.recent_logs[-1]
        assert recent_log.exception is not None
        assert "Test exception" in recent_log.exception
    
    def test_log_with_duration(self, logger):
        """测试带持续时间的日志"""
        logger.info(
            "Performance test", 
            LogCategory.PERFORMANCE, 
            duration=1.5
        )
        
        recent_log = logger.recent_logs[-1]
        assert recent_log.duration == 1.5
    
    def test_business_logging_methods(self, logger):
        """测试业务日志方法"""
        # 用户操作
        logger.log_user_action("user123", "login", "successful login")
        
        # 自动化步骤
        logger.log_automation_step("task456", "click_button", "success", 0.5)
        
        # 浏览器操作
        logger.log_browser_action("navigate", "https://example.com", "page loaded")
        
        # 网络请求
        logger.log_network_request("GET", "https://api.example.com", 200, 0.3)
        
        # 性能指标
        logger.log_performance_metric("response_time", 150.0, "ms")
        
        # 安全事件
        logger.log_security_event("login_attempt", "Failed login", "192.168.1.1", "HIGH")
        
        # 验证日志数量
        assert len(logger.recent_logs) >= 6
        
        # 验证分类统计
        assert logger.log_stats['category_用户'] >= 1
        assert logger.log_stats['category_自动化'] >= 1
        assert logger.log_stats['category_浏览器'] >= 1
        assert logger.log_stats['category_网络'] >= 1
        assert logger.log_stats['category_性能'] >= 1
        assert logger.log_stats['category_安全'] >= 1
    
    def test_get_recent_logs(self, logger):
        """测试获取最近日志"""
        # 创建不同级别和类别的日志
        logger.info("Info 1", LogCategory.SYSTEM)
        logger.error("Error 1", LogCategory.AUTOMATION)
        logger.warning("Warning 1", LogCategory.BROWSER)
        logger.info("Info 2", LogCategory.SYSTEM)
        logger.error("Error 2", LogCategory.AUTOMATION)
        
        # 获取所有日志
        all_logs = logger.get_recent_logs(10)
        assert len(all_logs) == 5
        
        # 按级别过滤
        error_logs = logger.get_recent_logs(10, level=LogLevel.ERROR)
        assert len(error_logs) == 2
        assert all(log.level == LogLevel.ERROR for log in error_logs)
        
        # 按类别过滤
        system_logs = logger.get_recent_logs(10, category=LogCategory.SYSTEM)
        assert len(system_logs) == 2
        assert all(log.category == LogCategory.SYSTEM for log in system_logs)
        
        # 限制数量
        limited_logs = logger.get_recent_logs(3)
        assert len(limited_logs) == 3
    
    def test_get_error_summary(self, logger):
        """测试错误摘要"""
        # 创建一些错误日志
        logger.error("Database connection failed", LogCategory.DATABASE)
        logger.error("Database connection failed", LogCategory.DATABASE)  # 重复
        logger.critical("System crash", LogCategory.SYSTEM)
        logger.error("Network timeout", LogCategory.NETWORK)
        
        summary = logger.get_error_summary(hours=1)
        
        assert len(summary) >= 3  # 至少3种不同类型的错误
        
        # 验证摘要结构
        for error in summary:
            assert 'error_type' in error
            assert 'count' in error
            assert 'first_occurrence' in error
            assert 'last_occurrence' in error
            assert 'sample_message' in error
            assert 'module' in error
        
        # 验证重复错误计数
        db_errors = [e for e in summary if 'Database connection failed' in e['error_type']]
        if db_errors:
            assert db_errors[0]['count'] == 2
    
    def test_log_filters(self, logger):
        """测试日志过滤器"""
        # 添加过滤器：只记录ERROR及以上级别
        def error_filter(entry: LogEntry) -> bool:
            return entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        
        logger.add_filter(error_filter)
        
        # 记录不同级别的日志
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
        
        # 由于过滤器的存在，只有ERROR和CRITICAL会被处理
        # 但所有日志都会被记录到recent_logs中
        assert len(logger.recent_logs) == 4
    
    def test_log_handlers(self, logger):
        """测试日志处理器"""
        handler_calls = []
        
        def test_handler(entry: LogEntry):
            handler_calls.append(entry.message)
        
        logger.add_handler(test_handler)
        
        logger.info("Test message 1")
        logger.error("Test message 2")
        
        assert len(handler_calls) == 2
        assert "Test message 1" in handler_calls
        assert "Test message 2" in handler_calls
    
    def test_export_logs(self, logger, tmp_path):
        """测试日志导出"""
        # 创建一些日志
        logger.info("Export test 1", LogCategory.SYSTEM)
        logger.error("Export test 2", LogCategory.AUTOMATION)
        
        export_path = tmp_path / "exported_logs.json"
        logger.export_logs(str(export_path), hours=1, format="json")
        
        assert export_path.exists()
        
        # 验证导出内容
        with open(export_path, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        assert isinstance(exported_data, list)
        assert len(exported_data) >= 2
        
        # 验证日志结构
        for log_entry in exported_data:
            assert 'timestamp' in log_entry
            assert 'level' in log_entry
            assert 'category' in log_entry
            assert 'message' in log_entry
    
    def test_statistics(self, logger):
        """测试日志统计"""
        # 清空统计
        logger.clear_stats()
        assert sum(logger.log_stats.values()) == 0
        
        # 创建一些日志
        logger.info("Stats test 1")
        logger.info("Stats test 2")
        logger.error("Stats test 3")
        
        stats = logger.get_log_statistics()
        assert stats['INFO'] == 2
        assert stats['ERROR'] == 1
    
    def test_log_rotation(self, logger, temp_log_dir):
        """测试日志轮转（验证文件创建）"""
        # 记录一些日志
        logger.info("Rotation test")
        
        # 给日志文件写入一些时间
        time.sleep(0.1)
        
        # 检查日志文件是否创建
        log_files = list(Path(temp_log_dir).glob("*.log"))
        assert len(log_files) > 0
    
    def test_json_formatter(self, logger):
        """测试JSON格式化器"""
        # 通过记录日志间接测试格式化器
        context = LogContext(user_id="test_user")
        logger.info("JSON format test", LogCategory.SYSTEM, context)
        
        # 验证日志被正确处理
        recent_log = logger.recent_logs[-1]
        assert recent_log.message == "JSON format test"
        assert recent_log.context.user_id == "test_user"
    
    @patch('src.auto_study.monitoring.structured_logger.Console')
    def test_show_log_dashboard(self, mock_console, logger):
        """测试日志仪表板显示"""
        # 创建一些测试数据
        logger.info("Dashboard test 1")
        logger.error("Dashboard test 2")
        logger.warning("Dashboard test 3")
        
        # 显示仪表板
        logger.show_log_dashboard()
        
        # 验证控制台被调用
        assert mock_console.called
    
    def test_concurrent_logging(self, logger):
        """测试并发日志记录"""
        import threading
        
        def log_worker(worker_id):
            for i in range(10):
                logger.info(f"Worker {worker_id} - Message {i}")
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证所有日志都被记录
        assert len(logger.recent_logs) == 50
    
    def test_memory_efficiency(self, logger):
        """测试内存效率（最近日志数量限制）"""
        # 创建超过限制的日志条目
        for i in range(1500):  # 超过maxlen=1000的限制
            logger.info(f"Memory test {i}")
        
        # 验证只保留最新的1000条
        assert len(logger.recent_logs) == 1000
        
        # 验证是最新的日志
        assert "Memory test 1499" in logger.recent_logs[-1].message
        assert "Memory test 500" in logger.recent_logs[0].message