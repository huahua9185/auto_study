#!/usr/bin/env python
"""
仅在视频播放页面进行监控

关键变更：
1. 登录后直接要求用户手动进入视频页面
2. 检测当前页面是否为视频页面，如果不是就停止
3. 只在确认是视频页面后才开始监控
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json
import time

async def monitor_video_page_only():
    """仅在视频播放页面进行监控"""
    logger.info("=" * 80)
    logger.info("🎬 视频播放页面专用监控器")
    logger.info("📋 目标：仅在视频播放页面监控'继续学习'按钮点击效果")
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
            
            # 明确指示用户需要手动导航
            logger.info("\n" + "="*80)
            logger.info("👆 重要：请您现在手动导航到视频播放页面")
            logger.info("="*80)
            logger.info("📝 操作步骤:")
            logger.info("1. 在浏览器中手动访问任意视频课程")
            logger.info("2. 确保进入包含视频播放器的页面")
            logger.info("3. 不要点击任何'继续学习'按钮")
            logger.info("4. 确认页面包含视频元素后，按回车继续")
            
            # 等待用户手动操作
            logger.info("\n⏰ 等待30秒供您手动导航到视频播放页面...")
            await asyncio.sleep(30)
            
            # 检查当前页面
            logger.info("🔍 检查当前页面是否为视频播放页面...")
            page_check = await page.evaluate("""
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        videoCount: document.querySelectorAll('video').length,
                        iframeCount: document.querySelectorAll('iframe').length,
                        hasTargetXpath: !!document.evaluate(
                            '/html/body/div/div[3]/div[2]',
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        ).singleNodeValue,
                        learningButtonCount: Array.from(document.querySelectorAll('*')).filter(el => 
                            (el.textContent || '').includes('继续学习') || 
                            (el.textContent || '').includes('开始学习')
                        ).length,
                        // 检查是否为课程列表页面
                        isCourseListPage: window.location.href.includes('study_center/tool_box/required')
                    };
                }
            """)
            
            logger.info(f"📍 当前URL: {page_check['url']}")
            logger.info(f"📄 页面标题: {page_check['title']}")
            logger.info(f"🎬 视频元素: {page_check['videoCount']}个")
            logger.info(f"🖼️  iframe元素: {page_check['iframeCount']}个")
            logger.info(f"🎯 目标xpath存在: {page_check['hasTargetXpath']}")
            logger.info(f"🔘 学习按钮数: {page_check['learningButtonCount']}个")
            
            # 严格检查是否为视频页面
            if page_check['isCourseListPage']:
                logger.error("❌ 错误：当前页面是课程列表页面，不是视频播放页面！")
                logger.error("💡 请手动点击课程进入视频播放页面，然后重新运行脚本")
                return
            
            if page_check['videoCount'] == 0 and page_check['iframeCount'] == 0:
                logger.warning("⚠️  警告：当前页面未检测到视频或iframe元素")
                should_continue = input("是否仍要继续监控？(y/n): ")
                if should_continue.lower() != 'y':
                    return
            
            # 确认是视频页面，开始监控
            logger.info("\n✅ 确认当前为视频播放页面，开始监控")
            
            # 获取初始快照
            logger.info("\n📸 获取视频页面初始快照...")
            initial_snapshot = await get_page_snapshot(page, "监控开始前")
            
            # 指导用户操作
            logger.info("\n" + "="*80)
            logger.info("👆 现在请在视频页面点击'继续学习'按钮")
            logger.info("="*80)
            logger.info("📝 操作说明:")
            logger.info("1. 在当前视频页面找到'继续学习'或'开始学习'按钮")
            logger.info("2. 点击该按钮（可能是弹窗或页面按钮）")
            logger.info("3. 不要关闭任何弹窗，让脚本记录变化")
            logger.info("4. 脚本将监控90秒的变化")
            
            # 开始监控
            logger.info("\n⏰ 开始监控页面变化（90秒）...")
            logger.info("💡 每5秒检查一次页面状态")
            
            previous_snapshot = initial_snapshot
            changes_detected = []
            
            for i in range(18):  # 90秒，每5秒检查一次
                await asyncio.sleep(5)
                
                current_snapshot = await get_page_snapshot(page, f"第{i+1}次检查")
                changes = analyze_changes(previous_snapshot, current_snapshot)
                
                # 检查重要变化
                has_important_change = (
                    changes['video_count_diff'] != 0 or
                    changes['video_state_changes'] or
                    changes['xpath_changes'] or
                    changes['popup_count_diff'] != 0 or
                    abs(changes['element_count_diff']) > 10
                )
                
                if has_important_change:
                    logger.info(f"🚨 第{i+1}次检查：检测到重要变化！")
                    if changes['video_count_diff'] > 0:
                        logger.info(f"  ➕ 新增{changes['video_count_diff']}个视频")
                    if changes['video_state_changes']:
                        logger.info(f"  ▶️  {len(changes['video_state_changes'])}个视频状态变化")
                        for change in changes['video_state_changes']:
                            status = "开始播放" if not change['now_paused'] else "暂停"
                            logger.info(f"    视频{change['index']}: {status}")
                    if changes['xpath_changes']:
                        logger.info(f"  🎯 xpath元素变化: {list(changes['xpath_changes'].keys())}")
                    if changes['popup_count_diff'] != 0:
                        logger.info(f"  🪟 弹窗变化: {changes['popup_count_diff']}")
                        
                    changes_detected.append({
                        'check_number': i+1,
                        'time': current_snapshot['readable_time'],
                        'changes': changes,
                        'snapshot': current_snapshot
                    })
                else:
                    logger.info(f"⏱️  第{i+1}次检查：无重要变化（元素变化: {changes['element_count_diff']}）")
                
                previous_snapshot = current_snapshot
            
            # 获取最终快照并分析
            logger.info("\n📸 获取最终快照...")
            final_snapshot = await get_page_snapshot(page, "监控结束")
            
            logger.info("\n" + "="*80)
            logger.info("📊 最终分析报告")
            logger.info("="*80)
            
            final_changes = analyze_changes(initial_snapshot, final_snapshot)
            display_final_analysis(final_changes, changes_detected)
            
            # 生成建议
            generate_recommendations(final_changes, changes_detected)
            
            # 保存结果
            save_results(initial_snapshot, final_snapshot, final_changes, changes_detected)
            
            logger.info("\n🔍 保持浏览器打开60秒以便观察...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

async def get_page_snapshot(page, label):
    """获取页面快照"""
    snapshot = await page.evaluate("""
        () => {
            const snapshot = {
                timestamp: Date.now(),
                url: window.location.href,
                title: document.title,
                elementCount: document.querySelectorAll('*').length,
                videos: [],
                iframes: [],
                popups: [],
                xpathElements: {},
                learningButtons: []
            };
            
            // 视频元素
            document.querySelectorAll('video').forEach((video, index) => {
                const rect = video.getBoundingClientRect();
                snapshot.videos.push({
                    index: index,
                    src: video.src || video.currentSrc || '无源',
                    visible: rect.width > 0 && rect.height > 0,
                    paused: video.paused,
                    duration: isNaN(video.duration) ? 0 : video.duration,
                    currentTime: video.currentTime,
                    readyState: video.readyState
                });
            });
            
            // iframe元素
            document.querySelectorAll('iframe').forEach((iframe, index) => {
                const rect = iframe.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    snapshot.iframes.push({
                        index: index,
                        src: iframe.src || '无源',
                        width: rect.width,
                        height: rect.height
                    });
                }
            });
            
            // 弹窗元素
            ['.el-dialog', '.modal', '.popup', '[role="dialog"]'].forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    if (rect.width > 0 && rect.height > 0 && style.display !== 'none') {
                        snapshot.popups.push({
                            selector: selector,
                            text: (el.textContent || '').substring(0, 100)
                        });
                    }
                });
            });
            
            // xpath检查
            const xpaths = ['/html/body/div/div[3]/div[2]', '/html/body/div/div[2]/div[2]', '/html/body/div/div[4]/div[2]'];
            xpaths.forEach(xpath => {
                const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const element = result.singleNodeValue;
                if (element) {
                    const rect = element.getBoundingClientRect();
                    snapshot.xpathElements[xpath] = {
                        exists: true,
                        visible: rect.width > 0 && rect.height > 0,
                        tag: element.tagName,
                        class: element.className || '',
                        text: (element.textContent || '').substring(0, 100)
                    };
                } else {
                    snapshot.xpathElements[xpath] = { exists: false };
                }
            });
            
            // 学习按钮
            document.querySelectorAll('*').forEach(el => {
                const text = el.textContent || '';
                if ((text.includes('继续学习') || text.includes('开始学习')) && text.length < 50) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        snapshot.learningButtons.push({
                            tag: el.tagName,
                            class: el.className || '',
                            text: text.trim()
                        });
                    }
                }
            });
            
            return snapshot;
        }
    """)
    
    snapshot['label'] = label
    snapshot['readable_time'] = time.strftime('%H:%M:%S', time.localtime(snapshot['timestamp'] / 1000))
    
    logger.info(f"✅ 快照完成: {snapshot['elementCount']}个元素, {len(snapshot['videos'])}个视频, {len(snapshot['popups'])}个弹窗")
    return snapshot

def analyze_changes(before, after):
    """分析页面变化"""
    changes = {
        'element_count_diff': after['elementCount'] - before['elementCount'],
        'video_count_diff': len(after['videos']) - len(before['videos']),
        'video_state_changes': [],
        'popup_count_diff': len(after['popups']) - len(before['popups']),
        'xpath_changes': {}
    }
    
    # 视频状态变化
    for i, after_video in enumerate(after['videos']):
        if i < len(before['videos']):
            before_video = before['videos'][i]
            if after_video['paused'] != before_video['paused']:
                changes['video_state_changes'].append({
                    'index': i,
                    'was_paused': before_video['paused'],
                    'now_paused': after_video['paused']
                })
    
    # xpath变化
    for xpath in after['xpathElements']:
        before_exists = before['xpathElements'].get(xpath, {}).get('exists', False)
        after_exists = after['xpathElements'][xpath]['exists']
        if before_exists != after_exists:
            changes['xpath_changes'][xpath] = {
                'before': before_exists,
                'after': after_exists,
                'info': after['xpathElements'][xpath] if after_exists else None
            }
    
    return changes

def display_final_analysis(changes, detected_changes):
    """显示最终分析"""
    logger.info(f"📊 元素数量变化: {changes['element_count_diff']}")
    logger.info(f"🎬 视频数量变化: {changes['video_count_diff']}")
    logger.info(f"🪟 弹窗数量变化: {changes['popup_count_diff']}")
    
    if changes['video_state_changes']:
        logger.info("▶️  视频状态变化:")
        for change in changes['video_state_changes']:
            status = "播放" if not change['now_paused'] else "暂停"
            logger.info(f"  视频{change['index']}: 变为{status}")
    
    if changes['xpath_changes']:
        logger.info("🎯 xpath元素变化:")
        for xpath, change in changes['xpath_changes'].items():
            logger.info(f"  {xpath}: {change['before']} → {change['after']}")
            if change['info']:
                logger.info(f"    {change['info']['tag']}.{change['info']['class']}")
    
    logger.info(f"📈 监控期间检测到 {len(detected_changes)} 次重要变化")

def generate_recommendations(final_changes, detected_changes):
    """生成解决方案建议"""
    logger.info("\n💡 自动化建议:")
    logger.info("="*50)
    
    if final_changes['video_state_changes']:
        logger.info("🎯 发现视频状态变化!")
        logger.info("💡 建议: 监控视频播放状态，实现播放控制")
        
    elif any(change['after'] and not change['before'] for change in final_changes['xpath_changes'].values()):
        logger.info("🎯 发现新出现的xpath元素!")
        for xpath, change in final_changes['xpath_changes'].items():
            if change['after'] and not change['before']:
                logger.info(f"💡 建议: 点击xpath元素 {xpath}")
                
    elif final_changes['popup_count_diff'] != 0:
        logger.info("🎯 发现弹窗变化!")
        logger.info("💡 建议: 处理弹窗元素")
        
    else:
        logger.info("❓ 未检测到明显变化")
        if len(detected_changes) == 0:
            logger.info("💡 建议:")
            logger.info("  1. 确认是否点击了正确的按钮")
            logger.info("  2. 检查页面是否需要特殊处理")
            logger.info("  3. 尝试不同的操作序列")

def save_results(initial, final, changes, detected_changes):
    """保存分析结果"""
    result = {
        'analysis_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'initial_snapshot': initial,
        'final_snapshot': final,
        'final_changes': changes,
        'detected_changes': detected_changes
    }
    
    with open('video_page_monitor_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info("✅ 结果已保存到 video_page_monitor_result.json")

if __name__ == "__main__":
    asyncio.run(monitor_video_page_only())