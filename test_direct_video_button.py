#!/usr/bin/env python
"""
直接测试视频按钮点击行为

测试主程序框架下VideoController的按钮点击优先级是否生效
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.auto_study.main import AutoStudyApp
from src.auto_study.utils.logger import logger

async def test_direct_video_button():
    """直接测试视频按钮点击"""
    logger.info("=" * 80)
    logger.info("🎯 直接测试主程序框架下的视频按钮点击")
    logger.info("📋 验证修正后的按钮优先级是否生效")
    logger.info("=" * 80)
    
    app = None
    try:
        # 初始化应用
        logger.info("\n🚀 初始化应用...")
        app = AutoStudyApp()
        
        if not await app.initialize():
            logger.error("❌ 应用初始化失败")
            return
        
        # 登录
        logger.info("\n🔐 登录...")
        if not await app.login():
            logger.error("❌ 登录失败")
            return
        
        logger.info("✅ 登录成功")
        
        # 直接导航到课程列表
        logger.info("\n📚 导航到课程列表...")
        page = await app.browser_manager.get_page()
        await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)
        
        logger.info(f"📍 当前页面: {page.url}")
        
        # 直接测试VideoController的play方法
        logger.info("\n🎬 测试VideoController的play方法...")
        video_controller = app.learning_automator.video_controller
        
        logger.info("🚀 调用video_controller.play()...")
        play_result = await video_controller.play()
        
        if play_result:
            logger.info("\n🎉 测试成功！")
            logger.info("✅ 主程序框架下的VideoController正常工作:")
            
            # 检查所有打开的页面
            context = page.context
            pages = context.pages
            logger.info(f"\n📄 当前打开的页面数: {len(pages)}")
            
            for i, p in enumerate(pages):
                logger.info(f"  页面{i+1}: {p.url[:60]}...")
                
                # 检查是否有视频页面
                if 'video_page' in p.url:
                    logger.info("    ✅ 这是视频页面")
                    
                    # 检查视频播放状态
                    video_state = await p.evaluate("""
                        () => {
                            const result = { has_video: false, is_playing: false };
                            
                            // 检查iframe内的视频
                            const iframes = document.querySelectorAll('iframe[src*="scorm_play"]');
                            if (iframes.length > 0) {
                                try {
                                    const iframe = iframes[0];
                                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                    const videos = iframeDoc.querySelectorAll('video');
                                    
                                    if (videos.length > 0) {
                                        result.has_video = true;
                                        result.is_playing = !videos[0].paused;
                                    }
                                } catch (e) {
                                    // 跨域限制
                                }
                            }
                            
                            return result;
                        }
                    """)
                    
                    if video_state['has_video']:
                        logger.info(f"    🎬 视频状态: {'播放中' if video_state['is_playing'] else '暂停'}")
                    
        else:
            logger.warning("\n⚠️ play方法返回False")
            logger.info("请检查日志中的详细信息")
        
        # 保持浏览器打开观察
        logger.info("\n👁️ 保持浏览器打开60秒以便观察...")
        await asyncio.sleep(60)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if app:
            logger.info("\n🧹 清理资源...")
            await app.cleanup()

if __name__ == "__main__":
    asyncio.run(test_direct_video_button())