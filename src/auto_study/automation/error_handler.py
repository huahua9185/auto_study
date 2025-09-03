"""
错误处理和重试机制

提供浏览器自动化操作的错误处理、重试逻辑和异常恢复功能
"""

import time
import functools
import traceback
from typing import Callable, Any, Optional, Union, List, Type
from enum import Enum
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError

from ..utils.logger import logger


class ErrorType(Enum):
    """错误类型分类"""
    TIMEOUT = "timeout"
    NETWORK = "network" 
    ELEMENT_NOT_FOUND = "element_not_found"
    JAVASCRIPT = "javascript"
    NAVIGATION = "navigation"
    UNKNOWN = "unknown"


class RetryStrategy(Enum):
    """重试策略"""
    LINEAR = "linear"           # 线性延迟
    EXPONENTIAL = "exponential" # 指数退避
    FIXED = "fixed"            # 固定延迟


class ErrorHandler:
    """错误处理和重试管理器"""
    
    def __init__(self):
        """初始化错误处理器"""
        self._error_statistics = {
            ErrorType.TIMEOUT: 0,
            ErrorType.NETWORK: 0,
            ErrorType.ELEMENT_NOT_FOUND: 0,
            ErrorType.JAVASCRIPT: 0,
            ErrorType.NAVIGATION: 0,
            ErrorType.UNKNOWN: 0
        }
        
        # 可重试的错误类型
        self._retryable_errors = {
            ErrorType.TIMEOUT,
            ErrorType.NETWORK,
            ErrorType.ELEMENT_NOT_FOUND,
            ErrorType.NAVIGATION
        }
        
        # 错误类型映射
        self._error_patterns = {
            ErrorType.TIMEOUT: [
                "timeout",
                "timed out",
                "waiting for",
                "TimeoutError"
            ],
            ErrorType.NETWORK: [
                "net::",
                "ERR_NETWORK",
                "ERR_CONNECTION",
                "ERR_INTERNET_DISCONNECTED",
                "Failed to fetch"
            ],
            ErrorType.ELEMENT_NOT_FOUND: [
                "strict mode violation",
                "element not found",
                "no element found",
                "locator resolved to 0 elements"
            ],
            ErrorType.JAVASCRIPT: [
                "ReferenceError",
                "TypeError",
                "SyntaxError",
                "evaluation failed"
            ],
            ErrorType.NAVIGATION: [
                "navigation",
                "ERR_ABORTED",
                "ERR_FAILED"
            ]
        }
    
    def classify_error(self, error: Exception) -> ErrorType:
        """
        分类错误类型
        
        Args:
            error: 异常对象
            
        Returns:
            错误类型
        """
        error_message = str(error).lower()
        
        for error_type, patterns in self._error_patterns.items():
            for pattern in patterns:
                if pattern.lower() in error_message:
                    self._error_statistics[error_type] += 1
                    return error_type
        
        # 检查异常类型
        if isinstance(error, PlaywrightTimeoutError):
            self._error_statistics[ErrorType.TIMEOUT] += 1
            return ErrorType.TIMEOUT
        
        self._error_statistics[ErrorType.UNKNOWN] += 1
        return ErrorType.UNKNOWN
    
    def is_retryable(self, error: Exception) -> bool:
        """
        判断错误是否可重试
        
        Args:
            error: 异常对象
            
        Returns:
            是否可重试
        """
        error_type = self.classify_error(error)
        return error_type in self._retryable_errors
    
    def calculate_delay(self, 
                       attempt: int, 
                       strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                       base_delay: float = 1.0,
                       max_delay: float = 60.0) -> float:
        """
        计算重试延迟时间
        
        Args:
            attempt: 当前重试次数（从1开始）
            strategy: 重试策略
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            
        Returns:
            延迟时间（秒）
        """
        if strategy == RetryStrategy.LINEAR:
            delay = base_delay * attempt
        elif strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (2 ** (attempt - 1))
        else:  # FIXED
            delay = base_delay
        
        return min(delay, max_delay)
    
    def retry_on_error(self,
                      max_retries: int = 3,
                      strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                      base_delay: float = 1.0,
                      max_delay: float = 60.0,
                      exceptions: tuple = (Exception,),
                      on_retry: Optional[Callable] = None):
        """
        重试装饰器
        
        Args:
            max_retries: 最大重试次数
            strategy: 重试策略
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
            exceptions: 需要重试的异常类型
            on_retry: 重试时的回调函数
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        result = func(*args, **kwargs)
                        
                        # 如果不是第一次尝试，记录成功信息
                        if attempt > 0:
                            logger.info(f"函数 {func.__name__} 在第 {attempt + 1} 次尝试后成功")
                        
                        return result
                        
                    except exceptions as e:
                        last_exception = e
                        
                        # 检查是否可重试
                        if not self.is_retryable(e):
                            logger.error(f"函数 {func.__name__} 遇到不可重试错误: {e}")
                            raise e
                        
                        # 如果是最后一次尝试，直接抛出异常
                        if attempt == max_retries:
                            break
                        
                        # 计算延迟时间
                        delay = self.calculate_delay(attempt + 1, strategy, base_delay, max_delay)
                        
                        logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败: {e}")
                        logger.info(f"将在 {delay:.2f} 秒后进行第 {attempt + 2} 次尝试")
                        
                        # 调用重试回调
                        if on_retry:
                            try:
                                on_retry(attempt + 1, e)
                            except Exception as callback_error:
                                logger.error(f"重试回调执行失败: {callback_error}")
                        
                        time.sleep(delay)
                
                # 所有重试都失败了
                logger.error(f"函数 {func.__name__} 在 {max_retries + 1} 次尝试后仍然失败")
                raise last_exception
            
            return wrapper
        return decorator
    
    def safe_execute(self,
                    func: Callable,
                    *args,
                    max_retries: int = 3,
                    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                    default_value: Any = None,
                    suppress_errors: bool = False,
                    **kwargs) -> Any:
        """
        安全执行函数，带重试和错误处理
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数
            strategy: 重试策略
            default_value: 默认返回值（发生错误时）
            suppress_errors: 是否抑制错误
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果或默认值
        """
        @self.retry_on_error(max_retries=max_retries, strategy=strategy)
        def wrapped_func():
            return func(*args, **kwargs)
        
        try:
            return wrapped_func()
        except Exception as e:
            if suppress_errors:
                logger.warning(f"函数 {func.__name__} 执行失败，返回默认值: {e}")
                return default_value
            else:
                raise e
    
    def handle_page_error(self, page: Page, error: Exception) -> bool:
        """
        处理页面相关错误
        
        Args:
            page: 页面对象
            error: 异常对象
            
        Returns:
            是否成功处理错误
        """
        try:
            error_type = self.classify_error(error)
            
            if error_type == ErrorType.TIMEOUT:
                return self._handle_timeout_error(page, error)
            elif error_type == ErrorType.NETWORK:
                return self._handle_network_error(page, error)
            elif error_type == ErrorType.ELEMENT_NOT_FOUND:
                return self._handle_element_not_found_error(page, error)
            elif error_type == ErrorType.JAVASCRIPT:
                return self._handle_javascript_error(page, error)
            elif error_type == ErrorType.NAVIGATION:
                return self._handle_navigation_error(page, error)
            else:
                return self._handle_unknown_error(page, error)
            
        except Exception as handling_error:
            logger.error(f"处理页面错误时发生异常: {handling_error}")
            return False
    
    def _handle_timeout_error(self, page: Page, error: Exception) -> bool:
        """处理超时错误"""
        try:
            logger.info("尝试处理超时错误...")
            
            # 检查页面是否仍然可用
            if page.is_closed():
                logger.error("页面已关闭，无法恢复")
                return False
            
            # 尝试停止加载
            try:
                page.evaluate("window.stop()")
            except:
                pass
            
            # 等待页面稳定
            try:
                page.wait_for_load_state('domcontentloaded', timeout=5000)
            except:
                pass
            
            logger.info("超时错误处理完成")
            return True
            
        except Exception as e:
            logger.error(f"处理超时错误失败: {e}")
            return False
    
    def _handle_network_error(self, page: Page, error: Exception) -> bool:
        """处理网络错误"""
        try:
            logger.info("尝试处理网络错误...")
            
            # 检查网络连接
            try:
                page.evaluate("navigator.onLine")
            except:
                logger.error("网络连接异常")
                return False
            
            # 尝试刷新页面
            try:
                page.reload(timeout=10000)
                logger.info("页面刷新成功")
                return True
            except:
                logger.error("页面刷新失败")
                return False
            
        except Exception as e:
            logger.error(f"处理网络错误失败: {e}")
            return False
    
    def _handle_element_not_found_error(self, page: Page, error: Exception) -> bool:
        """处理元素未找到错误"""
        try:
            logger.info("尝试处理元素未找到错误...")
            
            # 等待页面稳定
            try:
                page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass
            
            # 尝试滚动页面
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                time.sleep(1)
            except:
                pass
            
            logger.info("元素未找到错误处理完成")
            return True
            
        except Exception as e:
            logger.error(f"处理元素未找到错误失败: {e}")
            return False
    
    def _handle_javascript_error(self, page: Page, error: Exception) -> bool:
        """处理JavaScript错误"""
        try:
            logger.info("尝试处理JavaScript错误...")
            
            # 清除JavaScript错误
            try:
                page.evaluate("console.clear()")
            except:
                pass
            
            logger.info("JavaScript错误处理完成")
            return True
            
        except Exception as e:
            logger.error(f"处理JavaScript错误失败: {e}")
            return False
    
    def _handle_navigation_error(self, page: Page, error: Exception) -> bool:
        """处理导航错误"""
        try:
            logger.info("尝试处理导航错误...")
            
            # 检查当前URL
            current_url = page.url
            if current_url == 'about:blank':
                logger.error("页面导航失败，当前为空白页")
                return False
            
            logger.info(f"导航错误处理完成，当前URL: {current_url}")
            return True
            
        except Exception as e:
            logger.error(f"处理导航错误失败: {e}")
            return False
    
    def _handle_unknown_error(self, page: Page, error: Exception) -> bool:
        """处理未知错误"""
        try:
            logger.info("尝试处理未知错误...")
            
            # 记录详细错误信息
            logger.error(f"未知错误详情: {traceback.format_exc()}")
            
            # 检查页面基本状态
            if page.is_closed():
                logger.error("页面已关闭")
                return False
            
            logger.info("未知错误处理完成")
            return True
            
        except Exception as e:
            logger.error(f"处理未知错误失败: {e}")
            return False
    
    def get_error_statistics(self) -> dict:
        """
        获取错误统计信息
        
        Returns:
            错误统计字典
        """
        total_errors = sum(self._error_statistics.values())
        
        statistics = {
            'total_errors': total_errors,
            'by_type': dict(self._error_statistics),
            'percentages': {}
        }
        
        if total_errors > 0:
            for error_type, count in self._error_statistics.items():
                percentage = (count / total_errors) * 100
                statistics['percentages'][error_type.value] = round(percentage, 2)
        
        return statistics
    
    def reset_statistics(self) -> None:
        """重置错误统计"""
        for error_type in self._error_statistics:
            self._error_statistics[error_type] = 0
        logger.info("错误统计已重置")
    
    def create_circuit_breaker(self,
                             failure_threshold: int = 5,
                             timeout: int = 60,
                             expected_exception: Type[Exception] = Exception):
        """
        创建断路器装饰器
        
        Args:
            failure_threshold: 失败阈值
            timeout: 超时时间（秒）
            expected_exception: 预期异常类型
        """
        class CircuitBreaker:
            def __init__(self):
                self.failure_count = 0
                self.last_failure_time = None
                self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
            
            def __call__(self, func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    if self.state == 'OPEN':
                        if time.time() - self.last_failure_time < timeout:
                            raise Exception(f"断路器处于开启状态，拒绝执行 {func.__name__}")
                        else:
                            self.state = 'HALF_OPEN'
                    
                    try:
                        result = func(*args, **kwargs)
                        self.on_success()
                        return result
                    
                    except expected_exception as e:
                        self.on_failure()
                        raise e
                
                return wrapper
            
            def on_success(self):
                self.failure_count = 0
                self.state = 'CLOSED'
                logger.info("断路器重置为关闭状态")
            
            def on_failure(self):
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= failure_threshold:
                    self.state = 'OPEN'
                    logger.warning(f"断路器开启，失败次数: {self.failure_count}")
        
        return CircuitBreaker()


# 全局错误处理器实例
error_handler = ErrorHandler()


# 便捷装饰器
def retry(max_retries: int = 3, 
         strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
         base_delay: float = 1.0):
    """简化的重试装饰器"""
    return error_handler.retry_on_error(
        max_retries=max_retries,
        strategy=strategy,
        base_delay=base_delay
    )


# 登录专用错误处理
class LoginError(Exception):
    """登录相关错误基类"""
    pass


class CredentialsError(LoginError):
    """凭据错误"""
    pass


class CaptchaError(LoginError):
    """验证码错误"""
    pass


class FormNotFoundError(LoginError):
    """登录表单未找到错误"""
    pass


class LoginTimeoutError(LoginError):
    """登录超时错误"""
    pass


def login_retry(max_retries: int = 2, base_delay: float = 3.0):
    """登录专用重试装饰器，针对登录失败进行优化"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(f"登录重试成功，尝试次数: {attempt + 1}")
                    return result
                    
                except (CaptchaError, FormNotFoundError, LoginTimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (attempt + 1)  # 线性增长延迟
                        logger.warning(f"登录失败 ({e.__class__.__name__}): {e}，{delay}秒后重试...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"登录失败，已达最大重试次数: {e}")
                        break
                        
                except CredentialsError as e:
                    # 凭据错误不重试
                    logger.error(f"登录凭据错误，不进行重试: {e}")
                    raise
                    
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (attempt + 1)
                        logger.error(f"登录过程出现异常: {e}，{delay}秒后重试...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"登录异常，已达最大重试次数: {e}")
                        break
            
            raise last_exception
        return wrapper
    return decorator


def captcha_retry(max_retries: int = 3, base_delay: float = 1.0):
    """验证码识别专用重试装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if result:  # 识别成功
                        if attempt > 0:
                            logger.info(f"验证码识别重试成功，尝试次数: {attempt + 1}")
                        return result
                    else:  # 识别失败但无异常
                        if attempt < max_retries:
                            logger.warning(f"验证码识别失败，第 {attempt + 1} 次尝试")
                            time.sleep(base_delay)
                            continue
                        else:
                            logger.error("验证码识别失败，已达最大尝试次数")
                            return None
                            
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"验证码识别异常: {e}，进行第 {attempt + 2} 次尝试")
                        time.sleep(base_delay)
                        continue
                    else:
                        logger.error(f"验证码识别异常，已达最大重试次数: {e}")
                        break
            
            if last_exception:
                raise last_exception
            return None
        return wrapper
    return decorator


def safe_operation(default_value: Any = None, suppress_errors: bool = True):
    """安全操作装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return error_handler.safe_execute(
                func, *args, 
                default_value=default_value,
                suppress_errors=suppress_errors,
                **kwargs
            )
        return wrapper
    return decorator