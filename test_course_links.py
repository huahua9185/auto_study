#!/usr/bin/env python3
"""
测试课程链接的正确性
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from dotenv import load_dotenv
load_dotenv()

from playwright.async_api import async_playwright
from auto_study.automation.auto_login import AutoLogin

async def test_course_links():
    """测试课程链接"""
    try:
        username = os.getenv('AUTO_STUDY_USERNAME') or os.getenv('USERNAME')
        password = os.getenv('AUTO_STUDY_PASSWORD') or os.getenv('PASSWORD')
        
        if not username or not password:
            print(f"缺少用户凭据")
            return
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 登录
        auto_login = AutoLogin(page)
        success = await auto_login.login(username, password)
        print(f"登录结果: {success}")
        
        if not success:
            print("❌ 登录失败，无法测试课程链接")
            return
        
        # 访问课程页面
        courses_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275"
        print(f"访问课程页面: {courses_url}")
        await page.goto(courses_url)
        await asyncio.sleep(5)
        
        print(f"当前URL: {page.url}")
        
        # 等待Vue.js和Element UI加载
        try:
            await page.wait_for_selector('.el-collapse-item__content', timeout=10000)
            print("✅ 课程页面已加载")
        except:
            print("⚠️ 课程页面加载可能不完整")
        
        # 查找课程项
        course_selectors = [
            '.el-collapse-item__content .gj_top_list_box li',
            '.gj_top_list_box li'
        ]
        
        course_elements = None
        for selector in course_selectors:
            try:
                elements = page.locator(selector)
                count = await elements.count()
                if count > 0:
                    course_elements = elements
                    print(f"✅ 找到 {count} 个课程: {selector}")
                    break
            except:
                continue
        
        if not course_elements:
            print("❌ 未找到课程元素")
            return
        
        # 测试前3个课程的链接
        course_count = await course_elements.count()
        test_count = min(3, course_count)
        
        print(f"\n开始测试前 {test_count} 个课程的链接...")
        
        for i in range(test_count):
            element = course_elements.nth(i)
            
            # 获取课程标题
            title = "未知课程"
            try:
                title_elem = element.locator('.text_title').first
                if await title_elem.count() > 0:
                    title = await title_elem.text_content() or await title_elem.get_attribute('title') or title
                    title = title.strip()
            except:
                pass
                
            print(f"\n📖 测试课程 {i+1}: {title}")
            
            # 查找"继续学习"按钮
            learn_button_selectors = [
                '.btn:has-text("继续学习")',
                'button:has-text("继续学习")',
                '.btn:has-text("开始学习")',
                'button:has-text("开始学习")',
                '.btn',
                'button'
            ]
            
            learn_button = None
            button_found = False
            
            for btn_selector in learn_button_selectors:
                try:
                    btn_locator = element.locator(btn_selector).first
                    if await btn_locator.count() > 0 and await btn_locator.is_visible():
                        learn_button = btn_locator
                        btn_text = await btn_locator.text_content()
                        print(f"  ✅ 找到按钮: '{btn_text}' (选择器: {btn_selector})")
                        button_found = True
                        break
                except Exception as e:
                    print(f"  ⚠️ 按钮选择器失败 {btn_selector}: {e}")
                    continue
            
            if not learn_button:
                print("  ❌ 未找到学习按钮")
                continue
            
            # 检查按钮属性
            try:
                # 检查href属性
                href = await learn_button.get_attribute('href')
                if href:
                    print(f"  📎 按钮href: {href}")
                else:
                    print("  📎 按钮没有href属性")
                
                # 检查onclick属性
                onclick = await learn_button.get_attribute('onclick')
                if onclick:
                    print(f"  🖱️ 按钮onclick: {onclick}")
                else:
                    print("  🖱️ 按钮没有onclick属性")
                
                # 检查data属性
                data_attrs = ['data-url', 'data-href', 'data-link', 'data-course-id']
                for attr in data_attrs:
                    value = await learn_button.get_attribute(attr)
                    if value:
                        print(f"  📊 按钮{attr}: {value}")
                
            except Exception as e:
                print(f"  ❌ 获取按钮属性失败: {e}")
            
            # 测试点击按钮
            print("  🖱️ 测试点击学习按钮...")
            try:
                # 记录当前URL
                current_url = page.url
                print(f"  📍 点击前URL: {current_url}")
                
                # 点击按钮
                await learn_button.click()
                await asyncio.sleep(3)
                
                # 检查URL变化
                new_url = page.url
                print(f"  📍 点击后URL: {new_url}")
                
                if new_url != current_url:
                    print(f"  ✅ 成功跳转到新页面!")
                    
                    # 检查新页面是否是学习页面
                    title_after = await page.title()
                    print(f"  📑 新页面标题: {title_after}")
                    
                    # 检查是否有视频播放器
                    video_selectors = [
                        'video',
                        '.video-player',
                        '.player',
                        'iframe[src*="video"]',
                        '[class*="video"]'
                    ]
                    
                    has_video = False
                    for video_sel in video_selectors:
                        try:
                            video_count = await page.locator(video_sel).count()
                            if video_count > 0:
                                print(f"  🎥 发现视频元素: {video_sel} ({video_count} 个)")
                                has_video = True
                        except:
                            continue
                    
                    if has_video:
                        print(f"  ✅ 课程页面包含视频播放器")
                    else:
                        print(f"  ⚠️ 课程页面未发现视频播放器")
                    
                    # 保存真实的课程URL
                    print(f"  💾 真实课程URL: {new_url}")
                    
                else:
                    print(f"  ⚠️ 点击后URL未变化，可能是JavaScript处理")
                
                # 返回课程列表页面准备测试下一个
                print("  🔙 返回课程列表页面...")
                await page.goto(courses_url)
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"  ❌ 点击按钮失败: {e}")
                # 尝试返回课程页面
                try:
                    await page.goto(courses_url)
                    await asyncio.sleep(2)
                except:
                    pass
        
        print("\n📊 测试完成！")
        print("等待5秒后关闭浏览器...")
        await asyncio.sleep(5)
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_course_links())