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
            
            # 确保开始前没有活动的学习会话
            if hasattr(self.learning_automator, 'current_session') and self.learning_automator.current_session:
                logger.info("检测到活动的学习会话，停止后开始新的学习流程")
                await self.learning_automator.stop_learning()
                await asyncio.sleep(2)
            
            logger.info(f"开始串行学习 {len(pending_courses)} 门待完成课程...")
            logger.info("📋 学习模式：严格串行执行，确保同一时间只学习一门课程")
            
            # 依次串行学习每门课程（系统限制：同时最多只能播放一门课程）
            for i, course in enumerate(pending_courses, 1):
                if not self.is_running:
                    logger.info("用户停止了学习进程")
                    break
                
                logger.info(f"[{i}/{len(pending_courses)}] 🎯 开始学习课程: {course.title}")
                logger.info(f"📊 当前进度: {course.progress*100:.1f}% | 讲师: {course.instructor}")
                logger.log_course_start(course.title)
                
                import time
                start_time = time.time()
                
                # 串行学习单门课程（等待当前课程完全完成后才开始下一门）
                success = await self._learn_single_course(course)
                
                if success:
                    end_time = time.time()
                    duration = self._format_duration(end_time - start_time)
                    logger.log_course_complete(course.title, duration)
                    logger.info(f"✅ 课程 [{i}/{len(pending_courses)}] 学习完成: {course.title}")
                else:
                    logger.error(f"❌ 课程 [{i}/{len(pending_courses)}] 学习失败: {course.title}")
                    logger.error("⛔ 课程播放失败，终止学习流程")
                    logger.error(f"失败详情: 课程《{course.title}》无法正常播放或学习")
                    logger.info("提示: 请检查网络连接、登录状态或手动验证该课程是否可以正常访问")
                    # 课程播放失败时终止程序，不再继续下一门课程
                    self.is_running = False
                    return False
                
                # 课程间休息，确保系统资源释放和状态重置
                if i < len(pending_courses):  # 不是最后一门课程
                    logger.info(f"⏳ 课程间休息5秒，准备学习下一门课程...")
                    await asyncio.sleep(5)
            
            logger.info("🏆 所有课程学习完成!")
            return True
            
        except Exception as e:
            logger.log_error_with_context(e, "自动学习过程出错")
            return False
        finally:
            self.is_running = False
    
    async def _learn_single_course(self, course) -> bool:
        """串行学习单门课程（严格确保同时只有一门课程在播放）"""
        try:
            logger.info(f"🔍 准备学习课程: {course.title}")
            
            # 第一层保护：确保停止任何正在进行的学习会话
            if hasattr(self.learning_automator, 'current_session') and self.learning_automator.current_session:
                logger.info("🛑 检测到活动学习会话，强制停止以确保串行执行")
                await self.learning_automator.stop_learning()
                await asyncio.sleep(2)  # 等待完全停止
            
            # 第二层保护：验证当前没有活动会话
            if hasattr(self.learning_automator, 'current_session') and self.learning_automator.current_session:
                logger.error("⚠️ 无法停止活动学习会话，跳过当前课程以维持串行执行")
                return False
            
            logger.info(f"▶️ 开始串行学习课程: {course.title}")
            
            # 访问课程页面
            if course.url:
                logger.info(f"访问课程页面: {course.url}")
                page = await self.browser_manager.get_page()
                await page.goto(course.url)
                await asyncio.sleep(5)  # 等待页面加载
                
                # 如果当前在课程列表页面，直接使用VideoController处理点击和新tab
                if "study_center/tool_box/required" in course.url:
                    logger.info("当前在课程列表页面，使用VideoController处理完整流程")
                    # VideoController.play()会自动处理：
                    # 1. 点击"继续学习"按钮
                    # 2. 检测并切换到新tab
                    # 3. 处理iframe中的视频播放
                    play_success = await self.learning_automator.video_controller.play()
                    if play_success:
                        logger.info("✅ VideoController成功处理视频播放")
                        # 继续执行后续的学习流程
                        has_video = True
                    else:
                        logger.error(f"❌ VideoController无法播放视频: {course.title}")
                        return False
                else:
                    # 检查页面是否包含视频内容
                    has_video = await self.learning_automator.video_controller.detect_video_player()
                    if not has_video:
                        logger.warning(f"课程页面未检测到视频播放器: {course.title}")
                        # 尝试使用VideoController处理视频播放
                        try:
                            play_success = await self.learning_automator.video_controller.play()
                            if play_success:
                                logger.info("✅ VideoController成功处理视频播放")
                                has_video = True
                            else:
                                logger.error(f"❌ VideoController无法播放视频: {course.title}")
                                return False
                        except Exception as e:
                            logger.error(f"尝试进入课程失败: {e}")
                            return False
                
                # 只有在还没有成功播放视频的情况下，才需要进行后续处理
                if has_video:
                    logger.info("✅ 视频已经在播放中")
                    success = True
                else:
                    # 第一次弹窗处理：页面跳转后立即处理
                    logger.info("第一阶段: 处理页面加载后的弹窗...")
                    await self._handle_learning_confirmation_popup(page)
                    
                    # 等待页面完全稳定
                    await asyncio.sleep(3)
                    
                    # 第二次弹窗处理：在尝试播放前再次检查
                    logger.info("第二阶段: 播放前最终弹窗检查...")
                    await self._handle_learning_confirmation_popup(page)
                    
                    # 开始视频学习
                    logger.info("🎬 开始视频播放...")
                    success = await self.learning_automator.start_video_learning(course.id)
                
                # 如果播放失败，再次尝试处理弹窗
                if not success:
                    logger.warning("播放失败，再次尝试处理弹窗...")
                    await self._handle_learning_confirmation_popup(page)
                    await asyncio.sleep(2)
                    success = await self.learning_automator.start_video_learning(course.id)
                
                if not success:
                    logger.error(f"⛔ 启动视频学习失败: {course.title}")
                    logger.error("失败原因: 无法启动视频播放器或视频学习会话")
                    return False
                
                # 监控学习进度
                logger.info("监控学习进度...")
                await self._monitor_learning_progress(course)
                
                # 停止学习
                await self.learning_automator.stop_learning()
                
                logger.info(f"课程学习完成: {course.title}")
                return True
            else:
                logger.error(f"⛔ 课程缺少URL: {course.title}")
                logger.error("失败原因: 课程数据不完整，无法获取学习链接")
                return False
                
        except Exception as e:
            logger.error(f"学习课程失败: {course.title} - {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _handle_learning_confirmation_popup(self, page):
        """处理学习确认弹窗 - 增强版"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"检查学习确认弹窗... (尝试 {attempt + 1}/{max_retries})")
                
                # 更长的等待时间，确保弹窗完全加载
                await asyncio.sleep(3)
                
                # 定义各种可能的弹窗选择器 - 更全面的覆盖
                popup_selectors = [
                    # 根据实际HTML结构的特定选择器（最高优先级）
                    '.continue:has(.user_choise)',  # 包含继续学习按钮的容器
                    'div.continue',  # 继续学习容器
                    
                    # Element UI 弹窗
                    '.el-dialog__wrapper:has(.el-dialog[aria-label])',
                    '.el-dialog:not([style*="display: none"])',  
                    '.el-message-box__wrapper:not([style*="display: none"])',
                    '.el-popup:not([style*="display: none"])',
                    
                    # 通用弹窗模态框
                    '.modal:not(.fade):not([style*="display: none"])',
                    '.popup:not([style*="display: none"])',
                    '.dialog:not([style*="display: none"])',
                    '[role="dialog"]:not([style*="display: none"])',
                    
                    # 自定义学习弹窗
                    '.study-dialog',
                    '.confirm-dialog', 
                    '.learning-popup',
                    '.course-dialog',
                    
                    # 基于z-index的弹窗检测
                    '[style*="z-index"]:not([style*="display: none"])'
                ]
                
                # 检查是否有弹窗存在
                popup_found = False
                popup_element = None
                found_selector = ""
                
                for selector in popup_selectors:
                    try:
                        elements = page.locator(selector)
                        count = await elements.count()
                        
                        for i in range(count):
                            element = elements.nth(i)
                            if await element.is_visible():
                                # 检查弹窗是否包含学习相关内容
                                popup_text = await element.text_content()
                                if popup_text and any(keyword in popup_text for keyword in 
                                    ['学习', '开始', '继续', '课程', '播放', '确认']):
                                    logger.info(f"🎯 发现学习相关弹窗: {selector}")
                                    logger.info(f"弹窗内容预览: {popup_text[:100]}...")
                                    popup_element = element
                                    popup_found = True
                                    found_selector = selector
                                    break
                                else:
                                    logger.debug(f"跳过非学习相关弹窗: {selector}")
                        
                        if popup_found:
                            break
                            
                    except Exception as e:
                        logger.debug(f"检查弹窗选择器 {selector} 失败: {e}")
                        continue
                
                if not popup_found:
                    logger.debug(f"尝试 {attempt + 1}: 未发现学习确认弹窗")
                    continue
                
                # 在弹窗中查找确认按钮 - 更精确的匹配
                confirm_button_selectors = [
                    # 特定的div按钮（根据实际HTML结构 - 最高优先级）
                    '.user_choise:has-text("继续学习")',
                    '.user_choise:has-text("开始学习")',
                    'div.user_choise',
                    '.continue .user_choise',
                    
                    # 精确文本匹配（包括button和div）
                    'button:has-text("开始学习")',
                    'button:has-text("继续学习")', 
                    'div:has-text("继续学习"):not(.continue)',  # 排除容器div
                    'div:has-text("开始学习")',
                    'button:has-text("确定")',
                    'button:has-text("确认")',
                    'button:has-text("开始播放")',
                    'button:has-text("进入学习")',
                    
                    # 包含文本匹配
                    'button:text-matches(".*开始.*学习.*")',
                    'button:text-matches(".*继续.*学习.*")',
                    'button:text-matches(".*确.*定.*")',
                    
                    # Element UI 按钮类
                    '.el-button--primary:visible',
                    '.el-button.is-primary:visible',
                    '.el-dialog__footer .el-button--primary',
                    '.el-message-box__btns .el-button--primary',
                    
                    # 通用按钮类
                    '.btn-primary:visible',
                    '.btn-confirm:visible', 
                    '.confirm-btn:visible',
                    '.start-btn:visible',
                    '.learn-btn:visible',
                    '.study-btn:visible',
                    
                    # 可点击的div元素
                    '[onclick]:has-text("继续学习")',
                    '[onclick]:has-text("开始学习")',
                    'div[style*="cursor"]:has-text("继续学习")',
                    'div[style*="cursor"]:has-text("开始学习")',
                    
                    # 按钮角色和类型
                    'button[type="submit"]:visible',
                    'input[type="submit"]:visible',
                    '[role="button"]:visible',
                    
                    # 最后的fallback - 所有可见按钮
                    'button:visible'
                ]
                
                button_clicked = False
                
                for selector in confirm_button_selectors:
                    try:
                        # 优先在弹窗内查找按钮
                        if popup_element:
                            buttons = popup_element.locator(selector)
                        else:
                            buttons = page.locator(selector)
                        
                        button_count = await buttons.count()
                        logger.debug(f"在弹窗中找到 {button_count} 个匹配按钮: {selector}")
                        
                        for i in range(button_count):
                            button = buttons.nth(i)
                            
                            if await button.is_visible():
                                button_text = await button.text_content()
                                button_classes = await button.get_attribute('class') or ""
                                
                                logger.info(f"检查按钮: 选择器={selector}, 文本='{button_text}', 类名={button_classes}")
                                
                                # 更精确的按钮匹配逻辑
                                should_click = False
                                element_tag = await button.evaluate("el => el.tagName.toLowerCase()")
                                
                                if button_text:
                                    # 特别检查user_choise类的div元素
                                    if 'user_choise' in button_classes:
                                        should_click = True
                                        logger.info(f"✅ 匹配user_choise类的div按钮: {button_text}")
                                    # 包含学习相关关键词的按钮
                                    elif any(keyword in button_text for keyword in ['开始学习', '继续学习', '进入学习', '开始播放']):
                                        should_click = True
                                        logger.info(f"✅ 匹配学习关键词: {button_text}")
                                    elif any(keyword in button_text for keyword in ['确定', '确认', 'OK', '好的']):
                                        should_click = True
                                        logger.info(f"✅ 匹配确认关键词: {button_text}")
                                elif 'primary' in button_classes.lower():
                                    # 主要按钮（通常是确认按钮）
                                    should_click = True
                                    logger.info(f"✅ 匹配主要按钮类: {button_classes}")
                                
                                if should_click:
                                    logger.info(f"🎯 点击学习确认元素: 标签={element_tag}, 文本='{button_text or '(无文本)'}', 类='{button_classes}'")
                                    await button.click()
                                    button_clicked = True
                                    await asyncio.sleep(2)  # 等待弹窗消失
                                    break
                        
                        if button_clicked:
                            break
                            
                    except Exception as e:
                        logger.debug(f"尝试点击按钮 {selector} 失败: {e}")
                        continue
                
                if button_clicked:
                    # 验证弹窗是否已消失
                    await asyncio.sleep(2)
                    try:
                        if popup_element:
                            is_still_visible = await popup_element.is_visible()
                            if not is_still_visible:
                                logger.info("✅ 学习确认弹窗处理完成，弹窗已消失")
                                return True
                            else:
                                logger.warning("⚠️ 按钮已点击但弹窗仍然可见，可能需要重试")
                        else:
                            logger.info("✅ 学习确认弹窗处理完成")
                            return True
                    except:
                        logger.info("✅ 学习确认弹窗处理完成")
                        return True
                else:
                    logger.warning(f"⚠️ 尝试 {attempt + 1}: 找到弹窗但未能点击确认按钮")
                    
            except Exception as e:
                logger.error(f"处理学习确认弹窗失败 (尝试 {attempt + 1}): {e}")
                
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                logger.info(f"等待3秒后重试弹窗处理...")
                await asyncio.sleep(3)
        
        logger.error("❌ 所有弹窗处理尝试均失败")
        return False
    
    async def _fetch_courses_from_website(self, page, courses_url: str):
        """从网站获取课程列表"""
        try:
            from .automation.course_manager import Course, CourseStatus
            
            logger.info(f"访问课程页面: {courses_url}")
            await page.goto(courses_url)
            await page.wait_for_load_state('networkidle')
            
            # 等待Vue.js应用和Element UI组件完全加载
            logger.info("等待Vue.js和Element UI组件加载...")
            try:
                # 等待Vue实例
                await page.wait_for_function("() => window.Vue !== undefined", timeout=15000)
                logger.info("Vue.js已加载")
            except:
                logger.warning("未检测到Vue.js，继续尝试")
            
            # 等待Element UI collapse组件
            try:
                await page.wait_for_selector('.el-collapse', timeout=10000)
                logger.info("Element UI collapse组件已加载")
            except:
                logger.warning("未找到collapse组件")
            
            # 等待课程列表展开状态
            try:
                await page.wait_for_selector('.el-collapse-item__content:not(.is-hidden)', timeout=10000)
                logger.info("课程列表已展开")
            except:
                logger.warning("课程列表可能未展开")
                # 尝试点击展开按钮
                try:
                    expand_button = page.locator('.el-collapse-item__header').first
                    if await expand_button.count() > 0:
                        await expand_button.click()
                        await asyncio.sleep(2)
                        logger.info("已点击展开课程列表")
                except:
                    logger.warning("无法点击展开按钮")
            
            # 验证页面状态
            current_url = page.url
            if "requireAuth" in current_url or "login" in current_url:
                logger.error("页面跳转到认证页面，可能未正确登录")
                return []
            
            await asyncio.sleep(3)  # 给组件渲染时间
            
            # 渐进式选择器发现策略
            course_item_selectors = [
                # 最具体的选择器（基于用户提供的HTML结构）
                '.el-collapse-item__content .gj_top_list_box li',
                '.gj_top_list_box li',
                # Element UI特定选择器
                '.el-collapse-item__content li',
                '.el-collapse-item li',
                # Vue组件特定选择器（基于data-v-属性）
                'ul[data-v-31d29258] li',
                'li[data-v-31d29258]',
                # 更通用的fallback选择器
                '.el-collapse li',
                'ul li',
                # 最后的fallback
                'li'
            ]
            
            courses = []
            course_elements = None
            successful_selector = None
            
            # 首先检查课程列表容器是否存在
            container_selectors = [
                '.gj_top_list_box',
                '.el-collapse-item__content',
                '.el-collapse'
            ]
            
            container_found = False
            for container_sel in container_selectors:
                try:
                    if await page.locator(container_sel).count() > 0:
                        logger.info(f"找到课程容器: {container_sel}")
                        container_found = True
                        break
                except:
                    continue
            
            if not container_found:
                logger.error("未找到任何课程容器，可能页面结构已改变")
                # 调试：打印当前页面的基本信息
                try:
                    title = await page.title()
                    logger.info(f"当前页面标题: {title}")
                    logger.info(f"当前页面URL: {page.url}")
                    
                    # 检查是否有基本的HTML元素
                    basic_elements = ['div', 'ul', 'li']
                    for elem in basic_elements:
                        count = await page.locator(elem).count()
                        logger.info(f"{elem}元素数量: {count}")
                        
                except Exception as e:
                    logger.error(f"页面调试信息获取失败: {e}")
                
                return []
            
            # 尝试各种选择器
            for selector in course_item_selectors:
                try:
                    elements = page.locator(selector)
                    count = await elements.count()
                    if count > 0:
                        # 验证元素是否包含课程相关内容
                        first_element = elements.first
                        try:
                            # 检查是否包含课程标题或进度信息
                            has_title = await first_element.locator('.text_title, [title]').count() > 0
                            has_progress = await first_element.locator('.el-progress__text, .progress').count() > 0
                            has_course_content = await first_element.locator('.text_start, .btn').count() > 0
                            
                            if has_title or has_progress or has_course_content:
                                course_elements = elements
                                successful_selector = selector
                                logger.info(f"找到 {count} 个有效课程项: {selector}")
                                break
                            else:
                                logger.debug(f"选择器 {selector} 找到 {count} 个元素，但非课程内容")
                                
                        except Exception as e:
                            logger.debug(f"验证选择器内容时出错: {e}")
                            # 仍然使用这个选择器
                            course_elements = elements
                            successful_selector = selector
                            logger.info(f"找到 {count} 个课程项: {selector} (未验证内容)")
                            break
                            
                except Exception as e:
                    logger.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            if not course_elements:
                logger.error("未找到课程列表项，尝试所有选择器策略均失败")
                return []
            
            # 提取所有课程
            course_count = await course_elements.count()
            max_courses = min(50, course_count)  # 最多提取50门课程
            
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
                    
                    # 提取课程的实际学习链接
                    url = courses_url  # 默认值
                    try:
                        # 查找学习按钮或链接
                        learn_button = element.locator('.btn:has-text("继续学习"), .btn:has-text("开始学习"), .btn:has-text("学习")').first
                        if await learn_button.count() > 0:
                            # 尝试获取链接href属性
                            href = await learn_button.get_attribute('href')
                            if href:
                                if href.startswith('http'):
                                    url = href
                                elif href.startswith('#'):
                                    url = f"https://edu.nxgbjy.org.cn/nxxzxy/index.html{href}"
                                else:
                                    url = f"https://edu.nxgbjy.org.cn{href}"
                            else:
                                # 如果没有href，查找data-id或onclick等属性
                                data_id = await learn_button.get_attribute('data-id')
                                onclick = await learn_button.get_attribute('onclick')
                                
                                if data_id:
                                    # 根据数据ID构建课程URL
                                    url = f"https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/video_play?id={data_id}"
                                elif onclick and 'openStudy' in onclick:
                                    # 从onclick事件中提取课程ID
                                    import re
                                    match = re.search(r'openStudy\([\'"]([^\'"]+)[\'"]', onclick)
                                    if match:
                                        course_id = match.group(1)
                                        url = f"https://edu.nxgbjy.org.cn/nxxzxy/index.html#/study_center/video_play?id={course_id}"
                        
                        # 如果还没有找到具体URL，尝试查找父级链接
                        if url == courses_url:
                            parent_link = element.locator('a[href*="study"], a[href*="video"], a[href*="course"]').first
                            if await parent_link.count() > 0:
                                href = await parent_link.get_attribute('href')
                                if href:
                                    if href.startswith('http'):
                                        url = href
                                    elif href.startswith('#'):
                                        url = f"https://edu.nxgbjy.org.cn/nxxzxy/index.html{href}"
                                    else:
                                        url = f"https://edu.nxgbjy.org.cn{href}"
                    except Exception as e:
                        logger.debug(f"提取课程URL失败，使用默认URL: {e}")
                        pass
                    
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
            
            # 将提取的课程数据保存到课程管理器
            self.course_manager._load_courses_cache()
            for course in courses:
                # 如果缓存中已存在，保留原有的优先级和访问时间等信息
                if course.id in self.course_manager._courses_cache:
                    cached_course = self.course_manager._courses_cache[course.id]
                    course.priority = cached_course.priority
                    course.last_accessed = cached_course.last_accessed
                    course.created_time = cached_course.created_time
                
                self.course_manager._courses_cache[course.id] = course
            
            # 保存更新后的课程缓存
            success = self.course_manager.save_courses_cache()
            if success:
                logger.info(f"课程数据已保存到 {self.course_manager.courses_file}")
            else:
                logger.error("课程数据保存失败")
            
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