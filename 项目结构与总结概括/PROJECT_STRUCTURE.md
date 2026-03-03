# OpenClaw 项目结构

```
openclaw-workspace/
│
├── README.md                          # 📖 使用指南
├── HEARTBEAT.md                       # 🔒 安全约束与监控配置
├── API_STRATEGY.md                    # 📊 API 调用策略详解
│
├── config/                            # ⚙️ 配置文件目录
│   └── api_config.yaml               # API 配置（模型、路由、配额等）
│
├── scripts/                           # 🛠️ 工具脚本目录
│   ├── openclaw.sh                   # 主管理脚本（初始化、状态、报告）
│   ├── quota_monitor.py              # 配额监控工具
│   └── smart_router.py               # 智能路由器
│
└── examples/                          # 📚 示例代码（即将创建）
    ├── basic_usage.py                # 基础使用示例
    ├── batch_processing.py           # 批处理示例
    └── custom_rules.py               # 自定义规则示例

运行时目录（~/.openclaw/）：
~/.openclaw/
├── config/                            # 用户配置
│   ├── api_config.yaml
│   └── HEARTBEAT.md
│
├── logs/                              # 日志文件
│   └── api_usage.log                 # API 使用日志（JSON 格式）
│
├── state/                             # 状态文件
│   ├── quota_state.json              # 配额使用状态
│   └── task_queue.json               # 任务队列
│
├── reports/                           # 报告目录
│   ├── daily/                        # 每日报告
│   │   └── report_20260228.md
│   └── weekly/                       # 每周报告
│       └── report_2026_week09.md
│
├── cache/                             # 缓存目录
│   ├── file_analysis/                # 文件分析缓存
│   ├── code_review/                  # 代码审查缓存
│   └── faq_answers/                  # FAQ 答案缓存
│
└── backups/                           # 备份目录
    └── {timestamp}/                  # 按时间戳组织的备份
```

## 文件说明

### 核心文档

- **README.md**: 完整的使用指南，包含快速开始、命令参考、故障排查等
- **HEARTBEAT.md**: 定义 OpenClaw 的安全边界和操作约束
- **API_STRATEGY.md**: 详细的 API 调用策略和优化方案

### 配置文件

- **api_config.yaml**:
  - 模型配置和配额限制
  - 路由策略和复杂度评估
  - 批处理、缓存、监控配置
  - 安全和实验性功能

### 脚本工具

- **openclaw.sh**:
  - 一键初始化环境
  - 查看配额状态
  - 生成使用报告
  - 环境检查和清理

- **quota_monitor.py**:
  - 实时监控配额使用
  - 记录 API 请求
  - 生成每日/每周报告
  - 配额状态检查

- **smart_router.py**:
  - 自动分析任务复杂度
  - 智能选择最优模型
  - 基于关键词的路由
  - 配额感知的降级策略

## 数据流程

```
用户请求
    ↓
smart_router.py (分析任务)
    ↓
计算复杂度 + 检查关键词
    ↓
quota_monitor.py (检查配额)
    ↓
选择最优模型
    ↓
执行 API 调用
    ↓
记录使用情况 (logs/api_usage.log)
    ↓
更新配额状态 (state/quota_state.json)
    ↓
返回结果
```

## 安全检查流程

```
操作请求
    ↓
HEARTBEAT.md (安全约束检查)
    ↓
是否在禁止列表？
    ├─ 是 → 拒绝执行
    └─ 否 → 继续
        ↓
是否需要确认？
    ├─ 是 → 请求用户确认
    └─ 否 → 继续
        ↓
创建备份 (backups/)
    ↓
执行操作
    ↓
记录审计日志
    ↓
完成
```

## 配额管理流程

```
每分钟:
  - 重置 RPM 计数器
  - 清理过期的分钟级数据

每小时:
  - 检查小时配额使用
  - 生成小时摘要
  - 触发预警（如超过阈值）

每天 00:00 UTC:
  - 重置每日配额
  - 生成每日报告
  - 归档昨日数据
  - 清理过期缓存

每周一 00:10:
  - 生成每周报告
  - 备份审计日志
  - 安全合规检查
```

## 快速命令参考

```bash
# 初始化
./scripts/openclaw.sh init

# 日常使用
./scripts/openclaw.sh status          # 查看配额
./scripts/openclaw.sh report          # 生成报告
./scripts/openclaw.sh test            # 测试路由

# 维护
./scripts/openclaw.sh cleanup         # 清理旧数据
./scripts/openclaw.sh check           # 环境检查

# Python 工具
python3 scripts/quota_monitor.py --status
python3 scripts/smart_router.py
```

## 集成示例

```python
# 在你的项目中使用 OpenClaw
from smart_router import SmartRouter
from quota_monitor import APIQuotaMonitor, ModelType

# 初始化
router = SmartRouter()
monitor = APIQuotaMonitor()

# 路由任务
model, info = router.route(
    "帮我审查这段代码",
    context={
        'code': your_code,
        'priority': 1
    }
)

# 查看路由决策
print(router.explain_routing(model, info))

# 执行 API 调用（你的实现）
response = call_gemini_api(model, your_prompt)

# 记录使用
monitor.record_request(model, tokens=1500, success=True)

# 检查配额
status, percentage, color = monitor.check_quota(model)
print(f"{color} 配额使用: {percentage:.1f}%")
```

## 环境要求

- Python 3.8+
- PyYAML
- macOS / Linux / Windows (WSL)
- Claude API Key（Gemini 兼容）

## 下一步

1. 运行 `./scripts/openclaw.sh init` 初始化环境
2. 设置 `CLAUDE_API_KEY` 环境变量（可兼容 `GEMINI_API_KEY`）
3. 查看 `README.md` 了解详细使用方法
4. 根据需要自定义 `config/api_config.yaml`
5. 在 `HEARTBEAT.md` 底部添加自定义安全规则
