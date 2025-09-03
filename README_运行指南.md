# 自动学习系统 - 运行指南

## 🚀 快速开始

### 1. 环境准备

#### 系统要求
- Python 3.8+
- Chrome/Chromium 浏览器
- 4GB+ 内存
- 稳定的网络连接

#### 安装依赖
```bash
# 1. 克隆或下载项目到本地
cd auto_study

# 2. 创建虚拟环境（推荐）
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\\Scripts\\activate
# macOS/Linux:
source venv/bin/activate

# 4. 安装依赖包
pip install -r requirements.txt

# 5. 安装Playwright浏览器
playwright install chromium
```

### 2. 配置系统

#### 创建配置文件
复制示例配置文件并修改：
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下关键信息：
```bash
# 学习平台配置
PLATFORM_URL=https://your-learning-platform.com
USERNAME=your_username
PASSWORD=your_password

# 浏览器配置
BROWSER_HEADLESS=false  # true为无头模式，false为可视化模式
BROWSER_SLOW_MO=100     # 操作延迟（毫秒）

# 学习配置
AUTO_ANSWER=true        # 是否自动答题
SKIP_COMPLETED=true     # 跳过已完成课程
LEARNING_SPEED=1.25     # 播放倍速

# 系统配置
LOG_LEVEL=INFO          # 日志级别
MAX_RETRIES=3           # 最大重试次数
```

### 3. 运行系统

#### 完整运行（推荐）
```bash
python run.py
```

这将启动完整的自动学习系统，包括：
- 错误恢复机制
- 监控与日志系统
- 自动学习功能
- 崩溃检测与恢复

#### 演示模式
```bash
# 监控系统演示
python run.py --monitoring-only

# 恢复系统演示
python run.py --recovery-only

# 完整功能演示
python run.py --demo
```

#### 基础运行（仅核心功能）
```bash
python -m src.auto_study.main
```

## 🔧 系统功能详解

### 错误恢复机制

系统具备完整的错误恢复能力：

#### 自动重试
- **智能错误分类**：网络错误、认证错误、系统错误等
- **指数退避策略**：避免频繁重试造成的压力
- **自定义重试策略**：可针对不同错误类型配置重试参数

#### 断点续传
- **任务状态持久化**：所有学习任务状态自动保存
- **进度恢复**：系统重启后可从中断点继续
- **检查点机制**：关键步骤自动创建恢复点

#### 崩溃恢复
- **自动崩溃检测**：启动时检测异常退出
- **资源清理**：自动清理残留文件和进程锁
- **任务恢复**：未完成任务自动恢复到可执行状态

### 监控与日志系统

#### 实时监控界面
```bash
# 启动时会显示实时监控界面
┌─────────────────── 自动学习系统监控 ────────────────────┐
│ 系统状态: 运行中     │ CPU: 45%    内存: 2.1GB/8GB    │
│ 任务进度: 3/10      │ 网络: 良好   磁盘: 256GB可用    │
└─────────────────────────────────────────────────────────┘
```

#### 日志记录
- **结构化日志**：JSON格式，便于分析
- **多级日志**：DEBUG、INFO、WARNING、ERROR、CRITICAL
- **分类记录**：系统、用户、自动化、浏览器、网络、性能、安全
- **自动轮转**：防止日志文件过大

#### 告警系统
- **错误峰值检测**：连续错误自动告警
- **性能异常检测**：响应时间异常提醒
- **资源监控**：CPU、内存使用率告警

### 学习自动化功能

#### 智能登录
- **多种登录方式**：用户名密码、扫码、SSO等
- **验证码自动识别**：支持图像和滑块验证码
- **登录状态保持**：自动维护会话有效性
- **反检测机制**：模拟真实用户行为

#### 课程管理
- **自动发现课程**：爬取所有可学习课程
- **智能排序**：按优先级、截止时间排序
- **进度跟踪**：实时更新学习进度
- **状态同步**：与平台状态保持同步

#### 学习自动化
- **视频自动播放**：支持倍速播放
- **自动答题**：题库匹配和智能推理
- **进度控制**：防止过快完成引起注意
- **行为模拟**：模拟真实学习行为

## 📊 运行状态监控

### 查看系统状态
运行过程中，系统会显示详细的状态信息：

```
📊 系统状态
============================================================
📋 任务统计:
   总任务数: 15
   可恢复任务: 2
   按状态分布:
     running: 1
     completed: 10
     paused: 2
     failed: 2

🏥 系统健康:
   性能评分: 85.2
   健康状态: 良好
   错误数量: 3
   活跃告警: 0

🚑 恢复系统:
   当前进程: 12345
   活跃资源: 2
   恢复事件(7天): 5
```

### 日志文件位置
```
logs/
├── auto_study.log          # 主日志文件
├── error.log              # 错误日志
├── performance.log        # 性能日志
├── automation.log         # 自动化操作日志
└── recovery.log           # 恢复操作日志
```

### 数据存储位置
```
data/
├── auto_study.db          # 主数据库
├── auto_study.pid         # 进程ID文件
├── auto_study.lock        # 进程锁文件
├── courses.json           # 课程数据
├── user_progress.json     # 学习进度
└── configs/               # 配置文件
    ├── retry_strategies.json
    └── monitoring_rules.json
```

## 🛠️ 故障排查

### 常见问题解决

#### 1. 系统启动失败
```bash
# 检查Python版本
python --version  # 需要3.8+

# 检查依赖安装
pip list | grep -E "(playwright|loguru|rich)"

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

#### 2. 浏览器启动失败
```bash
# 重新安装浏览器
playwright install chromium

# 检查Chrome是否正确安装
google-chrome --version  # Linux
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version  # macOS
```

#### 3. 登录失败
- 检查用户名密码是否正确
- 确认学习平台URL是否可访问
- 查看是否需要验证码识别
- 检查网络连接状态

#### 4. 数据库锁定
```bash
# 检查是否有残留进程
ps aux | grep auto_study

# 删除锁文件
rm -f data/auto_study.lock data/auto_study.pid

# 重启系统
python run.py
```

#### 5. 内存使用过高
```bash
# 查看系统资源使用
python -c "
from src.auto_study.recovery import PersistenceManager
p = PersistenceManager()
print('数据库统计:', p.get_database_stats())
p.close()
"

# 清理历史数据
python -c "
from src.auto_study.recovery import StateManager, PersistenceManager
p = PersistenceManager()
s = StateManager(p)
cleaned = s.clean_completed_tasks(keep_hours=24)
print(f'已清理 {cleaned} 个已完成任务')
s.close()
p.close()
"
```

### 日志分析

#### 查看错误日志
```bash
# 查看最近的错误
tail -f logs/error.log

# 统计错误类型
grep -o '"level":"ERROR"' logs/auto_study.log | wc -l

# 查看特定错误
grep "登录失败" logs/auto_study.log
```

#### 性能分析
```bash
# 查看性能指标
grep "performance_metric" logs/auto_study.log | tail -10

# 分析响应时间
grep "响应时间" logs/performance.log | awk '{print $NF}' | sort -n
```

### 数据恢复

#### 备份数据库
```bash
python -c "
from src.auto_study.recovery import PersistenceManager
from datetime import datetime
p = PersistenceManager()
backup_path = f'backup_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.db'
p.backup_database(backup_path)
print(f'备份已创建: {backup_path}')
p.close()
"
```

#### 恢复任务状态
```bash
# 查看可恢复的任务
python -c "
from src.auto_study.recovery import StateManager, PersistenceManager
p = PersistenceManager()
s = StateManager(p)
tasks = s.get_resumable_tasks()
for task in tasks:
    print(f'{task.task_id}: {task.progress:.1f}%')
s.close()
p.close()
"
```

## ⚙️ 高级配置

### 自定义重试策略
创建 `config/retry_strategies.json`：
```json
{
  "network_error": {
    "max_attempts": 5,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2.0
  },
  "auth_error": {
    "max_attempts": 3,
    "base_delay": 5.0,
    "max_delay": 30.0,
    "exponential_base": 2.0
  }
}
```

### 监控告警配置
创建 `config/alert_rules.json`：
```json
{
  "error_spike": {
    "threshold": 10,
    "time_window": 300,
    "severity": "HIGH"
  },
  "performance_degradation": {
    "response_time_threshold": 5000,
    "severity": "MEDIUM"
  }
}
```

### 学习行为配置
创建 `config/learning_behavior.json`：
```json
{
  "video_watching": {
    "min_watch_time": 0.8,
    "max_speed": 2.0,
    "random_pause": true
  },
  "quiz_answering": {
    "think_time_min": 5,
    "think_time_max": 30,
    "accuracy_rate": 0.85
  }
}
```

## 🔒 安全注意事项

1. **凭据保护**
   - 不要将用户名密码硬编码在代码中
   - 使用环境变量或加密存储敏感信息
   - 定期更换密码

2. **访问控制**
   - 限制系统运行的用户权限
   - 定期检查日志访问记录
   - 设置防火墙规则

3. **数据隐私**
   - 学习记录数据仅本地存储
   - 不上传个人敏感信息
   - 定期清理历史数据

4. **合规使用**
   - 遵守学习平台的使用条款
   - 不要用于恶意目的
   - 尊重知识产权

## 📈 性能优化

### 系统调优
```python
# 数据库性能优化
python -c "
from src.auto_study.recovery import PersistenceManager
p = PersistenceManager()
p.vacuum_database()  # 压缩数据库
print('数据库已优化')
p.close()
"

# 清理过期数据
python -c "
from src.auto_study.recovery import StateManager, PersistenceManager
p = PersistenceManager()
s = StateManager(p)
cleaned_tasks = s.clean_completed_tasks(keep_hours=24)
cleaned_sessions = p.cleanup_expired_sessions()
print(f'已清理: {cleaned_tasks} 个任务, {cleaned_sessions} 个会话')
s.close()
p.close()
"
```

### 资源监控
- 监控CPU使用率 < 80%
- 监控内存使用率 < 70%
- 监控磁盘空间 > 1GB可用
- 监控网络连接稳定性

## 🆘 技术支持

### 获取帮助
1. 查看日志文件了解具体错误信息
2. 检查网络连接和学习平台状态  
3. 确认配置文件设置正确
4. 更新到最新版本

### 问题报告
提交问题时请包含：
- 系统环境信息（操作系统、Python版本）
- 错误日志片段
- 复现步骤
- 配置文件（脱敏后）

### 版本更新
```bash
# 更新系统
git pull origin main
pip install -r requirements.txt --upgrade

# 检查版本
python -c "
from src.auto_study.recovery import __version__
print(f'恢复系统版本: {__version__}')
"
```

---

## 🎉 开始使用

现在您可以运行以下命令启动系统：

```bash
python run.py
```

首次运行时，系统会：
1. 初始化数据库和配置
2. 检查依赖和环境
3. 启动监控和恢复系统
4. 进入自动学习流程

祝您学习愉快！ 📚✨