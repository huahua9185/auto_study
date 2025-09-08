#!/usr/bin/env python
"""
分析特定xpath的"继续学习"div元素

xpath: /html/body/div/div[3]/div[2]
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json

async def analyze_specific_xpath_div():
    """分析特定xpath的div元素"""
    logger.info("=" * 60)
    logger.info("分析特定xpath的'继续学习'div元素")
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
            
            # 点击"继续学习"按钮进入视频页面
            logger.info("步骤 3: 点击继续学习按钮进入视频页面...")
            course_clicked = await page.evaluate("""
                () => {
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
            
            if not course_clicked['clicked']:
                logger.error("❌ 未找到继续学习按钮")
                return
            
            logger.info(f"✅ 成功点击按钮: {course_clicked['buttonInfo']}")
            await asyncio.sleep(5)  # 等待页面变化
            
            # 分析特定xpath元素
            logger.info("步骤 4: 分析特定xpath元素...")
            logger.info("=" * 40)
            
            # 首先检查这个xpath是否存在
            target_xpath = "/html/body/div/div[3]/div[2]"
            
            xpath_analysis = await page.evaluate(f"""
                (xpath) => {{
                    const result = {{
                        exists: false,
                        element: null,
                        visible: false,
                        clickable: false,
                        text: '',
                        properties: {{}},
                        parentAnalysis: {{}},
                        siblingAnalysis: []
                    }};
                    
                    // 使用document.evaluate查找xpath元素
                    const xpathResult = document.evaluate(
                        xpath,
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    );
                    
                    const element = xpathResult.singleNodeValue;
                    
                    if (element) {{
                        result.exists = true;
                        result.text = element.textContent || '';
                        
                        const rect = element.getBoundingClientRect();
                        const style = window.getComputedStyle(element);
                        
                        result.visible = rect.width > 0 && rect.height > 0 && 
                                        style.display !== 'none' && 
                                        style.visibility !== 'hidden' && 
                                        style.opacity !== '0';
                        
                        result.clickable = element.onclick !== null || 
                                         element.getAttribute('onclick') !== null ||
                                         style.cursor === 'pointer';
                        
                        result.properties = {{
                            tagName: element.tagName,
                            className: element.className,
                            id: element.id,
                            innerHTML: element.innerHTML.substring(0, 500),
                            rect: {{
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            }},
                            style: {{
                                display: style.display,
                                visibility: style.visibility,
                                opacity: style.opacity,
                                cursor: style.cursor,
                                zIndex: style.zIndex,
                                position: style.position
                            }},
                            onclick: element.getAttribute('onclick'),
                            hasEventListeners: !!element._listeners // 检查是否有事件监听器
                        }};
                        
                        // 分析父元素
                        if (element.parentElement) {{
                            const parent = element.parentElement;
                            const parentRect = parent.getBoundingClientRect();
                            const parentStyle = window.getComputedStyle(parent);
                            
                            result.parentAnalysis = {{
                                tagName: parent.tagName,
                                className: parent.className,
                                id: parent.id,
                                visible: parentRect.width > 0 && parentRect.height > 0 && 
                                        parentStyle.display !== 'none' && 
                                        parentStyle.visibility !== 'hidden',
                                text: parent.textContent?.substring(0, 200)
                            }};
                        }}
                        
                        // 分析兄弟元素
                        if (element.parentElement) {{
                            const siblings = Array.from(element.parentElement.children);
                            result.siblingAnalysis = siblings.map(sibling => ({{
                                tagName: sibling.tagName,
                                className: sibling.className,
                                text: sibling.textContent?.substring(0, 100),
                                isCurrent: sibling === element
                            }}));
                        }}
                    }}
                    
                    return result;
                }}
            """, target_xpath)
            
            logger.info(f"XPath元素存在: {xpath_analysis['exists']}")
            
            if xpath_analysis['exists']:
                logger.info(f"✅ 找到目标xpath元素!")
                logger.info(f"  标签: {xpath_analysis['properties']['tagName']}")
                logger.info(f"  类名: {xpath_analysis['properties']['className']}")
                logger.info(f"  ID: {xpath_analysis['properties']['id']}")
                logger.info(f"  文本: '{xpath_analysis['text'][:100]}'")
                logger.info(f"  可见: {xpath_analysis['visible']}")
                logger.info(f"  可点击: {xpath_analysis['clickable']}")
                logger.info(f"  位置: ({xpath_analysis['properties']['rect']['x']}, {xpath_analysis['properties']['rect']['y']})")
                logger.info(f"  大小: {xpath_analysis['properties']['rect']['width']} x {xpath_analysis['properties']['rect']['height']}")
                logger.info(f"  显示样式: {xpath_analysis['properties']['style']['display']}")
                logger.info(f"  可见性: {xpath_analysis['properties']['style']['visibility']}")
                logger.info(f"  透明度: {xpath_analysis['properties']['style']['opacity']}")
                logger.info(f"  鼠标样式: {xpath_analysis['properties']['style']['cursor']}")
                logger.info(f"  onclick属性: {xpath_analysis['properties']['onclick']}")
                
                logger.info(f"\\n父元素分析:")
                logger.info(f"  父元素: {xpath_analysis['parentAnalysis']['tagName']}.{xpath_analysis['parentAnalysis']['className']}")
                logger.info(f"  父元素可见: {xpath_analysis['parentAnalysis']['visible']}")
                
                logger.info(f"\\n兄弟元素分析 (共{len(xpath_analysis['siblingAnalysis'])}个):")
                for i, sibling in enumerate(xpath_analysis['siblingAnalysis'][:5]):
                    current = "👆 当前" if sibling['isCurrent'] else ""
                    logger.info(f"  {i+1}. {sibling['tagName']}.{sibling['className']} - '{sibling['text'][:50]}' {current}")
                
                # 尝试多种方式点击这个元素
                logger.info("\\n步骤 5: 尝试多种方式点击目标元素...")
                
                if xpath_analysis['visible']:
                    # 方法1: 使用Playwright的xpath定位器
                    try:
                        logger.info("方法1: 使用Playwright xpath定位器...")
                        await page.locator(f"xpath={target_xpath}").click()
                        logger.info("✅ 方法1成功")
                        await asyncio.sleep(3)
                        
                        # 检查点击后的效果
                        new_url = page.url
                        logger.info(f"点击后URL: {new_url}")
                        
                    except Exception as e:
                        logger.warning(f"❌ 方法1失败: {e}")
                        
                        # 方法2: 使用JavaScript直接点击xpath元素
                        try:
                            logger.info("方法2: 使用JavaScript xpath点击...")
                            clicked = await page.evaluate(f"""
                                (xpath) => {{
                                    const xpathResult = document.evaluate(
                                        xpath,
                                        document,
                                        null,
                                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                                        null
                                    );
                                    
                                    const element = xpathResult.singleNodeValue;
                                    if (element) {{
                                        element.click();
                                        return true;
                                    }}
                                    return false;
                                }}
                            """, target_xpath)
                            
                            if clicked:
                                logger.info("✅ 方法2成功")
                                await asyncio.sleep(3)
                                new_url = page.url
                                logger.info(f"点击后URL: {new_url}")
                            else:
                                logger.error("❌ 方法2失败: 元素不存在")
                                
                        except Exception as e:
                            logger.error(f"❌ 方法2失败: {e}")
                            
                            # 方法3: 模拟鼠标点击坐标
                            try:
                                logger.info("方法3: 模拟鼠标点击坐标...")
                                rect = xpath_analysis['properties']['rect']
                                center_x = rect['x'] + rect['width'] / 2
                                center_y = rect['y'] + rect['height'] / 2
                                
                                await page.mouse.click(center_x, center_y)
                                logger.info(f"✅ 方法3成功，点击坐标: ({center_x}, {center_y})")
                                await asyncio.sleep(3)
                                new_url = page.url
                                logger.info(f"点击后URL: {new_url}")
                                
                            except Exception as e:
                                logger.error(f"❌ 方法3失败: {e}")
                else:
                    logger.warning("❌ 元素不可见，无法点击")
                    logger.info("尝试让元素可见...")
                    
                    # 尝试滚动到元素位置
                    try:
                        await page.evaluate(f"""
                            (xpath) => {{
                                const xpathResult = document.evaluate(
                                    xpath,
                                    document,
                                    null,
                                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                                    null
                                );
                                
                                const element = xpathResult.singleNodeValue;
                                if (element) {{
                                    element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                }}
                            }}
                        """, target_xpath)
                        
                        await asyncio.sleep(2)
                        logger.info("已滚动到元素位置")
                        
                        # 重新尝试点击
                        await page.locator(f"xpath={target_xpath}").click()
                        logger.info("✅ 滚动后点击成功")
                        
                    except Exception as e:
                        logger.error(f"❌ 滚动后点击失败: {e}")
            else:
                logger.error("❌ 未找到目标xpath元素")
                
                # 分析相似的路径
                logger.info("\\n分析相似路径的元素...")
                similar_paths = [
                    "/html/body/div/div[3]/div[1]",
                    "/html/body/div/div[3]/div[3]", 
                    "/html/body/div/div[2]/div[2]",
                    "/html/body/div/div[4]/div[2]"
                ]
                
                for similar_path in similar_paths:
                    exists = await page.evaluate(f"""
                        (xpath) => {{
                            const xpathResult = document.evaluate(
                                xpath,
                                document,
                                null,
                                XPathResult.FIRST_ORDERED_NODE_TYPE,
                                null
                            );
                            
                            const element = xpathResult.singleNodeValue;
                            if (element) {{
                                return {{
                                    exists: true,
                                    text: element.textContent?.substring(0, 100),
                                    tagName: element.tagName,
                                    className: element.className
                                }};
                            }}
                            return {{ exists: false }};
                        }}
                    """, similar_path)
                    
                    if exists['exists']:
                        logger.info(f"  {similar_path}: {exists['tagName']}.{exists['className']} - '{exists['text']}'")
            
            # 保持浏览器打开以便手动分析
            logger.info("\\n保持浏览器打开30秒以便手动分析...")
            logger.info("请手动检查目标xpath元素的状态和行为")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()
    
    logger.info("\\n" + "=" * 60)
    logger.info("特定xpath元素分析完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(analyze_specific_xpath_div())