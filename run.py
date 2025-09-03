#!/usr/bin/env python3
"""
自动学习系统启动器

集成了错误恢复机制、监控系统等完整功能
"""

import os
import sys
import signal
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.auto_study.main import AutoStudyApp
from src.auto_study.config.settings import settings
from src.auto_study.utils.logger import logger
from src.auto_study.recovery import (
    RecoveryManager, StateManager, RetryManager, PersistenceManager, TaskStatus
)
from src.auto_study.monitoring import MonitoringManager


class AutoStudySystem:
    """完整的自动学习系统"""
    
    def __init__(self):
        self.app = None
        self.recovery_manager = None
        self.monitoring_manager = None
        self.state_manager = None
        self.persistence = None
        self.is_shutting_down = False
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\\n收到信号 {signum}，开始优雅关闭...")
        asyncio.create_task(self.shutdown())
    
    async def initialize_recovery_system(self):
        """初始化错误恢复系统"""
        try:
            print("🔧 初始化错误恢复系统...")
            
            # 创建数据目录
            Path("data").mkdir(exist_ok=True)
            Path("logs").mkdir(exist_ok=True)
            
            # 初始化持久化管理器
            self.persistence = PersistenceManager("data/auto_study.db")
            
            # 初始化状态管理器
            self.state_manager = StateManager(self.persistence)
            
            # 初始化重试管理器
            retry_manager = RetryManager()
            
            # 初始化恢复管理器
            self.recovery_manager = RecoveryManager(
                self.state_manager,
                self.persistence,
                "data/auto_study.pid",
                "data/auto_study.lock"
            )
            
            # 注册恢复处理器
            self._register_recovery_handlers()
            
            print("✅ 错误恢复系统初始化完成")
            return True
            
        except Exception as e:
            print(f"❌ 错误恢复系统初始化失败: {e}")
            return False
    
    async def initialize_monitoring_system(self):
        """初始化监控系统"""
        try:
            print("📊 初始化监控系统...")
            
            # 初始化监控管理器
            self.monitoring_manager = MonitoringManager(
                log_dir="logs",
                enable_ui=True,  # 启用终端UI
                enable_alerts=True
            )
            
            # 启动监控
            self.monitoring_manager.start()
            
            print("✅ 监控系统初始化完成")
            return True
            
        except Exception as e:
            print(f"❌ 监控系统初始化失败: {e}")
            return False
    
    def _register_recovery_handlers(self):
        """注册恢复处理器"""
        
        def login_recovery_handler(task_state):
            """登录任务恢复处理器"""
            print(f"🔄 恢复登录任务: {task_state.task_id}")
            # 重新初始化登录状态
            return True
        
        def course_learning_recovery_handler(task_state):
            """课程学习任务恢复处理器"""
            print(f"📚 恢复课程学习任务: {task_state.task_id}")
            checkpoint = task_state.checkpoint
            if checkpoint:
                progress = checkpoint.data.get("progress", 0)
                print(f"   从进度 {progress}% 恢复")
                return True
            return False
        
        # 注册恢复处理器
        self.state_manager.register_recovery_handler("login", login_recovery_handler)
        self.state_manager.register_recovery_handler("course_learning", course_learning_recovery_handler)
        
        # 注册清理处理器
        def cleanup_browser_cache():
            print("🧹 清理浏览器缓存")
            # 清理浏览器相关缓存
        
        def cleanup_temp_downloads():
            print("🧹 清理临时下载文件")
            # 清理临时文件
        
        self.recovery_manager.register_cleanup_handler(cleanup_browser_cache)
        self.recovery_manager.register_cleanup_handler(cleanup_temp_downloads)
        
        # 注册关闭处理器
        def save_learning_progress():
            print("💾 保存学习进度")
            # 保存当前学习状态
        
        self.recovery_manager.register_shutdown_handler(save_learning_progress)
    
    async def check_crash_recovery(self):
        """检查并执行崩溃恢复"""
        try:
            print("🔍 检查是否需要崩溃恢复...")
            
            if self.recovery_manager.detect_crash_on_startup():
                print("💥 检测到上次异常退出，开始恢复...")
                
                # 执行崩溃恢复
                session = self.recovery_manager.recover_from_crash()
                
                print(f"📊 恢复结果:")
                print(f"   恢复状态: {session.recovery_status}")
                print(f"   恢复任务数: {len(session.recovered_tasks)}")
                print(f"   清理资源数: {len(session.cleaned_resources)}")
                
                if session.recovered_tasks:
                    print("📋 恢复的任务:")
                    for task_id in session.recovered_tasks:
                        task_state = self.state_manager.get_task_state(task_id)
                        if task_state:
                            print(f"   - {task_id}: {task_state.status.value} ({task_state.progress:.1f}%)")
                
                print("✅ 崩溃恢复完成")
                return True
            else:
                print("✅ 未检测到异常退出，正常启动")
                return False
                
        except Exception as e:
            print(f"❌ 崩溃恢复检查失败: {e}")
            return False
    
    async def start_normal_operation(self):
        """启动正常运行模式"""
        try:
            print("🚀 启动正常运行模式...")
            
            # 启动恢复管理器的正常运行模式
            self.recovery_manager.start_normal_operation()
            
            # 初始化主应用
            self.app = AutoStudyApp()
            
            # 创建学习任务
            task_id = self.state_manager.create_task("main_learning_session", initial_data={
                "start_time": datetime.now().isoformat(),
                "session_type": "auto_learning"
            })
            
            self.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            
            # 记录到监控系统
            if self.monitoring_manager:
                with self.monitoring_manager.task_context("系统启动") as monitor_task_id:
                    self.monitoring_manager.log_info("自动学习系统启动完成")
            
            print("✅ 正常运行模式启动完成")
            return task_id
            
        except Exception as e:
            print(f"❌ 启动正常运行模式失败: {e}")
            return None
    
    async def run_learning_session(self, task_id):
        """运行学习会话"""
        try:
            print("📚 开始学习会话...")
            
            # 更新任务进度
            self.state_manager.update_task_progress(task_id, 10.0, {"phase": "initialization"})
            
            # 创建检查点
            self.state_manager.create_checkpoint(task_id, "app_initialization", 1, {
                "initialized": True,
                "timestamp": datetime.now().isoformat()
            })
            
            # 记录监控信息
            if self.monitoring_manager:
                with self.monitoring_manager.task_context("学习会话") as monitor_task_id:
                    self.monitoring_manager.log_info("开始学习会话")
                    
                    # 运行主应用
                    await self.app.run()
                    
                    self.monitoring_manager.log_info("学习会话完成")
            else:
                await self.app.run()
            
            # 完成任务
            self.state_manager.complete_task(task_id, {
                "completion_time": datetime.now().isoformat(),
                "status": "success"
            })
            
            print("✅ 学习会话完成")
            
        except Exception as e:
            print(f"❌ 学习会话失败: {e}")
            self.state_manager.fail_task(task_id, str(e))
            
            # 记录错误到监控系统
            if self.monitoring_manager:
                self.monitoring_manager.log_error(f"学习会话失败: {e}")
    
    async def shutdown(self):
        """优雅关闭系统"""
        if self.is_shutting_down:
            return
        
        self.is_shutting_down = True
        print("\\n🛑 开始优雅关闭系统...")
        
        try:
            # 停止主应用
            if self.app:
                print("⏹️  停止主应用...")
                await self.app.cleanup()
            
            # 停止监控系统
            if self.monitoring_manager:
                print("📊 停止监控系统...")
                self.monitoring_manager.stop()
            
            # 关闭恢复系统
            if self.recovery_manager:
                print("🔧 关闭恢复系统...")
                self.recovery_manager.shutdown()
            
            # 关闭状态管理器
            if self.state_manager:
                print("💾 关闭状态管理器...")
                self.state_manager.close()
            
            # 关闭持久化管理器
            if self.persistence:
                print("🗃️  关闭持久化管理器...")
                self.persistence.close()
            
            print("✅ 系统优雅关闭完成")
            
        except Exception as e:
            print(f"❌ 关闭系统时发生错误: {e}")
    
    async def show_system_status(self):
        """显示系统状态"""
        print("\\n" + "="*60)
        print("📊 系统状态")
        print("="*60)
        
        # 任务统计
        if self.state_manager:
            task_stats = self.state_manager.get_task_statistics()
            print(f"📋 任务统计:")
            print(f"   总任务数: {task_stats['total']}")
            print(f"   可恢复任务: {task_stats['resumable_count']}")
            
            if task_stats['by_status']:
                print("   按状态分布:")
                for status, count in task_stats['by_status'].items():
                    print(f"     {status}: {count}")
        
        # 系统健康状态
        if self.monitoring_manager:
            health = self.monitoring_manager.get_system_health()
            print(f"\\n🏥 系统健康:")
            print(f"   性能评分: {health['performance_score']}")
            print(f"   健康状态: {health['health_status']}")
            print(f"   错误数量: {health['error_count']}")
            print(f"   活跃告警: {health['active_alerts']}")
        
        # 恢复系统统计
        if self.recovery_manager:
            recovery_stats = self.recovery_manager.get_recovery_statistics()
            print(f"\\n🚑 恢复系统:")
            print(f"   当前进程: {recovery_stats['current_pid']}")
            print(f"   活跃资源: {recovery_stats['active_resources']}")
            print(f"   恢复事件(7天): {recovery_stats['recovery_events_7days']}")
    
    async def run(self):
        """运行完整系统"""
        try:
            print("🤖 自动学习系统启动")
            print("="*60)
            
            # 1. 初始化错误恢复系统
            if not await self.initialize_recovery_system():
                return
            
            # 2. 初始化监控系统
            if not await self.initialize_monitoring_system():
                return
            
            # 3. 检查崩溃恢复
            recovered = await self.check_crash_recovery()
            
            if recovered:
                print("🔄 系统从异常状态恢复，检查是否有任务需要恢复...")
                
                # 获取可恢复的任务
                resumable_tasks = self.state_manager.get_resumable_tasks()
                if resumable_tasks:
                    print(f"发现 {len(resumable_tasks)} 个可恢复任务")
                    for task in resumable_tasks:
                        print(f"   - {task.task_id}: {task.progress:.1f}%")
                        
                        # 询问用户是否恢复
                        response = input(f"是否恢复任务 {task.task_id}? (y/n): ").strip().lower()
                        if response == 'y':
                            success = self.state_manager.resume_task(task.task_id)
                            if success:
                                print(f"✅ 任务 {task.task_id} 恢复成功")
                            else:
                                print(f"❌ 任务 {task.task_id} 恢复失败")
            
            # 4. 启动正常运行模式
            task_id = await self.start_normal_operation()
            if not task_id:
                return
            
            # 5. 运行学习会话
            await self.run_learning_session(task_id)
            
            # 6. 显示系统状态
            await self.show_system_status()
            
            print("\\n🎉 自动学习系统运行完成!")
            
        except KeyboardInterrupt:
            print("\\n⏹️  用户中断操作")
        except Exception as e:
            print(f"\\n❌ 系统运行异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.shutdown()


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动学习系统")
    parser.add_argument("--demo", action="store_true", help="运行演示模式")
    parser.add_argument("--monitoring-only", action="store_true", help="只运行监控演示")
    parser.add_argument("--recovery-only", action="store_true", help="只运行恢复演示")
    parser.add_argument("--config", type=str, help="配置文件路径")
    
    args = parser.parse_args()
    
    if args.demo or args.monitoring_only:
        # 运行监控演示
        print("🎬 运行监控系统演示...")
        from examples.monitoring_demo import main as monitoring_demo
        monitoring_demo()
        return
    
    if args.demo or args.recovery_only:
        # 运行恢复系统演示
        print("🎬 运行恢复系统演示...")
        from examples.recovery_demo import main as recovery_demo
        recovery_demo()
        return
    
    # 运行完整系统
    system = AutoStudySystem()
    await system.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n👋 再见!")
    except Exception as e:
        print(f"\\n💥 系统启动失败: {e}")
        sys.exit(1)