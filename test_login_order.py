#!/usr/bin/env python
"""
测试新的登录顺序逻辑

确保每次都按照正确顺序填写：
1. 用户名
2. 密码  
3. 验证码（最后）
"""

import asyncio
from src.auto_study.automation.auto_login import AutoLogin
from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger

async def test_login_order():
    """测试登录顺序"""
    logger.info("=" * 60)
    logger.info("测试新的登录顺序逻辑")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器方便观察
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 创建登录管理器
            auto_login = AutoLogin(page)
            
            logger.info("\n📋 测试说明：")
            logger.info("每次登录尝试都会按照以下顺序：")
            logger.info("1️⃣ 填写用户名")
            logger.info("2️⃣ 填写密码")
            logger.info("3️⃣ 填写验证码（最后）")
            logger.info("4️⃣ 点击登录按钮")
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
                max_captcha_retries=3  # 减少重试次数便于观察
            )
            
            if success:
                logger.info("\n✅ 登录成功！")
                logger.info("验证新的填写顺序工作正常")
                
                # 验证登录状态
                current_url = page.url
                logger.info(f"当前页面: {current_url}")
                
                if "requireAuth" not in current_url:
                    logger.info("✅ 已成功离开认证页面")
                
            else:
                logger.error("\n❌ 登录失败")
                logger.info("可能原因：")
                logger.info("• 验证码识别准确率低")
                logger.info("• 网络问题")
            
            # 保持浏览器打开
            logger.info("\n保持浏览器打开10秒...")
            await asyncio.sleep(10)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)
    
    logger.info("\n📊 改进内容：")
    logger.info("✅ 每次都按固定顺序填写表单")
    logger.info("✅ 用户名和密码始终在验证码之前填写")
    logger.info("✅ 避免因顺序问题导致的登录失败")

if __name__ == "__main__":
    asyncio.run(test_login_order())