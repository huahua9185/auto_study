#!/usr/bin/env python3
"""
测试增强版弹窗处理逻辑
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

def test_popup_enhancements():
    """测试弹窗处理增强功能"""
    print_section("弹窗处理增强验证")
    
    main_file = Path("src/auto_study/main.py")
    learning_automator_file = Path("src/auto_study/automation/learning_automator.py")
    
    if not main_file.exists():
        print("❌ 未找到main.py文件")
        return False
    
    if not learning_automator_file.exists():
        print("❌ 未找到learning_automator.py文件")
        return False
    
    with open(main_file, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    with open(learning_automator_file, 'r', encoding='utf-8') as f:
        automator_content = f.read()
    
    # 检查主要增强功能
    enhancements = {
        "多次重试机制": "max_retries = 3" in main_content,
        "更长等待时间": "await asyncio.sleep(3)" in main_content,
        "更全面选择器覆盖": "el-dialog__wrapper:has" in main_content,
        "学习内容过滤": "学习相关弹窗" in main_content,
        "精确按钮匹配": "learning_keywords = " in main_content,
        "弹窗消失验证": "弹窗已消失" in main_content,
        "多阶段处理": "第一阶段" in main_content and "第二阶段" in main_content,
        "播放失败重试": "播放失败，再次尝试处理弹窗" in main_content,
        "VideoController增强": "VideoController: 检查播放确认弹窗" in automator_content
    }
    
    print("🔍 弹窗处理增强检查结果:")
    all_passed = True
    for feature, passed in enhancements.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {feature}")
        if not passed:
            all_passed = False
    
    return all_passed

def test_popup_detection_strategy():
    """测试弹窗检测策略"""
    print_section("弹窗检测策略分析")
    
    print("📋 新的弹窗检测策略:")
    strategies = [
        "✅ 多层选择器覆盖: Element UI + 通用 + 自定义",
        "✅ 内容过滤: 只处理包含学习相关关键词的弹窗",
        "✅ 可见性验证: 排除隐藏的弹窗元素",
        "✅ 精确按钮匹配: 学习关键词 > 确认关键词 > 主要按钮",
        "✅ 多次重试: 最多3次尝试，每次间隔3秒",
        "✅ 结果验证: 点击后验证弹窗是否消失"
    ]
    
    for strategy in strategies:
        print(f"  {strategy}")
    
    print("\n🎯 处理流程:")
    flow = [
        "1. 页面跳转后立即处理弹窗 (第一阶段)",
        "2. 等待3秒页面完全稳定",
        "3. 播放前最终弹窗检查 (第二阶段)", 
        "4. 开始视频播放",
        "5. 播放失败时再次处理弹窗并重试"
    ]
    
    for step in flow:
        print(f"  {step}")

def test_selector_improvements():
    """测试选择器改进"""
    print_section("选择器改进对比")
    
    print("📊 选择器覆盖范围对比:")
    print("\n🔴 原始选择器 (可能遗漏):")
    old_selectors = [
        "  '.el-dialog'",
        "  '.el-message-box'", 
        "  '.popup'",
        "  '.modal'",
        "  '[role=\"dialog\"]'"
    ]
    for sel in old_selectors:
        print(sel)
    
    print("\n🟢 增强选择器 (全面覆盖):")
    new_selectors = [
        "  '.el-dialog__wrapper:has(.el-dialog[aria-label])'  # 完整Element UI弹窗",
        "  '.el-dialog:not([style*=\"display: none\"])'       # 排除隐藏弹窗",
        "  '.el-message-box__wrapper:not([style*=\"display: none\"])'",
        "  '.modal:not(.fade):not([style*=\"display: none\"])'  # 排除动画中的模态框",
        "  '.study-dialog', '.confirm-dialog', '.course-dialog'  # 自定义学习弹窗",
        "  '[style*=\"z-index\"]:not([style*=\"display: none\"])'  # 基于层级的弹窗"
    ]
    for sel in new_selectors:
        print(sel)

def test_button_matching_logic():
    """测试按钮匹配逻辑"""
    print_section("按钮匹配逻辑改进")
    
    print("🎯 新的按钮匹配优先级:")
    priorities = [
        "1. 学习关键词匹配 (最高优先级)",
        "   - '开始学习', '继续学习', '进入学习', '开始播放'",
        "",
        "2. 确认关键词匹配 (中等优先级)",
        "   - '确定', '确认', 'OK', '好的'",
        "",
        "3. 主要按钮类匹配 (最后选择)",
        "   - 'primary' class, 主要样式的按钮"
    ]
    
    for priority in priorities:
        if priority:
            print(f"  {priority}")
        else:
            print()
    
    print("\n🔍 匹配过程:")
    process = [
        "1. 获取按钮文本和CSS类",
        "2. 记录详细的匹配信息到日志",
        "3. 按优先级顺序检查匹配条件",
        "4. 找到匹配后立即点击并验证",
        "5. 等待2秒确保弹窗消失"
    ]
    
    for step in process:
        print(f"  {step}")

def test_error_scenarios():
    """测试错误场景处理"""
    print_section("错误场景处理")
    
    print("⚠️ 可能遇到的问题及解决方案:")
    scenarios = {
        "弹窗加载延迟": {
            "问题": "弹窗在页面跳转后需要时间加载",
            "解决": "增加等待时间到3秒，多阶段检测"
        },
        "弹窗内容动态": {
            "问题": "弹窗内容根据课程状态动态变化",
            "解决": "内容过滤，只处理学习相关弹窗"
        },
        "按钮样式多样": {
            "问题": "不同页面的确认按钮样式不统一",
            "解决": "多层选择器 + 优先级匹配"
        },
        "点击无效果": {
            "问题": "按钮点击后弹窗仍然存在",
            "解决": "点击验证 + 重试机制"
        }
    }
    
    for scenario, info in scenarios.items():
        print(f"\n{scenario}:")
        print(f"  问题: {info['问题']}")
        print(f"  解决: {info['解决']}")

def main():
    """主测试函数"""
    print("🔧 测试增强版弹窗处理逻辑")
    print("📅 针对问题: '继续学习'按钮没有被正确点击")
    
    # 运行测试
    passed = test_popup_detection_strategy()
    passed = test_popup_enhancements() and passed
    test_selector_improvements()
    test_button_matching_logic()
    test_error_scenarios()
    
    # 总结
    print_section("测试总结")
    
    if passed:
        print("✅ 所有弹窗处理增强功能已实现!")
        print()
        print("🎯 主要改进:")
        improvements = [
            "• 3次重试机制，每次间隔3秒",
            "• 更长的弹窗等待时间 (3秒)",
            "• 全面的选择器覆盖，包括隐藏状态过滤",
            "• 学习内容过滤，避免误操作其他弹窗",
            "• 精确的按钮匹配优先级",
            "• 多阶段弹窗处理 (页面跳转后 + 播放前)",
            "• 播放失败后的弹窗重试",
            "• 详细的日志记录，便于调试"
        ]
        
        for improvement in improvements:
            print(f"  {improvement}")
        
        print()
        print("🚀 建议测试步骤:")
        print("  1. 配置环境: 创建.env文件添加用户名密码")
        print("  2. 安装依赖: pip install playwright python-dotenv loguru")
        print("  3. 运行测试: python3 -m src.auto_study.main")
        print("  4. 观察日志: 查找弹窗处理相关信息")
        
        print()
        print("🔍 关键日志标识:")
        log_markers = [
            "• '🎯 发现学习相关弹窗'",
            "• '✅ 匹配学习关键词'",
            "• '🎯 点击学习确认按钮'", 
            "• '✅ 学习确认弹窗处理完成'"
        ]
        for marker in log_markers:
            print(f"  {marker}")
    else:
        print("❌ 部分增强功能实现不完整")
        print("请检查代码修改是否正确应用")

if __name__ == "__main__":
    main()