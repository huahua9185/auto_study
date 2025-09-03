"""
监控管理器
统一管理所有监控组件，提供简化的监控接口
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from contextlib import contextmanager

from .ui_panel import MonitoringUI, TaskStatus, SystemMetrics
from .status_monitor import StatusMonitor
from .structured_logger import StructuredLogger, LogLevel, LogCategory, LogContext
from .alert_system import AlertManager, NotificationConfig, AlertSeverity


class MonitoringManager:
    """监控管理器 - 统一的监控系统接口"""
    
    def __init__(self, 
                 log_dir: str = "logs",
                 notification_config: NotificationConfig = None,
                 enable_ui: bool = True,
                 enable_alerts: bool = True):
        
        # 初始化组件
        self.logger = StructuredLogger(log_dir=log_dir)
        self.status_monitor = StatusMonitor(update_interval=1.0)
        self.ui = MonitoringUI() if enable_ui else None
        self.alert_manager = AlertManager(notification_config) if enable_alerts else None
        
        # 状态管理
        self._is_running = False
        self._monitor_thread = None
        self._ui_thread = None
        
        # 连接组件
        self._setup_integrations()
    
    def _setup_integrations(self):
        """设置组件间的集成"""
        # 状态监控器回调 -> UI更新
        if self.ui:
            self.status_monitor.add_status_callback(self.ui.update_system_metrics)
        
        # 状态监控器回调 -> 告警检测
        if self.alert_manager:
            self.status_monitor.add_alert_callback(self._handle_system_alert)
        
        # 日志处理器 -> UI日志显示
        if self.ui:
            self.logger.add_handler(self._log_to_ui)
        
        # 日志处理器 -> 告警检测
        if self.alert_manager:
            self.logger.add_handler(self._log_to_alert_detection)
    
    def _handle_system_alert(self, alert_name: str, alert_data: Dict[str, Any]):
        """处理系统告警"""
        self.logger.warning(
            f"系统告警: {alert_name}",
            category=LogCategory.SYSTEM,
            alert_data=alert_data
        )
    
    def _log_to_ui(self, log_entry):
        """将日志发送到UI"""
        if self.ui:
            self.ui.add_log(
                level=log_entry.level.value,
                message=log_entry.message,
                timestamp=log_entry.timestamp
            )
    
    def _log_to_alert_detection(self, log_entry):
        """将日志发送到告警检测"""
        # 这里可以实现更复杂的日志到告警的转换逻辑
        pass
    
    def start(self):
        """启动监控系统"""
        if self._is_running:
            return
        
        self._is_running = True
        
        # 启动状态监控
        self.status_monitor.start()
        
        # 启动UI线程
        if self.ui:
            self._ui_thread = threading.Thread(target=self._run_ui, daemon=True)
            self._ui_thread.start()
        
        # 启动监控检测循环
        self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        self.logger.info("监控系统已启动", category=LogCategory.SYSTEM)
    
    def stop(self):
        """停止监控系统"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # 停止状态监控
        self.status_monitor.stop()
        
        # 停止UI
        if self.ui:
            self.ui.stop_monitoring()
        
        self.logger.info("监控系统已停止", category=LogCategory.SYSTEM)
    
    def _run_ui(self):
        """运行UI界面"""
        try:
            self.ui.start_monitoring()
        except Exception as e:
            self.logger.error(f"UI运行错误: {e}", category=LogCategory.SYSTEM, exception=e)
    
    def _monitoring_loop(self):
        """监控检测循环"""
        while self._is_running:
            try:
                if self.alert_manager:
                    # 获取最近的日志和系统指标
                    recent_logs = self.logger.get_recent_logs(100)
                    system_metrics = self.status_monitor.get_current_metrics()
                    
                    # 转换系统指标格式
                    metrics_dict = {
                        'cpu_usage': system_metrics.cpu_usage,
                        'memory_usage': system_metrics.memory_usage,
                        'disk_usage': system_metrics.disk_usage,
                        'network_sent': system_metrics.network_sent,
                        'network_recv': system_metrics.network_recv,
                        'active_threads': system_metrics.active_threads
                    }
                    
                    # 执行告警检测
                    self.alert_manager.process_detections(recent_logs, metrics_dict)
                
                time.sleep(5)  # 每5秒检测一次
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}", category=LogCategory.SYSTEM, exception=e)
                time.sleep(10)
    
    @contextmanager
    def task_context(self, task_name: str, task_id: str = None):
        """任务上下文管理器"""
        if task_id is None:
            task_id = f"task_{int(time.time())}"
        
        # 开始任务
        if self.ui:
            self.ui.add_task(task_id, task_name)
            self.ui.update_task(task_id, status=TaskStatus.RUNNING)
        
        context = LogContext(task_id=task_id)
        start_time = time.time()
        
        self.logger.info(f"任务开始: {task_name}", LogCategory.AUTOMATION, context)
        
        try:
            yield task_id
            
            # 任务成功
            duration = time.time() - start_time
            if self.ui:
                self.ui.update_task(task_id, status=TaskStatus.SUCCESS, progress=100.0)
            
            self.logger.info(
                f"任务完成: {task_name}",
                LogCategory.AUTOMATION,
                context,
                duration=duration
            )
            
        except Exception as e:
            # 任务失败
            duration = time.time() - start_time
            if self.ui:
                self.ui.update_task(
                    task_id, 
                    status=TaskStatus.FAILED, 
                    error_message=str(e)
                )
            
            self.logger.error(
                f"任务失败: {task_name} - {str(e)}",
                LogCategory.AUTOMATION,
                context,
                exception=e,
                duration=duration
            )
            raise
    
    def update_task_progress(self, task_id: str, progress: float, message: str = ""):
        """更新任务进度"""
        if self.ui:
            self.ui.update_task(task_id, progress=progress)
        
        if message:
            context = LogContext(task_id=task_id)
            self.logger.info(f"任务进度 {progress:.1f}%: {message}", LogCategory.AUTOMATION, context)
    
    # 便捷的日志方法
    def log_info(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """记录信息日志"""
        self.logger.info(message, category, **kwargs)
    
    def log_warning(self, message: str, category: LogCategory = LogCategory.SYSTEM, **kwargs):
        """记录警告日志"""
        self.logger.warning(message, category, **kwargs)
    
    def log_error(self, message: str, category: LogCategory = LogCategory.SYSTEM, 
                  exception: Exception = None, **kwargs):
        """记录错误日志"""
        self.logger.error(message, category, exception=exception, **kwargs)
    
    def log_user_action(self, user_id: str, action: str, details: str = ""):
        """记录用户操作"""
        self.logger.log_user_action(user_id, action, details)
    
    def log_automation_step(self, task_id: str, step: str, status: str, duration: float = None):
        """记录自动化步骤"""
        self.logger.log_automation_step(task_id, step, status, duration)
    
    def log_browser_action(self, action: str, url: str = "", details: str = ""):
        """记录浏览器操作"""
        self.logger.log_browser_action(action, url, details)
    
    def log_network_request(self, method: str, url: str, status_code: int, 
                           duration: float, user_agent: str = None):
        """记录网络请求"""
        self.logger.log_network_request(method, url, status_code, duration, user_agent)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """记录性能指标"""
        self.logger.log_performance_metric(metric_name, value, unit)
    
    def log_security_event(self, event_type: str, description: str, 
                          ip_address: str = None, severity: str = "INFO"):
        """记录安全事件"""
        self.logger.log_security_event(event_type, description, ip_address, severity)
    
    # 告警管理方法
    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        if self.alert_manager:
            return self.alert_manager.acknowledge_alert(alert_id)
        return False
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        if self.alert_manager:
            return self.alert_manager.resolve_alert(alert_id)
        return False
    
    def get_active_alerts(self):
        """获取活跃告警"""
        if self.alert_manager:
            return self.alert_manager.get_active_alerts()
        return []
    
    # 统计和报告方法
    def show_dashboard(self):
        """显示监控仪表板"""
        if self.ui:
            self.ui.show_summary()
        
        self.logger.show_log_dashboard()
        
        if self.alert_manager:
            self.alert_manager.show_alert_dashboard()
    
    def export_data(self, file_path: str, hours: int = 24):
        """导出监控数据"""
        # 导出系统指标
        self.status_monitor.export_metrics(f"{file_path}_metrics.json", format="json")
        
        # 导出日志
        self.logger.export_logs(f"{file_path}_logs.json", hours=hours, format="json")
        
        self.logger.info(f"监控数据已导出到: {file_path}", category=LogCategory.SYSTEM)
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        performance_score = self.status_monitor.calculate_performance_score()
        health_status = self.status_monitor.get_system_health()
        
        log_stats = self.logger.get_log_statistics()
        error_count = log_stats.get('ERROR', 0) + log_stats.get('CRITICAL', 0)
        
        active_alerts = len(self.get_active_alerts()) if self.alert_manager else 0
        
        return {
            'performance_score': performance_score,
            'health_status': health_status,
            'error_count': error_count,
            'active_alerts': active_alerts,
            'system_metrics': self.status_monitor.get_current_metrics(),
            'timestamp': datetime.now().isoformat()
        }


# 全局监控管理器实例
monitoring_manager = MonitoringManager()