#!/usr/bin/env python
"""
专门分析登录弹窗结构的脚本

用于理解点击"继续学习"后出现的登录弹窗的实际HTML结构
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json

async def analyze_login_popup():
    """分析登录弹窗结构"""
    logger.info("=" * 60)
    logger.info("分析登录弹窗结构")
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
            password = "My2062660"
            
            success = await auto_login.login(username, password)
            if not success:
                logger.error("❌ 登录失败，无法继续分析")
                return
            
            logger.info("✅ 登录成功")
            
            # 导航到课程页面
            logger.info("步骤 2: 导航到课程页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 点击"继续学习"按钮
            logger.info("步骤 3: 点击继续学习按钮...")
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
            await asyncio.sleep(3)  # 等待弹窗出现
            
            # 分析登录弹窗结构
            logger.info("步骤 4: 分析登录弹窗结构...")
            logger.info("=" * 40)
            
            popup_analysis = await page.evaluate("""
                () => {
                    const result = {
                        dialogs: [],
                        allInputs: [],
                        allButtons: []
                    };
                    
                    // 查找所有对话框
                    const dialogSelectors = [
                        '.el-dialog', '.el-dialog.el-dialog--center', '.modal', 
                        '[role=\"dialog\"]', '.popup', '.dialog'
                    ];
                    
                    dialogSelectors.forEach(selector => {
                        const dialogs = document.querySelectorAll(selector);
                        dialogs.forEach(dialog => {
                            const style = window.getComputedStyle(dialog);
                            if (style.display !== 'none' && style.visibility !== 'hidden') {
                                // 分析对话框内的输入框
                                const inputs = dialog.querySelectorAll('input');
                                const inputInfo = [];
                                inputs.forEach(input => {
                                    inputInfo.push({
                                        type: input.type,
                                        placeholder: input.placeholder,
                                        className: input.className,
                                        id: input.id,
                                        name: input.name,
                                        visible: input.offsetWidth > 0 && input.offsetHeight > 0
                                    });
                                });
                                
                                // 分析对话框内的按钮
                                const buttons = dialog.querySelectorAll('button, div[onclick], .btn');
                                const buttonInfo = [];
                                buttons.forEach(btn => {
                                    buttonInfo.push({
                                        tag: btn.tagName,
                                        text: btn.textContent?.trim(),
                                        className: btn.className,
                                        id: btn.id,
                                        onclick: btn.getAttribute('onclick'),
                                        visible: btn.offsetWidth > 0 && btn.offsetHeight > 0
                                    });
                                });
                                
                                result.dialogs.push({
                                    selector: selector,
                                    className: dialog.className,
                                    id: dialog.id,
                                    innerHTML: dialog.innerHTML.substring(0, 1000), // 限制长度
                                    inputs: inputInfo,
                                    buttons: buttonInfo,
                                    zIndex: style.zIndex,
                                    visible: true
                                });
                            }
                        });
                    });
                    
                    // 查找页面上所有输入框（备用分析）
                    const allInputs = document.querySelectorAll('input');
                    allInputs.forEach(input => {
                        const style = window.getComputedStyle(input);
                        if (style.display !== 'none' && input.offsetWidth > 0) {
                            result.allInputs.push({
                                type: input.type,
                                placeholder: input.placeholder,
                                className: input.className,
                                id: input.id,
                                name: input.name,
                                parentClass: input.parentElement?.className,
                                visible: true
                            });
                        }
                    });
                    
                    // 查找页面上所有按钮（备用分析）
                    const allButtons = document.querySelectorAll('button');
                    allButtons.forEach(btn => {
                        const style = window.getComputedStyle(btn);
                        if (style.display !== 'none' && btn.offsetWidth > 0) {
                            const text = btn.textContent?.trim();
                            if (text && (text.includes('登录') || text.includes('确定') || text.includes('提交'))) {
                                result.allButtons.push({
                                    text: text,
                                    className: btn.className,
                                    id: btn.id,
                                    parentClass: btn.parentElement?.className
                                });
                            }
                        }
                    });
                    
                    return result;
                }
            """)
            
            logger.info(f"找到 {len(popup_analysis['dialogs'])} 个对话框")
            for i, dialog in enumerate(popup_analysis['dialogs']):
                logger.info(f"\\n对话框 {i+1}:")
                logger.info(f"  选择器: {dialog['selector']}")
                logger.info(f"  类名: {dialog['className']}")
                logger.info(f"  输入框数量: {len(dialog['inputs'])}")
                
                for j, input_info in enumerate(dialog['inputs']):
                    logger.info(f"    输入框 {j+1}: type={input_info['type']}, placeholder='{input_info['placeholder']}', class='{input_info['className']}', visible={input_info['visible']}")
                
                logger.info(f"  按钮数量: {len(dialog['buttons'])}")
                for j, btn_info in enumerate(dialog['buttons']):
                    logger.info(f"    按钮 {j+1}: text='{btn_info['text']}', tag={btn_info['tag']}, class='{btn_info['className']}', visible={btn_info['visible']}")
            
            logger.info(f"\\n页面总输入框数量: {len(popup_analysis['allInputs'])}")
            logger.info("相关输入框:")
            for input_info in popup_analysis['allInputs'][:10]:  # 只显示前10个
                logger.info(f"  type={input_info['type']}, placeholder='{input_info['placeholder']}', class='{input_info['className']}'")
            
            logger.info(f"\\n页面相关按钮数量: {len(popup_analysis['allButtons'])}")
            for btn_info in popup_analysis['allButtons'][:5]:  # 只显示前5个
                logger.info(f"  text='{btn_info['text']}', class='{btn_info['className']}'")
            
            # 保持浏览器打开以便手动探索
            logger.info("\\n保持浏览器打开30秒以便手动分析...")
            logger.info("请手动查看登录弹窗的结构和元素")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()
    
    logger.info("\\n" + "=" * 60)
    logger.info("登录弹窗结构分析完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(analyze_login_popup())