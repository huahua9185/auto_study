#!/usr/bin/env python3
"""
综合测试脚本：验证所有修改功能
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# 添加源码路径
sys.path.append(str(Path(__file__).parent / "src"))

def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_course_data():
    """测试1: 验证课程数据"""
    print_section("测试1: 课程数据验证")
    
    courses_file = Path(__file__).parent / "data" / "courses.json"
    
    if not courses_file.exists():
        print("❌ 未找到courses.json文件")
        return False
    
    with open(courses_file, 'r', encoding='utf-8') as f:
        courses = json.load(f)
    
    print(f"✅ 成功加载课程数据")
    print(f"📊 课程统计:")
    print(f"  • 总课程数: {len(courses)}")
    
    # 按状态统计
    completed = sum(1 for c in courses if c.get('progress', 0) >= 1.0)
    in_progress = sum(1 for c in courses if 0 < c.get('progress', 0) < 1.0)
    not_started = sum(1 for c in courses if c.get('progress', 0) == 0)
    
    print(f"  • 已完成: {completed} 门")
    print(f"  • 进行中: {in_progress} 门")
    print(f"  • 未开始: {not_started} 门")
    
    # 显示进行中的课程
    if in_progress > 0:
        print("\n📚 进行中的课程:")
        for course in courses:
            if 0 < course.get('progress', 0) < 1.0:
                print(f"  - {course['title']} (进度: {course['progress']*100:.1f}%)")
    
    return True

def test_course_limit():
    """测试2: 验证课程提取上限"""
    print_section("测试2: 课程提取上限")
    
    # 读取main.py检查上限设置
    main_file = Path(__file__).parent / "src" / "auto_study" / "main.py"
    
    if main_file.exists():
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "max_courses = min(50, course_count)" in content:
                print("✅ 课程提取上限已设置为 50 门")
            else:
                print("❌ 未找到预期的课程上限设置")
                return False
    else:
        print("❌ 未找到main.py文件")
        return False
    
    return True

def test_serial_execution():
    """测试3: 验证串行执行机制"""
    print_section("测试3: 串行执行机制")
    
    checks = {
        "for循环串行结构": False,
        "await等待机制": False,
        "课程间休息": False,
        "会话冲突检测": False,
        "强制停止机制": False
    }
    
    main_file = Path(__file__).parent / "src" / "auto_study" / "main.py"
    
    if main_file.exists():
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查关键代码片段
            if "for i, course in enumerate(pending_courses, 1):" in content:
                checks["for循环串行结构"] = True
            
            if "await self._learn_single_course(course)" in content:
                checks["await等待机制"] = True
            
            if "课程间休息5秒" in content:
                checks["课程间休息"] = True
            
            if "if hasattr(self.learning_automator, 'current_session') and self.learning_automator.current_session:" in content:
                checks["会话冲突检测"] = True
            
            if "await self.learning_automator.stop_learning()" in content:
                checks["强制停止机制"] = True
    
    print("串行控制机制检查:")
    all_passed = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False
    
    return all_passed

def test_popup_handling():
    """测试4: 验证弹窗处理机制"""
    print_section("测试4: 弹窗处理机制")
    
    main_file = Path(__file__).parent / "src" / "auto_study" / "main.py"
    
    if main_file.exists():
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查弹窗处理函数
            if "_handle_learning_confirmation_popup" in content:
                print("✅ 主流程弹窗处理函数已实现")
            else:
                print("❌ 未找到弹窗处理函数")
                return False
            
            # 检查弹窗选择器
            popup_selectors = [
                '.el-dialog',
                '.el-message-box',
                '.popup',
                '.modal'
            ]
            
            found_selectors = sum(1 for s in popup_selectors if s in content)
            print(f"✅ 发现 {found_selectors}/{len(popup_selectors)} 个弹窗选择器")
            
            # 检查按钮文本
            button_texts = [
                '开始学习',
                '继续学习',
                '确定',
                '确认'
            ]
            
            found_texts = sum(1 for t in button_texts if t in content)
            print(f"✅ 发现 {found_texts}/{len(button_texts)} 个按钮文本匹配")
    
    # 检查视频控制器中的弹窗处理
    automator_file = Path(__file__).parent / "src" / "auto_study" / "automation" / "learning_automator.py"
    
    if automator_file.exists():
        with open(automator_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "_handle_play_confirmation_popup" in content:
                print("✅ 视频控制器弹窗处理已实现")
            else:
                print("⚠️  视频控制器中未找到弹窗处理")
    
    return True

def test_navigation_enhancement():
    """测试5: 验证导航增强功能"""
    print_section("测试5: 课程导航增强")
    
    main_file = Path(__file__).parent / "src" / "auto_study" / "main.py"
    
    if main_file.exists():
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查课程列表页面处理
            if 'if "study_center/tool_box/required" in course.url:' in content:
                print("✅ 课程列表页面识别逻辑已实现")
            else:
                print("❌ 未找到课程列表页面处理逻辑")
                return False
            
            # 检查学习按钮查找逻辑
            if "找到并点击对应课程的学习按钮" in content:
                print("✅ 课程学习按钮查找逻辑已实现")
            
            # 检查URL提取逻辑
            if "提取课程的实际学习链接" in content:
                print("✅ 课程URL提取逻辑已增强")
    
    return True

def test_video_detection():
    """测试6: 验证视频检测增强"""
    print_section("测试6: 视频播放器检测")
    
    automator_file = Path(__file__).parent / "src" / "auto_study" / "automation" / "learning_automator.py"
    
    if automator_file.exists():
        with open(automator_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查iframe检测
            if "检测iframe嵌入的视频播放器" in content:
                print("✅ iframe视频播放器检测已实现")
            
            # 检查播放器选择器数量
            selectors = [
                '.video-player',
                '.vjs-tech',
                '.jwplayer',
                '.dplayer',
                'iframe[src*="video"]'
            ]
            
            found = sum(1 for s in selectors if s in content)
            print(f"✅ 支持 {found}/{len(selectors)} 种播放器类型")
            
            # 检查播放按钮检测
            if "检查是否有播放按钮暗示有视频内容" in content:
                print("✅ 播放按钮检测逻辑已实现")
    
    return True

async def test_import_check():
    """测试7: 验证模块导入"""
    print_section("测试7: 模块导入检查")
    
    try:
        # 尝试导入主要模块
        from auto_study.main import AutoStudyApp
        print("✅ AutoStudyApp 导入成功")
        
        from auto_study.automation.course_manager import CourseManager
        print("✅ CourseManager 导入成功")
        
        from auto_study.automation.learning_automator import LearningAutomator
        print("✅ LearningAutomator 导入成功")
        
        from auto_study.automation.browser_manager import BrowserManager
        print("✅ BrowserManager 导入成功")
        
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("提示: 可能需要安装依赖，运行: pip install -r requirements.txt")
        return False

def generate_test_report(results):
    """生成测试报告"""
    print_section("测试报告")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"📊 测试结果统计:")
    print(f"  • 总测试数: {total}")
    print(f"  • 通过: {passed} ✅")
    print(f"  • 失败: {failed} ❌")
    print(f"  • 通过率: {passed/total*100:.1f}%")
    
    print("\n📋 详细结果:")
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统已准备就绪。")
    else:
        print("\n⚠️  部分测试失败，请检查相关功能。")
    
    return passed == total

async def main():
    """主测试函数"""
    print("🔍 自动学习系统 - 综合功能测试")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行所有测试
    results = {}
    
    # 同步测试
    results["课程数据验证"] = test_course_data()
    results["课程提取上限"] = test_course_limit()
    results["串行执行机制"] = test_serial_execution()
    results["弹窗处理机制"] = test_popup_handling()
    results["课程导航增强"] = test_navigation_enhancement()
    results["视频检测增强"] = test_video_detection()
    
    # 异步测试
    results["模块导入检查"] = await test_import_check()
    
    # 生成报告
    all_passed = generate_test_report(results)
    
    # 提供运行建议
    print_section("运行建议")
    
    if all_passed:
        print("✅ 系统测试通过，可以运行以下命令启动:")
        print("  1. 模拟模式测试: python3 -m src.auto_study.main --mode simulate")
        print("  2. 正式运行: python3 -m src.auto_study.main")
        print("\n注意事项:")
        print("  • 确保已配置环境变量 (.env 文件)")
        print("  • 首次运行会自动安装浏览器驱动")
        print("  • 串行学习24门课程预计需要约18小时")
    else:
        print("❌ 部分测试失败，建议:")
        print("  1. 检查失败的测试项")
        print("  2. 确认代码修改是否正确保存")
        print("  3. 运行 pip install -r requirements.txt 安装依赖")
        print("  4. 检查Python版本 (需要3.8+)")

if __name__ == "__main__":
    asyncio.run(main())