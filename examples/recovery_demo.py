"""
错误恢复机制演示

展示完整的错误恢复系统功能
"""

import time
import random
import asyncio
from datetime import datetime

from src.auto_study.recovery import (
    RecoveryManager, StateManager, RetryManager, PersistenceManager,
    TaskStatus, RetryableError, RetryErrorType, RetryStrategy
)


class LearningAutomationSimulator:
    """学习自动化模拟器"""
    
    def __init__(self):
        # 初始化恢复系统组件
        self.persistence = PersistenceManager("data/recovery_demo.db")
        self.state_manager = StateManager(self.persistence)
        self.retry_manager = RetryManager()
        self.recovery_manager = RecoveryManager(
            self.state_manager,
            self.persistence,
            "data/demo.pid",
            "data/demo.lock"
        )
        
        # 注册恢复处理器
        self._register_recovery_handlers()
        
        # 注册自定义重试策略
        self._setup_custom_retry_strategies()
        
        print("🤖 学习自动化模拟器已初始化")
    
    def _register_recovery_handlers(self):
        """注册恢复处理器"""
        
        def login_recovery_handler(task_state):
            """登录任务恢复处理器"""
            print(f"🔄 恢复登录任务: {task_state.task_id}")
            checkpoint = task_state.checkpoint
            if checkpoint and checkpoint.step == "credential_input":
                print(f"   从步骤恢复: {checkpoint.step}")
                return True
            return False
        
        def video_watch_recovery_handler(task_state):
            """视频观看任务恢复处理器"""
            print(f"🎥 恢复视频观看任务: {task_state.task_id}")
            checkpoint = task_state.checkpoint
            if checkpoint:
                progress = checkpoint.data.get("watch_progress", 0)
                print(f"   从进度恢复: {progress}%")
                return True
            return False
        
        def course_sync_recovery_handler(task_state):
            """课程同步任务恢复处理器"""
            print(f"📚 恢复课程同步任务: {task_state.task_id}")
            checkpoint = task_state.checkpoint
            if checkpoint:
                synced = checkpoint.data.get("synced_items", 0)
                total = checkpoint.data.get("total_items", 0)
                print(f"   从进度恢复: {synced}/{total} 项")
                return True
            return False
        
        # 注册处理器
        self.state_manager.register_recovery_handler("user_login", login_recovery_handler)
        self.state_manager.register_recovery_handler("video_watch", video_watch_recovery_handler)
        self.state_manager.register_recovery_handler("course_sync", course_sync_recovery_handler)
        
        # 注册清理处理器
        def cleanup_temp_files():
            print("🧹 清理临时文件")
        
        def cleanup_browser_cache():
            print("🧹 清理浏览器缓存")
        
        self.recovery_manager.register_cleanup_handler(cleanup_temp_files)
        self.recovery_manager.register_cleanup_handler(cleanup_browser_cache)
        
        # 注册关闭处理器
        def graceful_shutdown():
            print("⏹️  执行优雅关闭")
        
        self.recovery_manager.register_shutdown_handler(graceful_shutdown)
    
    def _setup_custom_retry_strategies(self):
        """设置自定义重试策略"""
        
        # 为验证码识别设置特殊策略
        captcha_strategy = RetryStrategy(
            max_attempts=10,  # 验证码可能需要多次尝试
            base_delay=2.0,
            max_delay=30.0,
            backoff_type="linear",
            jitter=True
        )
        
        self.retry_manager.update_strategy(RetryErrorType.TEMPORARY_ERROR, captcha_strategy)
        
        # 注册自定义错误分类器
        def classify_learning_errors(error):
            error_msg = str(error).lower()
            if "captcha" in error_msg or "验证码" in error_msg:
                return RetryErrorType.TEMPORARY_ERROR
            elif "video" in error_msg and "loading" in error_msg:
                return RetryErrorType.NETWORK_ERROR
            return RetryErrorType.UNKNOWN_ERROR
        
        self.retry_manager.register_error_classifier(classify_learning_errors)
    
    def simulate_user_login(self, username: str) -> dict:
        """模拟用户登录"""
        print(f"👤 开始登录用户: {username}")
        
        # 创建登录任务
        task_id = self.state_manager.create_task("user_login", initial_data={
            "username": username,
            "login_time": datetime.now().isoformat()
        })
        
        try:
            self.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            
            # 步骤1: 导航到登录页面
            self.state_manager.create_checkpoint(task_id, "navigation", 1, {
                "url": "https://example-learning.com/login"
            })
            self.state_manager.update_task_progress(task_id, 20.0)
            print("  📍 已导航到登录页面")
            time.sleep(0.5)
            
            # 步骤2: 输入凭据
            self.state_manager.create_checkpoint(task_id, "credential_input", 2, {
                "username_filled": True,
                "password_filled": True
            })
            self.state_manager.update_task_progress(task_id, 40.0)
            print("  🔑 已输入登录凭据")
            time.sleep(0.5)
            
            # 步骤3: 处理验证码（可能失败）
            def handle_captcha():
                if random.random() < 0.7:  # 70%失败率
                    raise RetryableError("验证码识别失败", RetryErrorType.TEMPORARY_ERROR)
                return {"captcha_token": "abc123"}
            
            captcha_result = self.retry_manager.retry_function(
                handle_captcha,
                max_attempts=5
            )
            
            self.state_manager.create_checkpoint(task_id, "captcha_verification", 3, captcha_result)
            self.state_manager.update_task_progress(task_id, 70.0)
            print("  🔍 验证码验证成功")
            time.sleep(0.5)
            
            # 步骤4: 登录验证（可能网络错误）
            def verify_login():
                if random.random() < 0.3:  # 30%网络错误率
                    raise RetryableError("登录验证网络超时", RetryErrorType.NETWORK_ERROR)
                return {
                    "user_id": f"user_{username}",
                    "token": f"token_{random.randint(1000, 9999)}",
                    "session_id": f"session_{random.randint(10000, 99999)}"
                }
            
            login_result = self.retry_manager.retry_function(
                verify_login,
                max_attempts=3
            )
            
            # 完成任务
            self.state_manager.complete_task(task_id, {
                "login_result": login_result,
                "completion_time": datetime.now().isoformat()
            })
            
            print(f"  ✅ 登录成功: {login_result['user_id']}")
            return login_result
            
        except Exception as e:
            self.state_manager.fail_task(task_id, str(e))
            print(f"  ❌ 登录失败: {e}")
            raise
    
    def simulate_video_watching(self, video_id: str, duration: int = 100) -> dict:
        """模拟视频观看"""
        print(f"🎥 开始观看视频: {video_id} (时长: {duration}分钟)")
        
        # 创建视频观看任务
        task_id = self.state_manager.create_task("video_watch", initial_data={
            "video_id": video_id,
            "duration": duration,
            "start_time": datetime.now().isoformat()
        })
        
        try:
            self.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            watched_time = 0
            
            # 模拟分段观看
            while watched_time < duration:
                segment_duration = min(20, duration - watched_time)  # 每段20分钟
                
                # 模拟观看这一段
                def watch_segment():
                    if random.random() < 0.2:  # 20%视频加载失败率
                        raise RetryableError("视频加载失败", RetryErrorType.NETWORK_ERROR)
                    return segment_duration
                
                try:
                    actual_watched = self.retry_manager.retry_function(
                        watch_segment,
                        max_attempts=3
                    )
                    
                    watched_time += actual_watched
                    progress = (watched_time / duration) * 100
                    
                    # 创建检查点
                    self.state_manager.create_checkpoint(task_id, f"watching_segment", 
                                                        watched_time // 20, {
                        "watch_progress": progress,
                        "watched_minutes": watched_time,
                        "current_segment": watched_time // 20 + 1
                    })
                    
                    self.state_manager.update_task_progress(task_id, progress)
                    print(f"  ⏱️  已观看: {watched_time}/{duration} 分钟 ({progress:.1f}%)")
                    
                    time.sleep(0.2)  # 模拟观看时间
                    
                except Exception as e:
                    print(f"  ⚠️  观看中断: {e}")
                    self.state_manager.update_task_status(task_id, TaskStatus.PAUSED)
                    raise
            
            # 完成观看
            result = {
                "total_watched": watched_time,
                "completion_rate": 100.0,
                "completion_time": datetime.now().isoformat()
            }
            
            self.state_manager.complete_task(task_id, {"watch_result": result})
            print(f"  ✅ 视频观看完成: {video_id}")
            return result
            
        except Exception as e:
            self.state_manager.fail_task(task_id, str(e))
            print(f"  ❌ 视频观看失败: {e}")
            raise
    
    def simulate_course_sync(self, course_id: str, item_count: int = 50) -> dict:
        """模拟课程同步"""
        print(f"📚 开始同步课程: {course_id} ({item_count} 项)")
        
        # 创建课程同步任务
        task_id = self.state_manager.create_task("course_sync", initial_data={
            "course_id": course_id,
            "total_items": item_count,
            "sync_start": datetime.now().isoformat()
        })
        
        try:
            self.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            synced_items = 0
            
            # 批量同步
            batch_size = 10
            while synced_items < item_count:
                current_batch = min(batch_size, item_count - synced_items)
                
                # 模拟同步批次
                def sync_batch():
                    if random.random() < 0.15:  # 15%同步失败率
                        raise RetryableError("课程数据同步失败", RetryErrorType.NETWORK_ERROR)
                    return current_batch
                
                try:
                    synced_count = self.retry_manager.retry_function(
                        sync_batch,
                        max_attempts=3
                    )
                    
                    synced_items += synced_count
                    progress = (synced_items / item_count) * 100
                    
                    # 创建检查点
                    self.state_manager.create_checkpoint(task_id, f"sync_batch", 
                                                        synced_items // batch_size, {
                        "synced_items": synced_items,
                        "total_items": item_count,
                        "current_batch": synced_items // batch_size + 1,
                        "sync_progress": progress
                    })
                    
                    self.state_manager.update_task_progress(task_id, progress)
                    print(f"  📋 已同步: {synced_items}/{item_count} 项 ({progress:.1f}%)")
                    
                    time.sleep(0.3)  # 模拟同步时间
                    
                except Exception as e:
                    print(f"  ⚠️  同步中断: {e}")
                    self.state_manager.update_task_status(task_id, TaskStatus.PAUSED)
                    raise
            
            # 完成同步
            result = {
                "synced_count": synced_items,
                "success_rate": 100.0,
                "completion_time": datetime.now().isoformat()
            }
            
            self.state_manager.complete_task(task_id, {"sync_result": result})
            print(f"  ✅ 课程同步完成: {course_id}")
            return result
            
        except Exception as e:
            self.state_manager.fail_task(task_id, str(e))
            print(f"  ❌ 课程同步失败: {e}")
            raise
    
    def simulate_crash_scenario(self):
        """模拟系统崩溃场景"""
        print("\\n💥 模拟系统崩溃场景")
        
        # 创建一些运行中的任务
        tasks = []
        
        # 登录任务（进行到一半）
        login_task = self.state_manager.create_task("user_login", "crash_login_001")
        self.state_manager.update_task_status(login_task, TaskStatus.RUNNING)
        self.state_manager.update_task_progress(login_task, 60.0)
        self.state_manager.create_checkpoint(login_task, "captcha_verification", 3, {
            "captcha_solved": True,
            "verification_pending": True
        })
        tasks.append(login_task)
        
        # 视频观看任务（看了一半）
        video_task = self.state_manager.create_task("video_watch", "crash_video_001")
        self.state_manager.update_task_status(video_task, TaskStatus.RUNNING)
        self.state_manager.update_task_progress(video_task, 45.0)
        self.state_manager.create_checkpoint(video_task, "watching_segment", 2, {
            "watch_progress": 45.0,
            "watched_minutes": 45,
            "current_segment": 3
        })
        tasks.append(video_task)
        
        # 同步任务（同步到30%）
        sync_task = self.state_manager.create_task("course_sync", "crash_sync_001")
        self.state_manager.update_task_status(sync_task, TaskStatus.RUNNING)
        self.state_manager.update_task_progress(sync_task, 30.0)
        self.state_manager.create_checkpoint(sync_task, "sync_batch", 1, {
            "synced_items": 15,
            "total_items": 50,
            "current_batch": 2
        })
        tasks.append(sync_task)
        
        print(f"📝 已创建 {len(tasks)} 个运行中的任务")
        
        # 模拟程序崩溃（创建残留文件）
        self.recovery_manager.pid_file.write_text("99999")  # 假PID
        self.recovery_manager.lock_file.write_text("crash_lock_content")
        
        print("💣 模拟系统崩溃...")
        time.sleep(1)
        
        return tasks
    
    def demonstrate_crash_recovery(self):
        """演示崩溃恢复"""
        print("\\n🔄 开始崩溃恢复演示")
        
        # 检测崩溃
        crashed = self.recovery_manager.detect_crash_on_startup()
        print(f"🔍 崩溃检测结果: {'检测到崩溃' if crashed else '正常启动'}")
        
        if crashed:
            # 执行恢复
            print("🚑 执行崩溃恢复...")
            session = self.recovery_manager.recover_from_crash()
            
            print(f"📊 恢复会话结果:")
            print(f"   会话ID: {session.session_id}")
            print(f"   恢复状态: {session.recovery_status}")
            print(f"   恢复任务数: {len(session.recovered_tasks)}")
            print(f"   清理资源数: {len(session.cleaned_resources)}")
            
            if session.recovered_tasks:
                print(f"   恢复的任务:")
                for task_id in session.recovered_tasks:
                    task_state = self.state_manager.get_task_state(task_id)
                    if task_state:
                        print(f"     - {task_id}: {task_state.status.value} ({task_state.progress:.1f}%)")
            
            return session
        
        return None
    
    def demonstrate_task_resumption(self):
        """演示任务恢复"""
        print("\\n▶️  开始任务恢复演示")
        
        # 获取可恢复的任务
        resumable_tasks = self.state_manager.get_resumable_tasks()
        
        if not resumable_tasks:
            print("📝 没有可恢复的任务")
            return
        
        print(f"📋 发现 {len(resumable_tasks)} 个可恢复任务:")
        
        for task in resumable_tasks:
            print(f"\\n🔄 恢复任务: {task.task_id} ({task.task_type})")
            print(f"   当前状态: {task.status.value}")
            print(f"   当前进度: {task.progress:.1f}%")
            
            if task.checkpoint:
                print(f"   检查点: {task.checkpoint.step} (步骤 {task.checkpoint.step_index})")
            
            # 尝试恢复任务
            success = self.state_manager.resume_task(task.task_id)
            if success:
                print(f"   ✅ 任务恢复成功")
                
                # 模拟继续执行
                if task.task_type == "video_watch":
                    try:
                        remaining = 100 - task.progress
                        print(f"   📹 继续观看剩余 {remaining:.1f}% 的视频...")
                        time.sleep(1)  # 模拟观看
                        self.state_manager.complete_task(task.task_id, {
                            "resumed_at": datetime.now().isoformat(),
                            "completion_method": "resumed"
                        })
                        print(f"   ✅ 视频观看完成")
                    except Exception as e:
                        print(f"   ❌ 视频观看继续失败: {e}")
                
                elif task.task_type == "course_sync":
                    try:
                        remaining_items = int((100 - task.progress) * 0.5)  # 简化计算
                        print(f"   📚 继续同步剩余 {remaining_items} 项...")
                        time.sleep(0.8)  # 模拟同步
                        self.state_manager.complete_task(task.task_id, {
                            "resumed_at": datetime.now().isoformat(),
                            "completion_method": "resumed"
                        })
                        print(f"   ✅ 课程同步完成")
                    except Exception as e:
                        print(f"   ❌ 课程同步继续失败: {e}")
                
                elif task.task_type == "user_login":
                    try:
                        print(f"   👤 完成登录验证...")
                        time.sleep(0.5)
                        self.state_manager.complete_task(task.task_id, {
                            "resumed_at": datetime.now().isoformat(),
                            "completion_method": "resumed",
                            "user_id": "resumed_user",
                            "token": "resumed_token"
                        })
                        print(f"   ✅ 登录完成")
                    except Exception as e:
                        print(f"   ❌ 登录继续失败: {e}")
            else:
                print(f"   ❌ 任务恢复失败")
    
    def show_system_status(self):
        """显示系统状态"""
        print("\\n📊 系统状态统计")
        print("=" * 50)
        
        # 任务统计
        task_stats = self.state_manager.get_task_statistics()
        print("📋 任务统计:")
        print(f"   总任务数: {task_stats['total']}")
        print(f"   可恢复任务: {task_stats['resumable_count']}")
        
        if task_stats['by_status']:
            print("   按状态分布:")
            for status, count in task_stats['by_status'].items():
                print(f"     {status}: {count}")
        
        if task_stats['by_type']:
            print("   按类型分布:")
            for task_type, count in task_stats['by_type'].items():
                print(f"     {task_type}: {count}")
        
        # 重试统计
        retry_stats = self.retry_manager.get_retry_statistics()
        print(f"\\n🔄 重试统计:")
        print(f"   活跃重试上下文: {retry_stats['active_contexts']}")
        print(f"   重试策略数: {retry_stats['total_strategies']}")
        print(f"   错误分类器数: {retry_stats['error_classifiers']}")
        
        # 恢复统计
        recovery_stats = self.recovery_manager.get_recovery_statistics()
        print(f"\\n🚑 恢复统计:")
        print(f"   当前进程ID: {recovery_stats['current_pid']}")
        print(f"   PID文件存在: {recovery_stats['pid_file_exists']}")
        print(f"   锁文件存在: {recovery_stats['lock_file_exists']}")
        print(f"   活跃资源数: {recovery_stats['active_resources']}")
        print(f"   恢复处理器数: {recovery_stats['registered_recovery_handlers']}")
        print(f"   清理处理器数: {recovery_stats['registered_cleanup_handlers']}")
        print(f"   7天内恢复事件: {recovery_stats['recovery_events_7days']}")
        
        # 数据库统计
        db_stats = self.persistence.get_database_stats()
        print(f"\\n💾 数据库统计:")
        print(f"   数据库大小: {db_stats['db_size'] / 1024:.1f} KB")
        print(f"   任务记录数: {db_stats['task_count']}")
        print(f"   会话记录数: {db_stats['session_count']}")
        print(f"   配置记录数: {db_stats['config_count']}")
        print(f"   恢复日志数: {db_stats['recovery_log_count']}")
    
    def cleanup(self):
        """清理资源"""
        print("\\n🧹 清理系统资源...")
        
        # 清理已完成的任务
        cleaned_tasks = self.state_manager.clean_completed_tasks(keep_hours=0)
        print(f"   已清理 {cleaned_tasks} 个已完成任务")
        
        # 清理过期会话
        cleaned_sessions = self.persistence.cleanup_expired_sessions()
        print(f"   已清理 {cleaned_sessions} 个过期会话")
        
        # 压缩数据库
        self.persistence.vacuum_database()
        print("   数据库已压缩")
        
        # 关闭组件
        self.recovery_manager.shutdown()
        self.state_manager.close()
        self.persistence.close()
        
        print("   ✅ 系统资源清理完成")


def main():
    """主演示函数"""
    print("🔧 错误恢复机制演示")
    print("=" * 60)
    
    simulator = LearningAutomationSimulator()
    
    try:
        # 启动正常运行模式
        simulator.recovery_manager.start_normal_operation()
        print("✅ 系统启动完成\\n")
        
        # 检查是否有崩溃需要恢复
        recovery_session = simulator.demonstrate_crash_recovery()
        
        if recovery_session:
            # 有崩溃恢复，演示任务恢复
            simulator.demonstrate_task_resumption()
        else:
            # 正常启动，演示正常功能
            print("🎯 开始正常功能演示\\n")
            
            # 演示用户登录
            try:
                login_result = simulator.simulate_user_login("demo_user")
                print(f"登录成功: {login_result['user_id']}")
            except Exception as e:
                print(f"登录演示失败: {e}")
            
            print()  # 空行
            
            # 演示视频观看
            try:
                video_result = simulator.simulate_video_watching("video_001", 60)
                print(f"视频观看完成: {video_result['completion_rate']}%")
            except Exception as e:
                print(f"视频观看演示失败: {e}")
            
            print()  # 空行
            
            # 演示课程同步
            try:
                sync_result = simulator.simulate_course_sync("course_001", 30)
                print(f"课程同步完成: {sync_result['synced_count']} 项")
            except Exception as e:
                print(f"课程同步演示失败: {e}")
            
            print()  # 空行
            
            # 模拟崩溃场景（为下次演示准备）
            print("🔥 为下次演示创建崩溃场景...")
            crash_tasks = simulator.simulate_crash_scenario()
            print(f"已创建 {len(crash_tasks)} 个任务用于崩溃恢复演示")
        
        # 显示系统状态
        simulator.show_system_status()
        
        print("\\n🎉 演示完成！")
        print("💡 提示: 再次运行此脚本将演示崩溃恢复功能")
        
    except KeyboardInterrupt:
        print("\\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        simulator.cleanup()


if __name__ == "__main__":
    main()