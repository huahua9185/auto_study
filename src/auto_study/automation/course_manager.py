"""
课程管理核心

负责课程数据的获取、解析、存储和管理，为自动化学习提供课程信息服务
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Callable, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from playwright.sync_api import Page, BrowserContext

from .browser_manager import BrowserManager
from .login_manager import LoginManager
from .error_handler import retry, safe_operation
from ..config.config_manager import ConfigManager
from ..utils.logger import logger


class CourseStatus(Enum):
    """课程状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    LOCKED = "locked"
    EXPIRED = "expired"


class CoursePriority(Enum):
    """课程优先级"""
    CRITICAL = 5    # 紧急且重要
    HIGH = 4        # 高优先级
    MEDIUM = 3      # 中等优先级
    LOW = 2         # 低优先级
    MINIMAL = 1     # 最低优先级


@dataclass
class Course:
    """课程数据模型"""
    id: str
    title: str
    url: str
    status: CourseStatus = CourseStatus.NOT_STARTED
    progress: float = 0.0  # 0.0 - 1.0
    deadline: Optional[datetime] = None
    priority: CoursePriority = CoursePriority.MEDIUM
    description: str = ""
    duration: Optional[int] = None  # 课程总时长（秒）
    completed_duration: int = 0  # 已完成时长（秒）
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    instructor: str = ""
    category: str = ""
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.status, str):
            self.status = CourseStatus(self.status)
        if isinstance(self.priority, (int, str)):
            if isinstance(self.priority, str):
                self.priority = CoursePriority[self.priority.upper()]
            else:
                self.priority = CoursePriority(self.priority)
        
        # 确保进度在有效范围内
        self.progress = max(0.0, min(1.0, self.progress))
    
    def is_completed(self) -> bool:
        """判断课程是否完成"""
        return self.status == CourseStatus.COMPLETED or self.progress >= 0.95
    
    def is_in_progress(self) -> bool:
        """判断课程是否进行中"""
        return self.status == CourseStatus.IN_PROGRESS or (0 < self.progress < 0.95)
    
    def days_until_deadline(self) -> Optional[int]:
        """距离截止时间的天数"""
        if not self.deadline:
            return None
        delta = self.deadline - datetime.now()
        return delta.days
    
    def is_overdue(self) -> bool:
        """判断是否已过期"""
        if not self.deadline:
            return False
        return datetime.now() > self.deadline
    
    def get_urgency_score(self) -> float:
        """获取紧急度评分 (0.0-1.0)"""
        if not self.deadline:
            return 0.3  # 无截止时间的默认紧急度
        
        days_left = self.days_until_deadline()
        if days_left is None:
            return 0.3
        
        if days_left <= 0:
            return 1.0  # 已过期，最高紧急度
        elif days_left <= 1:
            return 0.9
        elif days_left <= 3:
            return 0.7
        elif days_left <= 7:
            return 0.5
        elif days_left <= 14:
            return 0.3
        else:
            return 0.1
    
    def calculate_priority_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """
        计算综合优先级评分
        
        Args:
            weights: 各项权重配置
            
        Returns:
            优先级评分 (0.0-1.0)
        """
        if weights is None:
            weights = {
                'urgency': 0.4,      # 紧急度权重
                'priority': 0.3,     # 设定优先级权重  
                'progress': 0.2,     # 完成度权重
                'access': 0.1        # 最近访问权重
            }
        
        # 紧急度分数
        urgency_score = self.get_urgency_score()
        
        # 设定优先级分数
        priority_score = self.priority.value / 5.0
        
        # 完成度分数（进行中的课程优先）
        if self.is_completed():
            progress_score = 0.1  # 已完成课程降低优先级
        elif self.is_in_progress():
            progress_score = 0.8  # 进行中的课程提高优先级
        else:
            progress_score = 0.5  # 未开始的课程中等优先级
        
        # 最近访问分数
        if self.last_accessed:
            days_since_access = (datetime.now() - self.last_accessed).days
            if days_since_access == 0:
                access_score = 1.0
            elif days_since_access <= 3:
                access_score = 0.7
            elif days_since_access <= 7:
                access_score = 0.4
            else:
                access_score = 0.1
        else:
            access_score = 0.3  # 从未访问
        
        # 计算加权总分
        total_score = (
            urgency_score * weights['urgency'] +
            priority_score * weights['priority'] +
            progress_score * weights['progress'] +
            access_score * weights['access']
        )
        
        return min(1.0, max(0.0, total_score))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 处理枚举类型
        data['status'] = self.status.value
        data['priority'] = self.priority.value
        # 处理日期时间
        for field_name in ['deadline', 'created_time', 'updated_time', 'last_accessed']:
            if data[field_name]:
                data[field_name] = data[field_name].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Course':
        """从字典创建课程对象"""
        # 处理日期时间字段
        for field_name in ['deadline', 'created_time', 'updated_time', 'last_accessed']:
            if data.get(field_name):
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        return cls(**data)


class CourseManager:
    """课程管理器"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化课程管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.config = self.config_manager.get_config()
        
        # 数据存储配置
        self.data_dir = Path(self.config.get('system', {}).get('data_dir', 'data'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.courses_file = self.data_dir / 'courses.json'
        self.progress_file = self.data_dir / 'progress.json'
        
        # 课程管理配置
        self.course_config = self.config.get('course_management', {})
        
        # 课程数据缓存
        self._courses_cache: Dict[str, Course] = {}
        self._cache_loaded = False
        
        # 课程解析器配置
        self._course_selectors = {
            'course_list': [
                '.course-list .course-item',
                '.courses .course-card',
                '.my-courses .course',
                '[data-course-id]'
            ],
            'course_title': [
                '.course-title',
                '.course-name', 
                'h3',
                'h2',
                '.title'
            ],
            'course_link': [
                '.course-link a',
                'a[href*="course"]',
                '.title a',
                'a'
            ],
            'course_progress': [
                '.progress-bar',
                '.course-progress',
                '[data-progress]',
                '.completion'
            ],
            'course_status': [
                '.course-status',
                '.status',
                '.badge',
                '.completion-status'
            ],
            'course_description': [
                '.course-description',
                '.description',
                '.course-info',
                'p'
            ]
        }
        
        # 优先级排序权重配置
        self.priority_weights = self.course_config.get('priority_weights', {
            'urgency': 0.4,
            'priority': 0.3, 
            'progress': 0.2,
            'access': 0.1
        })
        
        logger.info("课程管理器初始化完成")
    
    def _load_courses_cache(self) -> None:
        """加载课程缓存"""
        if self._cache_loaded:
            return
        
        try:
            if self.courses_file.exists():
                with open(self.courses_file, 'r', encoding='utf-8') as f:
                    courses_data = json.load(f)
                
                for course_data in courses_data:
                    course = Course.from_dict(course_data)
                    self._courses_cache[course.id] = course
                
                logger.info(f"加载了 {len(self._courses_cache)} 个课程记录")
            
            self._cache_loaded = True
            
        except Exception as e:
            logger.error(f"加载课程缓存失败: {e}")
            self._courses_cache = {}
            self._cache_loaded = True
    
    @safe_operation(default_value=False)
    def save_courses_cache(self) -> bool:
        """保存课程缓存"""
        try:
            courses_data = [course.to_dict() for course in self._courses_cache.values()]
            
            # 写入临时文件，然后原子性替换
            temp_file = self.courses_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(courses_data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.courses_file)
            logger.info(f"保存了 {len(courses_data)} 个课程记录")
            return True
            
        except Exception as e:
            logger.error(f"保存课程缓存失败: {e}")
            return False
    
    def find_element_by_selectors(self, page: Page, selector_group: str, parent=None) -> Optional[Any]:
        """
        通过选择器组查找元素
        
        Args:
            page: 页面对象
            selector_group: 选择器组名
            parent: 父级元素
            
        Returns:
            找到的元素或None
        """
        selectors = self._course_selectors.get(selector_group, [])
        search_root = parent if parent else page
        
        for selector in selectors:
            try:
                element = search_root.locator(selector).first
                if element.count() > 0:
                    logger.debug(f"找到元素: {selector_group} -> {selector}")
                    return element
            except Exception as e:
                logger.debug(f"选择器 {selector} 未找到元素: {e}")
                continue
        
        logger.warning(f"未找到 {selector_group} 元素")
        return None
    
    @retry(max_retries=3, base_delay=2.0)
    def extract_courses_from_page(self, page: Page) -> List[Course]:
        """
        从页面提取课程信息
        
        Args:
            page: 页面对象
            
        Returns:
            课程列表
        """
        courses = []
        
        try:
            # 等待页面加载完成
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 查找课程列表元素
            course_elements = []
            for selector in self._course_selectors['course_list']:
                try:
                    elements = page.locator(selector).all()
                    if elements:
                        course_elements = elements
                        logger.info(f"找到 {len(elements)} 个课程，使用选择器: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"选择器 {selector} 查找失败: {e}")
                    continue
            
            if not course_elements:
                logger.warning("未找到课程列表元素")
                return courses
            
            # 提取每个课程的信息
            for i, course_element in enumerate(course_elements):
                try:
                    course = self._extract_single_course(page, course_element, i)
                    if course:
                        courses.append(course)
                        logger.debug(f"提取课程成功: {course.title}")
                    else:
                        logger.warning(f"提取第 {i+1} 个课程失败")
                        
                except Exception as e:
                    logger.error(f"提取第 {i+1} 个课程时出错: {e}")
                    continue
            
            logger.info(f"成功提取 {len(courses)} 个课程")
            return courses
            
        except Exception as e:
            logger.error(f"从页面提取课程信息失败: {e}")
            raise
    
    def _extract_single_course(self, page: Page, course_element, index: int) -> Optional[Course]:
        """
        提取单个课程信息
        
        Args:
            page: 页面对象
            course_element: 课程元素
            index: 课程索引
            
        Returns:
            课程对象或None
        """
        try:
            # 提取课程标题
            title = ""
            title_element = self.find_element_by_selectors(page, 'course_title', course_element)
            if title_element:
                title = title_element.text_content() or ""
                title = title.strip()
            
            if not title:
                logger.warning(f"课程 {index+1} 标题为空")
                return None
            
            # 提取课程链接
            url = ""
            link_element = self.find_element_by_selectors(page, 'course_link', course_element)
            if link_element:
                url = link_element.get_attribute('href') or ""
                # 处理相对链接
                if url and not url.startswith('http'):
                    base_url = page.url
                    if url.startswith('/'):
                        from urllib.parse import urljoin
                        url = urljoin(base_url, url)
                    else:
                        url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
            
            # 生成课程ID（使用URL或标题的哈希）
            import hashlib
            course_id = hashlib.md5((url or title).encode()).hexdigest()[:12]
            
            # 提取进度信息
            progress = 0.0
            progress_element = self.find_element_by_selectors(page, 'course_progress', course_element)
            if progress_element:
                progress = self._parse_progress(progress_element)
            
            # 提取状态信息
            status = CourseStatus.NOT_STARTED
            status_element = self.find_element_by_selectors(page, 'course_status', course_element)
            if status_element:
                status = self._parse_status(status_element, progress)
            elif progress > 0.95:
                status = CourseStatus.COMPLETED
            elif progress > 0:
                status = CourseStatus.IN_PROGRESS
            
            # 提取描述信息
            description = ""
            desc_element = self.find_element_by_selectors(page, 'course_description', course_element)
            if desc_element:
                description = desc_element.text_content() or ""
                description = description.strip()
            
            # 创建课程对象
            course = Course(
                id=course_id,
                title=title,
                url=url,
                status=status,
                progress=progress,
                description=description,
                updated_time=datetime.now()
            )
            
            return course
            
        except Exception as e:
            logger.error(f"提取单个课程信息失败: {e}")
            return None
    
    def _parse_progress(self, progress_element) -> float:
        """
        解析进度信息
        
        Args:
            progress_element: 进度元素
            
        Returns:
            进度值 (0.0-1.0)
        """
        try:
            # 尝试从data-progress属性获取
            progress_attr = progress_element.get_attribute('data-progress')
            if progress_attr:
                return float(progress_attr) / 100.0 if float(progress_attr) > 1 else float(progress_attr)
            
            # 尝试从样式width获取
            style = progress_element.get_attribute('style') or ""
            if 'width:' in style:
                import re
                match = re.search(r'width:\s*(\d+(?:\.\d+)?)%', style)
                if match:
                    return float(match.group(1)) / 100.0
            
            # 尝试从文本内容获取
            text = progress_element.text_content() or ""
            import re
            
            # 查找百分比
            percent_match = re.search(r'(\d+(?:\.\d+)?)%', text)
            if percent_match:
                return float(percent_match.group(1)) / 100.0
            
            # 查找分数形式 (如 3/10)
            fraction_match = re.search(r'(\d+)/(\d+)', text)
            if fraction_match:
                return float(fraction_match.group(1)) / float(fraction_match.group(2))
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"解析进度信息失败: {e}")
            return 0.0
    
    def _parse_status(self, status_element, progress: float) -> CourseStatus:
        """
        解析课程状态
        
        Args:
            status_element: 状态元素
            progress: 当前进度
            
        Returns:
            课程状态
        """
        try:
            text = status_element.text_content() or ""
            text = text.lower().strip()
            
            # 状态关键词映射
            status_keywords = {
                CourseStatus.COMPLETED: ['completed', '已完成', '完成', '100%', 'finished'],
                CourseStatus.IN_PROGRESS: ['in progress', '进行中', '学习中', 'ongoing', 'started'],
                CourseStatus.NOT_STARTED: ['not started', '未开始', '未学习', 'new'],
                CourseStatus.LOCKED: ['locked', '锁定', '未解锁', 'unavailable'],
                CourseStatus.EXPIRED: ['expired', '过期', '已过期', 'overdue']
            }
            
            for status, keywords in status_keywords.items():
                if any(keyword in text for keyword in keywords):
                    return status
            
            # 根据进度推断状态
            if progress >= 0.95:
                return CourseStatus.COMPLETED
            elif progress > 0:
                return CourseStatus.IN_PROGRESS
            else:
                return CourseStatus.NOT_STARTED
                
        except Exception as e:
            logger.debug(f"解析课程状态失败: {e}")
            # 根据进度推断
            if progress >= 0.95:
                return CourseStatus.COMPLETED
            elif progress > 0:
                return CourseStatus.IN_PROGRESS
            else:
                return CourseStatus.NOT_STARTED
    
    @retry(max_retries=2, base_delay=1.0)
    def fetch_courses(self, page: Page, course_url: Optional[str] = None) -> List[Course]:
        """
        获取课程列表
        
        Args:
            page: 页面对象
            course_url: 课程页面URL，如果为None则使用配置中的URL
            
        Returns:
            课程列表
        """
        try:
            # 获取课程页面URL
            if not course_url:
                course_url = self.course_config.get('course_list_url')
                if not course_url:
                    raise ValueError("未配置课程列表URL")
            
            logger.info(f"开始获取课程列表: {course_url}")
            
            # 导航到课程页面
            page.goto(course_url)
            page.wait_for_load_state('networkidle')
            time.sleep(3)  # 等待动态内容加载
            
            # 处理可能的分页或加载更多按钮
            self._handle_pagination(page)
            
            # 提取课程信息
            courses = self.extract_courses_from_page(page)
            
            # 更新缓存
            self._load_courses_cache()
            for course in courses:
                # 如果缓存中已存在，保留原有的优先级和访问时间等信息
                if course.id in self._courses_cache:
                    cached_course = self._courses_cache[course.id]
                    course.priority = cached_course.priority
                    course.last_accessed = cached_course.last_accessed
                    course.created_time = cached_course.created_time
                
                self._courses_cache[course.id] = course
            
            # 保存更新后的缓存
            self.save_courses_cache()
            
            logger.info(f"课程列表获取完成，共 {len(courses)} 个课程")
            return courses
            
        except Exception as e:
            logger.error(f"获取课程列表失败: {e}")
            raise
    
    def _handle_pagination(self, page: Page) -> None:
        """
        处理分页和动态加载
        
        Args:
            page: 页面对象
        """
        try:
            # 查找"加载更多"按钮
            load_more_selectors = [
                'button:has-text("加载更多")',
                'button:has-text("Load More")', 
                '.load-more',
                '.btn-load-more',
                '[data-action="load-more"]'
            ]
            
            max_clicks = 10  # 最多点击10次加载更多
            clicks = 0
            
            while clicks < max_clicks:
                load_more_button = None
                
                for selector in load_more_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.count() > 0 and element.is_visible():
                            load_more_button = element
                            break
                    except:
                        continue
                
                if not load_more_button:
                    break
                
                try:
                    # 滚动到按钮位置
                    load_more_button.scroll_into_view_if_needed()
                    time.sleep(1)
                    
                    # 点击加载更多
                    load_more_button.click()
                    clicks += 1
                    
                    # 等待内容加载
                    page.wait_for_load_state('networkidle', timeout=10000)
                    time.sleep(2)
                    
                    logger.debug(f"点击加载更多按钮 {clicks} 次")
                    
                except Exception as e:
                    logger.debug(f"点击加载更多按钮失败: {e}")
                    break
            
            # 处理下一页按钮
            next_page_selectors = [
                'a:has-text("下一页")',
                'a:has-text("Next")',
                '.pagination .next',
                '.pager-next'
            ]
            
            max_pages = 5  # 最多处理5页
            current_page = 1
            
            while current_page < max_pages:
                next_button = None
                
                for selector in next_page_selectors:
                    try:
                        element = page.locator(selector).first
                        if element.count() > 0 and element.is_visible():
                            next_button = element
                            break
                    except:
                        continue
                
                if not next_button:
                    break
                
                try:
                    next_button.click()
                    current_page += 1
                    
                    page.wait_for_load_state('networkidle', timeout=15000)
                    time.sleep(3)
                    
                    logger.debug(f"切换到第 {current_page} 页")
                    
                except Exception as e:
                    logger.debug(f"切换页面失败: {e}")
                    break
            
        except Exception as e:
            logger.debug(f"处理分页失败: {e}")
    
    def get_courses(self, reload: bool = False) -> List[Course]:
        """
        获取课程列表
        
        Args:
            reload: 是否重新加载
            
        Returns:
            课程列表
        """
        if reload or not self._cache_loaded:
            self._load_courses_cache()
        
        return list(self._courses_cache.values())
    
    def get_course_by_id(self, course_id: str) -> Optional[Course]:
        """
        根据ID获取课程
        
        Args:
            course_id: 课程ID
            
        Returns:
            课程对象或None
        """
        self._load_courses_cache()
        return self._courses_cache.get(course_id)
    
    def update_course_progress(self, course_id: str, progress: float, status: Optional[CourseStatus] = None) -> bool:
        """
        更新课程进度
        
        Args:
            course_id: 课程ID
            progress: 新的进度值
            status: 新的状态（可选）
            
        Returns:
            是否更新成功
        """
        try:
            self._load_courses_cache()
            
            if course_id not in self._courses_cache:
                logger.warning(f"课程 {course_id} 不存在")
                return False
            
            course = self._courses_cache[course_id]
            course.progress = max(0.0, min(1.0, progress))
            course.updated_time = datetime.now()
            course.last_accessed = datetime.now()
            
            if status:
                course.status = status
            elif progress >= 0.95:
                course.status = CourseStatus.COMPLETED
            elif progress > 0:
                course.status = CourseStatus.IN_PROGRESS
            
            # 保存缓存
            self.save_courses_cache()
            
            logger.info(f"课程 {course.title} 进度更新为 {progress:.1%}")
            return True
            
        except Exception as e:
            logger.error(f"更新课程进度失败: {e}")
            return False
    
    def sort_courses_by_priority(self, courses: Optional[List[Course]] = None, 
                                custom_weights: Optional[Dict[str, float]] = None) -> List[Course]:
        """
        按优先级排序课程
        
        Args:
            courses: 课程列表，如果为None则使用缓存中的所有课程
            custom_weights: 自定义权重配置
            
        Returns:
            排序后的课程列表
        """
        if courses is None:
            courses = self.get_courses()
        
        weights = custom_weights or self.priority_weights
        
        # 计算每个课程的优先级评分
        scored_courses = []
        for course in courses:
            score = course.calculate_priority_score(weights)
            scored_courses.append((course, score))
        
        # 按评分排序（分数高的优先）
        scored_courses.sort(key=lambda x: x[1], reverse=True)
        
        # 记录排序结果
        sorted_courses = [course for course, score in scored_courses]
        logger.info(f"课程优先级排序完成，共 {len(sorted_courses)} 个课程")
        
        for i, (course, score) in enumerate(scored_courses[:5]):  # 显示前5个
            logger.debug(f"{i+1}. {course.title} (评分: {score:.2f})")
        
        return sorted_courses
    
    def get_courses_by_status(self, status: CourseStatus) -> List[Course]:
        """
        按状态获取课程
        
        Args:
            status: 课程状态
            
        Returns:
            指定状态的课程列表
        """
        courses = self.get_courses()
        return [course for course in courses if course.status == status]
    
    def get_urgent_courses(self, days_threshold: int = 7) -> List[Course]:
        """
        获取紧急课程（即将到期）
        
        Args:
            days_threshold: 天数阈值
            
        Returns:
            紧急课程列表
        """
        courses = self.get_courses()
        urgent_courses = []
        
        for course in courses:
            if course.deadline and not course.is_completed():
                days_left = course.days_until_deadline()
                if days_left is not None and days_left <= days_threshold:
                    urgent_courses.append(course)
        
        # 按紧急度排序
        urgent_courses.sort(key=lambda c: c.get_urgency_score(), reverse=True)
        return urgent_courses
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取课程统计信息
        
        Returns:
            统计信息字典
        """
        courses = self.get_courses()
        
        if not courses:
            return {
                'total_courses': 0,
                'completed_courses': 0,
                'in_progress_courses': 0,
                'not_started_courses': 0,
                'completion_rate': 0.0,
                'average_progress': 0.0,
                'urgent_courses': 0,
                'overdue_courses': 0
            }
        
        completed = len([c for c in courses if c.is_completed()])
        in_progress = len([c for c in courses if c.is_in_progress()])
        not_started = len([c for c in courses if c.status == CourseStatus.NOT_STARTED])
        urgent = len(self.get_urgent_courses())
        overdue = len([c for c in courses if c.is_overdue()])
        
        total_progress = sum(c.progress for c in courses)
        average_progress = total_progress / len(courses)
        completion_rate = completed / len(courses)
        
        return {
            'total_courses': len(courses),
            'completed_courses': completed,
            'in_progress_courses': in_progress,
            'not_started_courses': not_started,
            'completion_rate': completion_rate,
            'average_progress': average_progress,
            'urgent_courses': urgent,
            'overdue_courses': overdue,
            'last_updated': datetime.now().isoformat()
        }


# 创建默认课程管理器实例
_default_manager = None


def get_course_manager(config_manager: Optional[ConfigManager] = None) -> CourseManager:
    """
    获取课程管理器实例
    
    Args:
        config_manager: 配置管理器
        
    Returns:
        课程管理器实例
    """
    global _default_manager
    
    if _default_manager is None:
        _default_manager = CourseManager(config_manager)
    
    return _default_manager