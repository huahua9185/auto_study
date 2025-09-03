"""
登录管理器

实现自动化登录功能，包括表单填充、验证码识别和登录状态管理
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable, Union, List, Tuple
from pathlib import Path
from playwright.sync_api import Page, BrowserContext, Locator

from .captcha_recognizer import CaptchaRecognizer, recognize_captcha
from .login_state import LoginStateManager, LoginStatus
from .anti_detection import AntiDetection
from .error_handler import error_handler, retry
from ..config.config_manager import ConfigManager
from ..utils.logger import logger


class LoginManager:
    """登录管理器"""
    
    def __init__(self, 
                 config_manager: Optional[ConfigManager] = None,
                 captcha_recognizer: Optional[CaptchaRecognizer] = None,
                 login_state_manager: Optional[LoginStateManager] = None):
        """
        初始化登录管理器
        
        Args:
            config_manager: 配置管理器
            captcha_recognizer: 验证码识别器
            login_state_manager: 登录状态管理器
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        
        # 组件初始化
        self.captcha_recognizer = captcha_recognizer or CaptchaRecognizer()
        self.login_state_manager = login_state_manager or LoginStateManager(self.config_manager)
        self.anti_detection = AntiDetection()
        
        # 登录配置
        self.login_config = self.config.get('login', {})
        self.credentials_config = self.config.get('credentials', {})
        self.site_config = self.config.get('site', {})
        
        # 默认选择器配置
        self._default_selectors = {
            'username_field': ['input[name="username"]', 'input[name="user"]', 'input[type="text"]', '#username', '#user'],
            'password_field': ['input[name="password"]', 'input[type="password"]', '#password', '#pwd'],
            'captcha_field': ['input[name="captcha"]', 'input[name="verifycode"]', '#captcha', '#verifycode'],
            'captcha_image': ['img[src*="captcha"]', 'img[src*="verify"]', '.captcha-img', '#captcha-img'],
            'login_button': ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("登录")', '#login-btn'],
            'error_message': ['.error-message', '.alert-danger', '.login-error', '.error']
        }
        
        # 登录统计
        self._login_stats = {
            'total_attempts': 0,
            'successful_logins': 0,
            'failed_logins': 0,
            'captcha_attempts': 0,
            'captcha_successes': 0
        }
    
    def set_credentials(self, username: str, password: str) -> None:
        """
        设置登录凭据
        
        Args:
            username: 用户名
            password: 密码
        """
        self.credentials_config['username'] = username
        self.credentials_config['password'] = password
        logger.info("登录凭据已更新")
    
    def get_credentials(self) -> Tuple[str, str]:
        """
        获取登录凭据
        
        Returns:
            用户名和密码的元组
        """
        username = self.credentials_config.get('username', '')
        password = self.credentials_config.get('password', '')
        
        if not username or not password:
            raise ValueError("登录凭据未配置或不完整")
        
        return username, password
    
    def update_selectors(self, selectors: Dict[str, List[str]]) -> None:
        """
        更新选择器配置
        
        Args:
            selectors: 新的选择器配置
        """
        for key, value in selectors.items():
            if key in self._default_selectors:
                self._default_selectors[key] = value
                logger.info(f"选择器已更新: {key}")
    
    def find_element(self, page: Page, selector_group: str, timeout: int = 5000) -> Optional[Locator]:
        """
        查找页面元素
        
        Args:
            page: 页面对象
            selector_group: 选择器组名
            timeout: 超时时间（毫秒）
            
        Returns:
            找到的元素或None
        """
        selectors = self._default_selectors.get(selector_group, [])
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    # 等待元素可见
                    element.wait_for(state='visible', timeout=timeout)
                    logger.debug(f"找到元素: {selector_group} -> {selector}")
                    return element
            except Exception as e:
                logger.debug(f"选择器 {selector} 未找到元素: {e}")
                continue
        
        logger.warning(f"未找到 {selector_group} 元素")
        return None
    
    def fill_login_form(self, page: Page, username: str, password: str) -> bool:
        """
        填充登录表单
        
        Args:
            page: 页面对象
            username: 用户名
            password: 密码
            
        Returns:
            是否填充成功
        """
        try:
            # 查找用户名输入框
            username_field = self.find_element(page, 'username_field')
            if not username_field:
                logger.error("未找到用户名输入框")
                return False
            
            # 查找密码输入框
            password_field = self.find_element(page, 'password_field')
            if not password_field:
                logger.error("未找到密码输入框")
                return False
            
            # 清空并填充用户名
            username_field.clear()
            self.anti_detection.simulate_human_typing(page, username_field, username)
            
            # 短暂延迟
            self.anti_detection.random_delay(500, 1000)
            
            # 清空并填充密码
            password_field.clear()
            self.anti_detection.simulate_human_typing(page, password_field, password)
            
            logger.info("登录表单填充完成")
            return True
            
        except Exception as e:
            logger.error(f"填充登录表单失败: {e}")
            return False
    
    def handle_captcha(self, page: Page, max_attempts: int = 3) -> bool:
        """
        处理验证码
        
        Args:
            page: 页面对象
            max_attempts: 最大尝试次数
            
        Returns:
            是否处理成功
        """
        self._login_stats['captcha_attempts'] += 1
        
        try:
            # 查找验证码输入框
            captcha_field = self.find_element(page, 'captcha_field')
            if not captcha_field:
                logger.info("未找到验证码输入框，跳过验证码处理")
                return True
            
            # 查找验证码图片
            captcha_image = self.find_element(page, 'captcha_image')
            if not captcha_image:
                logger.error("找到验证码输入框但未找到验证码图片")
                return False
            
            for attempt in range(max_attempts):
                try:
                    logger.info(f"开始第 {attempt + 1} 次验证码识别")
                    
                    # 等待验证码图片加载
                    time.sleep(1)
                    
                    # 截取验证码图片
                    captcha_screenshot = captcha_image.screenshot()
                    
                    # 识别验证码
                    captcha_text = self.captcha_recognizer.recognize(
                        captcha_screenshot, 
                        preprocess=True,
                        max_attempts=2
                    )
                    
                    if not captcha_text:
                        logger.warning(f"验证码识别失败，尝试 {attempt + 1}/{max_attempts}")
                        
                        # 尝试刷新验证码
                        if attempt < max_attempts - 1:
                            try:
                                captcha_image.click()
                                time.sleep(1)
                            except:
                                pass
                        continue
                    
                    # 填充验证码
                    captcha_field.clear()
                    captcha_field.type(captcha_text, delay=100)
                    
                    logger.info(f"验证码识别并填充成功: {captcha_text}")
                    self._login_stats['captcha_successes'] += 1
                    return True
                    
                except Exception as e:
                    logger.error(f"验证码处理第 {attempt + 1} 次尝试失败: {e}")
                    continue
            
            logger.error(f"验证码处理失败，已尝试 {max_attempts} 次")
            return False
            
        except Exception as e:
            logger.error(f"验证码处理过程出错: {e}")
            return False
    
    def submit_login_form(self, page: Page) -> bool:
        """
        提交登录表单
        
        Args:
            page: 页面对象
            
        Returns:
            是否提交成功
        """
        try:
            # 查找登录按钮
            login_button = self.find_element(page, 'login_button')
            if not login_button:
                logger.error("未找到登录按钮")
                return False
            
            # 模拟人类行为：鼠标移动到按钮
            self.anti_detection.simulate_mouse_movement(page, login_button)
            
            # 短暂延迟后点击
            self.anti_detection.random_delay(500, 1500)
            
            # 点击登录按钮
            login_button.click()
            
            logger.info("登录表单提交完成")
            return True
            
        except Exception as e:
            logger.error(f"提交登录表单失败: {e}")
            return False
    
    def check_login_result(self, page: Page, timeout: int = 10000) -> LoginStatus:
        """
        检查登录结果
        
        Args:
            page: 页面对象
            timeout: 等待超时时间
            
        Returns:
            登录状态
        """
        try:
            # 等待页面响应
            start_time = time.time()
            
            while time.time() - start_time < timeout / 1000:
                try:
                    # 检查是否有错误消息
                    error_element = self.find_element(page, 'error_message', timeout=1000)
                    if error_element and error_element.is_visible():
                        error_text = error_element.text_content() or ""
                        logger.warning(f"登录错误消息: {error_text}")
                        
                        # 根据错误消息判断类型
                        if any(keyword in error_text.lower() for keyword in ['验证码', 'captcha', 'verify']):
                            return LoginStatus.LOGIN_FAILED  # 验证码错误
                        elif any(keyword in error_text.lower() for keyword in ['密码', 'password', '用户名', 'username']):
                            return LoginStatus.LOGIN_FAILED  # 凭据错误
                        else:
                            return LoginStatus.LOGIN_FAILED  # 其他错误
                    
                    # 使用状态管理器检查登录状态
                    status = self.login_state_manager.check_login_status(page)
                    
                    if status == LoginStatus.LOGGED_IN:
                        logger.info("登录成功确认")
                        return LoginStatus.LOGGED_IN
                    elif status == LoginStatus.NOT_LOGGED_IN:
                        # 可能还在处理中，继续等待
                        time.sleep(1)
                        continue
                    else:
                        return status
                
                except Exception as e:
                    logger.debug(f"检查登录结果时出错: {e}")
                    time.sleep(1)
                    continue
            
            # 超时后最后一次检查
            final_status = self.login_state_manager.check_login_status(page)
            logger.warning(f"登录结果检查超时，最终状态: {final_status.value}")
            return final_status
            
        except Exception as e:
            logger.error(f"检查登录结果失败: {e}")
            return LoginStatus.UNKNOWN
    
    @retry(max_retries=3, base_delay=2.0)
    def login(self, 
              page: Page, 
              context: BrowserContext,
              username: Optional[str] = None,
              password: Optional[str] = None,
              save_state: bool = True) -> bool:
        """
        执行登录操作
        
        Args:
            page: 页面对象
            context: 浏览器上下文
            username: 用户名（可选，使用配置中的）
            password: 密码（可选，使用配置中的）
            save_state: 是否保存登录状态
            
        Returns:
            是否登录成功
        """
        self._login_stats['total_attempts'] += 1
        
        try:
            # 获取登录凭据
            if username and password:
                login_username, login_password = username, password
            else:
                login_username, login_password = self.get_credentials()
            
            logger.info(f"开始登录流程，用户名: {login_username}")
            
            # 设置登录中状态
            self.login_state_manager._current_status = LoginStatus.LOGGING_IN
            
            # 导航到登录页面
            login_url = self.site_config.get('login_url')
            if login_url:
                logger.info(f"导航到登录页面: {login_url}")
                page.goto(login_url)
                page.wait_for_load_state('networkidle')
            
            # 等待页面稳定
            time.sleep(2)
            
            # 填充登录表单
            if not self.fill_login_form(page, login_username, login_password):
                self.login_state_manager.set_login_failed("表单填充失败")
                return False
            
            # 处理验证码
            if not self.handle_captcha(page):
                self.login_state_manager.set_login_failed("验证码处理失败")
                return False
            
            # 提交表单
            if not self.submit_login_form(page):
                self.login_state_manager.set_login_failed("表单提交失败")
                return False
            
            # 检查登录结果
            login_result = self.check_login_result(page)
            
            if login_result == LoginStatus.LOGGED_IN:
                # 登录成功
                user_info = {
                    'username': login_username,
                    'login_time': time.time(),
                    'login_url': page.url
                }
                
                self.login_state_manager.set_login_success(user_info)
                
                # 保存登录状态
                if save_state:
                    self.login_state_manager.save_login_state(context)
                
                self._login_stats['successful_logins'] += 1
                logger.info("登录成功")
                return True
                
            else:
                # 登录失败
                self.login_state_manager.set_login_failed(f"登录结果: {login_result.value}")
                self._login_stats['failed_logins'] += 1
                logger.error(f"登录失败: {login_result.value}")
                return False
            
        except Exception as e:
            self.login_state_manager.set_login_failed(f"登录过程异常: {e}")
            self._login_stats['failed_logins'] += 1
            logger.error(f"登录过程出现异常: {e}")
            raise
    
    def auto_login_if_needed(self, 
                           page: Page, 
                           context: BrowserContext,
                           force_login: bool = False) -> bool:
        """
        根据需要自动登录
        
        Args:
            page: 页面对象
            context: 浏览器上下文
            force_login: 是否强制重新登录
            
        Returns:
            是否已登录（或登录成功）
        """
        try:
            # 如果强制登录，直接执行登录
            if force_login:
                logger.info("强制重新登录")
                return self.login(page, context)
            
            # 尝试加载之前的登录状态
            if self.login_state_manager.load_login_state(context):
                logger.info("成功加载之前的登录状态")
                
                # 验证当前状态
                current_status = self.login_state_manager.check_login_status(page)
                if current_status == LoginStatus.LOGGED_IN:
                    logger.info("登录状态有效，无需重新登录")
                    return True
                else:
                    logger.warning(f"登录状态验证失败: {current_status.value}")
            
            # 需要重新登录
            logger.info("需要重新登录")
            return self.login(page, context)
            
        except Exception as e:
            logger.error(f"自动登录检查失败: {e}")
            return False
    
    def logout(self, page: Page, context: BrowserContext) -> bool:
        """
        执行登出操作
        
        Args:
            page: 页面对象
            context: 浏览器上下文
            
        Returns:
            是否登出成功
        """
        try:
            # 查找登出链接/按钮
            logout_selectors = [
                'a[href*="logout"]',
                'button:has-text("退出")',
                'button:has-text("登出")',
                'a:has-text("退出登录")',
                '.logout-btn',
                '#logout'
            ]
            
            logout_element = None
            for selector in logout_selectors:
                try:
                    element = page.locator(selector).first
                    if element.count() > 0 and element.is_visible():
                        logout_element = element
                        break
                except:
                    continue
            
            if not logout_element:
                logger.warning("未找到登出按钮，尝试清除登录状态")
            else:
                # 点击登出
                logout_element.click()
                logger.info("已点击登出按钮")
                
                # 等待登出完成
                time.sleep(2)
            
            # 清除登录状态
            self.login_state_manager._current_status = LoginStatus.NOT_LOGGED_IN
            self.login_state_manager._login_time = None
            self.login_state_manager._user_info = None
            
            # 清除浏览器状态
            context.clear_cookies()
            
            logger.info("登出完成")
            return True
            
        except Exception as e:
            logger.error(f"登出操作失败: {e}")
            return False
    
    def get_login_stats(self) -> Dict[str, Any]:
        """
        获取登录统计信息
        
        Returns:
            统计信息字典
        """
        stats = self._login_stats.copy()
        
        # 计算成功率
        if stats['total_attempts'] > 0:
            stats['success_rate'] = stats['successful_logins'] / stats['total_attempts']
        else:
            stats['success_rate'] = 0.0
        
        # 计算验证码成功率
        if stats['captcha_attempts'] > 0:
            stats['captcha_success_rate'] = stats['captcha_successes'] / stats['captcha_attempts']
        else:
            stats['captcha_success_rate'] = 0.0
        
        # 添加当前状态信息
        stats['current_status'] = self.login_state_manager.current_status.value
        stats['is_logged_in'] = self.login_state_manager.is_logged_in
        
        return stats
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._login_stats = {
            'total_attempts': 0,
            'successful_logins': 0,
            'failed_logins': 0,
            'captcha_attempts': 0,
            'captcha_successes': 0
        }
        logger.info("登录统计信息已重置")


# 创建默认登录管理器实例
default_login_manager = None


def get_login_manager(config_manager: Optional[ConfigManager] = None) -> LoginManager:
    """
    获取登录管理器实例
    
    Args:
        config_manager: 配置管理器
        
    Returns:
        登录管理器实例
    """
    global default_login_manager
    
    if default_login_manager is None:
        default_login_manager = LoginManager(config_manager)
    
    return default_login_manager