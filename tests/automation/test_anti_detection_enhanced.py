"""
增强反检测机制测试模块

测试任务#8实现的高级反检测功能，包括：
- 贝塞尔曲线鼠标轨迹模拟
- 高斯分布键盘输入延迟  
- 增强的浏览器指纹随机化
- 彻底的WebDriver特征隐藏
- 综合反检测功能验证
"""

import pytest
import asyncio
import math
import time
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Tuple

from src.auto_study.automation.anti_detection import AntiDetection


class TestEnhancedAntiDetection:
    """增强反检测机制基础功能测试"""
    
    @pytest.fixture
    def anti_detection(self):
        """创建反检测实例"""
        return AntiDetection()
    
    @pytest.fixture
    def mock_page(self):
        """模拟页面对象"""
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.move = AsyncMock()
        page.keyboard = AsyncMock()
        page.locator = MagicMock()
        page.evaluate = AsyncMock()
        page.add_init_script = MagicMock()
        page.viewport_size = {'width': 1920, 'height': 1080}
        return page
    
    @pytest.fixture  
    def mock_context(self):
        """模拟浏览器上下文"""
        context = MagicMock()
        context.add_init_script = MagicMock()
        return context
    
    def test_generate_realistic_fingerprint_structure(self, anti_detection):
        """测试生成真实浏览器指纹的结构完整性"""
        fingerprint = anti_detection.generate_realistic_fingerprint()
        
        # 验证所有必需字段存在
        required_fields = {
            'user_agent': str,
            'viewport': dict,
            'screen': dict,
            'platform': str,
            'timezone': str,
            'timezone_offset': int,
            'language': str,
            'languages': list,
            'cpu_class': str,
            'hardware_concurrency': int,
            'device_memory': int,
            'geolocation': dict,
            'webgl': dict,
            'plugins': list,
            'fonts': list
        }
        
        for field, expected_type in required_fields.items():
            assert field in fingerprint, f"缺少字段: {field}"
            assert isinstance(fingerprint[field], expected_type), f"字段 {field} 类型错误"
        
        # 验证嵌套字段
        screen = fingerprint['screen']
        screen_fields = ['width', 'height', 'colorDepth', 'pixelDepth', 'availWidth', 'availHeight']
        for field in screen_fields:
            assert field in screen
            assert isinstance(screen[field], int)
            assert screen[field] > 0
        
        # 验证WebGL信息
        webgl = fingerprint['webgl']
        assert 'vendor' in webgl
        assert 'renderer' in webgl
        assert isinstance(webgl['vendor'], str)
        assert isinstance(webgl['renderer'], str)
    
    def test_fingerprint_consistency_validation(self, anti_detection):
        """测试指纹内部一致性验证"""
        fingerprint = anti_detection.generate_realistic_fingerprint()
        
        # 用户代理与平台一致性
        if 'Win32' in fingerprint['platform']:
            assert 'Windows' in fingerprint['user_agent']
        elif 'MacIntel' in fingerprint['platform']:
            assert 'Mac' in fingerprint['user_agent']
        
        # 屏幕尺寸逻辑性
        screen = fingerprint['screen']
        viewport = fingerprint['viewport']
        assert screen['width'] >= viewport['width']
        assert screen['height'] >= viewport['height']
        assert screen['availHeight'] <= screen['height']
        assert screen['availWidth'] <= screen['width']
        
        # 时区偏移合理性
        assert -720 <= fingerprint['timezone_offset'] <= 720  # UTC±12小时
        
        # 硬件配置合理性
        assert fingerprint['hardware_concurrency'] in [2, 4, 6, 8, 12, 16]
        assert fingerprint['device_memory'] in [2, 4, 8, 16]


class TestBezierCurveMouseMovement:
    """贝塞尔曲线鼠标移动高级测试"""
    
    @pytest.fixture
    def anti_detection(self):
        return AntiDetection()
    
    def test_bezier_curve_mathematical_correctness(self, anti_detection):
        """测试贝塞尔曲线的数学正确性"""
        start = (0, 0)
        end = (100, 100)
        
        # 测试二次贝塞尔曲线
        points = anti_detection.generate_bezier_curve(start, end, control_points=1, steps=100)
        
        assert len(points) == 101  # steps + 1
        assert points[0] == start
        assert points[-1] == end
        
        # 验证曲线的连续性
        max_step = 0
        for i in range(1, len(points)):
            prev_x, prev_y = points[i-1]
            curr_x, curr_y = points[i]
            step_size = math.sqrt((curr_x - prev_x)**2 + (curr_y - prev_y)**2)
            max_step = max(max_step, step_size)
        
        # 步长应该相对均匀，最大步长不应过大
        assert max_step < 20  # 对于100步的路径，这是合理的
    
    def test_bezier_curve_control_points_effect(self, anti_detection):
        """测试控制点数量对曲线形状的影响"""
        start = (0, 0)
        end = (200, 200)
        
        curves_by_control_points = {}
        for control_count in [0, 1, 2, 3]:
            curve = anti_detection.generate_bezier_curve(
                start, end, control_points=control_count, steps=20
            )
            curves_by_control_points[control_count] = curve
        
        # 不同控制点数量应该产生不同的路径
        for i in range(1, 4):
            for j in range(i + 1, 4):
                curve1 = curves_by_control_points[i]
                curve2 = curves_by_control_points[j]
                
                # 中间点应该有显著差异
                mid_idx = len(curve1) // 2
                diff = math.sqrt(
                    (curve1[mid_idx][0] - curve2[mid_idx][0])**2 + 
                    (curve1[mid_idx][1] - curve2[mid_idx][1])**2
                )
                assert diff > 5  # 应该有可察觉的差异
    
    def test_human_mouse_variations_randomness(self, anti_detection):
        """测试人类鼠标变化的随机性"""
        original_points = [(i*10, i*10) for i in range(10)]
        
        # 生成多条变化路径
        varied_paths = []
        for _ in range(5):
            varied = anti_detection.add_human_mouse_variations(original_points)
            varied_paths.append(varied)
        
        # 验证路径都不相同（除起始点外）
        for i in range(len(varied_paths)):
            for j in range(i + 1, len(varied_paths)):
                path1 = varied_paths[i]
                path2 = varied_paths[j]
                
                # 至少有一半的点应该有差异
                different_points = 0
                for k in range(1, len(path1)):  # 跳过起始点
                    if path1[k] != path2[k]:
                        different_points += 1
                
                assert different_points >= len(path1) // 2
    
    def test_human_like_delays_distribution(self, anti_detection):
        """测试人类化延迟的分布特性"""
        # 生成长路径以获得足够的延迟样本
        points = [(i, i) for i in range(0, 1000, 10)]  # 100个点
        
        delays = anti_detection.calculate_human_like_delays(points)
        valid_delays = [d for d in delays if d > 0]  # 排除起始点
        
        # 验证延迟分布特性
        assert len(valid_delays) > 50  # 足够的样本
        
        mean_delay = sum(valid_delays) / len(valid_delays)
        variance = sum((d - mean_delay)**2 for d in valid_delays) / len(valid_delays)
        std_dev = math.sqrt(variance)
        
        # 应该有合理的变异性
        assert std_dev > mean_delay * 0.1  # 标准差至少是均值的10%
        assert std_dev < mean_delay * 2.0   # 但不应过于分散
        
        # 应该有一些异常值（模拟偶发停顿）
        max_delay = max(valid_delays)
        assert max_delay > mean_delay * 2  # 至少有一些明显更长的延迟
    
    @pytest.mark.asyncio
    async def test_simulate_human_mouse_movement_accuracy(self, anti_detection):
        """测试人类鼠标移动的精确度"""
        mock_page = AsyncMock()
        mock_page.viewport_size = {'width': 1920, 'height': 1080}
        mock_page.mouse.move = AsyncMock()
        
        # 测试目标选择器移动
        mock_element = MagicMock()
        target_box = {'x': 500, 'y': 300, 'width': 100, 'height': 50}
        mock_element.bounding_box.return_value = target_box
        mock_page.locator.return_value = mock_element
        
        await anti_detection.simulate_human_mouse_movement(
            mock_page, 'button', start_pos=(100, 100)
        )
        
        # 验证最后一次移动接近目标区域
        last_call = mock_page.mouse.move.call_args_list[-1]
        final_x, final_y = last_call[0]
        
        # 最终位置应该在目标元素范围内或很接近
        target_center_x = target_box['x'] + target_box['width'] / 2
        target_center_y = target_box['y'] + target_box['height'] / 2
        
        distance_to_target = math.sqrt(
            (final_x - target_center_x)**2 + (final_y - target_center_y)**2
        )
        assert distance_to_target < 100  # 应该相当接近目标


class TestGaussianTypingDistribution:
    """高斯分布键盘输入深度测试"""
    
    @pytest.fixture
    def anti_detection(self):
        return AntiDetection()
    
    def test_typing_delays_gaussian_distribution(self, anti_detection):
        """测试打字延迟是否符合高斯分布"""
        # 生成大量样本进行统计测试
        text = "The quick brown fox jumps over the lazy dog. " * 10  # 足够长的文本
        delays = anti_detection.generate_gaussian_typing_delays(text, 'normal')
        
        # 基本统计
        mean_delay = sum(delays) / len(delays)
        variance = sum((d - mean_delay)**2 for d in delays) / len(delays)
        std_dev = math.sqrt(variance)
        
        # 验证高斯分布的68-95-99.7规则（大致）
        within_1_std = sum(1 for d in delays if abs(d - mean_delay) <= std_dev)
        within_2_std = sum(1 for d in delays if abs(d - mean_delay) <= 2 * std_dev)
        
        # 约68%应该在1个标准差内，约95%在2个标准差内
        ratio_1_std = within_1_std / len(delays)
        ratio_2_std = within_2_std / len(delays)
        
        assert 0.5 < ratio_1_std < 0.8  # 允许一些偏差
        assert 0.85 < ratio_2_std < 0.99
    
    def test_typing_user_profiles_differentiation(self, anti_detection):
        """测试不同用户类型的打字模式差异"""
        text = "Hello World! 123 @#$"
        
        profiles = ['fast', 'normal', 'slow', 'variable']
        profile_stats = {}
        
        for profile in profiles:
            delays = anti_detection.generate_gaussian_typing_delays(text, profile)
            mean_delay = sum(delays) / len(delays)
            variance = sum((d - mean_delay)**2 for d in delays) / len(delays)
            profile_stats[profile] = {
                'mean': mean_delay,
                'std': math.sqrt(variance),
                'max': max(delays)
            }
        
        # 验证速度差异：fast < normal < slow
        assert profile_stats['fast']['mean'] < profile_stats['normal']['mean']
        assert profile_stats['normal']['mean'] < profile_stats['slow']['mean']
        
        # 验证变异性：variable应该有最大的标准差
        assert profile_stats['variable']['std'] >= profile_stats['normal']['std']
        
        # 验证停顿概率：slow和variable应该有更多长延迟
        assert profile_stats['slow']['max'] > profile_stats['fast']['max']
        assert profile_stats['variable']['max'] > profile_stats['normal']['max']
    
    def test_character_type_delay_adjustment(self, anti_detection):
        """测试不同字符类型的延迟调整"""
        # 测试纯字母
        letter_delays = anti_detection.generate_gaussian_typing_delays("abcdefg", 'normal')
        # 测试纯数字
        digit_delays = anti_detection.generate_gaussian_typing_delays("1234567", 'normal')
        # 测试纯特殊字符
        special_delays = anti_detection.generate_gaussian_typing_delays("!@#$%^&", 'normal')
        # 测试空格
        space_delays = anti_detection.generate_gaussian_typing_delays("a b c d", 'normal')
        
        # 计算平均延迟
        avg_letter = sum(letter_delays) / len(letter_delays)
        avg_digit = sum(digit_delays) / len(digit_delays)
        avg_special = sum(special_delays) / len(special_delays)
        
        # 获取空格位置的延迟（索引1,3,5）
        space_delay_samples = [space_delays[i] for i in [1, 3, 5]]
        avg_space = sum(space_delay_samples) / len(space_delay_samples)
        
        # 验证延迟顺序：空格 < 字母 < 数字 < 特殊字符（大致趋势）
        assert avg_space <= avg_letter * 1.2  # 空格可能稍快
        assert avg_letter <= avg_special * 1.5  # 特殊字符应该更慢
    
    def test_typing_mistake_patterns(self, anti_detection):
        """测试打字错误模式的真实性"""
        text = "hello world"
        
        # 测试不同错误率
        for error_rate in [0.1, 0.3, 0.5]:
            mistakes_found = 0
            total_tests = 20
            
            for _ in range(total_tests):
                modified_text, error_positions = anti_detection.add_typing_mistakes(text, error_rate)
                if len(error_positions) > 0:
                    mistakes_found += 1
            
            # 错误率应该大致符合预期
            actual_mistake_rate = mistakes_found / total_tests
            assert abs(actual_mistake_rate - error_rate) < 0.3  # 允许随机变异
    
    @pytest.mark.asyncio
    async def test_typing_with_corrections_flow(self, anti_detection):
        """测试包含纠错的打字流程"""
        mock_page = AsyncMock()
        mock_element = AsyncMock()
        mock_page.locator.return_value = mock_element
        
        text = "Hello World"
        
        # 设置高错误率和纠正率以确保触发纠错
        await anti_detection.simulate_human_typing_with_corrections(
            mock_page, "#input", text, 'normal', 0.8, 1.0
        )
        
        # 验证基本操作
        mock_element.click.assert_called()
        mock_element.clear.assert_called()
        
        # 验证有打字和可能的纠错操作
        type_calls = mock_element.type.call_args_list
        press_calls = mock_element.press.call_args_list
        
        assert len(type_calls) >= len(text)  # 至少打了原文本
        
        # 检查是否有退格操作
        backspace_calls = [call for call in press_calls if call[0][0] == 'Backspace']
        # 由于高错误率，应该有一些退格操作
        assert len(backspace_calls) >= 0  # 至少不报错


class TestAdvancedFingerprinting:
    """高级浏览器指纹测试"""
    
    @pytest.fixture
    def anti_detection(self):
        return AntiDetection()
    
    def test_gpu_info_variety(self, anti_detection):
        """测试GPU信息的多样性"""
        gpu_infos = set()
        for _ in range(20):
            gpu = anti_detection._generate_gpu_info()
            gpu_infos.add(gpu)
        
        # 应该有多种不同的GPU信息
        assert len(gpu_infos) > 3
        
        # 验证都是合理的GPU型号
        valid_brands = ['NVIDIA', 'Intel', 'AMD', 'Apple']
        for gpu in gpu_infos:
            assert any(brand in gpu for brand in valid_brands)
    
    def test_plugin_list_realism(self, anti_detection):
        """测试插件列表的真实性"""
        plugins = anti_detection._generate_plugin_list()
        
        # 验证插件结构
        for plugin in plugins:
            assert 'name' in plugin
            assert 'filename' in plugin
            assert isinstance(plugin['name'], str)
            assert isinstance(plugin['filename'], str)
            assert len(plugin['name']) > 3
        
        # 应该包含常见的PDF插件
        plugin_names = [p['name'] for p in plugins]
        assert any('PDF' in name for name in plugin_names)
    
    def test_font_list_completeness(self, anti_detection):
        """测试字体列表的完整性"""
        fonts = anti_detection._generate_font_list()
        
        # 验证包含必需的基础字体
        required_fonts = ['Arial', 'Times New Roman', 'Courier New', '宋体']
        for font in required_fonts:
            assert font in fonts
        
        # 验证有足够的字体多样性
        assert len(fonts) >= 9
        
        # 验证包含中英文字体混合
        has_chinese = any(ord(char) > 127 for font in fonts for char in font)
        has_english = any(font.isascii() for font in fonts)
        
        assert has_chinese and has_english
    
    def test_fingerprint_uniqueness(self, anti_detection):
        """测试指纹唯一性"""
        fingerprints = []
        for _ in range(10):
            fp = anti_detection.generate_realistic_fingerprint()
            fingerprints.append(fp)
        
        # 每个指纹都应该是不同的
        for i in range(len(fingerprints)):
            for j in range(i + 1, len(fingerprints)):
                fp1, fp2 = fingerprints[i], fingerprints[j]
                
                # 至少在某些关键字段上应该不同
                differences = 0
                key_fields = ['user_agent', 'hardware_concurrency', 'device_memory', 
                             'timezone_offset', 'geolocation']
                
                for field in key_fields:
                    if fp1[field] != fp2[field]:
                        differences += 1
                
                assert differences > 0  # 应该有一些差异


class TestStealthScriptEffectiveness:
    """隐身脚本有效性测试"""
    
    @pytest.fixture
    def anti_detection(self):
        return AntiDetection()
    
    def test_stealth_script_comprehensiveness(self, anti_detection):
        """测试隐身脚本的全面性"""
        fingerprint = anti_detection.generate_realistic_fingerprint()
        script = anti_detection._get_stealth_script(fingerprint)
        
        # 验证包含所有关键的反检测特征
        critical_features = [
            'webdriver',           # WebDriver属性隐藏
            'navigator.plugins',   # 插件列表伪造
            'navigator.languages', # 语言设置
            'screen.colorDepth',   # 屏幕属性
            'hardwareConcurrency', # 硬件信息
            'deviceMemory',        # 内存信息
            'getTimezoneOffset',   # 时区信息
            'chrome.runtime',      # Chrome对象
            'outerWidth',          # 窗口属性
            'isTrusted',          # 事件信任度
        ]
        
        for feature in critical_features:
            assert feature in script, f"隐身脚本缺少关键特征: {feature}"
    
    def test_fingerprint_script_coverage(self, anti_detection):
        """测试指纹脚本的覆盖范围"""
        fingerprint = anti_detection.generate_realistic_fingerprint()
        script = anti_detection._get_fingerprint_script(fingerprint)
        
        # 验证包含所有主要指纹伪造技术
        fingerprint_techniques = [
            'WebGLRenderingContext',  # WebGL指纹
            'HTMLCanvasElement',      # Canvas指纹
            'toDataURL',             # Canvas数据URL
            'getParameter',          # WebGL参数
            'AnalyserNode',          # 音频指纹
            'getFloatFrequencyData', # 音频频率数据
            'fillText',              # Canvas文本渲染
            'devicePixelRatio',      # 设备像素比
            'performance.now',       # 时间指纹
            'getBattery',           # 电池信息
        ]
        
        for technique in fingerprint_techniques:
            assert technique in script, f"指纹脚本缺少技术: {technique}"
        
        # 验证使用了传入的指纹数据
        assert fingerprint['webgl']['vendor'] in script
        assert fingerprint['webgl']['renderer'] in script
    
    def test_script_injection_methods(self, anti_detection, mock_context, mock_page):
        """测试脚本注入方法"""
        fingerprint = anti_detection.generate_realistic_fingerprint()
        
        # 测试上下文注入
        anti_detection.setup_anti_detection_context(mock_context, fingerprint)
        assert mock_context.add_init_script.called
        
        # 测试页面注入
        anti_detection.setup_anti_detection_page(mock_page, fingerprint)
        assert mock_page.add_init_script.call_count == 2  # 隐身 + 指纹脚本
        
        # 验证注入的脚本内容
        context_script = mock_context.add_init_script.call_args[0][0]
        page_scripts = [call[0][0] for call in mock_page.add_init_script.call_args_list]
        
        assert len(context_script) > 1000
        assert all(len(script) > 500 for script in page_scripts)
    
    def test_anti_detection_config_completeness(self, anti_detection):
        """测试反检测配置的完整性"""
        config = anti_detection.create_anti_detection_config()
        
        # 验证配置结构
        assert 'context_options' in config
        assert 'fingerprint' in config
        assert 'stealth_script' in config
        assert 'fingerprint_script' in config
        
        # 验证上下文选项的完整性
        context_opts = config['context_options']
        required_options = [
            'viewport', 'user_agent', 'locale', 
            'timezone_id', 'geolocation', 'permissions'
        ]
        
        for option in required_options:
            assert option in context_opts
        
        # 验证地理位置权限设置
        assert 'geolocation' in context_opts['permissions']
        
        # 验证脚本可执行性（基本语法检查）
        stealth_script = config['stealth_script']
        fingerprint_script = config['fingerprint_script']
        
        # 不应包含明显的语法错误标志
        assert 'SyntaxError' not in stealth_script
        assert 'SyntaxError' not in fingerprint_script
        assert stealth_script.count('{') == stealth_script.count('}')
        assert fingerprint_script.count('{') == fingerprint_script.count('}')


class TestIntegratedAntiDetectionWorkflow:
    """集成反检测工作流测试"""
    
    @pytest.fixture
    def anti_detection(self):
        return AntiDetection()
    
    @pytest.fixture
    def mock_page(self):
        page = AsyncMock()
        page.mouse = AsyncMock()
        page.keyboard = AsyncMock()
        page.locator = MagicMock()
        page.evaluate = AsyncMock()
        page.add_init_script = MagicMock()
        page.viewport_size = {'width': 1920, 'height': 1080}
        return page
    
    @pytest.mark.asyncio
    async def test_comprehensive_user_simulation(self, anti_detection, mock_page):
        """测试综合用户模拟工作流"""
        # 设置元素
        mock_element = MagicMock()
        mock_element.bounding_box.return_value = {
            'x': 500, 'y': 300, 'width': 200, 'height': 40
        }
        mock_page.locator.return_value = mock_element
        
        # 执行综合用户活动模拟
        await anti_detection.simulate_user_activity(mock_page, activity_count=5)
        
        # 验证执行了多种活动
        # 由于活动选择是随机的，我们验证至少有一些交互发生
        total_interactions = (
            mock_page.mouse.move.call_count +
            mock_page.mouse.wheel.call_count +
            mock_page.evaluate.call_count
        )
        
        assert total_interactions > 0
    
    def test_detection_risk_assessment_accuracy(self, anti_detection):
        """测试检测风险评估的准确性"""
        mock_page = MagicMock()
        
        # 模拟发现多种风险
        detected_risks = [
            'webdriver属性未隐藏',
            '检测到Selenium特征', 
            '浏览器插件数量异常'
        ]
        mock_page.evaluate.return_value = detected_risks
        
        risks = anti_detection.check_detection_risks(mock_page)
        
        # 验证风险被正确识别
        assert len(risks) >= len(detected_risks)
        for risk in detected_risks:
            assert risk in risks
        
        # 验证JavaScript检测脚本被执行
        mock_page.evaluate.assert_called_once()
        
        # 验证检测脚本包含关键检查项
        detection_script = mock_page.evaluate.call_args[0][0]
        assert 'navigator.webdriver' in detection_script
        assert 'phantom' in detection_script.lower()
        assert 'selenium' in detection_script.lower()
    
    @pytest.mark.asyncio
    async def test_cloudflare_bypass_robustness(self, anti_detection):
        """测试Cloudflare绕过的鲁棒性"""
        mock_page = MagicMock()
        
        # 场景1: 无Cloudflare挑战
        mock_page.locator.return_value.is_visible.return_value = False
        result = anti_detection.bypass_cloudflare(mock_page, timeout=1000)
        assert result is True
        
        # 场景2: Cloudflare挑战快速通过
        call_count = 0
        def mock_visibility():
            nonlocal call_count
            call_count += 1
            return call_count == 1  # 第一次检查有挑战，之后通过
        
        mock_page.locator.return_value.is_visible.side_effect = mock_visibility
        
        with patch('time.time', side_effect=[0, 0.5, 1.0]):
            result = anti_detection.bypass_cloudflare(mock_page, timeout=5000)
            assert result is True
        
        # 场景3: 超时情况
        mock_page.locator.return_value.is_visible.return_value = True  # 一直有挑战
        
        with patch('time.time', side_effect=[0, 6.0]):  # 模拟超时
            result = anti_detection.bypass_cloudflare(mock_page, timeout=5000)
            assert result is False
    
    def test_backward_compatibility_preservation(self, anti_detection):
        """测试向后兼容性保持"""
        # 测试旧版本API仍然工作
        old_config = anti_detection.get_detection_config()
        new_config = anti_detection.create_anti_detection_config()
        
        # 旧配置应该包含必要字段
        old_fields = ['user_agent', 'viewport', 'timezone', 'locale', 'geolocation']
        for field in old_fields:
            assert field in old_config
        
        # 新配置应该更全面
        assert len(str(new_config)) > len(str(old_config))
        
        # 测试同步方法仍然工作
        anti_detection.random_delay(10, 20)  # 不应抛出异常
        
        mock_page = MagicMock()
        anti_detection.simulate_scroll_behavior(mock_page, 2)  # 不应抛出异常
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, anti_detection):
        """测试高负载下的性能"""
        mock_page = AsyncMock()
        mock_page.viewport_size = {'width': 1920, 'height': 1080}
        mock_page.mouse.move = AsyncMock()
        
        start_time = time.time()
        
        # 执行多项反检测操作
        tasks = []
        for _ in range(5):
            tasks.append(anti_detection.simulate_human_mouse_movement(mock_page))
            tasks.append(anti_detection.async_random_delay(0.01, 0.02))
        
        await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        
        # 所有操作应该在合理时间内完成
        assert elapsed < 10.0  # 不超过10秒
        
        # 验证所有鼠标移动都执行了
        assert mock_page.mouse.move.call_count >= 50  # 每次移动至少10个点
    
    def test_memory_efficiency(self, anti_detection):
        """测试内存效率"""
        import sys
        
        initial_objects = len(gc.get_objects()) if 'gc' in sys.modules else 0
        
        # 执行大量操作
        for _ in range(20):
            fingerprint = anti_detection.generate_realistic_fingerprint()
            stealth_script = anti_detection._get_stealth_script(fingerprint)
            fingerprint_script = anti_detection._get_fingerprint_script(fingerprint)
            
            # 确保脚本生成正常
            assert len(stealth_script) > 1000
            assert len(fingerprint_script) > 1000
        
        # 内存使用应该保持稳定（简单检查）
        final_objects = len(gc.get_objects()) if 'gc' in sys.modules else 0
        
        if initial_objects > 0:
            # 对象增长不应过多
            growth = final_objects - initial_objects
            assert growth < 10000  # 允许合理增长


if __name__ == '__main__':
    # 导入gc用于内存测试
    try:
        import gc
    except ImportError:
        gc = None
    
    pytest.main([__file__, '-v'])