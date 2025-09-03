"""
重试管理器测试
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch

from src.auto_study.recovery.retry_manager import (
    RetryManager, RetryStrategy, RetryableError, RetryErrorType
)


class TestRetryStrategy:
    """重试策略测试"""
    
    def test_exponential_backoff(self):
        """测试指数退避"""
        strategy = RetryStrategy(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False  # 关闭抖动以便测试
        )
        
        # 测试延迟计算
        assert strategy.calculate_delay(1) == 1.0  # 1 * 2^0
        assert strategy.calculate_delay(2) == 2.0  # 1 * 2^1
        assert strategy.calculate_delay(3) == 4.0  # 1 * 2^2
        assert strategy.calculate_delay(4) == 8.0  # 1 * 2^3
        assert strategy.calculate_delay(5) == 10.0  # 受max_delay限制
    
    def test_linear_backoff(self):
        """测试线性退避"""
        strategy = RetryStrategy(
            base_delay=2.0,
            backoff_type="linear",
            max_delay=20.0,
            jitter=False
        )
        
        assert strategy.calculate_delay(1) == 2.0   # 2 * 1
        assert strategy.calculate_delay(2) == 4.0   # 2 * 2
        assert strategy.calculate_delay(3) == 6.0   # 2 * 3
        assert strategy.calculate_delay(10) == 20.0  # 2 * 10 = 20（未超过max_delay）
        assert strategy.calculate_delay(15) == 20.0  # 2 * 15 = 30，受max_delay限制为20
    
    def test_fixed_backoff(self):
        """测试固定退避"""
        strategy = RetryStrategy(
            base_delay=5.0,
            backoff_type="fixed",
            jitter=False
        )
        
        assert strategy.calculate_delay(1) == 5.0
        assert strategy.calculate_delay(2) == 5.0
        assert strategy.calculate_delay(10) == 5.0
    
    def test_jitter(self):
        """测试抖动"""
        strategy = RetryStrategy(
            base_delay=4.0,
            backoff_type="fixed",
            jitter=True
        )
        
        delays = [strategy.calculate_delay(1) for _ in range(100)]
        
        # 所有延迟都应该在 [2.0, 4.0] 范围内（50%-100%的基础延迟）
        assert all(2.0 <= delay <= 4.0 for delay in delays)
        
        # 延迟应该有变化（不是所有值都相同）
        assert len(set(delays)) > 1


class TestRetryManager:
    """重试管理器测试"""
    
    @pytest.fixture
    def retry_manager(self):
        """重试管理器实例"""
        return RetryManager()
    
    def test_error_classification(self, retry_manager):
        """测试错误分类"""
        # 测试网络错误
        network_errors = [
            Exception("Connection timeout"),
            Exception("Network unreachable"),
            Exception("DNS resolution failed"),
            ConnectionError("Connection refused")
        ]
        
        for error in network_errors:
            error_type = retry_manager.classify_error(error)
            assert error_type == RetryErrorType.NETWORK_ERROR
        
        # 测试认证错误
        auth_errors = [
            Exception("Authentication failed"),
            Exception("Invalid credentials"),
            Exception("HTTP 401 Unauthorized"),
            Exception("403 Forbidden")
        ]
        
        for error in auth_errors:
            error_type = retry_manager.classify_error(error)
            assert error_type == RetryErrorType.AUTH_ERROR
        
        # 测试限流错误
        rate_limit_errors = [
            Exception("Rate limit exceeded"),
            Exception("Too many requests"),
            Exception("HTTP 429")
        ]
        
        for error in rate_limit_errors:
            error_type = retry_manager.classify_error(error)
            assert error_type == RetryErrorType.RATE_LIMIT_ERROR
        
        # 测试系统错误
        system_errors = [
            OSError("No space left on device"),
            IOError("Permission denied"),
            MemoryError()
        ]
        
        for error in system_errors:
            error_type = retry_manager.classify_error(error)
            assert error_type == RetryErrorType.SYSTEM_ERROR
        
        # 测试RetryableError
        retryable_error = RetryableError(
            "Custom error", 
            RetryErrorType.TEMPORARY_ERROR
        )
        error_type = retry_manager.classify_error(retryable_error)
        assert error_type == RetryErrorType.TEMPORARY_ERROR
        
        # 测试未知错误
        unknown_error = Exception("Some random error")
        error_type = retry_manager.classify_error(unknown_error)
        assert error_type == RetryErrorType.UNKNOWN_ERROR
    
    def test_custom_error_classifier(self, retry_manager):
        """测试自定义错误分类器"""
        def custom_classifier(error):
            if "database" in str(error).lower():
                return RetryErrorType.SYSTEM_ERROR
            return RetryErrorType.UNKNOWN_ERROR
        
        retry_manager.register_error_classifier(custom_classifier)
        
        db_error = Exception("Database connection lost")
        error_type = retry_manager.classify_error(db_error)
        assert error_type == RetryErrorType.SYSTEM_ERROR
    
    def test_should_retry(self, retry_manager):
        """测试重试判断"""
        network_error = Exception("Connection timeout")
        
        # 第1次尝试应该重试（网络错误默认最多5次）
        assert retry_manager.should_retry(network_error, 1) is True
        assert retry_manager.should_retry(network_error, 3) is True
        assert retry_manager.should_retry(network_error, 5) is False  # 已达最大次数
        
        # 认证错误默认最多3次
        auth_error = Exception("Authentication failed")
        assert retry_manager.should_retry(auth_error, 1) is True
        assert retry_manager.should_retry(auth_error, 3) is False
    
    def test_calculate_delay(self, retry_manager):
        """测试延迟计算"""
        network_error = Exception("Connection timeout")
        
        # 网络错误的延迟策略：基础1秒，指数退避
        delay1 = retry_manager.calculate_delay(network_error, 1)
        delay2 = retry_manager.calculate_delay(network_error, 2)
        delay3 = retry_manager.calculate_delay(network_error, 3)
        
        # 考虑到抖动，检查大致范围
        assert 0.5 <= delay1 <= 1.5
        assert 1.0 <= delay2 <= 3.0
        assert 2.0 <= delay3 <= 6.0
    
    def test_retry_function_success(self, retry_manager):
        """测试函数重试成功"""
        call_count = 0
        
        def flaky_function(value):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Network timeout")
            return f"success_{value}"
        
        # 函数在第3次调用时成功
        result = retry_manager.retry_function(flaky_function, "test", max_attempts=5)
        
        assert result == "success_test"
        assert call_count == 3
    
    def test_retry_function_failure(self, retry_manager):
        """测试函数重试失败"""
        call_count = 0
        
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent error")
        
        # 函数总是失败，应该重试指定次数后抛出异常
        with pytest.raises(Exception, match="Persistent error"):
            retry_manager.retry_function(always_failing_function, max_attempts=3)
        
        assert call_count == 3
    
    def test_retry_function_no_retry_needed(self, retry_manager):
        """测试不需要重试的情况"""
        call_count = 0
        
        def successful_function(a, b):
            nonlocal call_count
            call_count += 1
            return a + b
        
        result = retry_manager.retry_function(successful_function, 10, 20)
        
        assert result == 30
        assert call_count == 1
    
    def test_retry_function_with_custom_strategy(self, retry_manager):
        """测试使用自定义策略的函数重试"""
        call_count = 0
        
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Network error")
            return "success"
        
        # 使用自定义策略
        custom_strategy = RetryStrategy(
            max_attempts=5,
            base_delay=0.1,  # 很短的延迟以加快测试
            backoff_type="fixed",
            jitter=False
        )
        
        start_time = time.time()
        result = retry_manager.retry_function(
            flaky_function, 
            strategy=custom_strategy
        )
        end_time = time.time()
        
        assert result == "success"
        assert call_count == 2
        
        # 验证延迟时间大致正确（允许一些误差）
        assert 0.08 <= (end_time - start_time) <= 0.2
    
    @pytest.mark.asyncio
    async def test_async_retry_function(self, retry_manager):
        """测试异步函数重试"""
        call_count = 0
        
        async def async_flaky_function(value):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Async network error")
            return f"async_success_{value}"
        
        result = await retry_manager.async_retry_function(
            async_flaky_function, 
            "test", 
            max_attempts=5
        )
        
        assert result == "async_success_test"
        assert call_count == 3
    
    def test_retry_decorator_sync(self, retry_manager):
        """测试同步函数重试装饰器"""
        call_count = 0
        
        @retry_manager.retry_decorator(max_attempts=4)
        def decorated_function(multiplier):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return call_count * multiplier
        
        result = decorated_function(10)
        
        assert result == 30  # 3 * 10
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_decorator_async(self, retry_manager):
        """测试异步函数重试装饰器"""
        call_count = 0
        
        @retry_manager.retry_decorator(max_attempts=4)
        async def async_decorated_function(multiplier):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Async temporary failure")
            return call_count * multiplier
        
        result = await async_decorated_function(5)
        
        assert result == 10  # 2 * 5
        assert call_count == 2
    
    def test_retry_decorator_with_error_types(self, retry_manager):
        """测试指定错误类型的重试装饰器"""
        network_call_count = 0
        auth_call_count = 0
        
        @retry_manager.retry_decorator(
            max_attempts=3, 
            error_types=[ConnectionError]
        )
        def selective_retry_function(error_type):
            nonlocal network_call_count, auth_call_count
            
            if error_type == "network":
                network_call_count += 1
                if network_call_count < 2:
                    raise ConnectionError("Network issue")
                return "network_success"
            else:
                auth_call_count += 1
                raise ValueError("Auth issue")  # 不在重试列表中
        
        # 网络错误应该被重试
        result = selective_retry_function("network")
        assert result == "network_success"
        assert network_call_count == 2
        
        # 认证错误不应该被重试
        with pytest.raises(ValueError, match="Auth issue"):
            selective_retry_function("auth")
        assert auth_call_count == 1
    
    def test_update_strategy(self, retry_manager):
        """测试更新重试策略"""
        # 创建自定义策略
        custom_strategy = RetryStrategy(
            max_attempts=10,
            base_delay=0.5,
            max_delay=30.0
        )
        
        # 更新网络错误的策略
        retry_manager.update_strategy(RetryErrorType.NETWORK_ERROR, custom_strategy)
        
        # 验证策略已更新
        network_error = Exception("Connection timeout")
        assert retry_manager.should_retry(network_error, 8) is True  # 原来最多5次，现在10次
    
    def test_retry_statistics(self, retry_manager):
        """测试重试统计"""
        stats = retry_manager.get_retry_statistics()
        
        assert 'active_contexts' in stats
        assert 'total_strategies' in stats
        assert 'error_classifiers' in stats
        
        assert stats['active_contexts'] == 0
        assert stats['total_strategies'] == len(RetryErrorType)
        assert stats['error_classifiers'] > 0
    
    def test_context_management(self, retry_manager):
        """测试重试上下文管理"""
        call_count = 0
        
        def context_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Context test error")
            return "context_success"
        
        # 指定上下文键
        context_key = "test_context"
        result = retry_manager.retry_function(
            context_function,
            context_key=context_key,
            max_attempts=3
        )
        
        assert result == "context_success"
        
        # 验证上下文已被清理
        context = retry_manager.get_context(context_key)
        assert context is None
    
    def test_clear_contexts(self, retry_manager):
        """测试清理上下文"""
        # 创建一些上下文（通过启动但不完成的重试）
        import threading
        
        def long_running_function():
            time.sleep(1)  # 模拟长时间运行
            return "done"
        
        # 在后台线程中启动重试
        def background_retry():
            try:
                retry_manager.retry_function(long_running_function, max_attempts=1)
            except:
                pass
        
        thread = threading.Thread(target=background_retry)
        thread.start()
        
        # 等待一小段时间确保上下文被创建
        time.sleep(0.1)
        
        # 获取统计信息验证有活跃上下文
        stats_before = retry_manager.get_retry_statistics()
        
        # 清理上下文
        retry_manager.clear_contexts()
        
        # 验证上下文已被清理
        stats_after = retry_manager.get_retry_statistics()
        assert stats_after['active_contexts'] == 0
        
        # 等待后台线程完成
        thread.join()
    
    def test_concurrent_retry_operations(self, retry_manager):
        """测试并发重试操作"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def concurrent_flaky_function(thread_id):
            # 每个线程有不同的失败模式
            if thread_id % 2 == 0:
                raise Exception("Network timeout")
            return f"success_{thread_id}"
        
        def worker(thread_id):
            try:
                result = retry_manager.retry_function(
                    concurrent_flaky_function,
                    thread_id,
                    max_attempts=2
                )
                results.put(f"success_{thread_id}")
            except Exception:
                results.put(f"failed_{thread_id}")
        
        # 启动多个工作线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 收集结果
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())
        
        assert len(thread_results) == 10
        
        # 偶数线程ID应该失败（网络错误，会重试但仍然失败）
        # 奇数线程ID应该成功
        success_count = sum(1 for result in thread_results if result.startswith("success"))
        failed_count = sum(1 for result in thread_results if result.startswith("failed"))
        
        assert success_count == 5  # 奇数线程ID
        assert failed_count == 5   # 偶数线程ID
    
    @patch('time.sleep')
    def test_retry_timing(self, mock_sleep, retry_manager):
        """测试重试时间间隔"""
        call_count = 0
        
        def timed_function():
            nonlocal call_count
            call_count += 1
            if call_count < 4:  # 前3次失败
                raise Exception("Network timeout")
            return "timed_success"
        
        result = retry_manager.retry_function(timed_function, max_attempts=5)
        
        assert result == "timed_success"
        assert call_count == 4
        
        # 验证sleep被调用了3次（前3次失败后的延迟）
        assert mock_sleep.call_count == 3
        
        # 验证延迟时间递增（考虑指数退避）
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) == 3
        
        # 由于有抖动，只验证大致趋势
        assert sleep_calls[0] < sleep_calls[1] < sleep_calls[2]