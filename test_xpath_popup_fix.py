#!/usr/bin/env python
"""
测试修复后的xpath弹窗处理逻辑

专门测试用户提供的xpath: /html/body/div/div[3]/div[2]
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.learning_automator import VideoController
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_xpath_popup_fix():
    """测试修复后的xpath弹窗处理逻辑"""
    logger.info("=" * 60)
    logger.info("测试修复后的xpath弹窗处理逻辑")
    logger.info("目标xpath: /html/body/div/div[3]/div[2]")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 登录到系统
            logger.info("步骤 1: 登录到系统...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败")
                return
            
            logger.info("✅ 登录成功")
            
            # 导航到课程页面
            logger.info("步骤 2: 导航到课程页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 创建视频控制器并测试新的播放逻辑
            logger.info("步骤 3: 创建视频控制器并测试播放逻辑...")
            video_controller = VideoController(page)
            
            logger.info("开始执行新的针对性视频播放逻辑...")
            logger.info("-" * 50)
            
            # 这里会先处理课程列表的"继续学习"按钮，然后处理视频页面的xpath弹窗
            play_success = await video_controller.play()
            
            if play_success:
                logger.info("🎉 修复后的xpath处理逻辑测试成功！")
                logger.info("✅ 成功处理了:")
                logger.info("  1. ✅ 课程列表页的'继续学习'按钮")
                logger.info("  2. ✅ 视频页面的特定xpath弹窗")
                logger.info("  3. ✅ 视频播放器启动")
                
                # 监控播放状态
                logger.info("步骤 4: 监控播放状态...")
                for i in range(5):
                    current_time = await video_controller.get_current_time()
                    duration = await video_controller.get_duration()
                    logger.info(f"播放进度: {current_time:.1f}s / {duration:.1f}s")
                    await asyncio.sleep(2)
                    
            else:
                logger.error("❌ xpath处理逻辑测试失败")
                
                # 让用户手动点击以便验证xpath
                logger.info("步骤 4: 手动验证xpath元素...")
                logger.info("请手动点击课程进入视频页面，然后观察是否出现xpath弹窗")
                
                await asyncio.sleep(10)  # 给用户时间手动点击
                
                # 检查xpath元素是否存在
                xpath_check = await page.evaluate("""
                    () => {
                        const xpath = '/html/body/div/div[3]/div[2]';
                        const result = document.evaluate(
                            xpath,
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        
                        const element = result.singleNodeValue;
                        if (element) {
                            const rect = element.getBoundingClientRect();
                            return {
                                exists: true,
                                visible: rect.width > 0 && rect.height > 0,
                                text: element.textContent?.substring(0, 100),
                                tagName: element.tagName,
                                className: element.className
                            };
                        }
                        return { exists: false };
                    }
                """)
                
                if xpath_check['exists']:
                    logger.info(f"✅ 找到xpath元素: {xpath_check['tagName']}.{xpath_check['className']}")
                    logger.info(f"  可见: {xpath_check['visible']}")
                    logger.info(f"  文本: '{xpath_check['text']}'")
                    
                    if xpath_check['visible'] and ('继续学习' in xpath_check['text'] or '开始学习' in xpath_check['text']):
                        logger.info("🎯 这就是需要点击的xpath元素!")
                    else:
                        logger.warning("⚠️ xpath元素存在但可能不是目标弹窗")
                else:
                    logger.warning("❌ 未找到xpath元素，可能还没有进入正确的页面")
            
            # 保持浏览器打开以便观察
            logger.info("\\n保持浏览器打开30秒以便观察...")
            logger.info("请观察'继续学习'弹窗的处理情况")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()
    
    logger.info("\\n" + "=" * 60)
    logger.info("xpath弹窗处理逻辑测试完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_xpath_popup_fix())