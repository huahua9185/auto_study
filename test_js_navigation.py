#!/usr/bin/env python3
"""
分析课程按钮的JavaScript处理机制
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

async def analyze_js_navigation():
    """分析JavaScript导航机制"""
    try:
        username = os.getenv('AUTO_STUDY_USERNAME') or os.getenv('USERNAME')
        password = os.getenv('AUTO_STUDY_PASSWORD') or os.getenv('PASSWORD')
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 开启控制台日志监听
        page.on('console', lambda msg: print(f"🖥️ Console: {msg.text}"))
        page.on('response', lambda response: print(f"🌐 Response: {response.url} ({response.status})") if 'study' in response.url or 'course' in response.url else None)
        
        # 登录
        auto_login = AutoLogin(page)
        success = await auto_login.login(username, password)
        
        if not success:
            print("❌ 登录失败")
            return
        
        # 访问课程页面
        courses_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275"
        await page.goto(courses_url)
        await asyncio.sleep(5)
        
        # 等待Vue应用完全加载
        try:
            await page.wait_for_function("() => window.Vue || window.$vue || document.querySelector('[data-v-]')", timeout=10000)
            print("✅ Vue应用已检测到")
        except:
            print("⚠️ Vue应用检测超时")
        
        # 获取第一个课程按钮
        course_elements = page.locator('.el-collapse-item__content .gj_top_list_box li')
        if await course_elements.count() == 0:
            print("❌ 未找到课程元素")
            return
        
        first_course = course_elements.first
        learn_button = first_course.locator('.btn:has-text("继续学习")').first
        
        if await learn_button.count() == 0:
            print("❌ 未找到学习按钮")
            return
        
        # 获取课程标题
        title_elem = first_course.locator('.text_title').first
        title = await title_elem.text_content() if await title_elem.count() > 0 else "未知课程"
        print(f"📖 测试课程: {title}")
        
        # 分析按钮的事件监听器
        print("🔍 分析按钮事件...")
        
        # 执行JavaScript来分析按钮
        button_analysis = await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll('.btn');
                const results = [];
                
                buttons.forEach((btn, index) => {
                    if (btn.textContent.includes('继续学习')) {
                        const result = {
                            index: index,
                            text: btn.textContent.trim(),
                            tagName: btn.tagName,
                            className: btn.className,
                            id: btn.id || 'none',
                            dataset: Object.assign({}, btn.dataset),
                            attributes: {},
                            hasEventListeners: false
                        };
                        
                        // 获取所有属性
                        for (let attr of btn.attributes) {
                            result.attributes[attr.name] = attr.value;
                        }
                        
                        // 检查是否有Vue事件绑定
                        const vueKeys = Object.keys(btn).filter(key => key.startsWith('__vue'));
                        if (vueKeys.length > 0) {
                            result.hasVueBindings = true;
                            result.vueKeys = vueKeys;
                        }
                        
                        results.push(result);
                    }
                });
                
                return results;
            }
        """)
        
        print(f"🔍 找到 {len(button_analysis)} 个'继续学习'按钮")
        for i, btn_info in enumerate(button_analysis):
            print(f"\n按钮 {i+1}:")
            print(f"  文本: {btn_info['text']}")
            print(f"  标签: {btn_info['tagName']}")
            print(f"  类名: {btn_info['className']}")
            print(f"  ID: {btn_info['id']}")
            if btn_info['dataset']:
                print(f"  data属性: {btn_info['dataset']}")
            if btn_info.get('hasVueBindings'):
                print(f"  Vue绑定: {btn_info['vueKeys']}")
        
        # 监听页面变化
        print("\n🎯 监听页面导航和DOM变化...")
        
        # 设置导航监听
        navigation_promise = page.wait_for_event('framenavigated', timeout=10000)
        
        # 监听DOM变化
        await page.evaluate("""
            () => {
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                            console.log('DOM变化:', mutation.target.tagName, mutation.addedNodes.length, '个新节点');
                        }
                    });
                });
                observer.observe(document.body, { 
                    childList: true, 
                    subtree: true 
                });
                window.domObserver = observer;
            }
        """)
        
        # 监听URL变化（Vue Router）
        await page.evaluate("""
            () => {
                let lastUrl = window.location.href;
                setInterval(() => {
                    if (window.location.href !== lastUrl) {
                        console.log('URL变化:', lastUrl, ' -> ', window.location.href);
                        lastUrl = window.location.href;
                    }
                }, 100);
            }
        """)
        
        print("🖱️ 点击学习按钮...")
        current_url = page.url
        
        # 点击按钮并等待变化
        await learn_button.click()
        
        # 等待可能的导航或DOM变化
        try:
            await asyncio.sleep(5)  # 给更长时间等待
            
            new_url = page.url
            print(f"📍 URL变化: {current_url} -> {new_url}")
            
            # 检查页面内容变化
            page_title = await page.title()
            print(f"📑 页面标题: {page_title}")
            
            # 检查是否有新的DOM元素（可能是课程页面内容）
            video_elements = await page.locator('video, .video-player, iframe[src*="video"], [class*="video"]').count()
            player_elements = await page.locator('.player, [class*="player"]').count()
            study_elements = await page.locator('[class*="study"], [class*="course-content"], [class*="learning"]').count()
            
            print(f"🎥 视频相关元素: {video_elements}")
            print(f"🎮 播放器元素: {player_elements}")
            print(f"📚 学习内容元素: {study_elements}")
            
            # 检查页面的主要内容区域是否发生变化
            main_content = await page.evaluate("""
                () => {
                    const selectors = [
                        '.main-content', 
                        '.content', 
                        '.page-content',
                        '[class*="content"]',
                        'main'
                    ];
                    
                    for (let selector of selectors) {
                        const elem = document.querySelector(selector);
                        if (elem) {
                            return {
                                selector: selector,
                                innerHTML: elem.innerHTML.substring(0, 200) + '...',
                                children: elem.children.length
                            };
                        }
                    }
                    return null;
                }
            """)
            
            if main_content:
                print(f"📄 主要内容区域: {main_content['selector']} ({main_content['children']} 个子元素)")
            
        except Exception as e:
            print(f"⚠️ 等待变化时出错: {e}")
        
        print("\n等待10秒观察页面状态...")
        await asyncio.sleep(10)
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(analyze_js_navigation())