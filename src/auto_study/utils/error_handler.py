"""
错误处理器

统一的错误处理和恢复机制
"""

import asyncio
import functools
from typing import Callable, Any, Optional, Type, Union
from .logger import logger


class AutoStudyError(Exception):
    """自动学习系统基础异常"""
    pass


class LoginError(AutoStudyError):
    """登录相关异常"""
    pass


class CourseError(AutoStudyError):
    """课程相关异常"""
    pass


class BrowserError(AutoStudyError):
    """浏览器相关异常"""
    pass


class NetworkError(AutoStudyError):
    """网络相关异常"""
    pass


class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def retry(max_attempts: int = 3, delay: float = 1.0, 
              exceptions: tuple = (Exception,)) -> Callable:
        """重试装饰器"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"第{attempt + 1}次尝试失败: {str(e)}, "
                                f"{delay}秒后重试..."
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.error(f"所有重试失败: {str(e)}")
                
                raise last_exception
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"第{attempt + 1}次尝试失败: {str(e)}, "
                                f"{delay}秒后重试..."
                            )
                            import time
                            time.sleep(delay)
                        else:
                            logger.error(f"所有重试失败: {str(e)}")
                
                raise last_exception
            
            # 根据函数类型返回对应的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @staticmethod
    def handle_errors(
        error_types: dict[Type[Exception], str] = None
    ) -> Callable:
        """错误处理装饰器"""
        if error_types is None:
            error_types = {
                Exception: "未知错误"
            }
        
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # 查找匹配的错误类型
                    error_message = "未知错误"
                    for error_type, message in error_types.items():
                        if isinstance(e, error_type):
                            error_message = message
                            break
                    
                    logger.log_error_with_context(
                        e, 
                        f"{func.__name__}: {error_message}"
                    )
                    raise
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # 查找匹配的错误类型
                    error_message = "未知错误"
                    for error_type, message in error_types.items():
                        if isinstance(e, error_type):
                            error_message = message
                            break
                    
                    logger.log_error_with_context(
                        e, 
                        f"{func.__name__}: {error_message}"
                    )
                    raise
            
            # 根据函数类型返回对应的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @staticmethod
    def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        """安全执行函数"""
        try:
            result = func(*args, **kwargs)
            return True, result
        except Exception as e:
            logger.log_error_with_context(e, f"安全执行 {func.__name__} 失败")
            return False, None
    
    @staticmethod
    async def safe_execute_async(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
        """安全执行异步函数"""
        try:
            result = await func(*args, **kwargs)
            return True, result
        except Exception as e:
            logger.log_error_with_context(e, f"安全执行 {func.__name__} 失败")
            return False, None
    
    @staticmethod
    def classify_error(error: Exception) -> str:
        """分类错误"""
        if isinstance(error, LoginError):
            return "登录错误"
        elif isinstance(error, CourseError):
            return "课程错误"
        elif isinstance(error, BrowserError):
            return "浏览器错误"
        elif isinstance(error, NetworkError):
            return "网络错误"
        elif "timeout" in str(error).lower():
            return "超时错误"
        elif "network" in str(error).lower():
            return "网络连接错误"
        else:
            return "未知错误"


# 常用装饰器实例
retry_on_error = ErrorHandler.retry(max_attempts=3, delay=2.0)
retry_on_network_error = ErrorHandler.retry(
    max_attempts=5, 
    delay=1.0, 
    exceptions=(NetworkError, ConnectionError)
)

# 错误处理器实例
error_handler = ErrorHandler()