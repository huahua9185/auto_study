"""
登录功能测试

测试自动化登录功能，包括验证码识别、登录状态管理和登录管理器
"""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from src.auto_study.automation import (
    CaptchaRecognizer, LoginStateManager, LoginManager, LoginStatus,
    CredentialsError, CaptchaError, FormNotFoundError
)
from src.auto_study.config.config_manager import ConfigManager


class TestCaptchaRecognizer:
    """验证码识别器测试"""
    
    def setup_method(self):
        """设置测试"""
        self.recognizer = CaptchaRecognizer(model_type='common')
    
    def create_test_image(self, width=100, height=40, text="TEST"):
        """创建测试图片"""
        from PIL import Image, ImageDraw, ImageFont
        
        # 创建白色背景图片
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # 添加文字
        try:
            # 尝试使用系统字体
            font = ImageFont.load_default()
        except:
            font = None
        
        # 计算文字位置（居中）
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = len(text) * 8
            text_height = 12
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # 绘制文字
        draw.text((x, y), text, fill='black', font=font)
        
        return image
    
    def test_init_recognizer(self):
        """测试验证码识别器初始化"""
        assert self.recognizer.model_type == 'common'
        assert self.recognizer._ocr is not None
        
        # 测试不同模型类型
        number_recognizer = CaptchaRecognizer('number')
        assert number_recognizer.model_type == 'number'
    
    def test_convert_to_pil(self):
        """测试图片格式转换"""
        # 测试PIL图像
        test_image = self.create_test_image()
        result = self.recognizer._convert_to_pil(test_image)
        assert isinstance(result, Image.Image)
        
        # 测试字节数据
        import io
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        result = self.recognizer._convert_to_pil(img_bytes)
        assert isinstance(result, Image.Image)
    
    def test_preprocess_image(self):
        """测试图片预处理"""
        test_image = self.create_test_image()
        processed = self.recognizer.preprocess_image(test_image)
        
        assert isinstance(processed, Image.Image)
        # 预处理后图片应该还存在
        assert processed.size[0] > 0
        assert processed.size[1] > 0
    
    def test_clean_result(self):
        """测试识别结果清理"""
        # 测试基本清理
        result = self.recognizer._clean_result("  AB12  \n")
        assert result == "AB12"
        
        # 测试数字模型
        number_recognizer = CaptchaRecognizer('number')
        result = number_recognizer._clean_result("A1B2C3")
        assert result == "123"
        
        # 测试字母模型
        letter_recognizer = CaptchaRecognizer('letter')
        result = letter_recognizer._clean_result("A1B2C3")
        assert result == "ABC"
    
    def test_calculate_confidence(self):
        """测试置信度计算"""
        test_image = self.create_test_image()
        
        # 测试正常长度验证码
        confidence = self.recognizer._calculate_confidence("1234", test_image)
        assert 0.0 <= confidence <= 1.0
        
        # 测试过短验证码
        confidence = self.recognizer._calculate_confidence("12", test_image)
        assert confidence < 0.8
        
        # 测试过长验证码
        confidence = self.recognizer._calculate_confidence("123456789", test_image)
        assert confidence < 0.8
    
    def test_batch_recognize(self):
        """测试批量识别"""
        images = [self.create_test_image() for _ in range(3)]
        
        with patch.object(self.recognizer, 'recognize', return_value="TEST"):
            results = self.recognizer.batch_recognize(images)
            
            assert len(results) == 3
            assert all(result == "TEST" for result in results.values())
    
    def test_save_failed_image(self):
        """测试保存失败图片"""
        test_image = self.create_test_image()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = self.recognizer.save_failed_image(test_image, temp_dir)
            
            assert save_path is not None
            assert save_path.exists()
            assert save_path.name.startswith("failed_captcha_")
    
    def test_get_recognition_stats(self):
        """测试获取识别统计"""
        stats = self.recognizer.get_recognition_stats()
        
        assert 'total_attempts' in stats
        assert 'successful_recognitions' in stats
        assert 'failed_recognitions' in stats
        assert 'success_rate' in stats
    
    def test_reset_stats(self):
        """测试重置统计"""
        # 模拟一些识别尝试
        self.recognizer._recognition_stats['total_attempts'] = 5
        self.recognizer._recognition_stats['successful_recognitions'] = 3
        
        self.recognizer.reset_stats()
        
        assert self.recognizer._recognition_stats['total_attempts'] == 0
        assert self.recognizer._recognition_stats['successful_recognitions'] == 0


class TestLoginStateManager:
    """登录状态管理器测试"""
    
    def setup_method(self):
        """设置测试"""
        self.config_manager = Mock()
        self.config_manager.get_config.return_value = {
            'login_state': {
                'check_interval': 300,
                'max_idle_time': 1800
            }
        }
        self.manager = LoginStateManager(self.config_manager)
    
    def test_init_manager(self):
        """测试状态管理器初始化"""
        assert self.manager.current_status == LoginStatus.NOT_LOGGED_IN
        assert not self.manager.is_logged_in
        assert self.manager._login_time is None
    
    def test_set_login_success(self):
        """测试设置登录成功"""
        user_info = {
            'username': 'test_user',
            'login_time': time.time(),
            'login_url': 'https://example.com'
        }
        
        self.manager.set_login_success(user_info)
        
        assert self.manager.current_status == LoginStatus.LOGGED_IN
        assert self.manager.is_logged_in
        assert self.manager._user_info == user_info
        assert self.manager._login_time is not None
    
    def test_set_login_failed(self):
        """测试设置登录失败"""
        self.manager.set_login_failed("Invalid credentials")
        
        assert self.manager.current_status == LoginStatus.LOGIN_FAILED
        assert not self.manager.is_logged_in
        assert self.manager._last_error == "Invalid credentials"
    
    def test_is_session_expired(self):
        """测试会话过期检查"""
        # 未登录状态
        assert not self.manager.is_session_expired()
        
        # 设置登录状态
        user_info = {'username': 'test_user'}
        self.manager.set_login_success(user_info)
        
        # 刚登录不应该过期
        assert not self.manager.is_session_expired()
        
        # 模拟过期时间
        self.manager._login_time = time.time() - 2000  # 超过max_idle_time
        assert self.manager.is_session_expired()
    
    def test_add_status_checker(self):
        """测试添加状态检查器"""
        mock_page = Mock()
        
        def custom_checker(page):
            return True
        
        self.manager.add_status_checker(custom_checker)
        
        # 检查器应该被添加
        assert len(self.manager._status_checkers) == 1
        
        # 测试检查器工作
        with patch.object(self.manager, '_check_default_login_indicators', return_value=LoginStatus.NOT_LOGGED_IN):
            status = self.manager.check_login_status(mock_page)
            assert status == LoginStatus.LOGGED_IN  # 自定义检查器返回True
    
    def test_check_default_login_indicators(self):
        """测试默认登录指标检查"""
        mock_page = Mock()
        
        # 模拟登录指标存在
        mock_element = Mock()
        mock_element.count.return_value = 1
        mock_page.locator.return_value = mock_element
        
        status = self.manager._check_default_login_indicators(mock_page)
        
        # 应该检查多个指标
        assert mock_page.locator.call_count > 0
    
    def test_save_and_load_login_state(self):
        """测试保存和加载登录状态"""
        mock_context = Mock()
        
        # 设置登录状态
        user_info = {'username': 'test_user'}
        self.manager.set_login_success(user_info)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 模拟状态文件路径
            with patch.object(self.manager, '_get_state_file_path', return_value=Path(temp_dir) / 'login_state.json'):
                # 保存状态
                self.manager.save_login_state(mock_context)
                
                # 创建新的管理器实例
                new_manager = LoginStateManager(self.config_manager)
                
                # 加载状态
                result = new_manager.load_login_state(mock_context)
                
                assert result
                assert new_manager.current_status == LoginStatus.LOGGED_IN
                assert new_manager._user_info == user_info


class TestLoginManager:
    """登录管理器测试"""
    
    def setup_method(self):
        """设置测试"""
        self.config_manager = Mock()
        self.config_manager.get_config.return_value = {
            'login': {
                'max_attempts': 3,
                'delay_between_attempts': 2
            },
            'credentials': {
                'username': 'test_user',
                'password': 'test_pass'
            },
            'site': {
                'login_url': 'https://example.com/login'
            }
        }
        
        self.captcha_recognizer = Mock()
        self.login_state_manager = Mock()
        
        self.manager = LoginManager(
            self.config_manager,
            self.captcha_recognizer,
            self.login_state_manager
        )
    
    def test_init_manager(self):
        """测试登录管理器初始化"""
        assert self.manager.config_manager == self.config_manager
        assert self.manager.captcha_recognizer == self.captcha_recognizer
        assert self.manager.login_state_manager == self.login_state_manager
        
        assert 'username_field' in self.manager._default_selectors
        assert 'password_field' in self.manager._default_selectors
    
    def test_set_and_get_credentials(self):
        """测试设置和获取凭据"""
        self.manager.set_credentials('new_user', 'new_pass')
        
        username, password = self.manager.get_credentials()
        assert username == 'new_user'
        assert password == 'new_pass'
        
        # 测试缺少凭据的情况
        self.manager.credentials_config = {}
        with pytest.raises(ValueError, match="登录凭据未配置或不完整"):
            self.manager.get_credentials()
    
    def test_update_selectors(self):
        """测试更新选择器"""
        new_selectors = {
            'username_field': ['#new-username'],
            'password_field': ['#new-password']
        }
        
        self.manager.update_selectors(new_selectors)
        
        assert self.manager._default_selectors['username_field'] == ['#new-username']
        assert self.manager._default_selectors['password_field'] == ['#new-password']
    
    def test_find_element(self):
        """测试查找页面元素"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_element = Mock()
        
        mock_element.count.return_value = 1
        mock_locator.first = mock_element
        mock_page.locator.return_value = mock_locator
        
        result = self.manager.find_element(mock_page, 'username_field')
        
        assert result == mock_element
        mock_element.wait_for.assert_called_once()
    
    def test_find_element_not_found(self):
        """测试元素未找到的情况"""
        mock_page = Mock()
        mock_locator = Mock()
        mock_element = Mock()
        
        # 模拟元素未找到
        mock_element.count.return_value = 0
        mock_locator.first = mock_element
        mock_page.locator.return_value = mock_locator
        
        result = self.manager.find_element(mock_page, 'username_field')
        
        assert result is None
    
    def test_fill_login_form(self):
        """测试填充登录表单"""
        mock_page = Mock()
        mock_username_field = Mock()
        mock_password_field = Mock()
        
        with patch.object(self.manager, 'find_element') as mock_find:
            mock_find.side_effect = [mock_username_field, mock_password_field]
            
            result = self.manager.fill_login_form(mock_page, 'user', 'pass')
            
            assert result
            mock_username_field.clear.assert_called_once()
            mock_password_field.clear.assert_called_once()
    
    def test_fill_login_form_missing_fields(self):
        """测试表单字段缺失的情况"""
        mock_page = Mock()
        
        with patch.object(self.manager, 'find_element', return_value=None):
            result = self.manager.fill_login_form(mock_page, 'user', 'pass')
            assert not result
    
    def test_handle_captcha_not_found(self):
        """测试验证码不存在的情况"""
        mock_page = Mock()
        
        with patch.object(self.manager, 'find_element', return_value=None):
            result = self.manager.handle_captcha(mock_page)
            assert result  # 没有验证码应该返回True
    
    def test_handle_captcha_success(self):
        """测试验证码处理成功"""
        mock_page = Mock()
        mock_captcha_field = Mock()
        mock_captcha_image = Mock()
        
        with patch.object(self.manager, 'find_element') as mock_find:
            mock_find.side_effect = [mock_captcha_field, mock_captcha_image]
            mock_captcha_image.screenshot.return_value = b'image_data'
            self.captcha_recognizer.recognize.return_value = "1234"
            
            result = self.manager.handle_captcha(mock_page)
            
            assert result
            mock_captcha_field.clear.assert_called_once()
            mock_captcha_field.type.assert_called_once_with("1234", delay=100)
            assert self.manager._login_stats['captcha_successes'] == 1
    
    def test_handle_captcha_recognition_failed(self):
        """测试验证码识别失败"""
        mock_page = Mock()
        mock_captcha_field = Mock()
        mock_captcha_image = Mock()
        
        with patch.object(self.manager, 'find_element') as mock_find:
            mock_find.side_effect = [mock_captcha_field, mock_captcha_image]
            mock_captcha_image.screenshot.return_value = b'image_data'
            self.captcha_recognizer.recognize.return_value = None  # 识别失败
            
            result = self.manager.handle_captcha(mock_page, max_attempts=2)
            
            assert not result
            assert self.manager._login_stats['captcha_attempts'] == 1
    
    def test_submit_login_form(self):
        """测试提交登录表单"""
        mock_page = Mock()
        mock_login_button = Mock()
        
        with patch.object(self.manager, 'find_element', return_value=mock_login_button):
            result = self.manager.submit_login_form(mock_page)
            
            assert result
            mock_login_button.click.assert_called_once()
    
    def test_check_login_result_success(self):
        """测试检查登录结果成功"""
        mock_page = Mock()
        
        with patch.object(self.manager, 'find_element', return_value=None):  # 没有错误消息
            self.login_state_manager.check_login_status.return_value = LoginStatus.LOGGED_IN
            
            result = self.manager.check_login_result(mock_page)
            
            assert result == LoginStatus.LOGGED_IN
    
    def test_check_login_result_error_message(self):
        """测试检查到错误消息"""
        mock_page = Mock()
        mock_error_element = Mock()
        mock_error_element.is_visible.return_value = True
        mock_error_element.text_content.return_value = "验证码错误"
        
        with patch.object(self.manager, 'find_element', return_value=mock_error_element):
            result = self.manager.check_login_result(mock_page, timeout=1000)
            
            assert result == LoginStatus.LOGIN_FAILED
    
    def test_login_success_flow(self):
        """测试完整登录成功流程"""
        mock_page = Mock()
        mock_context = Mock()
        
        with patch.multiple(
            self.manager,
            fill_login_form=Mock(return_value=True),
            handle_captcha=Mock(return_value=True),
            submit_login_form=Mock(return_value=True),
            check_login_result=Mock(return_value=LoginStatus.LOGGED_IN)
        ):
            result = self.manager.login(mock_page, mock_context)
            
            assert result
            assert self.manager._login_stats['successful_logins'] == 1
            assert self.manager._login_stats['total_attempts'] == 1
    
    def test_login_form_fill_failure(self):
        """测试登录表单填充失败"""
        mock_page = Mock()
        mock_context = Mock()
        
        with patch.object(self.manager, 'fill_login_form', return_value=False):
            result = self.manager.login(mock_page, mock_context)
            
            assert not result
            assert self.manager._login_stats['failed_logins'] == 1
    
    def test_login_captcha_failure(self):
        """测试验证码处理失败"""
        mock_page = Mock()
        mock_context = Mock()
        
        with patch.multiple(
            self.manager,
            fill_login_form=Mock(return_value=True),
            handle_captcha=Mock(return_value=False)
        ):
            result = self.manager.login(mock_page, mock_context)
            
            assert not result
            assert self.manager._login_stats['failed_logins'] == 1
    
    def test_auto_login_if_needed_force(self):
        """测试强制重新登录"""
        mock_page = Mock()
        mock_context = Mock()
        
        with patch.object(self.manager, 'login', return_value=True) as mock_login:
            result = self.manager.auto_login_if_needed(mock_page, mock_context, force_login=True)
            
            assert result
            mock_login.assert_called_once()
    
    def test_auto_login_if_needed_valid_state(self):
        """测试有效登录状态无需重新登录"""
        mock_page = Mock()
        mock_context = Mock()
        
        self.login_state_manager.load_login_state.return_value = True
        self.login_state_manager.check_login_status.return_value = LoginStatus.LOGGED_IN
        
        result = self.manager.auto_login_if_needed(mock_page, mock_context)
        
        assert result
        # 不应该调用login方法
    
    def test_logout(self):
        """测试登出功能"""
        mock_page = Mock()
        mock_context = Mock()
        mock_logout_element = Mock()
        
        # 模拟找到登出按钮
        mock_logout_element.count.return_value = 1
        mock_logout_element.is_visible.return_value = True
        mock_page.locator.return_value.first = mock_logout_element
        
        result = self.manager.logout(mock_page, mock_context)
        
        assert result
        mock_logout_element.click.assert_called_once()
        mock_context.clear_cookies.assert_called_once()
    
    def test_get_login_stats(self):
        """测试获取登录统计"""
        # 设置一些统计数据
        self.manager._login_stats['total_attempts'] = 5
        self.manager._login_stats['successful_logins'] = 3
        self.manager._login_stats['captcha_attempts'] = 2
        self.manager._login_stats['captcha_successes'] = 1
        
        self.login_state_manager.current_status = LoginStatus.LOGGED_IN
        self.login_state_manager.is_logged_in = True
        
        stats = self.manager.get_login_stats()
        
        assert stats['success_rate'] == 0.6  # 3/5
        assert stats['captcha_success_rate'] == 0.5  # 1/2
        assert stats['current_status'] == LoginStatus.LOGGED_IN.value
        assert stats['is_logged_in']
    
    def test_reset_stats(self):
        """测试重置统计"""
        # 设置一些统计数据
        self.manager._login_stats['total_attempts'] = 5
        self.manager._login_stats['successful_logins'] = 3
        
        self.manager.reset_stats()
        
        assert self.manager._login_stats['total_attempts'] == 0
        assert self.manager._login_stats['successful_logins'] == 0


class TestLoginIntegration:
    """登录功能集成测试"""
    
    def test_get_login_manager(self):
        """测试获取登录管理器实例"""
        from src.auto_study.automation.login_manager import get_login_manager
        
        manager1 = get_login_manager()
        manager2 = get_login_manager()
        
        # 应该返回同一个实例（单例模式）
        assert manager1 is manager2
    
    def test_login_error_hierarchy(self):
        """测试登录错误类层次结构"""
        from src.auto_study.automation.error_handler import (
            LoginError, CredentialsError, CaptchaError, 
            FormNotFoundError, LoginTimeoutError
        )
        
        # 测试错误继承关系
        assert issubclass(CredentialsError, LoginError)
        assert issubclass(CaptchaError, LoginError)
        assert issubclass(FormNotFoundError, LoginError)
        assert issubclass(LoginTimeoutError, LoginError)
    
    def test_login_retry_decorator(self):
        """测试登录重试装饰器"""
        from src.auto_study.automation.error_handler import login_retry, CaptchaError
        
        call_count = 0
        
        @login_retry(max_retries=2, base_delay=0.1)
        def failing_login():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CaptchaError("验证码错误")
            return True
        
        result = failing_login()
        
        assert result
        assert call_count == 3  # 初始调用 + 2次重试
    
    def test_captcha_retry_decorator(self):
        """测试验证码重试装饰器"""
        from src.auto_study.automation.error_handler import captcha_retry
        
        call_count = 0
        
        @captcha_retry(max_retries=2, base_delay=0.1)
        def failing_captcha():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return None  # 识别失败
            return "1234"  # 识别成功
        
        result = failing_captcha()
        
        assert result == "1234"
        assert call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])