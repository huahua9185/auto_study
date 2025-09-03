"""
日志管理器

统一的日志记录和管理功能
"""

import logging
import os
from typing import Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.logging import RichHandler


class Logger:
    """日志管理器"""
    
    def __init__(self, name: str = "auto_study"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.console = Console()
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """设置日志器"""
        if self.logger.handlers:
            return  # 已经设置过了
        
        self.logger.setLevel(logging.INFO)
        
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 文件处理器
        file_handler = RotatingFileHandler(
            log_dir / "auto_study.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器（使用Rich）
        console_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False
        )
        console_handler.setFormatter(
            logging.Formatter('%(message)s')
        )
        self.logger.addHandler(console_handler)
    
    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """错误日志"""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self.logger.debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """严重错误日志"""
        self.logger.critical(message, **kwargs)
    
    def log_course_start(self, course_title: str) -> None:
        """记录课程开始学习"""
        self.info(f"🎓 开始学习课程: {course_title}")
    
    def log_course_complete(self, course_title: str, duration: str) -> None:
        """记录课程完成"""
        self.info(f"✅ 课程完成: {course_title} (耗时: {duration})")
    
    def log_login_success(self, username: str) -> None:
        """记录登录成功"""
        self.info(f"🔐 登录成功: {username}")
    
    def log_login_failed(self, username: str, reason: str) -> None:
        """记录登录失败"""
        self.error(f"❌ 登录失败: {username} - {reason}")
    
    def log_captcha_result(self, success: bool, text: str = "") -> None:
        """记录验证码识别结果"""
        if success:
            self.info(f"🔍 验证码识别成功: {text}")
        else:
            self.warning("❓ 验证码识别失败")
    
    def log_system_status(self, status: str, details: str = "") -> None:
        """记录系统状态"""
        self.info(f"⚙️  系统状态: {status} {details}")
    
    def log_error_with_context(self, error: Exception, context: str = "") -> None:
        """记录带上下文的错误"""
        error_msg = f"💥 错误: {str(error)}"
        if context:
            error_msg += f" - 上下文: {context}"
        self.error(error_msg, exc_info=True)


# 全局日志实例
logger = Logger()