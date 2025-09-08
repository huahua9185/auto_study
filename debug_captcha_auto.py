#!/usr/bin/env python
"""
自动调试验证码问题

检查为什么正确的验证码还是会报错
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.utils.logger import logger
from src.auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()
import ddddocr

async def debug_captcha_auto():
    """自动调试验证码问题"""
    logger.info("=" * 60)
    logger.info("开始自动调试验证码问题")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 监听网络请求
            login_requests = []
            login_responses = []
            
            async def log_request(request):
                if 'login' in request.url.lower() or 'auth' in request.url.lower():
                    logger.info(f"📤 请求: {request.method} {request.url}")
                    if request.method == "POST":
                        try:
                            post_data = request.post_data
                            if post_data:
                                logger.info(f"   请求数据: {post_data}")
                                login_requests.append({
                                    'url': request.url,
                                    'method': request.method,
                                    'data': post_data
                                })
                        except:
                            pass
            
            async def log_response(response):
                if 'login' in response.url.lower() or 'auth' in response.url.lower():
                    logger.info(f"📥 响应: {response.status} {response.url}")
                    try:
                        text = await response.text()
                        if len(text) < 500:
                            logger.info(f"   响应内容: {text}")
                            login_responses.append({
                                'url': response.url,
                                'status': response.status,
                                'text': text
                            })
                    except:
                        pass
            
            page.on("request", log_request)
            page.on("response", log_response)
            
            # 访问登录页面
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/rolling_news?id=notice")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            logger.info("页面加载完成")
            
            # 等待登录表单
            await page.wait_for_selector('input[placeholder*="用户名"]', timeout=10000)
            
            # 测试多次
            for attempt in range(2):
                logger.info(f"\n{'=' * 40}")
                logger.info(f"测试尝试 {attempt + 1}/2")
                logger.info(f"{'=' * 40}")
                
                # 清空之前的请求记录
                login_requests.clear()
                login_responses.clear()
                
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
                
                # 获取验证码URL
                captcha_url = await captcha_img.get_attribute('src')
                logger.info(f"验证码URL: {captcha_url}")
                
                # OCR识别
                ocr = ddddocr.DdddOcr()
                captcha_bytes = await captcha_img.screenshot()
                captcha_text = ocr.classification(captcha_bytes)
                logger.info(f"🤖 OCR识别结果: {captcha_text}")
                
                # 保存验证码图片
                await captcha_img.screenshot(path=f"debug_captcha_{attempt + 1}.png")
                logger.info(f"✅ 验证码图片已保存为 debug_captcha_{attempt + 1}.png")
                
                # 填写验证码
                captcha_input = page.locator('input[placeholder*="验证码"]')
                await captcha_input.clear()
                await captcha_input.fill(captcha_text)
                logger.info(f"✅ 已填写验证码: {captcha_text}")
                
                # 登录前检查表单值
                form_values_before = await page.evaluate("""
                    () => {
                        const username = document.querySelector('input[placeholder*="用户名"]').value;
                        const password = document.querySelector('input[type="password"]').value;
                        const captcha = document.querySelector('input[placeholder*="验证码"]').value;
                        return { username, password: password ? '***' : '', captcha };
                    }
                """)
                logger.info(f"登录前表单值: {form_values_before}")
                
                # 点击登录
                logger.info("点击登录按钮...")
                login_button = page.locator('button.el-button--primary:has-text("登录")')
                await login_button.click()
                
                # 等待响应
                await asyncio.sleep(3)
                
                # 检查结果
                current_url = page.url
                logger.info(f"当前URL: {current_url}")
                
                # 登录后检查表单值
                form_values_after = await page.evaluate("""
                    () => {
                        const username = document.querySelector('input[placeholder*="用户名"]').value;
                        const password = document.querySelector('input[type="password"]').value;
                        const captcha = document.querySelector('input[placeholder*="验证码"]').value;
                        return { username, password: password ? '***' : '', captcha };
                    }
                """)
                logger.info(f"登录后表单值: {form_values_after}")
                
                # 分析表单变化
                if not form_values_after['captcha'] and form_values_before['captcha']:
                    logger.warning("❗ 验证码输入框被清空 - 可能表示验证码错误")
                if not form_values_after['username'] and form_values_before['username']:
                    logger.warning("❗ 用户名输入框被清空")
                if not form_values_after['password'] and form_values_before['password']:
                    logger.warning("❗ 密码输入框被清空")
                
                # 检查错误消息
                error_messages = await page.evaluate("""
                    () => {
                        const messages = [];
                        // 查找所有可见的文本元素
                        const allElements = document.querySelectorAll('*');
                        allElements.forEach(elem => {
                            const text = elem.textContent;
                            if (text && (text.includes('验证码') || text.includes('错误') || text.includes('失败'))) {
                                const styles = window.getComputedStyle(elem);
                                if (styles.display !== 'none' && styles.visibility !== 'hidden') {
                                    // 检查是否是新出现的元素（不是placeholder等）
                                    if (!elem.placeholder && elem.tagName !== 'INPUT') {
                                        messages.push({
                                            tag: elem.tagName,
                                            text: text.substring(0, 100),
                                            class: elem.className
                                        });
                                    }
                                }
                            }
                        });
                        return messages.slice(0, 5); // 只返回前5个
                    }
                """)
                
                if error_messages:
                    logger.info("发现可能的错误提示:")
                    for msg in error_messages:
                        logger.info(f"  - [{msg['tag']}] {msg['text']}")
                
                # 分析请求和响应
                logger.info("\n📊 请求响应分析:")
                if login_requests:
                    logger.info(f"发送了 {len(login_requests)} 个登录相关请求")
                    for req in login_requests:
                        logger.info(f"  - {req['method']} {req['url']}")
                        if req['data']:
                            logger.info(f"    数据: {req['data'][:200]}")
                
                if login_responses:
                    logger.info(f"收到了 {len(login_responses)} 个登录相关响应")
                    for resp in login_responses:
                        logger.info(f"  - {resp['status']} {resp['url']}")
                        if resp['text']:
                            logger.info(f"    内容: {resp['text'][:200]}")
                
                # 如果登录成功，退出循环
                if "requireAuth" not in current_url:
                    logger.info("✅ 登录成功！")
                    break
                else:
                    logger.info("❌ 登录失败，准备下一次尝试...")
                    # 刷新验证码
                    await captcha_img.click()
                    await asyncio.sleep(2)
            
            # 总结分析
            logger.info("\n" + "=" * 60)
            logger.info("问题分析总结:")
            logger.info("=" * 60)
            
            possible_issues = []
            
            if any("验证码" in str(resp.get('text', '')) for resp in login_responses):
                possible_issues.append("服务器明确返回了验证码错误")
            
            if form_values_after and not form_values_after['captcha']:
                possible_issues.append("验证码输入框被清空（通常表示验证码错误）")
            
            if not login_requests:
                possible_issues.append("没有检测到登录请求（可能是JavaScript问题）")
            
            if possible_issues:
                logger.info("发现的问题:")
                for issue in possible_issues:
                    logger.info(f"  • {issue}")
            else:
                logger.info("未发现明显问题，可能是:")
                logger.info("  • 验证码有大小写敏感")
                logger.info("  • 验证码有特殊字符被识别错误")
                logger.info("  • 服务器端验证码过期太快")
                logger.info("  • 需要其他隐藏字段或token")
            
            # 保持浏览器打开
            logger.info("\n保持浏览器打开20秒，你可以手动尝试...")
            await asyncio.sleep(20)
            
        finally:
            await browser.close()
    
    logger.info("\n调试完成")

if __name__ == "__main__":
    asyncio.run(debug_captcha_auto())