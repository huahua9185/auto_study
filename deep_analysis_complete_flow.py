#!/usr/bin/env python
"""
完全重新分析视频学习的完整流程

从头开始，不做任何假设，观察整个用户学习流程
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json

async def deep_analysis_complete_flow():
    """完全重新分析视频学习流程"""
    logger.info("=" * 80)
    logger.info("🔍 完全重新分析视频学习的完整流程")
    logger.info("📋 目标：理解从登录到视频播放的每一个步骤")
    logger.info("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # ===== 步骤 1: 登录 =====
            logger.info("\\n🔐 步骤 1: 登录到系统")
            logger.info("-" * 50)
            
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败，无法继续分析")
                return
            
            logger.info("✅ 登录成功")
            
            # ===== 步骤 2: 分析课程列表页面 =====
            logger.info("\\n📚 步骤 2: 分析课程列表页面")
            logger.info("-" * 50)
            
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 详细分析课程列表页面
            course_page_analysis = await page.evaluate("""
                () => {
                    const analysis = {
                        url: window.location.href,
                        title: document.title,
                        courseItems: [],
                        allButtons: [],
                        allLinks: []
                    };
                    
                    // 查找所有可能的课程项
                    const possibleCourseSelectors = [
                        '.el-collapse-item',
                        '.course-item', 
                        'li',
                        '.gj_top_list_box li',
                        '[class*="course"]'
                    ];
                    
                    possibleCourseSelectors.forEach(selector => {
                        const items = document.querySelectorAll(selector);
                        items.forEach((item, index) => {
                            const text = item.textContent || '';
                            if (text.length > 10 && text.length < 500) { // 过滤掉太短或太长的文本
                                const buttons = item.querySelectorAll('button, .btn, div[onclick]');
                                const links = item.querySelectorAll('a');
                                
                                analysis.courseItems.push({
                                    selector: selector,
                                    index: index,
                                    title: text.substring(0, 100),
                                    buttonCount: buttons.length,
                                    linkCount: links.length,
                                    buttons: Array.from(buttons).map(btn => ({
                                        text: btn.textContent?.trim(),
                                        class: btn.className,
                                        tag: btn.tagName
                                    })),
                                    links: Array.from(links).map(link => ({
                                        text: link.textContent?.trim(),
                                        href: link.href,
                                        class: link.className
                                    }))
                                });
                            }
                        });
                    });
                    
                    // 查找所有按钮
                    const allButtons = document.querySelectorAll('button, .btn, div[onclick]');
                    allButtons.forEach((btn, index) => {
                        const rect = btn.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            analysis.allButtons.push({
                                index: index,
                                text: btn.textContent?.trim(),
                                class: btn.className,
                                tag: btn.tagName,
                                onclick: btn.getAttribute('onclick'),
                                rect: {
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height
                                }
                            });
                        }
                    });
                    
                    // 查找所有链接
                    const allLinks = document.querySelectorAll('a[href]');
                    allLinks.forEach((link, index) => {
                        const text = link.textContent?.trim();
                        if (text && (text.includes('学习') || text.includes('课程') || text.includes('播放'))) {
                            analysis.allLinks.push({
                                index: index,
                                text: text,
                                href: link.href,
                                class: link.className
                            });
                        }
                    });
                    
                    return analysis;
                }
            """)
            
            logger.info(f"📍 当前页面: {course_page_analysis['url']}")
            logger.info(f"📄 页面标题: {course_page_analysis['title']}")
            logger.info(f"📚 发现 {len(course_page_analysis['courseItems'])} 个课程项")
            logger.info(f"🔘 发现 {len(course_page_analysis['allButtons'])} 个可见按钮")
            logger.info(f"🔗 发现 {len(course_page_analysis['allLinks'])} 个学习相关链接")
            
            # 显示前几个课程项的详细信息
            logger.info("\\n📋 前5个课程项详情:")
            for i, course in enumerate(course_page_analysis['courseItems'][:5]):
                logger.info(f"  {i+1}. {course['title'][:50]}...")
                logger.info(f"     按钮数: {course['buttonCount']}, 链接数: {course['linkCount']}")
                if course['buttons']:
                    for j, btn in enumerate(course['buttons'][:2]):
                        logger.info(f"       按钮{j+1}: '{btn['text']}' ({btn['tag']}.{btn['class']})")
            
            # 显示学习相关的按钮
            logger.info("\\n🎯 学习相关按钮:")
            learning_buttons = [btn for btn in course_page_analysis['allButtons'] 
                             if btn['text'] and ('学习' in btn['text'] or '播放' in btn['text'])]
            
            for i, btn in enumerate(learning_buttons[:10]):
                logger.info(f"  {i+1}. '{btn['text']}' ({btn['tag']}.{btn['class']}) at ({btn['rect']['x']:.0f}, {btn['rect']['y']:.0f})")
            
            # ===== 步骤 3: 手动引导用户点击 =====
            logger.info("\\n👆 步骤 3: 用户引导")
            logger.info("-" * 50)
            logger.info("🔄 现在进入手动引导模式")
            logger.info("📝 请按以下步骤操作:")
            logger.info("   1. 在浏览器中手动点击任意一个'继续学习'按钮")
            logger.info("   2. 观察页面的变化")
            logger.info("   3. 如果出现弹窗，不要关闭")
            logger.info("   4. 等待30秒后，脚本将自动分析结果")
            
            logger.info("\\n⏰ 等待30秒供手动操作...")
            
            # 监控页面变化
            for i in range(30):
                await asyncio.sleep(1)
                if i % 5 == 0:
                    current_url = page.url
                    logger.info(f"⏱️  {30-i}秒剩余，当前URL: {current_url}")
            
            # ===== 步骤 4: 分析操作后的页面状态 =====
            logger.info("\\n📊 步骤 4: 分析操作后的页面状态")
            logger.info("-" * 50)
            
            final_analysis = await page.evaluate("""
                () => {
                    const analysis = {
                        url: window.location.href,
                        title: document.title,
                        popups: [],
                        videos: [],
                        iframes: [],
                        specialDivs: [],
                        xpathTarget: null
                    };
                    
                    // 查找所有可见的弹窗类元素
                    const popupSelectors = [
                        '.el-dialog', '.modal', '.popup', '[role="dialog"]',
                        'div[style*="z-index"]', '.overlay', '.mask'
                    ];
                    
                    popupSelectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const rect = el.getBoundingClientRect();
                            const style = window.getComputedStyle(el);
                            
                            if (rect.width > 0 && rect.height > 0 && 
                                style.display !== 'none' && 
                                style.visibility !== 'hidden') {
                                
                                analysis.popups.push({
                                    selector: selector,
                                    class: el.className,
                                    text: el.textContent?.substring(0, 200),
                                    rect: {
                                        x: rect.x,
                                        y: rect.y,
                                        width: rect.width,
                                        height: rect.height
                                    },
                                    zIndex: style.zIndex
                                });
                            }
                        });
                    });
                    
                    // 查找视频元素
                    const videos = document.querySelectorAll('video');
                    videos.forEach((video, index) => {
                        const rect = video.getBoundingClientRect();
                        analysis.videos.push({
                            index: index,
                            src: video.src || video.currentSrc,
                            visible: rect.width > 0 && rect.height > 0,
                            paused: video.paused,
                            duration: video.duration,
                            currentTime: video.currentTime
                        });
                    });
                    
                    // 查找iframe
                    const iframes = document.querySelectorAll('iframe');
                    iframes.forEach((iframe, index) => {
                        const rect = iframe.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            analysis.iframes.push({
                                index: index,
                                src: iframe.src,
                                width: rect.width,
                                height: rect.height
                            });
                        }
                    });
                    
                    // 特别查找包含"继续学习"的div
                    const allDivs = document.querySelectorAll('div');
                    allDivs.forEach(div => {
                        const text = div.textContent || '';
                        if ((text.includes('继续学习') || text.includes('开始学习')) && 
                            text.length < 100) {
                            
                            const rect = div.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                analysis.specialDivs.push({
                                    text: text.trim(),
                                    class: div.className,
                                    rect: {
                                        x: rect.x,
                                        y: rect.y,
                                        width: rect.width,
                                        height: rect.height
                                    }
                                });
                            }
                        }
                    });
                    
                    // 检查特定的xpath
                    const xpath = '/html/body/div/div[3]/div[2]';
                    const xpathResult = document.evaluate(
                        xpath, document, null, 
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    
                    const xpathElement = xpathResult.singleNodeValue;
                    if (xpathElement) {
                        const rect = xpathElement.getBoundingClientRect();
                        analysis.xpathTarget = {
                            exists: true,
                            visible: rect.width > 0 && rect.height > 0,
                            text: xpathElement.textContent?.substring(0, 200),
                            class: xpathElement.className,
                            tag: xpathElement.tagName,
                            rect: {
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            }
                        };
                    } else {
                        analysis.xpathTarget = { exists: false };
                    }
                    
                    return analysis;
                }
            """)
            
            logger.info(f"\\n📍 最终页面: {final_analysis['url']}")
            logger.info(f"📄 最终标题: {final_analysis['title']}")
            
            logger.info(f"\\n🪟 发现 {len(final_analysis['popups'])} 个弹窗:")
            for i, popup in enumerate(final_analysis['popups']):
                logger.info(f"  {i+1}. {popup['selector']} - {popup['class']}")
                logger.info(f"     大小: {popup['rect']['width']:.0f}x{popup['rect']['height']:.0f}")
                logger.info(f"     文本: '{popup['text'][:50]}...'")
            
            logger.info(f"\\n🎬 发现 {len(final_analysis['videos'])} 个视频:")
            for i, video in enumerate(final_analysis['videos']):
                logger.info(f"  {i+1}. 可见: {video['visible']}, 暂停: {video['paused']}")
                logger.info(f"     时长: {video['duration']}, 当前: {video['currentTime']}")
                logger.info(f"     源: {video['src'][:50]}...")
            
            logger.info(f"\\n🖼️  发现 {len(final_analysis['iframes'])} 个iframe:")
            for i, iframe in enumerate(final_analysis['iframes']):
                logger.info(f"  {i+1}. {iframe['width']}x{iframe['height']}")
                logger.info(f"     源: {iframe['src'][:50]}...")
            
            logger.info(f"\\n🎯 发现 {len(final_analysis['specialDivs'])} 个特殊div:")
            for i, div in enumerate(final_analysis['specialDivs']):
                logger.info(f"  {i+1}. '{div['text']}'")
                logger.info(f"     类: {div['class']}")
                logger.info(f"     位置: ({div['rect']['x']:.0f}, {div['rect']['y']:.0f})")
            
            logger.info(f"\\n🎯 目标xpath分析:")
            if final_analysis['xpathTarget']['exists']:
                xpath_info = final_analysis['xpathTarget']
                logger.info(f"  ✅ xpath存在: {xpath_info['tag']}.{xpath_info['class']}")
                logger.info(f"  👁️  可见: {xpath_info['visible']}")
                logger.info(f"  📝 文本: '{xpath_info['text']}'")
                logger.info(f"  📍 位置: ({xpath_info['rect']['x']:.0f}, {xpath_info['rect']['y']:.0f})")
                logger.info(f"  📏 大小: {xpath_info['rect']['width']:.0f}x{xpath_info['rect']['height']:.0f}")
            else:
                logger.info("  ❌ xpath不存在")
            
            # ===== 步骤 5: 总结和建议 =====
            logger.info("\\n💡 步骤 5: 分析总结和新方案建议")
            logger.info("-" * 50)
            
            # 基于分析结果给出建议
            if final_analysis['xpathTarget']['exists'] and final_analysis['xpathTarget']['visible']:
                logger.info("🎯 发现目标xpath元素且可见!")
                logger.info("💡 建议: 直接点击xpath元素")
            elif final_analysis['videos']:
                logger.info("🎬 发现视频元素!")
                logger.info("💡 建议: 直接控制视频播放")
            elif final_analysis['iframes']:
                logger.info("🖼️  发现iframe元素!")
                logger.info("💡 建议: 可能视频在iframe内")
            elif final_analysis['popups']:
                logger.info("🪟 发现弹窗元素!")
                logger.info("💡 建议: 需要先处理弹窗")
            else:
                logger.info("❓ 未发现明确的视频相关元素")
                logger.info("💡 建议: 需要进一步分析页面跳转逻辑")
            
            # 保持浏览器打开以便进一步手动分析
            logger.info("\\n🔍 保持浏览器打开60秒以便进一步手动分析...")
            logger.info("💭 请继续手动操作并观察页面行为")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()
    
    logger.info("\\n" + "=" * 80)
    logger.info("🏁 完整流程分析完成")
    logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(deep_analysis_complete_flow())