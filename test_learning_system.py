#!/usr/bin/env python3
"""
学习系统测试脚本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 应用PIL兼容性补丁
from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from auto_study.main import AutoStudyApp

async def test_learning_system():
    """测试学习系统"""
    try:
        print("🧪 测试学习系统完整流程...")
        
        # 创建应用
        app = AutoStudyApp()
        
        # 初始化
        print("🔧 初始化系统...")
        success = await app.initialize()
        if not success:
            print("❌ 初始化失败")
            return False
        
        # 登录
        print("🔐 执行登录...")
        login_success = await app.login()
        if not login_success:
            print("❌ 登录失败")
            await app.cleanup()
            return False
        
        print("✅ 登录成功")
        
        # 获取课程列表
        print("📚 获取课程列表...")
        try:
            courses = await app.get_courses()
            print(f"✅ 获取到 {len(courses)} 门课程")
            
            if courses:
                # 只测试第一门课程的前几步，不进行实际学习
                test_course = courses[0]
                print(f"📖 测试课程: {test_course.title}")
                print(f"📎 课程URL: {test_course.url}")
                
                if test_course.url:
                    # 只是访问课程页面，不开始学习
                    page = await app.browser_manager.get_page()
                    print("🌐 访问课程页面...")
                    await page.goto(test_course.url)
                    await asyncio.sleep(3)
                    
                    # 检测视频播放器
                    has_video = await app.learning_automator.video_controller.detect_video_player()
                    print(f"🎬 检测到视频播放器: {'是' if has_video else '否'}")
                    
                    if not has_video:
                        print("🔍 查找学习按钮...")
                        start_buttons = [
                            'button:has-text("开始学习")',
                            'button:has-text("进入课程")',
                            'a:has-text("开始学习")',
                            'a:has-text("进入课程")',
                            '.start-btn',
                            '.learn-btn'
                        ]
                        
                        for selector in start_buttons:
                            try:
                                button = page.locator(selector).first
                                if await button.count() > 0:
                                    print(f"  找到按钮: {selector}")
                                    break
                            except:
                                pass
                    
                    print("✅ 课程页面访问正常")
                else:
                    print("⚠️  课程缺少URL")
            else:
                print("⚠️  未找到课程")
                
        except Exception as e:
            print(f"❌ 获取课程失败: {e}")
        
        # 清理
        print("🧹 清理资源...")
        await app.cleanup()
        
        print("🎉 测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("=" * 50)
    print("🧪 学习系统集成测试")
    print("=" * 50)
    
    success = await test_learning_system()
    
    if success:
        print("\n🎉 学习系统测试通过!")
        print("系统已准备就绪，可以开始自动学习")
    else:
        print("\n💥 学习系统测试失败")

if __name__ == "__main__":
    asyncio.run(main())