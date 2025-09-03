#!/usr/bin/env python3
"""
登录页面调试脚本

分析登录页面的实际元素，为自动填写功能提供准确的选择器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright
from src.auto_study.config.config_manager import ConfigManager
from src.auto_study.utils.logger import logger


async def debug_login_page():
    """调试登录页面元素"""
    try:
        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        login_url = config.get('site', {}).get('login_url', '')
        
        print("🔍 登录页面元素分析")
        print(f"登录URL: {login_url}")
        print("-" * 60)
        
        # 启动浏览器
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False, 
            slow_mo=500,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        # 访问登录页面
        print(f"📍 访问登录页面: {login_url}")
        await page.goto(login_url)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)  # 等待Vue.js渲染完成
        
        print(f"实际URL: {page.url}")
        print(f"页面标题: {await page.title()}")
        
        # 分析所有输入框
        print(f"\n🔍 分析输入框元素:")
        inputs = await page.query_selector_all('input')
        
        for i, input_elem in enumerate(inputs):
            try:
                tag_name = await input_elem.evaluate('el => el.tagName')
                input_type = await input_elem.get_attribute('type') or 'text'
                name = await input_elem.get_attribute('name') or ''
                id_attr = await input_elem.get_attribute('id') or ''
                placeholder = await input_elem.get_attribute('placeholder') or ''
                class_attr = await input_elem.get_attribute('class') or ''
                is_visible = await input_elem.is_visible()
                
                print(f"输入框 {i+1}:")
                print(f"  类型: {input_type}")
                print(f"  name: '{name}'")
                print(f"  id: '{id_attr}'")
                print(f"  class: '{class_attr}'")
                print(f"  placeholder: '{placeholder}'")
                print(f"  可见: {is_visible}")
                print()
            except Exception as e:
                print(f"  分析输入框 {i+1} 时出错: {e}")
        
        # 分析表单
        print(f"📝 分析表单元素:")
        forms = await page.query_selector_all('form')
        for i, form in enumerate(forms):
            try:
                action = await form.get_attribute('action') or ''
                method = await form.get_attribute('method') or ''
                print(f"表单 {i+1}: action='{action}', method='{method}'")
            except Exception as e:
                print(f"  分析表单 {i+1} 时出错: {e}")
        
        # 分析按钮
        print(f"\n🔘 分析按钮元素:")
        buttons = await page.query_selector_all('button, input[type="button"], input[type="submit"]')
        for i, button in enumerate(buttons):
            try:
                tag_name = await button.evaluate('el => el.tagName')
                button_type = await button.get_attribute('type') or ''
                text = await button.text_content() or ''
                class_attr = await button.get_attribute('class') or ''
                is_visible = await button.is_visible()
                
                print(f"按钮 {i+1}: {tag_name}")
                print(f"  类型: '{button_type}'")
                print(f"  文本: '{text.strip()}'")
                print(f"  class: '{class_attr}'")
                print(f"  可见: {is_visible}")
                print()
            except Exception as e:
                print(f"  分析按钮 {i+1} 时出错: {e}")
        
        # 分析验证码
        print(f"🖼️ 分析验证码元素:")
        images = await page.query_selector_all('img')
        captcha_found = False
        for i, img in enumerate(images):
            try:
                src = await img.get_attribute('src') or ''
                alt = await img.get_attribute('alt') or ''
                class_attr = await img.get_attribute('class') or ''
                is_visible = await img.is_visible()
                
                if any(keyword in src.lower() or keyword in alt.lower() or keyword in class_attr.lower() 
                       for keyword in ['captcha', 'verify', 'code', '验证']):
                    print(f"验证码图片 {i+1}:")
                    print(f"  src: '{src}'")
                    print(f"  alt: '{alt}'")
                    print(f"  class: '{class_attr}'")
                    print(f"  可见: {is_visible}")
                    captcha_found = True
                    print()
            except Exception as e:
                print(f"  分析图片 {i+1} 时出错: {e}")
        
        if not captcha_found:
            print("  未发现明显的验证码元素")
        
        # 生成建议的选择器
        print(f"\n⚙️ 建议的选择器:")
        
        # 尝试智能识别用户名输入框
        username_selectors = [
            'input[placeholder*="用户名"]',
            'input[placeholder*="账号"]', 
            'input[placeholder*="手机"]',
            'input[placeholder*="身份证"]',
            'input[name*="user"]',
            'input[id*="user"]',
            'input[type="text"]:first-of-type',
            'input:not([type="password"]):not([type="hidden"])'
        ]
        
        for selector in username_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem and await elem.is_visible():
                    placeholder = await elem.get_attribute('placeholder') or ''
                    print(f"用户名输入框候选: '{selector}' - placeholder: '{placeholder}'")
            except:
                pass
        
        # 尝试智能识别密码输入框
        password_selectors = [
            'input[type="password"]',
            'input[placeholder*="密码"]'
        ]
        
        for selector in password_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem and await elem.is_visible():
                    placeholder = await elem.get_attribute('placeholder') or ''
                    print(f"密码输入框候选: '{selector}' - placeholder: '{placeholder}'")
            except:
                pass
        
        print(f"\n💡 手动测试提示:")
        print("1. 请手动在浏览器中尝试填写登录表单")
        print("2. 观察哪些输入框是用户名、密码、验证码")
        print("3. 记录下正确的选择器模式")
        
        input("\n按回车键关闭浏览器...")
        
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        logger.error(f"登录页面调试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_login_page())