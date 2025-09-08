# 测试命令指南

## 🔍 测试修改结果

### 1. 快速验证（无需依赖）
```bash
# 验证所有修改是否生效
python3 quick_test.py

# 查看测试结果（已包含6个功能测试）
python3 test_all_features.py
```

### 2. 安装依赖
```bash
# 安装Python依赖
pip install playwright python-dotenv loguru

# 安装浏览器驱动
playwright install chromium
```

### 3. 配置环境
创建 `.env` 文件：
```
USERNAME=你的用户名
PASSWORD=你的密码
```

### 4. 功能测试

#### 模拟模式测试（推荐先运行）
```bash
# 模拟学习流程，不真正播放视频
python3 -m src.auto_study.main --mode simulate
```

#### 单功能测试
```bash
# 测试串行学习逻辑
python3 test_serial_learning.py

# 测试弹窗处理
python3 test_popup_handling.py

# 测试并发防护
python3 test_concurrent_prevention.py

# 测试课程数据和导航
python3 test_flow.py
```

#### 正式运行
```bash
# 开始自动学习（会真正学习课程）
python3 -m src.auto_study.main
```

## ✅ 验证要点

### 串行学习验证
- 观察日志中是否显示 "📋 学习模式：严格串行执行"
- 确认每门课程是依次学习，不并发
- 检查课程间是否有5秒休息

### 弹窗处理验证
- 观察是否自动点击"开始学习"或"继续学习"按钮
- 查看日志中是否有"检查是否有学习确认弹窗"
- 确认弹窗被正确处理后开始播放

### 课程数据验证
- 确认加载了26门课程（而不是20门）
- 检查进行中的课程是否优先学习
- 验证已完成的课程被跳过

### 导航增强验证
- 观察是否从课程列表页成功进入播放页面
- 检查URL提取逻辑是否工作
- 确认视频播放器被正确检测

## 📊 预期结果

1. **课程加载**: 成功提取最多50门课程
2. **学习模式**: 严格串行，一次只学习一门
3. **弹窗处理**: 自动处理学习确认弹窗
4. **进度跟踪**: 实时显示学习进度
5. **错误恢复**: 单课程失败不影响后续

## 🚀 完整测试流程

1. 运行快速测试验证修改
   ```bash
   python3 quick_test.py
   ```

2. 安装依赖并配置
   ```bash
   pip install playwright python-dotenv loguru
   playwright install chromium
   ```

3. 模拟模式测试
   ```bash
   python3 -m src.auto_study.main --mode simulate
   ```

4. 观察以下关键日志：
   - "开始串行学习 X 门待完成课程"
   - "检查是否有学习确认弹窗"
   - "[1/24] 🎯 开始学习课程: xxx"
   - "✅ 课程 [1/24] 学习完成"
   - "⏳ 课程间休息5秒"

## ⚠️ 注意事项

- 首次运行会下载浏览器驱动，需要良好的网络连接
- 串行学习24门课程预计需要约18小时
- 建议先用模拟模式测试，确认无误后再正式运行
- 保持网络稳定，避免中断学习流程