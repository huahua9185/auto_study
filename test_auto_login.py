#!/usr/bin/env python3
"""
自动登录测试脚本
"""

import asyncio
import sys
from pathlib import Path
import os

# 添加项目路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 应用PIL兼容性补丁
from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from playwright.async_api import async_playwright
from auto_study.automation.auto_login import AutoLogin

async def test_auto_login():
    """测试自动登录功能"""
    try:
        print("🔐 测试自动登录功能...")
        
        # 从环境变量获取用户名和密码
        username = os.getenv('AUTO_STUDY_USERNAME')
        password = os.getenv('AUTO_STUDY_PASSWORD')
        
        if not username or not password:
            print("❌ 未设置用户名和密码环境变量")
            print("请确保设置了 AUTO_STUDY_USERNAME 和 AUTO_STUDY_PASSWORD")
            return
        
        print(f"用户名: {username}")
        print(f"密码: {'*' * len(password)}")
        
        # 启动浏览器
        print("启动浏览器...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 创建自动登录实例
        auto_login = AutoLogin(page)
        
        # 执行登录
        print("开始自动登录...")
        success = await auto_login.login(username, password)
        
        if success:
            print("✅ 自动登录成功!")
            # 等待用户查看结果
            await asyncio.sleep(10)
        else:
            print("❌ 自动登录失败")
            # 等待用户查看失败页面
            await asyncio.sleep(10)
        
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()
        
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    success = await test_auto_login()
    
    if success:
        print("\n🎉 自动登录测试通过!")
        print("现在可以运行完整的自动学习系统了")
    else:
        print("\n💥 自动登录测试失败")
        print("请检查配置和网络连接")

if __name__ == "__main__":
    asyncio.run(main())