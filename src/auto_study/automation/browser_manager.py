"""
浏览器管理器

负责浏览器实例的创建、配置和生命周期管理
支持多种浏览器类型，提供统一的操作接口
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from playwright.async_api import async_playwright, Browser as AsyncBrowser, BrowserContext as AsyncBrowserContext, Page as AsyncPage

from ..config.config_manager import ConfigManager
from ..utils.logger import logger


class BrowserType(Enum):
    """支持的浏览器类型"""
    CHROMIUM = "chromium"
    CHROME = "chrome"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化浏览器管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._pages: List[Page] = []
        
        # 异步属性
        self._async_playwright = None
        self._async_browser: Optional[AsyncBrowser] = None
        self._async_context: Optional[AsyncBrowserContext] = None
        self._async_pages: List[AsyncPage] = []
        
        # 浏览器配置
        self._browser_config = self.config.get('browser', {})
        self._anti_detection_config = self.config.get('anti_detection', {})
        
        # 数据目录
        self._data_dir = Path(self.config.get('system', {}).get('data_dir', 'data'))
        self._browser_data_dir = self._data_dir / 'browser_data'
        self._browser_data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_browser_launch_options(self, browser_type: BrowserType) -> Dict[str, Any]:
        """
        获取浏览器启动选项
        
        Args:
            browser_type: 浏览器类型
            
        Returns:
            启动选项字典
        """
        options = {
            'headless': self._browser_config.get('headless', False),
            'slow_mo': self._browser_config.get('slow_mo', 0),
            'timeout': self._browser_config.get('timeout', 30000),
        }
        
        # Chromium特定选项
        if browser_type in [BrowserType.CHROMIUM, BrowserType.CHROME]:
            chrome_args = [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-default-browser-check',
            ]
            
            # 代理设置
            proxy_config = self._browser_config.get('proxy')
            if proxy_config and proxy_config.get('enabled'):
                proxy_url = f"{proxy_config.get('host', 'localhost')}:{proxy_config.get('port', 8080)}"
                chrome_args.append(f'--proxy-server={proxy_url}')
            
            options['args'] = chrome_args
        
        # 用户代理设置
        user_agent = self._anti_detection_config.get('user_agent')
        if user_agent:
            options['user_agent'] = user_agent
        
        return options
    
    def _get_context_options(self) -> Dict[str, Any]:
        """
        获取浏览器上下文选项
        
        Returns:
            上下文选项字典
        """
        options = {}
        
        # 视窗大小
        viewport = {
            'width': self._browser_config.get('width', 1920),
            'height': self._browser_config.get('height', 1080)
        }
        options['viewport'] = viewport
        
        # 用户代理
        user_agent = self._anti_detection_config.get('user_agent')
        if user_agent:
            options['user_agent'] = user_agent
        
        # 地理位置
        geolocation = self._anti_detection_config.get('geolocation')
        if geolocation:
            options['geolocation'] = geolocation
            options['permissions'] = ['geolocation']
        
        # 时区
        timezone = self._anti_detection_config.get('timezone')
        if timezone:
            options['timezone_id'] = timezone
        
        # 语言
        locale = self._anti_detection_config.get('locale', 'zh-CN')
        options['locale'] = locale
        
        return options
    
    @contextmanager
    def launch_browser(self, browser_type: BrowserType = BrowserType.CHROMIUM):
        """
        启动浏览器（同步上下文管理器）
        
        Args:
            browser_type: 浏览器类型
            
        Yields:
            浏览器实例
        """
        self._playwright = sync_playwright().start()
        
        try:
            # 获取浏览器实例
            if browser_type == BrowserType.CHROMIUM:
                browser_launcher = self._playwright.chromium
            elif browser_type == BrowserType.FIREFOX:
                browser_launcher = self._playwright.firefox
            elif browser_type == BrowserType.WEBKIT:
                browser_launcher = self._playwright.webkit
            else:
                raise ValueError(f"不支持的浏览器类型: {browser_type}")
            
            # 启动浏览器
            launch_options = self._get_browser_launch_options(browser_type)
            self._browser = browser_launcher.launch(**launch_options)
            
            logger.info(f"浏览器启动成功: {browser_type.value}")
            yield self._browser
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            raise
        finally:
            self._cleanup()
    
    @contextmanager
    def create_context(self, **kwargs):
        """
        创建浏览器上下文（同步上下文管理器）
        
        Args:
            **kwargs: 额外的上下文选项
            
        Yields:
            浏览器上下文实例
        """
        if not self._browser:
            raise RuntimeError("浏览器未启动，请先调用launch_browser")
        
        try:
            # 合并上下文选项
            context_options = self._get_context_options()
            context_options.update(kwargs)
            
            # 创建上下文
            self._context = self._browser.new_context(**context_options)
            
            logger.info("浏览器上下文创建成功")
            yield self._context
            
        except Exception as e:
            logger.error(f"创建浏览器上下文失败: {e}")
            raise
        finally:
            if self._context:
                self._context.close()
                self._context = None
    
    def create_page(self) -> Page:
        """
        创建新页面
        
        Returns:
            页面实例
        """
        if not self._context:
            raise RuntimeError("浏览器上下文未创建，请先调用create_context")
        
        try:
            page = self._context.new_page()
            self._pages.append(page)
            
            # 设置默认超时
            page.set_default_timeout(self._browser_config.get('timeout', 30000))
            
            logger.info(f"新页面创建成功，当前页面数: {len(self._pages)}")
            return page
            
        except Exception as e:
            logger.error(f"创建页面失败: {e}")
            raise
    
    def close_page(self, page: Page) -> None:
        """
        关闭页面
        
        Args:
            page: 要关闭的页面
        """
        try:
            if page in self._pages:
                self._pages.remove(page)
            
            if not page.is_closed():
                page.close()
            
            logger.info(f"页面关闭成功，剩余页面数: {len(self._pages)}")
            
        except Exception as e:
            logger.error(f"关闭页面失败: {e}")
    
    def get_active_pages(self) -> List[Page]:
        """
        获取活动页面列表
        
        Returns:
            活动页面列表
        """
        # 过滤已关闭的页面
        self._pages = [page for page in self._pages if not page.is_closed()]
        return self._pages.copy()
    
    def screenshot_page(self, page: Page, path: Optional[Union[str, Path]] = None, **kwargs) -> bytes:
        """
        页面截图
        
        Args:
            page: 目标页面
            path: 保存路径，如果为None则返回字节数据
            **kwargs: 截图选项
            
        Returns:
            截图字节数据
        """
        try:
            screenshot_options = {
                'full_page': kwargs.get('full_page', True),
                'quality': kwargs.get('quality', 90),
                'type': kwargs.get('type', 'png')
            }
            
            if path:
                screenshot_path = Path(path)
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                screenshot_options['path'] = str(screenshot_path)
            
            screenshot_data = page.screenshot(**screenshot_options)
            
            if path:
                logger.info(f"页面截图保存成功: {path}")
            else:
                logger.info("页面截图完成")
            
            return screenshot_data
            
        except Exception as e:
            logger.error(f"页面截图失败: {e}")
            raise
    
    def save_page_content(self, page: Page, path: Union[str, Path], save_type: str = 'html') -> None:
        """
        保存页面内容
        
        Args:
            page: 目标页面
            path: 保存路径
            save_type: 保存类型 ('html', 'pdf')
        """
        try:
            save_path = Path(path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            if save_type.lower() == 'html':
                content = page.content()
                save_path.write_text(content, encoding='utf-8')
            elif save_type.lower() == 'pdf':
                pdf_data = page.pdf()
                save_path.write_bytes(pdf_data)
            else:
                raise ValueError(f"不支持的保存类型: {save_type}")
            
            logger.info(f"页面内容保存成功: {path}")
            
        except Exception as e:
            logger.error(f"保存页面内容失败: {e}")
            raise
    
    def wait_for_network_idle(self, page: Page, timeout: int = 30000) -> None:
        """
        等待网络空闲
        
        Args:
            page: 目标页面
            timeout: 超时时间（毫秒）
        """
        try:
            page.wait_for_load_state('networkidle', timeout=timeout)
            logger.info("网络空闲状态检测完成")
        except Exception as e:
            logger.warning(f"等待网络空闲超时: {e}")
    
    def get_browser_info(self) -> Dict[str, Any]:
        """
        获取浏览器信息
        
        Returns:
            浏览器信息字典
        """
        if not self._browser:
            return {}
        
        return {
            'version': self._browser.version,
            'connected': self._browser.is_connected(),
            'contexts_count': len(self._browser.contexts),
            'pages_count': len(self._pages)
        }
    
    def _cleanup(self) -> None:
        """清理资源"""
        try:
            # 关闭所有页面
            for page in self._pages:
                if not page.is_closed():
                    page.close()
            self._pages.clear()
            
            # 关闭上下文
            if self._context:
                self._context.close()
                self._context = None
            
            # 关闭浏览器
            if self._browser:
                self._browser.close()
                self._browser = None
            
            # 关闭Playwright
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            
            logger.info("浏览器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理浏览器资源失败: {e}")
    
    async def start_browser(self, headless: bool = None, browser_type: BrowserType = BrowserType.CHROMIUM):
        """
        启动浏览器（异步版本，用于main.py）
        
        Args:
            headless: 是否无头模式
            browser_type: 浏览器类型
        """
        if headless is not None:
            self._browser_config['headless'] = headless
            
        # 使用异步Playwright API
        self._async_playwright = await async_playwright().start()
        
        try:
            # 获取浏览器实例
            if browser_type == BrowserType.CHROMIUM:
                browser_launcher = self._async_playwright.chromium
            elif browser_type == BrowserType.FIREFOX:
                browser_launcher = self._async_playwright.firefox
            elif browser_type == BrowserType.WEBKIT:
                browser_launcher = self._async_playwright.webkit
            else:
                raise ValueError(f"不支持的浏览器类型: {browser_type}")
            
            # 启动浏览器
            launch_options = self._get_browser_launch_options(browser_type)
            self._async_browser = await browser_launcher.launch(**launch_options)
            
            # 创建上下文
            context_options = self._get_context_options()
            self._async_context = await self._async_browser.new_context(**context_options)
            
            logger.info(f"浏览器启动成功: {browser_type.value}")
            
        except Exception as e:
            logger.error(f"浏览器启动失败: {e}")
            await self._async_cleanup()
            raise
    
    async def get_page(self) -> AsyncPage:
        """
        获取或创建页面（异步版本，用于main.py）
        
        Returns:
            异步页面实例
        """
        if not self._async_context:
            raise RuntimeError("浏览器上下文未创建，请先调用start_browser")
        
        # 如果还没有页面，创建一个
        if not self._async_pages:
            return await self.create_async_page()
        
        # 返回第一个活跃页面
        active_pages = [page for page in self._async_pages if not page.is_closed()]
        if active_pages:
            return active_pages[0]
        
        # 如果没有活跃页面，创建新页面
        return await self.create_async_page()

    async def create_async_page(self) -> AsyncPage:
        """
        创建新的异步页面
        
        Returns:
            异步页面实例
        """
        if not self._async_context:
            raise RuntimeError("浏览器上下文未创建，请先调用start_browser")
        
        try:
            page = await self._async_context.new_page()
            self._async_pages.append(page)
            
            # 设置默认超时
            page.set_default_timeout(self._browser_config.get('timeout', 30000))
            
            logger.info(f"新异步页面创建成功，当前页面数: {len(self._async_pages)}")
            return page
            
        except Exception as e:
            logger.error(f"创建异步页面失败: {e}")
            raise
    
    async def _async_cleanup(self) -> None:
        """异步资源清理"""
        try:
            # 关闭所有异步页面
            for page in self._async_pages:
                if not page.is_closed():
                    await page.close()
            self._async_pages.clear()
            
            # 关闭异步上下文
            if self._async_context:
                await self._async_context.close()
                self._async_context = None
            
            # 关闭异步浏览器
            if self._async_browser:
                await self._async_browser.close()
                self._async_browser = None
            
            # 关闭异步Playwright
            if self._async_playwright:
                await self._async_playwright.stop()
                self._async_playwright = None
            
            logger.info("异步浏览器资源清理完成")
            
        except Exception as e:
            logger.error(f"异步资源清理失败: {e}")

    async def close(self):
        """关闭浏览器（异步版本）"""
        # 同时清理同步和异步资源
        await self._async_cleanup()
        self._cleanup()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self._cleanup()