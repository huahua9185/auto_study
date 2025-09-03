"""
重试管理器

实现智能自动重试机制，支持指数退避和不同错误类型的重试策略
"""

import time
import random
import asyncio
import threading
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from functools import wraps

from loguru import logger


class RetryErrorType(Enum):
    """重试错误类型"""
    NETWORK_ERROR = "network_error"       # 网络错误
    AUTH_ERROR = "auth_error"             # 认证错误
    SYSTEM_ERROR = "system_error"         # 系统错误
    RATE_LIMIT_ERROR = "rate_limit_error" # 限流错误
    TEMPORARY_ERROR = "temporary_error"   # 临时错误
    UNKNOWN_ERROR = "unknown_error"       # 未知错误


@dataclass
class RetryStrategy:
    """重试策略配置"""
    max_attempts: int = 3                 # 最大重试次数
    base_delay: float = 1.0              # 基础延迟时间（秒）
    max_delay: float = 60.0              # 最大延迟时间（秒）
    exponential_base: float = 2.0        # 指数退避基数
    jitter: bool = True                  # 是否添加随机抖动
    backoff_type: str = "exponential"    # 退避类型: exponential, linear, fixed
    timeout: Optional[float] = None      # 超时时间
    
    def calculate_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        if self.backoff_type == "exponential":
            delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        elif self.backoff_type == "linear":
            delay = self.base_delay * attempt
        else:  # fixed
            delay = self.base_delay
        
        # 限制最大延迟
        delay = min(delay, self.max_delay)
        
        # 添加随机抖动
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class RetryableError(Exception):
    """可重试的错误"""
    
    def __init__(self, message: str, error_type: RetryErrorType = RetryErrorType.UNKNOWN_ERROR, 
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.error_type = error_type
        self.original_error = original_error
        self.timestamp = datetime.now()


@dataclass
class RetryAttempt:
    """重试尝试记录"""
    attempt: int
    timestamp: datetime
    error: Optional[Exception] = None
    delay: float = 0.0
    success: bool = False


@dataclass 
class RetryContext:
    """重试上下文"""
    function_name: str
    max_attempts: int
    current_attempt: int = 0
    attempts: List[RetryAttempt] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    strategy: Optional[RetryStrategy] = None
    
    @property
    def total_duration(self) -> float:
        """获取总持续时间"""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """获取成功率"""
        if not self.attempts:
            return 0.0
        successful = sum(1 for attempt in self.attempts if attempt.success)
        return successful / len(self.attempts)


class RetryManager:
    """重试管理器"""
    
    # 默认重试策略配置
    DEFAULT_STRATEGIES = {
        RetryErrorType.NETWORK_ERROR: RetryStrategy(
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0
        ),
        RetryErrorType.AUTH_ERROR: RetryStrategy(
            max_attempts=3,
            base_delay=5.0,
            max_delay=30.0,
            exponential_base=2.0
        ),
        RetryErrorType.SYSTEM_ERROR: RetryStrategy(
            max_attempts=2,
            base_delay=10.0,
            max_delay=60.0,
            exponential_base=1.5
        ),
        RetryErrorType.RATE_LIMIT_ERROR: RetryStrategy(
            max_attempts=10,
            base_delay=30.0,
            max_delay=300.0,
            exponential_base=1.2
        ),
        RetryErrorType.TEMPORARY_ERROR: RetryStrategy(
            max_attempts=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=1.5
        ),
        RetryErrorType.UNKNOWN_ERROR: RetryStrategy(
            max_attempts=3,
            base_delay=5.0,
            max_delay=30.0,
            exponential_base=2.0
        )
    }
    
    def __init__(self, custom_strategies: Optional[Dict[RetryErrorType, RetryStrategy]] = None):
        """
        初始化重试管理器
        
        Args:
            custom_strategies: 自定义重试策略
        """
        self.strategies = self.DEFAULT_STRATEGIES.copy()
        if custom_strategies:
            self.strategies.update(custom_strategies)
        
        self._contexts: Dict[str, RetryContext] = {}
        self._lock = threading.RLock()
        self._error_classifiers: List[Callable[[Exception], RetryErrorType]] = []
        
        # 注册默认错误分类器
        self._register_default_classifiers()
        
        logger.info("重试管理器已初始化")
    
    def _register_default_classifiers(self):
        """注册默认错误分类器"""
        
        def classify_network_error(error: Exception) -> RetryErrorType:
            """分类网络错误"""
            error_str = str(error).lower()
            if any(keyword in error_str for keyword in [
                'connection', 'timeout', 'network', 'dns', 'socket',
                'unreachable', 'reset', 'refused', 'unavailable'
            ]):
                return RetryErrorType.NETWORK_ERROR
            return RetryErrorType.UNKNOWN_ERROR
        
        def classify_auth_error(error: Exception) -> RetryErrorType:
            """分类认证错误"""
            error_str = str(error).lower()
            if any(keyword in error_str for keyword in [
                'auth', 'login', 'password', 'token', 'credential',
                'unauthorized', 'forbidden', '401', '403'
            ]):
                return RetryErrorType.AUTH_ERROR
            return RetryErrorType.UNKNOWN_ERROR
        
        def classify_rate_limit_error(error: Exception) -> RetryErrorType:
            """分类限流错误"""
            error_str = str(error).lower()
            if any(keyword in error_str for keyword in [
                'rate limit', 'too many requests', '429',
                'throttle', 'quota exceeded'
            ]):
                return RetryErrorType.RATE_LIMIT_ERROR
            return RetryErrorType.UNKNOWN_ERROR
        
        def classify_system_error(error: Exception) -> RetryErrorType:
            """分类系统错误"""
            if isinstance(error, (OSError, IOError, MemoryError)):
                return RetryErrorType.SYSTEM_ERROR
            return RetryErrorType.UNKNOWN_ERROR
        
        self._error_classifiers = [
            classify_network_error,
            classify_auth_error,
            classify_rate_limit_error,
            classify_system_error
        ]
    
    def classify_error(self, error: Exception) -> RetryErrorType:
        """分类错误类型"""
        # 如果是RetryableError，直接返回其错误类型
        if isinstance(error, RetryableError):
            return error.error_type
        
        # 使用注册的分类器
        for classifier in self._error_classifiers:
            error_type = classifier(error)
            if error_type != RetryErrorType.UNKNOWN_ERROR:
                return error_type
        
        return RetryErrorType.UNKNOWN_ERROR
    
    def register_error_classifier(self, classifier: Callable[[Exception], RetryErrorType]):
        """注册错误分类器"""
        self._error_classifiers.append(classifier)
        logger.info("已注册自定义错误分类器")
    
    def update_strategy(self, error_type: RetryErrorType, strategy: RetryStrategy):
        """更新重试策略"""
        self.strategies[error_type] = strategy
        logger.info(f"已更新重试策略: {error_type.value}")
    
    def should_retry(self, error: Exception, current_attempt: int) -> bool:
        """判断是否应该重试"""
        error_type = self.classify_error(error)
        strategy = self.strategies.get(error_type)
        
        if not strategy:
            return False
        
        return current_attempt < strategy.max_attempts
    
    def calculate_delay(self, error: Exception, attempt: int) -> float:
        """计算重试延迟"""
        error_type = self.classify_error(error)
        strategy = self.strategies.get(error_type, self.strategies[RetryErrorType.UNKNOWN_ERROR])
        
        return strategy.calculate_delay(attempt)
    
    def retry_function(self, 
                      func: Callable, 
                      *args,
                      max_attempts: Optional[int] = None,
                      strategy: Optional[RetryStrategy] = None,
                      context_key: Optional[str] = None,
                      **kwargs) -> Any:
        """
        重试执行函数
        
        Args:
            func: 要执行的函数
            args: 函数参数
            max_attempts: 最大重试次数（覆盖策略配置）
            strategy: 自定义重试策略
            context_key: 重试上下文键
            kwargs: 函数关键字参数
        
        Returns:
            函数执行结果
        """
        func_name = getattr(func, '__name__', str(func))
        if not context_key:
            context_key = f"{func_name}_{threading.get_ident()}"
        
        with self._lock:
            context = self._contexts.get(context_key)
            if not context:
                context = RetryContext(
                    function_name=func_name,
                    max_attempts=max_attempts or 3,
                    strategy=strategy
                )
                self._contexts[context_key] = context
        
        last_error = None
        
        while context.current_attempt < context.max_attempts:
            context.current_attempt += 1
            attempt_start = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功的尝试
                attempt = RetryAttempt(
                    attempt=context.current_attempt,
                    timestamp=attempt_start,
                    success=True
                )
                context.attempts.append(attempt)
                
                # 清理上下文
                with self._lock:
                    if context_key in self._contexts:
                        del self._contexts[context_key]
                
                logger.info(f"函数执行成功: {func_name} (第 {context.current_attempt} 次尝试)")
                return result
                
            except Exception as error:
                last_error = error
                
                # 记录失败的尝试
                attempt = RetryAttempt(
                    attempt=context.current_attempt,
                    timestamp=attempt_start,
                    error=error,
                    success=False
                )
                context.attempts.append(attempt)
                
                # 判断是否应该重试
                if not self.should_retry(error, context.current_attempt):
                    logger.warning(f"函数执行失败，不再重试: {func_name} - {error}")
                    break
                
                if context.current_attempt >= context.max_attempts:
                    logger.warning(f"函数执行失败，已达最大重试次数: {func_name}")
                    break
                
                # 计算延迟时间
                if context.strategy:
                    delay = context.strategy.calculate_delay(context.current_attempt)
                else:
                    delay = self.calculate_delay(error, context.current_attempt)
                
                attempt.delay = delay
                
                logger.warning(f"函数执行失败，{delay:.1f}秒后重试: {func_name} - {error}")
                
                # 延迟后重试
                time.sleep(delay)
        
        # 清理上下文
        with self._lock:
            if context_key in self._contexts:
                del self._contexts[context_key]
        
        # 重试失败，抛出最后一个错误
        if last_error:
            raise last_error
        else:
            raise Exception(f"函数执行失败: {func_name}")
    
    async def async_retry_function(self, 
                                  func: Callable, 
                                  *args,
                                  max_attempts: Optional[int] = None,
                                  strategy: Optional[RetryStrategy] = None,
                                  context_key: Optional[str] = None,
                                  **kwargs) -> Any:
        """异步重试执行函数"""
        func_name = getattr(func, '__name__', str(func))
        if not context_key:
            context_key = f"{func_name}_{threading.get_ident()}"
        
        with self._lock:
            context = self._contexts.get(context_key)
            if not context:
                context = RetryContext(
                    function_name=func_name,
                    max_attempts=max_attempts or 3,
                    strategy=strategy
                )
                self._contexts[context_key] = context
        
        last_error = None
        
        while context.current_attempt < context.max_attempts:
            context.current_attempt += 1
            attempt_start = datetime.now()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 记录成功的尝试
                attempt = RetryAttempt(
                    attempt=context.current_attempt,
                    timestamp=attempt_start,
                    success=True
                )
                context.attempts.append(attempt)
                
                # 清理上下文
                with self._lock:
                    if context_key in self._contexts:
                        del self._contexts[context_key]
                
                logger.info(f"函数执行成功: {func_name} (第 {context.current_attempt} 次尝试)")
                return result
                
            except Exception as error:
                last_error = error
                
                # 记录失败的尝试
                attempt = RetryAttempt(
                    attempt=context.current_attempt,
                    timestamp=attempt_start,
                    error=error,
                    success=False
                )
                context.attempts.append(attempt)
                
                # 判断是否应该重试
                if not self.should_retry(error, context.current_attempt):
                    logger.warning(f"函数执行失败，不再重试: {func_name} - {error}")
                    break
                
                if context.current_attempt >= context.max_attempts:
                    logger.warning(f"函数执行失败，已达最大重试次数: {func_name}")
                    break
                
                # 计算延迟时间
                if context.strategy:
                    delay = context.strategy.calculate_delay(context.current_attempt)
                else:
                    delay = self.calculate_delay(error, context.current_attempt)
                
                attempt.delay = delay
                
                logger.warning(f"函数执行失败，{delay:.1f}秒后重试: {func_name} - {error}")
                
                # 异步延迟后重试
                await asyncio.sleep(delay)
        
        # 清理上下文
        with self._lock:
            if context_key in self._contexts:
                del self._contexts[context_key]
        
        # 重试失败，抛出最后一个错误
        if last_error:
            raise last_error
        else:
            raise Exception(f"函数执行失败: {func_name}")
    
    def retry_decorator(self, 
                       max_attempts: Optional[int] = None,
                       strategy: Optional[RetryStrategy] = None,
                       error_types: Optional[List[Type[Exception]]] = None):
        """重试装饰器"""
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return self.retry_function(
                        func, *args, 
                        max_attempts=max_attempts,
                        strategy=strategy,
                        **kwargs
                    )
                except Exception as error:
                    # 如果指定了错误类型，只重试指定类型的错误
                    if error_types and not isinstance(error, tuple(error_types)):
                        raise
                    raise
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await self.async_retry_function(
                        func, *args,
                        max_attempts=max_attempts,
                        strategy=strategy,
                        **kwargs
                    )
                except Exception as error:
                    # 如果指定了错误类型，只重试指定类型的错误
                    if error_types and not isinstance(error, tuple(error_types)):
                        raise
                    raise
            
            # 根据函数类型返回相应的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return wrapper
        
        return decorator
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """获取重试统计信息"""
        with self._lock:
            active_contexts = len(self._contexts)
            
            # 计算统计信息（需要保存历史数据才能提供完整统计）
            stats = {
                'active_contexts': active_contexts,
                'total_strategies': len(self.strategies),
                'error_classifiers': len(self._error_classifiers)
            }
            
            # 如果有活跃上下文，添加详细信息
            if self._contexts:
                contexts_info = []
                for key, context in self._contexts.items():
                    contexts_info.append({
                        'key': key,
                        'function': context.function_name,
                        'attempt': context.current_attempt,
                        'max_attempts': context.max_attempts,
                        'duration': context.total_duration,
                        'success_rate': context.success_rate
                    })
                stats['active_contexts_detail'] = contexts_info
            
            return stats
    
    def clear_contexts(self):
        """清理所有重试上下文"""
        with self._lock:
            cleared_count = len(self._contexts)
            self._contexts.clear()
            
        logger.info(f"已清理 {cleared_count} 个重试上下文")
    
    def get_context(self, context_key: str) -> Optional[RetryContext]:
        """获取重试上下文"""
        with self._lock:
            return self._contexts.get(context_key)