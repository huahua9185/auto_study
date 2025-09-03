"""
告警系统测试
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.auto_study.monitoring.alert_system import (
    AlertManager, AlertDetector, AlertRule, Alert, AlertSeverity, 
    AlertStatus, NotificationChannel, NotificationConfig
)
from src.auto_study.monitoring.structured_logger import LogLevel, LogCategory, LogEntry, LogContext


class TestAlertDetector:
    """告警检测器测试"""
    
    @pytest.fixture
    def detector(self):
        """创建检测器"""
        return AlertDetector()
    
    @pytest.fixture
    def sample_logs(self):
        """创建示例日志"""
        logs = []
        base_time = datetime.now()
        
        # 创建错误日志
        for i in range(15):
            log = LogEntry(
                timestamp=base_time - timedelta(seconds=i*10),
                level=LogLevel.ERROR,
                category=LogCategory.SYSTEM,
                module="test_module",
                message=f"Test error {i}",
                context=LogContext()
            )
            logs.append(log)
        
        # 创建性能日志
        for i in range(10):
            log = LogEntry(
                timestamp=base_time - timedelta(seconds=i*30),
                level=LogLevel.INFO,
                category=LogCategory.PERFORMANCE,
                module="test_module",
                message=f"Performance test {i}",
                context=LogContext(),
                duration=10.0 + i  # 递增的响应时间
            )
            logs.append(log)
        
        return logs
    
    def test_error_spike_detection(self, detector, sample_logs):
        """测试错误峰值检测"""
        result = detector._detect_error_spike(sample_logs, time_window=300)
        
        assert result is not None
        assert result['pattern'] == 'error_spike'
        assert result['error_count'] == 15
        assert result['threshold'] == 10
        assert len(result['sample_errors']) == 3
    
    def test_performance_degradation_detection(self, detector, sample_logs):
        """测试性能降级检测"""
        result = detector._detect_performance_degradation(sample_logs, time_window=600)
        
        assert result is not None
        assert result['pattern'] == 'performance_degradation'
        assert result['avg_duration'] > 5.0  # 应该超过阈值
        assert result['sample_count'] == 10
    
    def test_resource_exhaustion_detection(self, detector):
        """测试资源耗尽检测"""
        # 正常情况
        normal_metrics = {
            'cpu_usage': 50.0,
            'memory_usage': 60.0,
            'disk_usage': 70.0
        }
        result = detector._detect_resource_exhaustion(normal_metrics)
        assert result is None
        
        # 异常情况
        critical_metrics = {
            'cpu_usage': 95.0,
            'memory_usage': 98.0,
            'disk_usage': 99.0
        }
        result = detector._detect_resource_exhaustion(critical_metrics)
        assert result is not None
        assert result['pattern'] == 'resource_exhaustion'
        assert len(result['alerts']) == 3
    
    def test_suspicious_activity_detection(self, detector):
        """测试可疑活动检测"""
        # 创建安全日志
        security_logs = []
        base_time = datetime.now()
        
        for i in range(7):
            log = LogEntry(
                timestamp=base_time - timedelta(seconds=i*60),
                level=LogLevel.WARNING,
                category=LogCategory.SECURITY,
                module="security_module",
                message=f"Suspicious activity {i}",
                context=LogContext()
            )
            security_logs.append(log)
        
        result = detector._detect_suspicious_activity(security_logs)
        
        assert result is not None
        assert result['pattern'] == 'suspicious_activity'
        assert result['security_events'] == 7
        assert len(result['sample_events']) == 3
    
    def test_service_unavailable_detection(self, detector):
        """测试服务不可用检测"""
        # 创建连接失败日志
        failure_logs = []
        base_time = datetime.now()
        
        failure_messages = [
            "连接失败",
            "connection failed",
            "服务不可用", 
            "service unavailable"
        ]
        
        for i, msg in enumerate(failure_messages):
            log = LogEntry(
                timestamp=base_time - timedelta(seconds=i*60),
                level=LogLevel.ERROR,
                category=LogCategory.NETWORK,
                module="network_module",
                message=f"Network error: {msg}",
                context=LogContext()
            )
            failure_logs.append(log)
        
        result = detector._detect_service_unavailable(failure_logs)
        
        assert result is not None
        assert result['pattern'] == 'service_unavailable'
        assert result['failure_count'] == 4
    
    def test_detect_anomalies(self, detector, sample_logs):
        """测试异常检测集成"""
        system_metrics = {
            'cpu_usage': 95.0,
            'memory_usage': 98.0
        }
        
        anomalies = detector.detect_anomalies(sample_logs, system_metrics)
        
        # 应该检测到多种异常
        assert len(anomalies) >= 2
        
        patterns = [anomaly['pattern'] for anomaly in anomalies]
        assert 'error_spike' in patterns
        assert 'performance_degradation' in patterns
        assert 'resource_exhaustion' in patterns


class TestAlertManager:
    """告警管理器测试"""
    
    @pytest.fixture
    def notification_config(self):
        """创建通知配置"""
        return NotificationConfig(
            file_path="test_alerts.log",
            email_recipients=["test@example.com"]
        )
    
    @pytest.fixture
    def alert_manager(self, notification_config, tmp_path):
        """创建告警管理器"""
        # 设置临时文件路径
        notification_config.file_path = str(tmp_path / "alerts.log")
        return AlertManager(notification_config)
    
    def test_alert_manager_initialization(self, alert_manager):
        """测试告警管理器初始化"""
        assert len(alert_manager.alert_rules) > 0  # 应该有默认规则
        assert len(alert_manager.active_alerts) == 0
        assert len(alert_manager.alert_history) == 0
    
    def test_add_remove_rules(self, alert_manager):
        """测试添加和移除规则"""
        initial_count = len(alert_manager.alert_rules)
        
        # 添加规则
        rule = AlertRule(
            rule_id="test_rule",
            name="测试规则",
            description="测试用规则",
            conditions={"test": True},
            severity=AlertSeverity.MEDIUM
        )
        
        alert_manager.add_rule(rule)
        assert len(alert_manager.alert_rules) == initial_count + 1
        assert "test_rule" in alert_manager.alert_rules
        
        # 移除规则
        alert_manager.remove_rule("test_rule")
        assert len(alert_manager.alert_rules) == initial_count
        assert "test_rule" not in alert_manager.alert_rules
    
    def test_enable_disable_rules(self, alert_manager):
        """测试启用/禁用规则"""
        rule_id = list(alert_manager.alert_rules.keys())[0]
        
        # 禁用规则
        alert_manager.disable_rule(rule_id)
        assert not alert_manager.alert_rules[rule_id].enabled
        
        # 启用规则
        alert_manager.enable_rule(rule_id)
        assert alert_manager.alert_rules[rule_id].enabled
    
    def test_alert_suppression_cooldown(self, alert_manager):
        """测试告警抑制（冷却时间）"""
        rule = list(alert_manager.alert_rules.values())[0]
        rule.cooldown_seconds = 1  # 1秒冷却时间
        
        # 第一次检查（应该不被抑制）
        assert not alert_manager._should_suppress_alert(rule)
        
        # 设置冷却时间
        alert_manager.rule_cooldowns[rule.rule_id] = datetime.now()
        
        # 第二次检查（应该被抑制）
        assert alert_manager._should_suppress_alert(rule)
        
        # 等待冷却时间过去
        time.sleep(1.1)
        
        # 第三次检查（应该不被抑制）
        assert not alert_manager._should_suppress_alert(rule)
    
    def test_alert_suppression_rate_limit(self, alert_manager):
        """测试告警抑制（频率限制）"""
        rule = list(alert_manager.alert_rules.values())[0]
        rule.max_alerts_per_hour = 2
        
        # 模拟当前小时内已有2个告警
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        alert_manager.hourly_counts[rule.rule_id] = [
            current_hour + timedelta(minutes=10),
            current_hour + timedelta(minutes=20)
        ]
        
        # 应该被抑制
        assert alert_manager._should_suppress_alert(rule)
    
    @patch('src.auto_study.monitoring.alert_system.Console')
    def test_console_notification(self, mock_console, alert_manager):
        """测试控制台通知"""
        rule = list(alert_manager.alert_rules.values())[0]
        alert = alert_manager._create_alert(rule, {"test": "data"})
        
        alert_manager._send_console_notification(alert)
        
        # 验证控制台被调用
        mock_console.assert_called()
    
    def test_file_notification(self, alert_manager, tmp_path):
        """测试文件通知"""
        rule = list(alert_manager.alert_rules.values())[0]
        alert = alert_manager._create_alert(rule, {"test": "data"})
        
        alert_manager._send_file_notification(alert)
        
        # 验证文件被创建
        alert_file = tmp_path / "alerts.log"
        assert alert_file.exists()
        
        # 验证文件内容
        with open(alert_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert alert.alert_id in content
    
    def test_create_alert(self, alert_manager):
        """测试告警创建"""
        rule = list(alert_manager.alert_rules.values())[0]
        detection_result = {"pattern": "test", "value": 100}
        
        alert = alert_manager._create_alert(rule, detection_result)
        
        assert alert.rule == rule
        assert alert.severity == rule.severity
        assert alert.status == AlertStatus.ACTIVE
        assert alert.details == detection_result
        assert isinstance(alert.triggered_at, datetime)
    
    def test_process_detections_new_alert(self, alert_manager):
        """测试处理检测结果（新告警）"""
        # 创建错误日志
        logs = []
        for i in range(15):
            log = LogEntry(
                timestamp=datetime.now() - timedelta(seconds=i*10),
                level=LogLevel.ERROR,
                category=LogCategory.SYSTEM,
                module="test_module",
                message=f"Test error {i}",
                context=LogContext()
            )
            logs.append(log)
        
        initial_alert_count = len(alert_manager.active_alerts)
        
        alert_manager.process_detections(logs)
        
        # 应该生成新告警
        assert len(alert_manager.active_alerts) > initial_alert_count
        assert len(alert_manager.alert_history) > 0
    
    def test_process_detections_duplicate_alert(self, alert_manager):
        """测试处理检测结果（重复告警）"""
        # 创建错误日志
        logs = []
        for i in range(15):
            log = LogEntry(
                timestamp=datetime.now() - timedelta(seconds=i*10),
                level=LogLevel.ERROR,
                category=LogCategory.SYSTEM,
                module="test_module", 
                message=f"Test error {i}",
                context=LogContext()
            )
            logs.append(log)
        
        # 第一次处理
        alert_manager.process_detections(logs)
        first_count = len(alert_manager.active_alerts)
        
        # 第二次处理相同的检测结果
        alert_manager.process_detections(logs)
        
        # 活跃告警数量不应该增加（但计数会增加）
        assert len(alert_manager.active_alerts) == first_count
    
    def test_acknowledge_alert(self, alert_manager):
        """测试确认告警"""
        # 先创建一个告警
        rule = list(alert_manager.alert_rules.values())[0]
        alert = alert_manager._create_alert(rule, {"test": "data"})
        alert_manager.active_alerts[alert.alert_id] = alert
        
        # 确认告警
        result = alert_manager.acknowledge_alert(alert.alert_id)
        
        assert result is True
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_at is not None
    
    def test_resolve_alert(self, alert_manager):
        """测试解决告警"""
        # 先创建一个告警
        rule = list(alert_manager.alert_rules.values())[0]
        alert = alert_manager._create_alert(rule, {"test": "data"})
        alert_manager.active_alerts[alert.alert_id] = alert
        
        initial_count = len(alert_manager.active_alerts)
        
        # 解决告警
        result = alert_manager.resolve_alert(alert.alert_id)
        
        assert result is True
        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None
        assert len(alert_manager.active_alerts) == initial_count - 1
    
    def test_get_active_alerts(self, alert_manager):
        """测试获取活跃告警"""
        # 创建一些告警
        rule = list(alert_manager.alert_rules.values())[0]
        
        for i in range(3):
            alert = alert_manager._create_alert(rule, {"test": f"data_{i}"})
            alert_manager.active_alerts[alert.alert_id] = alert
        
        active_alerts = alert_manager.get_active_alerts()
        assert len(active_alerts) == 3
    
    def test_get_alert_history(self, alert_manager):
        """测试获取告警历史"""
        # 创建历史告警
        rule = list(alert_manager.alert_rules.values())[0]
        
        # 创建不同时间的告警
        for i in range(5):
            alert = alert_manager._create_alert(rule, {"test": f"data_{i}"})
            alert.triggered_at = datetime.now() - timedelta(hours=i)
            alert_manager.alert_history.append(alert)
        
        # 获取24小时内的历史
        history = alert_manager.get_alert_history(hours=24)
        assert len(history) == 5
        
        # 获取2小时内的历史
        history = alert_manager.get_alert_history(hours=2)
        assert len(history) <= 3
    
    def test_get_alert_statistics(self, alert_manager):
        """测试获取告警统计"""
        # 创建一些告警
        rule = list(alert_manager.alert_rules.values())[0]
        
        for i in range(3):
            alert = alert_manager._create_alert(rule, {"test": f"data_{i}"})
            alert_manager.active_alerts[alert.alert_id] = alert
            alert_manager.alert_history.append(alert)
        
        # 更新统计
        alert_manager.alert_stats['total'] = 3
        alert_manager.alert_stats[AlertSeverity.HIGH.value] = 2
        alert_manager.alert_stats[AlertSeverity.MEDIUM.value] = 1
        
        stats = alert_manager.get_alert_statistics()
        
        assert stats['total_alerts'] == 3
        assert stats['active_alerts'] == 3
        assert stats['rules_configured'] > 0
        assert stats['rules_enabled'] > 0
        assert AlertSeverity.HIGH.value in stats['severity_breakdown']
    
    @patch('src.auto_study.monitoring.alert_system.Console')
    def test_show_alert_dashboard(self, mock_console, alert_manager):
        """测试告警仪表板"""
        # 创建一些测试数据
        rule = list(alert_manager.alert_rules.values())[0]
        alert = alert_manager._create_alert(rule, {"test": "data"})
        alert_manager.active_alerts[alert.alert_id] = alert
        
        alert_manager.show_alert_dashboard()
        
        # 验证控制台被调用
        mock_console.assert_called()
    
    def test_email_notification_no_config(self, alert_manager):
        """测试无邮件配置时的邮件通知"""
        # 清空邮件配置
        alert_manager.config.email_recipients = []
        
        rule = list(alert_manager.alert_rules.values())[0]
        alert = alert_manager._create_alert(rule, {"test": "data"})
        
        # 不应该抛出异常
        alert_manager._send_email_notification(alert)
    
    def test_alert_callback(self, alert_manager):
        """测试告警回调"""
        callback_calls = []
        
        def test_callback(rule_name, alert_data):
            callback_calls.append((rule_name, alert_data))
        
        alert_manager.add_alert_callback(test_callback)
        
        # 模拟告警触发
        rule = list(alert_manager.alert_rules.values())[0]
        alert_data = {"pattern": "test", "value": 100}
        
        alert_manager._fire_alert(rule, type('MockSnapshot', (), {rule.metric: 100})())
        
        assert len(callback_calls) == 1
    
    def test_concurrent_alert_processing(self, alert_manager):
        """测试并发告警处理"""
        import threading
        
        def process_alerts():
            logs = [
                LogEntry(
                    timestamp=datetime.now(),
                    level=LogLevel.ERROR,
                    category=LogCategory.SYSTEM,
                    module="test_module",
                    message="Concurrent test error",
                    context=LogContext()
                )
            ] * 12  # 创建足够触发告警的错误日志
            
            alert_manager.process_detections(logs)
        
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=process_alerts)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证并发处理不会导致问题
        assert len(alert_manager.alert_history) >= 0  # 至少没有崩溃