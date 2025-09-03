"""
测试错误处理和重试机制
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.auto_study.automation.error_handler import (
    ErrorHandler, ErrorType, RetryStrategy, error_handler, retry, safe_operation
)
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError


class TestErrorHandler:
    """错误处理器测试"""
    
    @pytest.fixture
    def error_handler_instance(self):
        """创建错误处理器实例"""
        return ErrorHandler()
    
    def test_error_handler_init(self, error_handler_instance):
        """测试错误处理器初始化"""
        assert len(error_handler_instance._error_statistics) == 6
        assert all(count == 0 for count in error_handler_instance._error_statistics.values())
        assert len(error_handler_instance._retryable_errors) > 0
        assert len(error_handler_instance._error_patterns) > 0
    
    def test_classify_error_timeout(self, error_handler_instance):
        """测试超时错误分类"""
        error = PlaywrightTimeoutError("Operation timed out")
        error_type = error_handler_instance.classify_error(error)
        
        assert error_type == ErrorType.TIMEOUT
        assert error_handler_instance._error_statistics[ErrorType.TIMEOUT] == 1
    
    def test_classify_error_network(self, error_handler_instance):
        """测试网络错误分类"""
        error = Exception("net::ERR_CONNECTION_REFUSED")
        error_type = error_handler_instance.classify_error(error)
        
        assert error_type == ErrorType.NETWORK
        assert error_handler_instance._error_statistics[ErrorType.NETWORK] == 1
    
    def test_classify_error_element_not_found(self, error_handler_instance):
        """测试元素未找到错误分类"""
        error = Exception("locator resolved to 0 elements")
        error_type = error_handler_instance.classify_error(error)
        
        assert error_type == ErrorType.ELEMENT_NOT_FOUND
        assert error_handler_instance._error_statistics[ErrorType.ELEMENT_NOT_FOUND] == 1
    
    def test_classify_error_javascript(self, error_handler_instance):
        """测试JavaScript错误分类"""
        error = Exception("ReferenceError: variable is not defined")
        error_type = error_handler_instance.classify_error(error)
        
        assert error_type == ErrorType.JAVASCRIPT
        assert error_handler_instance._error_statistics[ErrorType.JAVASCRIPT] == 1
    
    def test_classify_error_navigation(self, error_handler_instance):
        """测试导航错误分类"""
        error = Exception("navigation failed: ERR_ABORTED")
        error_type = error_handler_instance.classify_error(error)
        
        assert error_type == ErrorType.NAVIGATION
        assert error_handler_instance._error_statistics[ErrorType.NAVIGATION] == 1
    
    def test_classify_error_unknown(self, error_handler_instance):
        """测试未知错误分类"""
        error = Exception("Some unknown error message")
        error_type = error_handler_instance.classify_error(error)
        
        assert error_type == ErrorType.UNKNOWN
        assert error_handler_instance._error_statistics[ErrorType.UNKNOWN] == 1
    
    def test_is_retryable(self, error_handler_instance):
        """测试错误是否可重试"""
        # 可重试错误
        timeout_error = PlaywrightTimeoutError("timeout")
        assert error_handler_instance.is_retryable(timeout_error) is True
        
        network_error = Exception("net::ERR_NETWORK")
        assert error_handler_instance.is_retryable(network_error) is True
        
        # 不可重试错误
        js_error = Exception("ReferenceError: test")
        assert error_handler_instance.is_retryable(js_error) is False
    
    def test_calculate_delay_linear(self, error_handler_instance):
        """测试线性延迟计算"""
        delay1 = error_handler_instance.calculate_delay(1, RetryStrategy.LINEAR, base_delay=2.0)
        delay2 = error_handler_instance.calculate_delay(2, RetryStrategy.LINEAR, base_delay=2.0)
        delay3 = error_handler_instance.calculate_delay(3, RetryStrategy.LINEAR, base_delay=2.0)
        
        assert delay1 == 2.0
        assert delay2 == 4.0
        assert delay3 == 6.0
    
    def test_calculate_delay_exponential(self, error_handler_instance):
        """测试指数退避延迟计算"""
        delay1 = error_handler_instance.calculate_delay(1, RetryStrategy.EXPONENTIAL, base_delay=1.0)
        delay2 = error_handler_instance.calculate_delay(2, RetryStrategy.EXPONENTIAL, base_delay=1.0)
        delay3 = error_handler_instance.calculate_delay(3, RetryStrategy.EXPONENTIAL, base_delay=1.0)
        
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0
    
    def test_calculate_delay_fixed(self, error_handler_instance):
        """测试固定延迟计算"""
        delay1 = error_handler_instance.calculate_delay(1, RetryStrategy.FIXED, base_delay=3.0)
        delay2 = error_handler_instance.calculate_delay(2, RetryStrategy.FIXED, base_delay=3.0)
        delay3 = error_handler_instance.calculate_delay(5, RetryStrategy.FIXED, base_delay=3.0)
        
        assert delay1 == 3.0
        assert delay2 == 3.0
        assert delay3 == 3.0
    
    def test_calculate_delay_max_limit(self, error_handler_instance):
        """测试最大延迟限制"""
        delay = error_handler_instance.calculate_delay(
            10, RetryStrategy.EXPONENTIAL, base_delay=1.0, max_delay=10.0
        )
        
        assert delay == 10.0  # 应该被限制在最大值
    
    def test_retry_decorator_success(self, error_handler_instance):
        """测试重试装饰器成功场景"""
        call_count = 0
        
        @error_handler_instance.retry_on_error(max_retries=3, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise PlaywrightTimeoutError("timeout")
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_decorator_failure(self, error_handler_instance):
        """测试重试装饰器失败场景"""
        call_count = 0
        
        @error_handler_instance.retry_on_error(max_retries=2, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise PlaywrightTimeoutError("persistent timeout")
        
        with pytest.raises(PlaywrightTimeoutError):
            test_function()
        
        assert call_count == 3  # 初始调用 + 2次重试
    
    def test_retry_decorator_non_retryable(self, error_handler_instance):
        """测试不可重试错误"""
        call_count = 0
        
        @error_handler_instance.retry_on_error(max_retries=3, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            raise Exception("ReferenceError: not retryable")
        
        with pytest.raises(Exception):
            test_function()
        
        assert call_count == 1  # 只调用一次，不重试
    
    def test_safe_execute_success(self, error_handler_instance):
        """测试安全执行成功"""
        def test_function(x, y):
            return x + y
        
        result = error_handler_instance.safe_execute(
            test_function, 1, 2, max_retries=1
        )
        
        assert result == 3
    
    def test_safe_execute_with_default(self, error_handler_instance):
        """测试安全执行返回默认值"""
        def failing_function():
            raise Exception("ReferenceError: always fails")
        
        result = error_handler_instance.safe_execute(
            failing_function,
            max_retries=1,
            default_value="default",
            suppress_errors=True
        )
        
        assert result == "default"
    
    def test_safe_execute_raise_error(self, error_handler_instance):
        """测试安全执行抛出错误"""
        def failing_function():
            raise Exception("ReferenceError: always fails")
        
        with pytest.raises(Exception):
            error_handler_instance.safe_execute(
                failing_function,
                max_retries=1,
                suppress_errors=False
            )
    
    def test_handle_page_error_timeout(self, error_handler_instance):
        """测试处理页面超时错误"""
        mock_page = Mock()
        mock_page.is_closed.return_value = False
        mock_page.evaluate = Mock()
        mock_page.wait_for_load_state = Mock()
        
        error = PlaywrightTimeoutError("timeout")
        result = error_handler_instance.handle_page_error(mock_page, error)
        
        assert result is True
        mock_page.evaluate.assert_called()  # 应该调用停止加载
    
    def test_handle_page_error_network(self, error_handler_instance):
        """测试处理页面网络错误"""
        mock_page = Mock()
        mock_page.evaluate.return_value = True  # 模拟在线状态
        mock_page.reload = Mock()
        
        error = Exception("net::ERR_NETWORK")
        result = error_handler_instance.handle_page_error(mock_page, error)
        
        assert result is True
        mock_page.reload.assert_called()
    
    def test_handle_page_error_element_not_found(self, error_handler_instance):
        """测试处理元素未找到错误"""
        mock_page = Mock()
        mock_page.wait_for_load_state = Mock()
        mock_page.evaluate = Mock()
        
        error = Exception("locator resolved to 0 elements")
        result = error_handler_instance.handle_page_error(mock_page, error)
        
        assert result is True
        mock_page.wait_for_load_state.assert_called()
        mock_page.evaluate.assert_called()  # 应该调用滚动
    
    def test_get_error_statistics(self, error_handler_instance):
        """测试获取错误统计"""
        # 人工增加一些错误统计
        error_handler_instance._error_statistics[ErrorType.TIMEOUT] = 5
        error_handler_instance._error_statistics[ErrorType.NETWORK] = 3
        error_handler_instance._error_statistics[ErrorType.UNKNOWN] = 2
        
        stats = error_handler_instance.get_error_statistics()
        
        assert stats['total_errors'] == 10
        assert stats['by_type'][ErrorType.TIMEOUT] == 5
        assert stats['by_type'][ErrorType.NETWORK] == 3
        assert stats['by_type'][ErrorType.UNKNOWN] == 2
        
        assert stats['percentages']['timeout'] == 50.0
        assert stats['percentages']['network'] == 30.0
        assert stats['percentages']['unknown'] == 20.0
    
    def test_reset_statistics(self, error_handler_instance):
        """测试重置统计"""
        # 先增加一些统计
        error_handler_instance._error_statistics[ErrorType.TIMEOUT] = 5
        error_handler_instance._error_statistics[ErrorType.NETWORK] = 3
        
        # 重置
        error_handler_instance.reset_statistics()
        
        # 检查所有统计都被重置
        assert all(count == 0 for count in error_handler_instance._error_statistics.values())
    
    def test_circuit_breaker(self, error_handler_instance):
        """测试断路器功能"""
        circuit_breaker = error_handler_instance.create_circuit_breaker(
            failure_threshold=2, timeout=0.1
        )
        
        call_count = 0
        
        @circuit_breaker
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise Exception("test error")
        
        # 前两次调用应该失败但执行
        for _ in range(2):
            with pytest.raises(Exception):
                failing_function()
        
        # 第三次调用应该被断路器阻止
        with pytest.raises(Exception, match="断路器处于开启状态"):
            failing_function()
        
        assert call_count == 2  # 只有前两次实际执行了函数
        
        # 等待超时后应该进入半开状态
        time.sleep(0.15)
        
        # 现在应该允许执行（但仍然会失败）
        with pytest.raises(Exception):
            failing_function()
        
        assert call_count == 3
    
    def test_global_error_handler(self):
        """测试全局错误处理器实例"""
        assert error_handler is not None
        assert isinstance(error_handler, ErrorHandler)
    
    def test_retry_decorator_convenience(self):
        """测试便捷重试装饰器"""
        call_count = 0
        
        @retry(max_retries=2, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise PlaywrightTimeoutError("timeout")
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert call_count == 2
    
    def test_safe_operation_decorator(self):
        """测试安全操作装饰器"""
        @safe_operation(default_value="default", suppress_errors=True)
        def failing_function():
            raise Exception("ReferenceError: always fails")
        
        result = failing_function()
        assert result == "default"
    
    def test_retry_callback(self, error_handler_instance):
        """测试重试回调函数"""
        callback_calls = []
        
        def retry_callback(attempt, error):
            callback_calls.append((attempt, str(error)))
        
        @error_handler_instance.retry_on_error(
            max_retries=2, 
            base_delay=0.01,
            on_retry=retry_callback
        )
        def test_function():
            if len(callback_calls) < 1:
                raise PlaywrightTimeoutError("test timeout")
            return "success"
        
        result = test_function()
        
        assert result == "success"
        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1  # 第一次重试
        assert "test timeout" in callback_calls[0][1]
    
    def test_handle_closed_page(self, error_handler_instance):
        """测试处理已关闭页面的错误"""
        mock_page = Mock()
        mock_page.is_closed.return_value = True
        
        error = PlaywrightTimeoutError("timeout")
        result = error_handler_instance.handle_page_error(mock_page, error)
        
        assert result is False  # 页面已关闭，无法恢复
    
    def test_error_patterns_coverage(self, error_handler_instance):
        """测试错误模式覆盖率"""
        test_cases = [
            ("Timeout waiting for element", ErrorType.TIMEOUT),
            ("Operation timed out after 30000ms", ErrorType.TIMEOUT),
            ("net::ERR_CONNECTION_REFUSED", ErrorType.NETWORK),
            ("ERR_INTERNET_DISCONNECTED", ErrorType.NETWORK),
            ("strict mode violation: locator resolved to 0 elements", ErrorType.ELEMENT_NOT_FOUND),
            ("element not found", ErrorType.ELEMENT_NOT_FOUND),
            ("ReferenceError: variable is not defined", ErrorType.JAVASCRIPT),
            ("TypeError: Cannot read property", ErrorType.JAVASCRIPT),
            ("navigation failed", ErrorType.NAVIGATION),
            ("ERR_ABORTED", ErrorType.NAVIGATION),
        ]
        
        for error_message, expected_type in test_cases:
            error = Exception(error_message)
            classified_type = error_handler_instance.classify_error(error)
            assert classified_type == expected_type, f"Error '{error_message}' was classified as {classified_type}, expected {expected_type}"