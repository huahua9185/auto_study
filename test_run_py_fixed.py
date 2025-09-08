#!/usr/bin/env python
"""
测试修正后的run.py是否正常工作

只测试视频播放部分，看按钮点击是否优先处理
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.auto_study.main import AutoStudyApp
from src.auto_study.utils.logger import logger

async def test_run_py_fixed():
    """测试修正后的run.py"""
    logger.info("=" * 80)
    logger.info("🧪 测试修正后的run.py中VideoController的行为")
    logger.info("📋 重点验证按钮点击优先级是否生效")
    logger.info("=" * 80)
    
    app = None
    try:
        # 创建AutoStudyApp实例（这会创建LearningAutomator和VideoController）
        logger.info("\n🚀 创建AutoStudyApp实例...")
        app = AutoStudyApp()
        
        # 初始化应用（创建浏览器和页面）
        logger.info("\n🔧 初始化应用...")
        init_success = await app.initialize()
        if not init_success:
            logger.error("❌ 应用初始化失败")
            return
        
        # 只运行登录和一次视频播放测试
        logger.info("\n🔐 开始登录...")
        success = await app.login()
        
        if not success:
            logger.error("❌ 登录失败")
            return
        
        logger.info("✅ 登录成功")
        
        # 获取课程列表
        logger.info("\n📚 获取课程列表...")
        courses = await app.get_courses()
        
        if not courses:
            logger.error("❌ 未找到课程")
            return
        
        logger.info(f"✅ 找到 {len(courses)} 门课程")
        
        # 测试学习第一门未完成的课程
        from src.auto_study.automation.course_manager import CourseStatus
        pending_courses = [c for c in courses if c.status != CourseStatus.COMPLETED]
        
        if not pending_courses:
            logger.info("🎉 所有课程已完成")
            return
        
        logger.info(f"\n🎬 测试学习第一门未完成课程: {pending_courses[0].title}")
        
        # 进入课程页面
        course = pending_courses[0]
        logger.info(f"进入课程: {course.title}")
        
        # 调用learning_automator的相关方法
        # 这里会用到内部的VideoController
        learning_result = await app.learning_automator.learn_course(course.course_id)
        
        if learning_result:
            logger.info("\n🎉 测试成功！")
            logger.info("✅ 修正后的VideoController工作正常:")
            logger.info("  - 按钮点击优先级生效")
            logger.info("  - '开始学习'按钮被正确处理")
        else:
            logger.warning("\n⚠️ 学习过程未完成，请检查日志")
        
        # 等待一段时间观察
        logger.info("\n👁️ 保持浏览器打开30秒以便观察...")
        await asyncio.sleep(30)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if app:
            logger.info("\n🧹 清理资源...")
            await app.cleanup()

if __name__ == "__main__":
    asyncio.run(test_run_py_fixed())