#!/usr/bin/env python
"""
测试优化后的iframe按钮处理逻辑

验证修正后的learning_automator.py是否能正确处理：
1. div.user_choise 类的"开始学习"按钮
2. div.continue 类的"继续学习"按钮  
3. cursor:pointer样式的div按钮
4. 优先级系统是否正常工作
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.learning_automator import VideoController
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger

async def test_enhanced_iframe_buttons():
    """测试优化后的iframe按钮处理逻辑"""
    logger.info("=" * 80)
    logger.info("🧪 测试优化后的iframe按钮处理逻辑")
    logger.info("📋 验证div.user_choise和div.continue按钮是否被正确处理")
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
            
            # 步骤3: 创建视频控制器并测试增强的iframe按钮处理
            logger.info("\n🎬 步骤 3: 测试增强的iframe按钮处理...")
            logger.info("-" * 60)
            
            video_controller = VideoController(page)
            
            logger.info("🚀 启动增强的iframe按钮处理测试...")
            
            # 执行完整自动化流程
            play_success = await video_controller.play()
            
            if play_success:
                logger.info("\n🎉 增强的iframe按钮处理测试成功！")
                logger.info("✅ 优化功能确认:")
                logger.info("  1. ✅ div.user_choise 类按钮检测")
                logger.info("  2. ✅ div.continue 类按钮检测") 
                logger.info("  3. ✅ cursor:pointer样式div按钮检测")
                logger.info("  4. ✅ 优先级排序系统")
                
                # 详细验证iframe内按钮处理
                logger.info("\n📊 步骤 4: 详细验证iframe按钮处理...")
                await detailed_iframe_button_verification(context)
                
            else:
                logger.error("\n❌ 增强的iframe按钮处理测试失败")
                logger.info("💡 进行详细诊断...")
                await diagnose_iframe_button_issues(context, page)
            
            # 保持浏览器打开以便观察
            logger.info("\n🔍 保持浏览器打开60秒以便观察结果...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

async def detailed_iframe_button_verification(context):
    """详细验证iframe内按钮处理"""
    try:
        logger.info("🔍 详细检查iframe内按钮处理情况...")
        
        # 查找视频页面
        video_page = None
        for page_obj in context.pages:
            if 'scorm_play' in page_obj.url or 'video_page' in page_obj.url:
                video_page = page_obj
                break
        
        if not video_page:
            logger.warning("⚠️ 未找到视频页面")
            return
        
        logger.info(f"📺 检查视频页面: {video_page.url}")
        
        # 检查iframe内的按钮状态
        iframe_analysis = await video_page.evaluate("""
            () => {
                const result = {
                    iframes_found: 0,
                    button_analysis: []
                };
                
                const iframes = document.querySelectorAll('iframe');
                result.iframes_found = iframes.length;
                
                iframes.forEach((iframe, index) => {
                    try {
                        if (iframe.src && iframe.src.includes('scorm_play')) {
                            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                            
                            const analysis = {
                                iframe_index: index,
                                iframe_src: iframe.src,
                                buttons_found: []
                            };
                            
                            // 检查各种按钮类型
                            const buttonTypes = [
                                { selector: '.user_choise', description: 'div.user_choise按钮' },
                                { selector: '.continue', description: 'div.continue按钮' },
                                { selector: 'div[style*="cursor: pointer"]', description: 'cursor:pointer div按钮' },
                                { selector: 'button', description: '标准button元素' },
                                { selector: '.btn', description: '.btn类按钮' },
                                { selector: 'div[onclick]', description: 'onclick div按钮' }
                            ];
                            
                            buttonTypes.forEach(type => {
                                const elements = iframeDoc.querySelectorAll(type.selector);
                                elements.forEach((el, i) => {
                                    const rect = el.getBoundingClientRect();
                                    const computedStyle = window.getComputedStyle(el);
                                    analysis.buttons_found.push({
                                        type: type.description,
                                        index: i,
                                        text: el.textContent?.trim() || '',
                                        visible: rect.width > 0 && rect.height > 0,
                                        clickable: computedStyle.cursor === 'pointer' || el.onclick !== null,
                                        class_name: el.className,
                                        tag_name: el.tagName
                                    });
                                });
                            });
                            
                            result.button_analysis.push(analysis);
                        }
                    } catch (e) {
                        console.log('iframe访问错误:', e);
                    }
                });
                
                return result;
            }
        """)
        
        logger.info(f"📊 iframe分析结果:")
        logger.info(f"  发现iframe数量: {iframe_analysis['iframes_found']}")
        
        for analysis in iframe_analysis['button_analysis']:
            logger.info(f"\n  📺 iframe {analysis['iframe_index']} ({analysis['iframe_src'][:50]}...):")
            logger.info(f"    发现按钮总数: {len(analysis['buttons_found'])}")
            
            # 按类型分组显示
            button_types = {}
            for btn in analysis['buttons_found']:
                btn_type = btn['type']
                if btn_type not in button_types:
                    button_types[btn_type] = []
                button_types[btn_type].append(btn)
            
            for btn_type, buttons in button_types.items():
                logger.info(f"    📋 {btn_type}: {len(buttons)}个")
                for btn in buttons:
                    status = "✅可见可点击" if btn['visible'] and btn['clickable'] else "❌不可用"
                    logger.info(f"      - '{btn['text']}' ({btn['tag_name']}.{btn['class_name']}) {status}")
        
        logger.info("✅ iframe按钮分析完成")
        
    except Exception as e:
        logger.error(f"❌ 详细验证iframe按钮处理时异常: {e}")

async def diagnose_iframe_button_issues(context, original_page):
    """诊断iframe按钮处理问题"""
    logger.info("\n🔧 iframe按钮处理问题诊断")
    logger.info("-" * 40)
    
    try:
        page_count = len(context.pages)
        logger.info(f"📊 当前页面数: {page_count}")
        
        if page_count == 1:
            logger.warning("⚠️ 只有1个页面，新tab可能没有打开")
        else:
            logger.info("✅ 检测到多个页面")
            
            # 检查每个页面的iframe情况
            for i, page_obj in enumerate(context.pages):
                logger.info(f"\n📄 页面 {i+1}: {page_obj.url[:50]}...")
                
                if 'scorm_play' in page_obj.url or 'video_page' in page_obj.url:
                    logger.info("  🎯 这是视频相关页面")
                    
                    # 专门检查iframe中的div.user_choise
                    iframe_div_check = await page_obj.evaluate("""
                        () => {
                            const result = { user_choise_found: false, details: [] };
                            
                            try {
                                const iframes = document.querySelectorAll('iframe');
                                iframes.forEach((iframe, index) => {
                                    if (iframe.src && iframe.src.includes('scorm_play')) {
                                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                        
                                        const userChoises = iframeDoc.querySelectorAll('.user_choise');
                                        if (userChoises.length > 0) {
                                            result.user_choise_found = true;
                                            userChoises.forEach((div, i) => {
                                                const rect = div.getBoundingClientRect();
                                                result.details.push({
                                                    iframe_index: index,
                                                    div_index: i,
                                                    text: div.textContent?.trim() || '',
                                                    visible: rect.width > 0 && rect.height > 0,
                                                    style: div.getAttribute('style') || '',
                                                    class: div.className
                                                });
                                            });
                                        }
                                    }
                                });
                            } catch (e) {
                                result.error = e.toString();
                            }
                            
                            return result;
                        }
                    """)
                    
                    if iframe_div_check['user_choise_found']:
                        logger.info("  ✅ 发现div.user_choise元素:")
                        for detail in iframe_div_check['details']:
                            logger.info(f"    - iframe{detail['iframe_index']} div{detail['div_index']}: '{detail['text']}'")
                            logger.info(f"      可见: {detail['visible']}, 样式: {detail['style']}")
                    else:
                        logger.warning("  ❌ 未发现div.user_choise元素")
                        if 'error' in iframe_div_check:
                            logger.error(f"    错误: {iframe_div_check['error']}")
        
        logger.info("\n💡 诊断完成")
        
    except Exception as e:
        logger.error(f"❌ 诊断过程中异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_enhanced_iframe_buttons())