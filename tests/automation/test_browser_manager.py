"""
测试浏览器管理器
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from src.auto_study.automation.browser_manager import BrowserManager, BrowserType
from src.auto_study.config.config_manager import ConfigManager


class TestBrowserManager:
    """浏览器管理器测试"""
    
    @pytest.fixture
    def temp_data_dir(self):
        """创建临时数据目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_config_manager(self, temp_data_dir):
        """Mock配置管理器"""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_config.return_value = {
            'browser': {
                'headless': True,
                'width': 1280,
                'height': 720,
                'timeout': 15000
            },
            'anti_detection': {
                'user_agent': 'Mozilla/5.0 (Test Browser)',
                'locale': 'zh-CN',
                'timezone': 'Asia/Shanghai'
            },
            'system': {
                'data_dir': temp_data_dir
            }
        }
        return config_manager
    
    @pytest.fixture
    def browser_manager(self, mock_config_manager):
        """创建浏览器管理器实例"""
        return BrowserManager(mock_config_manager)
    
    def test_browser_manager_init(self, browser_manager, temp_data_dir):
        """测试浏览器管理器初始化"""
        assert browser_manager.config_manager is not None
        assert browser_manager.config is not None
        assert browser_manager._browser is None
        assert browser_manager._context is None
        assert browser_manager._pages == []
        
        # 检查数据目录创建
        expected_browser_dir = Path(temp_data_dir) / 'browser_data'
        assert expected_browser_dir.exists()
    
    def test_get_browser_launch_options_chromium(self, browser_manager):
        """测试获取Chromium启动选项"""
        options = browser_manager._get_browser_launch_options(BrowserType.CHROMIUM)
        
        assert options['headless'] is True
        assert options['timeout'] == 15000
        assert 'args' in options
        assert '--no-sandbox' in options['args']
        assert '--disable-blink-features=AutomationControlled' in options['args']
    
    def test_get_browser_launch_options_firefox(self, browser_manager):
        """测试获取Firefox启动选项"""
        options = browser_manager._get_browser_launch_options(BrowserType.FIREFOX)
        
        assert options['headless'] is True
        assert options['timeout'] == 15000
        # Firefox没有Chrome特定的args
        assert 'args' not in options or options.get('args') is None
    
    def test_get_context_options(self, browser_manager):
        """测试获取上下文选项"""
        options = browser_manager._get_context_options()
        
        assert options['viewport']['width'] == 1280
        assert options['viewport']['height'] == 720
        assert options['user_agent'] == 'Mozilla/5.0 (Test Browser)'
        assert options['locale'] == 'zh-CN'
        assert options['timezone_id'] == 'Asia/Shanghai'
    
    def test_browser_launch_context_manager(self, browser_manager):
        """测试浏览器启动上下文管理器"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM) as browser:
            assert browser is not None
            assert browser_manager._browser is browser
            assert browser.is_connected()
        
        # 退出上下文管理器后应该清理资源
        assert browser_manager._browser is None
        assert browser_manager._playwright is None
    
    def test_create_context_manager(self, browser_manager):
        """测试创建浏览器上下文"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            with browser_manager.create_context() as context:
                assert context is not None
                assert browser_manager._context is context
                
                # 检查上下文配置
                viewport = context.pages[0].viewport_size if context.pages else None
                if viewport:
                    assert viewport['width'] == 1280
                    assert viewport['height'] == 720
        
        # 检查资源清理
        assert browser_manager._context is None
    
    def test_create_and_manage_pages(self, browser_manager):
        """测试页面创建和管理"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            with browser_manager.create_context():
                # 创建页面
                page1 = browser_manager.create_page()
                assert page1 is not None
                assert len(browser_manager._pages) == 1
                
                page2 = browser_manager.create_page()
                assert page2 is not None
                assert len(browser_manager._pages) == 2
                
                # 获取活动页面
                active_pages = browser_manager.get_active_pages()
                assert len(active_pages) == 2
                assert page1 in active_pages
                assert page2 in active_pages
                
                # 关闭页面
                browser_manager.close_page(page1)
                assert len(browser_manager._pages) == 1
                assert page1 not in browser_manager._pages
    
    def test_screenshot_page(self, browser_manager, temp_data_dir):
        """测试页面截图功能"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            with browser_manager.create_context():
                page = browser_manager.create_page()
                
                # 导航到一个简单页面
                page.goto('data:text/html,<h1>Test Page</h1>')
                
                # 截图到内存
                screenshot_data = browser_manager.screenshot_page(page)
                assert isinstance(screenshot_data, bytes)
                assert len(screenshot_data) > 0
                
                # 截图到文件
                screenshot_path = Path(temp_data_dir) / 'test_screenshot.png'
                browser_manager.screenshot_page(page, path=screenshot_path)
                assert screenshot_path.exists()
                assert screenshot_path.stat().st_size > 0
    
    def test_save_page_content_html(self, browser_manager, temp_data_dir):
        """测试保存HTML页面内容"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            with browser_manager.create_context():
                page = browser_manager.create_page()
                
                # 导航到测试页面
                test_html = '<html><head><title>Test</title></head><body><h1>Test Content</h1></body></html>'
                page.goto(f'data:text/html,{test_html}')
                
                # 保存HTML内容
                html_path = Path(temp_data_dir) / 'test_page.html'
                browser_manager.save_page_content(page, html_path, save_type='html')
                
                assert html_path.exists()
                content = html_path.read_text(encoding='utf-8')
                assert 'Test Content' in content
    
    def test_wait_for_network_idle(self, browser_manager):
        """测试网络空闲等待"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            with browser_manager.create_context():
                page = browser_manager.create_page()
                
                # 导航到简单页面
                page.goto('data:text/html,<h1>Test Page</h1>')
                
                # 等待网络空闲（应该很快完成）
                start_time = time.time()
                browser_manager.wait_for_network_idle(page, timeout=5000)
                end_time = time.time()
                
                # 应该在5秒内完成
                assert end_time - start_time < 5
    
    def test_get_browser_info(self, browser_manager):
        """测试获取浏览器信息"""
        # 浏览器未启动时
        info = browser_manager.get_browser_info()
        assert info == {}
        
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            info = browser_manager.get_browser_info()
            
            assert 'version' in info
            assert 'connected' in info
            assert 'contexts_count' in info
            assert 'pages_count' in info
            
            assert info['connected'] is True
            assert info['pages_count'] == 0
    
    def test_cleanup_on_exit(self, browser_manager):
        """测试退出时的资源清理"""
        # 使用上下文管理器
        with browser_manager:
            pass
        
        # 检查资源已清理
        assert browser_manager._playwright is None
        assert browser_manager._browser is None
        assert browser_manager._context is None
        assert browser_manager._pages == []
    
    def test_error_handling_without_browser(self, browser_manager):
        """测试在浏览器未启动时的错误处理"""
        # 尝试创建上下文应该失败
        with pytest.raises(RuntimeError, match="浏览器未启动"):
            with browser_manager.create_context():
                pass
    
    def test_error_handling_without_context(self, browser_manager):
        """测试在上下文未创建时的错误处理"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            # 尝试创建页面应该失败
            with pytest.raises(RuntimeError, match="浏览器上下文未创建"):
                browser_manager.create_page()
    
    def test_invalid_browser_type(self, browser_manager):
        """测试不支持的浏览器类型"""
        with pytest.raises(ValueError, match="不支持的浏览器类型"):
            with browser_manager.launch_browser("invalid_browser"):
                pass
    
    def test_browser_with_proxy_config(self, mock_config_manager, temp_data_dir):
        """测试带代理配置的浏览器"""
        # 更新配置包含代理
        config = mock_config_manager.get_config.return_value
        config['browser']['proxy'] = {
            'enabled': True,
            'host': 'localhost',
            'port': 8080
        }
        
        browser_manager = BrowserManager(mock_config_manager)
        options = browser_manager._get_browser_launch_options(BrowserType.CHROMIUM)
        
        assert any('--proxy-server=localhost:8080' in arg for arg in options.get('args', []))
    
    def test_multiple_pages_management(self, browser_manager):
        """测试多页面管理"""
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            with browser_manager.create_context():
                # 创建多个页面
                pages = []
                for i in range(3):
                    page = browser_manager.create_page()
                    page.goto(f'data:text/html,<h1>Page {i}</h1>')
                    pages.append(page)
                
                assert len(browser_manager._pages) == 3
                
                # 关闭中间的页面
                browser_manager.close_page(pages[1])
                assert len(browser_manager._pages) == 2
                
                # 获取活动页面应该返回剩余的页面
                active_pages = browser_manager.get_active_pages()
                assert len(active_pages) == 2
                assert pages[0] in active_pages
                assert pages[2] in active_pages
                assert pages[1] not in active_pages