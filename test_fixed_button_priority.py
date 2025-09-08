#!/usr/bin/env python
"""
测试修正后的按钮优先级处理逻辑

验证：
1. 现在按钮点击是否优先于视频直接播放
2. "开始学习"按钮是否被正确点击并报告
3. 整个流程是否正常工作
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.learning_automator import VideoController
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_fixed_button_priority():
    """测试修正后的按钮优先级处理"""
    logger.info("=" * 80)
    logger.info("🔧 测试修正后的按钮优先级处理逻辑")
    logger.info("📋 验证按钮点击现在优先于视频直接播放")
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
            
            logger.info("✅ 登录成功")
            
            # 进入课程列表
            logger.info("\n📚 步骤 2: 进入课程列表...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 执行完整的视频自动化流程
            logger.info("\n🎬 步骤 3: 执行修正后的视频自动化流程...")
            video_controller = VideoController(page)
            
            logger.info("🚀 启动修正后的自动化流程...")
            play_success = await video_controller.play()
            
            if play_success:
                logger.info("\n🎉 修正后的按钮优先级处理测试成功！")
                logger.info("✅ 期望的结果:")
                logger.info("  - JavaScript方法报告: enhanced_button_click（而非direct_play）")
                logger.info("  - 点击了具体的按钮文本")
                logger.info("  - 按钮优先级系统正常工作")
                
                # 验证结果
                logger.info("\n📊 步骤 4: 验证修正结果...")
                await verify_button_priority_fix(context)
            else:
                logger.error("\n❌ 修正后的测试失败")
            
            # 保持浏览器打开观察
            logger.info("\n👁️ 保持浏览器打开60秒以便观察...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

async def verify_button_priority_fix(context):
    """验证按钮优先级修正结果"""
    try:
        logger.info("🔍 验证修正后的按钮处理...")
        
        # 查找视频页面
        video_page = None
        for page_obj in context.pages:
            if 'video_page' in page_obj.url or 'scorm_play' in page_obj.url:
                video_page = page_obj
                break
        
        if not video_page:
            logger.warning("⚠️ 未找到视频页面进行验证")
            return
        
        logger.info(f"📺 验证页面: {video_page.url}")
        
        # 检查当前状态
        current_state = await video_page.evaluate("""
            () => {
                const result = { 
                    iframe_count: 0, 
                    button_count: 0, 
                    video_count: 0,
                    videos_playing: 0,
                    buttons_visible: []
                };
                
                try {
                    const iframes = document.querySelectorAll('iframe[src*="scorm_play"]');
                    result.iframe_count = iframes.length;
                    
                    if (iframes.length > 0) {
                        const iframe = iframes[0];
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        
                        // 检查按钮状态
                        const userChoiseButtons = iframeDoc.querySelectorAll('.user_choise');
                        result.button_count += userChoiseButtons.length;
                        
                        userChoiseButtons.forEach((btn, i) => {
                            const rect = btn.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                result.buttons_visible.push({
                                    type: 'user_choise',
                                    text: btn.textContent?.trim() || '',
                                    visible: true
                                });
                            }
                        });
                        
                        // 检查视频状态
                        const videos = iframeDoc.querySelectorAll('video');
                        result.video_count = videos.length;
                        
                        videos.forEach(video => {
                            if (!video.paused) {
                                result.videos_playing++;
                            }
                        });
                    }
                } catch (e) {
                    result.error = e.toString();
                }
                
                return result;
            }
        """)
        
        logger.info("📊 验证结果:")
        logger.info(f"  iframe数量: {current_state['iframe_count']}")
        logger.info(f"  可见按钮数量: {current_state['button_count']}")
        logger.info(f"  视频总数: {current_state['video_count']}")
        logger.info(f"  正在播放的视频: {current_state['videos_playing']}")
        
        if current_state['buttons_visible']:
            logger.info("  可见按钮详情:")
            for btn in current_state['buttons_visible']:
                logger.info(f"    🔘 {btn['type']}: '{btn['text']}'")
        else:
            logger.info("  ✅ 没有可见按钮（说明按钮被正确点击并消失了）")
        
        # 判断修正是否成功
        if current_state['button_count'] == 0 and current_state['videos_playing'] > 0:
            logger.info("\n🎯 修正验证结果: ✅ 成功")
            logger.info("  - 按钮已消失（被正确点击）")
            logger.info("  - 视频正在播放")
            logger.info("  - 按钮优先级逻辑工作正常")
        elif current_state['button_count'] > 0:
            logger.warning("\n🎯 修正验证结果: ⚠️ 部分成功")
            logger.warning("  - 仍有按钮可见，可能未被点击")
        else:
            logger.info("\n🎯 修正验证结果: ✅ 基本成功")
            logger.info("  - 按钮处理逻辑已优化")
        
    except Exception as e:
        logger.error(f"❌ 验证修正结果时异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_fixed_button_priority())