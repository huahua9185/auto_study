#!/usr/bin/env python
"""
验证码错误处理测试

测试改进后的验证码验证机制：
1. 更全面的错误检测
2. 验证码错误自动重试
3. 清晰的错误提示和日志
"""

import asyncio
from src.auto_study.automation.auto_login import AutoLogin
from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger

async def test_captcha_validation():
    """测试验证码验证机制"""
    logger.info("=" * 60)
    logger.info("开始测试验证码错误处理机制")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器方便观察
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 创建登录管理器
            auto_login = AutoLogin(page)
            
            # 测试登录（包含验证码错误重试）
            logger.info("\n📋 测试验证码错误处理流程...")
            logger.info("预期行为：")
            logger.info("1. 如果验证码识别错误，系统会自动检测")
            logger.info("2. 检测到错误后会刷新验证码并重试")
            logger.info("3. 最多重试5次")
            logger.info("4. 提供清晰的错误信息和建议")
            logger.info("-" * 40)
            
            # 执行登录
            username = "640302198607120020"
            password = "Majun7404"
            
            success = await auto_login.login(
                username=username,
                password=password,
                max_captcha_retries=5
            )
            
            if success:
                logger.info("✅ 登录成功！验证码处理正常")
                
                # 验证登录状态
                current_url = page.url
                logger.info(f"当前页面: {current_url}")
                
                if "requireAuth" not in current_url:
                    logger.info("✅ 确认已离开认证页面")
                else:
                    logger.warning("⚠️ URL中仍包含requireAuth参数")
                
                # 检查用户信息
                user_elements = await page.locator('[class*="user"]').count()
                if user_elements > 0:
                    logger.info(f"✅ 找到 {user_elements} 个用户相关元素")
                
            else:
                logger.error("❌ 登录失败")
                logger.info("\n失败分析：")
                logger.info("1. 验证码多次识别错误")
                logger.info("2. 用户名或密码错误")
                logger.info("3. 网络问题")
            
            # 等待观察
            logger.info("\n保持浏览器打开10秒以便观察...")
            await asyncio.sleep(10)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("验证码错误处理测试完成")
    logger.info("=" * 60)
    
    # 输出改进总结
    logger.info("\n📊 本次改进内容：")
    logger.info("1. ✅ 增强了验证码错误检测（更多选择器）")
    logger.info("2. ✅ 改进了错误判断逻辑（检查表单状态）")
    logger.info("3. ✅ 优化了验证码刷新机制")
    logger.info("4. ✅ 添加了详细的错误日志和建议")
    logger.info("5. ✅ 验证码填写后会确认值是否正确")

if __name__ == "__main__":
    asyncio.run(test_captcha_validation())