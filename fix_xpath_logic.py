#!/usr/bin/env python
"""
基于监控结果修正xpath处理逻辑

监控发现：
- 用户提供的xpath /html/body/div/div[3]/div[2] 不存在
- 实际存在的是 /html/body/div/div[2]/div[2]，包含视频信息
- 视频在iframe中播放
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_corrected_xpath_logic():
    """测试修正后的xpath逻辑"""
    logger.info("=" * 80)
    logger.info("🔧 测试修正后的xpath处理逻辑")
    logger.info("📋 基于监控结果的发现修正自动化代码")
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
            
            # 点击继续学习进入视频页面
            logger.info("🎯 步骤 3: 尝试进入视频页面...")
            entry_success = await enter_video_page_intelligently(page)
            
            if entry_success:
                logger.info("✅ 成功进入视频页面")
                
                # 处理视频页面的逻辑
                logger.info("🎬 步骤 4: 处理视频页面...")
                await handle_video_page_correctly(page)
                
            else:
                logger.error("❌ 无法进入视频页面")
            
            # 保持浏览器打开观察
            logger.info("\n🔍 保持浏览器打开60秒以便观察...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

async def enter_video_page_intelligently(page):
    """智能进入视频页面"""
    logger.info("🔍 查找'继续学习'按钮...")
    
    # 基于之前的分析，点击div.btn元素
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
        logger.info(f"✅ 点击了按钮: {clicked['text']}")
        
        # 等待页面跳转
        await asyncio.sleep(5)
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # 检查是否成功跳转到视频页面
        current_url = page.url
        if 'video_page' in current_url:
            logger.info(f"🎉 成功跳转到视频页面: {current_url}")
            return True
        else:
            logger.warning(f"❌ 跳转失败，当前URL: {current_url}")
            return False
    else:
        logger.error("❌ 未找到'继续学习'按钮")
        return False

async def handle_video_page_correctly(page):
    """基于监控结果正确处理视频页面"""
    logger.info("🔍 分析视频页面结构...")
    
    page_analysis = await page.evaluate("""
        () => {
            const analysis = {
                url: window.location.href,
                
                // 检查监控发现的关键xpath
                xpaths: {
                    original_target: '/html/body/div/div[3]/div[2]',
                    actual_target: '/html/body/div/div[2]/div[2]'
                },
                
                elements: {},
                
                // 检查iframe
                iframes: []
            };
            
            // 检查xpath元素
            [analysis.xpaths.original_target, analysis.xpaths.actual_target].forEach(xpath => {
                const result = document.evaluate(xpath, document, null, 
                    XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const element = result.singleNodeValue;
                
                if (element) {
                    const rect = element.getBoundingClientRect();
                    analysis.elements[xpath] = {
                        exists: true,
                        visible: rect.width > 0 && rect.height > 0,
                        tag: element.tagName,
                        class: element.className || '',
                        text: (element.textContent || '').substring(0, 200),
                        rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                    };
                } else {
                    analysis.elements[xpath] = { exists: false };
                }
            });
            
            // 检查iframe
            document.querySelectorAll('iframe').forEach((iframe, index) => {
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
            
            return analysis;
        }
    """)
    
    logger.info("📊 视频页面分析结果:")
    logger.info(f"📍 URL: {page_analysis['url']}")
    
    # 检查原始目标xpath
    original_xpath = page_analysis['xpaths']['original_target']
    if page_analysis['elements'][original_xpath]['exists']:
        logger.info(f"✅ 原始目标xpath存在: {original_xpath}")
        element_info = page_analysis['elements'][original_xpath]
        logger.info(f"  标签: {element_info['tag']}, 类: {element_info['class']}")
        logger.info(f"  文本: '{element_info['text']}'")
        
        # 尝试点击原始xpath
        logger.info("🖱️  尝试点击原始xpath...")
        await try_click_xpath(page, original_xpath)
        
    else:
        logger.warning(f"❌ 原始目标xpath不存在: {original_xpath}")
        
        # 检查替代xpath
        actual_xpath = page_analysis['xpaths']['actual_target']
        if page_analysis['elements'][actual_xpath]['exists']:
            logger.info(f"✅ 发现替代xpath: {actual_xpath}")
            element_info = page_analysis['elements'][actual_xpath]
            logger.info(f"  标签: {element_info['tag']}, 类: {element_info['class']}")
            logger.info(f"  文本: '{element_info['text']}'")
            
            if element_info['class'] == 'video':
                logger.info("🎬 这是视频容器元素，尝试点击...")
                await try_click_xpath(page, actual_xpath)
            else:
                logger.info("💡 元素可能不是目标，寻找其他方案...")
    
    # 检查iframe
    if page_analysis['iframes']:
        logger.info(f"🖼️  发现 {len(page_analysis['iframes'])} 个iframe:")
        for i, iframe in enumerate(page_analysis['iframes']):
            logger.info(f"  {i+1}. {iframe['src']}")
            logger.info(f"     大小: {iframe['width']}x{iframe['height']}")
        
        logger.info("💡 视频可能在iframe内播放，需要特殊处理")
        await handle_iframe_video(page, page_analysis['iframes'][0]['src'])

async def try_click_xpath(page, xpath):
    """尝试点击指定的xpath元素"""
    try:
        clicked = await page.evaluate(f"""
            () => {{
                const xpath = '{xpath}';
                const result = document.evaluate(xpath, document, null, 
                    XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const element = result.singleNodeValue;
                
                if (element) {{
                    element.click();
                    return {{
                        success: true,
                        tag: element.tagName,
                        text: (element.textContent || '').substring(0, 50)
                    }};
                }}
                return {{ success: false }};
            }}
        """)
        
        if clicked['success']:
            logger.info(f"✅ 成功点击xpath元素")
            logger.info(f"  元素: {clicked['tag']}")
            logger.info(f"  文本: '{clicked['text']}'")
            
            # 等待可能的变化
            await asyncio.sleep(3)
            
            # 检查点击后的效果
            await check_click_effect(page)
            
        else:
            logger.warning("❌ xpath元素点击失败")
            
    except Exception as e:
        logger.error(f"❌ 点击xpath时发生异常: {e}")

async def handle_iframe_video(page, iframe_src):
    """处理iframe中的视频"""
    logger.info("🎬 尝试处理iframe视频...")
    logger.info(f"📍 iframe源: {iframe_src}")
    
    try:
        # 等待iframe加载
        await asyncio.sleep(5)
        
        # 尝试与iframe交互
        iframe_interaction = await page.evaluate("""
            () => {
                const iframe = document.querySelector('iframe');
                if (iframe) {
                    // 尝试获取iframe的document（同源时才能访问）
                    try {
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        if (iframeDoc) {
                            return {
                                accessible: true,
                                title: iframeDoc.title,
                                url: iframeDoc.URL,
                                hasVideo: iframeDoc.querySelectorAll('video').length > 0
                            };
                        }
                    } catch (e) {
                        // 跨域iframe无法访问
                        return {
                            accessible: false,
                            error: 'Cross-origin iframe'
                        };
                    }
                }
                return { accessible: false, error: 'No iframe found' };
            }
        """)
        
        if iframe_interaction['accessible']:
            logger.info("✅ iframe可以访问")
            logger.info(f"  标题: {iframe_interaction.get('title', 'N/A')}")
            logger.info(f"  包含视频: {iframe_interaction.get('hasVideo', False)}")
        else:
            logger.warning(f"❌ iframe无法访问: {iframe_interaction.get('error', '未知错误')}")
            logger.info("💡 这可能是跨域iframe，需要其他方法处理")
            
    except Exception as e:
        logger.error(f"❌ 处理iframe时发生异常: {e}")

async def check_click_effect(page):
    """检查点击后的效果"""
    logger.info("🔍 检查点击效果...")
    
    effect = await page.evaluate("""
        () => {
            return {
                videoCount: document.querySelectorAll('video').length,
                iframeCount: document.querySelectorAll('iframe').length,
                popupCount: document.querySelectorAll('.el-dialog, .modal, .popup').length,
                hasPlayingVideo: Array.from(document.querySelectorAll('video')).some(v => !v.paused)
            };
        }
    """)
    
    logger.info("📊 点击效果:")
    logger.info(f"  🎬 视频元素: {effect['videoCount']}个")
    logger.info(f"  🖼️  iframe元素: {effect['iframeCount']}个")
    logger.info(f"  🪟 弹窗元素: {effect['popupCount']}个")
    logger.info(f"  ▶️  播放中视频: {effect['hasPlayingVideo']}")

if __name__ == "__main__":
    asyncio.run(test_corrected_xpath_logic())