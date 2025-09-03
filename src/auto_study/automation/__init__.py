"""
浏览器自动化模块

提供基于Playwright的浏览器自动化功能，包括：
- 浏览器实例管理和生命周期控制
- 反检测机制
- 上下文持久化
- 错误处理和重试
- 自动化登录功能
- 验证码识别
- 登录状态管理
"""

from .browser_manager import BrowserManager, BrowserType
from .anti_detection import AntiDetection
from .context_manager import ContextManager
from .error_handler import (
    ErrorHandler, error_handler, retry, safe_operation,
    LoginError, CredentialsError, CaptchaError, FormNotFoundError, LoginTimeoutError,
    login_retry, captcha_retry
)
from .captcha_recognizer import CaptchaRecognizer, recognize_captcha
from .login_state import LoginStateManager, LoginStatus
from .login_manager import LoginManager, get_login_manager
from .course_manager import CourseManager, Course, CourseStatus, CoursePriority, get_course_manager

__all__ = [
    'BrowserManager',
    'BrowserType',
    'AntiDetection', 
    'ContextManager',
    'ErrorHandler',
    'error_handler',
    'retry',
    'safe_operation',
    'LoginError',
    'CredentialsError',
    'CaptchaError',
    'FormNotFoundError',
    'LoginTimeoutError',
    'login_retry',
    'captcha_retry',
    'CaptchaRecognizer',
    'recognize_captcha',
    'LoginStateManager',
    'LoginStatus',
    'LoginManager',
    'get_login_manager',
    'CourseManager',
    'Course',
    'CourseStatus',
    'CoursePriority',
    'get_course_manager'
]