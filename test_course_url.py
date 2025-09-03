#!/usr/bin/env python3
"""
测试新的课程URL
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
from auto_study.automation.course_manager import CourseManager
from auto_study.config.config_manager import ConfigManager

async def test_course_url():
    """测试新的课程URL"""
    try:
        print("🔍 测试新的课程URL...")
        
        # 获取环境变量
        username = os.getenv('AUTO_STUDY_USERNAME')
        password = os.getenv('AUTO_STUDY_PASSWORD')
        
        if not username or not password:
            print("❌ 未设置用户名和密码环境变量")
            return False
        
        # 启动浏览器
        print("🚀 启动浏览器...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 登录
        print("🔐 执行登录...")
        auto_login = AutoLogin(page)
        login_success = await auto_login.login(username, password)
        
        if not login_success:
            print("❌ 登录失败")
            await browser.close()
            await playwright.stop()
            return False
            
        print("✅ 登录成功")
        
        # 创建课程管理器
        config_manager = ConfigManager()
        course_manager = CourseManager(config_manager)
        
        # 获取配置中的课程URL
        config = config_manager.get_config()
        courses_url = config.get('site', {}).get('courses_url')
        print(f"📚 课程页面URL: {courses_url}")
        
        # 访问课程页面
        print("📖 访问课程页面...")
        await page.goto(courses_url)
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(5)  # 等待页面完全加载
        
        print(f"✅ 当前页面URL: {page.url}")
        
        # 尝试提取课程信息
        print("🔍 查找课程元素...")
        
        # 检查页面内容
        page_content = await page.content()
        if "课程" in page_content or "course" in page_content.lower():
            print("✅ 页面包含课程相关内容")
        else:
            print("⚠️  页面可能不包含课程内容")
        
        # 尝试多种课程选择器
        course_selectors = [
            '.course-list .course-item',
            '.courses .course-card', 
            '.my-courses .course',
            '[data-course-id]',
            '.course-item',
            '.course-card',
            '.study-item',
            '.lesson-item',
            '[class*="course"]',
            '[class*="lesson"]',
            'li',
            '.item'
        ]
        
        found_elements = []
        for selector in course_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    found_elements.append((selector, count))
                    print(f"  找到 {count} 个元素: {selector}")
            except Exception as e:
                pass
        
        if found_elements:
            print(f"✅ 找到课程相关元素: {len(found_elements)} 种选择器")
            
            # 尝试提取第一个元素的详细信息
            best_selector, best_count = found_elements[0]
            print(f"\n📋 分析最佳选择器: {best_selector} ({best_count} 个元素)")
            
            try:
                first_element = page.locator(best_selector).first
                if await first_element.count() > 0:
                    text_content = await first_element.text_content()
                    print(f"  元素内容: {text_content[:100]}...")
                    
                    # 查找链接
                    links = first_element.locator('a')
                    link_count = await links.count()
                    if link_count > 0:
                        first_link = links.first
                        href = await first_link.get_attribute('href')
                        link_text = await first_link.text_content()
                        print(f"  链接: {link_text} -> {href}")
                        
            except Exception as e:
                print(f"  元素分析失败: {e}")
        else:
            print("❌ 未找到课程相关元素")
            print("📄 页面标题:", await page.title())
            
            # 保存页面截图用于调试
            await page.screenshot(path="course_page_debug.png")
            print("📸 页面截图已保存为: course_page_debug.png")
        
        # 等待用户查看
        await asyncio.sleep(10)
        
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
        return len(found_elements) > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("=" * 60)
    print("🧪 测试新课程URL: /study_center/tool_box/required")
    print("=" * 60)
    
    success = await test_course_url()
    
    if success:
        print("\n🎉 课程页面测试通过!")
        print("页面包含可识别的课程元素")
    else:
        print("\n⚠️  课程页面需要进一步调试")
        print("请检查页面结构和选择器")

if __name__ == "__main__":
    asyncio.run(main())