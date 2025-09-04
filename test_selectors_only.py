#!/usr/bin/env python3
"""
专门测试选择器的脚本，跳过登录环节
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from playwright.async_api import async_playwright

async def test_selectors():
    """测试课程页面选择器"""
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 直接访问课程页面（可能需要登录，但我们可以看页面结构）
        courses_url = "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275"
        print(f"访问: {courses_url}")
        await page.goto(courses_url)
        await asyncio.sleep(5)
        
        print(f"当前URL: {page.url}")
        title = await page.title()
        print(f"页面标题: {title}")
        
        # 测试基本选择器
        basic_selectors = [
            'div', 'ul', 'li', 
            '.el-collapse', '.el-collapse-item',
            '.gj_top_list_box', 
            '.text_title',
            '.el-progress__text'
        ]
        
        for selector in basic_selectors:
            try:
                count = await page.locator(selector).count()
                print(f"{selector}: {count} 个元素")
                
                # 如果找到了，显示前几个元素的文本
                if count > 0 and count < 10:
                    elements = page.locator(selector)
                    for i in range(min(3, count)):
                        try:
                            text = await elements.nth(i).text_content()
                            if text and len(text.strip()) > 0:
                                text = text.strip()[:100]  # 限制长度
                                print(f"  [{i}]: {text}")
                        except:
                            pass
                            
            except Exception as e:
                print(f"{selector}: 错误 - {e}")
        
        # 等待手动检查
        input("按回车键关闭浏览器...")
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_selectors())