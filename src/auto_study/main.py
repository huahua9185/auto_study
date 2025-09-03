"""
主程序入口

自动学习系统的主要执行逻辑
"""

import asyncio
from typing import List
from .automation.browser_manager import BrowserManager
from .automation.auto_login import AutoLogin
from .automation.course_manager import CourseManager, Course
from .automation.learning_automator import LearningAutomator
from .config.settings import settings
from .utils.logger import logger
from .utils.error_handler import retry_on_error, LoginError, CourseError


class AutoStudyApp:
    """自动学习应用主类"""
    
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.auto_login = None
        self.course_manager = None
        self.learning_automator = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """初始化应用"""
        try:
            logger.log_system_status("初始化", "开始启动系统...")
            
            # 验证配置
            if not settings.validate_config():
                logger.error("配置验证失败")
                return False
            
            # 启动浏览器
            await self.browser_manager.start_browser(
                headless=settings.browser.headless
            )
            
            page = await self.browser_manager.get_page()
            
            # 初始化各模块
            self.auto_login = AutoLogin(page)
            from .config.config_manager import ConfigManager
            config_manager = ConfigManager()
            self.course_manager = CourseManager(config_manager)
            self.learning_automator = LearningAutomator(page)
            
            logger.log_system_status("初始化", "系统启动完成")
            return True
            
        except Exception as e:
            logger.log_error_with_context(e, "系统初始化失败")
            return False
    
    @retry_on_error
    async def login(self) -> bool:
        """执行登录"""
        try:
            username, password = settings.get_user_credentials()
            if not username or not password:
                raise LoginError("未配置用户名和密码")
            
            logger.info(f"开始登录用户: {username}")
            
            success = await self.auto_login.login(username, password)
            if success:
                logger.log_login_success(username)
                return True
            else:
                raise LoginError("登录验证失败")
                
        except Exception as e:
            logger.log_login_failed(username or "未知用户", str(e))
            raise
    
    async def get_courses(self) -> List[Course]:
        """获取课程列表"""
        try:
            logger.info("获取课程列表...")
            
            # 从网站获取最新课程列表
            page = await self.browser_manager.get_page()
            
            # 获取课程页面URL
            from .config.config_manager import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.get_config()
            courses_url = config.get('site', {}).get('courses_url')
            
            if not courses_url:
                raise CourseError("未配置课程页面URL")
                
            courses = await self._fetch_courses_from_website(page, courses_url)
            
            if not courses:
                raise CourseError("未找到任何课程")
            
            logger.info(f"找到 {len(courses)} 门课程")
            
            # 显示课程统计
            from .automation.course_manager import CourseStatus
            completed = [c for c in courses if c.status == CourseStatus.COMPLETED]
            pending = [c for c in courses if c.status != CourseStatus.COMPLETED]
            
            logger.info(f"已完成: {len(completed)}, 待学习: {len(pending)}")
            
            return courses
            
        except Exception as e:
            logger.log_error_with_context(e, "获取课程列表失败")
            raise
    
    async def start_learning(self) -> bool:
        """开始自动学习"""
        try:
            self.is_running = True
            
            # 获取课程列表
            courses = await self.get_courses()
            
            # 获取按优先级排序的待学习课程
            from .automation.course_manager import CourseStatus
            all_courses = self.course_manager.get_courses()
            pending_courses = [c for c in all_courses if c.status != CourseStatus.COMPLETED]
            pending_courses = self.course_manager.sort_courses_by_priority(pending_courses)
            
            if not pending_courses:
                logger.info("🎉 所有课程已完成!")
                return True
            
            logger.info(f"开始学习 {len(pending_courses)} 门待完成课程...")
            
            # 依次学习每门课程
            for i, course in enumerate(pending_courses, 1):
                if not self.is_running:
                    logger.info("用户停止了学习进程")
                    break
                
                logger.info(f"[{i}/{len(pending_courses)}] 开始学习: {course.title}")
                logger.log_course_start(course.title)
                
                import time
                start_time = time.time()
                
                # 学习课程
                success = await self._learn_single_course(course)
                
                if success:
                    end_time = time.time()
                    duration = self._format_duration(end_time - start_time)
                    logger.log_course_complete(course.title, duration)
                else:
                    logger.error(f"课程学习失败: {course.title}")
                    # 可以选择继续下一门课程或停止
                    continue
                
                # 短暂休息
                await asyncio.sleep(5)
            
            logger.info("🏆 所有课程学习完成!")
            return True
            
        except Exception as e:
            logger.log_error_with_context(e, "自动学习过程出错")
            return False
        finally:
            self.is_running = False
    
    async def _learn_single_course(self, course) -> bool:
        """学习单门课程"""
        try:
            logger.info(f"开始学习课程: {course.title}")
            
            # 访问课程页面
            if course.url:
                logger.info(f"访问课程页面: {course.url}")
                page = await self.browser_manager.get_page()
                await page.goto(course.url)
                await asyncio.sleep(5)  # 等待页面加载
                
                # 检查页面是否包含视频内容
                has_video = await self.learning_automator.video_controller.detect_video_player()
                if not has_video:
                    logger.warning(f"课程页面未检测到视频播放器: {course.title}")
                    # 尝试查找课程链接或进入课程按钮
                    try:
                        # 查找"开始学习"、"进入课程"等按钮
                        start_buttons = [
                            'button:has-text("开始学习")',
                            'button:has-text("进入课程")', 
                            'a:has-text("开始学习")',
                            'a:has-text("进入课程")',
                            '.start-btn',
                            '.learn-btn',
                            '.course-btn'
                        ]
                        
                        button_found = False
                        for selector in start_buttons:
                            try:
                                button = page.locator(selector).first
                                if await button.count() > 0 and await button.is_visible():
                                    logger.info(f"点击学习按钮: {selector}")
                                    await button.click()
                                    await asyncio.sleep(3)
                                    button_found = True
                                    break
                            except:
                                continue
                        
                        if button_found:
                            # 重新检测视频播放器
                            has_video = await self.learning_automator.video_controller.detect_video_player()
                        
                        if not has_video:
                            logger.warning(f"仍然未检测到视频播放器，跳过课程: {course.title}")
                            return False
                    except Exception as e:
                        logger.error(f"尝试进入课程失败: {e}")
                        return False
                
                # 开始视频学习
                logger.info("开始视频播放...")
                success = await self.learning_automator.start_video_learning(course.id)
                
                if not success:
                    logger.error(f"启动视频学习失败: {course.title}")
                    return False
                
                # 监控学习进度
                logger.info("监控学习进度...")
                await self._monitor_learning_progress(course)
                
                # 停止学习
                await self.learning_automator.stop_learning()
                
                logger.info(f"课程学习完成: {course.title}")
                return True
            else:
                logger.warning(f"课程缺少URL: {course.title}")
                return False
                
        except Exception as e:
            logger.error(f"学习课程失败: {course.title} - {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _fetch_courses_from_website(self, page, courses_url: str):
        """从网站获取课程列表"""
        try:
            from .automation.course_manager import Course, CourseStatus
            
            logger.info(f"访问课程页面: {courses_url}")
            await page.goto(courses_url)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(5)  # 等待页面完全加载
            
            # 等待课程列表容器加载
            course_container_selector = '.el-collapse-item__content .gj_top_list_box'
            try:
                await page.wait_for_selector(course_container_selector, timeout=10000)
                logger.info("找到课程列表容器")
            except:
                logger.warning("未找到课程列表容器，尝试备用选择器")
            
            # 查找课程列表项
            course_item_selectors = [
                '.gj_top_list_box li',
                '.el-collapse-item__content li',
                'ul[data-v-31d29258] li',
                'li[data-v-31d29258]'
            ]
            
            courses = []
            course_elements = None
            
            for selector in course_item_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        course_elements = elements
                        logger.info(f"找到 {count} 个课程项: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            if not course_elements:
                logger.warning("未找到课程列表项")
                return []
            
            # 提取所有课程
            course_count = await course_elements.count()
            max_courses = min(20, course_count)  # 最多提取20门课程
            
            for i in range(max_courses):
                try:
                    element = course_elements.nth(i)
                    
                    # 提取课程标题（使用正确的选择器）
                    title = ""
                    try:
                        title_elem = element.locator('.text_title').first
                        if await title_elem.count() > 0:
                            title_text = await title_elem.text_content()
                            if title_text:
                                title = title_text.strip()
                        
                        # 如果没有找到，尝试title属性
                        if not title:
                            title_attr = await title_elem.get_attribute('title')
                            if title_attr:
                                title = title_attr.strip()
                    except:
                        pass
                    
                    if not title or len(title) < 3:
                        logger.debug(f"跳过第 {i+1} 个课程：标题无效")
                        continue
                    
                    # 提取学习进度
                    progress = 0.0
                    try:
                        progress_elem = element.locator('.el-progress__text').first
                        if await progress_elem.count() > 0:
                            progress_text = await progress_elem.text_content()
                            if progress_text and '%' in progress_text:
                                # 提取百分比数字
                                import re
                                match = re.search(r'([\d.]+)%', progress_text)
                                if match:
                                    progress = float(match.group(1)) / 100.0
                    except:
                        pass
                    
                    # 提取主讲人信息
                    instructor = ""
                    try:
                        instructor_elem = element.locator('.text_start').first
                        if await instructor_elem.count() > 0:
                            instructor_text = await instructor_elem.text_content()
                            if instructor_text:
                                # 提取主讲人姓名
                                import re
                                match = re.search(r'主讲人：([^职]+)', instructor_text)
                                if match:
                                    instructor = match.group(1).strip()
                    except:
                        pass
                    
                    # 暂时使用当前课程列表页面作为学习URL
                    # 后续在学习时会通过点击"继续学习"按钮进入实际的课程页面
                    url = courses_url
                    
                    # 根据进度确定状态
                    if progress >= 0.95:
                        status = CourseStatus.COMPLETED
                    elif progress > 0:
                        status = CourseStatus.IN_PROGRESS
                    else:
                        status = CourseStatus.NOT_STARTED
                    
                    # 生成课程ID
                    import hashlib
                    course_id = hashlib.md5(f"{title}{instructor}".encode()).hexdigest()[:12]
                    
                    # 创建课程对象
                    course = Course(
                        id=course_id,
                        title=title,
                        url=url,
                        status=status,
                        progress=progress,
                        instructor=instructor
                    )
                    
                    courses.append(course)
                    logger.info(f"提取课程: {title} (进度: {progress:.1%}, 主讲: {instructor})")
                    
                except Exception as e:
                    logger.debug(f"提取第 {i+1} 个课程失败: {e}")
                    continue
            
            logger.info(f"成功提取 {len(courses)} 门课程")
            return courses
            
        except Exception as e:
            logger.error(f"从网站获取课程失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _monitor_learning_progress(self, course, max_duration: int = 3600):
        """监控学习进度"""
        try:
            start_time = asyncio.get_event_loop().time()
            last_position = 0.0
            stuck_count = 0
            
            while self.is_running:
                current_time = asyncio.get_event_loop().time()
                elapsed = current_time - start_time
                
                # 检查最大学习时间限制
                if elapsed > max_duration:
                    logger.warning(f"达到最大学习时间限制 {max_duration}秒，停止学习")
                    break
                
                # 获取播放状态
                video_controller = self.learning_automator.video_controller
                position = await video_controller.get_current_time()
                duration = await video_controller.get_duration()
                is_playing = await video_controller.is_playing()
                is_ended = await video_controller.is_ended()
                
                # 计算进度
                progress = (position / duration * 100.0) if duration > 0 else 0.0
                
                logger.info(f"学习进度: {progress:.1f}% ({position:.0f}s/{duration:.0f}s)")
                
                # 检查是否播放结束
                if is_ended or progress >= 95.0:
                    logger.info("视频播放完成")
                    break
                
                # 检查是否卡住
                if abs(position - last_position) < 1.0 and is_playing:
                    stuck_count += 1
                    if stuck_count > 10:  # 10次检查都没有进度
                        logger.warning("检测到播放卡死，尝试恢复...")
                        await video_controller.play()  # 重新播放
                        stuck_count = 0
                else:
                    stuck_count = 0
                    last_position = position
                
                # 检查间隔
                await asyncio.sleep(30)  # 30秒检查一次
                
        except Exception as e:
            logger.error(f"监控学习进度失败: {e}")

    async def stop_learning(self) -> None:
        """停止学习"""
        self.is_running = False
        if self.learning_automator:
            await self.learning_automator.stop_learning()
        logger.info("学习进程已停止")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.learning_automator and self.is_running:
                await self.learning_automator.stop_learning()
            
            await self.browser_manager.close()
            logger.log_system_status("清理", "资源清理完成")
            
        except Exception as e:
            logger.log_error_with_context(e, "资源清理失败")
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟"
        else:
            return f"{seconds/3600:.1f}小时"
    
    async def run(self) -> None:
        """运行应用"""
        try:
            # 初始化
            if not await self.initialize():
                logger.error("系统初始化失败")
                return
            
            # 登录
            if not await self.login():
                logger.error("登录失败")
                return
            
            # 开始学习
            await self.start_learning()
            
        except KeyboardInterrupt:
            logger.info("用户中断操作")
        except Exception as e:
            logger.log_error_with_context(e, "应用运行异常")
        finally:
            await self.cleanup()


async def main():
    """主函数"""
    app = AutoStudyApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())