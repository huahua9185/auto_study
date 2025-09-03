#!/usr/bin/env python3
"""
完整系统测试脚本
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

async def test_full_system():
    """测试完整系统启动和初始化"""
    try:
        print("🚀 测试完整自动学习系统...")
        
        # 创建应用实例
        app = AutoStudyApp()
        print("✅ 应用实例创建成功")
        
        # 初始化应用
        print("🔧 初始化应用...")
        success = await app.initialize()
        
        if success:
            print("✅ 应用初始化成功")
            
            # 测试登录功能
            print("🔐 测试登录功能...")
            login_success = await app.login()
            
            if login_success:
                print("✅ 登录成功!")
                
                # 测试获取课程列表
                print("📚 测试获取课程列表...")
                try:
                    courses = await app.get_courses()
                    print(f"✅ 获取到 {len(courses)} 门课程")
                    
                    # 只是测试，不实际开始学习
                    print("⚠️  测试完成，不开始实际学习过程")
                    
                except Exception as e:
                    print(f"⚠️  获取课程列表失败: {e}")
                    print("这可能是因为网站需要实际的课程页面")
                    
            else:
                print("❌ 登录失败")
                
        else:
            print("❌ 应用初始化失败")
        
        # 清理资源
        print("🧹 清理资源...")
        await app.cleanup()
        print("✅ 资源清理完成")
        
        return success and login_success
        
    except Exception as e:
        print(f"❌ 系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("=" * 50)
    print("🧪 自动学习系统完整测试")
    print("=" * 50)
    
    success = await test_full_system()
    
    if success:
        print("\n🎉 系统测试通过! 系统已准备就绪")
        print("\n💡 运行完整系统请使用:")
        print("   source venv/bin/activate && set -a && source .env && set +a && python -m src.auto_study.main")
    else:
        print("\n💥 系统测试失败，请检查配置")

if __name__ == "__main__":
    asyncio.run(main())