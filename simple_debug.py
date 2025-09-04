#!/usr/bin/env python3
"""
简化的页面调试脚本
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from playwright.async_api import async_playwright
from auto_study.automation.auto_login import AutoLogin

async def simple_debug():
    try:
        # 加载环境变量
        from dotenv import load_dotenv
        load_dotenv()
        
        username = os.getenv('AUTO_STUDY_USERNAME') or os.getenv('USERNAME')
        password = os.getenv('AUTO_STUDY_PASSWORD') or os.getenv('PASSWORD')
        
        if not username or not password:
            print(f"缺少用户凭据: username={username}, password={'已设置' if password else '未设置'}")
            return
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 登录
        auto_login = AutoLogin(page)
        success = await auto_login.login(username, password)
        print(f"登录结果: {success}")
        
        if success:
            # 访问课程页面
            courses_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275"
            print(f"访问: {courses_url}")
            await page.goto(courses_url)
            await asyncio.sleep(5)
            
            print(f"当前URL: {page.url}")
            
            # 检查简单的选择器
            simple_selectors = ['li', 'ul', 'div', '[class*="list"]', '[class*="course"]']
            for selector in simple_selectors:
                try:
                    count = await page.locator(selector).count()
                    print(f"{selector}: {count}")
                except:
                    print(f"{selector}: 错误")
            
            # 查看页面标题
            title = await page.title()
            print(f"页面标题: {title}")
            
            # 等待5秒继续分析
            print("等待5秒后继续分析...")
            await asyncio.sleep(5)
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_debug())