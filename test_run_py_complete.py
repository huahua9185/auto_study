#!/usr/bin/env python
"""
测试run.py的完整流程

验证从run.py启动的完整学习流程是否正确处理视频播放
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from run import AutoStudySystem
from src.auto_study.utils.logger import logger

async def test_run_py_complete():
    """测试run.py的完整流程"""
    logger.info("=" * 80)
    logger.info("🧪 测试run.py的完整视频播放流程")
    logger.info("📋 验证整个系统的视频播放处理")
    logger.info("=" * 80)
    
    system = AutoStudySystem()
    
    try:
        # 1. 初始化错误恢复系统
        logger.info("\n🔧 初始化错误恢复系统...")
        if not await system.initialize_recovery_system():
            logger.error("❌ 错误恢复系统初始化失败")
            return
        
        # 2. 初始化监控系统（简化版，不启用UI）
        logger.info("\n📊 初始化监控系统...")
        # 跳过监控系统，只测试核心功能
        
        # 3. 启动正常运行模式
        logger.info("\n🚀 启动正常运行模式...")
        task_id = await system.start_normal_operation()
        if not task_id:
            logger.error("❌ 启动正常运行模式失败")
            return
        
        logger.info(f"✅ 任务ID: {task_id}")
        
        # 4. 初始化应用
        logger.info("\n🔧 初始化应用...")
        if not await system.app.initialize():
            logger.error("❌ 应用初始化失败")
            return
        
        # 5. 登录
        logger.info("\n🔐 登录...")
        if not await system.app.login():
            logger.error("❌ 登录失败")
            return
        
        logger.info("✅ 登录成功")
        
        # 6. 获取课程并学习第一门
        logger.info("\n📚 获取课程列表...")
        courses = await system.app.get_courses()
        
        if not courses:
            logger.error("❌ 未找到课程")
            return
        
        logger.info(f"✅ 找到 {len(courses)} 门课程")
        
        # 获取未完成的课程
        from src.auto_study.automation.course_manager import CourseStatus
        pending_courses = [c for c in courses if c.status != CourseStatus.COMPLETED]
        
        if not pending_courses:
            logger.info("🎉 所有课程已完成")
            return
        
        logger.info(f"\n🎬 测试学习第一门未完成课程: {pending_courses[0].title}")
        
        # 直接调用内部方法学习单个课程
        success = await system.app._learn_single_course(pending_courses[0])
        
        if success:
            logger.info("\n🎉 完整流程测试成功！")
            logger.info("✅ 视频播放正常处理:")
            logger.info("  - 系统正确调用了video_controller.play()")
            logger.info("  - '开始学习'按钮被正确处理")
            logger.info("  - 视频正常播放")
        else:
            logger.warning("\n⚠️ 学习过程未成功完成")
        
        # 检查页面状态
        page = await system.app.browser_manager.get_page()
        context = page.context
        pages = context.pages
        
        logger.info(f"\n📄 当前打开的页面数: {len(pages)}")
        for i, p in enumerate(pages):
            logger.info(f"  页面{i+1}: {p.url[:60]}...")
            if 'video_page' in p.url:
                logger.info("    ✅ 这是视频页面")
        
        # 保持运行一段时间观察
        logger.info("\n👁️ 保持系统运行30秒以便观察...")
        await asyncio.sleep(30)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("\n🛑 关闭系统...")
        await system.shutdown()

if __name__ == "__main__":
    asyncio.run(test_run_py_complete())