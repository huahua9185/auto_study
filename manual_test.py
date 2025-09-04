#!/usr/bin/env python3
"""
手动测试脚本 - 让用户手动登录后测试课程提取
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from playwright.async_api import async_playwright

async def manual_test():
    """手动登录后测试课程提取"""
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 访问登录页面
        login_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/rolling_news?id=notice"
        print(f"访问登录页面: {login_url}")
        await page.goto(login_url)
        await asyncio.sleep(3)
        
        # 等待用户手动登录（自动等待30秒，假设登录完成）
        print("请手动完成登录过程...")
        print("等待30秒后自动继续测试...")
        await asyncio.sleep(30)
        
        # 访问课程页面
        courses_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275"
        print(f"访问课程页面: {courses_url}")
        await page.goto(courses_url)
        await asyncio.sleep(3)
        
        print(f"当前URL: {page.url}")
        
        # 检查是否仍在认证页面
        if "requireAuth" in page.url:
            print("❌ 仍在认证页面，登录可能未成功")
            return
        else:
            print("✅ 已进入课程页面")
        
        # 等待Vue.js和Element UI加载
        print("等待Vue.js和Element UI组件加载...")
        
        try:
            await page.wait_for_function("() => window.Vue !== undefined", timeout=10000)
            print("✅ Vue.js已加载")
        except:
            print("⚠️ 未检测到Vue.js")
        
        try:
            await page.wait_for_selector('.el-collapse', timeout=10000)
            print("✅ Element UI collapse组件已加载")
        except:
            print("⚠️ 未找到collapse组件")
        
        # 检查课程相关元素
        course_selectors = [
            '.gj_top_list_box',
            '.el-collapse-item__content',
            '.el-collapse-item',
            '.text_title',
            '.el-progress__text'
        ]
        
        for selector in course_selectors:
            try:
                count = await page.locator(selector).count()
                print(f"{selector}: {count} 个元素")
                
                # 显示找到的内容
                if count > 0:
                    elements = page.locator(selector)
                    for i in range(min(3, count)):
                        try:
                            text = await elements.nth(i).text_content()
                            if text and len(text.strip()) > 0:
                                text = text.strip()[:100]
                                print(f"  [{i}]: {text}")
                        except:
                            pass
                            
            except Exception as e:
                print(f"{selector}: 错误 - {e}")
        
        # 尝试课程提取逻辑
        print("\n测试课程提取逻辑...")
        
        # 检查课程容器
        container_selectors = ['.gj_top_list_box', '.el-collapse-item__content', '.el-collapse']
        container_found = False
        
        for container_sel in container_selectors:
            try:
                if await page.locator(container_sel).count() > 0:
                    print(f"✅ 找到课程容器: {container_sel}")
                    container_found = True
                    break
            except:
                continue
        
        if not container_found:
            print("❌ 未找到课程容器")
        
        # 测试课程项选择器
        course_item_selectors = [
            '.el-collapse-item__content .gj_top_list_box li',
            '.gj_top_list_box li',
            '.el-collapse-item__content li',
            'ul[data-v-31d29258] li',
            'li[data-v-31d29258]'
        ]
        
        course_elements = None
        for selector in course_item_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    print(f"✅ 找到课程项: {selector} ({count} 个)")
                    
                    # 检查第一个元素的内容
                    first_element = elements.first
                    has_title = await first_element.locator('.text_title, [title]').count() > 0
                    has_progress = await first_element.locator('.el-progress__text, .progress').count() > 0
                    
                    if has_title or has_progress:
                        print(f"✅ 发现有效课程内容 (title: {has_title}, progress: {has_progress})")
                        course_elements = elements
                        break
                    else:
                        print(f"⚠️ 元素不包含课程内容")
            except:
                continue
        
        if course_elements:
            print(f"\n✅ 成功找到课程元素，测试提取...")
            try:
                count = await course_elements.count()
                print(f"课程总数: {count}")
                
                # 提取前3个课程的详细信息
                for i in range(min(3, count)):
                    course_element = course_elements.nth(i)
                    
                    # 提取标题
                    try:
                        title_element = course_element.locator('.text_title')
                        if await title_element.count() > 0:
                            title = await title_element.get_attribute('title') or await title_element.text_content()
                            print(f"  课程 {i+1} 标题: {title}")
                        else:
                            print(f"  课程 {i+1} 标题: 未找到")
                    except Exception as e:
                        print(f"  课程 {i+1} 标题提取失败: {e}")
                    
                    # 提取进度
                    try:
                        progress_element = course_element.locator('.el-progress__text')
                        if await progress_element.count() > 0:
                            progress_text = await progress_element.text_content()
                            print(f"  课程 {i+1} 进度: {progress_text}")
                        else:
                            print(f"  课程 {i+1} 进度: 未找到")
                    except Exception as e:
                        print(f"  课程 {i+1} 进度提取失败: {e}")
                        
            except Exception as e:
                print(f"❌ 课程信息提取失败: {e}")
        else:
            print("❌ 未找到有效的课程元素")
        
        print("\n测试完成，等待5秒后关闭浏览器...")
        await asyncio.sleep(5)
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(manual_test())