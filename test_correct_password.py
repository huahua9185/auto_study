#!/usr/bin/env python
"""
使用正确密码测试登录

验证修复后的登录逻辑能否成功登录
"""

import asyncio
from src.auto_study.automation.auto_login import AutoLogin
from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger

async def test_correct_password():
    """使用正确密码测试登录"""
    logger.info("=" * 60)
    logger.info("使用正确密码测试登录")
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
            
            logger.info("\n📋 测试说明：")
            logger.info("使用正确的用户名和密码测试登录")
            logger.info("验证修复后的错误检测逻辑是否正常工作")
            logger.info("-" * 40)
            
            # 使用正确的凭据
            username = "640302198607120020"
            password = "My2062660"  # 正确的密码
            
            logger.info(f"\n开始登录:")
            logger.info(f"用户名: {username}")
            logger.info(f"密码: {'*' * len(password)}")
            
            success = await auto_login.login(
                username=username,
                password=password,
                max_captcha_retries=5
            )
            
            if success:
                logger.info("\n🎉 登录成功！")
                logger.info("✅ 修复后的逻辑工作正常")
                
                # 验证登录状态
                current_url = page.url
                logger.info(f"当前页面: {current_url}")
                
                if "requireAuth" not in current_url:
                    logger.info("✅ 已成功离开认证页面")
                    
                # 检查用户信息
                try:
                    user_elements = await page.locator('[class*="user"]').count()
                    if user_elements > 0:
                        logger.info(f"✅ 找到 {user_elements} 个用户相关元素")
                except:
                    pass
                
            else:
                logger.error("\n❌ 登录仍然失败")
                logger.info("可能的原因：")
                logger.info("• 验证码识别准确率问题")
                logger.info("• 网络连接问题")
                logger.info("• 其他系统问题")
            
            # 保持浏览器打开以便观察
            logger.info("\n保持浏览器打开15秒以便观察...")
            await asyncio.sleep(15)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_correct_password())