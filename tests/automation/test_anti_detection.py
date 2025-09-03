"""
测试反检测机制
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.auto_study.automation.anti_detection import AntiDetection
from src.auto_study.automation.browser_manager import BrowserManager, BrowserType


class TestAntiDetection:
    """反检测机制测试"""
    
    @pytest.fixture
    def anti_detection(self):
        """创建反检测管理器实例"""
        return AntiDetection()
    
    def test_anti_detection_init(self, anti_detection):
        """测试反检测管理器初始化"""
        assert len(anti_detection._user_agents) > 0
        assert len(anti_detection._screen_resolutions) > 0
        assert len(anti_detection._timezones) > 0
        assert len(anti_detection._languages) > 0
    
    def test_get_random_user_agent(self, anti_detection):
        """测试获取随机用户代理"""
        user_agent = anti_detection.get_random_user_agent()
        
        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert 'Mozilla' in user_agent
        assert user_agent in anti_detection._user_agents
    
    def test_get_random_viewport(self, anti_detection):
        """测试获取随机视窗大小"""
        viewport = anti_detection.get_random_viewport()
        
        assert isinstance(viewport, dict)
        assert 'width' in viewport
        assert 'height' in viewport
        assert isinstance(viewport['width'], int)
        assert isinstance(viewport['height'], int)
        assert viewport['width'] > 0
        assert viewport['height'] > 0
        
        # 检查是否在预定义列表中
        resolution = (viewport['width'], viewport['height'])
        assert resolution in anti_detection._screen_resolutions
    
    def test_get_random_timezone(self, anti_detection):
        """测试获取随机时区"""
        timezone = anti_detection.get_random_timezone()
        
        assert isinstance(timezone, str)
        assert len(timezone) > 0
        assert timezone in anti_detection._timezones
    
    def test_get_random_language(self, anti_detection):
        """测试获取随机语言设置"""
        language = anti_detection.get_random_language()
        
        assert isinstance(language, str)
        assert len(language) > 0
        assert language in anti_detection._languages
    
    def test_get_detection_config(self, anti_detection):
        """测试获取反检测配置"""
        config = anti_detection.get_detection_config()
        
        assert isinstance(config, dict)
        assert 'user_agent' in config
        assert 'viewport' in config
        assert 'timezone' in config
        assert 'locale' in config
        assert 'geolocation' in config
        
        # 检查用户代理（来自指纹生成，是字符串即可）
        assert isinstance(config['user_agent'], str)
        assert len(config['user_agent']) > 0
        assert 'Mozilla' in config['user_agent']
        
        # 检查视窗（来自指纹生成，验证格式）
        viewport = config['viewport']
        assert isinstance(viewport, dict)
        assert 'width' in viewport and 'height' in viewport
        assert viewport['width'] > 0 and viewport['height'] > 0
        
        # 检查时区（来自指纹生成，是字符串即可）
        assert isinstance(config['timezone'], str)
        assert len(config['timezone']) > 0
        
        # 检查地理位置
        geolocation = config['geolocation']
        assert 'latitude' in geolocation
        assert 'longitude' in geolocation
        assert isinstance(geolocation['latitude'], (int, float))
        assert isinstance(geolocation['longitude'], (int, float))
    
    def test_stealth_script_generation(self, anti_detection):
        """测试隐身脚本生成"""
        script = anti_detection._get_stealth_script()
        
        assert isinstance(script, str)
        assert len(script) > 0
        
        # 检查关键的反检测代码
        assert 'webdriver' in script  # webdriver特征隐藏
        assert 'navigator.plugins' in script or 'plugins' in script
        assert 'navigator.languages' in script or 'languages' in script
        assert 'chrome' in script
    
    def test_fingerprint_script_generation(self, anti_detection):
        """测试指纹脚本生成"""
        script = anti_detection._get_fingerprint_script()
        
        assert isinstance(script, str)
        assert len(script) > 0
        
        # 检查关键的指纹伪造代码
        assert 'WebGLRenderingContext' in script
        assert 'HTMLCanvasElement' in script
        assert 'toDataURL' in script
    
    def test_random_delay(self, anti_detection):
        """测试随机延迟"""
        start_time = time.time()
        anti_detection.random_delay(min_ms=100, max_ms=200)
        end_time = time.time()
        
        elapsed = end_time - start_time
        # 应该在0.1到0.2秒之间（加上一些容差）
        assert 0.08 <= elapsed <= 0.25
    
    @pytest.mark.integration
    def test_setup_anti_detection_with_real_browser(self):
        """测试与真实浏览器的反检测设置集成"""
        from src.auto_study.config.config_manager import ConfigManager
        
        # 创建测试配置
        config_manager = Mock()
        config_manager.get_config.return_value = {
            'browser': {'headless': True, 'width': 1280, 'height': 720},
            'anti_detection': {},
            'system': {'data_dir': 'data'}
        }
        
        browser_manager = BrowserManager(config_manager)
        anti_detection = AntiDetection()
        
        with browser_manager.launch_browser(BrowserType.CHROMIUM):
            with browser_manager.create_context() as context:
                # 设置反检测
                anti_detection.setup_anti_detection_context(context)
                
                page = browser_manager.create_page()
                anti_detection.setup_anti_detection_page(page)
                
                # 导航到测试页面
                page.goto('data:text/html,<h1>Test</h1>')
                
                # 检查webdriver属性是否被隐藏
                webdriver_value = page.evaluate('navigator.webdriver')
                assert webdriver_value is None or webdriver_value is False
                
                # 检查plugins是否被设置
                plugins_length = page.evaluate('navigator.plugins.length')
                assert plugins_length > 0
    
    def test_simulate_human_typing_mock(self, anti_detection):
        """测试模拟人类打字（Mock版本）"""
        # 创建Mock页面
        mock_page = Mock()
        mock_element = Mock()
        mock_page.locator.return_value = mock_element
        
        # 测试打字模拟
        anti_detection.simulate_human_typing(
            mock_page, 
            '#test-input', 
            'test text',
            delay_range=(50, 100)
        )
        
        # 验证调用
        mock_page.locator.assert_called_once_with('#test-input')
        mock_element.click.assert_called_once()
        mock_element.clear.assert_called_once()
        assert mock_element.type.call_count == len('test text')
    
    def test_simulate_mouse_movement_mock(self, anti_detection):
        """测试模拟鼠标移动（Mock版本）"""
        mock_page = Mock()
        mock_mouse = Mock()
        mock_page.mouse = mock_mouse
        
        # 测试随机鼠标移动
        anti_detection.simulate_mouse_movement(mock_page)
        
        # 验证鼠标移动被调用
        assert mock_mouse.move.call_count > 0
    
    def test_simulate_scroll_behavior_mock(self, anti_detection):
        """测试模拟滚动行为（Mock版本）"""
        mock_page = Mock()
        mock_mouse = Mock()
        mock_page.mouse = mock_mouse
        
        # 测试滚动模拟
        anti_detection.simulate_scroll_behavior(mock_page, scroll_count=2)
        
        # 验证滚动被调用
        assert mock_mouse.wheel.call_count == 2
    
    def test_check_detection_risks_mock(self, anti_detection):
        """测试检测风险检查（Mock版本）"""
        mock_page = Mock()
        mock_page.evaluate.return_value = ['webdriver属性未隐藏']
        
        risks = anti_detection.check_detection_risks(mock_page)
        
        assert isinstance(risks, list)
        assert 'webdriver属性未隐藏' in risks
    
    def test_inject_mouse_events_mock(self, anti_detection):
        """测试注入鼠标事件（Mock版本）"""
        mock_page = Mock()
        
        # 测试鼠标事件注入
        anti_detection.inject_mouse_events(mock_page)
        
        # 验证JavaScript代码被执行
        mock_page.evaluate.assert_called_once()
        
        # 检查注入的代码
        injected_code = mock_page.evaluate.call_args[0][0]
        assert 'window._mouseEvents' in injected_code
        assert 'mousemove' in injected_code
    
    def test_bypass_cloudflare_mock(self, anti_detection):
        """测试绕过Cloudflare（Mock版本）"""
        mock_page = Mock()
        mock_locator = Mock()
        
        # 模拟没有Cloudflare挑战
        mock_locator.is_visible.return_value = False
        mock_page.locator.return_value = mock_locator
        
        result = anti_detection.bypass_cloudflare(mock_page, timeout=5000)
        
        assert result is True
    
    def test_user_agent_variety(self, anti_detection):
        """测试用户代理多样性"""
        user_agents = set()
        
        # 生成多个随机用户代理
        for _ in range(50):
            ua = anti_detection.get_random_user_agent()
            user_agents.add(ua)
        
        # 应该有多种不同的用户代理
        assert len(user_agents) > 1
    
    def test_viewport_variety(self, anti_detection):
        """测试视窗大小多样性"""
        viewports = set()
        
        # 生成多个随机视窗大小
        for _ in range(50):
            viewport = anti_detection.get_random_viewport()
            viewports.add((viewport['width'], viewport['height']))
        
        # 应该有多种不同的视窗大小
        assert len(viewports) > 1
    
    def test_timezone_variety(self, anti_detection):
        """测试时区多样性"""
        timezones = set()
        
        # 生成多个随机时区
        for _ in range(20):
            timezone = anti_detection.get_random_timezone()
            timezones.add(timezone)
        
        # 应该有多种不同的时区
        assert len(timezones) > 1
    
    def test_geolocation_randomization(self, anti_detection):
        """测试地理位置随机化"""
        locations = set()
        
        # 生成多个随机地理位置
        for _ in range(20):
            config = anti_detection.get_detection_config()
            geolocation = config['geolocation']
            location = (round(geolocation['latitude'], 2), round(geolocation['longitude'], 2))
            locations.add(location)
        
        # 应该有多种不同的位置（在北京附近）
        assert len(locations) > 1
        
        # 验证所有位置都在中国范围内（合理范围）
        for lat, lng in locations:
            assert 34.9 <= lat <= 44.9  # 中国纬度范围（考虑±5偏移）
            assert 106.4 <= lng <= 126.4  # 中国经度范围（考虑±10偏移）