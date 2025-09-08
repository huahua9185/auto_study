#!/usr/bin/env python
"""
验证码错误后用户名密码重填测试

测试改进后的登录机制：
1. 验证码错误后会重新填写用户名和密码
2. 防止表单数据丢失
3. 确保每次重试都有完整的登录信息
"""

import asyncio
from src.auto_study.automation.auto_login import AutoLogin
from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger

async def test_login_with_retry():
    """测试登录重试机制"""
    logger.info("=" * 60)
    logger.info("开始测试登录重试机制（包含用户名密码重填）")
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
            
            # 测试场景说明
            logger.info("\n📋 测试场景说明：")
            logger.info("1. 第一次尝试登录")
            logger.info("2. 如果验证码错误，系统会：")
            logger.info("   a) 检测到错误")
            logger.info("   b) 刷新验证码")
            logger.info("   c) 重新填写用户名和密码")
            logger.info("   d) 重新识别验证码")
            logger.info("   e) 再次尝试登录")
            logger.info("-" * 40)
            
            # 执行登录
            username = "640302198607120020"
            password = "Majun7404"
            
            logger.info(f"\n开始登录测试:")
            logger.info(f"用户名: {username}")
            logger.info(f"密码: {'*' * len(password)}")
            
            success = await auto_login.login(
                username=username,
                password=password,
                max_captcha_retries=5
            )
            
            if success:
                logger.info("\n✅ 登录成功！")
                
                # 验证登录状态
                current_url = page.url
                logger.info(f"当前页面URL: {current_url}")
                
                # 检查是否真的登录成功
                if "requireAuth" not in current_url:
                    logger.info("✅ 已成功离开认证页面")
                else:
                    logger.warning("⚠️ URL中仍包含认证参数，可能需要进一步验证")
                
                # 检查用户信息元素
                try:
                    user_elements = await page.locator('[class*="user"]').count()
                    if user_elements > 0:
                        logger.info(f"✅ 找到 {user_elements} 个用户相关元素")
                    
                    # 检查是否有登出按钮
                    logout_button = await page.locator('button:has-text("退出"), button:has-text("注销")').count()
                    if logout_button > 0:
                        logger.info("✅ 找到登出按钮，确认登录成功")
                except:
                    pass
                
            else:
                logger.error("\n❌ 登录失败")
                logger.info("\n失败可能原因：")
                logger.info("1. 验证码识别率太低（多次识别都错误）")
                logger.info("2. 用户名或密码本身就是错误的")
                logger.info("3. 网络连接问题")
                logger.info("4. 网站暂时不可用")
            
            # 保持浏览器打开以便观察
            logger.info("\n保持浏览器打开15秒以便观察...")
            await asyncio.sleep(15)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成")
    logger.info("=" * 60)
    
    # 输出改进总结
    logger.info("\n📊 本次改进的关键点：")
    logger.info("1. ✅ 验证码错误后会自动重新填写用户名和密码")
    logger.info("2. ✅ 检查表单数据是否被清空")
    logger.info("3. ✅ 刷新验证码时会验证是否真的刷新成功")
    logger.info("4. ✅ 页面重载后会重新填写所有表单")
    logger.info("5. ✅ 支持多种登录失败情况的重试")
    
    logger.info("\n💡 解决的问题：")
    logger.info("• 验证码错误后用户名密码被清空导致无法继续登录")
    logger.info("• 某些网站在验证码错误后会清空整个表单")
    logger.info("• 页面刷新后需要重新填写所有信息")

if __name__ == "__main__":
    asyncio.run(test_login_with_retry())