#!/usr/bin/env python
"""
测试完整的视频自动化播放功能

验证修正后的learning_automator.py是否能正确处理：
1. 新tab中打开的视频页面
2. iframe内的视频播放器
3. 完整的自动化流程
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.learning_automator import VideoController
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_complete_video_automation():
    """测试完整的视频自动化功能"""
    logger.info("=" * 80)
    logger.info("🧪 测试完整的视频自动化播放功能")
    logger.info("📋 验证所有修正后的逻辑是否正常工作")
    logger.info("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            # 创建浏览器上下文（支持多tab）
            context = await browser.new_context()
            page = await context.new_page()
            
            # 步骤1: 登录
            logger.info("\n🔐 步骤 1: 自动登录...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败，测试终止")
                return
            
            logger.info("✅ 登录成功")
            
            # 步骤2: 进入课程列表
            logger.info("\n📚 步骤 2: 进入课程列表页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            logger.info(f"📍 当前在课程列表页面: {page.url}")
            
            # 步骤3: 创建视频控制器并测试自动播放
            logger.info("\n🎬 步骤 3: 创建视频控制器并启动自动播放...")
            logger.info("-" * 60)
            
            video_controller = VideoController(page)
            
            # 这里会执行完整的自动化流程：
            # 1. 点击"继续学习" -> 在新tab打开视频页面
            # 2. 检测并切换到新tab
            # 3. 处理iframe视频播放器
            # 4. 启动视频播放
            logger.info("🚀 启动完整自动化视频播放流程...")
            
            play_success = await video_controller.play()
            
            if play_success:
                logger.info("\n🎉 自动化视频播放测试成功！")
                logger.info("✅ 所有功能正常工作:")
                logger.info("  1. ✅ 自动点击'继续学习'按钮")
                logger.info("  2. ✅ 检测并切换到新tab视频页面")
                logger.info("  3. ✅ 识别并处理iframe视频播放器")
                logger.info("  4. ✅ 成功启动视频播放")
                
                # 验证播放状态
                logger.info("\n📊 步骤 4: 验证视频播放状态...")
                await verify_video_playback(context)
                
            else:
                logger.error("\n❌ 自动化视频播放测试失败")
                logger.info("💡 让我们进行问题诊断...")
                await diagnose_issues(context, page)
            
            # 保持浏览器打开以便观察
            logger.info("\n🔍 保持浏览器打开90秒以便观察播放效果...")
            await asyncio.sleep(90)
            
        finally:
            await browser.close()

async def verify_video_playback(context):
    """验证视频播放状态"""
    try:
        logger.info("🔍 检查所有打开的页面中的视频状态...")
        
        all_pages = context.pages
        logger.info(f"📊 总页面数: {len(all_pages)}")
        
        for i, page_obj in enumerate(all_pages):
            logger.info(f"\n📄 页面 {i+1}: {page_obj.url}")
            
            # 检查每个页面的视频状态
            video_status = await check_page_video_status(page_obj)
            
            if video_status['has_videos']:
                logger.info(f"  🎬 发现 {video_status['video_count']} 个视频")
                for j, video in enumerate(video_status['videos']):
                    status = "▶️ 播放中" if not video['paused'] else "⏸️ 暂停"
                    logger.info(f"    视频{j+1}: {status} ({video['current_time']:.1f}s / {video['duration']:.1f}s)")
            
            if video_status['has_iframes']:
                logger.info(f"  🖼️ 发现 {video_status['iframe_count']} 个iframe")
                for iframe_info in video_status['iframes']:
                    if 'scorm_play' in iframe_info['src']:
                        logger.info(f"    📺 视频播放器iframe: {iframe_info['src'][:50]}...")
                    
        logger.info("✅ 视频状态检查完成")
        
    except Exception as e:
        logger.error(f"❌ 验证视频播放状态时异常: {e}")

async def check_page_video_status(page_obj):
    """检查单个页面的视频状态"""
    try:
        status = await page_obj.evaluate("""
            () => {
                const result = {
                    has_videos: false,
                    video_count: 0,
                    videos: [],
                    has_iframes: false,
                    iframe_count: 0,
                    iframes: []
                };
                
                // 检查直接的视频元素
                const videos = document.querySelectorAll('video');
                result.video_count = videos.length;
                result.has_videos = videos.length > 0;
                
                videos.forEach((video, index) => {
                    result.videos.push({
                        index: index,
                        paused: video.paused,
                        current_time: video.currentTime || 0,
                        duration: video.duration || 0,
                        ready_state: video.readyState
                    });
                });
                
                // 检查iframe
                const iframes = document.querySelectorAll('iframe');
                result.iframe_count = iframes.length;
                result.has_iframes = iframes.length > 0;
                
                iframes.forEach((iframe, index) => {
                    const rect = iframe.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        result.iframes.push({
                            index: index,
                            src: iframe.src || '',
                            visible: true
                        });
                    }
                });
                
                return result;
            }
        """)
        
        return status
        
    except Exception as e:
        logger.warning(f"⚠️ 检查页面 {page_obj.url} 时出错: {e}")
        return {
            'has_videos': False,
            'video_count': 0,
            'videos': [],
            'has_iframes': False,
            'iframe_count': 0,
            'iframes': []
        }

async def diagnose_issues(context, original_page):
    """诊断可能的问题"""
    logger.info("\n🔧 问题诊断模式")
    logger.info("-" * 40)
    
    try:
        # 检查页面数量
        page_count = len(context.pages)
        logger.info(f"📊 当前页面数: {page_count}")
        
        if page_count == 1:
            logger.warning("⚠️ 只有1个页面，可能新tab没有打开")
            logger.info("💡 建议检查点击逻辑或手动点击验证")
            
            # 检查原页面上的按钮
            button_info = await original_page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('div.btn');
                    const result = [];
                    buttons.forEach((btn, index) => {
                        const text = btn.textContent || '';
                        if (text.includes('继续学习') || text.includes('开始学习')) {
                            const rect = btn.getBoundingClientRect();
                            result.push({
                                index: index,
                                text: text.trim(),
                                visible: rect.width > 0 && rect.height > 0
                            });
                        }
                    });
                    return result;
                }
            """)
            
            logger.info(f"🔘 发现 {len(button_info)} 个'继续学习'按钮:")
            for btn in button_info:
                logger.info(f"  按钮{btn['index']}: '{btn['text']}' (可见: {btn['visible']})")
        
        elif page_count > 1:
            logger.info("✅ 检测到多个页面，新tab已打开")
            
            # 检查每个页面
            for i, page_obj in enumerate(context.pages):
                logger.info(f"\n📄 页面 {i+1}:")
                logger.info(f"  URL: {page_obj.url}")
                logger.info(f"  标题: {await page_obj.title()}")
                
                if 'video_page' in page_obj.url:
                    logger.info("  🎯 这是视频页面")
                    
                    # 检查iframe
                    iframe_check = await page_obj.evaluate("""
                        () => {
                            const iframes = document.querySelectorAll('iframe');
                            return Array.from(iframes).map(iframe => ({
                                src: iframe.src,
                                class: iframe.className,
                                visible: iframe.getBoundingClientRect().width > 0
                            }));
                        }
                    """)
                    
                    logger.info(f"  🖼️ iframe数量: {len(iframe_check)}")
                    for j, iframe in enumerate(iframe_check):
                        logger.info(f"    iframe{j+1}: {iframe['src'][:50]}... (class: {iframe['class']})")
                        if 'scorm_play' in iframe['src']:
                            logger.info("      ✅ 这是视频播放器iframe")
        
        logger.info("\n💡 诊断完成")
        
    except Exception as e:
        logger.error(f"❌ 诊断过程中异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_complete_video_automation())