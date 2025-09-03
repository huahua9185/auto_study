"""
登录状态管理器

负责管理和验证登录状态，包括状态持久化、自动检测和恢复
"""

import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from pathlib import Path
from enum import Enum
from playwright.sync_api import Page, BrowserContext

from ..utils.logger import logger
from ..config.config_manager import ConfigManager


class LoginStatus(Enum):
    """登录状态枚举"""
    NOT_LOGGED_IN = "not_logged_in"
    LOGGING_IN = "logging_in"
    LOGGED_IN = "logged_in"
    SESSION_EXPIRED = "session_expired"
    LOGIN_FAILED = "login_failed"
    UNKNOWN = "unknown"


class LoginStateManager:
    """登录状态管理器"""
    
    def __init__(self, 
                 config_manager: Optional[ConfigManager] = None,
                 data_dir: Optional[Path] = None):
        """
        初始化登录状态管理器
        
        Args:
            config_manager: 配置管理器
            data_dir: 数据存储目录
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        
        # 数据目录设置
        if data_dir:
            self._data_dir = Path(data_dir)
        else:
            self._data_dir = Path(self.config.get('system', {}).get('data_dir', 'data'))
        
        self._login_state_dir = self._data_dir / 'login_states'
        self._login_state_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前状态
        self._current_status = LoginStatus.NOT_LOGGED_IN
        self._login_time: Optional[datetime] = None
        self._last_check_time: Optional[datetime] = None
        self._user_info: Optional[Dict[str, Any]] = None
        self._session_data: Optional[Dict[str, Any]] = None
        
        # 登录状态检查配置
        self._check_config = self.config.get('login', {})
        self._check_interval = self._check_config.get('check_interval', 300)  # 5分钟
        self._session_timeout = self._check_config.get('session_timeout', 7200)  # 2小时
        
        # 状态检查器列表
        self._status_checkers: List[Callable[[Page], bool]] = []
        
        # 默认状态文件名
        self._default_state_name = 'default_login_state'
    
    def add_status_checker(self, checker: Callable[[Page], bool]) -> None:
        """
        添加自定义状态检查器
        
        Args:
            checker: 检查函数，接收Page对象，返回是否已登录
        """
        self._status_checkers.append(checker)
        logger.info("已添加自定义登录状态检查器")
    
    def check_login_status(self, page: Page, use_custom_checkers: bool = True) -> LoginStatus:
        """
        检查当前登录状态
        
        Args:
            page: 页面对象
            use_custom_checkers: 是否使用自定义检查器
            
        Returns:
            当前登录状态
        """
        try:
            self._last_check_time = datetime.now()
            
            # 使用自定义检查器
            if use_custom_checkers and self._status_checkers:
                for checker in self._status_checkers:
                    try:
                        if checker(page):
                            self._current_status = LoginStatus.LOGGED_IN
                            logger.debug("自定义检查器确认已登录")
                            return self._current_status
                    except Exception as e:
                        logger.warning(f"自定义状态检查器执行失败: {e}")
                        continue
                
                # 如果所有自定义检查器都返回False
                self._current_status = LoginStatus.NOT_LOGGED_IN
                return self._current_status
            
            # 默认检查方法
            status = self._check_default_login_indicators(page)
            self._current_status = status
            
            logger.debug(f"登录状态检查完成: {status.value}")
            return status
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            self._current_status = LoginStatus.UNKNOWN
            return self._current_status
    
    def _check_default_login_indicators(self, page: Page) -> LoginStatus:
        """
        使用默认方法检查登录指示器
        
        Args:
            page: 页面对象
            
        Returns:
            登录状态
        """
        try:
            current_url = page.url.lower()
            page_content = page.content().lower()
            
            # 检查URL指示器
            login_url_indicators = ['login', 'signin', 'auth', 'authenticate']
            logout_url_indicators = ['logout', 'signout', 'dashboard', 'profile', 'home']
            
            # 如果在登录页面
            if any(indicator in current_url for indicator in login_url_indicators):
                return LoginStatus.NOT_LOGGED_IN
            
            # 如果在已登录用户页面
            if any(indicator in current_url for indicator in logout_url_indicators):
                return LoginStatus.LOGGED_IN
            
            # 检查页面内容指示器
            logged_in_indicators = [
                '退出登录', 'logout', 'signout', '用户中心', 'dashboard',
                '个人资料', 'profile', '设置', 'settings', '欢迎'
            ]
            
            not_logged_in_indicators = [
                '登录', 'login', 'signin', '用户名', 'username', 
                '密码', 'password', '验证码', 'captcha'
            ]
            
            # 计算指示器得分
            logged_in_score = sum(1 for indicator in logged_in_indicators if indicator in page_content)
            not_logged_in_score = sum(1 for indicator in not_logged_in_indicators if indicator in page_content)
            
            if logged_in_score > not_logged_in_score:
                return LoginStatus.LOGGED_IN
            elif not_logged_in_score > logged_in_score:
                return LoginStatus.NOT_LOGGED_IN
            else:
                # 得分相等，检查更具体的元素
                try:
                    # 查找登录表单
                    login_form_selectors = [
                        'form[action*="login"]',
                        'form:has(input[name*="username"])',
                        'form:has(input[name*="password"])',
                        'form:has(input[type="password"])'
                    ]
                    
                    for selector in login_form_selectors:
                        if page.locator(selector).count() > 0:
                            return LoginStatus.NOT_LOGGED_IN
                    
                    # 查找登出链接/按钮
                    logout_selectors = [
                        'a[href*="logout"]',
                        'button:has-text("退出")',
                        'button:has-text("登出")',
                        'a:has-text("退出登录")'
                    ]
                    
                    for selector in logout_selectors:
                        if page.locator(selector).count() > 0:
                            return LoginStatus.LOGGED_IN
                    
                except Exception as e:
                    logger.debug(f"检查页面元素时出错: {e}")
            
            # 如果无法确定，返回未知状态
            return LoginStatus.UNKNOWN
            
        except Exception as e:
            logger.error(f"默认登录状态检查失败: {e}")
            return LoginStatus.UNKNOWN
    
    def set_login_success(self, 
                         user_info: Optional[Dict[str, Any]] = None,
                         session_data: Optional[Dict[str, Any]] = None) -> None:
        """
        设置登录成功状态
        
        Args:
            user_info: 用户信息
            session_data: 会话数据
        """
        self._current_status = LoginStatus.LOGGED_IN
        self._login_time = datetime.now()
        self._user_info = user_info or {}
        self._session_data = session_data or {}
        
        logger.info(f"登录状态设置为成功，用户: {user_info.get('username', 'unknown') if user_info else 'unknown'}")
    
    def set_login_failed(self, reason: Optional[str] = None) -> None:
        """
        设置登录失败状态
        
        Args:
            reason: 失败原因
        """
        self._current_status = LoginStatus.LOGIN_FAILED
        self._login_time = None
        self._user_info = None
        self._session_data = None
        
        logger.warning(f"登录状态设置为失败: {reason or 'unknown reason'}")
    
    def is_session_valid(self) -> bool:
        """
        检查会话是否仍然有效
        
        Returns:
            会话是否有效
        """
        if self._current_status != LoginStatus.LOGGED_IN:
            return False
        
        if not self._login_time:
            return False
        
        # 检查会话是否超时
        elapsed = datetime.now() - self._login_time
        if elapsed.total_seconds() > self._session_timeout:
            self._current_status = LoginStatus.SESSION_EXPIRED
            logger.warning("会话已超时")
            return False
        
        # 检查是否需要验证状态
        if self._last_check_time:
            check_elapsed = datetime.now() - self._last_check_time
            if check_elapsed.total_seconds() > self._check_interval:
                logger.debug("需要重新验证登录状态")
                return False
        
        return True
    
    def save_login_state(self, 
                        context: BrowserContext,
                        state_name: Optional[str] = None) -> bool:
        """
        保存登录状态到文件
        
        Args:
            context: 浏览器上下文（用于保存cookies等）
            state_name: 状态名称
            
        Returns:
            是否保存成功
        """
        state_name = state_name or self._default_state_name
        
        try:
            state_data = {
                'status': self._current_status.value,
                'login_time': self._login_time.isoformat() if self._login_time else None,
                'last_check_time': self._last_check_time.isoformat() if self._last_check_time else None,
                'user_info': self._user_info,
                'session_data': self._session_data,
                'saved_at': datetime.now().isoformat()
            }
            
            # 保存状态数据
            state_file = self._login_state_dir / f"{state_name}.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
            # 保存浏览器上下文（cookies等）
            if self._current_status == LoginStatus.LOGGED_IN:
                from .context_manager import ContextManager
                context_manager = ContextManager(data_dir=self._data_dir)
                context_manager.save_context_state(context, f"login_{state_name}")
            
            logger.info(f"登录状态保存成功: {state_name}")
            return True
            
        except Exception as e:
            logger.error(f"保存登录状态失败: {e}")
            return False
    
    def load_login_state(self, 
                        context: BrowserContext,
                        state_name: Optional[str] = None) -> bool:
        """
        从文件加载登录状态
        
        Args:
            context: 浏览器上下文
            state_name: 状态名称
            
        Returns:
            是否加载成功
        """
        state_name = state_name or self._default_state_name
        state_file = self._login_state_dir / f"{state_name}.json"
        
        if not state_file.exists():
            logger.info(f"登录状态文件不存在: {state_name}")
            return False
        
        try:
            # 加载状态数据
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # 恢复状态
            self._current_status = LoginStatus(state_data.get('status', 'not_logged_in'))
            
            login_time_str = state_data.get('login_time')
            self._login_time = datetime.fromisoformat(login_time_str) if login_time_str else None
            
            last_check_str = state_data.get('last_check_time')
            self._last_check_time = datetime.fromisoformat(last_check_str) if last_check_str else None
            
            self._user_info = state_data.get('user_info')
            self._session_data = state_data.get('session_data')
            
            # 检查状态是否过期
            if not self.is_session_valid():
                logger.warning("加载的登录状态已过期")
                return False
            
            # 恢复浏览器上下文
            if self._current_status == LoginStatus.LOGGED_IN:
                from .context_manager import ContextManager
                context_manager = ContextManager(data_dir=self._data_dir)
                context_manager.load_context_state(context, f"login_{state_name}")
            
            logger.info(f"登录状态加载成功: {state_name}")
            return True
            
        except Exception as e:
            logger.error(f"加载登录状态失败: {e}")
            return False
    
    def get_login_info(self) -> Dict[str, Any]:
        """
        获取登录信息
        
        Returns:
            登录信息字典
        """
        return {
            'status': self._current_status.value,
            'is_logged_in': self._current_status == LoginStatus.LOGGED_IN,
            'is_session_valid': self.is_session_valid(),
            'login_time': self._login_time.isoformat() if self._login_time else None,
            'last_check_time': self._last_check_time.isoformat() if self._last_check_time else None,
            'session_duration': (datetime.now() - self._login_time).total_seconds() if self._login_time else None,
            'user_info': self._user_info,
            'session_data': self._session_data
        }
    
    def cleanup_expired_states(self, max_age_days: int = 7) -> int:
        """
        清理过期的登录状态文件
        
        Args:
            max_age_days: 最大保存天数
            
        Returns:
            清理的文件数量
        """
        try:
            cleanup_count = 0
            current_time = datetime.now()
            max_age = timedelta(days=max_age_days)
            
            for state_file in self._login_state_dir.glob('*.json'):
                try:
                    with open(state_file, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                    
                    saved_at_str = state_data.get('saved_at')
                    if saved_at_str:
                        saved_at = datetime.fromisoformat(saved_at_str)
                        if current_time - saved_at > max_age:
                            state_file.unlink()
                            cleanup_count += 1
                            logger.info(f"清理过期登录状态文件: {state_file.name}")
                
                except Exception as e:
                    logger.warning(f"处理状态文件 {state_file.name} 时出错: {e}")
                    continue
            
            logger.info(f"登录状态清理完成，共清理 {cleanup_count} 个文件")
            return cleanup_count
            
        except Exception as e:
            logger.error(f"清理登录状态失败: {e}")
            return 0
    
    def get_saved_states(self) -> List[str]:
        """
        获取所有已保存的状态名称
        
        Returns:
            状态名称列表
        """
        try:
            states = []
            for state_file in self._login_state_dir.glob('*.json'):
                state_name = state_file.stem
                states.append(state_name)
            
            return sorted(states)
            
        except Exception as e:
            logger.error(f"获取保存的状态列表失败: {e}")
            return []
    
    def delete_saved_state(self, state_name: str) -> bool:
        """
        删除已保存的状态
        
        Args:
            state_name: 状态名称
            
        Returns:
            是否删除成功
        """
        try:
            state_file = self._login_state_dir / f"{state_name}.json"
            
            if state_file.exists():
                state_file.unlink()
                logger.info(f"登录状态已删除: {state_name}")
            
            # 同时删除对应的上下文状态
            try:
                from .context_manager import ContextManager
                context_manager = ContextManager(data_dir=self._data_dir)
                context_manager.delete_context_state(f"login_{state_name}")
            except Exception as e:
                logger.warning(f"删除对应的上下文状态失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"删除登录状态失败: {e}")
            return False
    
    @property
    def current_status(self) -> LoginStatus:
        """获取当前状态"""
        return self._current_status
    
    @property
    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self._current_status == LoginStatus.LOGGED_IN and self.is_session_valid()
    
    @property
    def user_info(self) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        return self._user_info
    
    @property
    def session_data(self) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        return self._session_data