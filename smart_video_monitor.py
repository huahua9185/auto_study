#!/usr/bin/env python
"""
智能视频页面监控器

自动帮助用户从课程列表进入视频页面，然后监控点击变化
"""

import asyncio
from playwright.async_api import async_playwright
from src.auto_study.automation.auto_login import AutoLogin
from src.auto_study.utils.logger import logger
import json
import time

async def smart_video_monitor():
    """智能视频页面监控"""
    logger.info("=" * 80)
    logger.info("🎯 智能视频页面监控器")
    logger.info("📋 目标：自动进入视频页面并监控'继续学习'按钮点击效果")
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
            
            # 尝试自动进入视频页面
            logger.info("🎯 步骤 3: 尝试自动进入视频页面...")
            video_page_url = await attempt_enter_video_page(page)
            
            if not video_page_url:
                logger.info("🤏 自动进入失败，需要手动操作...")
                logger.info("👆 请手动点击任一'继续学习'按钮进入视频页面")
                logger.info("⏰ 等待60秒供手动操作...")
                
                initial_url = page.url
                for i in range(60):
                    await asyncio.sleep(1)
                    current_url = page.url
                    if current_url != initial_url:
                        logger.info(f"🎉 检测到页面跳转: {current_url}")
                        video_page_url = current_url
                        break
                    elif i % 10 == 0:
                        logger.info(f"⏱️  还有{60-i}秒...")
                
                if not video_page_url:
                    logger.error("❌ 未能进入视频页面")
                    return
            
            # 等待视频页面加载
            logger.info("⏳ 等待视频页面完全加载...")
            await page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(5)
            
            # 验证是否成功进入视频页面
            page_verification = await verify_video_page(page)
            if not page_verification['is_video_page']:
                logger.warning("⚠️  当前页面可能不是视频播放页面")
                logger.info("💡 但仍继续监控，因为可能页面结构有变化")
            else:
                logger.info("✅ 确认成功进入视频播放页面")
            
            # 开始监控视频页面
            logger.info("\n" + "="*80)
            logger.info("🔍 开始监控视频页面的'继续学习'按钮点击效果")
            logger.info("="*80)
            
            await monitor_video_page_clicks(page)
            
            logger.info("\n🔍 保持浏览器打开60秒以便观察...")
            await asyncio.sleep(60)
            
        finally:
            await browser.close()

async def attempt_enter_video_page(page):
    """尝试自动进入视频页面"""
    logger.info("🔍 查找可用的'继续学习'按钮...")
    
    # 查找所有可能的继续学习按钮
    buttons_info = await page.evaluate("""
        () => {
            const buttons = [];
            // 查找所有可能的按钮
            const selectors = ['div.btn', 'button', '.continue-btn', '[onclick*="学习"]'];
            
            selectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach((el, index) => {
                    const text = el.textContent || '';
                    if (text.includes('继续学习') || text.includes('开始学习')) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            buttons.push({
                                selector: selector,
                                index: index,
                                text: text.trim(),
                                rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                            });
                        }
                    }
                });
            });
            return buttons;
        }
    """)
    
    logger.info(f"🔘 找到 {len(buttons_info)} 个可用的学习按钮")
    
    if not buttons_info:
        logger.warning("❌ 未找到'继续学习'按钮")
        return None
    
    # 尝试点击第一个按钮
    initial_url = page.url
    logger.info(f"🖱️  尝试点击第一个按钮: '{buttons_info[0]['text']}'")
    
    try:
        # 使用JavaScript点击
        clicked = await page.evaluate(f"""
            () => {{
                const buttons = document.querySelectorAll('{buttons_info[0]['selector']}');
                if (buttons[{buttons_info[0]['index']}]) {{
                    buttons[{buttons_info[0]['index']}].click();
                    return true;
                }}
                return false;
            }}
        """)
        
        if clicked:
            logger.info("✅ 成功点击按钮")
            # 等待页面响应
            await asyncio.sleep(5)
            
            new_url = page.url
            if new_url != initial_url:
                logger.info(f"🎉 页面已跳转: {new_url}")
                return new_url
            else:
                logger.warning("❌ 点击后页面未跳转")
                return None
        else:
            logger.error("❌ 点击失败")
            return None
            
    except Exception as e:
        logger.error(f"❌ 点击时发生异常: {e}")
        return None

async def verify_video_page(page):
    """验证是否为视频页面"""
    verification = await page.evaluate("""
        () => {
            return {
                url: window.location.href,
                title: document.title,
                videoCount: document.querySelectorAll('video').length,
                iframeCount: document.querySelectorAll('iframe').length,
                hasXpathTarget: !!document.evaluate(
                    '/html/body/div/div[3]/div[2]',
                    document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                ).singleNodeValue,
                hasVideoKeywords: document.body.innerHTML.includes('播放') || 
                                document.body.innerHTML.includes('视频') ||
                                document.title.includes('播放'),
                isCourseList: window.location.href.includes('study_center/tool_box/required')
            };
        }
    """)
    
    verification['is_video_page'] = (
        verification['videoCount'] > 0 or 
        verification['iframeCount'] > 0 or 
        verification['hasXpathTarget'] or 
        verification['hasVideoKeywords']
    ) and not verification['isCourseList']
    
    logger.info(f"📊 页面验证结果:")
    logger.info(f"  🎬 视频元素: {verification['videoCount']}个")
    logger.info(f"  🖼️  iframe元素: {verification['iframeCount']}个")
    logger.info(f"  🎯 目标xpath: {verification['hasXpathTarget']}")
    logger.info(f"  🔍 视频相关内容: {verification['hasVideoKeywords']}")
    logger.info(f"  ✅ 判定为视频页面: {verification['is_video_page']}")
    
    return verification

async def monitor_video_page_clicks(page):
    """监控视频页面点击变化"""
    logger.info("📸 获取初始页面状态...")
    
    initial_state = await get_page_state(page, "初始状态")
    
    # 指导用户点击
    logger.info("\n" + "="*60)
    logger.info("👆 请现在在视频页面点击'继续学习'或'开始学习'按钮")
    logger.info("="*60)
    logger.info("📝 监控说明:")
    logger.info("1. 在当前页面找到并点击'继续学习'按钮")
    logger.info("2. 可能是弹窗、对话框或页面按钮")
    logger.info("3. 点击后不要关闭弹窗，让脚本记录变化")
    logger.info("4. 脚本将监控120秒的变化")
    
    logger.info(f"\n⏰ 开始监控120秒...")
    
    changes_log = []
    previous_state = initial_state
    
    for i in range(24):  # 120秒，每5秒检查一次
        await asyncio.sleep(5)
        
        current_state = await get_page_state(page, f"监控点-{i+1}")
        changes = analyze_state_changes(previous_state, current_state)
        
        # 检查是否有重要变化
        has_change = (
            changes['videos']['count_changed'] or
            changes['videos']['state_changed'] or
            changes['popups']['count_changed'] or
            changes['xpath']['changed'] or
            abs(changes['basic']['element_diff']) > 15
        )
        
        if has_change:
            logger.info(f"🚨 第{i+1}次检查: 发现重要变化!")
            log_changes(changes, i+1)
            changes_log.append({
                'check': i+1,
                'time': current_state['time'],
                'changes': changes
            })
        else:
            logger.info(f"⏱️  第{i+1}次检查: 无重要变化")
        
        previous_state = current_state
    
    # 最终分析
    logger.info("\n" + "="*80)
    logger.info("📊 监控完成 - 最终分析")
    logger.info("="*80)
    
    final_state = await get_page_state(page, "最终状态")
    final_changes = analyze_state_changes(initial_state, final_state)
    
    display_final_results(final_changes, changes_log)
    save_monitor_results(initial_state, final_state, final_changes, changes_log)

async def get_page_state(page, label):
    """获取页面状态快照"""
    state = await page.evaluate("""
        () => {
            const state = {
                timestamp: Date.now(),
                url: window.location.href,
                title: document.title,
                totalElements: document.querySelectorAll('*').length,
                videos: [],
                popups: [],
                xpaths: {}
            };
            
            // 视频状态
            document.querySelectorAll('video').forEach((video, i) => {
                state.videos.push({
                    index: i,
                    src: video.src || video.currentSrc || '',
                    paused: video.paused,
                    duration: video.duration || 0,
                    currentTime: video.currentTime || 0
                });
            });
            
            // 弹窗状态
            ['.el-dialog', '.modal', '.popup', '[role="dialog"]'].forEach(sel => {
                const elements = document.querySelectorAll(sel);
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    if (rect.width > 0 && rect.height > 0 && style.display !== 'none') {
                        state.popups.push({
                            selector: sel,
                            text: (el.textContent || '').substring(0, 100)
                        });
                    }
                });
            });
            
            // xpath状态
            ['/html/body/div/div[3]/div[2]', '/html/body/div/div[2]/div[2]'].forEach(xpath => {
                const result = document.evaluate(xpath, document, null, 
                    XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const el = result.singleNodeValue;
                state.xpaths[xpath] = {
                    exists: !!el,
                    visible: el ? el.getBoundingClientRect().width > 0 : false,
                    text: el ? (el.textContent || '').substring(0, 50) : ''
                };
            });
            
            return state;
        }
    """)
    
    state['label'] = label
    state['time'] = time.strftime('%H:%M:%S', time.localtime(state['timestamp'] / 1000))
    return state

def analyze_state_changes(before, after):
    """分析状态变化"""
    return {
        'basic': {
            'element_diff': after['totalElements'] - before['totalElements']
        },
        'videos': {
            'count_changed': len(after['videos']) != len(before['videos']),
            'state_changed': check_video_state_changes(before['videos'], after['videos'])
        },
        'popups': {
            'count_changed': len(after['popups']) != len(before['popups']),
            'diff': len(after['popups']) - len(before['popups'])
        },
        'xpath': {
            'changed': check_xpath_changes(before['xpaths'], after['xpaths'])
        }
    }

def check_video_state_changes(before_videos, after_videos):
    """检查视频状态变化"""
    changes = []
    for i, after_video in enumerate(after_videos):
        if i < len(before_videos):
            before_video = before_videos[i]
            if after_video['paused'] != before_video['paused']:
                changes.append({
                    'index': i,
                    'change': 'started' if before_video['paused'] and not after_video['paused'] else 'paused'
                })
    return changes

def check_xpath_changes(before_xpaths, after_xpaths):
    """检查xpath变化"""
    changes = {}
    for xpath in after_xpaths:
        before_state = before_xpaths.get(xpath, {'exists': False, 'visible': False})
        after_state = after_xpaths[xpath]
        
        if (before_state['exists'] != after_state['exists'] or 
            before_state['visible'] != after_state['visible']):
            changes[xpath] = {
                'before': before_state,
                'after': after_state
            }
    return changes

def log_changes(changes, check_num):
    """记录变化日志"""
    if changes['videos']['count_changed']:
        logger.info(f"  🎬 视频数量变化")
    
    if changes['videos']['state_changed']:
        for change in changes['videos']['state_changed']:
            action = "开始播放" if change['change'] == 'started' else "暂停"
            logger.info(f"  ▶️  视频{change['index']}: {action}")
    
    if changes['popups']['count_changed']:
        logger.info(f"  🪟 弹窗变化: {'+' if changes['popups']['diff'] > 0 else ''}{changes['popups']['diff']}")
    
    if changes['xpath']['changed']:
        for xpath, change in changes['xpath']['changed'].items():
            logger.info(f"  🎯 {xpath}: {change['before']['exists']}->{change['after']['exists']}")

def display_final_results(changes, changes_log):
    """显示最终结果"""
    logger.info(f"📈 监控期间检测到 {len(changes_log)} 次重要变化")
    logger.info(f"📊 总体元素变化: {changes['basic']['element_diff']}")
    
    if changes['videos']['state_changed']:
        logger.info("🎬 视频状态发生变化:")
        for change in changes['videos']['state_changed']:
            logger.info(f"  视频{change['index']}: {change['change']}")
    
    if changes['xpath']['changed']:
        logger.info("🎯 xpath元素变化:")
        for xpath, change in changes['xpath']['changed'].items():
            logger.info(f"  {xpath}: 存在({change['before']['exists']}->{change['after']['exists']})")
    
    # 生成建议
    logger.info("\n💡 自动化建议:")
    if changes['videos']['state_changed']:
        logger.info("✅ 发现视频播放状态变化，可以实现播放控制")
    elif changes['xpath']['changed']:
        logger.info("✅ 发现xpath元素变化，可以实现元素交互")
    elif changes['popups']['count_changed']:
        logger.info("✅ 发现弹窗变化，需要处理弹窗逻辑")
    else:
        logger.info("⚠️  未发现明显的有效变化，可能需要调整策略")

def save_monitor_results(initial, final, changes, log):
    """保存监控结果"""
    result = {
        'monitor_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'initial_state': initial,
        'final_state': final,
        'final_changes': changes,
        'changes_log': log
    }
    
    filename = 'smart_video_monitor_result.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 监控结果已保存到 {filename}")

if __name__ == "__main__":
    asyncio.run(smart_video_monitor())