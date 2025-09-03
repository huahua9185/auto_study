"""
反检测机制模块

提供浏览器指纹伪造、行为模拟等反检测功能
帮助自动化脚本避免被网站检测识别
"""

import random
import time
import asyncio
import math
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from playwright.sync_api import Page, BrowserContext
from playwright.async_api import Page as AsyncPage

from ..utils.logger import logger


class AntiDetection:
    """反检测机制管理器"""
    
    def __init__(self):
        """初始化反检测管理器"""
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        
        self._screen_resolutions = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1280, 720),
            (1680, 1050),
            (2560, 1440)
        ]
        
        self._timezones = [
            "Asia/Shanghai",
            "Asia/Beijing", 
            "Asia/Hong_Kong",
            "Asia/Taipei",
            "Asia/Tokyo"
        ]
        
        self._languages = [
            "zh-CN,zh;q=0.9,en;q=0.8",
            "zh-CN,zh;q=0.9",
            "zh,en-US;q=0.9,en;q=0.8",
            "zh-CN"
        ]
    
    def get_random_user_agent(self) -> str:
        """
        获取随机用户代理字符串
        
        Returns:
            随机用户代理
        """
        return random.choice(self._user_agents)
    
    def get_random_viewport(self) -> Dict[str, int]:
        """
        获取随机视窗大小
        
        Returns:
            包含width和height的字典
        """
        width, height = random.choice(self._screen_resolutions)
        return {"width": width, "height": height}
    
    def get_random_timezone(self) -> str:
        """
        获取随机时区
        
        Returns:
            时区字符串
        """
        return random.choice(self._timezones)
    
    def get_random_language(self) -> str:
        """
        获取随机语言设置
        
        Returns:
            语言字符串
        """
        return random.choice(self._languages)
    
    def setup_anti_detection_context(self, context: BrowserContext, fingerprint: Dict[str, Any] = None) -> None:
        """
        为浏览器上下文设置反检测
        
        Args:
            context: 浏览器上下文
            fingerprint: 浏览器指纹配置
        """
        try:
            if not fingerprint:
                fingerprint = self.generate_realistic_fingerprint()
            
            # 添加初始化脚本，隐藏自动化特征
            context.add_init_script(self._get_stealth_script(fingerprint))
            logger.info("浏览器上下文反检测设置完成")
        except Exception as e:
            logger.error(f"设置浏览器上下文反检测失败: {e}")
    
    def setup_anti_detection_page(self, page: Page, fingerprint: Dict[str, Any] = None) -> None:
        """
        为页面设置反检测
        
        Args:
            page: 页面对象
            fingerprint: 浏览器指纹配置
        """
        try:
            if not fingerprint:
                fingerprint = self.generate_realistic_fingerprint()
            
            # 添加初始化脚本
            page.add_init_script(self._get_stealth_script(fingerprint))
            
            # 设置额外的反检测属性
            page.add_init_script(self._get_fingerprint_script(fingerprint))
            
            logger.info("页面反检测设置完成")
        except Exception as e:
            logger.error(f"设置页面反检测失败: {e}")
    
    def _get_stealth_script(self, fingerprint: Dict[str, Any] = None) -> str:
        """
        获取增强的隐身脚本，彻底隐藏自动化特征
        
        Args:
            fingerprint: 浏览器指纹配置
        
        Returns:
            JavaScript代码字符串
        """
        if not fingerprint:
            fingerprint = self.generate_realistic_fingerprint()
        
        return f"""
        // =============基础WebDriver特征隐藏=============
        
        // 隐藏webdriver属性
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
        }});
        
        // 删除Selenium特征
        delete window.document.$cdc_asdjflasutopfhvcZLmcfl_;
        delete window.$chrome_asyncScriptInfo;
        delete window.$cdc_asdjflasutopfhvcZLmcfl_;
        
        // 隐藏PhantomJS特征
        delete window.callPhantom;
        delete window._phantom;
        delete window.__phantom;
        
        // =============浏览器指纹伪造=============
        
        // 重写navigator属性
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{fingerprint['platform']}'
        }});
        
        Object.defineProperty(navigator, 'languages', {{
            get: () => {fingerprint['languages']}
        }});
        
        Object.defineProperty(navigator, 'language', {{
            get: () => '{fingerprint['language']}'
        }});
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {fingerprint['hardware_concurrency']}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {fingerprint['device_memory']}
        }});
        
        // 重写screen属性
        Object.defineProperty(screen, 'width', {{
            get: () => {fingerprint['screen']['width']}
        }});
        
        Object.defineProperty(screen, 'height', {{
            get: () => {fingerprint['screen']['height']}
        }});
        
        Object.defineProperty(screen, 'availWidth', {{
            get: () => {fingerprint['screen']['availWidth']}
        }});
        
        Object.defineProperty(screen, 'availHeight', {{
            get: () => {fingerprint['screen']['availHeight']}
        }});
        
        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {fingerprint['screen']['colorDepth']}
        }});
        
        Object.defineProperty(screen, 'pixelDepth', {{
            get: () => {fingerprint['screen']['pixelDepth']}
        }});
        
        // 重写Date时区信息
        const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function() {{
            return {fingerprint['timezone_offset']};
        }};
        
        // =============插件和字体伪造=============
        
        // 重写plugins属性
        const pluginArray = {json.dumps(fingerprint['plugins'])};
        Object.defineProperty(navigator, 'plugins', {{
            get: () => {{
                const plugins = [];
                pluginArray.forEach((plugin, index) => {{
                    plugins[index] = {{
                        name: plugin.name,
                        filename: plugin.filename,
                        description: plugin.name,
                        length: 1,
                        item: () => null,
                        namedItem: () => null
                    }};
                }});
                plugins.length = pluginArray.length;
                plugins.refresh = () => {{}};
                return plugins;
            }}
        }});
        
        // 伪造字体检测
        const originalOffsetWidth = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetWidth');
        const originalOffsetHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
        
        // 添加微小的随机偏移来模糊字体指纹
        Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {{
            get: function() {{
                const width = originalOffsetWidth.get.call(this);
                return width + (Math.random() - 0.5) * 0.1;
            }}
        }});
        
        Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {{
            get: function() {{
                const height = originalOffsetHeight.get.call(this);
                return height + (Math.random() - 0.5) * 0.1;
            }}
        }});
        
        // =============高级反检测=============
        
        // 防止检测自动化框架
        Object.defineProperty(window, 'outerWidth', {{
            get: () => {fingerprint['screen']['width']}
        }});
        
        Object.defineProperty(window, 'outerHeight', {{
            get: () => {fingerprint['screen']['height']}
        }});
        
        // 伪造Chrome对象
        if (!window.chrome) {{
            window.chrome = {{}};
        }}
        
        window.chrome.runtime = {{
            onConnect: undefined,
            onMessage: undefined
        }};
        
        // 隐藏自动化相关的全局变量
        ['webdriver', 'driver', 'domAutomation', 'domAutomationController'].forEach(prop => {{
            if (window[prop]) {{
                delete window[prop];
            }}
        }});
        
        // 修改iframe检测
        Object.defineProperty(window, 'top', {{
            get: () => window
        }});
        
        Object.defineProperty(window, 'parent', {{
            get: () => window  
        }});
        
        // 防止检测鼠标事件模拟
        const originalDispatchEvent = EventTarget.prototype.dispatchEvent;
        EventTarget.prototype.dispatchEvent = function(event) {{
            if (event.isTrusted === false && event.type.startsWith('mouse')) {{
                Object.defineProperty(event, 'isTrusted', {{
                    get: () => true
                }});
            }}
            return originalDispatchEvent.call(this, event);
        }};
        
        // 伪造正常的权限API
        const originalPermissionsQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {{
            const permission = parameters.name;
            if (permission === 'notifications') {{
                return Promise.resolve({{ state: 'default' }});
            }}
            return originalPermissionsQuery.call(this, parameters);
        }};
        
        // 添加真实的触摸支持
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: () => 0  // 桌面端不支持触摸
        }});
        
        console.log('🔒 反棂测脚本已加载');
        """
    
    def _get_fingerprint_script(self, fingerprint: Dict[str, Any] = None) -> str:
        """
        获取增强的浏览器指纹伪造脚本
        
        Args:
            fingerprint: 浏览器指纹配置
        
        Returns:
            JavaScript代码字符串
        """
        if not fingerprint:
            fingerprint = self.generate_realistic_fingerprint()
        
        webgl_vendor = fingerprint['webgl']['vendor']
        webgl_renderer = fingerprint['webgl']['renderer']
        
        return f"""
        // =============WebGL指纹伪造=============
        
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            // VENDOR
            if (parameter === 37445 || parameter === this.VENDOR) {{
                return '{webgl_vendor}';
            }}
            // RENDERER 
            if (parameter === 37446 || parameter === this.RENDERER) {{
                return '{webgl_renderer}';
            }}
            // VERSION
            if (parameter === 37447 || parameter === this.VERSION) {{
                return 'WebGL 1.0 (OpenGL ES 2.0)';
            }}
            // SHADING_LANGUAGE_VERSION
            if (parameter === 35724 || parameter === this.SHADING_LANGUAGE_VERSION) {{
                return 'WebGL GLSL ES 1.0';
            }}
            return getParameter.call(this, parameter);
        }};
        
        // WebGL2支持
        if (window.WebGL2RenderingContext) {{
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) return '{webgl_vendor}';
                if (parameter === 37446) return '{webgl_renderer}';
                return getParameter2.call(this, parameter);
            }};
        }}
        
        // =============Canvas指纹伪造=============
        
        // 更精细的Canvas指纹干扰
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {{
            const context = this.getContext('2d');
            if (context && this.width > 0 && this.height > 0) {{
                // 添加微小的像素噪声
                const imageData = context.getImageData(0, 0, Math.min(this.width, 10), Math.min(this.height, 10));
                const data = imageData.data;
                
                for (let i = 0; i < data.length; i += 4) {{
                    // 修改RGB值，但保持在合理范围内
                    if (Math.random() < 0.1) {{  // 10%概率修改
                        data[i] = Math.max(0, Math.min(255, data[i] + (Math.random() - 0.5) * 2));
                        data[i+1] = Math.max(0, Math.min(255, data[i+1] + (Math.random() - 0.5) * 2)); 
                        data[i+2] = Math.max(0, Math.min(255, data[i+2] + (Math.random() - 0.5) * 2));
                    }}
                }}
                
                context.putImageData(imageData, 0, 0);
            }}
            return originalToDataURL.apply(this, args);
        }};
        
        // Canvas文本渲染干扰
        const originalFillText = CanvasRenderingContext2D.prototype.fillText;
        CanvasRenderingContext2D.prototype.fillText = function(text, x, y, maxWidth) {{
            // 添加微小的位置偏移
            const offsetX = (Math.random() - 0.5) * 0.001;
            const offsetY = (Math.random() - 0.5) * 0.001;
            return originalFillText.call(this, text, x + offsetX, y + offsetY, maxWidth);
        }};
        
        // =============音频指纹干扰=============
        
        // AudioContext指纹干扰
        if (window.AudioContext || window.webkitAudioContext) {{
            const OriginalAnalyserNode = window.AnalyserNode || window.webkitAnalyserNode;
            if (OriginalAnalyserNode) {{
                const originalGetFloatFrequencyData = OriginalAnalyserNode.prototype.getFloatFrequencyData;
                OriginalAnalyserNode.prototype.getFloatFrequencyData = function(array) {{
                    originalGetFloatFrequencyData.call(this, array);
                    // 添加微小的音频指纹噪声
                    for (let i = 0; i < array.length; i++) {{
                        array[i] = array[i] + (Math.random() - 0.5) * 0.0001;
                    }}
                }};
                
                const originalGetByteFrequencyData = OriginalAnalyserNode.prototype.getByteFrequencyData;
                OriginalAnalyserNode.prototype.getByteFrequencyData = function(array) {{
                    originalGetByteFrequencyData.call(this, array);
                    for (let i = 0; i < array.length; i++) {{
                        array[i] = Math.max(0, Math.min(255, array[i] + Math.floor((Math.random() - 0.5) * 0.1)));
                    }}
                }};
            }}
        }}
        
        // =============高级指纹干扰=============
        
        // 屏幕指纹干扰 - 伪造DPI
        Object.defineProperty(window, 'devicePixelRatio', {{
            get: () => 1 + (Math.random() - 0.5) * 0.0001  // 微小随机化
        }});
        
        // 时间指纹干扰
        const originalNow = performance.now;
        performance.now = function() {{
            return originalNow.call(this) + (Math.random() - 0.5) * 0.01;
        }};
        
        // 电池信息随机化
        if (navigator.getBattery) {{
            const originalGetBattery = navigator.getBattery;
            navigator.getBattery = function() {{
                return originalGetBattery.call(this).then(battery => {{
                    const newBattery = Object.assign({{}}, battery);
                    newBattery.level = 0.5 + (Math.random() - 0.5) * 0.4;  // 0.3-0.7范围
                    newBattery.charging = Math.random() > 0.5;
                    newBattery.chargingTime = Math.random() * 10000;
                    newBattery.dischargingTime = Math.random() * 20000;
                    return newBattery;
                }});
            }};
        }}
        
        console.log('🎨 指纹伪造脚本已加载');
        """
    
    def generate_gaussian_typing_delays(self, text: str, user_type: str = 'normal') -> List[float]:
        """
        生成基于高斯分布的打字延迟
        
        Args:
            text: 要输入的文本
            user_type: 用户类型 ('fast', 'normal', 'slow', 'variable')
            
        Returns:
            每个字符的延迟时间列表（秒）
        """
        delays = []
        
        # 不同用户类型的基础参数
        typing_profiles = {
            'fast': {'mean': 0.08, 'std': 0.02, 'pause_prob': 0.02},      # 快速打字者
            'normal': {'mean': 0.12, 'std': 0.04, 'pause_prob': 0.05},    # 普通打字者
            'slow': {'mean': 0.18, 'std': 0.06, 'pause_prob': 0.08},      # 慢速打字者
            'variable': {'mean': 0.15, 'std': 0.08, 'pause_prob': 0.12}   # 不稳定打字者
        }
        
        profile = typing_profiles.get(user_type, typing_profiles['normal'])
        
        for i, char in enumerate(text):
            # 基础延迟（高斯分布）
            base_delay = max(0.03, np.random.normal(profile['mean'], profile['std']))
            
            # 字符类型调整
            if char.isalpha():
                # 字母：正常延迟
                char_factor = 1.0
            elif char.isdigit():
                # 数字：稍慢一些（需要思考）
                char_factor = 1.2
            elif char in '.,;!?':
                # 标点符号：更慢（需要找键位）
                char_factor = 1.4
            elif char in ' ':
                # 空格：稍快（大拇指操作）
                char_factor = 0.8
            else:
                # 特殊字符：最慢（需要组合键或查找）
                char_factor = 1.8
            
            # 位置因子：某些键位更难按
            position_factor = 1.0
            if char.upper() in 'QWERTY':
                position_factor = 0.95  # 上排稍快
            elif char.upper() in 'ASDFGH':
                position_factor = 1.0   # 中排正常
            elif char.upper() in 'ZXCVBN':
                position_factor = 1.05  # 下排稍慢
            
            # 连续字符调整
            if i > 0:
                prev_char = text[i-1]
                # 相同字符连击
                if char == prev_char:
                    char_factor *= 0.85  # 连击稍快
                # 常见组合
                elif (char.lower() + prev_char.lower()) in ['th', 'he', 'in', 'er', 'an']:
                    char_factor *= 0.9   # 常见组合稍快
                # 困难组合（不同手指协调）
                elif char.lower() in 'qwerty' and prev_char.lower() in 'asdfgh':
                    char_factor *= 1.1   # 跨排稍慢
            
            # 疲劳因子：随着输入增多，速度逐渐下降
            fatigue_factor = 1.0 + (i / len(text)) * 0.1
            
            # 计算最终延迟
            final_delay = base_delay * char_factor * position_factor * fatigue_factor
            
            # 添加随机停顿（模拟思考、查看屏幕等）
            if random.random() < profile['pause_prob']:
                pause_duration = random.uniform(0.2, 1.0)  # 200ms到1s的停顿
                final_delay += pause_duration
            
            # 限制在合理范围内
            final_delay = max(0.03, min(final_delay, 2.0))
            delays.append(final_delay)
        
        return delays
    
    def add_typing_mistakes(self, text: str, error_rate: float = 0.02) -> Tuple[str, List[int]]:
        """
        添加打字错误，模拟真实的打字体验
        
        Args:
            text: 原始文本
            error_rate: 错误率 (0.0-1.0)
            
        Returns:
            修改后的文本和错误位置列表
        """
        if error_rate <= 0:
            return text, []
        
        chars = list(text)
        error_positions = []
        
        # 常见打字错误模式
        common_errors = {
            'a': ['s', 'q'],
            's': ['a', 'd', 'w'],
            'd': ['s', 'f', 'e'],
            'f': ['d', 'g', 'r'],
            'g': ['f', 'h', 't'],
            'h': ['g', 'j', 'y'],
            'j': ['h', 'k', 'u'],
            'k': ['j', 'l', 'i'],
            'l': ['k', 'o'],
            # 添加更多常见错误...
        }
        
        i = 0
        while i < len(chars):
            if random.random() < error_rate:
                char = chars[i].lower()
                
                # 选择错误类型
                error_type = random.choice(['substitute', 'extra', 'omit'])
                
                if error_type == 'substitute' and char in common_errors:
                    # 替换为相邻键
                    chars[i] = random.choice(common_errors[char])
                    error_positions.append(i)
                    
                elif error_type == 'extra':
                    # 插入额外字符
                    if char in common_errors:
                        extra_char = random.choice(common_errors[char])
                        chars.insert(i, extra_char)
                        error_positions.append(i)
                        i += 1  # 跳过插入的字符
                    
                elif error_type == 'omit' and len(chars) > 1:
                    # 删除字符
                    del chars[i]
                    error_positions.append(i)
                    i -= 1  # 调整索引
            
            i += 1
        
        return ''.join(chars), error_positions
    
    async def simulate_human_typing_with_corrections(self, page: Page, selector: str, text: str, 
                                                    user_type: str = 'normal', 
                                                    error_rate: float = 0.02,
                                                    correction_rate: float = 0.8) -> None:
        """
        模拟包含错误和纠正的人类打字行为
        
        Args:
            page: 页面对象
            selector: 元素选择器
            text: 要输入的文本
            user_type: 用户类型 ('fast', 'normal', 'slow', 'variable')
            error_rate: 错误率
            correction_rate: 错误纠正率
        """
        try:
            element = page.locator(selector)
            await element.click()
            
            # 清空输入框
            await element.clear()
            
            # 生成带错误的文本
            typed_text, error_positions = self.add_typing_mistakes(text, error_rate)
            
            # 生成打字延迟
            delays = self.generate_gaussian_typing_delays(typed_text, user_type)
            
            # 执行打字
            for i, (char, delay) in enumerate(zip(typed_text, delays)):
                await element.type(char)
                
                # 检查是否是错误位置且需要纠正
                if i in error_positions and random.random() < correction_rate:
                    # 模拟发现错误，停顿一下
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # 回删错误字符
                    await element.press('Backspace')
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                    
                    # 输入正确字符
                    correct_char = text[min(i, len(text)-1)]
                    await element.type(correct_char)
                    
                    # 纠正后的短暂停顿
                    await asyncio.sleep(random.uniform(0.05, 0.1))
                
                # 应用延迟
                if delay > 0:
                    await asyncio.sleep(delay)
            
            logger.info(f"完成高斯分布人类打字模拟: {selector}, "
                       f"用户类型: {user_type}, 文本长度: {len(text)}")
            
        except Exception as e:
            logger.error(f"高斯分布人类打字模拟失败: {e}")
            raise
    
    def simulate_human_typing(self, page: Page, selector: str, text: str, 
                             delay_range: Tuple[int, int] = (100, 300)) -> None:
        """
        模拟人类打字行为 (同步版本，向后兼容)
        
        Args:
            page: 页面对象
            selector: 元素选择器
            text: 要输入的文本
            delay_range: 打字延迟范围（毫秒）
        """
        try:
            element = page.locator(selector)
            element.click()
            
            # 清空输入框
            element.clear()
            
            # 使用高斯分布延迟逐字符输入
            delays = self.generate_gaussian_typing_delays(text, 'normal')
            
            for char, delay in zip(text, delays):
                element.type(char)
                # 转换为毫秒并应用范围限制
                delay_ms = max(delay_range[0], min(int(delay * 1000), delay_range[1]))
                time.sleep(delay_ms / 1000.0)
                
            logger.info(f"完成人类模拟打字: {selector}")
        except Exception as e:
            logger.error(f"人类模拟打字失败: {e}")
            raise
    
    def generate_bezier_curve(self, start: Tuple[float, float], end: Tuple[float, float], 
                             control_points: int = 2, steps: int = 50) -> List[Tuple[float, float]]:
        """
        生成贝塞尔曲线路径点
        
        Args:
            start: 起始点坐标 (x, y)
            end: 结束点坐标 (x, y)
            control_points: 控制点数量
            steps: 路径点数量
            
        Returns:
            路径点列表
        """
        # 生成控制点
        points = [start]
        
        # 添加随机控制点，增加轨迹的自然性
        for i in range(control_points):
            progress = (i + 1) / (control_points + 1)
            
            # 基础插值点
            base_x = start[0] + (end[0] - start[0]) * progress
            base_y = start[1] + (end[1] - start[1]) * progress
            
            # 添加随机偏移，模拟人类不完美的移动
            offset_x = random.uniform(-50, 50)
            offset_y = random.uniform(-50, 50)
            
            # 确保控制点不会偏离太远
            distance = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            max_offset = min(distance * 0.3, 100)  # 最大偏移为路径长度的30%
            
            if abs(offset_x) > max_offset:
                offset_x = max_offset if offset_x > 0 else -max_offset
            if abs(offset_y) > max_offset:
                offset_y = max_offset if offset_y > 0 else -max_offset
            
            control_x = base_x + offset_x
            control_y = base_y + offset_y
            
            points.append((control_x, control_y))
        
        points.append(end)
        
        # 使用贝塞尔曲线公式计算路径点
        curve_points = []
        n = len(points) - 1
        
        for i in range(steps + 1):
            t = i / steps
            x = 0
            y = 0
            
            # 贝塞尔曲线公式
            for j, point in enumerate(points):
                # 二项式系数
                binomial_coeff = math.comb(n, j)
                # 贝塞尔基函数
                bezier_basis = binomial_coeff * (t ** j) * ((1 - t) ** (n - j))
                
                x += point[0] * bezier_basis
                y += point[1] * bezier_basis
            
            curve_points.append((x, y))
        
        return curve_points
    
    def add_human_mouse_variations(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        为鼠标轨迹添加人类特征变化
        
        Args:
            points: 原始路径点列表
            
        Returns:
            添加变化后的路径点列表
        """
        if len(points) < 2:
            return points
        
        varied_points = [points[0]]  # 起始点不变
        
        for i in range(1, len(points)):
            x, y = points[i]
            
            # 添加微小的随机抖动，模拟手部微动
            jitter_x = random.gauss(0, 0.5)  # 高斯分布的抖动
            jitter_y = random.gauss(0, 0.5)
            
            # 添加速度变化 - 人类在转向时会稍微减速
            if i > 1 and i < len(points) - 1:
                prev_point = points[i-1]
                next_point = points[i+1]
                
                # 计算角度变化
                angle1 = math.atan2(y - prev_point[1], x - prev_point[0])
                angle2 = math.atan2(next_point[1] - y, next_point[0] - x)
                angle_change = abs(angle1 - angle2)
                
                # 角度变化越大，抖动越大
                if angle_change > math.pi / 4:  # 45度以上的转向
                    jitter_x *= 2
                    jitter_y *= 2
            
            varied_points.append((x + jitter_x, y + jitter_y))
        
        return varied_points
    
    def calculate_human_like_delays(self, points: List[Tuple[float, float]]) -> List[float]:
        """
        计算人类化的移动延迟
        
        Args:
            points: 路径点列表
            
        Returns:
            每个点的延迟时间列表（秒）
        """
        if len(points) < 2:
            return [0.0] * len(points)
        
        delays = [0.0]  # 起始点无延迟
        
        for i in range(1, len(points)):
            prev_point = points[i-1]
            curr_point = points[i]
            
            # 计算距离
            distance = math.sqrt((curr_point[0] - prev_point[0])**2 + 
                               (curr_point[1] - prev_point[1])**2)
            
            # 基础延迟：距离越长，时间越长，但不是线性关系
            base_delay = 0.008 + (distance * 0.001)  # 8ms基础 + 距离因子
            
            # 添加随机变化，模拟人类不均匀的移动速度
            variation = random.gauss(1.0, 0.2)  # 高斯分布的速度变化
            variation = max(0.5, min(variation, 2.0))  # 限制在合理范围内
            
            # 添加偶发的停顿，模拟人类思考或调整
            if random.random() < 0.05:  # 5%概率的停顿
                variation *= random.uniform(2.0, 4.0)
            
            final_delay = base_delay * variation
            delays.append(final_delay)
        
        return delays
    
    async def simulate_human_mouse_movement(self, page: Page, target_selector: str = None, 
                                           start_pos: Tuple[float, float] = None) -> None:
        """
        使用贝塞尔曲线模拟人类鼠标移动轨迹
        
        Args:
            page: 页面对象
            target_selector: 目标元素选择器，如果为None则随机移动
            start_pos: 起始位置，如果为None则使用当前鼠标位置
        """
        try:
            # 确定目标位置
            if target_selector:
                element = page.locator(target_selector)
                box = element.bounding_box()
                if box:
                    # 在元素范围内随机选择一个点，更自然
                    target_x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
                    target_y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
                else:
                    target_x, target_y = 500, 300
            else:
                viewport = page.viewport_size
                target_x = random.randint(100, viewport['width'] - 100)
                target_y = random.randint(100, viewport['height'] - 100)
            
            # 确定起始位置
            if start_pos:
                start_x, start_y = start_pos
            else:
                # 使用当前鼠标位置或默认位置
                start_x, start_y = random.randint(100, 300), random.randint(100, 300)
            
            # 生成贝塞尔曲线路径
            control_points = random.randint(1, 3)  # 随机控制点数量
            steps = random.randint(30, 60)  # 随机路径密度
            
            curve_points = self.generate_bezier_curve(
                (start_x, start_y), (target_x, target_y), 
                control_points, steps
            )
            
            # 添加人类特征变化
            varied_points = self.add_human_mouse_variations(curve_points)
            
            # 计算人类化延迟
            delays = self.calculate_human_like_delays(varied_points)
            
            # 执行鼠标移动
            for i, ((x, y), delay) in enumerate(zip(varied_points, delays)):
                await page.mouse.move(x, y)
                if delay > 0:
                    await asyncio.sleep(delay)
            
            logger.info(f"完成贝塞尔曲线鼠标移动到 ({target_x:.1f}, {target_y:.1f})，"
                       f"路径点数: {len(varied_points)}, 控制点: {control_points}")
            
        except Exception as e:
            logger.error(f"贝塞尔曲线鼠标移动失败: {e}")
    
    def simulate_mouse_movement(self, page: Page, target_selector: str = None) -> None:
        """
        模拟鼠标移动轨迹 (同步版本，向后兼容)
        
        Args:
            page: 页面对象
            target_selector: 目标元素选择器，如果为None则随机移动
        """
        try:
            # 使用简化的直线路径进行同步移动
            if target_selector:
                element = page.locator(target_selector)
                box = element.bounding_box()
                if box:
                    target_x = box['x'] + box['width'] / 2
                    target_y = box['y'] + box['height'] / 2
                else:
                    target_x, target_y = 500, 300
            else:
                target_x = random.randint(100, 800)
                target_y = random.randint(100, 600)
            
            # 生成简单的弯曲路径
            current_x, current_y = 100, 100
            steps = random.randint(8, 15)
            
            for i in range(steps):
                progress = (i + 1) / steps
                x = current_x + (target_x - current_x) * progress
                y = current_y + (target_y - current_y) * progress
                
                # 添加更自然的随机偏移
                offset_scale = math.sin(progress * math.pi) * 30  # 中间偏移更大
                x += random.gauss(0, offset_scale * 0.3)
                y += random.gauss(0, offset_scale * 0.3)
                
                page.mouse.move(x, y)
                
                # 使用高斯分布的延迟
                delay = max(0.01, random.gauss(0.03, 0.01))
                time.sleep(delay)
            
            logger.info(f"完成鼠标移动模拟到 ({target_x}, {target_y})")
        except Exception as e:
            logger.error(f"鼠标移动模拟失败: {e}")
    
    def simulate_scroll_behavior(self, page: Page, scroll_count: int = 3) -> None:
        """
        模拟滚动行为
        
        Args:
            page: 页面对象
            scroll_count: 滚动次数
        """
        try:
            for _ in range(scroll_count):
                # 随机滚动方向和距离
                scroll_delta = random.randint(200, 800)
                if random.choice([True, False]):
                    scroll_delta = -scroll_delta
                
                page.mouse.wheel(0, scroll_delta)
                
                # 随机停顿
                time.sleep(random.uniform(0.5, 2.0))
            
            logger.info(f"完成滚动行为模拟，共滚动 {scroll_count} 次")
        except Exception as e:
            logger.error(f"滚动行为模拟失败: {e}")
    
    def random_delay(self, min_ms: int = 1000, max_ms: int = 3000) -> None:
        """
        随机延迟
        
        Args:
            min_ms: 最小延迟毫秒数
            max_ms: 最大延迟毫秒数
        """
        delay = random.randint(min_ms, max_ms) / 1000.0
        time.sleep(delay)
        logger.debug(f"随机延迟 {delay:.2f} 秒")
    
    def generate_realistic_fingerprint(self) -> Dict[str, Any]:
        """
        生成更真实的浏览器指纹
        
        Returns:
            包含完整浏览器指纹的字典
        """
        # 选择一个一致的操作系统配置
        os_configs = [
            {
                'platform': 'Win32',
                'os': 'Windows NT 10.0; Win64; x64',
                'cpu_class': 'x86',
                'screen_resolutions': [(1920, 1080), (1366, 768), (1536, 864), (2560, 1440)],
                'timezone_offset': -480,  # UTC+8
                'language': 'zh-CN'
            },
            {
                'platform': 'MacIntel', 
                'os': 'Intel Mac OS X 10_15_7',
                'cpu_class': 'x86',
                'screen_resolutions': [(1440, 900), (1680, 1050), (1920, 1080), (2560, 1600)],
                'timezone_offset': -480,  # UTC+8
                'language': 'zh-CN'
            }
        ]
        
        config = random.choice(os_configs)
        width, height = random.choice(config['screen_resolutions'])
        
        # 生成一致的User-Agent
        if 'Win32' in config['platform']:
            ua_templates = [
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(115, 121)}.0.0.0 Safari/537.36",
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{random.randint(109, 121)}.0) Gecko/20100101 Firefox/{random.randint(109, 121)}.0",
            ]
        else:
            ua_templates = [
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(115, 121)}.0.0.0 Safari/537.36",
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{random.randint(109, 121)}.0) Gecko/20100101 Firefox/{random.randint(109, 121)}.0",
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.{random.randint(0, 3)} Safari/605.1.15"
            ]
        
        user_agent = random.choice(ua_templates)
        
        # 生成随机但合理的屏幕配置
        color_depth = random.choice([24, 32])
        pixel_depth = color_depth
        
        return {
            'user_agent': user_agent,
            'viewport': {'width': width, 'height': height},
            'screen': {
                'width': width + random.randint(0, 100),  # 屏幕可能比视窗大
                'height': height + random.randint(100, 200),
                'colorDepth': color_depth,
                'pixelDepth': pixel_depth,
                'availWidth': width,
                'availHeight': height - random.randint(30, 80)  # 任务栏高度
            },
            'platform': config['platform'],
            'timezone': self.get_random_timezone(),
            'timezone_offset': config['timezone_offset'] + random.randint(-60, 60),  # 稍微偏移
            'language': config['language'],
            'languages': ['zh-CN', 'zh', 'en'],
            'cpu_class': config['cpu_class'],
            'hardware_concurrency': random.choice([2, 4, 6, 8, 12, 16]),
            'device_memory': random.choice([2, 4, 8, 16]),  # GB
            'geolocation': {
                'latitude': 39.9042 + random.uniform(-5.0, 5.0),   # 中国范围内
                'longitude': 116.4074 + random.uniform(-10.0, 10.0),
                'accuracy': random.randint(10, 100)
            },
            'webgl': {
                'vendor': random.choice(['NVIDIA Corporation', 'Intel Inc.', 'AMD']),
                'renderer': self._generate_gpu_info()
            },
            'plugins': self._generate_plugin_list(),
            'fonts': self._generate_font_list()
        }
    
    def _generate_gpu_info(self) -> str:
        """生成随机的GPU信息"""
        gpu_options = [
            'NVIDIA GeForce GTX 1050',
            'NVIDIA GeForce GTX 1060', 
            'NVIDIA GeForce RTX 3060',
            'Intel(R) UHD Graphics 620',
            'Intel(R) Iris(TM) Graphics 6100',
            'AMD Radeon RX 580',
            'Apple M1'
        ]
        return random.choice(gpu_options)
    
    def _generate_plugin_list(self) -> List[Dict[str, str]]:
        """生成真实的浏览器插件列表"""
        common_plugins = [
            {'name': 'Chrome PDF Plugin', 'filename': 'internal-pdf-viewer'},
            {'name': 'Chromium PDF Plugin', 'filename': 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {'name': 'Microsoft Edge PDF Plugin', 'filename': 'pdf'},
            {'name': 'WebKit built-in PDF', 'filename': 'pdf'}
        ]
        
        # 随机选择一些插件
        selected_plugins = random.sample(common_plugins, random.randint(2, len(common_plugins)))
        return selected_plugins
    
    def _generate_font_list(self) -> List[str]:
        """生成真实的系统字体列表"""
        common_fonts = [
            'Arial', 'Arial Black', 'Arial Unicode MS',
            'Calibri', 'Cambria', 'Comic Sans MS',
            'Courier New', 'Georgia', 'Impact',
            'Lucida Console', 'Microsoft Sans Serif', 'Segoe UI',
            'Tahoma', 'Times New Roman', 'Trebuchet MS',
            'Verdana', 'Webdings', 'Wingdings',
            # 中文字体
            '宋体', '黑体', '微软雅黑',
            'SimSun', 'Microsoft YaHei', 'SimHei'
        ]
        
        # 随机选择一些字体，但保证有基础字体
        base_fonts = ['Arial', 'Times New Roman', 'Courier New', '宋体']
        additional_fonts = random.sample(
            [f for f in common_fonts if f not in base_fonts], 
            random.randint(5, 15)
        )
        
        return base_fonts + additional_fonts
    
    def get_detection_config(self) -> Dict[str, Any]:
        """
        获取随机的反检测配置 (向后兼容)
        
        Returns:
            包含反检测配置的字典
        """
        fingerprint = self.generate_realistic_fingerprint()
        return {
            'user_agent': fingerprint['user_agent'],
            'viewport': fingerprint['viewport'],
            'timezone': fingerprint['timezone'],
            'locale': fingerprint['language'],
            'geolocation': fingerprint['geolocation']
        }
    
    def check_detection_risks(self, page: Page) -> List[str]:
        """
        检查当前页面的检测风险
        
        Args:
            page: 页面对象
            
        Returns:
            风险列表
        """
        risks = []
        
        try:
            # 检查是否有反自动化脚本
            result = page.evaluate("""
                () => {
                    const risks = [];
                    
                    // 检查webdriver属性
                    if (navigator.webdriver === true) {
                        risks.push('webdriver属性未隐藏');
                    }
                    
                    // 检查phantom.js特征
                    if (window.callPhantom || window._phantom) {
                        risks.push('检测到PhantomJS特征');
                    }
                    
                    // 检查Selenium特征
                    if (window.document.$cdc_asdjflasutopfhvcZLmcfl_ !== undefined) {
                        risks.push('检测到Selenium特征');
                    }
                    
                    // 检查插件数量
                    if (navigator.plugins.length === 0) {
                        risks.push('浏览器插件数量异常');
                    }
                    
                    return risks;
                }
            """)
            
            risks.extend(result)
            
        except Exception as e:
            logger.error(f"检测风险评估失败: {e}")
            risks.append("风险评估失败")
        
        if risks:
            logger.warning(f"检测到以下风险: {risks}")
        else:
            logger.info("未发现明显的检测风险")
        
        return risks
    
    def inject_mouse_events(self, page: Page) -> None:
        """
        注入鼠标事件历史
        
        Args:
            page: 页面对象
        """
        try:
            page.evaluate("""
                () => {
                    // 创建鼠标事件历史
                    window._mouseEvents = [];
                    
                    // 监听鼠标移动
                    document.addEventListener('mousemove', (e) => {
                        window._mouseEvents.push({
                            type: 'mousemove',
                            x: e.clientX,
                            y: e.clientY,
                            timestamp: Date.now()
                        });
                        
                        // 保持最近100个事件
                        if (window._mouseEvents.length > 100) {
                            window._mouseEvents.shift();
                        }
                    });
                    
                    // 模拟一些历史移动事件
                    for (let i = 0; i < 10; i++) {
                        window._mouseEvents.push({
                            type: 'mousemove',
                            x: Math.floor(Math.random() * 1000),
                            y: Math.floor(Math.random() * 600),
                            timestamp: Date.now() - Math.floor(Math.random() * 10000)
                        });
                    }
                }
            """)
            
            logger.info("鼠标事件历史注入完成")
        except Exception as e:
            logger.error(f"注入鼠标事件失败: {e}")
    
    def bypass_cloudflare(self, page: Page, timeout: int = 30000) -> bool:
        """
        尝试绕过Cloudflare检测
        
        Args:
            page: 页面对象
            timeout: 等待超时时间
            
        Returns:
            是否成功绕过
        """
        try:
            # 检测是否遇到Cloudflare页面
            cloudflare_selectors = [
                'text="Checking your browser before accessing"',
                'text="Please wait while we check your browser"',
                '.cf-browser-verification',
                '#challenge-form'
            ]
            
            is_cloudflare = False
            for selector in cloudflare_selectors:
                try:
                    if page.locator(selector).is_visible():
                        is_cloudflare = True
                        break
                except:
                    continue
            
            if not is_cloudflare:
                logger.info("未检测到Cloudflare挑战")
                return True
            
            logger.info("检测到Cloudflare挑战，等待自动通过...")
            
            # 等待挑战完成
            start_time = time.time()
            while time.time() - start_time < timeout / 1000:
                try:
                    # 检查是否已经通过挑战
                    if not any(page.locator(sel).is_visible() for sel in cloudflare_selectors):
                        logger.info("成功通过Cloudflare挑战")
                        return True
                except:
                    pass
                
                time.sleep(1)
            
            logger.warning("Cloudflare挑战等待超时")
            return False
            
        except Exception as e:
            logger.error(f"处理Cloudflare挑战失败: {e}")
            return False
    
    async def async_random_delay(self, min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
        """
        随机延迟 (异步版本)
        
        Args:
            min_seconds: 最小延迟秒数
            max_seconds: 最大延迟秒数
        """
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
        logger.debug(f"异步随机延迟 {delay:.2f} 秒")
    
    async def simulate_user_activity(self, page: Page, activity_count: int = 3) -> None:
        """
        模拟综合的用户活动
        
        Args:
            page: 页面对象 
            activity_count: 活动次数
        """
        activities = [
            lambda: self.simulate_human_mouse_movement(page),
            lambda: self.simulate_scroll_behavior(page, random.randint(1, 3)),
            lambda: self.async_random_delay(0.5, 2.0),
            lambda: self.inject_mouse_events(page)
        ]
        
        for _ in range(activity_count):
            activity = random.choice(activities)
            try:
                if asyncio.iscoroutinefunction(activity):
                    await activity()
                else:
                    activity()
            except Exception as e:
                logger.warning(f"模拟用户活动失败: {e}")
                
        logger.info(f"完成 {activity_count} 个用户活动模拟")
    
    def create_anti_detection_config(self) -> Dict[str, Any]:
        """
        创建完整的反检测配置
        
        Returns:
            包含完整反检测配置的字典
        """
        fingerprint = self.generate_realistic_fingerprint()
        
        return {
            'context_options': {
                'viewport': fingerprint['viewport'],
                'user_agent': fingerprint['user_agent'],
                'locale': fingerprint['language'],
                'timezone_id': fingerprint['timezone'],
                'geolocation': fingerprint['geolocation'],
                'permissions': ['geolocation']
            },
            'fingerprint': fingerprint,
            'stealth_script': self._get_stealth_script(fingerprint),
            'fingerprint_script': self._get_fingerprint_script(fingerprint)
        }