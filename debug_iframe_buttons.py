#!/usr/bin/env python
"""
深度调试iframe内的"开始学习"或"继续学习"按钮

问题：用户反馈这些按钮仍然没有被正确处理
目标：详细分析iframe内的按钮结构和交互逻辑
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def debug_iframe_buttons():
    """详细调试iframe内的按钮"""
    logger.info("=" * 80)
    logger.info("🔍 深度调试iframe内的按钮处理逻辑")
    logger.info("📋 目标：找出为什么'开始学习'或'继续学习'按钮没有被正确处理")
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
            logger.info("🔐 步骤 1: 登录...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败")
                return
            
            logger.info("✅ 登录成功")
            
            # 进入课程列表并打开视频页面
            logger.info("📚 步骤 2: 进入课程列表并打开视频页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 设置新页面监听
            context.on("page", lambda new_page: logger.info(f"🆕 检测到新页面: {new_page.url}"))
            
            # 点击继续学习打开新tab
            initial_pages = len(context.pages)
            clicked = await page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('div.btn');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习')) {
                            btn.click();
                            return { success: true, text: text.trim() };
                        }
                    }
                    return { success: false };
                }
            """)
            
            if not clicked['success']:
                logger.error("❌ 未找到继续学习按钮")
                return
            
            logger.info(f"✅ 点击了: {clicked['text']}")
            
            # 等待新tab
            await asyncio.sleep(5)
            if len(context.pages) <= initial_pages:
                logger.error("❌ 新tab未打开")
                return
            
            # 获取视频页面
            video_page = context.pages[-1]
            await video_page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)
            
            logger.info(f"🎬 视频页面: {video_page.url}")
            
            # 步骤3: 深度分析iframe内容
            logger.info("\n🔍 步骤 3: 深度分析iframe内容...")
            logger.info("-" * 60)
            
            await deep_analyze_iframe_content(video_page)
            
            # 步骤4: 多种方法尝试处理iframe按钮
            logger.info("\n🛠️ 步骤 4: 尝试多种方法处理iframe按钮...")
            logger.info("-" * 60)
            
            await try_multiple_iframe_methods(video_page)
            
            # 保持浏览器打开以便手动验证
            logger.info("\n👁️ 步骤 5: 手动验证...")
            logger.info("-" * 60)
            logger.info("🔍 浏览器将保持打开120秒")
            logger.info("💡 请手动检查iframe内是否还有未处理的按钮")
            logger.info("💡 如果有弹窗或按钮，请手动点击观察效果")
            
            await asyncio.sleep(120)
            
        finally:
            await browser.close()

async def deep_analyze_iframe_content(video_page):
    """深度分析iframe内容"""
    try:
        logger.info("🔍 获取iframe基本信息...")
        
        iframe_info = await video_page.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe');
                const result = [];
                
                iframes.forEach((iframe, index) => {
                    const rect = iframe.getBoundingClientRect();
                    result.push({
                        index: index,
                        src: iframe.src,
                        class: iframe.className,
                        id: iframe.id,
                        width: rect.width,
                        height: rect.height,
                        visible: rect.width > 0 && rect.height > 0
                    });
                });
                
                return result;
            }
        """)
        
        logger.info(f"📊 发现 {len(iframe_info)} 个iframe:")
        for i, iframe in enumerate(iframe_info):
            logger.info(f"  iframe {i+1}:")
            logger.info(f"    源: {iframe['src']}")
            logger.info(f"    类: {iframe['class']}")
            logger.info(f"    ID: {iframe['id']}")
            logger.info(f"    大小: {iframe['width']}x{iframe['height']}")
            logger.info(f"    可见: {iframe['visible']}")
            
            if 'scorm_play' in iframe['src'] and iframe['visible']:
                logger.info(f"🎯 iframe {i+1} 是视频播放器，开始详细分析...")
                await analyze_specific_iframe(video_page, i, iframe)
        
    except Exception as e:
        logger.error(f"❌ 分析iframe内容时异常: {e}")

async def analyze_specific_iframe(video_page, iframe_index, iframe_info):
    """分析特定iframe的详细内容"""
    try:
        logger.info(f"\n🔬 深度分析iframe {iframe_index+1}...")
        
        # 方法1: 尝试JavaScript访问
        logger.info("🔹 方法1: JavaScript访问iframe内容...")
        
        js_analysis = await video_page.evaluate(f"""
            (index) => {{
                const iframe = document.querySelectorAll('iframe')[index];
                if (!iframe) return {{ success: false, error: 'iframe不存在' }};
                
                try {{
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!iframeDoc) {{
                        return {{ 
                            success: false, 
                            error: '无法访问iframe内容(跨域)',
                            crossOrigin: true 
                        }};
                    }}
                    
                    const analysis = {{
                        success: true,
                        title: iframeDoc.title,
                        url: iframeDoc.URL,
                        bodyContent: iframeDoc.body ? iframeDoc.body.innerHTML.substring(0, 500) : 'no body',
                        
                        // 详细分析所有可能的按钮元素
                        allButtons: [],
                        allDivs: [],
                        allClickable: [],
                        learningRelated: [],
                        
                        // 视频元素
                        videos: [],
                        
                        // 表单元素
                        forms: []
                    }};
                    
                    // 分析所有button元素
                    const buttons = iframeDoc.querySelectorAll('button');
                    buttons.forEach((btn, i) => {{
                        const rect = btn.getBoundingClientRect();
                        analysis.allButtons.push({{
                            index: i,
                            text: btn.textContent?.trim() || '',
                            class: btn.className || '',
                            id: btn.id || '',
                            type: btn.type || '',
                            disabled: btn.disabled,
                            visible: rect.width > 0 && rect.height > 0,
                            onclick: btn.onclick ? 'has onclick' : 'no onclick'
                        }});
                    }});
                    
                    // 分析所有div元素（可能是自定义按钮）
                    const divs = iframeDoc.querySelectorAll('div');
                    divs.forEach((div, i) => {{
                        const text = div.textContent?.trim() || '';
                        const rect = div.getBoundingClientRect();
                        
                        // 只记录可能是按钮的div
                        if ((text.length > 0 && text.length < 100) && 
                            (div.onclick || div.className.includes('btn') || div.className.includes('button') ||
                             text.includes('学习') || text.includes('播放') || text.includes('开始') || text.includes('继续'))) {{
                            
                            analysis.allDivs.push({{
                                index: i,
                                text: text,
                                class: div.className || '',
                                id: div.id || '',
                                visible: rect.width > 0 && rect.height > 0,
                                onclick: div.onclick ? 'has onclick' : 'no onclick',
                                cursor: window.getComputedStyle(div).cursor
                            }});
                        }}
                    }});
                    
                    // 分析所有可点击元素
                    const clickable = iframeDoc.querySelectorAll('[onclick], [role="button"], .btn, .button, a[href]');
                    clickable.forEach((el, i) => {{
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {{
                            analysis.allClickable.push({{
                                index: i,
                                tag: el.tagName,
                                text: (el.textContent?.trim() || '').substring(0, 50),
                                class: el.className || '',
                                onclick: el.onclick ? 'has onclick' : 'no onclick'
                            }});
                        }}
                    }});
                    
                    // 查找学习相关元素
                    const allElements = iframeDoc.querySelectorAll('*');
                    allElements.forEach((el, i) => {{
                        const text = el.textContent?.trim() || '';
                        if (text.includes('学习') || text.includes('播放') || text.includes('开始') || text.includes('继续') ||
                            text.includes('play') || text.includes('start') || text.includes('continue')) {{
                            
                            if (text.length > 0 && text.length < 200) {{
                                const rect = el.getBoundingClientRect();
                                analysis.learningRelated.push({{
                                    tag: el.tagName,
                                    text: text.substring(0, 100),
                                    class: el.className || '',
                                    visible: rect.width > 0 && rect.height > 0,
                                    clickable: el.onclick || el.className.includes('btn') || el.tagName === 'BUTTON'
                                }});
                            }}
                        }}
                    }});
                    
                    // 分析视频
                    const videos = iframeDoc.querySelectorAll('video');
                    videos.forEach((video, i) => {{
                        analysis.videos.push({{
                            index: i,
                            src: video.src || video.currentSrc || '',
                            paused: video.paused,
                            duration: video.duration || 0,
                            currentTime: video.currentTime || 0,
                            readyState: video.readyState
                        }});
                    }});
                    
                    // 分析表单
                    const forms = iframeDoc.querySelectorAll('form');
                    analysis.forms = Array.from(forms).map(form => ({{
                        action: form.action || '',
                        method: form.method || '',
                        inputs: form.querySelectorAll('input').length
                    }}));
                    
                    return analysis;
                    
                }} catch (e) {{
                    return {{ 
                        success: false, 
                        error: `分析错误: ${{e.message}}`,
                        stack: e.stack 
                    }};
                }}
            }}
        """, iframe_index)
        
        if js_analysis['success']:
            logger.info("✅ JavaScript访问成功!")
            logger.info(f"   标题: {js_analysis['title']}")
            logger.info(f"   URL: {js_analysis['url']}")
            
            # 显示按钮分析
            logger.info(f"\n📊 iframe内容分析:")
            logger.info(f"   🔘 Button元素: {len(js_analysis['allButtons'])}个")
            logger.info(f"   📦 Div按钮: {len(js_analysis['allDivs'])}个")
            logger.info(f"   🖱️  可点击元素: {len(js_analysis['allClickable'])}个")
            logger.info(f"   🎯 学习相关元素: {len(js_analysis['learningRelated'])}个")
            logger.info(f"   🎬 视频元素: {len(js_analysis['videos'])}个")
            logger.info(f"   📝 表单: {len(js_analysis['forms'])}个")
            
            # 详细显示学习相关元素
            if js_analysis['learningRelated']:
                logger.info("\n🎯 学习相关元素详情:")
                for i, elem in enumerate(js_analysis['learningRelated']):
                    logger.info(f"  {i+1}. {elem['tag']}: '{elem['text']}'")
                    logger.info(f"     类: {elem['class']}")
                    logger.info(f"     可见: {elem['visible']}")
                    logger.info(f"     可点击: {elem['clickable']}")
            
            # 详细显示所有按钮
            if js_analysis['allButtons']:
                logger.info("\n🔘 所有Button元素:")
                for btn in js_analysis['allButtons']:
                    logger.info(f"  - '{btn['text']}' (类: {btn['class']}, 可见: {btn['visible']}, 禁用: {btn['disabled']})")
            
            # 详细显示Div按钮
            if js_analysis['allDivs']:
                logger.info("\n📦 Div按钮元素:")
                for div in js_analysis['allDivs']:
                    logger.info(f"  - '{div['text']}' (类: {div['class']}, 可见: {div['visible']}, 光标: {div['cursor']})")
            
            # 显示页面内容片段
            logger.info(f"\n📄 页面内容片段:")
            logger.info(f"{js_analysis['bodyContent'][:300]}...")
            
            return js_analysis
            
        else:
            logger.warning(f"❌ JavaScript访问失败: {js_analysis['error']}")
            if js_analysis.get('crossOrigin'):
                logger.info("💡 这是跨域iframe，尝试其他方法...")
                
                # 方法2: 使用Playwright frame locator分析
                logger.info("🔹 方法2: Playwright frame locator分析...")
                await analyze_iframe_with_frame_locator(video_page, iframe_index)
            
            return None
            
    except Exception as e:
        logger.error(f"❌ 分析iframe时异常: {e}")
        return None

async def analyze_iframe_with_frame_locator(video_page, iframe_index):
    """使用Playwright frame locator分析iframe"""
    try:
        iframe_selector = f"iframe:nth-child({iframe_index + 1})"
        frame = video_page.frame_locator(iframe_selector)
        
        logger.info("🎭 使用Playwright frame locator分析...")
        
        # 分析各种元素
        button_count = await frame.locator('button').count()
        div_count = await frame.locator('div').count()
        link_count = await frame.locator('a').count()
        video_count = await frame.locator('video').count()
        
        logger.info(f"   📊 Frame locator统计:")
        logger.info(f"      Button: {button_count}个")
        logger.info(f"      Div: {div_count}个")
        logger.info(f"      Link: {link_count}个")
        logger.info(f"      Video: {video_count}个")
        
        # 尝试找特定的学习按钮
        learning_selectors = [
            'button:has-text("继续学习")',
            'button:has-text("开始学习")', 
            'button:has-text("播放")',
            'div:has-text("继续学习")',
            'div:has-text("开始学习")',
            'div:has-text("播放")',
            '.btn', '.button', '.play-btn'
        ]
        
        logger.info("   🔍 搜索学习相关按钮:")
        for selector in learning_selectors:
            try:
                count = await frame.locator(selector).count()
                if count > 0:
                    logger.info(f"      ✅ '{selector}': {count}个")
                    
                    # 尝试获取第一个元素的文本
                    try:
                        first_text = await frame.locator(selector).first.text_content()
                        logger.info(f"         第一个元素文本: '{first_text}'")
                    except:
                        pass
                else:
                    logger.info(f"      ❌ '{selector}': 0个")
            except Exception as e:
                logger.debug(f"      ⚠️ '{selector}': 检查失败 - {e}")
        
    except Exception as e:
        logger.error(f"❌ Frame locator分析失败: {e}")

async def try_multiple_iframe_methods(video_page):
    """尝试多种方法处理iframe按钮"""
    logger.info("🛠️ 尝试各种方法处理iframe按钮...")
    
    # 获取iframe数量
    iframe_count = await video_page.evaluate("() => document.querySelectorAll('iframe').length")
    logger.info(f"📊 总共 {iframe_count} 个iframe")
    
    for i in range(iframe_count):
        logger.info(f"\n🎯 处理iframe {i+1}...")
        
        # 方法1: JavaScript直接点击
        logger.info("🔹 方法1: JavaScript直接点击学习按钮...")
        js_result = await try_javascript_click(video_page, i)
        
        if js_result:
            logger.info("✅ JavaScript点击成功!")
            await asyncio.sleep(3)
            continue
        
        # 方法2: Playwright frame locator点击
        logger.info("🔹 方法2: Playwright frame locator点击...")
        frame_result = await try_frame_locator_click(video_page, i)
        
        if frame_result:
            logger.info("✅ Frame locator点击成功!")
            await asyncio.sleep(3)
            continue
        
        # 方法3: 等待后重试
        logger.info("🔹 方法3: 等待5秒后重试...")
        await asyncio.sleep(5)
        retry_result = await try_javascript_click(video_page, i)
        
        if retry_result:
            logger.info("✅ 重试成功!")
        else:
            logger.warning(f"❌ iframe {i+1} 所有方法都失败了")

async def try_javascript_click(video_page, iframe_index):
    """JavaScript方法点击按钮"""
    try:
        result = await video_page.evaluate(f"""
            (index) => {{
                const iframe = document.querySelectorAll('iframe')[index];
                if (!iframe) return {{ success: false, error: 'iframe不存在' }};
                
                try {{
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!iframeDoc) return {{ success: false, error: '跨域iframe' }};
                    
                    // 策略1: 查找并点击视频元素
                    const videos = iframeDoc.querySelectorAll('video');
                    for (let video of videos) {{
                        if (video.paused) {{
                            try {{
                                video.play();
                                return {{ success: true, method: 'video.play()', element: 'video' }};
                            }} catch (e) {{
                                console.log('视频播放失败:', e);
                            }}
                        }}
                    }}
                    
                    // 策略2: 查找学习相关按钮
                    const allElements = iframeDoc.querySelectorAll('button, div, a, span, [onclick]');
                    const candidates = [];
                    
                    for (let el of allElements) {{
                        const text = el.textContent?.trim() || '';
                        const rect = el.getBoundingClientRect();
                        
                        if (rect.width > 0 && rect.height > 0 && (
                            text.includes('继续学习') || text.includes('开始学习') || 
                            text.includes('播放') || text.includes('开始') ||
                            text.includes('play') || text.includes('start') ||
                            el.className.includes('play') || el.className.includes('start')
                        )) {{
                            candidates.push({{ element: el, text: text, tag: el.tagName }});
                        }}
                    }}
                    
                    // 按优先级排序并尝试点击
                    candidates.sort((a, b) => {{
                        // 优先级：包含"继续学习" > "开始学习" > "播放" > 其他
                        const scoreA = a.text.includes('继续学习') ? 4 : 
                                      a.text.includes('开始学习') ? 3 :
                                      a.text.includes('播放') ? 2 : 1;
                        const scoreB = b.text.includes('继续学习') ? 4 : 
                                      b.text.includes('开始学习') ? 3 :
                                      b.text.includes('播放') ? 2 : 1;
                        return scoreB - scoreA;
                    }});
                    
                    for (let candidate of candidates) {{
                        try {{
                            candidate.element.click();
                            return {{ 
                                success: true, 
                                method: 'element.click()', 
                                element: candidate.tag,
                                text: candidate.text 
                            }};
                        }} catch (e) {{
                            console.log('点击失败:', e);
                        }}
                    }}
                    
                    return {{ 
                        success: false, 
                        error: '未找到可点击元素',
                        candidates: candidates.length,
                        videos: videos.length
                    }};
                    
                }} catch (e) {{
                    return {{ success: false, error: e.message }};
                }}
            }}
        """, iframe_index)
        
        if result['success']:
            logger.info(f"   ✅ {result['method']} 成功")
            if 'text' in result:
                logger.info(f"      点击了: {result['element']} - '{result['text']}'")
            elif 'element' in result:
                logger.info(f"      操作了: {result['element']}")
            return True
        else:
            logger.info(f"   ❌ 失败: {result['error']}")
            if 'candidates' in result:
                logger.info(f"      候选元素: {result['candidates']}个, 视频: {result.get('videos', 0)}个")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ JavaScript点击异常: {e}")
        return False

async def try_frame_locator_click(video_page, iframe_index):
    """Frame locator方法点击按钮"""
    try:
        iframe_selector = f"iframe:nth-child({iframe_index + 1})"
        frame = video_page.frame_locator(iframe_selector)
        
        # 尝试各种选择器
        selectors_to_try = [
            ('video', '视频元素'),
            ('button:has-text("继续学习")', '继续学习按钮'),
            ('button:has-text("开始学习")', '开始学习按钮'),
            ('button:has-text("播放")', '播放按钮'),
            ('div:has-text("继续学习")', '继续学习div'),
            ('div:has-text("开始学习")', '开始学习div'),
            ('.play-btn', '播放按钮类'),
            ('.btn', '通用按钮类'),
            ('button', '任意button'),
            ('[onclick]', '任意可点击元素')
        ]
        
        for selector, description in selectors_to_try:
            try:
                count = await frame.locator(selector).count()
                if count > 0:
                    logger.info(f"   🎯 尝试点击 {description} ({count}个)")
                    element = frame.locator(selector).first
                    
                    if await element.is_visible():
                        await element.click()
                        logger.info(f"   ✅ 成功点击 {description}")
                        return True
                    else:
                        logger.info(f"   ⚠️ {description} 不可见")
                        
            except Exception as e:
                logger.debug(f"   ❌ {description} 点击失败: {e}")
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"   ❌ Frame locator点击异常: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(debug_iframe_buttons())