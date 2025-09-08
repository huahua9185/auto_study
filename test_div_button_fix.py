#!/usr/bin/env python3
"""
测试div元素作为按钮的修复
针对问题：继续学习按钮是<div class="user_choise">而不是<button>
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

def test_div_button_support():
    """测试对div按钮的支持"""
    print_section("DIV按钮支持验证")
    
    main_file = Path("src/auto_study/main.py")
    learning_automator_file = Path("src/auto_study/automation/learning_automator.py")
    
    if not main_file.exists() or not learning_automator_file.exists():
        print("❌ 未找到必要文件")
        return False
    
    with open(main_file, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    with open(learning_automator_file, 'r', encoding='utf-8') as f:
        automator_content = f.read()
    
    # 检查关键修复
    fixes = {
        "user_choise选择器": ".user_choise" in main_content,
        "continue容器检测": ".continue" in main_content,
        "div文本匹配": 'div:has-text("继续学习")' in main_content,
        "user_choise类检测": "'user_choise' in button_classes" in main_content,
        "元素标签获取": "el.tagName.toLowerCase()" in main_content,
        "VideoController支持": ".user_choise" in automator_content
    }
    
    print("🔍 DIV按钮支持检查:")
    all_passed = True
    for feature, passed in fixes.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {feature}")
        if not passed:
            all_passed = False
    
    return all_passed

def show_actual_html_structure():
    """显示实际的HTML结构"""
    print_section("实际HTML结构分析")
    
    print("📄 用户提供的HTML结构:")
    print("""
    <div class="continue">
        <div style="color:#ff5400">您上次学习到 00:04:08</div>
        <div class="user_choise">继续学习</div>
    </div>
    """)
    
    print("🔍 关键发现:")
    findings = [
        "1. 按钮不是<button>元素，而是<div>元素",
        "2. 按钮有特定的类名: user_choise",
        "3. 按钮包含在continue容器中",
        "4. 按钮文本是'继续学习'",
        "5. 上方有学习进度提示文本"
    ]
    
    for finding in findings:
        print(f"  {finding}")

def show_selector_priority():
    """显示选择器优先级"""
    print_section("新的选择器优先级")
    
    print("🎯 弹窗检测优先级:")
    popup_priority = [
        "1. '.continue:has(.user_choise)' - 特定容器",
        "2. 'div.continue' - 继续学习容器",
        "3. Element UI弹窗选择器",
        "4. 通用弹窗选择器"
    ]
    
    for priority in popup_priority:
        print(f"  {priority}")
    
    print("\n🎯 按钮点击优先级:")
    button_priority = [
        "1. '.user_choise:has-text(\"继续学习\")' - 最精确匹配",
        "2. 'div.user_choise' - 类名匹配",
        "3. '.continue .user_choise' - 容器内匹配",
        "4. 'div:has-text(\"继续学习\")' - 文本匹配",
        "5. 标准button元素",
        "6. 其他可点击元素"
    ]
    
    for priority in button_priority:
        print(f"  {priority}")

def show_matching_logic():
    """显示匹配逻辑"""
    print_section("增强的匹配逻辑")
    
    print("🔍 新的匹配流程:")
    flow = [
        "1. 获取元素的标签名（button/div/span等）",
        "2. 获取元素的class属性",
        "3. 特别检查user_choise类",
        "4. 检查文本内容匹配",
        "5. 记录详细信息到日志",
        "6. 点击匹配的元素"
    ]
    
    for step in flow:
        print(f"  {step}")
    
    print("\n📝 日志输出示例:")
    logs = [
        "检查按钮: 选择器=.user_choise, 文本='继续学习', 类名=user_choise",
        "✅ 匹配user_choise类的div按钮: 继续学习",
        "🎯 点击学习确认元素: 标签=div, 文本='继续学习', 类='user_choise'"
    ]
    
    for log in logs:
        print(f"  {log}")

def show_troubleshooting():
    """显示故障排除指南"""
    print_section("故障排除指南")
    
    print("⚠️ 如果仍然无法点击，检查以下内容:")
    
    checks = {
        "元素可见性": [
            "• 元素是否被其他元素遮挡",
            "• 元素是否在视口内",
            "• 使用await button.scroll_into_view_if_needed()"
        ],
        "元素状态": [
            "• 元素是否已启用（非disabled）",
            "• 元素是否可点击",
            "• 使用await button.is_enabled()"
        ],
        "时机问题": [
            "• 弹窗是否完全加载",
            "• 动画是否完成",
            "• 增加等待时间"
        ],
        "选择器准确性": [
            "• 使用浏览器开发者工具验证选择器",
            "• 检查是否有多个匹配元素",
            "• 使用更精确的选择器"
        ]
    }
    
    for category, items in checks.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  {item}")

def main():
    """主测试函数"""
    print("🔧 测试DIV元素作为按钮的修复")
    print("📅 针对问题: <div class='user_choise'>继续学习</div>")
    
    # 运行测试
    show_actual_html_structure()
    passed = test_div_button_support()
    show_selector_priority()
    show_matching_logic()
    show_troubleshooting()
    
    # 总结
    print_section("测试总结")
    
    if passed:
        print("✅ DIV按钮支持已成功实现!")
        print()
        print("🎯 关键改进:")
        improvements = [
            "• 支持div元素作为可点击按钮",
            "• 特定类名user_choise的识别",
            "• continue容器的检测",
            "• 元素标签类型的记录",
            "• 更精确的选择器匹配"
        ]
        
        for improvement in improvements:
            print(f"  {improvement}")
        
        print()
        print("🚀 测试建议:")
        print("  1. 运行程序: python3 -m src.auto_study.main")
        print("  2. 观察日志中的以下关键信息:")
        print("     • '✅ 匹配user_choise类的div按钮'")
        print("     • '🎯 点击学习确认元素: 标签=div'")
        print("  3. 确认视频开始播放")
        
    else:
        print("❌ 部分修复未完成，请检查代码")

if __name__ == "__main__":
    main()