#!/usr/bin/env python3
"""
课程管理器测试脚本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from auto_study.config.config_manager import ConfigManager
from auto_study.automation.course_manager import CourseManager, Course, CourseStatus
from auto_study.utils.logger import logger

def test_course_manager():
    """测试课程管理器基本功能"""
    try:
        print("🧪 测试课程管理器...")
        
        # 创建配置管理器和课程管理器
        config_manager = ConfigManager()
        course_manager = CourseManager(config_manager)
        
        print("✅ 课程管理器创建成功")
        
        # 测试获取课程列表
        courses = course_manager.get_courses()
        print(f"📚 当前课程数量: {len(courses)}")
        
        # 创建一些测试课程
        test_courses = [
            Course(
                id="test1",
                title="测试课程1",
                url="http://example.com/course1",
                status=CourseStatus.NOT_STARTED,
                progress=0.0
            ),
            Course(
                id="test2", 
                title="测试课程2",
                url="http://example.com/course2",
                status=CourseStatus.IN_PROGRESS,
                progress=0.5
            ),
            Course(
                id="test3",
                title="测试课程3",
                url="http://example.com/course3", 
                status=CourseStatus.COMPLETED,
                progress=1.0
            )
        ]
        
        # 添加测试课程到缓存
        for course in test_courses:
            course_manager._courses_cache[course.id] = course
        
        # 保存缓存
        success = course_manager.save_courses_cache()
        print(f"💾 保存课程缓存: {'成功' if success else '失败'}")
        
        # 重新获取课程
        courses = course_manager.get_courses(reload=True)
        print(f"📚 重新加载后课程数量: {len(courses)}")
        
        # 测试按状态筛选
        completed_courses = course_manager.get_courses_by_status(CourseStatus.COMPLETED)
        pending_courses = [c for c in courses if c.status != CourseStatus.COMPLETED]
        
        print(f"✅ 已完成课程: {len(completed_courses)}")
        print(f"⏳ 待学习课程: {len(pending_courses)}")
        
        # 测试优先级排序
        sorted_courses = course_manager.sort_courses_by_priority(courses)
        print(f"🔢 按优先级排序: {len(sorted_courses)} 门课程")
        
        for i, course in enumerate(sorted_courses, 1):
            print(f"  {i}. {course.title} - {course.status.value} ({course.progress:.1%})")
        
        # 测试统计信息
        stats = course_manager.get_statistics()
        print("\n📊 统计信息:")
        for key, value in stats.items():
            if key != 'last_updated':
                print(f"  {key}: {value}")
        
        print("\n🎉 课程管理器测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_course_manager()
    sys.exit(0 if success else 1)