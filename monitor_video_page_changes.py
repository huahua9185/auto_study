#!/usr/bin/env python
"""
监控视频播放页面的点击变化

确保在视频播放页面监控"继续学习"按钮的点击效果
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json
import time

async def monitor_video_page_changes():
    """在视频播放页面监控点击变化"""
    logger.info("=" * 80)
    logger.info("🎬 视频播放页面点击变化监控器")
    logger.info("📋 目标：在视频播放页面监控'继续学习'按钮点击效果")
    logger.info("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        try:
            page = await browser.new_page()
            
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
            
            logger.info("✅ 课程列表页面加载完成")
            
            # 指导用户进入视频页面
            logger.info("\n" + "="*80)
            logger.info("👆 请您现在手动操作 - 第一阶段：进入视频播放页面")
            logger.info("="*80)
            logger.info("📝 操作步骤:")
            logger.info("1. 在课程列表中找到一个'继续学习'按钮")
            logger.info("2. 点击该按钮，尝试进入视频播放页面")
            logger.info("3. 如果出现任何弹窗，先不要关闭")
            logger.info("4. 确保最终进入了包含视频播放器的页面")
            logger.info("5. 进入视频页面后，请按任意键继续...")
            
            # 等待用户进入视频页面
            logger.info("⏰ 等待用户进入视频播放页面...")
            logger.info("💡 页面URL应该会发生变化")
            
            initial_url = page.url
            logger.info(f"📍 当前URL: {initial_url}")
            
            # 监控URL变化，等待进入视频页面
            for i in range(60):  # 最多等待60秒
                await asyncio.sleep(1)
                current_url = page.url
                
                if current_url != initial_url:
                    logger.info(f"🎉 检测到页面跳转!")
                    logger.info(f"📍 新URL: {current_url}")
                    
                    # 等待新页面完全加载
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    await asyncio.sleep(3)
                    break
                elif i % 10 == 0:
                    logger.info(f"⏱️  等待中... ({60-i}秒剩余)")
            else:
                logger.warning("❌ 60秒内未检测到页面跳转")
                logger.info("💡 请手动确认是否已进入视频播放页面")
            
            # 检查当前页面是否是视频页面
            current_page_info = await page.evaluate("""
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        hasVideo: document.querySelectorAll('video').length > 0,
                        hasIframe: document.querySelectorAll('iframe').length > 0,
                        videoCount: document.querySelectorAll('video').length,
                        iframeCount: document.querySelectorAll('iframe').length,
                        hasXpathTarget: !!document.evaluate(
                            '/html/body/div/div[3]/div[2]',
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        ).singleNodeValue
                    };
                }
            """)
            
            logger.info("\n📊 当前页面分析:")
            logger.info(f"📍 URL: {current_page_info['url']}")
            logger.info(f"📄 标题: {current_page_info['title']}")
            logger.info(f"🎬 视频元素: {current_page_info['videoCount']}个")
            logger.info(f"🖼️  iframe元素: {current_page_info['iframeCount']}个")
            logger.info(f"🎯 目标xpath存在: {current_page_info['hasXpathTarget']}")
            
            if not (current_page_info['hasVideo'] or current_page_info['hasIframe'] or current_page_info['hasXpathTarget']):
                logger.warning("⚠️  当前页面可能不是视频播放页面")
                logger.info("💡 请手动导航到包含视频播放器的页面")
                logger.info("⏰ 等待30秒供手动操作...")
                await asyncio.sleep(30)
            
            # 现在开始在视频页面监控
            logger.info("\n" + "="*80)
            logger.info("🔍 开始在视频播放页面监控变化")
            logger.info("="*80)
            
            # 获取视频页面的初始快照
            logger.info("📸 获取视频页面初始快照...")
            initial_snapshot = await get_video_page_snapshot(page, "视频页面-点击前")
            
            # 用户操作指引 - 第二阶段
            logger.info("\n" + "="*80)
            logger.info("👆 请您现在手动操作 - 第二阶段：在视频页面点击")
            logger.info("="*80)
            logger.info("📝 操作步骤:")
            logger.info("1. 在当前视频页面中找到'继续学习'或'开始学习'按钮")
            logger.info("2. 这可能是一个弹窗、对话框或页面上的按钮")
            logger.info("3. 点击该按钮")
            logger.info("4. 观察是否有视频开始播放或其他变化")
            logger.info("5. 不要关闭任何弹窗，让脚本记录所有变化")
            
            # 开始监控视频页面的变化
            logger.info("\n⏰ 开始监控视频页面变化（90秒）...")
            logger.info("💡 脚本将每3秒检查一次页面状态")
            
            previous_snapshot = initial_snapshot
            significant_changes = []
            
            for i in range(30):  # 90秒，每3秒检查一次
                await asyncio.sleep(3)
                
                # 获取当前快照
                current_snapshot = await get_video_page_snapshot(page, f"监控点-{i+1}")
                
                # 分析变化
                changes = analyze_video_page_changes(previous_snapshot, current_snapshot)
                
                # 检查重要变化
                is_significant = (
                    changes['video_changes']['count_diff'] != 0 or
                    changes['video_changes']['state_changes'] or
                    changes['popup_changes']['count_diff'] != 0 or
                    changes['xpath_changes'] or
                    changes['basic_changes']['element_diff'] > 20
                )
                
                if is_significant:
                    logger.info(f"🚨 第{i+1}次检查: 检测到重要变化!")
                    if changes['video_changes']['count_diff'] > 0:
                        logger.info(f"  🎬 新增 {changes['video_changes']['count_diff']} 个视频")
                    if changes['video_changes']['state_changes']:
                        logger.info(f"  ▶️  视频状态变化: {len(changes['video_changes']['state_changes'])}个")
                    if changes['popup_changes']['count_diff'] != 0:
                        logger.info(f"  🪟 弹窗变化: {changes['popup_changes']['count_diff']}")
                    if changes['xpath_changes']:
                        logger.info(f"  🎯 xpath元素变化: {list(changes['xpath_changes'].keys())}")
                    
                    significant_changes.append({
                        'time': i+1,
                        'changes': changes,
                        'snapshot': current_snapshot
                    })
                else:
                    logger.info(f"⏱️  第{i+1}次检查: 无重要变化 (元素差异: {changes['basic_changes']['element_diff']})")
                
                previous_snapshot = current_snapshot
            
            # 获取最终快照
            logger.info("\n📸 获取最终快照...")
            final_snapshot = await get_video_page_snapshot(page, "视频页面-点击后")
            
            # 详细分析最终结果
            logger.info("\n" + "="*80)
            logger.info("📊 最终变化分析")
            logger.info("="*80)
            
            final_changes = analyze_video_page_changes(initial_snapshot, final_snapshot)
            
            # 显示详细分析
            display_change_analysis(final_changes)
            
            # 生成解决方案
            generate_solution_recommendations(final_changes, significant_changes)
            
            # 保存分析结果
            save_analysis_results(initial_snapshot, final_snapshot, final_changes, significant_changes)
            
            # 保持浏览器打开
            logger.info("\n🔍 保持浏览器打开60秒以便进一步观察...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

async def get_video_page_snapshot(page, label):
    """获取视频页面快照"""
    logger.info(f"📸 正在获取快照: {label}")
    
    snapshot = await page.evaluate("""
        () => {
            const snapshot = {
                timestamp: Date.now(),
                url: window.location.href,
                title: document.title,
                totalElements: document.querySelectorAll('*').length,
                
                videos: [],
                iframes: [],
                popups: [],
                xpathElements: {},
                highZIndexElements: [],
                learningElements: []
            };
            
            // 视频元素
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
                    rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                });
            });
            
            // iframe元素
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach((iframe, index) => {
                const rect = iframe.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    snapshot.iframes.push({
                        index: index,
                        src: iframe.src,
                        rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                    });
                }
            });
            
            // 弹窗元素
            const popupSelectors = ['.el-dialog', '.modal', '.popup', '[role="dialog"]'];
            popupSelectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    if (rect.width > 0 && rect.height > 0 && style.display !== 'none') {
                        snapshot.popups.push({
                            selector: selector,
                            class: el.className,
                            text: el.textContent?.substring(0, 100),
                            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                        });
                    }
                });
            });
            
            // xpath元素检查
            const xpaths = [
                '/html/body/div/div[3]/div[2]',
                '/html/body/div/div[2]/div[2]', 
                '/html/body/div/div[4]/div[2]'
            ];
            
            xpaths.forEach(xpath => {
                const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const element = result.singleNodeValue;
                if (element) {
                    const rect = element.getBoundingClientRect();
                    snapshot.xpathElements[xpath] = {
                        exists: true,
                        visible: rect.width > 0 && rect.height > 0,
                        tag: element.tagName,
                        class: element.className,
                        text: element.textContent?.substring(0, 100),
                        rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                    };
                } else {
                    snapshot.xpathElements[xpath] = { exists: false };
                }
            });
            
            // 高z-index元素
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                const style = window.getComputedStyle(el);
                const zIndex = parseInt(style.zIndex);
                if (zIndex > 100) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        snapshot.highZIndexElements.push({
                            tag: el.tagName,
                            class: el.className,
                            zIndex: zIndex,
                            text: el.textContent?.substring(0, 50),
                            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                        });
                    }
                }
            });
            
            // 学习相关元素
            allElements.forEach(el => {
                const text = el.textContent || '';
                if ((text.includes('继续学习') || text.includes('开始学习') || text.includes('播放')) && text.length < 100) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        snapshot.learningElements.push({
                            tag: el.tagName,
                            class: el.className,
                            text: text.trim(),
                            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                        });
                    }
                }
            });
            
            return snapshot;
        }
    """)
    
    snapshot['label'] = label
    snapshot['readable_time'] = time.strftime('%H:%M:%S', time.localtime(snapshot['timestamp'] / 1000))
    
    logger.info(f"✅ 快照完成: {snapshot['totalElements']}个元素, {len(snapshot['videos'])}个视频, {len(snapshot['popups'])}个弹窗")
    return snapshot

def analyze_video_page_changes(before, after):
    """分析视频页面变化"""
    changes = {
        'basic_changes': {
            'url_changed': before['url'] != after['url'],
            'element_diff': after['totalElements'] - before['totalElements']
        },
        'video_changes': {
            'count_diff': len(after['videos']) - len(before['videos']),
            'new_videos': [],
            'state_changes': []
        },
        'popup_changes': {
            'count_diff': len(after['popups']) - len(before['popups']),
            'new_popups': [],
            'disappeared_popups': []
        },
        'xpath_changes': {},
        'iframe_changes': {
            'count_diff': len(after['iframes']) - len(before['iframes']),
            'new_iframes': []
        }
    }
    
    # 视频变化分析
    before_video_srcs = set(v['src'] for v in before['videos'])
    for video in after['videos']:
        if video['src'] not in before_video_srcs:
            changes['video_changes']['new_videos'].append(video)
    
    # 视频状态变化
    for after_video in after['videos']:
        for before_video in before['videos']:
            if after_video['src'] == before_video['src'] and after_video['paused'] != before_video['paused']:
                changes['video_changes']['state_changes'].append({
                    'src': after_video['src'][:50] + '...',
                    'was_paused': before_video['paused'],
                    'now_paused': after_video['paused']
                })
    
    # xpath变化
    for xpath in after['xpathElements']:
        before_exists = before['xpathElements'].get(xpath, {}).get('exists', False)
        after_exists = after['xpathElements'][xpath]['exists']
        if before_exists != after_exists:
            changes['xpath_changes'][xpath] = {
                'before_exists': before_exists,
                'after_exists': after_exists,
                'element_info': after['xpathElements'][xpath] if after_exists else None
            }
    
    return changes

def display_change_analysis(changes):
    """显示变化分析"""
    logger.info("📊 基本变化:")
    logger.info(f"  URL变化: {changes['basic_changes']['url_changed']}")
    logger.info(f"  元素数差异: {changes['basic_changes']['element_diff']}")
    
    logger.info("🎬 视频变化:")
    logger.info(f"  数量差异: {changes['video_changes']['count_diff']}")
    if changes['video_changes']['new_videos']:
        logger.info(f"  新增视频: {len(changes['video_changes']['new_videos'])}个")
    if changes['video_changes']['state_changes']:
        logger.info(f"  状态变化: {len(changes['video_changes']['state_changes'])}个")
        for change in changes['video_changes']['state_changes']:
            state = '开始播放' if change['was_paused'] and not change['now_paused'] else '暂停播放'
            logger.info(f"    {change['src']} -> {state}")
    
    logger.info("🎯 xpath元素变化:")
    if changes['xpath_changes']:
        for xpath, change in changes['xpath_changes'].items():
            logger.info(f"  {xpath}: {change['before_exists']} -> {change['after_exists']}")
            if change['element_info']:
                info = change['element_info']
                logger.info(f"    {info['tag']}.{info['class']}: '{info['text']}'")

def generate_solution_recommendations(final_changes, significant_changes):
    """生成解决方案建议"""
    logger.info("\n💡 解决方案建议:")
    logger.info("="*50)
    
    if final_changes['video_changes']['state_changes']:
        logger.info("🎯 发现视频状态变化!")
        logger.info("💡 建议: 视频已经开始播放，继续监控播放状态")
        
    elif final_changes['video_changes']['count_diff'] > 0:
        logger.info("🎯 发现新增视频元素!")
        logger.info("💡 建议: 控制新出现的视频元素")
        
    elif any(change['after_exists'] and not change['before_exists'] for change in final_changes['xpath_changes'].values()):
        logger.info("🎯 发现新的xpath元素!")
        for xpath, change in final_changes['xpath_changes'].items():
            if change['after_exists'] and not change['before_exists']:
                logger.info(f"💡 建议: 处理xpath元素 {xpath}")
                
    else:
        logger.info("❓ 未检测到明显的有用变化")
        logger.info("💡 可能需要:")
        logger.info("  1. 确认是否点击了正确的按钮")
        logger.info("  2. 检查是否有权限或其他限制")
        logger.info("  3. 尝试不同的操作方式")

def save_analysis_results(initial, final, changes, significant_changes):
    """保存分析结果"""
    logger.info("💾 保存分析结果...")
    
    result = {
        'initial_snapshot': initial,
        'final_snapshot': final,
        'changes_analysis': changes,
        'significant_changes': significant_changes,
        'analysis_time': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('video_page_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info("✅ 结果已保存到 video_page_analysis.json")

if __name__ == "__main__":
    asyncio.run(monitor_video_page_changes())