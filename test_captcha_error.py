#!/usr/bin/env python3
"""
专门测试验证码错误处理的脚本
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from dotenv import load_dotenv
load_dotenv()

from playwright.async_api import async_playwright
from auto_study.automation.auto_login import AutoLogin

class TestAutoLogin(AutoLogin):
    """测试用的登录类，可以故意输入错误的验证码"""
    
    def __init__(self, page, force_wrong_captcha=False):
        super().__init__(page)
        self.force_wrong_captcha = force_wrong_captcha
        self.captcha_attempts = 0
    
    async def _handle_captcha(self) -> bool:
        """重写验证码处理，可以故意输入错误答案"""
        try:
            self.captcha_attempts += 1
            logger.info(f"检查验证码 (第 {self.captcha_attempts} 次)")
            
            # 查找验证码图片
            captcha_selectors = [
                '.captcha-img',
                'img[src*="captcha"]',
                'img[src*="verifyCode"]',
                'canvas[id*="captcha"]',
                '[class*="captcha"] img',
                'img[alt*="验证码"]'
            ]
            
            captcha_img = None
            for selector in captcha_selectors:
                try:
                    img = self.page.locator(selector).first
                    if await img.count() > 0:
                        captcha_img = img
                        logger.info("找到验证码图片")
                        break
                except:
                    continue
            
            if not captcha_img:
                logger.warning("未找到验证码图片")
                return True  # 可能没有验证码
            
            # 故意输入错误的验证码（前2次）
            if self.force_wrong_captcha and self.captcha_attempts <= 2:
                wrong_code = "9999"  # 故意错误的验证码
                logger.warning(f"故意输入错误验证码: {wrong_code}")
                
                # 填入验证码
                captcha_input = self.page.locator(self.selectors['captcha'])
                await captcha_input.clear()
                await captcha_input.fill(wrong_code)
                await asyncio.sleep(1)
                
                logger.info("验证码填写完成（故意错误）")
                return True
            else:
                # 正常处理验证码
                return await super()._handle_captcha()
                
        except Exception as e:
            logger.error(f"验证码处理失败: {e}")
            return False

async def test_captcha_error():
    """测试验证码错误处理"""
    try:
        username = os.getenv('AUTO_STUDY_USERNAME') or os.getenv('USERNAME')
        password = os.getenv('AUTO_STUDY_PASSWORD') or os.getenv('PASSWORD')
        
        if not username or not password:
            print("❌ 缺少用户凭据")
            return
        
        print(f"🔐 测试用户: {username}")
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 启用详细日志
        page.on('console', lambda msg: print(f"🖥️ Console: {msg.text}"))
        
        # 创建测试登录器（前2次故意输入错误验证码）
        test_login = TestAutoLogin(page, force_wrong_captcha=True)
        
        print("🚀 开始测试验证码错误重试机制...")
        print("📝 前2次将故意输入错误验证码，观察重试行为")
        
        # 测试登录（最多重试5次验证码）
        success = await test_login.login(username, password, max_captcha_retries=5)
        
        print(f"\n📊 最终登录结果: {'✅ 成功' if success else '❌ 失败'}")
        print(f"📈 验证码尝试次数: {test_login.captcha_attempts}")
        
        if success:
            print("🎉 验证码重试机制工作正常！")
            print("✅ 系统能够正确处理验证码错误并重试")
        else:
            print("❌ 验证码重试可能存在问题")
        
        print("\n⏳ 等待10秒观察最终状态...")
        await asyncio.sleep(10)
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 导入logger
    from auto_study.automation.auto_login import logger
    
    asyncio.run(test_captcha_error())