#!/usr/bin/env python3
"""
测试课程提取逻辑
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from auto_study.utils.pil_compatibility import patch_ddddocr_compatibility
patch_ddddocr_compatibility()

from dotenv import load_dotenv
load_dotenv()

from auto_study.main import AutoStudy

async def test_course_extraction():
    """测试课程提取功能"""
    try:
        auto_study = AutoStudy()
        
        # 启动主程序，但我们会在登录后手动测试课程提取
        success = await auto_study.run()
        if success:
            print("测试完成")
        else:
            print("测试失败")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_course_extraction())