---
name: auto_study
status: backlog
created: 2025-09-03T06:01:09Z
progress: 0%
prd: .claude/prds/auto_study.md
github: [Will be updated when synced to GitHub]
---

# Epic: auto_study

## Overview

构建一个针对edu.nxgbjy.org.cn平台的自动化学习系统，采用Python + Playwright架构实现浏览器自动化控制。系统将通过模拟真实用户行为，完成从登录到课程学习的全流程自动化，同时具备强大的反检测能力和错误恢复机制。核心设计理念是简单、可靠、易维护。

## Architecture Decisions

### 核心技术选型
- **浏览器自动化**: Playwright (优于Selenium，性能更好，API更现代)
- **编程语言**: Python 3.10+ (生态丰富，开发效率高)
- **OCR服务**: ddddocr (本地离线识别，无需API费用)
- **数据存储**: SQLite + JSON (轻量级，无需额外服务)
- **配置管理**: Python-dotenv + YAML (简单易用)
- **日志系统**: Python logging + Rich (美观且功能强大)

### 设计原则
- **模块化设计**: 各功能模块独立，便于维护和扩展
- **配置驱动**: 所有参数可配置，无需修改代码
- **错误容错**: 每个操作都有重试和恢复机制
- **行为仿真**: 深度模拟人类操作模式，避免检测

### 简化策略
- 使用Playwright的内置等待机制，减少自定义等待代码
- 利用浏览器上下文持久化，避免重复登录
- 采用事件驱动架构，减少轮询开销
- 复用Playwright的截图和录屏功能进行调试

## Technical Approach

### 核心组件架构

#### 1. 配置管理器 (ConfigManager)
- 加载和验证配置文件
- 管理用户凭据加密
- 动态参数调整

#### 2. 浏览器管理器 (BrowserManager)
- Playwright浏览器实例管理
- 上下文持久化和恢复
- 浏览器指纹随机化
- 自动重启和资源清理

#### 3. 认证模块 (AuthModule)
- 登录流程自动化
- 验证码识别集成
- Session管理
- 自动续期机制

#### 4. 课程管理器 (CourseManager)
- 课程列表获取和解析
- 学习状态跟踪
- 优先级排序算法
- 进度持久化

#### 5. 学习执行器 (LearningExecutor)
- 视频播放控制
- 进度监控
- 反检测行为模拟
- 异常处理和恢复

#### 6. 监控仪表盘 (MonitorDashboard)
- 实时状态显示
- 进度可视化
- 日志聚合
- 性能指标

### 反检测策略
```python
# 核心反检测技术
1. 浏览器指纹随机化
2. 鼠标轨迹模拟（贝塞尔曲线）
3. 键盘输入延迟（高斯分布）
4. 随机停顿和操作间隔
5. WebDriver特征隐藏
6. Canvas指纹混淆
```

### 数据流设计
```
用户配置 → 系统初始化 → 自动登录 → 获取课程
     ↓                              ↓
监控面板 ← 学习执行 ← 课程调度 ← 进度管理
```

## Implementation Strategy

### 开发方法
- **增量开发**: 从MVP逐步迭代到完整功能
- **测试驱动**: 每个模块都有单元测试和集成测试
- **持续集成**: 自动化测试和代码质量检查

### 质量保证
- 代码审查：所有代码需要review
- 自动化测试覆盖率 > 70%
- 错误日志和监控告警
- 用户反馈快速响应机制

### 部署策略
- Docker容器化部署
- 支持命令行和Web界面两种模式
- 配置热更新，无需重启
- 自动更新检查

## Task Breakdown Preview

精简为10个核心任务，确保高效实施：

- [ ] **T1: 项目初始化与环境搭建** - 创建项目结构，安装Playwright和依赖，配置开发环境
- [ ] **T2: 配置管理系统** - 实现配置文件加载、验证和加密存储
- [ ] **T3: 浏览器自动化基础** - 集成Playwright，实现浏览器启动、上下文管理
- [ ] **T4: 登录功能实现** - 自动填表、ddddocr验证码识别、登录状态验证
- [ ] **T5: 课程管理核心** - 课程列表获取、状态解析、进度存储
- [ ] **T6: 视频学习控制** - 播放控制、进度监控、异常处理
- [ ] **T7: 反检测机制** - 实现鼠标轨迹、键盘模拟、随机行为
- [ ] **T8: 监控与日志** - 实时状态显示、日志记录、异常告警
- [ ] **T9: 错误恢复机制** - 断点续传、自动重试、崩溃恢复
- [ ] **T10: 集成测试与优化** - 端到端测试、性能优化、用户文档

## Dependencies

### 外部服务依赖
- **edu.nxgbjy.org.cn平台**: 核心依赖，需要监控可用性
- **网络连接**: 稳定的互联网访问
- **Python环境**: 3.10或更高版本

### 技术栈依赖
```python
# requirements.txt 核心依赖
playwright>=1.40.0      # 浏览器自动化
ddddocr>=1.4.0         # 验证码识别
python-dotenv>=1.0.0   # 环境变量管理
pyyaml>=6.0           # 配置文件
rich>=13.0            # 终端UI
sqlalchemy>=2.0       # 数据库ORM
apscheduler>=3.10     # 定时任务
```

### 开发工具依赖
- Git版本控制
- VS Code或PyCharm IDE
- Chrome/Edge浏览器（调试用）

## Success Criteria (Technical)

### 性能基准
- 启动时间 < 15秒
- 内存占用 < 300MB
- CPU使用率 < 20%（空闲时）
- 单课程完成时间 = 视频实际时长 + 5%

### 质量门槛
- 代码测试覆盖率 > 70%
- 无Critical级别安全漏洞
- 代码复杂度 < 10（圈复杂度）
- 文档完整性 100%

### 可靠性指标
- 自动恢复成功率 > 90%
- 验证码识别准确率 > 85%
- 24小时连续运行稳定性
- 平均故障间隔时间 > 100小时

### 用户体验指标
- 安装配置时间 < 10分钟
- 命令行操作步骤 < 3步
- 错误提示清晰度评分 > 4.0/5
- 首次使用成功率 > 80%

## Estimated Effort

### 时间估算
- **总工期**: 3-4周（单人开发）
- **Phase 1 (MVP)**: 1周 - 基础功能
- **Phase 2 (Core)**: 1.5周 - 核心功能
- **Phase 3 (Polish)**: 0.5-1.5周 - 优化完善

### 资源需求
- **开发人员**: 1名Python开发者
- **测试环境**: 1个测试账号
- **开发设备**: 标准开发机即可

### 关键路径
1. 浏览器自动化基础 (前置依赖)
2. 登录功能 (核心依赖)
3. 反检测机制 (关键技术)
4. 视频学习控制 (业务核心)

### 风险缓冲
- 预留20%时间用于处理平台变化
- 保持代码灵活性以快速适配
- 建立用户反馈快速响应机制

## 优化建议

### 代码复用
- 利用Playwright内置功能，避免重复造轮子
- 使用成熟的OCR库，不自己实现识别算法
- 复用Python标准库，减少外部依赖

### 性能优化
- 使用浏览器上下文缓存，减少登录次数
- 采用异步编程提高并发能力
- 实现智能等待，避免固定延时

### 维护性优化
- 所有选择器配置化，便于更新
- 模块化设计，单一职责
- 完善的错误处理和日志记录

## Tasks Created
- [ ] 001.md - 项目初始化与环境搭建 (parallel: true with 007, 008)
- [ ] 002.md - 配置管理系统 (parallel: false, depends on 001)
- [ ] 003.md - 浏览器自动化基础 (parallel: false, depends on 001)
- [ ] 004.md - 登录功能实现 (parallel: false, depends on 002, 003)
- [ ] 005.md - 课程管理核心 (parallel: false, depends on 004)
- [ ] 006.md - 视频学习控制 (parallel: false, depends on 005)
- [ ] 007.md - 反检测机制 (parallel: true with 008, 009, depends on 003, 004)
- [ ] 008.md - 监控与日志 (parallel: true with 007, 009, depends on 001)
- [ ] 009.md - 错误恢复机制 (parallel: true with 007, 008, depends on 005, 006)
- [ ] 010.md - 集成测试与优化 (parallel: false, depends on all previous tasks)

Total tasks: 10
Parallel tasks: 6 (001 can run with 007,008; 007,008,009 can run together)
Sequential tasks: 4 (002,003,004,005,006,010)
Estimated total effort: 68 hours (~8.5 days)