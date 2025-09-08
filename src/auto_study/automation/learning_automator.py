"""
学习自动化核心

实现视频学习的智能控制，包括播放控制、进度监控、异常处理和断点续播
"""

import json
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import logger


class PlaybackStatus(Enum):
    """播放状态枚举"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"
    ERROR = "error"
    COMPLETED = "completed"


class LearningMode(Enum):
    """学习模式"""
    NORMAL = "normal"    # 正常学习模式
    FAST = "fast"        # 快速学习模式


@dataclass
class PlaybackState:
    """播放状态数据模型"""
    course_id: str
    video_id: str = ""
    position: float = 0.0  # 播放位置(秒)
    duration: float = 0.0  # 视频总时长(秒)
    status: PlaybackStatus = PlaybackStatus.STOPPED
    completed: bool = False
    last_played: Optional[datetime] = None
    play_count: int = 0
    error_count: int = 0
    session_id: str = ""
    
    @property
    def progress(self) -> float:
        """计算播放进度百分比"""
        if self.duration == 0:
            return 0.0
        return (self.position / self.duration) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "course_id": self.course_id,
            "video_id": self.video_id,
            "position": self.position,
            "duration": self.duration,
            "status": self.status.value,
            "completed": self.completed,
            "last_played": self.last_played.isoformat() if self.last_played else None,
            "play_count": self.play_count,
            "error_count": self.error_count,
            "session_id": self.session_id
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaybackState":
        """从字典创建对象"""
        last_played = None
        if data.get("last_played"):
            last_played = datetime.fromisoformat(data["last_played"])
        
        return cls(
            course_id=data["course_id"],
            video_id=data.get("video_id", ""),
            position=data.get("position", 0.0),
            duration=data.get("duration", 0.0),
            status=PlaybackStatus(data.get("status", "stopped")),
            completed=data.get("completed", False),
            last_played=last_played,
            play_count=data.get("play_count", 0),
            error_count=data.get("error_count", 0),
            session_id=data.get("session_id", "")
        )


@dataclass
class LearningSession:
    """学习会话数据"""
    course_id: str
    mode: LearningMode
    session_id: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_time: float = 0.0
    videos_completed: int = 0
    errors: List[str] = None
    progress_snapshots: List[Dict] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.errors is None:
            self.errors = []
        if self.progress_snapshots is None:
            self.progress_snapshots = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "course_id": self.course_id,
            "mode": self.mode.value,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_time": self.total_time,
            "videos_completed": self.videos_completed,
            "errors": self.errors,
            "progress_snapshots": self.progress_snapshots
        }


class VideoController:
    """视频播放控制器"""
    
    def __init__(self, page):
        """初始化视频控制器"""
        self.page = page
    
    async def detect_video_player(self) -> bool:
        """检测视频播放器"""
        try:
            # 尝试JavaScript检测 - 检测video标签
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        console.log('发现video标签:', videos.length);
                        return true;
                    }
                    return false;
                }
            """)
            if result:
                return True
        except:
            pass
        
        # 检测iframe嵌入的视频播放器
        try:
            result = await self.page.evaluate("""
                () => {
                    const iframes = document.querySelectorAll('iframe');
                    for (let iframe of iframes) {
                        const src = iframe.src || '';
                        const id = iframe.id || '';
                        const className = iframe.className || '';
                        
                        if (src.includes('video') || src.includes('player') || src.includes('media') ||
                            id.includes('video') || id.includes('player') ||
                            className.includes('video') || className.includes('player')) {
                            console.log('发现视频iframe:', src);
                            return true;
                        }
                    }
                    return false;
                }
            """)
            if result:
                return True
        except:
            pass
        
        # 尝试UI元素检测 - 扩展选择器列表
        try:
            selectors = [
                'video', 
                '.video-player', 
                '.player', 
                '#player',
                '.video-container',
                '.media-player',
                '.vjs-tech',  # Video.js播放器
                '.jwplayer',  # JW Player
                '.dplayer',   # DPlayer
                '.xgplayer',  # XGPlayer
                '.aplayer',   # APlayer
                '[data-player]',
                '[data-video]',
                '.video-js',  # Video.js
                '.plyr',      # Plyr播放器
                'iframe[src*="video"]',
                'iframe[src*="player"]',
                'iframe[src*="media"]'
            ]
            for selector in selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    print(f"发现视频播放器元素: {selector}")
                    return True
        except:
            pass
        
        # 检测特殊的播放器容器
        try:
            # 检查是否有播放按钮暗示有视频内容
            play_button_selectors = [
                'button:has-text("播放")',
                'button:has-text("开始播放")', 
                'button[title*="播放"]',
                'button[title*="Play"]',
                '.play-btn',
                '.btn-play',
                '[class*="play"]',
                '[id*="play"]'
            ]
            
            for selector in play_button_selectors:
                locator = self.page.locator(selector)
                if await locator.count() > 0:
                    print(f"发现播放按钮，暗示有视频内容: {selector}")
                    return True
        except:
            pass
        
        return False
    
    async def _handle_play_confirmation_popup(self, use_xpath=True):
        """处理播放确认弹窗 - 增强版
        
        Args:
            use_xpath: 是否使用特定的xpath选择器（视频页面用）
        """
        try:
            logger.info("VideoController: 检查播放确认弹窗...")
            
            # 等待弹窗加载
            await asyncio.sleep(2)
            
            # 更全面的弹窗选择器
            popup_selectors = [
                # Element UI 弹窗
                '.el-dialog:not([style*="display: none"])',  
                '.el-message-box__wrapper:not([style*="display: none"])',
                '.el-popup:not([style*="display: none"])',
                
                # 通用弹窗
                '.modal:not(.fade):not([style*="display: none"])',
                '.popup:not([style*="display: none"])',
                '.dialog:not([style*="display: none"])',
                '[role="dialog"]:not([style*="display: none"])',
                
                # 自定义弹窗
                '.play-dialog',
                '.video-dialog',
                '.confirm-dialog'
            ]
            
            for selector in popup_selectors:
                try:
                    elements = self.page.locator(selector)
                    count = await elements.count()
                    
                    for i in range(count):
                        element = elements.nth(i)
                        if await element.is_visible():
                            # 检查是否包含播放/学习相关内容
                            popup_text = await element.text_content()
                            if popup_text and any(keyword in popup_text for keyword in 
                                ['播放', '学习', '开始', '继续', '视频', '确认']):
                                
                                logger.info(f"VideoController: 发现播放相关弹窗: {selector}")
                                
                                # 查找确认按钮（包括div元素）
                                confirm_buttons = [
                                    # 最高优先级：基于监控发现的实际 xpath
                                    'xpath=/html/body/div/div[2]/div[2]',  # 实际存在的视频页面元素
                                    'xpath=/html/body/div/div[3]/div[2]',  # 原始用户提供的xpath（备用）
                                    
                                    # 基于实际分析："btn" 类名的 DIV 按钮
                                    'div.btn:has-text("继续学习")',
                                    'div.btn:has-text("开始学习")',
                                    'div.btn',  # 通用 btn 类
                                    
                                    # user_choise 类（之前已见过）
                                    '.user_choise:has-text("继续学习")',
                                    '.user_choise:has-text("开始学习")',
                                    'div.user_choise',
                                    
                                    # 标准 HTML button 元素
                                    'button:has-text("继续学习")',
                                    'button:has-text("开始学习")',
                                    'button:has-text("开始播放")',
                                    'button:has-text("确定")',
                                    'button:has-text("确认")',
                                    
                                    # 具有点击事件的 DIV
                                    'div[onclick]:has-text("继续学习")',
                                    'div[onclick]:has-text("开始学习")',
                                    
                                    # Element UI 按钮类
                                    '.el-button:has-text("继续学习")',
                                    '.el-button:has-text("开始学习")',
                                    '.el-button--primary:visible',
                                    
                                    # 其他可能的按钮类
                                    '.btn-primary:visible',
                                    '.confirm-btn:visible'
                                ]
                                
                                for btn_selector in confirm_buttons:
                                    try:
                                        # 特殊处理xpath选择器
                                        if btn_selector.startswith('xpath='):
                                            xpath = btn_selector[6:]  # 去除'xpath='前缀
                                            logger.info(f"VideoController: 尝试xpath选择器: {xpath}")
                                            
                                            # 检查xpath元素是否存在
                                            xpath_exists = await self.page.evaluate(f"""
                                                (xpath) => {{
                                                    const result = document.evaluate(
                                                        xpath, document, null, 
                                                        XPathResult.FIRST_ORDERED_NODE_TYPE, null
                                                    );
                                                    const element = result.singleNodeValue;
                                                    if (element) {{
                                                        const rect = element.getBoundingClientRect();
                                                        return {{
                                                            exists: true,
                                                            visible: rect.width > 0 && rect.height > 0,
                                                            text: element.textContent || '',
                                                            tagName: element.tagName
                                                        }};
                                                    }}
                                                    return {{ exists: false }};
                                                }}
                                            """, xpath)
                                            
                                            if xpath_exists['exists'] and xpath_exists['visible']:
                                                logger.info(f"VideoController: 找到xpath元素: {xpath_exists['tagName']} - '{xpath_exists['text'][:50]}'")
                                                
                                                # 记录点击前的URL
                                                current_url = self.page.url
                                                
                                                # 使用JavaScript直接点击xpath元素
                                                clicked = await self.page.evaluate(f"""
                                                    (xpath) => {{
                                                        const result = document.evaluate(
                                                            xpath, document, null,
                                                            XPathResult.FIRST_ORDERED_NODE_TYPE, null
                                                        );
                                                        const element = result.singleNodeValue;
                                                        if (element) {{
                                                            element.click();
                                                            return true;
                                                        }}
                                                        return false;
                                                    }}
                                                """, xpath)
                                                
                                                if clicked:
                                                    logger.info(f"VideoController: 成功点击xpath元素: {xpath}")
                                                    await asyncio.sleep(3)
                                                    
                                                    # 检查是否跳转到了新页面
                                                    new_url = self.page.url
                                                    if new_url != current_url:
                                                        logger.info(f"VideoController: 页面跳转成功: {new_url}")
                                                        return
                                                    else:
                                                        logger.info(f"VideoController: xpath点击成功，但页面未跳转")
                                                        # 对于视频页面弹窗，点击后可能不会跳转页面，只是关闭弹窗
                                                        return  # 这里直接返回，认为处理成功
                                                else:
                                                    logger.warning(f"VideoController: xpath点击失败")
                                            else:
                                                logger.info(f"VideoController: xpath元素不存在或不可见: {xpath}")
                                            
                                            continue
                                        
                                        # 常规选择器处理
                                        buttons = element.locator(btn_selector)
                                        button_count = await buttons.count()
                                        
                                        for j in range(button_count):
                                            button = buttons.nth(j)
                                            if await button.is_visible():
                                                button_text = await button.text_content()
                                                logger.info(f"VideoController: 点击确认按钮: {button_text}")
                                                
                                                # 记录点击前的URL
                                                current_url = self.page.url
                                                
                                                await button.click()
                                                await asyncio.sleep(3)
                                                
                                                # 检查是否跳转到了新页面
                                                new_url = self.page.url
                                                if new_url != current_url:
                                                    logger.info(f"VideoController: 页面跳转成功: {new_url}")
                                                    return
                                                else:
                                                    logger.info(f"VideoController: 页面未跳转，继续尝试下一个按钮")
                                                    continue
                                    except Exception as e:
                                        logger.debug(f"VideoController: 选择器 {btn_selector} 失败: {e}")
                                        continue
                                break
                except Exception as e:
                    logger.debug(f"VideoController: 检查弹窗失败 {selector}: {e}")
                    continue
        except Exception as e:
            logger.error(f"VideoController: 处理播放确认弹窗失败: {e}")
    
    async def _handle_login_popup(self) -> bool:
        """处理登录弹窗 - 基于网站实际结构"""
        try:
            logger.info("检查登录弹窗...")
            
            # 根据页面结构分析，登录弹窗使用 Element UI 的 el-dialog
            login_selectors = [
                '.el-dialog.el-dialog--center',  # Element UI 对话框
                '.el-dialog',  # 通用 Element UI 对话框
                '[role="dialog"]',  # 标准对话框角色
            ]
            
            for selector in login_selectors:
                dialogs = await self.page.locator(selector).count()
                if dialogs > 0:
                    logger.info(f"找到 {dialogs} 个对话框: {selector}")
                    
                    # 检查是否为登录弹窗（包含用户名、密码输入框）
                    dialog = self.page.locator(selector).first
                    
                    # 查找输入框
                    username_inputs = await dialog.locator('input[placeholder*="用户"], input[placeholder*="账号"], input[type="text"]').count()
                    password_inputs = await dialog.locator('input[type="password"], input[placeholder*="密码"]').count()
                    
                    if username_inputs > 0 and password_inputs > 0:
                        logger.info("确认为登录弹窗，直接在弹窗中登录...")
                        
                        # 直接在弹窗中填写表单
                        success = await self._fill_popup_login_form(
                            dialog,
                            username="640302198607120020",
                            password="My2062660"
                        )
                        
                        if success:
                            logger.info("✅ 登录弹窗处理成功")
                            await asyncio.sleep(2)  # 等待登录完成
                            return True
                        else:
                            logger.error("❌ 登录弹窗处理失败")
                            return False
            
            logger.info("未检测到登录弹窗")
            return True  # 没有弹窗也算成功
            
        except Exception as e:
            logger.error(f"VideoController: 处理登录弹窗失败: {e}")
            return False
    
    async def _fill_popup_login_form(self, dialog, username: str, password: str) -> bool:
        """在弹窗中填写登录表单"""
        try:
            logger.info("在弹窗中填写登录表单...")
            
            # 等待弹窗完全显示（非常重要！）
            logger.info("等待弹窗完全显示...")
            await asyncio.sleep(3)
            
            # 等待输入框可见
            try:
                await dialog.locator('input[placeholder*="用户"]').wait_for(state='visible', timeout=10000)
                logger.info("✅ 输入框已可见")
            except Exception as e:
                logger.warning(f"等待输入框可见超时: {e}")
            
            # 1. 填写用户名
            username_selectors = [
                'input[placeholder*="用户"]',
                'input[placeholder*="账号"]', 
                'input[type="text"]'
            ]
            
            username_filled = False
            for selector in username_selectors:
                username_input = dialog.locator(selector)
                if await username_input.count() > 0 and await username_input.first.is_visible():
                    await username_input.first.clear()
                    await username_input.first.fill(username)
                    logger.info(f"✅ 填写用户名: {username}")
                    username_filled = True
                    break
            
            if not username_filled:
                logger.error("❌ 未找到用户名输入框")
                return False
            
            # 2. 填写密码
            password_selectors = [
                'input[type="password"]',
                'input[placeholder*="密码"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                password_input = dialog.locator(selector)
                if await password_input.count() > 0 and await password_input.first.is_visible():
                    await password_input.first.clear()
                    await password_input.first.fill(password)
                    logger.info(f"✅ 填写密码: {'*' * len(password)}")
                    password_filled = True
                    break
            
            if not password_filled:
                logger.error("❌ 未找到密码输入框")
                return False
            
            # 3. 处理验证码（如果有）
            captcha_img = dialog.locator('img[src*="captcha"], img[src*="code"], .captcha img')
            if await captcha_img.count() > 0:
                logger.info("检测到验证码，进行识别...")
                
                # 使用 OCR 识别验证码
                from ..utils.ocr_recognizer import OCRRecognizer
                ocr = OCRRecognizer()
                
                captcha_result = await ocr.recognize_captcha_from_element(captcha_img.first)
                if captcha_result['success']:
                    captcha_code = captcha_result['code']
                    logger.info(f"验证码识别结果: {captcha_code}")
                    
                    # 填写验证码
                    captcha_input = dialog.locator('input[placeholder*="验证"], input[placeholder*="代码"]')
                    if await captcha_input.count() > 0:
                        await captcha_input.first.fill(captcha_code)
                        logger.info("✅ 填写验证码")
                    else:
                        logger.warning("未找到验证码输入框")
                else:
                    logger.warning("验证码识别失败")
            
            # 4. 点击登录按钮
            login_button_selectors = [
                'button:has-text("登录")',
                'button:has-text("登陆")',
                'button:has-text("确定")',
                '.el-button--primary',
                'button[type="submit"]',
                '.login-btn'
            ]
            
            login_clicked = False
            for selector in login_button_selectors:
                login_button = dialog.locator(selector)
                if await login_button.count() > 0 and await login_button.first.is_visible():
                    await login_button.first.click()
                    logger.info(f"✅ 点击登录按钮: {selector}")
                    login_clicked = True
                    break
            
            if not login_clicked:
                logger.error("❌ 未找到登录按钮")
                return False
            
            # 5. 等待登录结果
            await asyncio.sleep(3)
            
            # 检查登录是否成功（弹窗是否关闭）
            dialog_visible = await dialog.is_visible()
            if not dialog_visible:
                logger.info("✅ 登录弹窗已关闭，登录成功")
                return True
            else:
                # 检查是否有错误信息
                error_selectors = ['.error', '.el-message--error', '[class*="error"]']
                for error_sel in error_selectors:
                    error_elements = dialog.locator(error_sel)
                    if await error_elements.count() > 0:
                        error_text = await error_elements.first.text_content()
                        logger.error(f"登录错误: {error_text}")
                        return False
                
                logger.warning("登录弹窗仍然可见，可能登录失败")
                return False
                
        except Exception as e:
            logger.error(f"VideoController: 填写弹窗登录表单失败: {e}")
            return False
    
    async def _find_and_start_video(self) -> bool:
        """查找并启动视频播放器"""
        try:
            logger.info("开始查找视频播放器...")
            
            # 等待页面完全加载
            await asyncio.sleep(2)
            
            # 查找视频元素的多种方式
            video_info = await self.page.evaluate("""
                () => {
                    const result = {
                        videos: [],
                        iframes: [],
                        players: [],
                        clickableElements: []
                    };
                    
                    // 1. 查找 HTML5 video 标签
                    const videos = document.querySelectorAll('video');
                    videos.forEach((video, index) => {
                        result.videos.push({
                            index: index,
                            src: video.src || video.currentSrc,
                            id: video.id,
                            class: video.className,
                            paused: video.paused,
                            readyState: video.readyState,
                            visible: video.offsetWidth > 0 && video.offsetHeight > 0
                        });
                    });
                    
                    // 2. 查找 iframe（可能包含视频）
                    const iframes = document.querySelectorAll('iframe');
                    iframes.forEach((iframe, index) => {
                        const style = window.getComputedStyle(iframe);
                        result.iframes.push({
                            index: index,
                            src: iframe.src,
                            id: iframe.id,
                            class: iframe.className,
                            visible: style.display !== 'none' && iframe.offsetWidth > 0
                        });
                    });
                    
                    // 3. 查找常见的视频播放器容器
                    const playerSelectors = [
                        '.video-player', '.player', '[class*="video"]', 
                        '.prism-player', '.dplayer', '.vjs-player',
                        '[id*="player"]', '[class*="play"]'
                    ];
                    
                    playerSelectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.display !== 'none' && el.offsetWidth > 0) {
                                result.players.push({
                                    selector: selector,
                                    class: el.className,
                                    id: el.id,
                                    hasVideo: el.querySelector('video') !== null,
                                    hasIframe: el.querySelector('iframe') !== null
                                });
                            }
                        });
                    });
                    
                    // 4. 查找可能的播放按钮
                    const playSelectors = [
                        'button[class*="play"]', '.play-btn', '[title*="播放"]',
                        '[class*="start"]', '.btn-play', 'div[onclick*="play"]'
                    ];
                    
                    playSelectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const style = window.getComputedStyle(el);
                            if (style.display !== 'none' && el.offsetWidth > 0) {
                                result.clickableElements.push({
                                    selector: selector,
                                    text: el.textContent?.trim() || '',
                                    class: el.className,
                                    tag: el.tagName
                                });
                            }
                        });
                    });
                    
                    return result;
                }
            """)
            
            logger.info(f"视频元素数量: {len(video_info['videos'])}")
            logger.info(f"iframe数量: {len(video_info['iframes'])}")
            logger.info(f"播放器容器数量: {len(video_info['players'])}")
            logger.info(f"播放按钮数量: {len(video_info['clickableElements'])}")
            
            # 优先尝试HTML5视频
            if video_info['videos']:
                for i, video in enumerate(video_info['videos']):
                    if video['visible'] and video['readyState'] >= 2:  # HAVE_CURRENT_DATA
                        logger.info(f"尝试播放第{i}个视频: {video}")
                        
                        success = await self.page.evaluate(f"""
                            () => {{
                                const video = document.querySelectorAll('video')[{i}];
                                if (video && video.paused) {{
                                    video.play().then(() => {{
                                        console.log('视频开始播放');
                                    }}).catch(e => {{
                                        console.error('视频播放失败:', e);
                                    }});
                                    return true;
                                }}
                                return false;
                            }}
                        """)
                        
                        if success:
                            logger.info(f"✅ 成功启动第{i}个视频")
                            return True
            
            # 如果没有直接的视频，尝试点击播放按钮
            if video_info['clickableElements']:
                for element in video_info['clickableElements']:
                    if any(keyword in element['text'].lower() for keyword in ['播放', 'play', '开始']):
                        logger.info(f"尝试点击播放按钮: {element}")
                        
                        clicked = await self.page.evaluate(f"""
                            () => {{
                                const elements = document.querySelectorAll('{element['selector']}');
                                for (let el of elements) {{
                                    if (el.textContent && el.textContent.includes('{element['text'][:10]}')) {{
                                        el.click();
                                        return true;
                                    }}
                                }}
                                return false;
                            }}
                        """)
                        
                        if clicked:
                            logger.info("✅ 成功点击播放按钮")
                            await asyncio.sleep(2)  # 等待视频加载
                            return True
            
            # 如果没有直接的视频，检查iframe
            if video_info['iframes']:
                logger.info("🖼️  检测到iframe，尝试处理iframe内的视频...")
                iframe_success = await self._handle_iframe_video(video_info['iframes'])
                if iframe_success:
                    return True
            
            # 如果没有直接的视频，检查是否需要点击更多按钮
            logger.warning("未找到直接的视频元素")
            
            # 检查当前页面是否还在课程列表页
            current_url = self.page.url
            logger.info(f"当前页面: {current_url}")
            
            if 'tool_box/required' in current_url:
                logger.info("仍在课程列表页，尝试点击其他学习按钮...")
                
                # 查找并点击其他的继续学习按钮
                more_clicked = await self.page.evaluate("""
                    () => {
                        const buttons = document.querySelectorAll('div.btn');
                        for (let i = 0; i < Math.min(buttons.length, 5); i++) {
                            const btn = buttons[i];
                            const text = btn.textContent || '';
                            if (text.includes('继续学习') || text.includes('开始学习')) {
                                // 检查这个按钮是否在视窗内
                                const rect = btn.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    btn.click();
                                    return {
                                        clicked: true,
                                        index: i,
                                        text: text.trim()
                                    };
                                }
                            }
                        }
                        return { clicked: false };
                    }
                """)
                
                if more_clicked['clicked']:
                    logger.info(f"点击了第{more_clicked['index']+1}个按钮: {more_clicked['text']}")
                    await asyncio.sleep(5)  # 等待页面可能的跳转
                    
                    # 检查是否跳转了
                    new_url = self.page.url
                    if new_url != current_url:
                        logger.info(f"✅ 成功跳转到新页面: {new_url}")
                        
                        # 再次查找视频元素
                        await asyncio.sleep(3)
                        new_video_info = await self.page.evaluate("""
                            () => {
                                const videos = document.querySelectorAll('video');
                                return {
                                    count: videos.length,
                                    videos: Array.from(videos).map((v, i) => ({
                                        index: i,
                                        src: v.src || v.currentSrc,
                                        visible: v.offsetWidth > 0 && v.offsetHeight > 0,
                                        readyState: v.readyState
                                    }))
                                };
                            }
                        """)
                        
                        logger.info(f"新页面视频数量: {new_video_info['count']}")
                        if new_video_info['videos']:
                            logger.info(f"视频详情: {new_video_info['videos']}")
                            
                            # 尝试播放第一个可见的视频
                            for video in new_video_info['videos']:
                                if video['visible'] and video['readyState'] >= 2:
                                    success = await self.page.evaluate(f"""
                                        () => {{
                                            const video = document.querySelectorAll('video')[{video['index']}];
                                            if (video && video.paused) {{
                                                video.play();
                                                return true;
                                            }}
                                            return false;
                                        }}
                                    """)
                                    
                                    if success:
                                        logger.info(f"✅ 成功在新页面播放视频")
                                        return True
            
            logger.warning("最终未找到可用的视频播放器")
            logger.info(f"详细信息 - 视频: {video_info['videos']}")
            logger.info(f"详细信息 - iframe: {video_info['iframes']}")
            return False
            
        except Exception as e:
            logger.error(f"VideoController: 查找视频播放器失败: {e}")
            return False
    
    async def _handle_iframe_video(self, iframes_info) -> bool:
        """处理iframe内的视频播放器
        
        基于用户提供的信息：iframe包含真正的视频播放器
        "继续学习"弹窗可能出现在iframe内部
        """
        try:
            logger.info(f"🎬 开始处理 {len(iframes_info)} 个iframe...")
            
            for i, iframe_data in enumerate(iframes_info):
                logger.info(f"🖼️  处理iframe {i+1}: {iframe_data['src']}")
                
                # 优先处理包含scorm_play.do的iframe（视频播放器）
                if 'scorm_play.do' in iframe_data['src'] or 'player' in iframe_data.get('class', ''):
                    logger.info("🎯 发现视频播放器iframe")
                    
                    # 方法1：尝试通过JavaScript访问iframe内容
                    js_success = await self._handle_iframe_via_javascript(i, iframe_data)
                    if js_success:
                        return True
                    
                    # 方法2：尝试通过Playwright frame locator
                    frame_success = await self._handle_iframe_via_frame_locator(i, iframe_data)
                    if frame_success:
                        return True
                    
                    # 方法3：等待iframe加载后再次尝试
                    logger.info("⏳ 等待iframe完全加载后重试...")
                    await asyncio.sleep(5)
                    retry_success = await self._handle_iframe_via_javascript(i, iframe_data)
                    if retry_success:
                        return True
            
            logger.warning("❌ 所有iframe处理方法都失败了")
            return False
            
        except Exception as e:
            logger.error(f"❌ 处理iframe视频时异常: {e}")
            return False
    
    async def _handle_iframe_via_javascript(self, iframe_index, iframe_data) -> bool:
        """通过JavaScript处理iframe"""
        try:
            logger.info(f"🔧 使用JavaScript方法处理iframe {iframe_index+1}...")
            
            result = await self.page.evaluate(f"""
                (index) => {{
                    const iframe = document.querySelectorAll('iframe')[index];
                    if (!iframe) return {{ success: false, error: 'iframe不存在' }};
                    
                    try {{
                        // 尝试访问iframe的document
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (!iframeDoc) {{
                            return {{ success: false, error: '无法访问iframe内容(跨域)', crossOrigin: true }};
                        }}
                        
                        // 查找iframe内的视频
                        const videos = iframeDoc.querySelectorAll('video');
                        if (videos.length > 0) {{
                            let videoStarted = false;
                            for (let video of videos) {{
                                if (video.paused) {{
                                    try {{
                                        video.play();
                                        videoStarted = true;
                                        break;
                                    }} catch (e) {{
                                        console.log('视频播放失败:', e);
                                    }}
                                }}
                            }}
                            
                            if (videoStarted) {{
                                return {{
                                    success: true,
                                    method: 'direct_video_play',
                                    videoCount: videos.length
                                }};
                            }}
                        }}
                        
                        // 查找iframe内的播放按钮
                        const playButtons = [
                            ...iframeDoc.querySelectorAll('button'),
                            ...iframeDoc.querySelectorAll('div[onclick]'),
                            ...iframeDoc.querySelectorAll('.btn'),
                            ...iframeDoc.querySelectorAll('[class*="play"]'),
                            ...iframeDoc.querySelectorAll('[class*="start"]')
                        ];
                        
                        const learningButtons = [];
                        playButtons.forEach((btn, i) => {{
                            const text = btn.textContent || '';
                            if (text.includes('继续学习') || text.includes('开始学习') || 
                                text.includes('播放') || text.includes('play') || 
                                text.includes('开始') || text.includes('start')) {{
                                learningButtons.push({{
                                    index: i,
                                    text: text.trim(),
                                    tagName: btn.tagName,
                                    className: btn.className
                                }});
                            }}
                        }});
                        
                        // 尝试点击找到的按钮
                        if (learningButtons.length > 0) {{
                            const firstBtn = playButtons[learningButtons[0].index];
                            if (firstBtn) {{
                                firstBtn.click();
                                return {{
                                    success: true,
                                    method: 'button_click',
                                    clicked: learningButtons[0],
                                    totalButtons: playButtons.length,
                                    learningButtons: learningButtons.length
                                }};
                            }}
                        }}
                        
                        return {{
                            success: false,
                            error: '未找到可操作的元素',
                            totalButtons: playButtons.length,
                            videos: videos.length
                        }};
                        
                    }} catch (e) {{
                        return {{ success: false, error: `JavaScript错误: ${{e.message}}` }};
                    }}
                }}
            """, iframe_index)
            
            if result['success']:
                logger.info(f"✅ JavaScript方法成功!")
                logger.info(f"   方法: {result['method']}")
                
                if result['method'] == 'direct_video_play':
                    logger.info(f"   直接播放iframe内的 {result['videoCount']} 个视频")
                elif result['method'] == 'button_click':
                    logger.info(f"   点击了按钮: {result['clicked']['text']}")
                    logger.info(f"   iframe内总按钮: {result['totalButtons']}个, 学习相关: {result['learningButtons']}个")
                
                # 等待操作生效
                await asyncio.sleep(3)
                return True
                
            else:
                error_msg = result['error']
                logger.warning(f"⚠️  JavaScript方法失败: {error_msg}")
                
                if result.get('crossOrigin'):
                    logger.info("💡 这是跨域iframe，需要使用其他方法")
                elif 'totalButtons' in result or 'videos' in result:
                    logger.info(f"   iframe内按钮: {result.get('totalButtons', 0)}个, 视频: {result.get('videos', 0)}个")
                
                return False
                
        except Exception as e:
            logger.error(f"❌ JavaScript处理iframe时异常: {e}")
            return False
    
    async def _handle_iframe_via_frame_locator(self, iframe_index, iframe_data) -> bool:
        """通过Playwright frame locator处理iframe"""
        try:
            logger.info(f"🎭 使用Playwright frame locator处理iframe {iframe_index+1}...")
            
            # 尝试获取iframe句柄
            iframe_selector = f"iframe:nth-child({iframe_index + 1})"
            
            # 等待iframe加载
            await asyncio.sleep(2)
            
            try:
                # 使用frame locator
                frame = self.page.frame_locator(iframe_selector)
                
                # 检查iframe内的视频
                video_count = await frame.locator('video').count()
                if video_count > 0:
                    logger.info(f"🎬 iframe内发现 {video_count} 个视频元素")
                    
                    for i in range(video_count):
                        video = frame.locator('video').nth(i)
                        if await video.is_visible():
                            logger.info(f"🖱️  尝试播放第 {i+1} 个视频")
                            
                            # 直接尝试点击视频元素
                            await video.click()
                            await asyncio.sleep(2)
                            return True
                
                # 查找iframe内的播放按钮
                button_selectors = [
                    'button:has-text("继续学习")',
                    'button:has-text("开始学习")', 
                    'button:has-text("播放")',
                    'div:has-text("继续学习")',
                    'div:has-text("开始学习")',
                    'div:has-text("播放")',
                    '.play-btn',
                    '.continue-btn',
                    '[class*="play"]',
                    '[onclick*="play"]'
                ]
                
                for selector in button_selectors:
                    try:
                        elements = frame.locator(selector)
                        count = await elements.count()
                        
                        if count > 0:
                            logger.info(f"✅ iframe内找到 {count} 个 '{selector}' 元素")
                            
                            for i in range(count):
                                element = elements.nth(i)
                                if await element.is_visible():
                                    logger.info(f"🖱️  点击 '{selector}' 元素 {i+1}")
                                    await element.click()
                                    await asyncio.sleep(3)
                                    return True
                                    
                    except Exception as e:
                        logger.debug(f"尝试 '{selector}' 时出错: {e}")
                        continue
                
                logger.warning("⚠️  frame locator未找到可操作的元素")
                return False
                
            except Exception as e:
                logger.warning(f"⚠️  frame locator失败: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Playwright frame locator处理异常: {e}")
            return False
    
    async def play(self) -> bool:
        """播放视频 - 基于网站实际结构的针对性实现
        
        关键发现：点击"继续学习"按钮会在新tab中打开视频页面
        """
        try:
            logger.info("开始针对性视频播放逻辑")
            
            # 获取浏览器上下文和初始页面数
            context = self.page.context
            initial_page_count = len(context.pages)
            logger.info(f"初始页面数: {initial_page_count}")
            
            # 第一步：点击"继续学习"按钮（会在新tab中打开视频页面）
            logger.info("1. 点击'继续学习'按钮（会在新tab中打开）...")
            new_tab_opened = await self._click_continue_learning_for_new_tab()
            
            if not new_tab_opened:
                logger.error("❌ 未能打开新tab")
                return False
            
            # 第二步：等待并切换到新的视频tab
            logger.info("2. 等待新tab打开并切换...")
            video_page = await self._wait_for_new_tab(context, initial_page_count)
            
            if not video_page:
                logger.error("❌ 未能获取到新的视频页面")
                return False
            
            logger.info(f"✅ 成功切换到视频页面: {video_page.url}")
            
            # 第三步：在新的视频页面中处理iframe和播放器
            logger.info("3. 处理视频页面中的iframe播放器...")
            video_started = await self._handle_video_page_iframe(video_page)
            
            if video_started:
                logger.info("✅ 视频播放逻辑执行成功")
                return True
            else:
                logger.warning("❌ iframe视频处理失败")
                return False
                
        except Exception as e:
            logger.error(f"VideoController: 播放视频失败: {e}")
            return False
    
    async def _click_continue_learning_for_new_tab(self) -> bool:
        """点击继续学习按钮，准备在新tab中打开视频页面"""
        try:
            logger.info("🎯 查找并点击'继续学习'按钮...")
            
            clicked = await self.page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('div.btn');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习')) {
                            // 滚动到按钮位置确保可见
                            btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                            btn.click();
                            return {
                                success: true,
                                text: text.trim()
                            };
                        }
                    }
                    return { success: false };
                }
            """)
            
            if clicked['success']:
                logger.info(f"✅ 成功点击按钮: {clicked['text']}")
                return True
            else:
                logger.error("❌ 未找到'继续学习'按钮")
                return False
                
        except Exception as e:
            logger.error(f"❌ 点击按钮时异常: {e}")
            return False
    
    async def _wait_for_new_tab(self, context, initial_count, timeout=10):
        """等待新tab打开并返回视频页面"""
        try:
            logger.info("⏳ 等待新tab打开...")
            
            for i in range(timeout):
                await asyncio.sleep(1)
                current_count = len(context.pages)
                
                if current_count > initial_count:
                    logger.info(f"🎉 检测到新tab打开! (页面数: {initial_count} -> {current_count})")
                    
                    # 获取最新的页面
                    video_page = context.pages[-1]
                    
                    # 等待新页面加载
                    logger.info("⏳ 等待新页面完全加载...")
                    await video_page.wait_for_load_state('networkidle', timeout=15000)
                    await asyncio.sleep(3)
                    
                    logger.info(f"📍 视频页面URL: {video_page.url}")
                    logger.info(f"📄 视频页面标题: {await video_page.title()}")
                    
                    # 验证是否为视频页面
                    if 'video_page' in video_page.url:
                        return video_page
                    else:
                        logger.warning(f"⚠️  新页面可能不是视频页面: {video_page.url}")
                        return video_page  # 仍然返回，但记录警告
                
                elif i % 3 == 0:
                    logger.info(f"⏱️  等待新tab... ({timeout-i}秒剩余)")
            
            logger.error(f"❌ {timeout}秒内未检测到新tab打开")
            return None
            
        except Exception as e:
            logger.error(f"❌ 等待新tab时异常: {e}")
            return None
    
    async def _handle_video_page_iframe(self, video_page) -> bool:
        """处理视频页面中的iframe播放器"""
        try:
            logger.info("🎬 开始处理视频页面中的iframe...")
            
            # 分析页面中的iframe
            iframe_analysis = await video_page.evaluate("""
                () => {
                    const iframes = document.querySelectorAll('iframe');
                    const result = [];
                    
                    iframes.forEach((iframe, index) => {
                        const rect = iframe.getBoundingClientRect();
                        result.push({
                            index: index,
                            src: iframe.src || iframe.getAttribute('src') || '',
                            class: iframe.className || '',
                            width: rect.width,
                            height: rect.height,
                            visible: rect.width > 0 && rect.height > 0
                        });
                    });
                    
                    return result;
                }
            """)
            
            logger.info(f"🖼️  发现 {len(iframe_analysis)} 个iframe")
            
            if not iframe_analysis:
                logger.warning("❌ 视频页面中未发现iframe")
                return False
            
            # 处理每个iframe
            for iframe_info in iframe_analysis:
                logger.info(f"\n🎯 处理iframe: {iframe_info['src']}")
                logger.info(f"   大小: {iframe_info['width']}x{iframe_info['height']}")
                logger.info(f"   可见: {iframe_info['visible']}")
                
                # 优先处理视频播放器iframe
                if 'scorm_play.do' in iframe_info['src'] or 'player' in iframe_info['class']:
                    logger.info("✅ 发现视频播放器iframe")
                    
                    # 尝试处理iframe内容
                    success = await self._process_iframe_video(video_page, iframe_info['index'])
                    if success:
                        return True
            
            logger.warning("❌ 所有iframe处理都失败了")
            return False
            
        except Exception as e:
            logger.error(f"❌ 处理视频页面iframe时异常: {e}")
            return False
    
    async def _process_iframe_video(self, video_page, iframe_index) -> bool:
        """处理specific iframe中的视频内容"""
        try:
            logger.info(f"🔧 处理iframe {iframe_index+1} 的视频内容...")
            
            # 方法1: JavaScript直接访问iframe内容
            js_success = await self._iframe_javascript_method(video_page, iframe_index)
            if js_success:
                return True
            
            # 方法2: Playwright frame locator
            frame_success = await self._iframe_frame_locator_method(video_page, iframe_index)
            if frame_success:
                return True
            
            # 方法3: 延迟重试
            logger.info("🔄 延迟后重试...")
            await asyncio.sleep(5)
            retry_success = await self._iframe_javascript_method(video_page, iframe_index)
            if retry_success:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 处理iframe视频内容时异常: {e}")
            return False
    
    async def _iframe_javascript_method(self, video_page, iframe_index) -> bool:
        """使用JavaScript方法处理iframe内容"""
        try:
            result = await video_page.evaluate(f"""
                (index) => {{
                    const iframe = document.querySelectorAll('iframe')[index];
                    if (!iframe) return {{ success: false, error: 'iframe不存在' }};
                    
                    try {{
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (!iframeDoc) {{
                            return {{ success: false, error: '跨域iframe', crossOrigin: true }};
                        }}
                        
                        // 优先处理按钮点击 - 增强版，专门处理发现的div按钮
                        const allButtons = [
                            ...iframeDoc.querySelectorAll('button'),
                            ...iframeDoc.querySelectorAll('div[onclick]'), 
                            ...iframeDoc.querySelectorAll('.btn'),
                            ...iframeDoc.querySelectorAll('[class*="play"]'),
                            // 专门添加发现的按钮类
                            ...iframeDoc.querySelectorAll('.user_choise'),  // 发现的"开始学习"按钮
                            ...iframeDoc.querySelectorAll('.continue'),     // 发现的"继续学习"相关按钮
                            ...iframeDoc.querySelectorAll('div[style*="cursor: pointer"]'), // 光标为pointer的div
                        ];
                        
                        // 按优先级排序和点击
                        const candidates = [];
                        for (let btn of allButtons) {{
                            const text = btn.textContent?.trim() || '';
                            const style = iframeDoc.defaultView.getComputedStyle(btn);
                            const rect = btn.getBoundingClientRect();
                            
                            // 更全面的可点击判断
                            const isClickable = (
                                btn.onclick || 
                                btn.className.includes('btn') || 
                                btn.className.includes('user_choise') ||
                                btn.className.includes('continue') ||
                                style.cursor === 'pointer' ||
                                btn.tagName === 'BUTTON'
                            );
                            
                            if (rect.width > 0 && rect.height > 0 && (
                                text.includes('继续学习') || text.includes('开始学习') || 
                                text.includes('播放') || text.includes('play') ||
                                btn.className.includes('user_choise') || // 专门处理发现的类名
                                btn.className.includes('continue')
                            )) {{
                                candidates.push({{
                                    element: btn,
                                    text: text,
                                    priority: text.includes('开始学习') ? 5 : 
                                             text.includes('继续学习') ? 4 : 
                                             text.includes('播放') ? 3 :
                                             btn.className.includes('user_choise') ? 4 :
                                             btn.className.includes('continue') ? 3 : 1,
                                    isClickable: isClickable,
                                    className: btn.className
                                }});
                            }}
                        }}
                        
                        // 按优先级排序
                        candidates.sort((a, b) => b.priority - a.priority);
                        
                        for (let candidate of candidates) {{
                            try {{
                                candidate.element.click();
                                return {{ 
                                    success: true, 
                                    method: 'enhanced_button_click', 
                                    text: candidate.text,
                                    className: candidate.className,
                                    priority: candidate.priority
                                }};
                            }} catch (e) {{
                                console.log('点击失败:', e);
                            }}
                        }}
                        
                        // 如果按钮点击失败，尝试直接播放视频作为备用方案
                        const videos = iframeDoc.querySelectorAll('video');
                        if (videos.length > 0) {{
                            for (let video of videos) {{
                                if (video.paused) {{
                                    try {{
                                        video.play();
                                        return {{ success: true, method: 'direct_play_fallback', count: videos.length }};
                                    }} catch (e) {{
                                        console.log('直接播放视频失败:', e);
                                    }}
                                }}
                            }}
                        }}
                        
                        return {{ success: false, error: '未找到可操作元素', videos: videos.length, buttons: allButtons.length }};
                        
                    }} catch (e) {{
                        return {{ success: false, error: e.message }};
                    }}
                }}
            """, iframe_index)
            
            if result['success']:
                logger.info(f"✅ JavaScript方法成功: {result['method']}")
                if 'text' in result:
                    logger.info(f"   点击了: {result['text']}")
                elif 'count' in result:
                    logger.info(f"   播放了 {result['count']} 个视频")
                return True
            else:
                logger.warning(f"❌ JavaScript方法失败: {result['error']}")
                if not result.get('crossOrigin') and ('videos' in result or 'buttons' in result):
                    logger.info(f"   iframe内容: {result.get('videos', 0)}个视频, {result.get('buttons', 0)}个按钮")
                return False
                
        except Exception as e:
            logger.error(f"❌ JavaScript方法异常: {e}")
            return False
    
    async def _iframe_frame_locator_method(self, video_page, iframe_index) -> bool:
        """使用Playwright frame locator处理iframe"""
        try:
            iframe_selector = f"iframe:nth-child({iframe_index + 1})"
            frame = video_page.frame_locator(iframe_selector)
            
            # 尝试找到并点击视频
            video_count = await frame.locator('video').count()
            if video_count > 0:
                logger.info(f"🎬 frame locator发现 {video_count} 个视频")
                video = frame.locator('video').first
                if await video.is_visible():
                    await video.click()
                    logger.info("✅ frame locator点击了视频")
                    return True
            
            # 尝试找到并点击播放按钮
            selectors = [
                'button:has-text("继续学习")', 'button:has-text("开始学习")',
                'button:has-text("播放")', 'div:has-text("继续学习")',
                '.play-btn', '.continue-btn', '[class*="play"]'
            ]
            
            for selector in selectors:
                try:
                    count = await frame.locator(selector).count()
                    if count > 0:
                        element = frame.locator(selector).first
                        if await element.is_visible():
                            await element.click()
                            logger.info(f"✅ frame locator点击了 '{selector}'")
                            return True
                except Exception as e:
                    logger.debug(f"尝试 '{selector}' 失败: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"❌ Frame locator方法失败: {e}")
            return False
    
    async def pause(self) -> bool:
        """暂停视频"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        videos[0].pause();
                        return true;
                    }
                    return false;
                }
            """)
            return result
        except:
            return False
    
    async def get_current_time(self) -> float:
        """获取当前播放时间"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return videos[0].currentTime;
                    }
                    return 0;
                }
            """)
            return float(result)
        except:
            return 0.0
    
    async def get_duration(self) -> float:
        """获取视频总时长"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return videos[0].duration;
                    }
                    return 0;
                }
            """)
            return float(result)
        except:
            return 0.0
    
    async def seek_to(self, position: float) -> bool:
        """跳转到指定位置"""
        try:
            result = await self.page.evaluate(f"""
                (position) => {{
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {{
                        videos[0].currentTime = position;
                        return true;
                    }}
                    return false;
                }}
            """, position)
            return result
        except:
            return False
    
    async def is_playing(self) -> bool:
        """检测是否正在播放"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return !videos[0].paused;
                    }
                    return false;
                }
            """)
            return result
        except:
            return False
    
    async def is_ended(self) -> bool:
        """检测是否播放结束"""
        try:
            result = await self.page.evaluate("""
                () => {
                    const videos = document.querySelectorAll('video');
                    if (videos.length > 0) {
                        return videos[0].ended;
                    }
                    return false;
                }
            """)
            return result
        except:
            return False
    
    async def get_playback_status(self) -> PlaybackStatus:
        """获取播放状态"""
        try:
            is_ended = await self.is_ended()
            if is_ended:
                return PlaybackStatus.COMPLETED
            
            is_playing = await self.is_playing()
            if is_playing:
                return PlaybackStatus.PLAYING
            else:
                return PlaybackStatus.PAUSED
        except:
            return PlaybackStatus.ERROR


class ProgressMonitor:
    """进度监控器"""
    
    def __init__(self, video_controller: VideoController, check_interval: float = 1.0):
        """初始化进度监控器"""
        self.video_controller = video_controller
        self.check_interval = check_interval
        self.is_monitoring = False
        self.callbacks: List[Callable] = []
        self._monitor_task = None
        self._last_position = 0.0
        self._stuck_count = 0
    
    def add_progress_callback(self, callback: Callable):
        """添加进度回调"""
        self.callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable):
        """移除进度回调"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    async def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_progress())
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_progress(self):
        """监控进度的内部方法"""
        while self.is_monitoring:
            try:
                position = await self.video_controller.get_current_time()
                duration = await self.video_controller.get_duration()
                status = await self.video_controller.get_playback_status()
                
                # 检测播放卡死
                if position == self._last_position and status == PlaybackStatus.PLAYING:
                    self._stuck_count += 1
                else:
                    self._stuck_count = 0
                    self._last_position = position
                
                # 计算进度百分比
                progress = (position / duration * 100.0) if duration > 0 else 0.0
                
                # 调用回调函数
                for callback in self.callbacks:
                    try:
                        callback(position, duration, status, progress)
                    except Exception as e:
                        logger.error(f"进度回调执行失败: {e}")
                
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"进度监控错误: {e}")
                await asyncio.sleep(self.check_interval)


class LearningAutomator:
    """学习自动化器"""
    
    def __init__(self, page, anti_detection=None, data_dir: Path = None):
        """初始化学习自动化器"""
        self.page = page
        self.anti_detection = anti_detection
        self.data_dir = data_dir or Path.cwd() / "data"
        
        # 创建数据目录
        self.playback_dir = self.data_dir / "playback"
        self.sessions_dir = self.data_dir / "sessions"
        self.playback_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.video_controller = VideoController(page)
        self.progress_monitor = ProgressMonitor(self.video_controller)
        
        # 会话状态
        self.current_session: Optional[LearningSession] = None
        self.playback_state: Optional[PlaybackState] = None
    
    def _save_playback_state(self, state: PlaybackState):
        """保存播放状态"""
        try:
            file_path = self.playback_dir / f"{state.course_id}.json"
            temp_path = file_path.with_suffix('.json.tmp')
            
            # 原子写入
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
            
            temp_path.rename(file_path)
            logger.debug(f"播放状态已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存播放状态失败: {e}")
    
    def _load_playback_state(self, course_id: str) -> Optional[PlaybackState]:
        """加载播放状态"""
        try:
            file_path = self.playback_dir / f"{course_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return PlaybackState.from_dict(data)
            
        except Exception as e:
            logger.error(f"加载播放状态失败: {e}")
            return None
    
    def _save_learning_session(self, session: LearningSession):
        """保存学习会话"""
        try:
            file_path = self.sessions_dir / f"{session.session_id}.json"
            temp_path = file_path.with_suffix('.json.tmp')
            
            # 原子写入
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
            
            temp_path.rename(file_path)
            logger.debug(f"学习会话已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存学习会话失败: {e}")
    
    def _load_learning_session(self, session_id: str) -> Optional[LearningSession]:
        """加载学习会话"""
        try:
            file_path = self.sessions_dir / f"{session_id}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 重新创建会话对象
            session = LearningSession(
                course_id=data["course_id"],
                mode=LearningMode(data["mode"])
            )
            session.session_id = data["session_id"]
            session.start_time = datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None
            session.end_time = datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
            session.total_time = data.get("total_time", 0.0)
            session.videos_completed = data.get("videos_completed", 0)
            session.errors = data.get("errors", [])
            session.progress_snapshots = data.get("progress_snapshots", [])
            
            return session
            
        except Exception as e:
            logger.error(f"加载学习会话失败: {e}")
            return None
    
    async def start_video_learning(self, course_id: str, resume: bool = True, mode: LearningMode = LearningMode.NORMAL) -> bool:
        """开始视频学习"""
        try:
            # 检查是否已有活动会话
            if self.current_session is not None:
                logger.warning("已有活动学习会话，无法开始新的学习")
                return False
            
            # 检测视频播放器
            has_player = await self.video_controller.detect_video_player()
            if not has_player:
                logger.error("未检测到视频播放器")
                return False
            
            # 创建新的学习会话
            self.current_session = LearningSession(course_id=course_id, mode=mode)
            
            # 尝试加载已保存的播放状态
            if resume:
                saved_state = self._load_playback_state(course_id)
                if saved_state:
                    self.playback_state = saved_state
                    self.playback_state.session_id = self.current_session.session_id
                    
                    # 跳转到断点位置
                    if self.playback_state.position > 0:
                        await self.video_controller.seek_to(self.playback_state.position)
                        logger.info(f"已跳转到断点位置: {self.playback_state.position}秒")
                else:
                    # 创建新的播放状态
                    self.playback_state = PlaybackState(
                        course_id=course_id,
                        session_id=self.current_session.session_id
                    )
            else:
                # 创建新的播放状态
                self.playback_state = PlaybackState(
                    course_id=course_id,
                    session_id=self.current_session.session_id
                )
            
            # 开始播放
            play_success = await self.video_controller.play()
            if not play_success:
                logger.error("播放视频失败")
                self.current_session = None
                self.playback_state = None
                return False
            
            # 获取视频信息
            duration = await self.video_controller.get_duration()
            current_time = await self.video_controller.get_current_time()
            
            # 更新播放状态
            self.playback_state.duration = duration
            self.playback_state.position = current_time
            self.playback_state.status = PlaybackStatus.PLAYING
            self.playback_state.last_played = datetime.now()
            self.playback_state.play_count += 1
            
            # 设置播放速度（快速模式）
            if mode == LearningMode.FAST:
                try:
                    await self.page.evaluate("""
                        () => {
                            const videos = document.querySelectorAll('video');
                            if (videos.length > 0) {
                                videos[0].playbackRate = 2.0;
                            }
                        }
                    """)
                except:
                    pass
            
            # 反检测延迟
            if self.anti_detection:
                await self.anti_detection.random_delay(0.5, 2.0)
            
            logger.info(f"开始学习课程: {course_id}, 模式: {mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"开始视频学习失败: {e}")
            self.current_session = None
            self.playback_state = None
            return False
    
    async def pause_learning(self) -> bool:
        """暂停学习"""
        if not self.current_session or not self.playback_state:
            return False
        
        try:
            success = await self.video_controller.pause()
            if success:
                # 更新播放位置
                current_time = await self.video_controller.get_current_time()
                self.playback_state.position = current_time
                self.playback_state.status = PlaybackStatus.PAUSED
                
                # 保存状态
                self._save_playback_state(self.playback_state)
                
                logger.info("学习已暂停")
                return True
            
        except Exception as e:
            logger.error(f"暂停学习失败: {e}")
        
        return False
    
    async def resume_learning(self) -> bool:
        """恢复学习"""
        if not self.current_session or not self.playback_state:
            return False
        
        try:
            success = await self.video_controller.play()
            if success:
                # 更新播放位置和状态
                current_time = await self.video_controller.get_current_time()
                self.playback_state.position = current_time
                self.playback_state.status = PlaybackStatus.PLAYING
                
                logger.info("学习已恢复")
                return True
            
        except Exception as e:
            logger.error(f"恢复学习失败: {e}")
        
        return False
    
    async def stop_learning(self):
        """停止学习"""
        if not self.current_session:
            return
        
        try:
            # 停止进度监控
            await self.progress_monitor.stop_monitoring()
            
            # 暂停视频
            await self.video_controller.pause()
            
            # 更新最终状态
            if self.playback_state:
                current_time = await self.video_controller.get_current_time()
                self.playback_state.position = current_time
                self.playback_state.status = PlaybackStatus.STOPPED
                self._save_playback_state(self.playback_state)
            
            # 完成会话
            self.current_session.end_time = datetime.now()
            self._save_learning_session(self.current_session)
            
            logger.info("学习已停止")
            
        except Exception as e:
            logger.error(f"停止学习失败: {e}")
    
    def _handle_playback_error(self, error_type: str, error_message: str) -> str:
        """处理播放错误"""
        if self.playback_state:
            self.playback_state.error_count += 1
        
        if self.current_session:
            error_info = f"{error_type}: {error_message}"
            self.current_session.errors.append(error_info)
        
        # 根据错误类型决定恢复策略
        if error_type == "network_error":
            return "refresh_page"
        elif error_type == "playback_stuck":
            return "restart_playback"
        elif error_type == "buffering_timeout":
            return "wait_and_retry"
        else:
            return "log_and_skip"
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习统计"""
        stats = {
            "current_session": self.current_session.to_dict() if self.current_session else None,
            "playback_state": self.playback_state.to_dict() if self.playback_state else None,
            "total_learning_time": self.current_session.total_time if self.current_session else 0,
            "videos_completed": self.current_session.videos_completed if self.current_session else 0,
            "error_count": self.playback_state.error_count if self.playback_state else 0,
            "session_errors": self.current_session.errors if self.current_session else []
        }
        return stats
    
    def add_progress_callback(self, callback: Callable):
        """添加进度回调"""
        self.progress_monitor.add_progress_callback(callback)
    
    async def cleanup(self):
        """清理资源"""
        await self.progress_monitor.stop_monitoring()
        
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self._save_learning_session(self.current_session)