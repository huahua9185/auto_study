#!/usr/bin/env python
"""
监控点击前后页面元素变化

用户手动点击"开始学习"或"继续学习"按钮，脚本对比点击前后的页面变化
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json
import time

class PageChangeMonitor:
    def __init__(self, page):
        self.page = page
        self.snapshots = []
    
    async def take_snapshot(self, label=""):
        """获取页面当前状态快照"""
        logger.info(f"📸 正在获取页面快照: {label}")
        
        snapshot = await self.page.evaluate("""
            () => {
                const snapshot = {
                    timestamp: Date.now(),
                    url: window.location.href,
                    title: document.title,
                    
                    // DOM 基本信息
                    totalElements: document.querySelectorAll('*').length,
                    totalDivs: document.querySelectorAll('div').length,
                    totalButtons: document.querySelectorAll('button').length,
                    
                    // 视频相关元素
                    videos: [],
                    iframes: [],
                    
                    // 弹窗相关元素  
                    popups: [],
                    overlays: [],
                    
                    // 特定xpath元素
                    xpathElements: {},
                    
                    // 所有可见的div（按位置分组）
                    visibleDivs: [],
                    
                    // z-index高的元素（可能是弹窗）
                    highZIndexElements: [],
                    
                    // 最近添加的元素（可能是动态生成的）
                    recentElements: [],
                    
                    // 包含学习相关文本的元素
                    learningElements: []
                };
                
                // === 视频元素分析 ===
                const videos = document.querySelectorAll('video');
                videos.forEach((video, index) => {
                    const rect = video.getBoundingClientRect();
                    snapshot.videos.push({
                        index: index,
                        src: video.src || video.currentSrc,
                        visible: rect.width > 0 && rect.height > 0,
                        paused: video.paused,
                        duration: video.duration,
                        currentTime: video.currentTime,
                        readyState: video.readyState,
                        rect: {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y), 
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        }
                    });
                });
                
                // === iframe元素分析 ===
                const iframes = document.querySelectorAll('iframe');
                iframes.forEach((iframe, index) => {
                    const rect = iframe.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        snapshot.iframes.push({
                            index: index,
                            src: iframe.src,
                            rect: {
                                x: Math.round(rect.x),
                                y: Math.round(rect.y),
                                width: Math.round(rect.width), 
                                height: Math.round(rect.height)
                            }
                        });
                    }
                });
                
                // === 弹窗元素分析 ===
                const popupSelectors = [
                    '.el-dialog', '.el-message-box', '.modal', '.popup', 
                    '[role="dialog"]', '.overlay', '.mask', '.layer'
                ];
                
                popupSelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach((el, index) => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        
                        if (rect.width > 0 && rect.height > 0 && 
                            style.display !== 'none' && 
                            style.visibility !== 'hidden') {
                            
                            snapshot.popups.push({
                                selector: selector,
                                index: index,
                                class: el.className,
                                id: el.id,
                                text: el.textContent?.substring(0, 200),
                                rect: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                },
                                zIndex: style.zIndex,
                                opacity: style.opacity
                            });
                        }
                    });
                });
                
                // === 特定xpath元素检查 ===
                const xpaths = [
                    '/html/body/div/div[3]/div[2]',
                    '/html/body/div/div[2]/div[2]',
                    '/html/body/div/div[4]/div[2]',
                    '/html/body/div/div[3]/div[1]',
                    '/html/body/div/div[3]/div[3]'
                ];
                
                xpaths.forEach(xpath => {
                    const result = document.evaluate(
                        xpath, document, null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE, null
                    );
                    
                    const element = result.singleNodeValue;
                    if (element) {
                        const rect = element.getBoundingClientRect();
                        snapshot.xpathElements[xpath] = {
                            exists: true,
                            visible: rect.width > 0 && rect.height > 0,
                            tag: element.tagName,
                            class: element.className,
                            id: element.id,
                            text: element.textContent?.substring(0, 100),
                            rect: {
                                x: Math.round(rect.x),
                                y: Math.round(rect.y),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            }
                        };
                    } else {
                        snapshot.xpathElements[xpath] = { exists: false };
                    }
                });
                
                // === 高z-index元素（可能的弹窗） ===
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const zIndex = parseInt(style.zIndex);
                    
                    if (zIndex > 100) { // 高z-index通常表示弹窗
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            snapshot.highZIndexElements.push({
                                tag: el.tagName,
                                class: el.className,
                                id: el.id,
                                zIndex: zIndex,
                                text: el.textContent?.substring(0, 50),
                                rect: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                }
                            });
                        }
                    }
                });
                
                // === 包含学习相关文本的元素 ===
                const learningKeywords = ['继续学习', '开始学习', '播放', '视频', '学习'];
                allElements.forEach(el => {
                    const text = el.textContent || '';
                    const hasKeyword = learningKeywords.some(keyword => text.includes(keyword));
                    
                    if (hasKeyword && text.length < 200) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            snapshot.learningElements.push({
                                tag: el.tagName,
                                class: el.className,
                                id: el.id,
                                text: text.trim(),
                                rect: {
                                    x: Math.round(rect.x),
                                    y: Math.round(rect.y),
                                    width: Math.round(rect.width),
                                    height: Math.round(rect.height)
                                }
                            });
                        }
                    }
                });
                
                // === body直接子元素分析 ===
                const bodyChildren = Array.from(document.body.children);
                snapshot.bodyChildrenCount = bodyChildren.length;
                snapshot.bodyChildren = bodyChildren.map((child, index) => ({
                    index: index,
                    tag: child.tagName,
                    class: child.className,
                    id: child.id,
                    childCount: child.children.length,
                    visible: child.offsetWidth > 0 && child.offsetHeight > 0
                }));
                
                return snapshot;
            }
        """)
        
        snapshot['label'] = label
        snapshot['readable_time'] = time.strftime('%H:%M:%S', time.localtime(snapshot['timestamp'] / 1000))
        
        self.snapshots.append(snapshot)
        logger.info(f"✅ 快照获取完成: {snapshot['totalElements']}个元素, {len(snapshot['videos'])}个视频, {len(snapshot['popups'])}个弹窗")
        
        return snapshot
    
    def compare_snapshots(self, before_snapshot, after_snapshot):
        """对比两个快照的差异"""
        logger.info("🔍 对比页面变化...")
        
        changes = {
            'basic_changes': {},
            'video_changes': {},
            'popup_changes': {},
            'xpath_changes': {},
            'new_elements': [],
            'disappeared_elements': [],
            'learning_elements_changes': {}
        }
        
        # === 基本变化对比 ===
        changes['basic_changes'] = {
            'url_changed': before_snapshot['url'] != after_snapshot['url'],
            'title_changed': before_snapshot['title'] != after_snapshot['title'],
            'total_elements_diff': after_snapshot['totalElements'] - before_snapshot['totalElements'],
            'total_divs_diff': after_snapshot['totalDivs'] - before_snapshot['totalDivs'],
            'body_children_diff': after_snapshot['bodyChildrenCount'] - before_snapshot['bodyChildrenCount']
        }
        
        # === 视频变化对比 ===
        changes['video_changes'] = {
            'count_diff': len(after_snapshot['videos']) - len(before_snapshot['videos']),
            'new_videos': [],
            'video_state_changes': []
        }
        
        # 检查新增视频
        before_video_srcs = set(v['src'] for v in before_snapshot['videos'])
        for video in after_snapshot['videos']:
            if video['src'] not in before_video_srcs:
                changes['video_changes']['new_videos'].append(video)
        
        # 检查视频状态变化
        for after_video in after_snapshot['videos']:
            for before_video in before_snapshot['videos']:
                if after_video['src'] == before_video['src']:
                    if after_video['paused'] != before_video['paused']:
                        changes['video_changes']['video_state_changes'].append({
                            'src': after_video['src'],
                            'was_paused': before_video['paused'],
                            'now_paused': after_video['paused']
                        })
        
        # === 弹窗变化对比 ===  
        changes['popup_changes'] = {
            'count_diff': len(after_snapshot['popups']) - len(before_snapshot['popups']),
            'new_popups': [],
            'disappeared_popups': []
        }
        
        # 通过类名和位置对比弹窗
        before_popup_keys = set(f"{p['class']}_{p['rect']['x']}_{p['rect']['y']}" for p in before_snapshot['popups'])
        after_popup_keys = set(f"{p['class']}_{p['rect']['x']}_{p['rect']['y']}" for p in after_snapshot['popups'])
        
        for popup in after_snapshot['popups']:
            popup_key = f"{popup['class']}_{popup['rect']['x']}_{popup['rect']['y']}"
            if popup_key not in before_popup_keys:
                changes['popup_changes']['new_popups'].append(popup)
        
        for popup in before_snapshot['popups']:
            popup_key = f"{popup['class']}_{popup['rect']['x']}_{popup['rect']['y']}"
            if popup_key not in after_popup_keys:
                changes['popup_changes']['disappeared_popups'].append(popup)
        
        # === xpath元素变化对比 ===
        for xpath in after_snapshot['xpathElements']:
            before_exists = before_snapshot['xpathElements'].get(xpath, {}).get('exists', False)
            after_exists = after_snapshot['xpathElements'][xpath]['exists']
            
            if before_exists != after_exists:
                changes['xpath_changes'][xpath] = {
                    'before_exists': before_exists,
                    'after_exists': after_exists,
                    'element_info': after_snapshot['xpathElements'][xpath] if after_exists else None
                }
        
        # === 学习相关元素变化对比 ===
        before_learning_texts = set(el['text'] for el in before_snapshot['learningElements'])
        after_learning_texts = set(el['text'] for el in after_snapshot['learningElements'])
        
        changes['learning_elements_changes'] = {
            'count_diff': len(after_snapshot['learningElements']) - len(before_snapshot['learningElements']),
            'new_texts': list(after_learning_texts - before_learning_texts),
            'disappeared_texts': list(before_learning_texts - after_learning_texts)
        }
        
        return changes

async def monitor_click_changes():
    """监控点击前后的页面变化"""
    logger.info("=" * 80)
    logger.info("🔍 页面点击变化监控器")
    logger.info("📋 将记录您手动点击前后的页面变化")
    logger.info("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            monitor = PageChangeMonitor(page)
            
            # 登录
            logger.info("🔐 步骤 1: 登录到系统...")
            auto_login = AutoLogin(page)
            success = await auto_login.login("640302198607120020", "My2062660")
            if not success:
                logger.error("❌ 登录失败")
                return
            
            logger.info("✅ 登录成功")
            
            # 进入课程列表页面
            logger.info("📚 步骤 2: 进入课程列表页面...")
            await page.goto("https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275")
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            logger.info("✅ 页面加载完成")
            
            # 获取初始快照
            logger.info("\\n📸 步骤 3: 获取点击前的页面快照...")
            initial_snapshot = await monitor.take_snapshot("点击前-初始状态")
            
            # 用户操作指引
            logger.info("\\n" + "="*60)
            logger.info("👆 请您现在手动操作:")
            logger.info("1. 在浏览器中找到任意一个'继续学习'或'开始学习'按钮")
            logger.info("2. 点击该按钮")
            logger.info("3. 观察页面的任何变化（弹窗、视频、页面跳转等）")
            logger.info("4. 不要关闭任何可能出现的弹窗或对话框")
            logger.info("5. 完成操作后，等待脚本自动继续分析")
            logger.info("="*60)
            
            # 监控页面变化
            logger.info("\\n⏰ 开始监控页面变化（60秒）...")
            logger.info("💡 脚本将每5秒检查一次页面状态")
            
            previous_snapshot = initial_snapshot
            change_detected = False
            
            for i in range(12):  # 60秒，每5秒检查一次
                await asyncio.sleep(5)
                
                # 获取当前快照
                current_snapshot = await monitor.take_snapshot(f"监控点-{i+1}")
                
                # 对比变化
                changes = monitor.compare_snapshots(previous_snapshot, current_snapshot)
                
                # 检查是否有重要变化
                has_significant_changes = (
                    changes['basic_changes']['total_elements_diff'] > 10 or
                    changes['video_changes']['count_diff'] > 0 or
                    changes['popup_changes']['count_diff'] > 0 or
                    any(changes['xpath_changes'].values()) or
                    changes['basic_changes']['url_changed']
                )
                
                if has_significant_changes:
                    logger.info(f"🚨 检测到重要变化! (第{i+1}次检查)")
                    change_detected = True
                    break
                else:
                    logger.info(f"⏱️  第{i+1}次检查: 无重要变化 (元素差异: {changes['basic_changes']['total_elements_diff']})")
                
                previous_snapshot = current_snapshot
            
            # 获取最终快照并分析
            logger.info("\\n📸 获取最终快照...")
            final_snapshot = await monitor.take_snapshot("点击后-最终状态")
            
            # 详细对比分析
            logger.info("\\n" + "="*60)
            logger.info("📊 详细变化分析")
            logger.info("="*60)
            
            final_changes = monitor.compare_snapshots(initial_snapshot, final_snapshot)
            
            # 显示分析结果
            logger.info(f"\\n🔢 基本变化:")
            basic = final_changes['basic_changes']
            logger.info(f"  URL变化: {basic['url_changed']}")
            logger.info(f"  标题变化: {basic['title_changed']}")
            logger.info(f"  总元素数差异: {basic['total_elements_diff']}")
            logger.info(f"  div元素数差异: {basic['total_divs_diff']}")
            logger.info(f"  body子元素数差异: {basic['body_children_diff']}")
            
            logger.info(f"\\n🎬 视频变化:")
            video = final_changes['video_changes']
            logger.info(f"  视频数量差异: {video['count_diff']}")
            if video['new_videos']:
                logger.info(f"  新增视频: {len(video['new_videos'])}个")
                for i, v in enumerate(video['new_videos']):
                    logger.info(f"    {i+1}. {v['src'][:50]}... (暂停: {v['paused']})")
            if video['video_state_changes']:
                logger.info(f"  视频状态变化: {len(video['video_state_changes'])}个")
                for change in video['video_state_changes']:
                    logger.info(f"    {change['src'][:30]}... 从{'暂停' if change['was_paused'] else '播放'}变为{'暂停' if change['now_paused'] else '播放'}")
            
            logger.info(f"\\n🪟 弹窗变化:")
            popup = final_changes['popup_changes']
            logger.info(f"  弹窗数量差异: {popup['count_diff']}")
            if popup['new_popups']:
                logger.info(f"  新增弹窗: {len(popup['new_popups'])}个")
                for i, p in enumerate(popup['new_popups']):
                    logger.info(f"    {i+1}. {p['selector']} - {p['class']}")
                    logger.info(f"       位置: ({p['rect']['x']}, {p['rect']['y']}) 大小: {p['rect']['width']}x{p['rect']['height']}")
                    logger.info(f"       文本: '{p['text'][:50]}...'")
            
            logger.info(f"\\n🎯 xpath元素变化:")
            if final_changes['xpath_changes']:
                for xpath, change in final_changes['xpath_changes'].items():
                    logger.info(f"  {xpath}:")
                    logger.info(f"    之前存在: {change['before_exists']}")
                    logger.info(f"    现在存在: {change['after_exists']}")
                    if change['element_info']:
                        info = change['element_info']
                        logger.info(f"    元素信息: {info['tag']}.{info['class']}")
                        logger.info(f"    可见: {info['visible']}")
                        logger.info(f"    文本: '{info['text']}'")
                        logger.info(f"    位置: ({info['rect']['x']}, {info['rect']['y']})")
            else:
                logger.info("  无xpath元素变化")
            
            logger.info(f"\\n📝 学习相关元素变化:")
            learning = final_changes['learning_elements_changes']
            logger.info(f"  元素数量差异: {learning['count_diff']}")
            if learning['new_texts']:
                logger.info(f"  新增文本: {learning['new_texts']}")
            if learning['disappeared_texts']:
                logger.info(f"  消失文本: {learning['disappeared_texts']}")
            
            # 生成解决方案建议
            logger.info("\\n" + "="*60)
            logger.info("💡 基于变化分析的解决方案建议")
            logger.info("="*60)
            
            if final_changes['video_changes']['count_diff'] > 0:
                logger.info("🎬 检测到新增视频元素!")
                logger.info("💡 建议: 直接控制视频元素进行播放")
                logger.info("🔧 实现方式: 使用video.play()方法")
            
            elif final_changes['popup_changes']['count_diff'] > 0:
                logger.info("🪟 检测到新增弹窗!")
                logger.info("💡 建议: 处理弹窗中的确认按钮")
                for popup in popup['new_popups']:
                    logger.info(f"🔧 目标弹窗: {popup['selector']} at ({popup['rect']['x']}, {popup['rect']['y']})")
            
            elif any(change['after_exists'] and not change['before_exists'] 
                    for change in final_changes['xpath_changes'].values()):
                logger.info("🎯 检测到新的xpath元素出现!")
                for xpath, change in final_changes['xpath_changes'].items():
                    if change['after_exists'] and not change['before_exists']:
                        logger.info(f"💡 建议: 点击xpath元素 {xpath}")
                        logger.info(f"🔧 元素信息: {change['element_info']}")
            
            elif final_changes['basic_changes']['url_changed']:
                logger.info("🔄 检测到页面跳转!")
                logger.info("💡 建议: 在新页面中查找视频元素")
            
            else:
                logger.info("❓ 未检测到明显变化")
                logger.info("💡 建议检查:")
                logger.info("  1. 按钮点击是否真正触发")
                logger.info("  2. 是否需要满足特定条件")
                logger.info("  3. 是否有网络延迟导致的异步加载")
            
            # 保存分析结果
            logger.info("\\n💾 保存分析结果到文件...")
            analysis_data = {
                'initial_snapshot': initial_snapshot,
                'final_snapshot': final_snapshot,
                'changes_analysis': final_changes,
                'all_snapshots': monitor.snapshots
            }
            
            with open('click_analysis_result.json', 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            logger.info("✅ 分析结果已保存到 click_analysis_result.json")
            
            # 保持浏览器打开
            logger.info("\\n🔍 保持浏览器打开30秒以便进一步观察...")
            await asyncio.sleep(30)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(monitor_click_changes())