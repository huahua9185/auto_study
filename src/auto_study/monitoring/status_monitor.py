"""
实时状态监控系统
收集并管理系统状态数据
"""

import psutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
from pathlib import Path

from .ui_panel import SystemMetrics, TaskStatus, TaskInfo


@dataclass
class StatusSnapshot:
    """状态快照"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    active_threads: int
    active_tasks: int
    queue_size: int


@dataclass 
class AlertRule:
    """告警规则"""
    name: str
    metric: str  # 指标名称，如 'cpu_percent', 'memory_percent' 等
    threshold: float  # 阈值
    operator: str  # 操作符: '>', '<', '>=', '<=', '==', '!='
    duration: int  # 持续时间（秒）
    enabled: bool = True
    triggered: bool = False
    trigger_time: Optional[datetime] = None
    callback: Optional[Callable] = None


class StatusMonitor:
    """状态监控器"""
    
    def __init__(self, update_interval: float = 1.0, history_size: int = 300):
        self.update_interval = update_interval
        self.history_size = history_size
        
        # 状态数据
        self.current_metrics = SystemMetrics()
        self.history: deque[StatusSnapshot] = deque(maxlen=history_size)
        self.tasks: Dict[str, TaskInfo] = {}
        
        # 告警系统
        self.alert_rules: List[AlertRule] = []
        self.alert_history: List[Dict[str, Any]] = []
        
        # 线程控制
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # 网络统计
        self._last_network_stats = None
        
        # 回调函数
        self.status_update_callbacks: List[Callable[[SystemMetrics], None]] = []
        self.alert_callbacks: List[Callable[[str, Dict], None]] = []
        
        # 初始化默认告警规则
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """设置默认告警规则"""
        default_rules = [
            AlertRule(
                name="高CPU使用率",
                metric="cpu_percent",
                threshold=80.0,
                operator=">",
                duration=30
            ),
            AlertRule(
                name="高内存使用率",
                metric="memory_percent", 
                threshold=90.0,
                operator=">",
                duration=30
            ),
            AlertRule(
                name="磁盘空间不足",
                metric="disk_percent",
                threshold=95.0,
                operator=">",
                duration=60
            ),
            AlertRule(
                name="线程数过多",
                metric="active_threads",
                threshold=100,
                operator=">",
                duration=60
            )
        ]
        
        self.alert_rules.extend(default_rules)
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        with self._lock:
            self.alert_rules.append(rule)
    
    def remove_alert_rule(self, rule_name: str):
        """移除告警规则"""
        with self._lock:
            self.alert_rules = [rule for rule in self.alert_rules if rule.name != rule_name]
    
    def add_status_callback(self, callback: Callable[[SystemMetrics], None]):
        """添加状态更新回调"""
        self.status_update_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable[[str, Dict], None]):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 网络统计
            network_stats = psutil.net_io_counters()
            network_sent = network_stats.bytes_sent
            network_recv = network_stats.bytes_recv
            
            # 活跃线程数
            active_threads = threading.active_count()
            
            return SystemMetrics(
                cpu_usage=cpu_percent,
                memory_usage=memory_percent,
                disk_usage=disk_percent,
                network_sent=network_sent,
                network_recv=network_recv,
                active_threads=active_threads,
                last_updated=datetime.now()
            )
        except Exception as e:
            # 如果收集失败，返回默认值
            return SystemMetrics(last_updated=datetime.now())
    
    def _create_snapshot(self, metrics: SystemMetrics) -> StatusSnapshot:
        """创建状态快照"""
        return StatusSnapshot(
            timestamp=metrics.last_updated,
            cpu_percent=metrics.cpu_usage,
            memory_percent=metrics.memory_usage,
            disk_percent=metrics.disk_usage,
            network_sent=metrics.network_sent,
            network_recv=metrics.network_recv,
            active_threads=metrics.active_threads,
            active_tasks=len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
            queue_size=len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
        )
    
    def _check_alerts(self, snapshot: StatusSnapshot):
        """检查告警规则"""
        current_time = datetime.now()
        
        for rule in self.alert_rules:
            if not rule.enabled:
                continue
            
            # 获取指标值
            metric_value = getattr(snapshot, rule.metric, None)
            if metric_value is None:
                continue
            
            # 检查阈值
            triggered = self._evaluate_condition(metric_value, rule.threshold, rule.operator)
            
            if triggered:
                if not rule.triggered:
                    # 刚触发
                    rule.triggered = True
                    rule.trigger_time = current_time
                elif rule.trigger_time and (current_time - rule.trigger_time).total_seconds() >= rule.duration:
                    # 持续时间已达到
                    self._fire_alert(rule, snapshot)
                    # 重置触发状态以避免重复告警
                    rule.trigger_time = current_time
            else:
                # 未触发，重置状态
                rule.triggered = False
                rule.trigger_time = None
    
    def _evaluate_condition(self, value: float, threshold: float, operator: str) -> bool:
        """评估条件"""
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '==':
            return value == threshold
        elif operator == '!=':
            return value != threshold
        else:
            return False
    
    def _fire_alert(self, rule: AlertRule, snapshot: StatusSnapshot):
        """触发告警"""
        alert_data = {
            'rule_name': rule.name,
            'metric': rule.metric,
            'current_value': getattr(snapshot, rule.metric),
            'threshold': rule.threshold,
            'operator': rule.operator,
            'timestamp': snapshot.timestamp,
            'duration': rule.duration
        }
        
        # 记录告警历史
        self.alert_history.append(alert_data)
        
        # 执行回调
        if rule.callback:
            try:
                rule.callback(alert_data)
            except Exception as e:
                print(f"Alert callback error: {e}")
        
        # 执行全局告警回调
        for callback in self.alert_callbacks:
            try:
                callback(rule.name, alert_data)
            except Exception as e:
                print(f"Global alert callback error: {e}")
    
    def _monitor_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                # 收集指标
                metrics = self._collect_system_metrics()
                
                with self._lock:
                    self.current_metrics = metrics
                    
                    # 创建快照
                    snapshot = self._create_snapshot(metrics)
                    self.history.append(snapshot)
                    
                    # 检查告警
                    self._check_alerts(snapshot)
                
                # 执行状态更新回调
                for callback in self.status_update_callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        print(f"Status callback error: {e}")
                
            except Exception as e:
                print(f"Monitor loop error: {e}")
            
            # 等待下次更新
            self._stop_event.wait(self.update_interval)
    
    def start(self):
        """启动监控"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop(self):
        """停止监控"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._stop_event.set()
            self._monitor_thread.join(timeout=5.0)
    
    def get_current_metrics(self) -> SystemMetrics:
        """获取当前指标"""
        with self._lock:
            return self.current_metrics
    
    def get_history(self, duration_minutes: int = 30) -> List[StatusSnapshot]:
        """获取历史数据"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        with self._lock:
            return [
                snapshot for snapshot in self.history
                if snapshot.timestamp >= cutoff_time
            ]
    
    def get_task_statistics(self) -> Dict[str, int]:
        """获取任务统计"""
        with self._lock:
            stats = defaultdict(int)
            for task in self.tasks.values():
                stats[task.status.value] += 1
            
            return dict(stats)
    
    def add_task(self, task_info: TaskInfo):
        """添加任务"""
        with self._lock:
            self.tasks[task_info.task_id] = task_info
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
    
    def remove_task(self, task_id: str):
        """移除任务"""
        with self._lock:
            self.tasks.pop(task_id, None)
    
    def get_alert_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取告警历史"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alert_history
            if alert['timestamp'] >= cutoff_time
        ]
    
    def export_metrics(self, file_path: str, format: str = 'json'):
        """导出指标数据"""
        with self._lock:
            data = {
                'current_metrics': {
                    'cpu_usage': self.current_metrics.cpu_usage,
                    'memory_usage': self.current_metrics.memory_usage,
                    'disk_usage': self.current_metrics.disk_usage,
                    'network_sent': self.current_metrics.network_sent,
                    'network_recv': self.current_metrics.network_recv,
                    'active_threads': self.current_metrics.active_threads,
                    'last_updated': self.current_metrics.last_updated.isoformat()
                },
                'history': [
                    {
                        'timestamp': snapshot.timestamp.isoformat(),
                        'cpu_percent': snapshot.cpu_percent,
                        'memory_percent': snapshot.memory_percent,
                        'disk_percent': snapshot.disk_percent,
                        'network_sent': snapshot.network_sent,
                        'network_recv': snapshot.network_recv,
                        'active_threads': snapshot.active_threads,
                        'active_tasks': snapshot.active_tasks,
                        'queue_size': snapshot.queue_size
                    }
                    for snapshot in self.history
                ],
                'alert_history': self.alert_history,
                'tasks': {
                    task_id: {
                        'task_id': task.task_id,
                        'name': task.name,
                        'status': task.status.value,
                        'progress': task.progress,
                        'start_time': task.start_time.isoformat() if task.start_time else None,
                        'end_time': task.end_time.isoformat() if task.end_time else None,
                        'error_message': task.error_message
                    }
                    for task_id, task in self.tasks.items()
                }
            }
        
        file_path = Path(file_path)
        
        if format.lower() == 'json':
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def calculate_performance_score(self) -> float:
        """计算性能得分（0-100）"""
        with self._lock:
            metrics = self.current_metrics
            
            # 各项指标权重
            cpu_weight = 0.3
            memory_weight = 0.3
            disk_weight = 0.2
            threads_weight = 0.2
            
            # 计算各项得分（使用率越低得分越高）
            cpu_score = max(0, 100 - metrics.cpu_usage) * cpu_weight
            memory_score = max(0, 100 - metrics.memory_usage) * memory_weight
            disk_score = max(0, 100 - metrics.disk_usage) * disk_weight
            
            # 线程数得分（假设100个线程以下为正常）
            thread_score = max(0, min(100, (100 - metrics.active_threads) * 1.0)) * threads_weight
            
            total_score = cpu_score + memory_score + disk_score + thread_score
            
            return round(total_score, 1)
    
    def get_system_health(self) -> str:
        """获取系统健康状态"""
        score = self.calculate_performance_score()
        
        if score >= 80:
            return "优秀"
        elif score >= 60:
            return "良好"
        elif score >= 40:
            return "一般"
        elif score >= 20:
            return "较差"
        else:
            return "严重"