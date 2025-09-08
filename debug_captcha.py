#!/usr/bin/env python
"""
调试验证码问题

检查为什么正确的验证码还是会报错
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger
from src.auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()
import ddddocr

async def debug_captcha():
    """调试验证码问题"""
    logger.info("=" * 60)
    logger.info("开始调试验证码问题")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 访问登录页面
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/rolling_news?id=notice")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            logger.info("页面加载完成")
            
            # 等待登录表单
            await page.wait_for_selector('input[placeholder*="用户名"]', timeout=10000)
            
            # 分析页面结构
            form_info = await page.evaluate("""
                () => {
                    const result = {
                        inputs: [],
                        captchaInfo: null,
                        formAction: null
                    };
                    
                    // 查找所有输入框
                    const inputs = document.querySelectorAll('input');
                    inputs.forEach(input => {
                        result.inputs.push({
                            type: input.type,
                            placeholder: input.placeholder,
                            name: input.name,
                            id: input.id,
                            class: input.className,
                            value: input.value,
                            maxLength: input.maxLength,
                            required: input.required
                        });
                    });
                    
                    // 查找验证码相关信息
                    const captchaImg = document.querySelector('img.image[src*="auth_code"]');
                    if (captchaImg) {
                        result.captchaInfo = {
                            src: captchaImg.src,
                            alt: captchaImg.alt,
                            width: captchaImg.width,
                            height: captchaImg.height
                        };
                    }
                    
                    // 查找表单
                    const form = document.querySelector('form');
                    if (form) {
                        result.formAction = form.action;
                        result.formMethod = form.method;
                    }
                    
                    return result;
                }
            """)
            
            logger.info(f"输入框信息: {form_info['inputs']}")
            logger.info(f"验证码图片: {form_info['captchaInfo']}")
            
            # 手动填写并观察
            logger.info("\n开始手动测试流程...")
            
            # 1. 填写用户名
            username = "640302198607120020"
            username_input = page.locator('input[placeholder*="用户名"]')
            await username_input.clear()
            await username_input.fill(username)
            logger.info(f"✅ 用户名已填写: {username}")
            
            # 2. 填写密码
            password = "Majun7404"
            password_input = page.locator('input[type="password"]')
            await password_input.clear()
            await password_input.fill(password)
            logger.info(f"✅ 密码已填写: {'*' * len(password)}")
            
            # 3. 处理验证码
            captcha_img = page.locator('img.image[src*="auth_code"]')
            
            # 保存验证码图片
            await captcha_img.screenshot(path="debug_captcha.png")
            logger.info("✅ 验证码图片已保存为 debug_captcha.png")
            
            # OCR识别
            ocr = ddddocr.DdddOcr()
            captcha_bytes = await captcha_img.screenshot()
            captcha_text = ocr.classification(captcha_bytes)
            logger.info(f"🤖 OCR识别结果: {captcha_text}")
            
            # 等待用户手动输入
            logger.info("\n" + "=" * 40)
            logger.info("请查看浏览器中的验证码")
            logger.info(f"OCR识别为: {captcha_text}")
            logger.info("你可以：")
            logger.info("1. 手动输入正确的验证码")
            logger.info("2. 或者让程序自动填写OCR结果")
            logger.info("=" * 40)
            
            choice = input("\n是否使用OCR结果？(y/n，默认y): ").strip().lower()
            
            if choice != 'n':
                # 使用OCR结果
                captcha_input = page.locator('input[placeholder*="验证码"]')
                await captcha_input.clear()
                await captcha_input.fill(captcha_text)
                logger.info(f"✅ 已填写OCR识别的验证码: {captcha_text}")
            else:
                # 等待手动输入
                manual_captcha = input("请输入你看到的验证码: ").strip()
                captcha_input = page.locator('input[placeholder*="验证码"]')
                await captcha_input.clear()
                await captcha_input.fill(manual_captcha)
                logger.info(f"✅ 已填写手动输入的验证码: {manual_captcha}")
            
            # 监听网络请求
            logger.info("\n开始监听网络请求...")
            
            # 设置请求监听
            async def log_request(request):
                if 'login' in request.url.lower() or 'auth' in request.url.lower():
                    logger.info(f"📤 请求: {request.method} {request.url}")
                    if request.method == "POST":
                        try:
                            post_data = request.post_data
                            if post_data:
                                logger.info(f"   请求数据: {post_data}")
                        except:
                            pass
            
            async def log_response(response):
                if 'login' in response.url.lower() or 'auth' in response.url.lower():
                    logger.info(f"📥 响应: {response.status} {response.url}")
                    try:
                        if response.status == 200:
                            text = await response.text()
                            if len(text) < 500:  # 只打印短响应
                                logger.info(f"   响应内容: {text}")
                    except:
                        pass
            
            page.on("request", log_request)
            page.on("response", log_response)
            
            # 点击登录按钮前的状态
            form_values = await page.evaluate("""
                () => {
                    const username = document.querySelector('input[placeholder*="用户名"]').value;
                    const password = document.querySelector('input[type="password"]').value;
                    const captcha = document.querySelector('input[placeholder*="验证码"]').value;
                    return { username, password, captcha };
                }
            """)
            logger.info(f"\n登录前表单值: {form_values}")
            
            # 点击登录
            logger.info("\n点击登录按钮...")
            login_button = page.locator('button.el-button--primary:has-text("登录")')
            await login_button.click()
            
            # 等待响应
            await asyncio.sleep(5)
            
            # 检查结果
            current_url = page.url
            logger.info(f"\n当前URL: {current_url}")
            
            # 检查错误提示
            error_messages = await page.evaluate("""
                () => {
                    const messages = [];
                    // Element UI消息
                    const elMessages = document.querySelectorAll('.el-message');
                    elMessages.forEach(msg => {
                        messages.push({
                            type: 'el-message',
                            text: msg.textContent,
                            class: msg.className
                        });
                    });
                    
                    // 查找所有可能的错误提示
                    const errorElements = document.querySelectorAll('[class*="error"], .error-message');
                    errorElements.forEach(elem => {
                        if (elem.textContent) {
                            messages.push({
                                type: 'error-element',
                                text: elem.textContent,
                                class: elem.className
                            });
                        }
                    });
                    
                    return messages;
                }
            """)
            
            if error_messages:
                logger.info("\n发现错误提示:")
                for msg in error_messages:
                    logger.info(f"  - {msg}")
            
            # 检查表单是否被清空
            form_values_after = await page.evaluate("""
                () => {
                    const username = document.querySelector('input[placeholder*="用户名"]').value;
                    const password = document.querySelector('input[type="password"]').value;
                    const captcha = document.querySelector('input[placeholder*="验证码"]').value;
                    return { username, password, captcha };
                }
            """)
            logger.info(f"\n登录后表单值: {form_values_after}")
            
            if not form_values_after['captcha']:
                logger.info("❗ 验证码输入框被清空了")
            if not form_values_after['username']:
                logger.info("❗ 用户名输入框被清空了")
            if not form_values_after['password']:
                logger.info("❗ 密码输入框被清空了")
            
            # 保持浏览器打开
            logger.info("\n保持浏览器打开30秒，你可以手动尝试...")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("调试完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(debug_captcha())