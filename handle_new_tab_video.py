#!/usr/bin/env python
"""
处理在新tab中打开的视频页面

关键发现：点击"继续学习"按钮会在新tab中打开视频播放页面
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_new_tab_video():
    """测试处理新tab中的视频页面"""
    logger.info("=" * 80)
    logger.info("🆕 处理在新tab中打开的视频页面")
    logger.info("📋 关键发现：点击'继续学习'会在新tab中打开视频")
    logger.info("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            # 创建浏览器上下文
            context = await browser.new_context()
            page = await context.new_page()
            
            # 登录
            logger.info("🔐 步骤 1: 登录...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败")
                return
            
            logger.info("✅ 登录成功")
            
            # 进入课程列表
            logger.info("📚 步骤 2: 进入课程列表...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            logger.info(f"📍 课程列表页面: {page.url}")
            
            # 监听新页面创建事件
            logger.info("👂 设置新页面监听器...")
            new_pages = []
            context.on("page", lambda new_page: new_pages.append(new_page))
            
            # 点击继续学习按钮
            logger.info("🎯 步骤 3: 点击'继续学习'按钮...")
            initial_page_count = len(context.pages)
            logger.info(f"点击前页面数: {initial_page_count}")
            
            clicked = await page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('div.btn');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习')) {
                            btn.click();
                            return {
                                success: true,
                                text: text.trim()
                            };
                        }
                    }
                    return { success: false };
                }
            """)
            
            if clicked['success']:
                logger.info(f"✅ 成功点击按钮: {clicked['text']}")
                
                # 等待新页面创建
                logger.info("⏳ 等待新tab打开...")
                await asyncio.sleep(5)
                
                current_page_count = len(context.pages)
                logger.info(f"点击后页面数: {current_page_count}")
                
                if current_page_count > initial_page_count:
                    logger.info(f"🎉 检测到 {current_page_count - initial_page_count} 个新页面!")
                    
                    # 获取最新的页面（视频页面）
                    video_page = context.pages[-1]  # 最后一个页面应该是新打开的
                    
                    logger.info("⏳ 等待新页面加载...")
                    await video_page.wait_for_load_state('networkidle')
                    await asyncio.sleep(3)
                    
                    logger.info(f"🎬 视频页面URL: {video_page.url}")
                    logger.info(f"📄 视频页面标题: {await video_page.title()}")
                    
                    # 切换到视频页面进行处理
                    await handle_video_page_with_iframe(video_page)
                    
                    # 保持浏览器打开观察
                    logger.info("\n🔍 保持浏览器打开90秒以便观察...")
                    await asyncio.sleep(90)
                    
                else:
                    logger.warning("❌ 未检测到新页面创建")
                    logger.info("💡 可能需要手动点击")
                    
                    # 等待手动操作
                    logger.info("👆 请手动点击'继续学习'按钮")
                    logger.info("⏰ 等待60秒检测新页面...")
                    
                    for i in range(12):  # 60秒，每5秒检查一次
                        await asyncio.sleep(5)
                        current_count = len(context.pages)
                        if current_count > initial_page_count:
                            logger.info(f"🎉 检测到手动打开的新页面!")
                            video_page = context.pages[-1]
                            await video_page.wait_for_load_state('networkidle')
                            await asyncio.sleep(3)
                            
                            logger.info(f"🎬 视频页面URL: {video_page.url}")
                            await handle_video_page_with_iframe(video_page)
                            break
                        elif i % 2 == 0:
                            logger.info(f"⏱️  还有{60-i*5}秒...")
                    else:
                        logger.error("❌ 60秒内未检测到新页面")
            else:
                logger.error("❌ 未找到'继续学习'按钮")
                
        finally:
            await browser.close()

async def handle_video_page_with_iframe(video_page):
    """处理包含iframe的视频页面"""
    logger.info("\n" + "="*80)
    logger.info("🎬 处理视频页面中的iframe播放器")
    logger.info("="*80)
    
    try:
        # 分析页面结构
        page_analysis = await analyze_video_page_structure(video_page)
        
        if page_analysis['iframes']:
            logger.info(f"🖼️  发现 {len(page_analysis['iframes'])} 个iframe")
            
            # 处理每个iframe
            for i, iframe_info in enumerate(page_analysis['iframes']):
                logger.info(f"\n🎯 处理iframe {i+1}:")
                logger.info(f"   源: {iframe_info['src']}")
                logger.info(f"   类: {iframe_info['class']}")
                logger.info(f"   大小: {iframe_info['width']}x{iframe_info['height']}")
                
                if 'scorm_play.do' in iframe_info['src'] or 'player' in iframe_info['class']:
                    logger.info("✅ 这是视频播放器iframe")
                    
                    # 尝试处理iframe内的内容
                    success = await handle_iframe_content(video_page, i, iframe_info)
                    if success:
                        logger.info("🎉 iframe处理成功!")
                        return
                    else:
                        logger.warning("⚠️  iframe处理失败，尝试其他方法")
        
        # 如果iframe处理失败，检查是否有xpath元素
        xpath_elements = page_analysis.get('xpath_elements', {})
        if xpath_elements:
            logger.info("\n🎯 检查xpath元素...")
            for xpath, info in xpath_elements.items():
                if info['exists'] and info['visible']:
                    logger.info(f"✅ 发现可见的xpath元素: {xpath}")
                    logger.info(f"   文本: {info['text']}")
                    
                    # 尝试点击xpath元素
                    clicked = await video_page.evaluate(f"""
                        () => {{
                            const xpath = '{xpath}';
                            const result = document.evaluate(xpath, document, null,
                                XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                            const element = result.singleNodeValue;
                            if (element) {{
                                element.click();
                                return true;
                            }}
                            return false;
                        }}
                    """)
                    
                    if clicked:
                        logger.info(f"✅ 成功点击xpath元素: {xpath}")
                        await asyncio.sleep(3)
                        break
        
    except Exception as e:
        logger.error(f"❌ 处理视频页面时异常: {e}")

async def analyze_video_page_structure(video_page):
    """分析视频页面结构"""
    logger.info("🔍 分析视频页面结构...")
    
    analysis = await video_page.evaluate("""
        () => {
            const result = {
                url: window.location.href,
                title: document.title,
                iframes: [],
                videos: [],
                xpath_elements: {}
            };
            
            // 分析iframe
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach((iframe, index) => {
                const rect = iframe.getBoundingClientRect();
                result.iframes.push({
                    index: index,
                    src: iframe.src || iframe.getAttribute('src') || '',
                    class: iframe.className || '',
                    id: iframe.id || '',
                    width: rect.width,
                    height: rect.height,
                    visible: rect.width > 0 && rect.height > 0
                });
            });
            
            // 分析视频元素
            const videos = document.querySelectorAll('video');
            videos.forEach((video, index) => {
                const rect = video.getBoundingClientRect();
                result.videos.push({
                    index: index,
                    src: video.src || video.currentSrc || '',
                    visible: rect.width > 0 && rect.height > 0,
                    paused: video.paused
                });
            });
            
            // 检查关键xpath
            const xpaths = [
                '/html/body/div/div[3]/div[2]',
                '/html/body/div/div[2]/div[2]',
                '/html/body/div/div[4]/div[2]'
            ];
            
            xpaths.forEach(xpath => {
                const xpathResult = document.evaluate(xpath, document, null,
                    XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const element = xpathResult.singleNodeValue;
                
                if (element) {
                    const rect = element.getBoundingClientRect();
                    result.xpath_elements[xpath] = {
                        exists: true,
                        visible: rect.width > 0 && rect.height > 0,
                        tag: element.tagName,
                        class: element.className || '',
                        text: (element.textContent || '').substring(0, 100)
                    };
                } else {
                    result.xpath_elements[xpath] = { exists: false };
                }
            });
            
            return result;
        }
    """)
    
    logger.info(f"📊 页面分析结果:")
    logger.info(f"   📍 URL: {analysis['url']}")
    logger.info(f"   📄 标题: {analysis['title']}")
    logger.info(f"   🖼️  iframe数: {len(analysis['iframes'])}")
    logger.info(f"   🎬 video数: {len(analysis['videos'])}")
    
    return analysis

async def handle_iframe_content(video_page, iframe_index, iframe_info):
    """处理iframe内容的多种方法"""
    logger.info(f"🔧 尝试多种方法处理iframe {iframe_index+1}")
    
    # 方法1: JavaScript直接访问
    logger.info("🔹 方法1: JavaScript直接访问iframe内容")
    js_result = await handle_iframe_via_javascript(video_page, iframe_index)
    if js_result:
        return True
    
    # 方法2: Playwright frame locator
    logger.info("🔹 方法2: Playwright frame locator")
    frame_result = await handle_iframe_via_frame_locator(video_page, iframe_index)
    if frame_result:
        return True
    
    # 方法3: 等待加载后重试
    logger.info("🔹 方法3: 等待加载后重试JavaScript方法")
    await asyncio.sleep(5)
    retry_result = await handle_iframe_via_javascript(video_page, iframe_index)
    if retry_result:
        return True
    
    return False

async def handle_iframe_via_javascript(video_page, iframe_index):
    """JavaScript方法处理iframe"""
    try:
        result = await video_page.evaluate(f"""
            (index) => {{
                const iframe = document.querySelectorAll('iframe')[index];
                if (!iframe) return {{ success: false, error: 'iframe不存在' }};
                
                try {{
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!iframeDoc) {{
                        return {{ success: false, error: '跨域iframe无法访问' }};
                    }}
                    
                    // 查找视频
                    const videos = iframeDoc.querySelectorAll('video');
                    if (videos.length > 0) {{
                        for (let video of videos) {{
                            if (video.paused) {{
                                try {{
                                    video.play();
                                    return {{ success: true, method: '直接播放视频', videos: videos.length }};
                                }} catch (e) {{
                                    console.log('播放失败:', e);
                                }}
                            }}
                        }}
                    }}
                    
                    // 查找播放按钮
                    const buttons = [
                        ...iframeDoc.querySelectorAll('button'),
                        ...iframeDoc.querySelectorAll('div[onclick]'),
                        ...iframeDoc.querySelectorAll('.btn')
                    ];
                    
                    for (let btn of buttons) {{
                        const text = btn.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习') || text.includes('播放')) {{
                            btn.click();
                            return {{ success: true, method: '点击按钮', text: text.trim() }};
                        }}
                    }}
                    
                    return {{ success: false, error: '未找到可操作元素', buttons: buttons.length, videos: videos.length }};
                    
                }} catch (e) {{
                    return {{ success: false, error: `错误: ${{e.message}}` }};
                }}
            }}
        """, iframe_index)
        
        if result['success']:
            logger.info(f"✅ JavaScript方法成功: {result['method']}")
            if 'text' in result:
                logger.info(f"   点击了: {result['text']}")
            elif 'videos' in result:
                logger.info(f"   播放了 {result['videos']} 个视频")
            return True
        else:
            logger.warning(f"❌ JavaScript方法失败: {result['error']}")
            if 'buttons' in result:
                logger.info(f"   iframe内按钮: {result['buttons']}个, 视频: {result.get('videos', 0)}个")
            return False
            
    except Exception as e:
        logger.error(f"❌ JavaScript处理异常: {e}")
        return False

async def handle_iframe_via_frame_locator(video_page, iframe_index):
    """Frame locator方法处理iframe"""
    try:
        iframe_selector = f"iframe:nth-child({iframe_index + 1})"
        frame = video_page.frame_locator(iframe_selector)
        
        # 查找视频
        video_count = await frame.locator('video').count()
        if video_count > 0:
            logger.info(f"🎬 iframe内发现 {video_count} 个视频")
            video = frame.locator('video').first
            if await video.is_visible():
                await video.click()
                logger.info("✅ 点击了视频元素")
                return True
        
        # 查找按钮
        button_selectors = [
            'button:has-text("继续学习")',
            'button:has-text("开始学习")',
            'button:has-text("播放")',
            'div:has-text("继续学习")',
            '.play-btn'
        ]
        
        for selector in button_selectors:
            try:
                count = await frame.locator(selector).count()
                if count > 0:
                    element = frame.locator(selector).first
                    if await element.is_visible():
                        await element.click()
                        logger.info(f"✅ 点击了 '{selector}' 元素")
                        return True
            except Exception as e:
                logger.debug(f"尝试 '{selector}' 失败: {e}")
                continue
        
        return False
        
    except Exception as e:
        logger.warning(f"❌ Frame locator方法失败: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_new_tab_video())