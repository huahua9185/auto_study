#!/usr/bin/env python
"""
测试新的针对性视频播放和弹窗处理逻辑

基于网站实际页面结构分析后编写的测试
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.learning_automator import VideoController
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_targeted_video_logic():
    """测试针对性视频处理逻辑"""
    logger.info("=" * 60)
    logger.info("测试针对性视频播放和弹窗处理逻辑")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 首先登录到系统
            logger.info("步骤 1: 登录到系统...")
            auto_login = AutoLogin(page)
            username = "640302198607120020"
            password = "My2062660"  # 正确的密码
            
            success = await auto_login.login(username, password)
            if not success:
                logger.error("❌ 登录失败，无法继续测试")
                return
            
            logger.info("✅ 登录成功")
            
            # 导航到课程页面
            logger.info("步骤 2: 导航到课程页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 创建视频控制器
            logger.info("步骤 3: 创建视频控制器...")
            video_controller = VideoController(page)
            
            # 查找第一个课程并尝试点击
            logger.info("步骤 4: 查找并点击第一个课程...")
            course_clicked = await page.evaluate("""
                () => {
                    // 根据页面结构分析，查找"继续学习"或"开始学习"按钮
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
            
            if course_clicked['clicked']:
                logger.info(f"✅ 成功点击课程按钮: {course_clicked['buttonInfo']}")
                await asyncio.sleep(2)
                
                # 测试新的视频播放逻辑
                logger.info("步骤 5: 测试新的视频播放逻辑...")
                logger.info("-" * 40)
                
                play_success = await video_controller.play()
                
                if play_success:
                    logger.info("🎉 针对性视频播放逻辑测试成功！")
                    logger.info("✅ 所有处理步骤都正常工作：")
                    logger.info("  1. ✅ 学习确认弹窗处理")
                    logger.info("  2. ✅ 登录弹窗处理")  
                    logger.info("  3. ✅ 视频查找和播放")
                    
                    # 监控播放状态
                    logger.info("步骤 6: 监控播放状态...")
                    for i in range(5):
                        current_time = await video_controller.get_current_time()
                        duration = await video_controller.get_duration()
                        logger.info(f"播放进度: {current_time:.1f}s / {duration:.1f}s")
                        await asyncio.sleep(2)
                        
                else:
                    logger.error("❌ 针对性视频播放逻辑测试失败")
                    logger.info("可能的原因：")
                    logger.info("• 登录弹窗处理失败")
                    logger.info("• 视频播放器未找到")
                    logger.info("• 页面结构发生变化")
                    
            else:
                logger.error("❌ 未找到课程按钮，无法开始测试")
                logger.info("页面可能还在加载或结构发生了变化")
            
            # 保持浏览器打开以便观察
            logger.info("保持浏览器打开20秒以便观察...")
            await asyncio.sleep(20)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("针对性视频处理逻辑测试完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_targeted_video_logic())