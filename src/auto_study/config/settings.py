"""
系统设置配置

包含默认配置、用户配置加载、环境变量管理等
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BrowserConfig:
    """浏览器配置"""
    headless: bool = False
    width: int = 1920
    height: int = 1080
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    timeout: int = 30000  # 毫秒


@dataclass
class LoginConfig:
    """登录配置"""
    max_retries: int = 3
    retry_delay: int = 5  # 秒
    captcha_timeout: int = 30  # 秒


@dataclass
class LearningConfig:
    """学习配置"""
    check_interval: int = 30  # 秒，检查间隔
    human_behavior: bool = True  # 是否启用人类行为模拟
    auto_handle_popups: bool = True  # 是否自动处理弹窗
    max_learning_time: int = 8 * 60 * 60  # 8小时，最大学习时间（秒）


@dataclass
class SystemConfig:
    """系统配置"""
    log_level: str = "INFO"
    log_file: str = "logs/auto_study.log"
    data_dir: str = "data"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


class Settings:
    """设置管理器"""
    
    def __init__(self):
        self.browser = BrowserConfig()
        self.login = LoginConfig()
        self.learning = LearningConfig()
        self.system = SystemConfig()
        
        # 网站相关配置
        self.site_url = "https://edu.nxgbjy.org.cn"
        self.login_url = f"{self.site_url}/login"
        self.courses_url = f"{self.site_url}/courses"
        
        # 加载用户配置
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            from dotenv import load_dotenv
            
            # 加载.env文件
            env_path = Path(".env")
            if env_path.exists():
                load_dotenv(env_path)
            
            # 从环境变量更新配置
            self._update_from_env()
            
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def _update_from_env(self) -> None:
        """从环境变量更新配置"""
        # 浏览器配置
        if os.getenv("BROWSER_HEADLESS"):
            self.browser.headless = os.getenv("BROWSER_HEADLESS").lower() == "true"
        
        if os.getenv("BROWSER_WIDTH"):
            self.browser.width = int(os.getenv("BROWSER_WIDTH"))
        
        if os.getenv("BROWSER_HEIGHT"):
            self.browser.height = int(os.getenv("BROWSER_HEIGHT"))
        
        # 登录配置
        if os.getenv("LOGIN_MAX_RETRIES"):
            self.login.max_retries = int(os.getenv("LOGIN_MAX_RETRIES"))
        
        if os.getenv("LOGIN_RETRY_DELAY"):
            self.login.retry_delay = int(os.getenv("LOGIN_RETRY_DELAY"))
        
        # 学习配置
        if os.getenv("LEARNING_CHECK_INTERVAL"):
            self.learning.check_interval = int(os.getenv("LEARNING_CHECK_INTERVAL"))
        
        if os.getenv("LEARNING_HUMAN_BEHAVIOR"):
            self.learning.human_behavior = os.getenv("LEARNING_HUMAN_BEHAVIOR").lower() == "true"
        
        # 系统配置
        if os.getenv("LOG_LEVEL"):
            self.system.log_level = os.getenv("LOG_LEVEL")
        
        if os.getenv("LOG_FILE"):
            self.system.log_file = os.getenv("LOG_FILE")
    
    def get_user_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """获取用户凭据"""
        # 优先使用AUTO_STUDY_前缀的环境变量，避免与系统环境变量冲突
        username = os.getenv("AUTO_STUDY_USERNAME") or os.getenv("USERNAME")
        password = os.getenv("AUTO_STUDY_PASSWORD") or os.getenv("PASSWORD")
        
        # 如果获取的是系统用户名，则忽略它
        if username == os.getenv("USER") or username == os.getenv("LOGNAME"):
            username = os.getenv("AUTO_STUDY_USERNAME")
        
        return username, password
    
    def validate_config(self) -> bool:
        """验证配置"""
        try:
            # 检查必要目录
            os.makedirs(self.system.data_dir, exist_ok=True)
            os.makedirs(os.path.dirname(self.system.log_file), exist_ok=True)
            
            # 检查用户凭据
            username, password = self.get_user_credentials()
            if not username or not password:
                print("警告: 未设置用户名和密码环境变量")
                return False
            
            return True
            
        except Exception as e:
            print(f"配置验证失败: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'browser': {
                'headless': self.browser.headless,
                'width': self.browser.width,
                'height': self.browser.height,
                'user_agent': self.browser.user_agent,
                'timeout': self.browser.timeout
            },
            'login': {
                'max_retries': self.login.max_retries,
                'retry_delay': self.login.retry_delay,
                'captcha_timeout': self.login.captcha_timeout
            },
            'learning': {
                'check_interval': self.learning.check_interval,
                'human_behavior': self.learning.human_behavior,
                'auto_handle_popups': self.learning.auto_handle_popups,
                'max_learning_time': self.learning.max_learning_time
            },
            'system': {
                'log_level': self.system.log_level,
                'log_file': self.system.log_file,
                'data_dir': self.system.data_dir,
                'max_log_size': self.system.max_log_size,
                'backup_count': self.system.backup_count
            }
        }


# 全局设置实例
settings = Settings()