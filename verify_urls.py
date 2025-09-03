#!/usr/bin/env python3
"""
URL验证脚本

验证配置文件中的URL是否有效
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright
from src.auto_study.config.config_manager import ConfigManager
from src.auto_study.utils.logger import logger


async def verify_urls():
    """验证配置的URL"""
    try:
        # 加载配置
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        site_config = config.get('site', {})
        base_url = site_config.get('url', '')
        login_url = site_config.get('login_url', '')
        courses_url = site_config.get('courses_url', '')
        
        print("🔍 验证配置的URL...")
        print(f"基础URL: {base_url}")
        print(f"登录URL: {login_url}")
        print(f"课程URL: {courses_url}")
        print("-" * 60)
        
        # 启动浏览器
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # 验证基础URL
        print(f"✅ 访问基础URL: {base_url}")
        await page.goto(base_url)
        await page.wait_for_load_state('networkidle')
        print(f"   标题: {await page.title()}")
        
        # 验证登录URL
        print(f"\n✅ 访问登录URL: {login_url}")
        await page.goto(login_url)
        await page.wait_for_load_state('networkidle')
        print(f"   标题: {await page.title()}")
        print(f"   实际URL: {page.url}")
        
        # 检查是否有登录表单
        login_forms = await page.query_selector_all('form')
        username_inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[name*="user"], input[id*="user"]')
        password_inputs = await page.query_selector_all('input[type="password"]')
        
        print(f"   找到表单: {len(login_forms)} 个")
        print(f"   用户名输入框: {len(username_inputs)} 个")
        print(f"   密码输入框: {len(password_inputs)} 个")
        
        if username_inputs and password_inputs:
            print("   ✅ 检测到登录表单元素")
        else:
            print("   ⚠️  未检测到明显的登录表单元素")
        
        # 验证课程URL
        print(f"\n✅ 访问课程URL: {courses_url}")
        await page.goto(courses_url)
        await page.wait_for_load_state('networkidle')
        print(f"   标题: {await page.title()}")
        print(f"   实际URL: {page.url}")
        
        # 检查课程相关元素
        course_elements = await page.query_selector_all('a[href*="course"], div[class*="course"], .course')
        print(f"   找到课程相关元素: {len(course_elements)} 个")
        
        if course_elements:
            print("   ✅ 检测到课程相关元素")
            # 显示前几个课程链接
            for i, element in enumerate(course_elements[:3]):
                text = await element.text_content()
                if text and text.strip():
                    print(f"   课程 {i+1}: {text.strip()[:50]}")
        else:
            print("   ⚠️  未检测到明显的课程元素")
        
        print(f"\n🎉 URL验证完成!")
        input("\n按回车键关闭浏览器...")
        
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        logger.error(f"URL验证失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(verify_urls())