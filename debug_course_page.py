#!/usr/bin/env python3
"""
课程页面调试脚本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 应用PIL兼容性补丁
from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from playwright.async_api import async_playwright
from auto_study.automation.auto_login import AutoLogin

async def debug_course_page():
    """调试课程页面结构"""
    try:
        print("🔍 调试课程页面结构...")
        
        # 获取环境变量
        username = os.getenv('AUTO_STUDY_USERNAME')
        password = os.getenv('AUTO_STUDY_PASSWORD')
        
        if not username or not password:
            print("❌ 未设置用户名和密码环境变量")
            return
        
        # 启动浏览器
        print("🚀 启动浏览器...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 登录
        print("🔐 执行登录...")
        auto_login = AutoLogin(page)
        success = await auto_login.login(username, password)
        
        if not success:
            print("❌ 登录失败")
            await browser.close()
            await playwright.stop()
            return
            
        print("✅ 登录成功")
        
        # 访问课程页面
        courses_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275"
        print(f"📖 访问课程页面: {courses_url}")
        await page.goto(courses_url)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(10)  # 等待页面完全加载
        
        print(f"✅ 当前页面URL: {page.url}")
        
        # 保存页面截图
        await page.screenshot(path="course_page_debug.png")
        print("📸 页面截图已保存为: course_page_debug.png")
        
        # 检查各种选择器
        print("\n🔍 检查页面选择器:")
        
        selectors_to_check = [
            # 课程容器选择器
            '.el-collapse-item__content',
            '.gj_top_list_box',
            '.el-collapse-item__content .gj_top_list_box',
            'ul[data-v-31d29258]',
            
            # 课程列表项选择器
            '.gj_top_list_box li',
            '.el-collapse-item__content li',
            'ul[data-v-31d29258] li',
            'li[data-v-31d29258]',
            
            # 课程信息选择器
            '.text_title',
            '.el-progress__text',
            '.text_start',
            '.btn',
            
            # 通用选择器
            'li',
            'ul',
            '[class*="course"]'
        ]
        
        for selector in selectors_to_check:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                print(f"  {selector}: {count} 个元素")
                
                if count > 0 and count < 50:  # 显示前几个元素的内容
                    first_element = elements.first
                    text = await first_element.text_content()
                    if text:
                        text_preview = text.strip()[:100]
                        print(f"    示例内容: {text_preview}...")
            except Exception as e:
                print(f"  {selector}: 错误 - {e}")
        
        # 检查页面HTML内容
        print("\n📄 检查页面HTML片段:")
        try:
            # 获取包含课程信息的HTML片段
            html_content = await page.content()
            
            # 查找关键词
            keywords = ['中国式现代化', '习近平', '课程', '学习', 'gj_top_list_box', 'text_title']
            for keyword in keywords:
                if keyword in html_content:
                    print(f"  找到关键词: {keyword}")
                    # 找到关键词周围的HTML片段
                    import re
                    pattern = f'.{{0,200}}{re.escape(keyword)}.{{0,200}}'
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    if matches:
                        for i, match in enumerate(matches[:2]):  # 只显示前2个匹配
                            print(f"    匹配 {i+1}: {match[:150]}...")
                else:
                    print(f"  未找到关键词: {keyword}")
        except Exception as e:
            print(f"检查HTML内容失败: {e}")
        
        print("\n⏳ 等待20秒用于手动检查...")
        await asyncio.sleep(20)
        
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_course_page())