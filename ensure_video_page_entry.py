#!/usr/bin/env python
"""
确保真正进入视频播放页面

目标：从课程列表页面成功跳转到视频播放页面
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def ensure_video_page_entry():
    """确保成功进入视频播放页面"""
    logger.info("=" * 80)
    logger.info("🎯 目标：确保成功进入视频播放页面")
    logger.info("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 登录
            logger.info("🔐 步骤 1: 登录...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败")
                return
            
            logger.info("✅ 登录成功")
            
            # 进入课程列表
            logger.info("📚 步骤 2: 进入课程列表页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            initial_url = page.url
            logger.info(f"📍 当前在课程列表页面: {initial_url}")
            
            # 智能点击策略：尝试多种方式进入视频页面
            logger.info("🎯 步骤 3: 尝试多种方式进入视频播放页面...")
            
            methods = [
                "点击第一个继续学习按钮",
                "双击继续学习按钮", 
                "点击课程标题后再点击继续学习",
                "滚动到页面中间再点击",
                "等待更长时间再点击"
            ]
            
            for i, method in enumerate(methods):
                logger.info(f"\\n🔄 方法 {i+1}: {method}")
                logger.info("-" * 40)
                
                try:
                    if i == 0:  # 方法1：简单点击
                        clicked = await page.evaluate("""
                            () => {
                                const buttons = document.querySelectorAll('div.btn');
                                for (let btn of buttons) {
                                    if (btn.textContent.includes('继续学习')) {
                                        btn.click();
                                        return {
                                            success: true, 
                                            text: btn.textContent.trim(),
                                            method: 'simple_click'
                                        };
                                    }
                                }
                                return { success: false };
                            }
                        """)
                    
                    elif i == 1:  # 方法2：双击
                        clicked = await page.evaluate("""
                            () => {
                                const buttons = document.querySelectorAll('div.btn');
                                for (let btn of buttons) {
                                    if (btn.textContent.includes('继续学习')) {
                                        btn.click();
                                        setTimeout(() => btn.click(), 100);
                                        return {
                                            success: true, 
                                            text: btn.textContent.trim(),
                                            method: 'double_click'
                                        };
                                    }
                                }
                                return { success: false };
                            }
                        """)
                    
                    elif i == 2:  # 方法3：先点击课程区域
                        clicked = await page.evaluate("""
                            () => {
                                const courseItems = document.querySelectorAll('.el-collapse-item, li');
                                for (let item of courseItems) {
                                    const btn = item.querySelector('div.btn');
                                    if (btn && btn.textContent.includes('继续学习')) {
                                        // 先点击课程区域，再点击按钮
                                        item.click();
                                        setTimeout(() => btn.click(), 200);
                                        return {
                                            success: true, 
                                            text: btn.textContent.trim(),
                                            method: 'course_area_first'
                                        };
                                    }
                                }
                                return { success: false };
                            }
                        """)
                    
                    elif i == 3:  # 方法4：滚动后点击
                        await page.evaluate("window.scrollTo(0, window.innerHeight)")
                        await asyncio.sleep(1)
                        clicked = await page.evaluate("""
                            () => {
                                const buttons = document.querySelectorAll('div.btn');
                                for (let btn of buttons) {
                                    if (btn.textContent.includes('继续学习')) {
                                        btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                                        setTimeout(() => btn.click(), 500);
                                        return {
                                            success: true, 
                                            text: btn.textContent.trim(),
                                            method: 'scroll_then_click'
                                        };
                                    }
                                }
                                return { success: false };
                            }
                        """)
                    
                    elif i == 4:  # 方法5：等待后点击
                        await asyncio.sleep(2)
                        clicked = await page.evaluate("""
                            () => {
                                const buttons = document.querySelectorAll('div.btn');
                                for (let btn of buttons) {
                                    if (btn.textContent.includes('继续学习')) {
                                        btn.click();
                                        return {
                                            success: true, 
                                            text: btn.textContent.trim(),
                                            method: 'delayed_click'
                                        };
                                    }
                                }
                                return { success: false };
                            }
                        """)
                    
                    if clicked['success']:
                        logger.info(f"✅ 点击成功: {clicked['text']} (方法: {clicked['method']})")
                        
                        # 等待页面变化
                        logger.info("⏰ 等待页面跳转...")
                        await asyncio.sleep(5)
                        
                        # 检查页面是否跳转
                        new_url = page.url
                        if new_url != initial_url:
                            logger.info(f"🎉 成功跳转到新页面!")
                            logger.info(f"📍 新URL: {new_url}")
                            
                            # 等待新页面完全加载
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            await asyncio.sleep(3)
                            
                            # 分析新页面
                            await analyze_video_page(page, new_url)
                            break
                        else:
                            logger.warning(f"❌ 页面未跳转，仍在: {new_url}")
                            # 继续尝试下一种方法
                            continue
                    else:
                        logger.warning(f"❌ 方法{i+1}点击失败")
                        continue
                        
                except Exception as e:
                    logger.error(f"❌ 方法{i+1}发生异常: {e}")
                    continue
            
            else:
                logger.error("❌ 所有方法都失败了，无法进入视频页面")
                logger.info("💡 可能需要手动操作来进入视频页面")
                
                logger.info("\\n👆 请手动点击任意'继续学习'按钮进入视频页面")
                logger.info("⏰ 等待30秒供手动操作...")
                
                for i in range(30):
                    await asyncio.sleep(1)
                    current_url = page.url
                    if current_url != initial_url:
                        logger.info(f"🎉 检测到手动跳转成功!")
                        logger.info(f"📍 新URL: {current_url}")
                        await page.wait_for_load_state('networkidle', timeout=10000)
                        await asyncio.sleep(3)
                        await analyze_video_page(page, current_url)
                        break
                    elif i % 5 == 0:
                        logger.info(f"⏱️  还有{30-i}秒...")
                else:
                    logger.error("❌ 30秒内未检测到页面跳转")
            
            # 保持浏览器打开
            logger.info("\\n🔍 保持浏览器打开60秒以便进一步分析...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

async def analyze_video_page(page, url):
    """分析视频播放页面"""
    logger.info("\\n" + "=" * 60)
    logger.info("📹 分析视频播放页面")
    logger.info("=" * 60)
    
    # 分析页面内容
    video_page_analysis = await page.evaluate("""
        () => {
            const analysis = {
                url: window.location.href,
                title: document.title,
                videos: [],
                iframes: [],
                xpathTarget: null,
                popups: [],
                allDivs: []
            };
            
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
                    currentTime: video.currentTime,
                    rect: { width: rect.width, height: rect.height }
                });
            });
            
            // 查找iframe
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach((iframe, index) => {
                const rect = iframe.getBoundingClientRect();
                analysis.iframes.push({
                    index: index,
                    src: iframe.src,
                    visible: rect.width > 0 && rect.height > 0,
                    rect: { width: rect.width, height: rect.height }
                });
            });
            
            // 检查目标xpath
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
                    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                };
            } else {
                analysis.xpathTarget = { exists: false };
            }
            
            // 查找弹窗
            const popupSelectors = ['.el-dialog', '.modal', '.popup', '[role="dialog"]'];
            popupSelectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        analysis.popups.push({
                            selector: selector,
                            class: el.className,
                            text: el.textContent?.substring(0, 100)
                        });
                    }
                });
            });
            
            // 查找包含"继续学习"的div
            const allDivs = document.querySelectorAll('div');
            allDivs.forEach(div => {
                const text = div.textContent || '';
                if ((text.includes('继续学习') || text.includes('开始学习')) && text.length < 50) {
                    const rect = div.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        analysis.allDivs.push({
                            text: text.trim(),
                            class: div.className,
                            rect: { x: rect.x, y: rect.y }
                        });
                    }
                }
            });
            
            return analysis;
        }
    """)
    
    logger.info(f"📍 视频页面URL: {video_page_analysis['url']}")
    logger.info(f"📄 页面标题: {video_page_analysis['title']}")
    
    logger.info(f"\\n🎬 发现 {len(video_page_analysis['videos'])} 个视频元素:")
    for i, video in enumerate(video_page_analysis['videos']):
        logger.info(f"  {i+1}. 可见: {video['visible']}, 暂停: {video['paused']}")
        logger.info(f"     大小: {video['rect']['width']}x{video['rect']['height']}")
    
    logger.info(f"\\n🖼️  发现 {len(video_page_analysis['iframes'])} 个iframe:")
    for i, iframe in enumerate(video_page_analysis['iframes']):
        logger.info(f"  {i+1}. 可见: {iframe['visible']}")
        logger.info(f"     大小: {iframe['rect']['width']}x{iframe['rect']['height']}")
    
    logger.info(f"\\n🎯 目标xpath分析:")
    if video_page_analysis['xpathTarget']['exists']:
        xpath_info = video_page_analysis['xpathTarget']
        logger.info(f"  ✅ 找到xpath元素: {xpath_info['tag']}.{xpath_info['class']}")
        logger.info(f"  👁️  可见: {xpath_info['visible']}")
        logger.info(f"  📝 文本: '{xpath_info['text']}'")
        logger.info(f"  📍 位置: ({xpath_info['rect']['x']:.0f}, {xpath_info['rect']['y']:.0f})")
        
        if xpath_info['visible'] and ('继续学习' in xpath_info['text'] or '开始学习' in xpath_info['text']):
            logger.info("🎯 这就是需要处理的xpath弹窗!")
            
            # 尝试点击
            logger.info("🖱️  尝试点击xpath弹窗...")
            clicked = await page.evaluate("""
                () => {
                    const xpath = '/html/body/div/div[3]/div[2]';
                    const result = document.evaluate(
                        xpath, document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    const element = result.singleNodeValue;
                    if (element) {
                        element.click();
                        return true;
                    }
                    return false;
                }
            """)
            
            if clicked:
                logger.info("✅ 成功点击xpath弹窗!")
                await asyncio.sleep(3)
                
                # 检查点击后的变化
                new_analysis = await page.evaluate("""
                    () => {
                        const videos = document.querySelectorAll('video');
                        return {
                            videoCount: videos.length,
                            hasPlayingVideo: Array.from(videos).some(v => !v.paused)
                        };
                    }
                """)
                
                logger.info(f"点击后视频状态: {new_analysis['videoCount']}个视频, 有播放中的视频: {new_analysis['hasPlayingVideo']}")
            else:
                logger.error("❌ 点击xpath弹窗失败")
    else:
        logger.info("  ❌ xpath元素不存在")
    
    logger.info(f"\\n🪟 发现 {len(video_page_analysis['popups'])} 个弹窗:")
    for popup in video_page_analysis['popups']:
        logger.info(f"  - {popup['selector']}: {popup['text'][:50]}...")
    
    logger.info(f"\\n🎯 发现 {len(video_page_analysis['allDivs'])} 个学习相关div:")
    for div in video_page_analysis['allDivs']:
        logger.info(f"  - '{div['text']}' at ({div['rect']['x']:.0f}, {div['rect']['y']:.0f})")

if __name__ == "__main__":
    asyncio.run(ensure_video_page_entry())