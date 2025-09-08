#!/usr/bin/env python
"""
分析网站页面结构，特别是视频播放器和弹窗

用于理解网站的实际HTML结构，以便编写针对性的处理逻辑
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json

async def analyze_page_structure():
    """分析页面结构"""
    logger.info("=" * 60)
    logger.info("开始分析网站页面结构")
    logger.info("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
            # 登录
            auto_login = AutoLogin(page)
            username = "640302198607120020"
            password = "My2062660"  # 正确的密码
            
            logger.info("正在登录...")
            success = await auto_login.login(username, password)
            
            if not success:
                logger.error("登录失败")
                return
            
            logger.info("登录成功，导航到课程页面...")
            
            # 访问课程列表页面
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # 分析课程列表结构
            logger.info("\n" + "=" * 40)
            logger.info("分析课程列表结构")
            logger.info("=" * 40)
            
            course_list_info = await page.evaluate("""
                () => {
                    const result = {
                        containers: [],
                        courses: [],
                        buttons: []
                    };
                    
                    // 查找课程容器
                    const containers = document.querySelectorAll('.gj_top_list_box, .el-collapse-item, .course-list');
                    containers.forEach(container => {
                        result.containers.push({
                            class: container.className,
                            childCount: container.children.length
                        });
                    });
                    
                    // 查找课程项
                    const courseItems = document.querySelectorAll('.el-collapse-item__content .gj_top_list_box li, .course-item, li[class*="course"]');
                    courseItems.forEach(item => {
                        const title = item.querySelector('.title, .course-title, h3, h4')?.textContent || '';
                        const button = item.querySelector('button, .btn, [class*="btn"], div[onclick]');
                        result.courses.push({
                            title: title.trim(),
                            hasButton: !!button,
                            buttonText: button?.textContent?.trim() || '',
                            buttonClass: button?.className || '',
                            buttonTag: button?.tagName || ''
                        });
                    });
                    
                    // 查找所有按钮
                    const buttons = document.querySelectorAll('button, .btn, [class*="study"], [class*="learn"]');
                    buttons.forEach(btn => {
                        if (btn.textContent && (btn.textContent.includes('学习') || btn.textContent.includes('继续'))) {
                            result.buttons.push({
                                text: btn.textContent.trim(),
                                class: btn.className,
                                tag: btn.tagName,
                                onclick: btn.getAttribute('onclick')
                            });
                        }
                    });
                    
                    return result;
                }
            """)
            
            logger.info(f"课程容器: {json.dumps(course_list_info['containers'], indent=2, ensure_ascii=False)}")
            logger.info(f"找到 {len(course_list_info['courses'])} 个课程项")
            if course_list_info['courses'][:3]:
                logger.info(f"前3个课程示例: {json.dumps(course_list_info['courses'][:3], indent=2, ensure_ascii=False)}")
            logger.info(f"学习按钮: {json.dumps(course_list_info['buttons'][:5], indent=2, ensure_ascii=False)}")
            
            # 尝试点击一个课程进入学习页面
            logger.info("\n" + "=" * 40)
            logger.info("尝试进入课程学习页面...")
            logger.info("=" * 40)
            
            # 查找并点击第一个"继续学习"或"开始学习"按钮
            clicked = await page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('button, .btn, div[onclick]');
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
            
            if clicked['clicked']:
                logger.info(f"点击了按钮: {clicked['buttonInfo']}")
                await asyncio.sleep(5)  # 等待页面加载
                
                # 分析弹窗结构
                logger.info("\n" + "=" * 40)
                logger.info("分析弹窗结构")
                logger.info("=" * 40)
                
                popup_info = await page.evaluate("""
                    () => {
                        const result = {
                            popups: [],
                            divBoxes: []
                        };
                        
                        // 查找所有可能的弹窗
                        const popupSelectors = [
                            '.el-dialog', '.el-message-box', '.modal', '.popup',
                            '[role="dialog"]', '.continue', 'div[style*="z-index"]'
                        ];
                        
                        popupSelectors.forEach(selector => {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(el => {
                                const display = window.getComputedStyle(el).display;
                                const visibility = window.getComputedStyle(el).visibility;
                                if (display !== 'none' && visibility !== 'hidden') {
                                    const buttons = el.querySelectorAll('button, div[onclick], .user_choise, [class*="btn"]');
                                    const buttonInfo = [];
                                    buttons.forEach(btn => {
                                        buttonInfo.push({
                                            text: btn.textContent?.trim(),
                                            class: btn.className,
                                            tag: btn.tagName
                                        });
                                    });
                                    
                                    result.popups.push({
                                        selector: selector,
                                        class: el.className,
                                        id: el.id,
                                        text: el.textContent?.substring(0, 200),
                                        buttons: buttonInfo,
                                        zIndex: window.getComputedStyle(el).zIndex
                                    });
                                }
                            });
                        });
                        
                        // 特别查找包含"继续学习"的div
                        const continueElements = document.querySelectorAll('div');
                        continueElements.forEach(div => {
                            if (div.textContent && (div.textContent.includes('继续学习') || div.textContent.includes('开始学习'))) {
                                const parent = div.parentElement;
                                if (parent && window.getComputedStyle(parent).display !== 'none') {
                                    result.divBoxes.push({
                                        class: div.className,
                                        parentClass: parent.className,
                                        text: div.textContent.substring(0, 100),
                                        hasUserChoise: div.querySelector('.user_choise') !== null,
                                        userChoiseInfo: div.querySelector('.user_choise') ? {
                                            class: div.querySelector('.user_choise').className,
                                            text: div.querySelector('.user_choise').textContent?.trim()
                                        } : null
                                    });
                                }
                            }
                        });
                        
                        return result;
                    }
                """)
                
                logger.info(f"发现弹窗: {json.dumps(popup_info['popups'], indent=2, ensure_ascii=False)}")
                logger.info(f"学习相关div: {json.dumps(popup_info['divBoxes'], indent=2, ensure_ascii=False)}")
                
                # 分析视频播放器结构
                logger.info("\n" + "=" * 40)
                logger.info("分析视频播放器结构")
                logger.info("=" * 40)
                
                # 先处理弹窗（如果有）
                await page.evaluate("""
                    () => {
                        // 点击继续学习按钮
                        const buttons = document.querySelectorAll('.user_choise, button, div[onclick]');
                        for (let btn of buttons) {
                            if (btn.textContent && (btn.textContent.includes('继续学习') || btn.textContent.includes('开始学习'))) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                
                await asyncio.sleep(3)
                
                video_info = await page.evaluate("""
                    () => {
                        const result = {
                            videos: [],
                            iframes: [],
                            players: []
                        };
                        
                        // 查找video标签
                        const videos = document.querySelectorAll('video');
                        videos.forEach(video => {
                            result.videos.push({
                                src: video.src,
                                id: video.id,
                                class: video.className,
                                width: video.width,
                                height: video.height,
                                paused: video.paused,
                                controls: video.controls
                            });
                        });
                        
                        // 查找iframe（可能包含视频）
                        const iframes = document.querySelectorAll('iframe');
                        iframes.forEach(iframe => {
                            result.iframes.push({
                                src: iframe.src,
                                id: iframe.id,
                                class: iframe.className,
                                width: iframe.width,
                                height: iframe.height
                            });
                        });
                        
                        // 查找视频播放器容器
                        const playerSelectors = [
                            '.video-player', '.player', '[class*="video"]',
                            '.prism-player', '.dplayer', '.vjs-player'
                        ];
                        
                        playerSelectors.forEach(selector => {
                            const players = document.querySelectorAll(selector);
                            players.forEach(player => {
                                result.players.push({
                                    selector: selector,
                                    class: player.className,
                                    id: player.id,
                                    hasVideo: player.querySelector('video') !== null,
                                    hasIframe: player.querySelector('iframe') !== null
                                });
                            });
                        });
                        
                        return result;
                    }
                """)
                
                logger.info(f"视频元素: {json.dumps(video_info['videos'], indent=2, ensure_ascii=False)}")
                logger.info(f"iframe元素: {json.dumps(video_info['iframes'], indent=2, ensure_ascii=False)}")
                logger.info(f"播放器容器: {json.dumps(video_info['players'], indent=2, ensure_ascii=False)}")
            
            # 保持浏览器打开以便观察
            logger.info("\n保持浏览器打开30秒以便手动探索...")
            logger.info("你可以手动点击课程，观察弹窗和视频播放器的行为")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("页面结构分析完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(analyze_page_structure())