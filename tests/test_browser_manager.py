"""
测试浏览器管理器
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.auto_study.automation.browser_manager import BrowserManager


class TestBrowserManager:
    """浏览器管理器测试"""
    
    @pytest.fixture
    def browser_manager(self):
        """创建浏览器管理器实例"""
        return BrowserManager()
    
    @pytest.mark.asyncio
    async def test_browser_manager_init(self, browser_manager):
        """测试浏览器管理器初始化"""
        assert browser_manager.playwright is None
        assert browser_manager.browser is None
        assert browser_manager.context is None
        assert browser_manager.page is None
    
    @pytest.mark.asyncio
    @patch('src.auto_study.automation.browser_manager.async_playwright')
    async def test_start_browser(self, mock_playwright, browser_manager):
        """测试启动浏览器"""
        # 设置模拟对象
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # 执行测试
        await browser_manager.start_browser(headless=True)
        
        # 验证调用
        mock_playwright.return_value.start.assert_called_once()
        mock_playwright_instance.chromium.launch.assert_called_once()
        mock_browser.new_context.assert_called_once()
        mock_context.new_page.assert_called_once()
        mock_page.add_init_script.assert_called_once()
        
        # 验证状态
        assert browser_manager.playwright == mock_playwright_instance
        assert browser_manager.browser == mock_browser
        assert browser_manager.context == mock_context
        assert browser_manager.page == mock_page
    
    @pytest.mark.asyncio
    async def test_close_browser(self, browser_manager, mock_browser, mock_context, mock_page):
        """测试关闭浏览器"""
        # 设置浏览器状态
        mock_playwright = AsyncMock()
        browser_manager.playwright = mock_playwright
        browser_manager.browser = mock_browser
        browser_manager.context = mock_context
        browser_manager.page = mock_page
        
        # 执行关闭
        await browser_manager.close()
        
        # 验证关闭调用
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.auto_study.automation.browser_manager.async_playwright')
    async def test_get_page_without_browser(self, mock_playwright, browser_manager):
        """测试在未启动浏览器时获取页面"""
        # 设置模拟对象
        mock_playwright_instance = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        
        # 执行测试
        page = await browser_manager.get_page()
        
        # 验证自动启动浏览器
        assert page == mock_page
        assert browser_manager.page == mock_page
    
    @pytest.mark.asyncio
    async def test_get_page_with_existing_browser(self, browser_manager, mock_page):
        """测试在已有浏览器时获取页面"""
        # 设置已存在的页面
        browser_manager.page = mock_page
        
        # 执行测试
        page = await browser_manager.get_page()
        
        # 验证直接返回现有页面
        assert page == mock_page
    
    @pytest.mark.asyncio
    async def test_close_with_none_objects(self, browser_manager):
        """测试在对象为None时关闭"""
        # 确保所有对象都是None
        browser_manager.playwright = None
        browser_manager.browser = None
        browser_manager.context = None
        browser_manager.page = None
        
        # 应该不抛出异常
        await browser_manager.close()
    
    @pytest.mark.asyncio 
    async def test_browser_startup_with_custom_args(self, browser_manager):
        """测试使用自定义参数启动浏览器"""
        with patch('src.auto_study.automation.browser_manager.async_playwright') as mock_playwright:
            mock_playwright_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.start = AsyncMock(return_value=mock_playwright_instance)
            mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            
            await browser_manager.start_browser(headless=False)
            
            # 验证参数传递
            launch_call = mock_playwright_instance.chromium.launch.call_args
            assert launch_call[1]['headless'] == False
            assert '--no-sandbox' in launch_call[1]['args']
            assert '--disable-blink-features=AutomationControlled' in launch_call[1]['args']
            
            # 验证上下文配置
            context_call = mock_browser.new_context.call_args
            assert context_call[1]['viewport']['width'] == 1920
            assert context_call[1]['viewport']['height'] == 1080
            assert 'Chrome/120.0.0.0' in context_call[1]['user_agent']