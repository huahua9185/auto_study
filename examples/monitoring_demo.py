"""
监控与日志系统演示
展示完整的监控功能
"""

import time
import random
import threading
from datetime import datetime

from src.auto_study.monitoring import (
    MonitoringManager, LogCategory, AlertSeverity, NotificationConfig
)


def simulate_automation_tasks(manager: MonitoringManager):
    """模拟自动化任务"""
    tasks = [
        "用户登录",
        "课程列表获取", 
        "视频播放",
        "进度更新",
        "数据同步"
    ]
    
    for i, task_name in enumerate(tasks):
        with manager.task_context(task_name) as task_id:
            # 模拟任务步骤
            steps = ["准备", "执行", "验证", "完成"]
            
            for j, step in enumerate(steps):
                progress = (j + 1) / len(steps) * 100
                manager.update_task_progress(task_id, progress, f"{step}中...")
                
                # 记录自动化步骤
                manager.log_automation_step(task_id, step, "成功", random.uniform(0.1, 2.0))
                
                time.sleep(random.uniform(0.5, 1.5))
            
            # 随机失败一些任务
            if random.random() < 0.2:  # 20%失败率
                raise Exception(f"{task_name}执行失败")


def simulate_browser_operations(manager: MonitoringManager):
    """模拟浏览器操作"""
    urls = [
        "https://example.com/login",
        "https://example.com/dashboard",
        "https://example.com/courses", 
        "https://example.com/profile"
    ]
    
    for url in urls:
        # 记录导航
        manager.log_browser_action("导航", url, "开始加载")
        time.sleep(random.uniform(0.5, 2.0))
        
        # 记录网络请求
        status_codes = [200, 200, 200, 404, 500]  # 大部分成功，少数失败
        status = random.choice(status_codes)
        duration = random.uniform(0.1, 3.0)
        
        manager.log_network_request("GET", url, status, duration)
        
        if status == 200:
            manager.log_browser_action("加载完成", url, "页面加载成功")
        else:
            manager.log_error(f"页面加载失败: {url} - HTTP {status}", LogCategory.BROWSER)
        
        time.sleep(random.uniform(0.3, 1.0))


def simulate_user_activities(manager: MonitoringManager):
    """模拟用户活动"""
    users = ["user001", "user002", "user003"]
    actions = ["登录", "查看课程", "开始学习", "提交作业", "退出登录"]
    
    for _ in range(20):
        user = random.choice(users)
        action = random.choice(actions)
        
        manager.log_user_action(user, action)
        
        # 记录安全事件
        if action == "登录" and random.random() < 0.1:  # 10%的登录失败
            manager.log_security_event(
                "登录失败", 
                f"用户 {user} 登录失败",
                f"192.168.1.{random.randint(100, 200)}",
                "MEDIUM"
            )
        
        time.sleep(random.uniform(0.2, 1.0))


def simulate_performance_monitoring(manager: MonitoringManager):
    """模拟性能监控"""
    metrics = [
        ("CPU使用率", "cpu_usage", "%"),
        ("内存使用率", "memory_usage", "%"),
        ("响应时间", "response_time", "ms"),
        ("并发用户数", "concurrent_users", "个"),
        ("数据库连接数", "db_connections", "个")
    ]
    
    for _ in range(30):
        for metric_name, metric_key, unit in metrics:
            if metric_key in ["cpu_usage", "memory_usage"]:
                value = random.uniform(20, 95)
            elif metric_key == "response_time":
                value = random.uniform(50, 2000)
            elif metric_key == "concurrent_users":
                value = random.randint(10, 500)
            else:
                value = random.randint(5, 100)
            
            manager.log_performance_metric(metric_name, value, unit)
        
        time.sleep(2.0)


def generate_error_spike(manager: MonitoringManager):
    """生成错误峰值来触发告警"""
    print("🚨 生成错误峰值以触发告警...")
    
    error_types = [
        "数据库连接失败",
        "网络超时", 
        "认证失败",
        "资源不足",
        "服务不可用"
    ]
    
    for i in range(15):  # 快速生成15个错误
        error_type = random.choice(error_types)
        manager.log_error(f"{error_type}: 错误详情 {i}", LogCategory.SYSTEM)
        time.sleep(0.1)


def main():
    """主演示函数"""
    print("🤖 监控与日志系统演示")
    print("=" * 50)
    
    # 创建通知配置
    notification_config = NotificationConfig(
        file_path="logs/demo_alerts.log"
    )
    
    # 创建监控管理器
    manager = MonitoringManager(
        log_dir="logs",
        notification_config=notification_config,
        enable_ui=False,  # 演示中禁用UI避免阻塞
        enable_alerts=True
    )
    
    # 启动监控
    print("📊 启动监控系统...")
    manager.start()
    
    try:
        print("🔄 开始模拟各种活动...\n")
        
        # 创建模拟活动的线程
        threads = [
            threading.Thread(target=simulate_automation_tasks, args=(manager,), name="自动化任务"),
            threading.Thread(target=simulate_browser_operations, args=(manager,), name="浏览器操作"),
            threading.Thread(target=simulate_user_activities, args=(manager,), name="用户活动"),
            threading.Thread(target=simulate_performance_monitoring, args=(manager,), name="性能监控")
        ]
        
        # 启动所有线程
        for thread in threads:
            thread.daemon = True
            thread.start()
            print(f"✅ 启动线程: {thread.name}")
        
        # 等待一些活动
        time.sleep(10)
        
        # 生成错误峰值
        generate_error_spike(manager)
        
        # 继续运行一段时间让告警系统检测
        print("⏳ 等待告警检测...")
        time.sleep(8)
        
        # 显示系统健康状态
        print("\n" + "="*50)
        print("📈 系统健康状态:")
        health = manager.get_system_health()
        for key, value in health.items():
            if key != 'system_metrics':
                print(f"  {key}: {value}")
        
        # 显示活跃告警
        print("\n🚨 活跃告警:")
        active_alerts = manager.get_active_alerts()
        if active_alerts:
            for alert in active_alerts[:5]:  # 显示前5个
                print(f"  - [{alert.severity.value}] {alert.title}")
                print(f"    {alert.message}")
        else:
            print("  无活跃告警")
        
        # 显示日志统计
        print("\n📊 日志统计:")
        log_stats = manager.logger.get_log_statistics()
        for level, count in log_stats.items():
            if not level.startswith('category_') and count > 0:
                print(f"  {level}: {count}")
        
        # 显示错误摘要
        print("\n🔍 错误摘要:")
        error_summary = manager.logger.get_error_summary(hours=1)
        if error_summary:
            for error in error_summary[:3]:  # 显示前3个错误
                print(f"  - {error['error_type'][:50]}... (出现 {error['count']} 次)")
        else:
            print("  无错误记录")
        
        # 导出数据
        print("\n💾 导出监控数据...")
        export_path = f"logs/monitoring_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        manager.export_data(export_path, hours=1)
        print(f"  数据已导出到: {export_path}_*.json")
        
        print("\n🎉 演示完成！")
        print("📝 查看 logs/ 目录下的日志文件获取详细信息")
        
    except KeyboardInterrupt:
        print("\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        manager.log_error(f"演示错误: {e}", LogCategory.SYSTEM, exception=e)
    finally:
        # 停止监控
        print("\n⏹️  停止监控系统...")
        manager.stop()
        
        # 等待线程结束
        time.sleep(2)
        
        print("✅ 演示结束")


if __name__ == "__main__":
    main()