"""
结构化日志记录系统
基于loguru实现，提供结构化日志、日志聚合和分析功能
"""

import json
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import threading

from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志分类"""
    SYSTEM = "系统"
    AUTOMATION = "自动化"
    BROWSER = "浏览器"
    NETWORK = "网络"
    DATABASE = "数据库"
    USER = "用户"
    SECURITY = "安全"
    PERFORMANCE = "性能"


@dataclass
class LogContext:
    """日志上下文"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    module: str
    message: str
    context: LogContext
    exception: Optional[str] = None
    duration: Optional[float] = None
    tags: List[str] = None


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, 
                 log_dir: str = "logs",
                 max_file_size: str = "100 MB",
                 retention: str = "30 days",
                 compression: str = "gz"):
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.console = Console()
        self._lock = threading.Lock()
        
        # 日志缓存用于实时显示
        self.recent_logs: deque[LogEntry] = deque(maxlen=1000)
        
        # 日志统计
        self.log_stats = defaultdict(int)
        
        # 日志过滤器和处理器
        self.filters: List[Callable[[LogEntry], bool]] = []
        self.handlers: List[Callable[[LogEntry], None]] = []
        
        self._setup_loguru(max_file_size, retention, compression)
    
    def _setup_loguru(self, max_file_size: str, retention: str, compression: str):
        """配置loguru日志系统"""
        # 移除默认处理器
        logger.remove()
        
        # 添加控制台处理器（带颜色）
        def safe_format(record):
            category = record.get("extra", {}).get("category", "SYSTEM")
            return f"<green>{record['time'].strftime('%Y-%m-%d %H:%M:%S')}</green> | " \
                   f"<level>{record['level'].name: <8}</level> | " \
                   f"<cyan>{category}</cyan> | " \
                   f"<white>{record['message']}</white>"
        
        logger.add(
            sink=self._console_sink,
            format=safe_format,
            level="INFO",
            colorize=True
        )
        
        # 添加文件处理器（结构化JSON格式）
        logger.add(
            sink=self.log_dir / "structured_{time:YYYY-MM-DD}.log",
            serialize=True,
            level="DEBUG",
            rotation="1 day",
            retention=retention,
            compression=compression,
            enqueue=True,
            encoding="utf-8"
        )
        
        # 添加错误日志文件
        logger.add(
            sink=self.log_dir / "error_{time:YYYY-MM-DD}.log", 
            serialize=True,
            level="ERROR",
            rotation="1 day",
            retention=retention,
            compression=compression,
            filter=lambda record: record["level"].name in ["ERROR", "CRITICAL"],
            enqueue=True,
            encoding="utf-8"
        )
        
        # 性能日志文件
        logger.add(
            sink=self.log_dir / "performance_{time:YYYY-MM-DD}.log",
            serialize=True,
            level="INFO",
            rotation="1 day",
            retention=retention,
            compression=compression,
            filter=lambda record: record["extra"].get("category") == "PERFORMANCE",
            enqueue=True,
            encoding="utf-8"
        )
    
    def _console_sink(self, message):
        """控制台输出处理"""
        print(message, end='')
    
    def _json_formatter(self, record):
        """JSON格式化器（已弃用，现在使用serialize=True）"""
        # 该方法不再被使用，Loguru的serialize=True选项会自动处理JSON序列化
        pass
    
    def _create_log_entry(self, level: LogLevel, category: LogCategory, 
                         message: str, context: LogContext = None, 
                         exception: Exception = None, duration: float = None,
                         tags: List[str] = None, module: str = None) -> LogEntry:
        """创建日志条目"""
        import inspect
        
        # 获取调用模块
        if module is None:
            frame = inspect.currentframe().f_back.f_back
            module = frame.f_globals.get("__name__", "unknown")
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            category=category,
            module=module,
            message=message,
            context=context or LogContext(),
            exception=str(exception) if exception else None,
            duration=duration,
            tags=tags or []
        )
        
        return entry
    
    def _process_log_entry(self, entry: LogEntry):
        """处理日志条目"""
        with self._lock:
            # 添加到最近日志
            self.recent_logs.append(entry)
            
            # 更新统计
            self.log_stats[entry.level.value] += 1
            self.log_stats[f"category_{entry.category.value}"] += 1
            
            # 应用过滤器
            if all(filter_func(entry) for filter_func in self.filters):
                # 执行处理器
                for handler in self.handlers:
                    try:
                        handler(entry)
                    except Exception as e:
                        print(f"Log handler error: {e}")
    
    def _log(self, level: LogLevel, category: LogCategory, message: str,
             context: LogContext = None, exception: Exception = None,
             duration: float = None, tags: List[str] = None, **kwargs):
        """内部日志方法"""
        # 创建日志条目
        entry = self._create_log_entry(
            level, category, message, context, exception, duration, tags
        )
        
        # 处理日志条目
        self._process_log_entry(entry)
        
        # 准备loguru的extra数据
        extra_data = {
            "category": category.value,
            "context": asdict(entry.context) if entry.context else {},
            "tags": tags or [],
            "duration": duration
        }
        extra_data.update(kwargs)
        
        # 记录到loguru
        logger_method = getattr(logger, level.value.lower())
        
        try:
            if exception:
                logger_method(message, extra=extra_data, exception=exception)
            else:
                logger_method(message, extra=extra_data)
        except Exception as e:
            print(f"Logger error: {e}")
    
    # 基础日志方法
    def debug(self, message: str, category: LogCategory = LogCategory.SYSTEM,
              context: LogContext = None, **kwargs):
        """记录调试信息"""
        self._log(LogLevel.DEBUG, category, message, context, **kwargs)
    
    def info(self, message: str, category: LogCategory = LogCategory.SYSTEM,
             context: LogContext = None, **kwargs):
        """记录一般信息"""
        self._log(LogLevel.INFO, category, message, context, **kwargs)
    
    def warning(self, message: str, category: LogCategory = LogCategory.SYSTEM,
                context: LogContext = None, **kwargs):
        """记录警告信息"""
        self._log(LogLevel.WARNING, category, message, context, **kwargs)
    
    def error(self, message: str, category: LogCategory = LogCategory.SYSTEM,
              context: LogContext = None, exception: Exception = None, **kwargs):
        """记录错误信息"""
        self._log(LogLevel.ERROR, category, message, context, exception, **kwargs)
    
    def critical(self, message: str, category: LogCategory = LogCategory.SYSTEM,
                 context: LogContext = None, exception: Exception = None, **kwargs):
        """记录严重错误"""
        self._log(LogLevel.CRITICAL, category, message, context, exception, **kwargs)
    
    # 业务日志方法
    def log_user_action(self, user_id: str, action: str, details: str = ""):
        """记录用户操作"""
        context = LogContext(user_id=user_id)
        self.info(f"用户操作: {action} {details}", LogCategory.USER, context)
    
    def log_automation_step(self, task_id: str, step: str, status: str, duration: float = None):
        """记录自动化步骤"""
        context = LogContext(task_id=task_id)
        self.info(f"自动化步骤: {step} - {status}", LogCategory.AUTOMATION, context, duration=duration)
    
    def log_browser_action(self, action: str, url: str = "", details: str = ""):
        """记录浏览器操作"""
        message = f"浏览器操作: {action}"
        if url:
            message += f" - {url}"
        if details:
            message += f" - {details}"
        self.info(message, LogCategory.BROWSER)
    
    def log_network_request(self, method: str, url: str, status_code: int, 
                           duration: float, user_agent: str = None):
        """记录网络请求"""
        context = LogContext(user_agent=user_agent)
        message = f"网络请求: {method} {url} - {status_code}"
        self.info(message, LogCategory.NETWORK, context, duration=duration)
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = ""):
        """记录性能指标"""
        message = f"性能指标: {metric_name} = {value} {unit}"
        self.info(message, LogCategory.PERFORMANCE, duration=value)
    
    def log_security_event(self, event_type: str, description: str, 
                          ip_address: str = None, severity: str = "INFO"):
        """记录安全事件"""
        context = LogContext(ip_address=ip_address)
        level = LogLevel.WARNING if severity == "HIGH" else LogLevel.INFO
        self._log(level, LogCategory.SECURITY, f"安全事件: {event_type} - {description}", context)
    
    # 日志分析方法
    def get_recent_logs(self, count: int = 100, level: LogLevel = None, 
                       category: LogCategory = None) -> List[LogEntry]:
        """获取最近的日志"""
        with self._lock:
            logs = list(self.recent_logs)
            
            # 按条件过滤
            if level:
                logs = [log for log in logs if log.level == level]
            if category:
                logs = [log for log in logs if log.category == category]
            
            return logs[-count:]
    
    def get_log_statistics(self, hours: int = 24) -> Dict[str, int]:
        """获取日志统计信息"""
        with self._lock:
            return dict(self.log_stats)
    
    def get_error_summary(self, hours: int = 24) -> List[Dict[str, Any]]:
        """获取错误摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            error_logs = [
                log for log in self.recent_logs
                if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]
                and log.timestamp >= cutoff_time
            ]
        
        # 按错误类型分组
        error_groups = defaultdict(list)
        for log in error_logs:
            key = f"{log.module}:{log.message[:50]}"
            error_groups[key].append(log)
        
        # 生成摘要
        summary = []
        for error_key, logs in error_groups.items():
            summary.append({
                'error_type': error_key,
                'count': len(logs),
                'first_occurrence': min(log.timestamp for log in logs),
                'last_occurrence': max(log.timestamp for log in logs),
                'sample_message': logs[0].message,
                'module': logs[0].module
            })
        
        return sorted(summary, key=lambda x: x['count'], reverse=True)
    
    def show_log_dashboard(self):
        """显示日志仪表板"""
        self.console.print("\n" + "="*80, style="blue")
        self.console.print("📊 日志仪表板", style="bold blue", justify="center")
        self.console.print("="*80, style="blue")
        
        # 日志统计表
        stats_table = Table(title="日志统计", show_header=True, header_style="bold magenta")
        stats_table.add_column("级别", style="cyan", width=15)
        stats_table.add_column("数量", style="white", width=10)
        stats_table.add_column("占比", style="green", width=10)
        
        total_logs = sum(self.log_stats.values())
        for level in LogLevel:
            count = self.log_stats.get(level.value, 0)
            percentage = (count / total_logs * 100) if total_logs > 0 else 0
            stats_table.add_row(level.value, str(count), f"{percentage:.1f}%")
        
        self.console.print(stats_table)
        
        # 分类统计表
        category_table = Table(title="分类统计", show_header=True, header_style="bold magenta")
        category_table.add_column("分类", style="cyan", width=15)
        category_table.add_column("数量", style="white", width=10)
        
        for category in LogCategory:
            count = self.log_stats.get(f"category_{category.value}", 0)
            category_table.add_row(category.value, str(count))
        
        self.console.print(category_table)
        
        # 错误摘要
        errors = self.get_error_summary()
        if errors:
            error_table = Table(title="错误摘要", show_header=True, header_style="bold red")
            error_table.add_column("错误类型", style="red", width=40)
            error_table.add_column("次数", style="white", width=10)
            error_table.add_column("模块", style="cyan", width=20)
            
            for error in errors[:10]:  # 显示前10个错误
                error_table.add_row(
                    error['error_type'][:37] + "..." if len(error['error_type']) > 40 else error['error_type'],
                    str(error['count']),
                    error['module']
                )
            
            self.console.print(error_table)
    
    def add_filter(self, filter_func: Callable[[LogEntry], bool]):
        """添加日志过滤器"""
        self.filters.append(filter_func)
    
    def add_handler(self, handler_func: Callable[[LogEntry], None]):
        """添加日志处理器"""
        self.handlers.append(handler_func)
    
    def clear_stats(self):
        """清空统计数据"""
        with self._lock:
            self.log_stats.clear()
    
    def export_logs(self, file_path: str, hours: int = 24, format: str = "json"):
        """导出日志"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            filtered_logs = [
                log for log in self.recent_logs
                if log.timestamp >= cutoff_time
            ]
        
        if format == "json":
            log_data = [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level.value,
                    "category": log.category.value,
                    "module": log.module,
                    "message": log.message,
                    "context": asdict(log.context) if log.context else {},
                    "exception": log.exception,
                    "duration": log.duration,
                    "tags": log.tags
                }
                for log in filtered_logs
            ]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")


# 全局结构化日志实例
structured_logger = StructuredLogger()