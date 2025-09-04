#!/usr/bin/env python3
"""
测试新的登录重试机制
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

async def test_login_retry():
    """测试登录重试机制"""
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
        
        # 创建登录器
        auto_login = AutoLogin(page)
        
        print("🚀 开始测试新的登录重试机制...")
        print("📝 注意观察验证码错误时的重试行为")
        
        # 测试登录（最多重试3次验证码）
        success = await auto_login.login(username, password, max_captcha_retries=3)
        
        print(f"\n📊 登录结果: {'✅ 成功' if success else '❌ 失败'}")
        
        if success:
            print("🎉 登录成功！验证码重试机制工作正常")
            
            # 验证是否真的登录成功
            current_url = page.url
            print(f"📍 当前URL: {current_url}")
            
            if "requireAuth" not in current_url:
                print("✅ 确认登录成功 - URL中没有requireAuth参数")
            else:
                print("⚠️ 可能登录未完全成功 - URL中仍有requireAuth参数")
        else:
            print("❌ 登录失败，可能是：")
            print("   1. 验证码多次识别错误")
            print("   2. 用户名或密码错误")
            print("   3. 其他网络或系统问题")
        
        print("\n⏳ 等待5秒后关闭浏览器...")
        await asyncio.sleep(5)
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_login_retry())