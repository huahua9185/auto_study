#!/usr/bin/env python
"""
确保进入视频页面后分析特定xpath的"继续学习"div

先通过手动方式确保进入视频页面，再查找xpath: /html/body/div/div[3]/div[2]
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json

async def analyze_video_page_xpath():
    """确保进入视频页面后分析xpath元素"""
    logger.info("=" * 60)
    logger.info("确保进入视频页面后分析特定xpath")
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
            
            # 更加智能的方式点击课程进入视频页面
            logger.info("步骤 3: 智能点击课程进入视频页面...")
            
            # 先分析当前页面的所有课程和按钮
            course_analysis = await page.evaluate("""
                () => {
                    const result = {
                        courses: [],
                        buttons: []
                    };
                    
                    // 查找课程条目（更精确的查找）
                    const courseSelectors = [
                        '.el-collapse-item__content .gj_top_list_box li',
                        '.course-item', 
                        'li:has(.btn)',
                        '.gj_top_list_box li'
                    ];
                    
                    courseSelectors.forEach(selector => {
                        const courses = document.querySelectorAll(selector);
                        courses.forEach((course, index) => {
                            const btn = course.querySelector('.btn, button');
                            if (btn && btn.textContent.includes('继续学习')) {
                                const title = course.querySelector('.title, h3, h4, .course-title')?.textContent || '';
                                result.courses.push({
                                    index: index,
                                    title: title.trim(),
                                    buttonText: btn.textContent.trim(),
                                    hasVideo: title.includes('视频') || title.includes('播放'),
                                    selector: selector
                                });
                            }
                        });
                    });
                    
                    // 查找所有继续学习按钮
                    const buttons = document.querySelectorAll('div.btn, .btn');
                    buttons.forEach((btn, index) => {
                        if (btn.textContent.includes('继续学习')) {
                            result.buttons.push({
                                index: index,
                                text: btn.textContent.trim(),
                                className: btn.className,
                                parentInfo: {
                                    tagName: btn.parentElement?.tagName,
                                    className: btn.parentElement?.className,
                                    text: btn.parentElement?.textContent?.substring(0, 100)
                                }
                            });
                        }
                    });
                    
                    return result;
                }
            """)
            
            logger.info(f"找到 {len(course_analysis['courses'])} 个课程条目")
            logger.info(f"找到 {len(course_analysis['buttons'])} 个继续学习按钮")
            
            # 优先点击有视频关键词的课程
            video_course = None
            for course in course_analysis['courses']:
                if course['hasVideo']:
                    video_course = course
                    break
            
            if not video_course and course_analysis['courses']:
                video_course = course_analysis['courses'][0]  # 选择第一个课程
            
            if video_course:
                logger.info(f"选择课程: {video_course['title']} (索引: {video_course['index']})")
                
                # 尝试多种方式点击这个特定课程的按钮
                clicked = False
                
                # 方法1: 通过课程标题定位并点击按钮
                try:
                    success = await page.evaluate(f"""
                        () => {{
                            const courseTitle = '{video_course['title'][:20]}';  // 使用标题前20个字符匹配
                            const courseElements = document.querySelectorAll('li, .course-item');
                            
                            for (let course of courseElements) {{
                                const titleText = course.textContent || '';
                                if (titleText.includes(courseTitle)) {{
                                    const btn = course.querySelector('.btn');
                                    if (btn && btn.textContent.includes('继续学习')) {{
                                        btn.click();
                                        return true;
                                    }}
                                }}
                            }}
                            return false;
                        }}
                    """)
                    
                    if success:
                        logger.info("✅ 方法1成功 - 通过课程标题定位点击")
                        clicked = True
                    else:
                        logger.warning("❌ 方法1失败")
                        
                except Exception as e:
                    logger.warning(f"❌ 方法1异常: {e}")
                
                # 如果方法1失败，尝试方法2: 点击第N个继续学习按钮
                if not clicked:
                    try:
                        success = await page.evaluate(f"""
                            () => {{
                                const buttons = document.querySelectorAll('.btn');
                                let count = 0;
                                for (let btn of buttons) {{
                                    if (btn.textContent.includes('继续学习')) {{
                                        if (count === {video_course['index']}) {{
                                            btn.click();
                                            return true;
                                        }}
                                        count++;
                                    }}
                                }}
                                return false;
                            }}
                        """)
                        
                        if success:
                            logger.info(f"✅ 方法2成功 - 点击第{video_course['index']}个按钮")
                            clicked = True
                        else:
                            logger.warning("❌ 方法2失败")
                            
                    except Exception as e:
                        logger.warning(f"❌ 方法2异常: {e}")
                
                if clicked:
                    logger.info("等待页面跳转到视频页面...")
                    await asyncio.sleep(8)  # 给更多时间让页面跳转和加载
                    
                    current_url = page.url
                    logger.info(f"当前URL: {current_url}")
                    
                    # 检查是否真的跳转到了视频页面
                    if current_url != "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275":
                        logger.info("✅ 成功跳转到新页面，现在查找目标xpath...")
                        
                        # 等待新页面完全加载
                        await page.wait_for_load_state('networkidle', timeout=15000)
                        await asyncio.sleep(5)
                        
                        # 现在分析目标xpath
                        await analyze_target_xpath(page)
                        
                    else:
                        logger.warning("❌ 页面未跳转，仍在课程列表页")
                        
                        # 尝试等待页面内容变化
                        logger.info("等待页面内容可能的异步加载...")
                        await asyncio.sleep(10)
                        await analyze_target_xpath(page)
                else:
                    logger.error("❌ 所有点击方法都失败了")
            else:
                logger.error("❌ 未找到可点击的课程")
            
            # 保持浏览器打开以便手动分析
            logger.info("\\n保持浏览器打开60秒以便手动分析...")
            logger.info("请手动点击课程并观察'继续学习'弹窗的出现")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()
    
    logger.info("\\n" + "=" * 60)
    logger.info("视频页面xpath分析完成")
    logger.info("=" * 60)

async def analyze_target_xpath(page):
    """分析目标xpath元素"""
    target_xpath = "/html/body/div/div[3]/div[2]"
    
    logger.info("\\n" + "=" * 40)
    logger.info("分析目标xpath元素")
    logger.info("=" * 40)
    
    # 首先检查页面上的div结构
    page_structure = await page.evaluate("""
        () => {
            const result = {
                bodyChildren: [],
                divStructure: {}
            };
            
            // 分析body下的直接子元素
            const bodyChildren = Array.from(document.body.children);
            result.bodyChildren = bodyChildren.map((child, index) => ({
                index: index,
                tagName: child.tagName,
                className: child.className,
                id: child.id,
                childCount: child.children.length
            }));
            
            // 分析可能的div结构
            const firstDiv = document.querySelector('body > div');
            if (firstDiv && firstDiv.children.length > 2) {
                const thirdChild = firstDiv.children[2]; // div[3]
                if (thirdChild && thirdChild.children.length > 1) {
                    const secondGrandChild = thirdChild.children[1]; // div[2]
                    if (secondGrandChild) {
                        result.divStructure = {
                            exists: true,
                            tagName: secondGrandChild.tagName,
                            className: secondGrandChild.className,
                            id: secondGrandChild.id,
                            text: secondGrandChild.textContent?.substring(0, 200),
                            innerHTML: secondGrandChild.innerHTML?.substring(0, 500),
                            visible: secondGrandChild.offsetWidth > 0 && secondGrandChild.offsetHeight > 0,
                            rect: {
                                x: secondGrandChild.getBoundingClientRect().x,
                                y: secondGrandChild.getBoundingClientRect().y,
                                width: secondGrandChild.getBoundingClientRect().width,
                                height: secondGrandChild.getBoundingClientRect().height
                            }
                        };
                    }
                }
            }
            
            return result;
        }
    """)
    
    logger.info(f"Body直接子元素数量: {len(page_structure['bodyChildren'])}")
    for i, child in enumerate(page_structure['bodyChildren']):
        logger.info(f"  {i}: {child['tagName']}.{child['className']} (子元素:{child['childCount']}个)")
    
    if page_structure['divStructure'].get('exists'):
        logger.info(f"\\n✅ 找到目标路径元素!")
        div_info = page_structure['divStructure']
        logger.info(f"  标签: {div_info['tagName']}")
        logger.info(f"  类名: {div_info['className']}")
        logger.info(f"  ID: {div_info['id']}")
        logger.info(f"  可见: {div_info['visible']}")
        logger.info(f"  位置: ({div_info['rect']['x']}, {div_info['rect']['y']})")
        logger.info(f"  大小: {div_info['rect']['width']} x {div_info['rect']['height']}")
        logger.info(f"  文本: '{div_info['text']}'")
        
        if '继续学习' in div_info['text'] or '开始学习' in div_info['text']:
            logger.info("🎯 这就是目标的'继续学习'弹窗!")
            
            # 尝试点击
            try:
                await page.locator(f"xpath={target_xpath}").click()
                logger.info("✅ 成功点击目标xpath元素")
                
                await asyncio.sleep(3)
                new_url = page.url
                logger.info(f"点击后URL: {new_url}")
                
            except Exception as e:
                logger.error(f"❌ 点击目标xpath失败: {e}")
        else:
            logger.warning("⚠️ 元素存在但不包含'继续学习'文本")
    else:
        logger.warning("❌ 未找到目标路径的元素结构")
        
        # 查找所有包含"继续学习"的元素，帮助定位正确的xpath
        continue_elements = await page.evaluate("""
            () => {
                const result = [];
                const allElements = document.querySelectorAll('*');
                
                allElements.forEach(el => {
                    const text = el.textContent || '';
                    if ((text.includes('继续学习') || text.includes('开始学习')) && text.length < 100) {
                        // 生成xpath
                        let xpath = '';
                        let current = el;
                        while (current && current.nodeType === Node.ELEMENT_NODE) {
                            let selector = current.nodeName.toLowerCase();
                            if (current.id) {
                                selector += `[@id='${current.id}']`;
                            } else {
                                let sibling = current;
                                let nth = 1;
                                while (sibling = sibling.previousElementSibling) {
                                    if (sibling.nodeName.toLowerCase() === current.nodeName.toLowerCase()) {
                                        nth++;
                                    }
                                }
                                if (nth > 1) {
                                    selector += `[${nth}]`;
                                }
                            }
                            xpath = '/' + selector + xpath;
                            current = current.parentElement;
                        }
                        xpath = '/html' + xpath;
                        
                        result.push({
                            text: text.trim(),
                            tagName: el.tagName,
                            className: el.className,
                            xpath: xpath,
                            visible: el.offsetWidth > 0 && el.offsetHeight > 0
                        });
                    }
                });
                
                return result;
            }
        """)
        
        logger.info(f"\\n找到 {len(continue_elements)} 个包含'继续学习'的元素:")
        for i, el in enumerate(continue_elements[:5]):  # 只显示前5个
            logger.info(f"  {i+1}. {el['tagName']}.{el['className']} - '{el['text'][:50]}'")
            logger.info(f"      xpath: {el['xpath']}")
            logger.info(f"      可见: {el['visible']}")

if __name__ == "__main__":
    asyncio.run(analyze_video_page_xpath())