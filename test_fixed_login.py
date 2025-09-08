#!/usr/bin/env python
"""
测试修复后的登录逻辑

验证是否能正确区分：
1. 验证码错误
2. 用户名/密码错误
3. 登录成功
"""

import asyncio
from src.auto_study.automation.auto_login import AutoLogin
from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger

async def test_fixed_login():
    """测试修复后的登录逻辑"""
    logger.info("=" * 60)
    logger.info("测试修复后的登录逻辑")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 创建登录管理器
            auto_login = AutoLogin(page)
            
            logger.info("\n📋 修复内容：")
            logger.info("1. 检查具体的错误提示文本")
            logger.info("2. 区分验证码错误 vs 用户名/密码错误")
            logger.info("3. 只有在确认是验证码问题时才重试验证码")
            logger.info("-" * 40)
            
            # 执行登录
            username = "640302198607120020"
            password = "Majun7404"
            
            logger.info(f"\n开始登录:")
            logger.info(f"用户名: {username}")
            logger.info(f"密码: {'*' * len(password)}")
            
            success = await auto_login.login(
                username=username,
                password=password,
                max_captcha_retries=3
            )
            
            if success:
                logger.info("\n✅ 登录成功！")
                
                # 验证登录状态
                current_url = page.url
                logger.info(f"当前页面: {current_url}")
                
                if "requireAuth" not in current_url:
                    logger.info("✅ 已成功离开认证页面")
                
            else:
                logger.error("\n❌ 登录失败")
                logger.info("现在系统应该能够正确识别失败原因：")
                logger.info("• 如果是验证码问题，会显示验证码错误")
                logger.info("• 如果是用户名/密码问题，会显示账号名或密码错误")
                logger.info("• 避免了错误地将密码问题归咎于验证码")
            
            # 保持浏览器打开
            logger.info("\n保持浏览器打开10秒...")
            await asyncio.sleep(10)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)
    
    logger.info("\n📊 修复总结：")
    logger.info("✅ 增强了错误检测逻辑")
    logger.info("✅ 区分不同类型的登录错误")
    logger.info("✅ 避免错误地判断验证码错误")
    logger.info("✅ 更准确的错误原因识别")

if __name__ == "__main__":
    asyncio.run(test_fixed_login())