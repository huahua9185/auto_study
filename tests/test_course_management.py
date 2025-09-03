"""
课程管理核心测试

测试课程管理功能，包括课程数据模型、优先级排序、进度管理和数据持久化
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.auto_study.automation import (
    CourseManager, Course, CourseStatus, CoursePriority, get_course_manager
)
from src.auto_study.config.config_manager import ConfigManager


class TestCourse:
    """课程数据模型测试"""
    
    def setup_method(self):
        """设置测试"""
        self.sample_course_data = {
            'id': 'test_course_001',
            'title': '测试课程',
            'url': 'https://example.com/course/1',
            'status': CourseStatus.NOT_STARTED,
            'progress': 0.0,
            'description': '这是一个测试课程'
        }
    
    def test_course_creation(self):
        """测试课程创建"""
        course = Course(**self.sample_course_data)
        
        assert course.id == 'test_course_001'
        assert course.title == '测试课程'
        assert course.status == CourseStatus.NOT_STARTED
        assert course.progress == 0.0
        assert course.priority == CoursePriority.MEDIUM
    
    def test_course_post_init(self):
        """测试课程初始化后处理"""
        # 测试字符串状态转换
        data = self.sample_course_data.copy()
        data['status'] = 'in_progress'
        course = Course(**data)
        assert course.status == CourseStatus.IN_PROGRESS
        
        # 测试进度范围限制
        data['progress'] = 1.5
        course = Course(**data)
        assert course.progress == 1.0
        
        data['progress'] = -0.5
        course = Course(**data)
        assert course.progress == 0.0
    
    def test_course_completion_status(self):
        """测试课程完成状态判断"""
        course = Course(**self.sample_course_data)
        
        # 未开始状态
        assert not course.is_completed()
        assert not course.is_in_progress()
        
        # 进行中状态
        course.progress = 0.5
        assert not course.is_completed()
        assert course.is_in_progress()
        
        # 完成状态（通过进度）
        course.progress = 0.95
        assert course.is_completed()
        
        # 完成状态（通过状态）
        course.progress = 0.8
        course.status = CourseStatus.COMPLETED
        assert course.is_completed()
    
    def test_course_deadline_methods(self):
        """测试课程截止时间相关方法"""
        course = Course(**self.sample_course_data)
        
        # 无截止时间
        assert course.days_until_deadline() is None
        assert not course.is_overdue()
        
        # 设置未来截止时间
        future_date = datetime.now() + timedelta(days=5)
        course.deadline = future_date
        assert course.days_until_deadline() == 5
        assert not course.is_overdue()
        
        # 设置过期截止时间
        past_date = datetime.now() - timedelta(days=2)
        course.deadline = past_date
        assert course.days_until_deadline() == -2
        assert course.is_overdue()
    
    def test_course_urgency_score(self):
        """测试紧急度评分"""
        course = Course(**self.sample_course_data)
        
        # 无截止时间
        assert course.get_urgency_score() == 0.3
        
        # 不同时间段的紧急度
        test_cases = [
            (-1, 1.0),  # 已过期
            (0, 1.0),   # 今天到期
            (1, 0.9),   # 1天后到期
            (3, 0.7),   # 3天后到期
            (7, 0.5),   # 7天后到期
            (14, 0.3),  # 14天后到期
            (30, 0.1)   # 30天后到期
        ]
        
        for days, expected_score in test_cases:
            course.deadline = datetime.now() + timedelta(days=days)
            score = course.get_urgency_score()
            assert score == expected_score, f"Days: {days}, Expected: {expected_score}, Got: {score}"
    
    def test_course_priority_score(self):
        """测试优先级评分计算"""
        course = Course(**self.sample_course_data)
        
        # 基础评分
        score = course.calculate_priority_score()
        assert 0.0 <= score <= 1.0
        
        # 自定义权重
        custom_weights = {
            'urgency': 0.5,
            'priority': 0.3,
            'progress': 0.1,
            'access': 0.1
        }
        score_custom = course.calculate_priority_score(custom_weights)
        assert 0.0 <= score_custom <= 1.0
        
        # 高优先级课程应该有更高评分
        high_priority_course = Course(
            id='high_priority',
            title='高优先级课程',
            url='https://example.com/high',
            priority=CoursePriority.HIGH
        )
        high_score = high_priority_course.calculate_priority_score()
        
        normal_course = Course(
            id='normal',
            title='普通课程',
            url='https://example.com/normal',
            priority=CoursePriority.MEDIUM
        )
        normal_score = normal_course.calculate_priority_score()
        
        assert high_score > normal_score
    
    def test_course_serialization(self):
        """测试课程序列化和反序列化"""
        # 创建包含各种数据类型的课程
        course = Course(
            id='serialization_test',
            title='序列化测试',
            url='https://example.com/test',
            status=CourseStatus.IN_PROGRESS,
            progress=0.6,
            deadline=datetime.now() + timedelta(days=7),
            priority=CoursePriority.HIGH,
            description='测试描述',
            tags=['python', 'testing'],
            instructor='测试教师'
        )
        
        # 转为字典
        course_dict = course.to_dict()
        assert isinstance(course_dict, dict)
        assert course_dict['status'] == 'in_progress'
        assert course_dict['priority'] == 4
        assert isinstance(course_dict['deadline'], str)
        
        # 从字典恢复
        restored_course = Course.from_dict(course_dict)
        assert restored_course.id == course.id
        assert restored_course.title == course.title
        assert restored_course.status == course.status
        assert restored_course.priority == course.priority
        assert isinstance(restored_course.deadline, datetime)


class TestCourseManager:
    """课程管理器测试"""
    
    def setup_method(self):
        """设置测试"""
        self.config_manager = Mock()
        self.config_manager.get_config.return_value = {
            'system': {'data_dir': tempfile.mkdtemp()},
            'course_management': {
                'course_list_url': 'https://example.com/courses',
                'priority_weights': {
                    'urgency': 0.4,
                    'priority': 0.3,
                    'progress': 0.2,
                    'access': 0.1
                }
            }
        }
        self.manager = CourseManager(self.config_manager)
    
    def create_sample_courses(self) -> list:
        """创建示例课程"""
        return [
            Course(
                id='course_001',
                title='Python基础',
                url='https://example.com/python-basics',
                status=CourseStatus.IN_PROGRESS,
                progress=0.3,
                priority=CoursePriority.HIGH
            ),
            Course(
                id='course_002',
                title='数据结构',
                url='https://example.com/data-structures',
                status=CourseStatus.NOT_STARTED,
                progress=0.0,
                priority=CoursePriority.MEDIUM,
                deadline=datetime.now() + timedelta(days=3)
            ),
            Course(
                id='course_003',
                title='算法设计',
                url='https://example.com/algorithms',
                status=CourseStatus.COMPLETED,
                progress=1.0,
                priority=CoursePriority.LOW
            )
        ]
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        assert self.manager.config_manager == self.config_manager
        assert self.manager.data_dir.exists()
        assert isinstance(self.manager._courses_cache, dict)
        assert not self.manager._cache_loaded
    
    def test_save_and_load_courses_cache(self):
        """测试课程缓存保存和加载"""
        # 创建示例课程并添加到缓存
        courses = self.create_sample_courses()
        for course in courses:
            self.manager._courses_cache[course.id] = course
        
        # 保存缓存
        success = self.manager.save_courses_cache()
        assert success
        assert self.manager.courses_file.exists()
        
        # 清空缓存
        self.manager._courses_cache.clear()
        self.manager._cache_loaded = False
        
        # 加载缓存
        self.manager._load_courses_cache()
        
        assert len(self.manager._courses_cache) == 3
        assert 'course_001' in self.manager._courses_cache
        
        # 验证数据完整性
        loaded_course = self.manager._courses_cache['course_001']
        assert loaded_course.title == 'Python基础'
        assert loaded_course.status == CourseStatus.IN_PROGRESS
        assert loaded_course.progress == 0.3
    
    def test_parse_progress(self):
        """测试进度解析"""
        # 创建模拟的进度元素
        progress_element = Mock()
        
        # 测试data-progress属性
        progress_element.get_attribute.return_value = "75"
        progress_element.text_content.return_value = ""
        progress = self.manager._parse_progress(progress_element)
        assert progress == 0.75
        
        # 测试百分比属性（>1的值）
        progress_element.get_attribute.return_value = "85"
        progress = self.manager._parse_progress(progress_element)
        assert progress == 0.85
        
        # 测试样式width
        progress_element.get_attribute.side_effect = lambda x: "width: 60%" if x == 'style' else None
        progress = self.manager._parse_progress(progress_element)
        assert progress == 0.6
        
        # 测试文本内容百分比
        progress_element.get_attribute.return_value = None
        progress_element.text_content.return_value = "完成度: 45%"
        progress = self.manager._parse_progress(progress_element)
        assert progress == 0.45
        
        # 测试分数形式
        progress_element.text_content.return_value = "已完成 3/10"
        progress = self.manager._parse_progress(progress_element)
        assert progress == 0.3
    
    def test_parse_status(self):
        """测试状态解析"""
        status_element = Mock()
        
        # 测试不同状态关键词
        test_cases = [
            ("已完成", 0.5, CourseStatus.COMPLETED),
            ("进行中", 0.3, CourseStatus.IN_PROGRESS),
            ("未开始", 0.0, CourseStatus.NOT_STARTED),
            ("锁定", 0.0, CourseStatus.LOCKED),
            ("过期", 0.0, CourseStatus.EXPIRED),
        ]
        
        for text, progress, expected_status in test_cases:
            status_element.text_content.return_value = text
            status = self.manager._parse_status(status_element, progress)
            assert status == expected_status
        
        # 测试根据进度推断状态
        status_element.text_content.return_value = "其他状态"
        
        # 完成状态（进度>=0.95）
        status = self.manager._parse_status(status_element, 0.95)
        assert status == CourseStatus.COMPLETED
        
        # 进行中状态（0<进度<0.95）
        status = self.manager._parse_status(status_element, 0.5)
        assert status == CourseStatus.IN_PROGRESS
        
        # 未开始状态（进度=0）
        status = self.manager._parse_status(status_element, 0.0)
        assert status == CourseStatus.NOT_STARTED
    
    def test_extract_single_course(self):
        """测试单个课程信息提取"""
        mock_page = Mock()
        mock_course_element = Mock()
        
        # 模拟页面元素
        mock_title_element = Mock()
        mock_title_element.text_content.return_value = "测试课程"
        
        mock_link_element = Mock()
        mock_link_element.get_attribute.return_value = "/course/123"
        
        mock_progress_element = Mock()
        mock_progress_element.get_attribute.return_value = "60"
        
        mock_status_element = Mock()
        mock_status_element.text_content.return_value = "进行中"
        
        mock_desc_element = Mock()
        mock_desc_element.text_content.return_value = "课程描述"
        
        # 模拟页面URL
        mock_page.url = "https://example.com"
        
        with patch.object(self.manager, 'find_element_by_selectors') as mock_find:
            mock_find.side_effect = [
                mock_title_element,   # title
                mock_link_element,    # link
                mock_progress_element, # progress
                mock_status_element,  # status
                mock_desc_element     # description
            ]
            
            course = self.manager._extract_single_course(mock_page, mock_course_element, 0)
            
            assert course is not None
            assert course.title == "测试课程"
            assert course.url == "https://example.com/course/123"
            assert course.progress == 0.6
            assert course.status == CourseStatus.IN_PROGRESS
            assert course.description == "课程描述"
    
    def test_get_courses_by_status(self):
        """测试按状态获取课程"""
        courses = self.create_sample_courses()
        for course in courses:
            self.manager._courses_cache[course.id] = course
        self.manager._cache_loaded = True
        
        # 获取进行中的课程
        in_progress_courses = self.manager.get_courses_by_status(CourseStatus.IN_PROGRESS)
        assert len(in_progress_courses) == 1
        assert in_progress_courses[0].title == "Python基础"
        
        # 获取已完成的课程
        completed_courses = self.manager.get_courses_by_status(CourseStatus.COMPLETED)
        assert len(completed_courses) == 1
        assert completed_courses[0].title == "算法设计"
        
        # 获取未开始的课程
        not_started_courses = self.manager.get_courses_by_status(CourseStatus.NOT_STARTED)
        assert len(not_started_courses) == 1
        assert not_started_courses[0].title == "数据结构"
    
    def test_sort_courses_by_priority(self):
        """测试按优先级排序课程"""
        courses = self.create_sample_courses()
        
        # 设置不同的访问时间和紧急度
        courses[0].last_accessed = datetime.now()  # 最近访问
        courses[1].deadline = datetime.now() + timedelta(days=1)  # 紧急
        courses[2].progress = 1.0  # 已完成
        
        sorted_courses = self.manager.sort_courses_by_priority(courses)
        
        assert len(sorted_courses) == 3
        # 验证排序逻辑（具体顺序取决于权重计算）
        assert all(isinstance(course, Course) for course in sorted_courses)
        
        # 测试自定义权重
        custom_weights = {
            'urgency': 0.6,  # 更高的紧急度权重
            'priority': 0.2,
            'progress': 0.1,
            'access': 0.1
        }
        
        custom_sorted = self.manager.sort_courses_by_priority(courses, custom_weights)
        assert len(custom_sorted) == 3
    
    def test_get_urgent_courses(self):
        """测试获取紧急课程"""
        courses = self.create_sample_courses()
        
        # 设置不同的截止时间
        courses[0].deadline = datetime.now() + timedelta(days=2)  # 紧急
        courses[1].deadline = datetime.now() + timedelta(days=10) # 不紧急
        courses[2].deadline = None  # 无截止时间
        
        for course in courses:
            self.manager._courses_cache[course.id] = course
        self.manager._cache_loaded = True
        
        urgent_courses = self.manager.get_urgent_courses(days_threshold=7)
        
        # 应该只有一个紧急课程（未完成且截止时间<=7天）
        assert len(urgent_courses) == 1
        assert urgent_courses[0].id == 'course_001'
    
    def test_update_course_progress(self):
        """测试更新课程进度"""
        courses = self.create_sample_courses()
        for course in courses:
            self.manager._courses_cache[course.id] = course
        self.manager._cache_loaded = True
        
        # 更新进度
        success = self.manager.update_course_progress('course_001', 0.8)
        assert success
        
        updated_course = self.manager.get_course_by_id('course_001')
        assert updated_course.progress == 0.8
        assert updated_course.status == CourseStatus.IN_PROGRESS
        
        # 更新到完成状态
        success = self.manager.update_course_progress('course_001', 0.95)
        assert success
        
        completed_course = self.manager.get_course_by_id('course_001')
        assert completed_course.progress == 0.95
        assert completed_course.status == CourseStatus.COMPLETED
        
        # 更新不存在的课程
        success = self.manager.update_course_progress('nonexistent', 0.5)
        assert not success
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        courses = self.create_sample_courses()
        for course in courses:
            self.manager._courses_cache[course.id] = course
        self.manager._cache_loaded = True
        
        stats = self.manager.get_statistics()
        
        assert stats['total_courses'] == 3
        assert stats['completed_courses'] == 1
        assert stats['in_progress_courses'] == 1
        assert stats['not_started_courses'] == 1
        assert stats['completion_rate'] == 1/3
        assert 0.0 <= stats['average_progress'] <= 1.0
        assert 'last_updated' in stats
    
    def test_empty_statistics(self):
        """测试空课程列表的统计"""
        # 确保缓存为空
        self.manager._courses_cache.clear()
        self.manager._cache_loaded = True
        
        stats = self.manager.get_statistics()
        
        assert stats['total_courses'] == 0
        assert stats['completed_courses'] == 0
        assert stats['in_progress_courses'] == 0
        assert stats['not_started_courses'] == 0
        assert stats['completion_rate'] == 0.0
        assert stats['average_progress'] == 0.0
    
    def test_handle_pagination(self):
        """测试分页处理"""
        mock_page = Mock()
        
        # 模拟"加载更多"按钮
        mock_load_more = Mock()
        mock_load_more.count.return_value = 1
        mock_load_more.is_visible.return_value = True
        
        # 第一次返回按钮，第二次不返回（模拟没有更多内容）
        mock_page.locator.return_value.first = mock_load_more
        
        # 模拟点击后的状态变化
        click_count = 0
        def mock_click():
            nonlocal click_count
            click_count += 1
            if click_count >= 2:
                mock_load_more.count.return_value = 0
        
        mock_load_more.click.side_effect = mock_click
        
        # 执行分页处理
        self.manager._handle_pagination(mock_page)
        
        # 验证点击了按钮
        assert mock_load_more.click.called


class TestCourseManagerIntegration:
    """课程管理器集成测试"""
    
    def test_get_course_manager_singleton(self):
        """测试获取课程管理器单例"""
        manager1 = get_course_manager()
        manager2 = get_course_manager()
        
        # 应该返回同一个实例
        assert manager1 is manager2
    
    def test_full_workflow_simulation(self):
        """测试完整工作流程模拟"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置
            config_manager = Mock()
            config_manager.get_config.return_value = {
                'system': {'data_dir': temp_dir},
                'course_management': {
                    'course_list_url': 'https://example.com/courses'
                }
            }
            
            manager = CourseManager(config_manager)
            
            # 1. 模拟获取课程列表
            mock_page = Mock()
            courses_data = [
                {
                    'id': 'workflow_001',
                    'title': '工作流测试课程1',
                    'url': 'https://example.com/course/1',
                    'status': CourseStatus.NOT_STARTED,
                    'progress': 0.0
                },
                {
                    'id': 'workflow_002', 
                    'title': '工作流测试课程2',
                    'url': 'https://example.com/course/2',
                    'status': CourseStatus.IN_PROGRESS,
                    'progress': 0.4
                }
            ]
            
            # 创建课程对象并添加到缓存
            for data in courses_data:
                course = Course(**data)
                manager._courses_cache[course.id] = course
            manager._cache_loaded = True
            
            # 2. 保存到文件
            success = manager.save_courses_cache()
            assert success
            
            # 3. 获取课程列表
            courses = manager.get_courses()
            assert len(courses) == 2
            
            # 4. 按优先级排序
            sorted_courses = manager.sort_courses_by_priority()
            assert len(sorted_courses) == 2
            
            # 5. 更新课程进度
            success = manager.update_course_progress('workflow_002', 0.8)
            assert success
            
            # 6. 获取统计信息
            stats = manager.get_statistics()
            assert stats['total_courses'] == 2
            assert stats['in_progress_courses'] == 1
            
            # 7. 验证数据持久化
            new_manager = CourseManager(config_manager)
            new_manager._load_courses_cache()
            reloaded_courses = new_manager.get_courses()
            assert len(reloaded_courses) == 2
            
            # 验证更新的进度被保存
            updated_course = new_manager.get_course_by_id('workflow_002')
            assert updated_course.progress == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])