"""
异常告警系统
实现智能异常检测、告警分级、通知机制和告警历史管理
"""

import time
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
from pathlib import Path

# 邮件相关导入（如果需要邮件功能）
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .structured_logger import LogLevel, LogCategory, LogEntry


class AlertSeverity(Enum):
    """告警严重程度"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "激活"
    ACKNOWLEDGED = "已确认"
    RESOLVED = "已解决"
    SUPPRESSED = "已抑制"


class NotificationChannel(Enum):
    """通知渠道"""
    CONSOLE = "控制台"
    FILE = "文件"
    EMAIL = "邮件"
    WEBHOOK = "webhook"


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    description: str
    conditions: Dict[str, Any]  # 触发条件
    severity: AlertSeverity
    enabled: bool = True
    cooldown_seconds: int = 300  # 冷却时间（秒）
    max_alerts_per_hour: int = 10
    notification_channels: List[NotificationChannel] = field(default_factory=list)
    custom_message_template: Optional[str] = None


@dataclass 
class Alert:
    """告警实例"""
    alert_id: str
    rule: AlertRule
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    details: Dict[str, Any]
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    count: int = 1  # 重复次数
    last_occurrence: datetime = field(default_factory=datetime.now)


@dataclass
class NotificationConfig:
    """通知配置"""
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_recipients: List[str] = field(default_factory=list)
    webhook_urls: List[str] = field(default_factory=list)
    file_path: str = "logs/alerts.log"


class AlertDetector:
    """告警检测器"""
    
    def __init__(self):
        self.patterns = {
            'error_spike': self._detect_error_spike,
            'performance_degradation': self._detect_performance_degradation,
            'resource_exhaustion': self._detect_resource_exhaustion,
            'suspicious_activity': self._detect_suspicious_activity,
            'service_unavailable': self._detect_service_unavailable
        }
    
    def _detect_error_spike(self, logs: List[LogEntry], time_window: int = 300) -> Optional[Dict[str, Any]]:
        """检测错误峰值"""
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=time_window)
        
        # 统计时间窗口内的错误
        error_logs = [
            log for log in logs
            if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
            and log.timestamp >= window_start
        ]
        
        error_count = len(error_logs)
        threshold = 10  # 5分钟内超过10个错误
        
        if error_count > threshold:
            return {
                'pattern': 'error_spike',
                'error_count': error_count,
                'time_window': time_window,
                'threshold': threshold,
                'sample_errors': [log.message for log in error_logs[:3]]
            }
        
        return None
    
    def _detect_performance_degradation(self, logs: List[LogEntry], 
                                      time_window: int = 600) -> Optional[Dict[str, Any]]:
        """检测性能降级"""
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=time_window)
        
        # 查找性能相关日志
        perf_logs = [
            log for log in logs
            if log.category == LogCategory.PERFORMANCE
            and log.duration is not None
            and log.timestamp >= window_start
        ]
        
        if len(perf_logs) < 5:
            return None
        
        # 计算平均响应时间
        avg_duration = sum(log.duration for log in perf_logs) / len(perf_logs)
        max_duration = max(log.duration for log in perf_logs)
        
        # 性能阈值
        if avg_duration > 5.0 or max_duration > 30.0:
            return {
                'pattern': 'performance_degradation',
                'avg_duration': avg_duration,
                'max_duration': max_duration,
                'sample_count': len(perf_logs),
                'threshold_avg': 5.0,
                'threshold_max': 30.0
            }
        
        return None
    
    def _detect_resource_exhaustion(self, system_metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """检测资源耗尽"""
        alerts = []
        
        if system_metrics.get('cpu_usage', 0) > 90:
            alerts.append('CPU使用率过高')
        
        if system_metrics.get('memory_usage', 0) > 95:
            alerts.append('内存使用率过高')
        
        if system_metrics.get('disk_usage', 0) > 98:
            alerts.append('磁盘空间不足')
        
        if alerts:
            return {
                'pattern': 'resource_exhaustion',
                'alerts': alerts,
                'metrics': system_metrics
            }
        
        return None
    
    def _detect_suspicious_activity(self, logs: List[LogEntry]) -> Optional[Dict[str, Any]]:
        """检测可疑活动"""
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=10)
        
        # 查找安全相关日志
        security_logs = [
            log for log in logs
            if log.category == LogCategory.SECURITY
            and log.timestamp >= window_start
        ]
        
        if len(security_logs) > 5:
            return {
                'pattern': 'suspicious_activity',
                'security_events': len(security_logs),
                'sample_events': [log.message for log in security_logs[:3]]
            }
        
        return None
    
    def _detect_service_unavailable(self, logs: List[LogEntry]) -> Optional[Dict[str, Any]]:
        """检测服务不可用"""
        current_time = datetime.now()
        window_start = current_time - timedelta(minutes=5)
        
        # 查找连接失败的日志
        failure_logs = [
            log for log in logs
            if ('连接失败' in log.message or 'connection failed' in log.message.lower()
                or '服务不可用' in log.message or 'service unavailable' in log.message.lower())
            and log.timestamp >= window_start
        ]
        
        if len(failure_logs) > 3:
            return {
                'pattern': 'service_unavailable',
                'failure_count': len(failure_logs),
                'failures': [log.message for log in failure_logs]
            }
        
        return None
    
    def detect_anomalies(self, logs: List[LogEntry], 
                        system_metrics: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """检测异常"""
        anomalies = []
        
        # 基于日志的检测
        for pattern_name, detector in self.patterns.items():
            try:
                if pattern_name == 'resource_exhaustion' and system_metrics:
                    result = detector(system_metrics)
                else:
                    result = detector(logs)
                
                if result:
                    anomalies.append(result)
            except Exception as e:
                print(f"Error in {pattern_name} detector: {e}")
        
        return anomalies


class AlertManager:
    """告警管理器"""
    
    def __init__(self, config: NotificationConfig = None):
        self.config = config or NotificationConfig()
        self.console = Console()
        
        # 告警存储
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_rules: Dict[str, AlertRule] = {}
        
        # 统计信息
        self.alert_stats = defaultdict(int)
        
        # 冷却时间追踪
        self.rule_cooldowns: Dict[str, datetime] = {}
        self.hourly_counts: Dict[str, List[datetime]] = defaultdict(list)
        
        # 检测器
        self.detector = AlertDetector()
        
        # 线程控制
        self._lock = threading.Lock()
        
        # 初始化默认规则
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                rule_id="error_spike",
                name="错误峰值告警",
                description="短时间内错误数量激增",
                conditions={"pattern": "error_spike"},
                severity=AlertSeverity.HIGH,
                notification_channels=[NotificationChannel.CONSOLE, NotificationChannel.FILE]
            ),
            AlertRule(
                rule_id="performance_degradation",
                name="性能降级告警",
                description="系统性能明显下降",
                conditions={"pattern": "performance_degradation"},
                severity=AlertSeverity.MEDIUM,
                notification_channels=[NotificationChannel.CONSOLE, NotificationChannel.FILE]
            ),
            AlertRule(
                rule_id="resource_exhaustion",
                name="资源耗尽告警",
                description="系统资源使用率过高",
                conditions={"pattern": "resource_exhaustion"},
                severity=AlertSeverity.CRITICAL,
                notification_channels=[NotificationChannel.CONSOLE, NotificationChannel.FILE, NotificationChannel.EMAIL]
            ),
            AlertRule(
                rule_id="security_alert",
                name="安全告警",
                description="检测到可疑的安全活动",
                conditions={"pattern": "suspicious_activity"},
                severity=AlertSeverity.HIGH,
                notification_channels=[NotificationChannel.CONSOLE, NotificationChannel.FILE, NotificationChannel.EMAIL]
            ),
            AlertRule(
                rule_id="service_unavailable", 
                name="服务不可用告警",
                description="关键服务无法访问",
                conditions={"pattern": "service_unavailable"},
                severity=AlertSeverity.CRITICAL,
                notification_channels=[NotificationChannel.CONSOLE, NotificationChannel.FILE, NotificationChannel.EMAIL]
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        with self._lock:
            self.alert_rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        with self._lock:
            self.alert_rules.pop(rule_id, None)
    
    def enable_rule(self, rule_id: str):
        """启用告警规则"""
        with self._lock:
            if rule_id in self.alert_rules:
                self.alert_rules[rule_id].enabled = True
    
    def disable_rule(self, rule_id: str):
        """禁用告警规则"""
        with self._lock:
            if rule_id in self.alert_rules:
                self.alert_rules[rule_id].enabled = False
    
    def _should_suppress_alert(self, rule: AlertRule) -> bool:
        """判断是否应该抑制告警"""
        current_time = datetime.now()
        
        # 检查冷却时间
        if rule.rule_id in self.rule_cooldowns:
            cooldown_end = self.rule_cooldowns[rule.rule_id] + timedelta(seconds=rule.cooldown_seconds)
            if current_time < cooldown_end:
                return True
        
        # 检查小时内告警次数限制
        hour_start = current_time.replace(minute=0, second=0, microsecond=0)
        recent_alerts = [
            alert_time for alert_time in self.hourly_counts[rule.rule_id]
            if alert_time >= hour_start
        ]
        
        if len(recent_alerts) >= rule.max_alerts_per_hour:
            return True
        
        return False
    
    def _create_alert(self, rule: AlertRule, detection_result: Dict[str, Any]) -> Alert:
        """创建告警"""
        alert_id = f"{rule.rule_id}_{int(time.time())}"
        
        # 生成告警消息
        if rule.custom_message_template:
            message = rule.custom_message_template.format(**detection_result)
        else:
            message = f"{rule.description}: {detection_result}"
        
        alert = Alert(
            alert_id=alert_id,
            rule=rule,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            title=rule.name,
            message=message,
            details=detection_result,
            triggered_at=datetime.now()
        )
        
        return alert
    
    def _send_notifications(self, alert: Alert):
        """发送通知"""
        for channel in alert.rule.notification_channels:
            try:
                if channel == NotificationChannel.CONSOLE:
                    self._send_console_notification(alert)
                elif channel == NotificationChannel.FILE:
                    self._send_file_notification(alert)
                elif channel == NotificationChannel.EMAIL:
                    self._send_email_notification(alert)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_webhook_notification(alert)
            except Exception as e:
                print(f"Failed to send {channel.value} notification: {e}")
    
    def _send_console_notification(self, alert: Alert):
        """发送控制台通知"""
        severity_colors = {
            AlertSeverity.LOW: "green",
            AlertSeverity.MEDIUM: "yellow", 
            AlertSeverity.HIGH: "red",
            AlertSeverity.CRITICAL: "bold red"
        }
        
        severity_icons = {
            AlertSeverity.LOW: "ℹ️",
            AlertSeverity.MEDIUM: "⚠️",
            AlertSeverity.HIGH: "🚨",
            AlertSeverity.CRITICAL: "🔥"
        }
        
        color = severity_colors.get(alert.severity, "white")
        icon = severity_icons.get(alert.severity, "📢")
        
        alert_text = Text()
        alert_text.append(f"{icon} ", style="bold")
        alert_text.append(f"[{alert.severity.value}] ", style=f"bold {color}")
        alert_text.append(alert.title, style="bold white")
        alert_text.append("\n")
        alert_text.append(alert.message, style=color)
        
        panel = Panel(
            alert_text,
            title=f"告警 - {alert.alert_id}",
            border_style=color,
            title_align="left"
        )
        
        self.console.print(panel)
    
    def _send_file_notification(self, alert: Alert):
        """发送文件通知"""
        log_entry = {
            "timestamp": alert.triggered_at.isoformat(),
            "alert_id": alert.alert_id,
            "rule_id": alert.rule.rule_id,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "details": alert.details
        }
        
        log_file = Path(self.config.file_path)
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def _send_email_notification(self, alert: Alert):
        """发送邮件通知"""
        if not EMAIL_AVAILABLE:
            print("Email functionality not available")
            return
            
        if not self.config.email_recipients:
            return
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.config.email_username
            msg['To'] = ', '.join(self.config.email_recipients)
            msg['Subject'] = f"[{alert.severity.value}] {alert.title}"
            
            body = f"""
告警ID: {alert.alert_id}
告警规则: {alert.rule.name}
严重程度: {alert.severity.value}
触发时间: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

告警信息:
{alert.message}

详细信息:
{json.dumps(alert.details, ensure_ascii=False, indent=2)}
            """
            
            msg.attach(MimeText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.config.email_smtp_host, self.config.email_smtp_port)
            server.starttls()
            server.login(self.config.email_username, self.config.email_password)
            text = msg.as_string()
            server.sendmail(self.config.email_username, self.config.email_recipients, text)
            server.quit()
            
        except Exception as e:
            print(f"Failed to send email notification: {e}")
    
    def _send_webhook_notification(self, alert: Alert):
        """发送webhook通知"""
        # TODO: 实现webhook通知
        pass
    
    def process_detections(self, logs: List[LogEntry], system_metrics: Dict[str, Any] = None):
        """处理检测结果"""
        # 检测异常
        anomalies = self.detector.detect_anomalies(logs, system_metrics)
        
        for anomaly in anomalies:
            pattern = anomaly.get('pattern')
            
            # 查找匹配的规则
            matching_rules = [
                rule for rule in self.alert_rules.values()
                if rule.enabled and rule.conditions.get('pattern') == pattern
            ]
            
            for rule in matching_rules:
                # 检查是否应该抑制
                if self._should_suppress_alert(rule):
                    continue
                
                # 创建告警
                alert = self._create_alert(rule, anomaly)
                
                with self._lock:
                    # 检查是否已有相同的活跃告警
                    existing_alert = None
                    for active_alert in self.active_alerts.values():
                        if (active_alert.rule.rule_id == rule.rule_id and
                            active_alert.status == AlertStatus.ACTIVE):
                            existing_alert = active_alert
                            break
                    
                    if existing_alert:
                        # 更新现有告警
                        existing_alert.count += 1
                        existing_alert.last_occurrence = datetime.now()
                    else:
                        # 添加新告警
                        self.active_alerts[alert.alert_id] = alert
                        self.alert_history.append(alert)
                        
                        # 更新统计
                        self.alert_stats[alert.severity.value] += 1
                        self.alert_stats['total'] += 1
                        
                        # 更新冷却时间和计数
                        self.rule_cooldowns[rule.rule_id] = datetime.now()
                        self.hourly_counts[rule.rule_id].append(datetime.now())
                        
                        # 发送通知
                        self._send_notifications(alert)
    
    def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """确认告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = datetime.now()
                return True
        return False
    
    def resolve_alert(self, alert_id: str, user: str = "system"):
        """解决告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()
                # 从活跃告警中移除
                del self.active_alerts[alert_id]
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        with self._lock:
            return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """获取告警历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alert_history
            if alert.triggered_at >= cutoff_time
        ]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        with self._lock:
            return {
                'total_alerts': self.alert_stats.get('total', 0),
                'active_alerts': len(self.active_alerts),
                'severity_breakdown': {
                    severity.value: self.alert_stats.get(severity.value, 0)
                    for severity in AlertSeverity
                },
                'rules_configured': len(self.alert_rules),
                'rules_enabled': len([r for r in self.alert_rules.values() if r.enabled])
            }
    
    def show_alert_dashboard(self):
        """显示告警仪表板"""
        self.console.print("\n" + "="*80, style="red")
        self.console.print("🚨 告警仪表板", style="bold red", justify="center")
        self.console.print("="*80, style="red")
        
        # 活跃告警
        active_alerts = self.get_active_alerts()
        if active_alerts:
            alert_table = Table(title="活跃告警", show_header=True, header_style="bold red")
            alert_table.add_column("告警ID", style="cyan", width=20)
            alert_table.add_column("规则", style="white", width=20)
            alert_table.add_column("严重程度", style="red", width=10)
            alert_table.add_column("触发时间", style="dim", width=15)
            alert_table.add_column("次数", style="yellow", width=8)
            
            for alert in active_alerts[:10]:  # 显示前10个
                severity_color = {
                    AlertSeverity.LOW: "green",
                    AlertSeverity.MEDIUM: "yellow",
                    AlertSeverity.HIGH: "red", 
                    AlertSeverity.CRITICAL: "bold red"
                }.get(alert.severity, "white")
                
                alert_table.add_row(
                    alert.alert_id[:18] + "..." if len(alert.alert_id) > 20 else alert.alert_id,
                    alert.rule.name[:18] + "..." if len(alert.rule.name) > 20 else alert.rule.name,
                    f"[{severity_color}]{alert.severity.value}[/{severity_color}]",
                    alert.triggered_at.strftime("%m-%d %H:%M"),
                    str(alert.count)
                )
            
            self.console.print(alert_table)
        else:
            self.console.print("✅ 当前没有活跃告警", style="green")
        
        # 统计信息
        stats = self.get_alert_statistics()
        stats_table = Table(title="告警统计", show_header=True, header_style="bold magenta")
        stats_table.add_column("项目", style="cyan", width=20)
        stats_table.add_column("数值", style="white", width=15)
        
        stats_table.add_row("总告警数", str(stats['total_alerts']))
        stats_table.add_row("活跃告警", str(stats['active_alerts']))
        stats_table.add_row("已配置规则", str(stats['rules_configured']))
        stats_table.add_row("已启用规则", str(stats['rules_enabled']))
        
        for severity, count in stats['severity_breakdown'].items():
            stats_table.add_row(f"{severity}告警", str(count))
        
        self.console.print(stats_table)