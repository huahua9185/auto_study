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
    
    async def login(self, username: str, password: str, max_captcha_retries: int = 5) -> bool:
        """执行登录流程，支持验证码错误重试"""
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
            
            # 验证码重试循环
            for attempt in range(max_captcha_retries):
                logger.info(f"验证码尝试 {attempt + 1}/{max_captcha_retries}")
                
                # 每次都按照顺序填写：用户名 -> 密码 -> 验证码
                logger.info("按顺序填写表单: 用户名 -> 密码 -> 验证码")
                
                # 1. 填写用户名
                logger.info("1. 填写用户名")
                username_input = self.page.locator(self.selectors['username'])
                await username_input.clear()
                await username_input.fill(username)
                await asyncio.sleep(0.5)
                
                # 2. 填写密码
                logger.info("2. 填写密码")
                password_input = self.page.locator(self.selectors['password'])
                await password_input.clear()
                await password_input.fill(password)
                await asyncio.sleep(0.5)
                
                # 3. 处理验证码（最后填写）
                logger.info("3. 处理验证码")
                captcha_solved = await self._handle_captcha()
                if not captcha_solved:
                    logger.error(f"验证码处理失败，尝试 {attempt + 1}")
                    if attempt < max_captcha_retries - 1:
                        await asyncio.sleep(2)  # 等待一下再重试
                        continue
                    else:
                        logger.error("验证码处理多次失败，放弃登录")
                        return False
                
                # 点击登录按钮
                logger.info("点击登录按钮")
                login_button = self.page.locator(self.selectors['login_button'])
                if not await login_button.is_visible():
                    # 备用按钮选择器
                    login_button = self.page.locator(self.selectors['submit_button'])
                
                await login_button.click()
                
                # 等待登录结果（增加等待时间用于验证码验证）
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                except:
                    pass  # 忽略超时，继续检查结果
                await asyncio.sleep(2)  # 给服务器验证时间
                
                # 检查登录结果
                login_result = await self._check_login_result()
                
                if login_result == "success":
                    logger.info("✅ 登录成功!")
                    return True
                elif login_result == "captcha_error":
                    logger.warning(f"❌ 验证码错误，第 {attempt + 1}/{max_captcha_retries} 次尝试")
                    if attempt < max_captcha_retries - 1:
                        # 刷新验证码
                        await self._refresh_captcha()
                        await asyncio.sleep(1)
                        logger.info("准备重新按顺序填写所有表单项...")
                        continue
                    else:
                        logger.error("⛔ 验证码多次错误，登录失败")
                        logger.error(f"失败原因: 尝试了 {max_captcha_retries} 次验证码均失败")
                        logger.info("建议: 1. 检查验证码识别模型是否正常")
                        logger.info("      2. 尝试手动登录查看验证码是否特殊")
                        logger.info("      3. 考虑增加重试次数或改进识别算法")
                        return False
                elif login_result == "other_error":
                    logger.error("登录失败：用户名、密码错误或其他问题")
                    # 可能是网络问题，尝试重新填写
                    if attempt < max_captcha_retries - 1:
                        logger.info("尝试重新登录...")
                        await asyncio.sleep(2)
                        continue
                    return False
                else:
                    logger.error("登录状态未知")
                    if attempt < max_captcha_retries - 1:
                        logger.info("状态未知，尝试重新登录...")
                        await asyncio.sleep(2)
                        continue
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"登录过程异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def _handle_captcha(self) -> bool:
        """处理验证码（最后填写）"""
        try:
            logger.info("🔍 检查验证码")
            
            # 在填写验证码前，确保用户名和密码已经填写
            # 检查用户名和密码是否已填写
            try:
                username_value = await self.page.locator(self.selectors['username']).input_value()
                password_value = await self.page.locator(self.selectors['password']).input_value()
                if not username_value or not password_value:
                    logger.warning("⚠️ 用户名或密码为空，这不应该发生")
            except:
                pass
            
            # 查找验证码图片
            captcha_img = self.page.locator(self.selectors['captcha_image'])
            
            # 等待验证码图片加载
            try:
                await captcha_img.wait_for(state='visible', timeout=5000)
                logger.info("✅ 找到验证码图片")
            except:
                logger.info("ℹ️ 未找到验证码图片，可能不需要验证码")
                return True
            
            # 等待图片完全加载
            await asyncio.sleep(0.5)
            
            # 截取验证码图片
            logger.info("📸 截取验证码图片")
            captcha_bytes = await captcha_img.screenshot()
            
            # 检查图片大小（避免空图片）
            if len(captcha_bytes) < 1000:
                logger.warning("验证码图片太小，可能未正确加载")
                await asyncio.sleep(1)
                captcha_bytes = await captcha_img.screenshot()
            
            # OCR识别
            logger.info("🤖 识别验证码")
            captcha_text = self.ocr.classification(captcha_bytes)
            logger.info(f"🔤 识别结果: {captcha_text}")
            
            # 验证识别结果基本合理性
            if not captcha_text or len(captcha_text) < 3 or len(captcha_text) > 8:
                logger.warning(f"识别结果异常: '{captcha_text}'，长度: {len(captcha_text) if captcha_text else 0}")
                logger.info("可能需要重新识别")
            
            # 填写验证码（最后一步）
            logger.info("🖊️ 填写验证码（最后一步）")
            captcha_input = self.page.locator(self.selectors['captcha_input'])
            await captcha_input.clear()
            await captcha_input.fill(captcha_text)
            await asyncio.sleep(0.5)
            
            # 确认填写成功
            filled_value = await captcha_input.input_value()
            if filled_value != captcha_text:
                logger.warning(f"验证码填写不一致: 期望'{captcha_text}', 实际'{filled_value}'")
                await captcha_input.clear()
                await captcha_input.fill(captcha_text)
            
            logger.info("✅ 验证码填写完成（所有表单项已按顺序填写）")
            return True
            
        except Exception as e:
            logger.error(f"验证码处理失败: {e}")
            return False
    
    async def _check_login_result(self) -> str:
        """检查登录结果：success, captcha_error, other_error, unknown"""
        try:
            logger.info("检查登录状态")
            
            # 检查页面是否仍然有效
            if self.page.is_closed():
                logger.warning("页面已关闭，无法验证登录状态")
                return "unknown"
            
            # 等待导航完成
            try:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            except Exception as e:
                if "Target page, context or browser has been closed" in str(e):
                    logger.warning("页面上下文在导航期间丢失")
                    return "unknown"
                logger.warning(f"等待页面加载时出错: {e}")
            
            # 等待页面响应
            await asyncio.sleep(3)
            
            # 再次检查页面是否有效
            if self.page.is_closed():
                logger.warning("页面在等待期间被关闭")
                return "unknown"
                
            current_url = self.page.url
            logger.info(f"当前URL: {current_url}")
            
            # 首先检查是否有验证码错误提示（更全面的选择器）
            captcha_error_selectors = [
                # Element UI 消息提示
                '.el-message:has-text("验证码")',
                '.el-message:has-text("校验码")',
                '.el-message--error:has-text("验证码")',
                '.el-message--error:has-text("校验码")',
                '.el-message__content:has-text("验证码错误")',
                '.el-message__content:has-text("验证码不正确")',
                '.el-message__content:has-text("验证码输入错误")',
                
                # 通用错误提示
                '.error-message:has-text("验证码")',
                '.error-message:has-text("校验码")',
                '[class*="error"]:has-text("验证码")',
                '[class*="error"]:has-text("校验码")',
                
                # 表单验证错误
                '.el-form-item__error:has-text("验证码")',
                '.form-error:has-text("验证码")',
                
                # 弹出提示
                '.el-notification:has-text("验证码")',
                '.el-alert:has-text("验证码")',
                
                # 直接文本提示
                'div:has-text("验证码错误")',
                'div:has-text("验证码不正确")',
                'div:has-text("校验码错误")',
                'span:has-text("验证码错误")',
                'p:has-text("验证码错误")'
            ]
            
            for selector in captcha_error_selectors:
                try:
                    if self.page.is_closed():
                        return "unknown"
                    
                    error_elem = self.page.locator(selector)
                    if await error_elem.count() > 0:
                        # 检查所有匹配的元素
                        for i in range(await error_elem.count()):
                            elem = error_elem.nth(i)
                            if await elem.is_visible():
                                error_text = await elem.text_content()
                                logger.warning(f"检测到验证码错误: {error_text}")
                                return "captcha_error"
                except Exception as e:
                    if "Target page, context or browser has been closed" in str(e):
                        return "unknown"
                    continue
            
            # 检查页面是否包含验证码相关的错误文本（更宽泛的检查）
            try:
                page_content = await self.page.content()
                error_keywords = [
                    "验证码错误", "验证码不正确", "验证码输入错误",
                    "校验码错误", "校验码不正确", "请输入正确的验证码"
                ]
                for keyword in error_keywords:
                    if keyword in page_content:
                        logger.warning(f"页面内容中发现验证码错误关键词: {keyword}")
                        # 确认这不是表单提示文本
                        if "placeholder" not in page_content[max(0, page_content.index(keyword)-50):page_content.index(keyword)+50]:
                            return "captcha_error"
            except Exception as e:
                logger.debug(f"页面内容检查失败: {e}")
            
            # 检查URL变化判断登录状态
            if "requireAuth" not in current_url:
                logger.info("URL中无requireAuth参数，登录可能成功")
                # 额外确认：检查是否真的离开了登录页面
                if "/login" not in current_url.lower() and "/signin" not in current_url.lower():
                    return "success"
            
            # 检查是否有具体的错误信息
            if "requireAuth" in current_url or "/login" in current_url.lower():
                # 首先检查是否有明确的错误提示
                try:
                    # 查找包含错误信息的元素
                    error_elements = await self.page.locator('div:has-text("账号名或密码错误"), p:has-text("账号名或密码错误")').count()
                    if error_elements > 0:
                        logger.warning("检测到账号名或密码错误")
                        return "other_error"
                    
                    # 检查验证码相关错误
                    captcha_error_elements = await self.page.locator('div:has-text("验证码错误"), p:has-text("验证码错误")').count()
                    if captcha_error_elements > 0:
                        logger.warning("检测到验证码错误")
                        return "captcha_error"
                    
                    # 只有在没有明确错误提示且验证码被清空时才判断为验证码错误
                    captcha_input = self.page.locator(self.selectors['captcha_input'])
                    if await captcha_input.is_visible():
                        captcha_value = await captcha_input.input_value()
                        username_value = await self.page.locator(self.selectors['username']).input_value()
                        
                        # 如果用户名还在但验证码被清空，可能是验证码错误
                        if username_value and (not captcha_value or len(captcha_value) == 0):
                            logger.warning("用户名保持但验证码被清空，可能是验证码错误")
                            return "captcha_error"
                        # 如果所有表单都被清空，可能是用户名/密码错误
                        elif not username_value and not captcha_value:
                            logger.warning("所有表单都被清空，可能是用户名或密码错误")
                            return "other_error"
                except Exception as e:
                    logger.debug(f"检查错误提示失败: {e}")
            
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
                    # 再次检查页面是否有效
                    if self.page.is_closed():
                        logger.warning("页面在检查用户信息时被关闭")
                        return "unknown"
                        
                    element = self.page.locator(selector)
                    if await element.is_visible():
                        logger.info(f"找到登录成功标识: {selector}")
                        return "success"
                except Exception as e:
                    if "Target page, context or browser has been closed" in str(e):
                        logger.warning("页面上下文在检查用户信息时丢失")
                        return "unknown"
                    continue
            
            # 检查是否有其他错误提示（非验证码错误）
            other_error_selectors = [
                '.error-message:not(:has-text("验证码")):not(:has-text("校验码"))',
                '.alert-danger:not(:has-text("验证码")):not(:has-text("校验码"))', 
                '.el-message--error:not(:has-text("验证码")):not(:has-text("校验码"))'
            ]
            
            for selector in other_error_selectors:
                try:
                    # 检查页面是否仍然有效
                    if self.page.is_closed():
                        logger.warning("页面在检查错误信息时被关闭")
                        return "unknown"
                        
                    error_msg = self.page.locator(selector)
                    if await error_msg.is_visible():
                        error_text = await error_msg.text_content()
                        logger.error(f"登录错误提示: {error_text}")
                        return "other_error"
                except:
                    continue
            
            # 检查登录表单是否还存在
            try:
                login_form_visible = await self.page.locator(self.selectors['username']).is_visible()
                if login_form_visible:
                    logger.warning("登录表单仍然可见，登录失败")
                    
                    # 再次检查是否有明确的错误信息
                    error_text = await self.page.locator('div, p').evaluate_all("""
                        elements => {
                            const errors = [];
                            elements.forEach(el => {
                                const text = el.textContent?.trim();
                                if (text && (text.includes('账号名或密码错误') || 
                                           text.includes('验证码错误') || 
                                           text.includes('用户名错误') || 
                                           text.includes('密码错误'))) {
                                    errors.push(text);
                                }
                            });
                            return errors;
                        }
                    """)
                    
                    if error_text:
                        logger.info(f"发现错误提示: {error_text}")
                        if any('验证码' in err for err in error_text):
                            return "captcha_error"
                        else:
                            return "other_error"
                    
                    return "other_error"
            except Exception as e:
                logger.debug(f"检查登录表单失败: {e}")
            
            # 如果没有明确的错误标识且不在登录页面，则认为成功
            logger.info("无明确的失败标识，假定登录成功")
            return "success"
            
        except Exception as e:
            logger.error(f"登录状态检查失败: {e}")
            return "unknown"
    
    async def _refresh_captcha(self) -> bool:
        """刷新验证码"""
        try:
            logger.info("🔄 刷新验证码")
            
            # 检查页面是否有效
            if self.page.is_closed():
                logger.warning("页面已关闭，无法刷新验证码")
                return False
            
            # 首先尝试点击验证码图片（最常见的刷新方式）
            captcha_img = self.page.locator(self.selectors['captcha_image'])
            if await captcha_img.is_visible():
                logger.info("点击验证码图片进行刷新")
                # 保存当前验证码的src用于比较
                old_src = await captcha_img.get_attribute('src')
                await captcha_img.click()
                await asyncio.sleep(1.5)  # 等待新验证码加载
                # 确认验证码已更新
                new_src = await captcha_img.get_attribute('src')
                if old_src != new_src:
                    logger.info("✅ 验证码已刷新")
                else:
                    logger.warning("验证码可能未刷新，尝试其他方法")
                return True
            
            # 备用刷新方式
            refresh_selectors = [
                'img.image[src*="auth_code"]',  # 特定的验证码图片
                '.captcha-img',  # 验证码图片类
                'img[src*="captcha"]',
                'img[src*="verifyCode"]', 
                '[class*="captcha"] img',
                '.refresh-captcha',  # 专门的刷新按钮
                '.captcha-refresh',
                'button:has-text("刷新")',
                'i[class*="refresh"]',  # 刷新图标
                'span:has-text("换一张")'  # 换一张按钮
            ]
            
            captcha_refreshed = False
            for selector in refresh_selectors:
                try:
                    elements = self.page.locator(selector)
                    if await elements.count() > 0:
                        element = elements.first
                        if await element.is_visible():
                            logger.info(f"点击刷新验证码: {selector}")
                            await element.click()
                            await asyncio.sleep(1.5)  # 等待验证码加载
                            captcha_refreshed = True
                            break
                except Exception as e:
                    logger.debug(f"尝试刷新验证码选择器 {selector} 失败: {e}")
                    continue
            
            if not captcha_refreshed:
                logger.warning("⚠️ 未找到明确的验证码刷新方式")
                logger.info("尝试重新加载页面来刷新验证码")
                # 最后的手段：重新加载页面
                # 注意：重新加载页面会清空所有表单，需要在调用方重新填写
                await self.page.reload()
                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                logger.warning("⚠️ 页面已重新加载，所有表单已被清空，需要重新填写")
            
            return True
            
        except Exception as e:
            logger.error(f"刷新验证码失败: {e}")
            return False