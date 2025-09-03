"""
Rich终端UI面板
实现美观的终端界面用于状态监控
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.columns import Columns


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "等待中"
    RUNNING = "运行中"
    SUCCESS = "成功"
    FAILED = "失败"
    CANCELLED = "已取消"


@dataclass
class SystemMetrics:
    """系统指标数据"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_sent: int = 0
    network_recv: int = 0
    active_threads: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    name: str
    status: TaskStatus
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None


class MonitoringUI:
    """监控UI面板"""
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.is_running = False
        self._lock = threading.Lock()
        
        # 数据存储
        self.system_metrics = SystemMetrics()
        self.tasks: Dict[str, TaskInfo] = {}
        self.recent_logs: List[Dict[str, Any]] = []
        self.statistics = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'success_rate': 0.0,
            'uptime': 0,
            'errors_count': 0,
            'warnings_count': 0
        }
        
        self._setup_layout()
    
    def _setup_layout(self):
        """设置UI布局"""
        # 创建主布局
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # 主区域分割
        self.layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        # 左侧分割
        self.layout["left"].split_column(
            Layout(name="tasks", ratio=2),
            Layout(name="logs", ratio=1)
        )
        
        # 右侧分割
        self.layout["right"].split_column(
            Layout(name="metrics"),
            Layout(name="stats")
        )
    
    def _create_header(self) -> Panel:
        """创建头部面板"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uptime = self.statistics['uptime']
        
        header_text = Text()
        header_text.append("🤖 ", style="bold blue")
        header_text.append("Auto Study Monitor", style="bold white")
        header_text.append(f"  •  {current_time}", style="dim white")
        header_text.append(f"  •  运行时间: {uptime}s", style="green")
        
        return Panel(
            Align.center(header_text),
            style="blue",
            title="系统监控"
        )
    
    def _create_tasks_panel(self) -> Panel:
        """创建任务面板"""
        if not self.tasks:
            return Panel(
                Align.center("暂无任务"),
                title="📋 任务状态",
                border_style="green"
            )
        
        table = Table(expand=True)
        table.add_column("任务ID", style="cyan", no_wrap=True, width=12)
        table.add_column("任务名称", style="white")
        table.add_column("状态", style="bold")
        table.add_column("进度", style="blue")
        table.add_column("开始时间", style="dim")
        
        for task in list(self.tasks.values())[-10:]:  # 显示最近10个任务
            # 状态颜色
            status_color = {
                TaskStatus.PENDING: "yellow",
                TaskStatus.RUNNING: "blue",
                TaskStatus.SUCCESS: "green",
                TaskStatus.FAILED: "red",
                TaskStatus.CANCELLED: "dim"
            }.get(task.status, "white")
            
            # 进度显示
            progress_text = f"{task.progress:.1f}%" if task.progress > 0 else "-"
            
            # 开始时间
            start_time = task.start_time.strftime("%H:%M:%S") if task.start_time else "-"
            
            table.add_row(
                task.task_id,
                task.name[:30] + "..." if len(task.name) > 30 else task.name,
                f"[{status_color}]{task.status.value}[/{status_color}]",
                progress_text,
                start_time
            )
        
        return Panel(table, title="📋 任务状态", border_style="green")
    
    def _create_logs_panel(self) -> Panel:
        """创建日志面板"""
        if not self.recent_logs:
            return Panel(
                Align.center("暂无日志"),
                title="📝 实时日志",
                border_style="yellow"
            )
        
        log_text = Text()
        for log_entry in self.recent_logs[-20:]:  # 显示最近20条日志
            timestamp = log_entry.get('timestamp', '')
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')
            
            # 日志级别颜色
            level_colors = {
                'DEBUG': 'dim',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold red'
            }
            color = level_colors.get(level, 'white')
            
            log_text.append(f"{timestamp} ", style="dim")
            log_text.append(f"[{level}]", style=f"bold {color}")
            log_text.append(f" {message}\n", style=color)
        
        return Panel(log_text, title="📝 实时日志", border_style="yellow")
    
    def _create_metrics_panel(self) -> Panel:
        """创建系统指标面板"""
        table = Table(show_header=False, expand=True)
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="white")
        
        table.add_row("CPU使用率", f"{self.system_metrics.cpu_usage:.1f}%")
        table.add_row("内存使用率", f"{self.system_metrics.memory_usage:.1f}%")
        table.add_row("磁盘使用率", f"{self.system_metrics.disk_usage:.1f}%")
        table.add_row("活跃线程", str(self.system_metrics.active_threads))
        table.add_row("网络发送", f"{self.system_metrics.network_sent / 1024:.1f}KB")
        table.add_row("网络接收", f"{self.system_metrics.network_recv / 1024:.1f}KB")
        
        return Panel(table, title="📊 系统指标", border_style="blue")
    
    def _create_stats_panel(self) -> Panel:
        """创建统计面板"""
        stats = self.statistics
        
        table = Table(show_header=False, expand=True)
        table.add_column("统计项", style="cyan")
        table.add_column("数值", style="white")
        
        table.add_row("总任务数", str(stats['total_tasks']))
        table.add_row("已完成", str(stats['completed_tasks']))
        table.add_row("失败任务", str(stats['failed_tasks']))
        table.add_row("成功率", f"{stats['success_rate']:.1f}%")
        table.add_row("错误数量", str(stats['errors_count']))
        table.add_row("警告数量", str(stats['warnings_count']))
        
        return Panel(table, title="📈 运行统计", border_style="magenta")
    
    def _create_footer(self) -> Panel:
        """创建底部面板"""
        footer_text = Text()
        footer_text.append("💡 提示: ", style="bold yellow")
        footer_text.append("按 Ctrl+C 退出监控  ", style="white")
        footer_text.append("• ", style="dim")
        footer_text.append("F5 刷新  ", style="white")
        footer_text.append("• ", style="dim")
        footer_text.append("ESC 返回主界面", style="white")
        
        return Panel(
            Align.center(footer_text),
            style="dim"
        )
    
    def update_layout(self):
        """更新布局内容"""
        with self._lock:
            self.layout["header"].update(self._create_header())
            self.layout["tasks"].update(self._create_tasks_panel())
            self.layout["logs"].update(self._create_logs_panel())
            self.layout["metrics"].update(self._create_metrics_panel())
            self.layout["stats"].update(self._create_stats_panel())
            self.layout["footer"].update(self._create_footer())
    
    def add_task(self, task_id: str, name: str) -> None:
        """添加任务"""
        with self._lock:
            self.tasks[task_id] = TaskInfo(
                task_id=task_id,
                name=name,
                status=TaskStatus.PENDING,
                start_time=datetime.now()
            )
            self.statistics['total_tasks'] += 1
    
    def update_task(self, task_id: str, status: TaskStatus = None, 
                   progress: float = None, error_message: str = None) -> None:
        """更新任务状态"""
        with self._lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            
            if status:
                task.status = status
                if status == TaskStatus.RUNNING and not task.start_time:
                    task.start_time = datetime.now()
                elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    task.end_time = datetime.now()
                    if status == TaskStatus.SUCCESS:
                        self.statistics['completed_tasks'] += 1
                    elif status == TaskStatus.FAILED:
                        self.statistics['failed_tasks'] += 1
            
            if progress is not None:
                task.progress = progress
            
            if error_message:
                task.error_message = error_message
            
            # 更新成功率
            if self.statistics['total_tasks'] > 0:
                self.statistics['success_rate'] = (
                    self.statistics['completed_tasks'] / self.statistics['total_tasks'] * 100
                )
    
    def add_log(self, level: str, message: str, timestamp: datetime = None) -> None:
        """添加日志"""
        with self._lock:
            if timestamp is None:
                timestamp = datetime.now()
            
            log_entry = {
                'timestamp': timestamp.strftime("%H:%M:%S"),
                'level': level,
                'message': message
            }
            
            self.recent_logs.append(log_entry)
            
            # 保持日志数量在合理范围内
            if len(self.recent_logs) > 100:
                self.recent_logs = self.recent_logs[-100:]
            
            # 更新统计
            if level in ['ERROR', 'CRITICAL']:
                self.statistics['errors_count'] += 1
            elif level == 'WARNING':
                self.statistics['warnings_count'] += 1
    
    def update_system_metrics(self, metrics: SystemMetrics) -> None:
        """更新系统指标"""
        with self._lock:
            self.system_metrics = metrics
    
    def start_monitoring(self) -> None:
        """开始监控"""
        self.is_running = True
        start_time = time.time()
        
        try:
            with Live(self.layout, console=self.console, refresh_per_second=2) as live:
                while self.is_running:
                    # 更新运行时间
                    self.statistics['uptime'] = int(time.time() - start_time)
                    
                    # 更新界面
                    self.update_layout()
                    
                    time.sleep(0.5)
        except KeyboardInterrupt:
            self.console.print("\n👋 监控已退出", style="yellow")
        finally:
            self.is_running = False
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self.is_running = False
    
    def show_summary(self) -> None:
        """显示监控摘要"""
        self.console.print("\n" + "="*60, style="blue")
        self.console.print("📊 监控摘要", style="bold blue", justify="center")
        self.console.print("="*60, style="blue")
        
        stats = self.statistics
        
        summary_table = Table(title="运行统计", show_header=True, header_style="bold magenta")
        summary_table.add_column("项目", style="cyan", width=20)
        summary_table.add_column("数值", style="white", width=20)
        summary_table.add_column("备注", style="dim")
        
        summary_table.add_row("总任务数", str(stats['total_tasks']), "包含所有任务")
        summary_table.add_row("成功任务", str(stats['completed_tasks']), "✅ 成功完成")
        summary_table.add_row("失败任务", str(stats['failed_tasks']), "❌ 执行失败")
        summary_table.add_row("成功率", f"{stats['success_rate']:.1f}%", "成功/总数")
        summary_table.add_row("运行时长", f"{stats['uptime']}秒", "总运行时间")
        summary_table.add_row("错误数量", str(stats['errors_count']), "🚨 需要关注")
        summary_table.add_row("警告数量", str(stats['warnings_count']), "⚠️  可能需要处理")
        
        self.console.print(summary_table)
        self.console.print("\n感谢使用监控系统！", style="green")