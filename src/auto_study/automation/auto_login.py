"""
自动登录模块

负责网站自动登录、验证码识别、session管理等
"""

import asyncio
from typing import Optional
from playwright.async_api import Page

# 应用PIL兼容性补丁（必须在导入ddddocr之前）
from ..utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

import ddddocr
from ..config.config_manager import ConfigManager
from ..utils.logger import logger


class AutoLogin:
    """自动登录管理器"""
    
    def __init__(self, page: Page):
        self.page = page
        self.ocr = ddddocr.DdddOcr()
        
        # 加载配置
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        self.login_url = self.config.get('site', {}).get('login_url', '')
        
        # Element UI选择器
        self.selectors = {
            'username': 'input[placeholder*="用户名"]',
            'password': 'input[type="password"]',
            'captcha_input': 'input[placeholder*="验证码"]',
            'captcha_image': 'img.image[src*="auth_code"]',
            'login_button': 'button.el-button--primary:has-text("登录")',
            'submit_button': 'button:has-text("登录")'
        }
    
    async def login(self, username: str, password: str) -> bool:
        """执行登录流程"""
        try:
            logger.info(f"开始登录用户: {username}")
            
            # 访问登录页面
            logger.info(f"访问登录页面: {self.login_url}")
            await self.page.goto(self.login_url)
            await self.page.wait_for_load_state('networkidle')
            
            # 等待Vue.js渲染完成
            await asyncio.sleep(3)
            logger.info(f"实际页面URL: {self.page.url}")
            
            # 等待登录表单出现
            await self.page.wait_for_selector(self.selectors['username'], timeout=10000)
            logger.info("登录表单已加载")
            
            # 填写用户名
            logger.info("填写用户名")
            username_input = self.page.locator(self.selectors['username'])
            await username_input.clear()
            await username_input.fill(username)
            await asyncio.sleep(1)
            
            # 填写密码
            logger.info("填写密码")
            password_input = self.page.locator(self.selectors['password'])
            await password_input.clear()
            await password_input.fill(password)
            await asyncio.sleep(1)
            
            # 处理验证码
            captcha_solved = await self._handle_captcha()
            if not captcha_solved:
                logger.error("验证码处理失败")
                return False
            
            # 点击登录按钮
            logger.info("点击登录按钮")
            login_button = self.page.locator(self.selectors['login_button'])
            if not await login_button.is_visible():
                # 备用按钮选择器
                login_button = self.page.locator(self.selectors['submit_button'])
            
            await login_button.click()
            
            # 等待登录结果
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 检查是否登录成功
            success = await self._check_login_success()
            if success:
                logger.info("登录成功!")
            else:
                logger.error("登录失败")
            
            return success
            
        except Exception as e:
            logger.error(f"登录过程异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def _handle_captcha(self) -> bool:
        """处理验证码"""
        try:
            logger.info("检查验证码")
            
            # 查找验证码图片
            captcha_img = self.page.locator(self.selectors['captcha_image'])
            
            # 等待验证码图片加载
            try:
                await captcha_img.wait_for(state='visible', timeout=5000)
                logger.info("找到验证码图片")
            except:
                logger.info("未找到验证码图片，可能不需要验证码")
                return True
            
            # 截取验证码图片
            logger.info("截取验证码图片")
            captcha_bytes = await captcha_img.screenshot()
            
            # OCR识别
            logger.info("识别验证码")
            captcha_text = self.ocr.classification(captcha_bytes)
            logger.info(f"识别结果: {captcha_text}")
            
            # 填写验证码
            captcha_input = self.page.locator(self.selectors['captcha_input'])
            await captcha_input.clear()
            await captcha_input.fill(captcha_text)
            await asyncio.sleep(1)
            
            logger.info("验证码填写完成")
            return True
            
        except Exception as e:
            logger.error(f"验证码处理失败: {e}")
            return False
    
    async def _check_login_success(self) -> bool:
        """检查登录是否成功"""
        try:
            logger.info("检查登录状态")
            
            # 等待页面响应
            await asyncio.sleep(3)
            current_url = self.page.url
            logger.info(f"当前URL: {current_url}")
            
            # 检查是否还在认证页面（requireAuth参数）
            if "requireAuth" not in current_url:
                logger.info("URL中无requireAuth参数，登录可能成功")
                return True
            
            # 检查是否有用户信息或登录后的元素
            user_info_selectors = [
                '.user-info',
                '.username',
                '[class*="user"]',
                'button:has-text("退出")',
                'button:has-text("注销")',
                '.logout'
            ]
            
            for selector in user_info_selectors:
                try:
                    element = self.page.locator(selector)
                    if await element.is_visible():
                        logger.info(f"找到登录成功标识: {selector}")
                        return True
                except:
                    continue
            
            # 检查是否有错误提示
            error_selectors = [
                '.error-message',
                '.alert-danger', 
                '.el-message--error',
                '[class*="error"]'
            ]
            
            for selector in error_selectors:
                try:
                    error_msg = self.page.locator(selector)
                    if await error_msg.is_visible():
                        error_text = await error_msg.text_content()
                        logger.error(f"登录错误提示: {error_text}")
                        return False
                except:
                    continue
            
            # 检查登录表单是否还存在
            login_form_visible = await self.page.locator(self.selectors['username']).is_visible()
            if login_form_visible:
                logger.warning("登录表单仍然可见，可能登录失败")
                return False
            
            logger.info("无明确的失败标识，假定登录成功")
            return True
            
        except Exception as e:
            logger.error(f"登录状态检查失败: {e}")
            return False