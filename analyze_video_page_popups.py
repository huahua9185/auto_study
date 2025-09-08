#!/usr/bin/env python
"""
专门分析视频页面中真正的"继续学习"弹窗结构

跳过隐藏的登录弹窗，专注于视频页面的实际弹窗
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json

async def analyze_video_page_popups():
    """分析视频页面中的真实弹窗结构"""
    logger.info("=" * 60)
    logger.info("分析视频页面中的真实弹窗结构")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 登录到系统
            logger.info("步骤 1: 登录到系统...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败")
                return
            
            logger.info("✅ 登录成功")
            
            # 导航到课程页面
            logger.info("步骤 2: 导航到课程页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 点击"继续学习"按钮
            logger.info("步骤 3: 点击继续学习按钮...")
            course_clicked = await page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('div.btn, button, .user_choise');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习')) {
                            btn.click();
                            return {
                                clicked: true,
                                buttonInfo: {
                                    text: text.trim(),
                                    tag: btn.tagName,
                                    class: btn.className
                                }
                            };
                        }
                    }
                    return { clicked: false };
                }
            """)
            
            if not course_clicked['clicked']:
                logger.error("❌ 未找到继续学习按钮")
                return
            
            logger.info(f"✅ 成功点击按钮: {course_clicked['buttonInfo']}")
            
            # 等待页面变化并跳过隐藏的登录弹窗
            logger.info("步骤 4: 等待页面加载，跳过隐藏元素...")
            await asyncio.sleep(5)  # 给页面足够时间加载
            
            # 分析当前页面状态
            logger.info("步骤 5: 分析当前页面状态...")
            logger.info("=" * 40)
            
            page_analysis = await page.evaluate("""
                () => {
                    const result = {
                        currentUrl: window.location.href,
                        title: document.title,
                        visiblePopups: [],
                        visibleButtons: [],
                        videos: [],
                        iframes: [],
                        playButtons: []
                    };
                    
                    // 查找真正可见的弹窗（不是隐藏的DOM元素）
                    const popupSelectors = [
                        '.continue', '.user_choise', '.el-message-box__wrapper',
                        '.modal:not(.fade)', '.popup', '.dialog',
                        '[role="dialog"][style*="display: block"]'
                    ];
                    
                    popupSelectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            
                            // 只统计真正可见的元素
                            if (rect.width > 0 && rect.height > 0 && 
                                style.display !== 'none' && 
                                style.visibility !== 'hidden' && 
                                style.opacity !== '0') {
                                
                                const buttons = el.querySelectorAll('button, div[onclick], .user_choise, .btn');
                                const buttonInfo = [];
                                buttons.forEach(btn => {
                                    const btnRect = btn.getBoundingClientRect();
                                    if (btnRect.width > 0 && btnRect.height > 0) {
                                        buttonInfo.push({
                                            text: btn.textContent?.trim(),
                                            class: btn.className,
                                            tag: btn.tagName,
                                            clickable: true
                                        });
                                    }
                                });
                                
                                result.visiblePopups.push({
                                    selector: selector,
                                    class: el.className,
                                    text: el.textContent?.substring(0, 200),
                                    buttons: buttonInfo,
                                    rect: {
                                        width: rect.width,
                                        height: rect.height,
                                        x: rect.x,
                                        y: rect.y
                                    }
                                });
                            }
                        });
                    });
                    
                    // 查找页面上所有可见的"继续学习"相关按钮
                    const allElements = document.querySelectorAll('*');
                    allElements.forEach(el => {
                        const text = el.textContent || '';
                        if ((text.includes('继续学习') || text.includes('开始学习') || text.includes('播放')) && text.length < 50) {
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            
                            if (rect.width > 0 && rect.height > 0 && 
                                style.display !== 'none' && 
                                style.visibility !== 'hidden') {
                                
                                result.visibleButtons.push({
                                    text: text.trim(),
                                    tag: el.tagName,
                                    class: el.className,
                                    id: el.id,
                                    rect: {
                                        width: rect.width,
                                        height: rect.height,
                                        x: rect.x,
                                        y: rect.y
                                    }
                                });
                            }
                        }
                    });
                    
                    // 查找视频元素
                    const videos = document.querySelectorAll('video');
                    videos.forEach(video => {
                        const rect = video.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.videos.push({
                                src: video.src || video.currentSrc,
                                width: rect.width,
                                height: rect.height,
                                paused: video.paused,
                                readyState: video.readyState
                            });
                        }
                    });
                    
                    // 查找iframe
                    const iframes = document.querySelectorAll('iframe');
                    iframes.forEach(iframe => {
                        const rect = iframe.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            result.iframes.push({
                                src: iframe.src,
                                width: rect.width,
                                height: rect.height
                            });
                        }
                    });
                    
                    // 查找播放相关按钮
                    const playSelectors = [
                        'button[class*="play"]', '.play-btn', '[title*="播放"]',
                        '[class*="start"]', '.btn-play'
                    ];
                    
                    playSelectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                result.playButtons.push({
                                    selector: selector,
                                    text: el.textContent?.trim(),
                                    class: el.className
                                });
                            }
                        });
                    });
                    
                    return result;
                }
            """)
            
            logger.info(f"当前URL: {page_analysis['currentUrl']}")
            logger.info(f"页面标题: {page_analysis['title']}")
            
            logger.info(f"\\n找到 {len(page_analysis['visiblePopups'])} 个真正可见的弹窗:")
            for i, popup in enumerate(page_analysis['visiblePopups']):
                logger.info(f"  弹窗 {i+1}: {popup['selector']}")
                logger.info(f"    类名: {popup['class']}")
                logger.info(f"    大小: {popup['rect']['width']}x{popup['rect']['height']}")
                logger.info(f"    按钮数量: {len(popup['buttons'])}")
                for j, btn in enumerate(popup['buttons']):
                    logger.info(f"      按钮 {j+1}: '{btn['text']}' ({btn['tag']}.{btn['class']})")
                logger.info(f"    文本预览: {popup['text'][:100]}...")
            
            logger.info(f"\\n找到 {len(page_analysis['visibleButtons'])} 个可见的学习/播放按钮:")
            for i, btn in enumerate(page_analysis['visibleButtons'][:10]):  # 只显示前10个
                logger.info(f"  按钮 {i+1}: '{btn['text']}' ({btn['tag']}.{btn['class']})")
            
            logger.info(f"\\n视频元素: {len(page_analysis['videos'])} 个")
            logger.info(f"iframe元素: {len(page_analysis['iframes'])} 个") 
            logger.info(f"播放按钮: {len(page_analysis['playButtons'])} 个")
            
            # 如果找到可见的"继续学习"按钮，尝试点击
            if page_analysis['visibleButtons']:
                logger.info("\\n步骤 6: 尝试点击可见的学习按钮...")
                for btn in page_analysis['visibleButtons']:
                    if '继续学习' in btn['text'] or '开始学习' in btn['text']:
                        logger.info(f"尝试点击: {btn['text']}")
                        
                        clicked = await page.evaluate(f"""
                            () => {{
                                const elements = document.querySelectorAll('{btn['tag'].lower()}');
                                for (let el of elements) {{
                                    if (el.textContent && el.textContent.includes('{btn['text'][:10]}')) {{
                                        el.click();
                                        return true;
                                    }}
                                }}
                                return false;
                            }}
                        """)
                        
                        if clicked:
                            logger.info(f"✅ 成功点击按钮: {btn['text']}")
                            await asyncio.sleep(3)
                            break
            
            # 保持浏览器打开以便手动探索
            logger.info("\\n保持浏览器打开30秒以便手动分析...")
            logger.info("请手动点击和探索真正的弹窗元素")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()
    
    logger.info("\\n" + "=" * 60)
    logger.info("视频页面弹窗结构分析完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(analyze_video_page_popups())