#!/usr/bin/env python
"""
iframe视频播放器处理逻辑

基于用户提供的信息：
- 视频播放页面包含iframe: /device/study_new!scorm_play.do?terminal=1&id=1988341
- class="player" 的iframe包含真正的视频播放器
- "继续学习"弹窗可能出现在iframe内部
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_iframe_video_handler():
    """测试iframe视频播放器处理"""
    logger.info("=" * 80)
    logger.info("🎬 iframe视频播放器处理测试")
    logger.info("📋 目标：正确处理iframe内的视频播放和弹窗")
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
            logger.info("📚 步骤 2: 进入课程列表...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 尝试进入视频页面
            logger.info("🎯 步骤 3: 尝试进入视频页面...")
            video_page_entered = await enter_video_page_with_retry(page)
            
            if video_page_entered:
                logger.info("✅ 成功进入视频页面")
                
                # 等待iframe加载
                logger.info("⏳ 等待iframe视频播放器加载...")
                await asyncio.sleep(5)
                
                # 处理iframe视频播放器
                await handle_iframe_player(page)
                
            else:
                logger.error("❌ 无法进入视频页面")
                logger.info("💡 请手动点击'继续学习'按钮进入视频页面")
                logger.info("⏰ 等待30秒供手动操作...")
                await asyncio.sleep(30)
                
                # 检查是否手动进入了视频页面
                current_url = page.url
                if 'video_page' in current_url:
                    logger.info("🎉 检测到手动进入视频页面")
                    await handle_iframe_player(page)
                else:
                    logger.error("❌ 仍未进入视频页面")
                    return
            
            # 保持浏览器打开观察
            logger.info("\n🔍 保持浏览器打开90秒以便观察iframe视频播放...")
            await asyncio.sleep(90)
            
        finally:
            await browser.close()

async def enter_video_page_with_retry(page, max_attempts=3):
    """多次尝试进入视频页面"""
    initial_url = page.url
    
    for attempt in range(max_attempts):
        logger.info(f"🔄 尝试 {attempt + 1}/{max_attempts}: 点击'继续学习'按钮")
        
        # 查找并点击继续学习按钮
        clicked = await page.evaluate("""
            () => {
                // 查找所有可能的按钮
                const selectors = ['div.btn', 'button', '.continue-btn', '[onclick*="学习"]'];
                
                for (let selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    for (let el of elements) {
                        const text = el.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习')) {
                            // 滚动到元素位置并点击
                            el.scrollIntoView({behavior: 'smooth', block: 'center'});
                            el.click();
                            return {
                                success: true,
                                text: text.trim(),
                                selector: selector
                            };
                        }
                    }
                }
                return { success: false };
            }
        """)
        
        if clicked['success']:
            logger.info(f"✅ 点击了按钮: '{clicked['text']}' (选择器: {clicked['selector']})")
            
            # 等待页面响应
            await asyncio.sleep(8)  # 增加等待时间
            
            # 检查是否成功跳转
            current_url = page.url
            if current_url != initial_url and 'video_page' in current_url:
                logger.info(f"🎉 成功跳转到视频页面: {current_url}")
                return True
            else:
                logger.warning(f"⚠️  尝试{attempt + 1}: 点击后未跳转，当前URL: {current_url}")
                # 继续下一次尝试
        else:
            logger.warning(f"⚠️  尝试{attempt + 1}: 未找到'继续学习'按钮")
        
        # 短暂等待再尝试
        if attempt < max_attempts - 1:
            await asyncio.sleep(3)
    
    return False

async def handle_iframe_player(page):
    """处理iframe视频播放器"""
    logger.info("\n" + "="*80)
    logger.info("🎬 开始处理iframe视频播放器")
    logger.info("="*80)
    
    # 首先分析页面上的iframe
    iframe_info = await analyze_page_iframes(page)
    
    if not iframe_info['iframes']:
        logger.error("❌ 页面上未找到iframe元素")
        return
    
    # 处理每个iframe
    for i, iframe_data in enumerate(iframe_info['iframes']):
        logger.info(f"\n🖼️  处理iframe {i+1}: {iframe_data['src']}")
        
        if 'scorm_play.do' in iframe_data['src'] or 'player' in iframe_data.get('class', ''):
            logger.info("🎯 这是视频播放器iframe")
            await handle_player_iframe(page, i, iframe_data)
        else:
            logger.info("ℹ️  跳过非播放器iframe")

async def analyze_page_iframes(page):
    """分析页面上的iframe"""
    logger.info("🔍 分析页面iframe结构...")
    
    iframe_analysis = await page.evaluate("""
        () => {
            const analysis = {
                url: window.location.href,
                title: document.title,
                iframes: []
            };
            
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach((iframe, index) => {
                const rect = iframe.getBoundingClientRect();
                analysis.iframes.push({
                    index: index,
                    src: iframe.src || iframe.getAttribute('src') || '',
                    class: iframe.className || '',
                    id: iframe.id || '',
                    width: rect.width,
                    height: rect.height,
                    visible: rect.width > 0 && rect.height > 0,
                    // 尝试获取其他属性
                    border: iframe.getAttribute('border') || '',
                    scrolling: iframe.getAttribute('scrolling') || ''
                });
            });
            
            return analysis;
        }
    """)
    
    logger.info(f"📊 iframe分析结果:")
    logger.info(f"📍 当前页面: {iframe_analysis['url']}")
    logger.info(f"📄 页面标题: {iframe_analysis['title']}")
    logger.info(f"🖼️  发现 {len(iframe_analysis['iframes'])} 个iframe:")
    
    for i, iframe in enumerate(iframe_analysis['iframes']):
        logger.info(f"  {i+1}. 源: {iframe['src']}")
        logger.info(f"     类: {iframe['class']}")
        logger.info(f"     大小: {iframe['width']}x{iframe['height']}")
        logger.info(f"     可见: {iframe['visible']}")
    
    return iframe_analysis

async def handle_player_iframe(page, iframe_index, iframe_data):
    """处理视频播放器iframe"""
    logger.info(f"🎬 开始处理视频播放器iframe {iframe_index}")
    
    try:
        # 等待iframe完全加载
        logger.info("⏳ 等待iframe完全加载...")
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(5)
        
        # 尝试获取iframe元素
        iframe_selector = f"iframe:nth-child({iframe_index + 1})"
        iframe_handle = page.frame_locator(iframe_selector)
        
        if iframe_handle:
            logger.info("✅ 成功获取iframe句柄")
            
            # 分析iframe内容
            await analyze_iframe_content(page, iframe_selector, iframe_handle)
            
            # 处理iframe内的弹窗和视频
            await handle_iframe_interactions(iframe_handle, iframe_data)
            
        else:
            logger.error("❌ 无法获取iframe句柄")
            
            # 备用方法：尝试通过JavaScript交互
            logger.info("🔄 尝试备用方法...")
            await handle_iframe_via_javascript(page, iframe_index, iframe_data)
    
    except Exception as e:
        logger.error(f"❌ 处理iframe时发生异常: {e}")
        logger.info("🔄 尝试备用处理方法...")
        await handle_iframe_via_javascript(page, iframe_index, iframe_data)

async def analyze_iframe_content(page, iframe_selector, iframe_handle):
    """分析iframe内容"""
    logger.info("🔍 分析iframe内容...")
    
    try:
        # 尝试获取iframe内的基本信息
        iframe_title = await iframe_handle.locator('title').text_content() if await iframe_handle.locator('title').count() > 0 else "未知"
        logger.info(f"📄 iframe标题: {iframe_title}")
        
        # 检查iframe内的视频元素
        video_count = await iframe_handle.locator('video').count()
        logger.info(f"🎬 iframe内视频元素: {video_count}个")
        
        # 检查iframe内的按钮元素
        button_selectors = ['button', 'div.btn', '.play-btn', '.continue-btn', '[onclick]']
        total_buttons = 0
        
        for selector in button_selectors:
            count = await iframe_handle.locator(selector).count()
            if count > 0:
                logger.info(f"🔘 '{selector}': {count}个")
                total_buttons += count
        
        logger.info(f"📊 iframe内总按钮数: {total_buttons}")
        
        # 检查可能的弹窗元素
        popup_selectors = ['.modal', '.dialog', '.popup', '.overlay', '.el-dialog']
        popup_count = 0
        
        for selector in popup_selectors:
            count = await iframe_handle.locator(selector).count()
            popup_count += count
        
        logger.info(f"🪟 iframe内弹窗元素: {popup_count}个")
        
    except Exception as e:
        logger.warning(f"⚠️  分析iframe内容时出错: {e}")
        logger.info("💡 这可能是跨域iframe，无法直接访问内容")

async def handle_iframe_interactions(iframe_handle, iframe_data):
    """处理iframe内的交互"""
    logger.info("🖱️  开始处理iframe内的交互...")
    
    try:
        # 查找并点击可能的"继续学习"或播放按钮
        learning_button_selectors = [
            'button:has-text("继续学习")',
            'button:has-text("开始学习")',
            'button:has-text("播放")',
            'div:has-text("继续学习")',
            'div:has-text("开始学习")',
            '.play-btn',
            '.continue-btn',
            '[onclick*="play"]',
            '[onclick*="学习"]'
        ]
        
        for selector in learning_button_selectors:
            try:
                elements = iframe_handle.locator(selector)
                count = await elements.count()
                
                if count > 0:
                    logger.info(f"✅ 找到 {count} 个 '{selector}' 元素")
                    
                    for i in range(count):
                        element = elements.nth(i)
                        if await element.is_visible():
                            logger.info(f"🖱️  点击 '{selector}' 元素 {i+1}")
                            await element.click()
                            
                            # 等待响应
                            await asyncio.sleep(3)
                            
                            # 检查点击效果
                            await check_iframe_click_effect(iframe_handle)
                            break
                    break
            
            except Exception as e:
                logger.debug(f"尝试 '{selector}' 时出错: {e}")
                continue
        
    except Exception as e:
        logger.error(f"❌ 处理iframe交互时出错: {e}")

async def handle_iframe_via_javascript(page, iframe_index, iframe_data):
    """通过JavaScript处理iframe"""
    logger.info("🔧 使用JavaScript方法处理iframe...")
    
    try:
        result = await page.evaluate(f"""
            (index) => {{
                const iframe = document.querySelectorAll('iframe')[index];
                if (!iframe) return {{ success: false, error: 'iframe不存在' }};
                
                try {{
                    // 尝试访问iframe的document
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    if (!iframeDoc) {{
                        return {{ success: false, error: '无法访问iframe内容(跨域)' }};
                    }}
                    
                    // 查找按钮
                    const buttons = iframeDoc.querySelectorAll('button, div[onclick], .btn');
                    const learningButtons = [];
                    
                    buttons.forEach((btn, i) => {{
                        const text = btn.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习') || text.includes('播放')) {{
                            learningButtons.push({{
                                index: i,
                                text: text.trim(),
                                tagName: btn.tagName,
                                className: btn.className
                            }});
                        }}
                    }});
                    
                    // 尝试点击第一个找到的按钮
                    if (learningButtons.length > 0) {{
                        const firstBtn = buttons[learningButtons[0].index];
                        firstBtn.click();
                        
                        return {{
                            success: true,
                            clicked: learningButtons[0],
                            totalButtons: buttons.length,
                            learningButtons: learningButtons.length
                        }};
                    }}
                    
                    return {{
                        success: false,
                        error: '未找到学习相关按钮',
                        totalButtons: buttons.length
                    }};
                    
                }} catch (e) {{
                    return {{ success: false, error: `JavaScript错误: ${{e.message}}` }};
                }}
            }}
        """, iframe_index)
        
        if result['success']:
            logger.info(f"✅ 成功点击iframe内按钮: {result['clicked']['text']}")
            logger.info(f"📊 iframe内总按钮: {result['totalButtons']}个, 学习相关: {result['learningButtons']}个")
            
            # 等待效果
            await asyncio.sleep(5)
            
        else:
            logger.warning(f"⚠️  JavaScript方法失败: {result['error']}")
            if 'totalButtons' in result:
                logger.info(f"📊 iframe内总按钮: {result['totalButtons']}个")
    
    except Exception as e:
        logger.error(f"❌ JavaScript处理iframe时异常: {e}")

async def check_iframe_click_effect(iframe_handle):
    """检查iframe内点击的效果"""
    logger.info("🔍 检查iframe内点击效果...")
    
    try:
        # 检查是否有视频开始播放
        video_count = await iframe_handle.locator('video').count()
        if video_count > 0:
            logger.info(f"🎬 iframe内有 {video_count} 个视频元素")
            
            # 尝试获取视频状态（可能会因为跨域问题失败）
            try:
                video = iframe_handle.locator('video').first
                if await video.is_visible():
                    logger.info("✅ 视频元素可见")
            except:
                logger.info("ℹ️  无法获取视频详细状态（可能是跨域限制）")
        
        # 检查弹窗变化
        popup_count = await iframe_handle.locator('.modal, .dialog, .popup').count()
        logger.info(f"🪟 iframe内弹窗: {popup_count}个")
        
    except Exception as e:
        logger.warning(f"⚠️  检查点击效果时出错: {e}")

if __name__ == "__main__":
    asyncio.run(test_iframe_video_handler())