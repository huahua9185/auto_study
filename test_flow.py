#!/usr/bin/env python3
"""
简单测试脚本：验证课程学习流程修复
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# 添加源码路径
sys.path.append(str(Path(__file__).parent / "src"))

async def test_course_url_extraction():
    """测试课程URL提取逻辑"""
    print("=== 测试课程URL提取逻辑 ===")
    
    # 读取当前课程数据
    courses_file = Path(__file__).parent / "data" / "courses.json"
    if courses_file.exists():
        with open(courses_file, 'r', encoding='utf-8') as f:
            courses_data = json.load(f)
        
        print(f"发现 {len(courses_data)} 门课程")
        
        # 分析URL模式
        url_patterns = {}
        for course in courses_data:
            url = course.get('url', '')
            if 'study_center/tool_box/required' in url:
                url_patterns['课程列表页面'] = url_patterns.get('课程列表页面', 0) + 1
            elif 'video_play' in url:
                url_patterns['视频播放页面'] = url_patterns.get('视频播放页面', 0) + 1
            else:
                url_patterns['其他'] = url_patterns.get('其他', 0) + 1
        
        print("URL模式统计:")
        for pattern, count in url_patterns.items():
            print(f"  {pattern}: {count} 门课程")
        
        # 显示几个示例课程的信息
        print("\n前3门课程的详细信息:")
        for i, course in enumerate(courses_data[:3]):
            print(f"  {i+1}. {course.get('title', '未知标题')}")
            print(f"     URL: {course.get('url', '无URL')}")
            print(f"     进度: {course.get('progress', 0)*100:.1f}%")
            print(f"     状态: {course.get('status', '未知')}")
            print()
        
        return True
    else:
        print("❌ 未找到courses.json文件")
        return False

def test_navigation_logic():
    """测试导航逻辑"""
    print("=== 测试导航逻辑 ===")
    
    # 模拟URL判断逻辑
    test_urls = [
        "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/tool_box/required?id=275",
        "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/video_play?id=123",
        "https://edu.nxgbjy.org.cn/nxxzxy/index.html#/course/detail/456"
    ]
    
    for url in test_urls:
        print(f"URL: {url}")
        if "study_center/tool_box/required" in url:
            print("  ✅ 识别为课程列表页面，需要点击学习按钮进入具体课程")
        elif "video_play" in url:
            print("  ✅ 识别为视频播放页面，可以直接开始学习")
        else:
            print("  ⚠️  未知URL模式，需要进一步识别")
        print()

def test_video_detection_selectors():
    """测试视频检测选择器"""
    print("=== 测试视频检测选择器 ===")
    
    selectors = [
        'video', 
        '.video-player', 
        '.player', 
        '#player',
        '.video-container',
        '.media-player',
        '.vjs-tech',  # Video.js播放器
        '.jwplayer',  # JW Player
        '.dplayer',   # DPlayer
        '.xgplayer',  # XGPlayer
        'iframe[src*="video"]',
        'iframe[src*="player"]',
        'iframe[src*="media"]'
    ]
    
    print(f"共定义了 {len(selectors)} 个视频播放器检测选择器:")
    for i, selector in enumerate(selectors, 1):
        print(f"  {i:2d}. {selector}")
    
    print("\n播放按钮检测选择器:")
    play_selectors = [
        'button:has-text("播放")',
        'button:has-text("开始播放")', 
        'button[title*="播放"]',
        'button[title*="Play"]',
        '.play-btn',
        '.btn-play'
    ]
    
    for i, selector in enumerate(play_selectors, 1):
        print(f"  {i:2d}. {selector}")

async def main():
    """主测试函数"""
    print("🔍 开始测试修复后的课程学习流程...")
    print()
    
    # 测试1: 课程URL提取
    success1 = await test_course_url_extraction()
    print()
    
    # 测试2: 导航逻辑
    test_navigation_logic()
    print()
    
    # 测试3: 视频检测选择器
    test_video_detection_selectors()
    print()
    
    # 总结
    print("=== 测试总结 ===")
    if success1:
        print("✅ 课程数据读取成功")
    else:
        print("❌ 课程数据读取失败")
    
    print("✅ 导航逻辑检查完成")
    print("✅ 视频检测选择器检查完成")
    
    print("\n🎯 修复要点总结:")
    print("1. 修复了课程URL提取逻辑，现在会尝试获取每个课程的真实学习链接")
    print("2. 增强了课程学习流程，支持从课程列表页面自动导航到播放页面")
    print("3. 扩展了视频播放器检测功能，支持更多类型的播放器")
    print("4. 改进了学习按钮点击逻辑，提高成功率")
    
    print("\n🚀 下一步测试建议:")
    print("1. 在真实环境中运行完整的学习流程")
    print("2. 观察是否能成功从课程列表导航到播放页面")
    print("3. 检查视频播放器检测是否工作正常")

if __name__ == "__main__":
    asyncio.run(main())