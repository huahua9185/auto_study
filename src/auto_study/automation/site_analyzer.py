"""
网站分析器

负责分析网站结构、元素定位、页面状态检测等
"""

import asyncio
from typing import Dict, List, Optional
from playwright.async_api import Page


class SiteAnalyzer:
    """网站分析器"""
    
    def __init__(self, page: Page):
        self.page = page
        self.selectors: Dict[str, str] = {}
    
    async def analyze_login_page(self) -> Dict[str, str]:
        """分析登录页面结构"""
        try:
            await self.page.goto("https://edu.nxgbjy.org.cn/login")
            await self.page.wait_for_load_state('networkidle')
            
            # 分析表单元素
            username_selectors = [
                'input[name="username"]',
                'input[name="user"]', 
                'input[name="account"]',
                'input[type="text"]',
                '#username',
                '#user'
            ]
            
            password_selectors = [
                'input[name="password"]',
                'input[name="pwd"]',
                'input[type="password"]',
                '#password',
                '#pwd'
            ]
            
            captcha_selectors = [
                'input[name="captcha"]',
                'input[name="code"]',
                'input[name="verifyCode"]',
                '#captcha',
                '#code'
            ]
            
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.login-btn',
                '.submit-btn',
                'button:has-text("登录")',
                'button:has-text("登陆")'
            ]
            
            # 查找有效选择器
            selectors = {}
            selectors['username'] = await self._find_valid_selector(username_selectors)
            selectors['password'] = await self._find_valid_selector(password_selectors)
            selectors['captcha'] = await self._find_valid_selector(captcha_selectors)
            selectors['submit'] = await self._find_valid_selector(submit_selectors)
            
            # 查找验证码图片
            captcha_img_selectors = [
                'img[alt*="验证码"]',
                'img[alt*="captcha"]',
                'img.captcha-img',
                '.captcha img'
            ]
            selectors['captcha_img'] = await self._find_valid_selector(captcha_img_selectors)
            
            self.selectors.update(selectors)
            return selectors
            
        except Exception as e:
            print(f"分析登录页面失败: {e}")
            return {}
    
    async def analyze_course_list_page(self) -> Dict[str, str]:
        """分析课程列表页面结构"""
        try:
            await self.page.goto("https://edu.nxgbjy.org.cn/courses")
            await self.page.wait_for_load_state('networkidle')
            
            # 课程相关选择器
            course_selectors = [
                '.course-item',
                '.course-card',
                '.course-list li',
                '.lesson-item'
            ]
            
            title_selectors = [
                '.course-title',
                '.course-name',
                'h3',
                'h4'
            ]
            
            status_selectors = [
                '.course-status',
                '.status',
                '.progress-status'
            ]
            
            progress_selectors = [
                '.progress-text',
                '.progress-percent',
                '.course-progress'
            ]
            
            # 查找有效选择器
            selectors = {}
            selectors['course_item'] = await self._find_valid_selector(course_selectors)
            selectors['course_title'] = await self._find_valid_selector(title_selectors)
            selectors['course_status'] = await self._find_valid_selector(status_selectors)
            selectors['course_progress'] = await self._find_valid_selector(progress_selectors)
            
            self.selectors.update(selectors)
            return selectors
            
        except Exception as e:
            print(f"分析课程列表页面失败: {e}")
            return {}
    
    async def analyze_learning_page(self, course_url: str) -> Dict[str, str]:
        """分析学习页面结构"""
        try:
            await self.page.goto(course_url)
            await self.page.wait_for_load_state('networkidle')
            
            # 视频播放器相关选择器
            video_selectors = [
                'video',
                '.video-player video',
                '.dplayer-video'
            ]
            
            play_button_selectors = [
                'button.play-btn',
                '.video-play-button',
                '.dplayer-play-icon',
                '[aria-label*="播放"]',
                '.play-icon'
            ]
            
            progress_selectors = [
                '.video-progress',
                '.dplayer-progress',
                '.progress-bar'
            ]
            
            # 查找有效选择器
            selectors = {}
            selectors['video'] = await self._find_valid_selector(video_selectors)
            selectors['play_button'] = await self._find_valid_selector(play_button_selectors)
            selectors['video_progress'] = await self._find_valid_selector(progress_selectors)
            
            self.selectors.update(selectors)
            return selectors
            
        except Exception as e:
            print(f"分析学习页面失败: {e}")
            return {}
    
    async def _find_valid_selector(self, selectors: List[str]) -> Optional[str]:
        """查找有效的选择器"""
        for selector in selectors:
            try:
                element = self.page.locator(selector)
                if await element.is_visible():
                    return selector
            except:
                continue
        return None
    
    async def get_page_info(self) -> Dict[str, str]:
        """获取当前页面信息"""
        try:
            return {
                'url': self.page.url,
                'title': await self.page.title(),
                'html': await self.page.content()
            }
        except Exception as e:
            print(f"获取页面信息失败: {e}")
            return {}
    
    async def take_screenshot(self, filename: str = "screenshot.png") -> str:
        """截取页面截图"""
        try:
            import os
            os.makedirs("logs", exist_ok=True)
            
            screenshot_path = f"logs/{filename}"
            await self.page.screenshot(path=screenshot_path, full_page=True)
            return screenshot_path
            
        except Exception as e:
            print(f"截图失败: {e}")
            return ""