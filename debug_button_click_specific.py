#!/usr/bin/env python
"""
专门调试"开始学习"按钮点击问题

重点关注：
1. 按钮确实被找到了
2. 但按钮是否真的被点击了  
3. 点击后按钮状态是否发生变化
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.learning_automator import VideoController
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def debug_button_click_specific():
    """专门调试按钮点击问题"""
    logger.info("=" * 80)
    logger.info("🔍 专门调试\"开始学习\"按钮点击问题")
    logger.info("📋 重点观察按钮是否真的被点击及点击后的状态变化")
    logger.info("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            
            # 登录
            logger.info("\n🔐 步骤 1: 自动登录...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败")
                return
            
            # 进入课程列表
            logger.info("\n📚 步骤 2: 进入课程列表...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 获取初始页面数
            initial_page_count = len(context.pages)
            
            # 点击继续学习按钮
            logger.info("\n🎯 步骤 3: 点击继续学习按钮...")
            video_controller = VideoController(page)
            new_tab_opened = await video_controller._click_continue_learning_for_new_tab()
            
            if not new_tab_opened:
                logger.error("❌ 未能打开新tab")
                return
            
            # 切换到新的视频页面
            video_page = await video_controller._wait_for_new_tab(context, initial_page_count)
            if not video_page:
                logger.error("❌ 未能获取视频页面")
                return
            
            logger.info(f"✅ 成功切换到视频页面: {video_page.url}")
            
            # 专门调试iframe内的按钮状态
            logger.info("\n🔍 步骤 4: 详细调试iframe内按钮状态...")
            await detailed_button_debug(video_page)
            
            # 保持页面打开以便观察
            logger.info("\n👁️ 保持浏览器打开120秒以便观察...")
            await asyncio.sleep(120)
            
        finally:
            await browser.close()

async def detailed_button_debug(video_page):
    """详细调试按钮状态"""
    try:
        logger.info("🔍 第一步：获取iframe中按钮的初始状态...")
        
        # 获取初始状态
        initial_state = await video_page.evaluate("""
            () => {
                const result = { buttons: [], error: null };
                
                try {
                    const iframes = document.querySelectorAll('iframe');
                    if (iframes.length === 0) {
                        result.error = '未找到iframe';
                        return result;
                    }
                    
                    const iframe = iframes[0];
                    if (!iframe.src || !iframe.src.includes('scorm_play')) {
                        result.error = '未找到视频iframe';
                        return result;
                    }
                    
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    
                    // 查找各种类型的按钮
                    const userChoiseButtons = iframeDoc.querySelectorAll('.user_choise');
                    const continueButtons = iframeDoc.querySelectorAll('.continue');
                    const pointerDivs = iframeDoc.querySelectorAll('div[style*="cursor: pointer"]');
                    
                    userChoiseButtons.forEach((btn, i) => {
                        const rect = btn.getBoundingClientRect();
                        const style = iframeDoc.defaultView.getComputedStyle(btn);
                        result.buttons.push({
                            type: 'user_choise',
                            index: i,
                            text: btn.textContent?.trim() || '',
                            visible: rect.width > 0 && rect.height > 0,
                            className: btn.className,
                            cursor: style.cursor,
                            display: style.display,
                            opacity: style.opacity,
                            rect: { width: rect.width, height: rect.height, x: rect.x, y: rect.y }
                        });
                    });
                    
                    continueButtons.forEach((btn, i) => {
                        const rect = btn.getBoundingClientRect();
                        const style = iframeDoc.defaultView.getComputedStyle(btn);
                        result.buttons.push({
                            type: 'continue',
                            index: i,
                            text: btn.textContent?.trim() || '',
                            visible: rect.width > 0 && rect.height > 0,
                            className: btn.className,
                            cursor: style.cursor,
                            display: style.display,
                            opacity: style.opacity,
                            rect: { width: rect.width, height: rect.height, x: rect.x, y: rect.y }
                        });
                    });
                    
                } catch (e) {
                    result.error = e.toString();
                }
                
                return result;
            }
        """)
        
        if initial_state['error']:
            logger.error(f"❌ 获取初始状态失败: {initial_state['error']}")
            return
        
        logger.info(f"📊 找到 {len(initial_state['buttons'])} 个相关按钮:")
        for btn in initial_state['buttons']:
            logger.info(f"  🔘 {btn['type']}[{btn['index']}]: '{btn['text']}'")
            logger.info(f"     可见: {btn['visible']}, 类名: {btn['className']}")
            logger.info(f"     样式: cursor={btn['cursor']}, display={btn['display']}, opacity={btn['opacity']}")
            logger.info(f"     位置: {btn['rect']}")
        
        # 现在尝试手动点击这些按钮并观察变化
        logger.info("\n🖱️ 第二步：尝试手动点击按钮并观察状态变化...")
        
        click_result = await video_page.evaluate("""
            () => {
                const result = { clicked: [], errors: [], before: [], after: [] };
                
                try {
                    const iframe = document.querySelector('iframe[src*="scorm_play"]');
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    
                    // 记录点击前状态
                    const userChoiseButtons = iframeDoc.querySelectorAll('.user_choise');
                    userChoiseButtons.forEach((btn, i) => {
                        result.before.push({
                            type: 'user_choise',
                            index: i,
                            text: btn.textContent?.trim(),
                            classList: Array.from(btn.classList),
                            style: btn.getAttribute('style') || '',
                            innerHTML: btn.innerHTML
                        });
                    });
                    
                    // 尝试点击user_choise按钮
                    userChoiseButtons.forEach((btn, i) => {
                        try {
                            console.log(`尝试点击user_choise按钮[${i}]: ${btn.textContent?.trim()}`);
                            
                            // 多种点击方式
                            btn.click(); // 标准点击
                            
                            // 如果有onclick属性也尝试执行
                            if (btn.onclick) {
                                btn.onclick();
                            }
                            
                            // 触发各种事件
                            btn.dispatchEvent(new MouseEvent('mousedown'));
                            btn.dispatchEvent(new MouseEvent('mouseup'));
                            btn.dispatchEvent(new MouseEvent('click'));
                            
                            result.clicked.push({
                                type: 'user_choise',
                                index: i,
                                text: btn.textContent?.trim(),
                                success: true
                            });
                            
                        } catch (e) {
                            result.errors.push({
                                type: 'user_choise',
                                index: i,
                                error: e.toString()
                            });
                        }
                    });
                    
                    // 等待一会儿再检查点击后状态
                    setTimeout(() => {
                        userChoiseButtons.forEach((btn, i) => {
                            result.after.push({
                                type: 'user_choise',
                                index: i,
                                text: btn.textContent?.trim(),
                                classList: Array.from(btn.classList),
                                style: btn.getAttribute('style') || '',
                                innerHTML: btn.innerHTML
                            });
                        });
                    }, 500);
                    
                } catch (e) {
                    result.errors.push({ general: e.toString() });
                }
                
                return result;
            }
        """)
        
        logger.info(f"🖱️ 点击结果:")
        logger.info(f"  成功点击: {len(click_result['clicked'])}个")
        for click in click_result['clicked']:
            logger.info(f"    ✅ {click['type']}[{click['index']}]: '{click['text']}'")
        
        logger.info(f"  点击错误: {len(click_result['errors'])}个")
        for error in click_result['errors']:
            logger.info(f"    ❌ {error.get('type', 'general')}: {error.get('error', error)}")
        
        # 等待一会儿查看状态变化
        await asyncio.sleep(2)
        
        # 获取点击后的状态
        after_state = await video_page.evaluate("""
            () => {
                const result = { buttons: [], videos: [], page_changed: false };
                
                try {
                    const iframe = document.querySelector('iframe[src*="scorm_play"]');
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    
                    // 检查按钮状态
                    const userChoiseButtons = iframeDoc.querySelectorAll('.user_choise');
                    userChoiseButtons.forEach((btn, i) => {
                        const rect = btn.getBoundingClientRect();
                        const style = iframeDoc.defaultView.getComputedStyle(btn);
                        result.buttons.push({
                            type: 'user_choise',
                            index: i,
                            text: btn.textContent?.trim() || '',
                            visible: rect.width > 0 && rect.height > 0,
                            className: btn.className,
                            cursor: style.cursor,
                            display: style.display,
                            opacity: style.opacity
                        });
                    });
                    
                    // 检查视频状态
                    const videos = iframeDoc.querySelectorAll('video');
                    videos.forEach((video, i) => {
                        result.videos.push({
                            index: i,
                            paused: video.paused,
                            currentTime: video.currentTime,
                            duration: video.duration || 0,
                            readyState: video.readyState
                        });
                    });
                    
                    // 检查页面是否有明显变化（比如有新元素出现）
                    const allElements = iframeDoc.querySelectorAll('*');
                    result.page_changed = allElements.length !== undefined; // 简单检查
                    
                } catch (e) {
                    result.error = e.toString();
                }
                
                return result;
            }
        """)
        
        logger.info(f"\n📊 点击后状态:")
        logger.info(f"  按钮数量: {len(after_state['buttons'])}")
        for btn in after_state['buttons']:
            logger.info(f"    🔘 {btn['type']}[{btn['index']}]: '{btn['text']}' (可见: {btn['visible']})")
        
        logger.info(f"  视频数量: {len(after_state['videos'])}")
        for video in after_state['videos']:
            status = "播放中" if not video['paused'] else "暂停"
            logger.info(f"    🎬 视频[{video['index']}]: {status} ({video['currentTime']:.1f}s / {video['duration']:.1f}s)")
        
        # 对比前后状态变化
        logger.info("\n🔍 第三步：对比按钮状态变化...")
        if len(initial_state['buttons']) == len(after_state['buttons']):
            for i, (before, after) in enumerate(zip(initial_state['buttons'], after_state['buttons'])):
                if before != after:
                    logger.info(f"  📝 按钮[{i}]发生变化:")
                    logger.info(f"    变化前: 可见={before['visible']}, 样式={before['cursor']}")
                    logger.info(f"    变化后: 可见={after['visible']}, 样式={after['cursor']}")
                else:
                    logger.info(f"  📝 按钮[{i}]无变化: '{before['text']}'")
        
        logger.info("✅ 详细按钮调试完成")
        
    except Exception as e:
        logger.error(f"❌ 详细按钮调试异常: {e}")

if __name__ == "__main__":
    asyncio.run(debug_button_click_specific())