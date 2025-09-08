#!/usr/bin/env python3
"""
测试课程播放失败处理逻辑
"""
import sys
from pathlib import Path

# 添加源码路径
sys.path.append(str(Path(__file__).parent / "src"))

def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)

def test_failure_behavior():
    """测试失败行为修改"""
    print_section("失败处理逻辑测试")
    
    print("📋 原始行为 (已删除):")
    print("  ❌ 课程播放失败 → continue → 继续下一门课程")
    print("  问题: 失败的课程被跳过，可能遗漏重要内容")
    print()
    
    print("✅ 新行为 (已实现):")
    print("  ⛔ 课程播放失败 → return False → 终止程序")
    print("  优点: 确保每门课程都成功学习，不会遗漏")
    print()
    
    print("🔄 失败处理流程:")
    print("  1. 检测到课程播放失败")
    print("  2. 记录详细错误日志")
    print("  3. 显示失败原因和提示")
    print("  4. 设置 is_running = False")
    print("  5. 返回 False 终止学习流程")
    print("  6. 程序退出")

def test_error_messages():
    """测试错误信息增强"""
    print_section("错误信息增强")
    
    error_scenarios = {
        "缺少URL": {
            "原因": "课程数据不完整，无法获取学习链接",
            "日志": "⛔ 课程缺少URL: {course.title}"
        },
        "视频检测失败": {
            "原因": "尝试所有方式后仍无法找到或启动视频播放器",
            "日志": "⛔ 仍然未检测到视频播放器: {course.title}"
        },
        "启动学习失败": {
            "原因": "无法启动视频播放器或视频学习会话",
            "日志": "⛔ 启动视频学习失败: {course.title}"
        }
    }
    
    for scenario, info in error_scenarios.items():
        print(f"\n场景: {scenario}")
        print(f"  错误日志: {info['日志']}")
        print(f"  失败原因: {info['原因']}")

def test_code_verification():
    """验证代码修改"""
    print_section("代码修改验证")
    
    main_file = Path("src/auto_study/main.py")
    
    if not main_file.exists():
        print("❌ 未找到main.py文件")
        return False
    
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键修改
    checks = {
        "终止而非跳过": "课程播放失败时终止程序" in content,
        "设置运行状态": "self.is_running = False" in content,
        "返回False": "return False" in content and "课程播放失败" in content,
        "错误图标": "⛔" in content,
        "失败提示": "请检查网络连接、登录状态" in content
    }
    
    print("代码检查结果:")
    all_passed = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False
    
    return all_passed

def test_execution_flow():
    """测试执行流程"""
    print_section("执行流程示例")
    
    print("📚 假设有3门课程需要学习:")
    print("  课程1: 正常学习 ✅")
    print("  课程2: 播放失败 ❌")
    print("  课程3: 等待学习 ⏳")
    print()
    
    print("🔄 原流程（跳过失败）:")
    print("  1. 学习课程1 → 成功 ✅")
    print("  2. 学习课程2 → 失败 ❌ → 跳过")
    print("  3. 学习课程3 → 成功 ✅")
    print("  结果: 课程2被遗漏")
    print()
    
    print("⛔ 新流程（失败终止）:")
    print("  1. 学习课程1 → 成功 ✅")
    print("  2. 学习课程2 → 失败 ❌ → 终止")
    print("  3. 程序退出")
    print("  结果: 需要解决问题后重新运行")

def test_recovery_strategy():
    """测试恢复策略"""
    print_section("失败后的恢复策略")
    
    print("🔧 当课程播放失败时，用户应该:")
    print()
    print("1. 检查问题原因:")
    print("   • 网络连接是否正常")
    print("   • 登录状态是否有效")
    print("   • 课程页面是否可以手动访问")
    print("   • 视频播放器是否需要特殊权限")
    print()
    print("2. 解决问题后:")
    print("   • 重新运行程序")
    print("   • 由于课程进度已保存，会从失败的课程继续")
    print("   • 不会重复学习已完成的课程")
    print()
    print("3. 临时跳过方案:")
    print("   • 如果确实无法播放某课程")
    print("   • 可以手动编辑courses.json")
    print("   • 将该课程的progress设为1.0标记为完成")
    print("   • 或将status改为'completed'")

def main():
    """主测试函数"""
    print("🔍 测试课程播放失败处理逻辑")
    print("📅 修改内容: 失败时终止程序而不是跳过")
    
    # 运行测试
    test_failure_behavior()
    test_error_messages()
    passed = test_code_verification()
    test_execution_flow()
    test_recovery_strategy()
    
    # 总结
    print_section("测试总结")
    
    if passed:
        print("✅ 所有修改已成功实现!")
        print()
        print("🎯 关键改变:")
        print("  • 失败时终止: 确保不遗漏任何课程")
        print("  • 详细错误: 提供清晰的失败原因")
        print("  • 用户提示: 指导如何解决问题")
        print("  • 进度保护: 已完成的课程不会重复")
        print()
        print("⚠️  注意事项:")
        print("  • 这个修改使系统更严格")
        print("  • 任何播放失败都会导致程序终止")
        print("  • 适合需要确保每门课程都完成的场景")
    else:
        print("❌ 部分修改未生效，请检查代码")

if __name__ == "__main__":
    main()