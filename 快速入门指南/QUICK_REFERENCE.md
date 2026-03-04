# OpenClaw 快速参考卡

## 🚀 快速开始

```bash
# 1. 初始化
cd /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace
./scripts/openclaw.sh init

# 2. 设置 API 密钥
export CLAUDE_API_KEY='your-api-key'

# 3. 查看状态
./scripts/openclaw.sh status
```


## 🔒 安全等级

### 🔴 绝对禁止
- 删除重要文件/对话/邮件
- 未经确认的对外通信
- 修改系统权限
- 财务法律操作

### 🟡 需要确认
- 大规模文件修改 (>100行)
- 发送邮件/消息
- 安装软件
- 系统配置变更

### 🟢 自动允许
- 只读操作
- 临时文件创建
- 日志记录
- 数据分类

## 💻 常用命令

### 管理工具
```bash
./scripts/openclaw.sh status    # 查看配额
./scripts/openclaw.sh report    # 生成报告
./scripts/openclaw.sh test      # 测试路由
./scripts/openclaw.sh cleanup   # 清理数据
./scripts/openclaw.sh check     # 环境检查
```

### Python 工具
```bash
# 配额监控
python3 scripts/quota_monitor.py --status
python3 scripts/quota_monitor.py --report
python3 scripts/quota_monitor.py --record flash 1500 true

# 智能路由
python3 scripts/smart_router.py

# 运行示例
python3 examples/basic_usage.py
python3 examples/batch_processing.py
python3 examples/custom_rules.py
```

## 🎯 复杂度评分

| 分数 | 任务类型 | 建议模型 |
|------|---------|---------|
| 0-4 | 简单查询、文本处理 | Haiku |
| 5-7 | 代码审查、功能开发 | Sonnet |
| 8-10 | 架构设计、安全审计 | Opus |

## 📈 优化技巧

### 批处理
- 合并相似任务
- 节省 40-60% 调用
- 批次大小: 5-10 个
- 等待时间: ≤30 秒

### 缓存
- 文件分析: 24 小时
- 代码审查: 7 天
- FAQ 答案: 30 天
- 节省 20-40% 请求

### 本地处理
- 文本搜索/替换
- 格式转换
- 数据验证
- 节省 50-70% 配额

## 🔧 配置文件

### API 配置
```
~/.openclaw/config/api_config.yaml
```

### 安全约束
```
~/.openclaw/config/HEARTBEAT.md
```

### 日志和状态
```
~/.openclaw/logs/api_usage.log
~/.openclaw/state/quota_state.json
```

```

### API 密钥问题
```bash
# 检查密钥
echo $CLAUDE_API_KEY

# 重新设置
export CLAUDE_API_KEY='your-key'
```

### 路由异常
```bash
# 测试路由器
python3 scripts/smart_router.py
```

## 📝 代码示例

### 基础使用
```python
from smart_router import SmartRouter
from quota_monitor import APIQuotaMonitor, ModelType

router = SmartRouter()
monitor = APIQuotaMonitor()

# 路由任务
model, info = router.route("审查代码", context={'code': code})

# 记录使用
monitor.record_request(model, tokens=1500, success=True)

# 检查配额
status, percentage, color = monitor.check_quota(model)
```

### 批处理
```python
# 合并多个任务
tasks = ["分析 file1.py", "分析 file2.py", "分析 file3.py"]
combined = f"批量分析: {', '.join(tasks)}"

# 一次调用处理所有任务
model, info = router.route(combined)
```

### 自定义规则
```python
# 添加安全规则
security.add_rule({
    'name': 'my_rule',
    'condition': lambda op: check_condition(op),
    'action': 'block',
    'message': '操作被阻止'
})

# 添加路由规则
router.add_routing_rule({
    'name': 'my_routing',
    'condition': lambda desc, ctx: 'keyword' in desc,
    'model': ModelType.PRO
})
```

## 📊 监控指标

### 配额状态
- 🟢 OK: < 70%
- 🟡 Caution: 70-85%
- 🟠 Warning: 85-95%
- 🔴 Critical: > 95%

### 每日报告
```bash
./scripts/openclaw.sh report
# 保存在: ~/.openclaw/reports/daily/
```

## 🔐 安全最佳实践

1. ✅ 使用环境变量存储密钥
2. ✅ 定期轮换密钥 (90天)
3. ✅ 启用审计日志
4. ✅ 定期检查安全配置
5. ❌ 不要硬编码密钥
6. ❌ 不要禁用安全检查

## 💡 性能优化

### 减少调用
- 启用批处理: -40~60%
- 使用缓存: -20~40%
- 本地处理: -50~70%

### 优化 Token
- 移除不必要上下文
- 压缩重复信息
- 限制历史长度
- 设置 max_tokens

### 智能降级
- 配额不足自动降级
- 低复杂度用低级模型
- 高峰时段分散请求

## 📞 获取帮助

### 文档
- [README.md](README.md) - 完整指南
- [HEARTBEAT.md](HEARTBEAT.md) - 安全约束
- [API_STRATEGY.md](API_STRATEGY.md) - 调用策略

### 命令帮助
```bash
./scripts/openclaw.sh help
```

### 日志查看
```bash
tail -f ~/.openclaw/logs/api_usage.log
```

## 🎓 学习路径

1. **入门** (5分钟)
   - 运行 `openclaw.sh init`
   - 查看 `openclaw.sh status`
   - 阅读 README.md

2. **基础** (15分钟)
   - 运行 `examples/basic_usage.py`
   - 理解三级安全模型
   - 学习配额管理

3. **进阶** (30分钟)
   - 运行 `examples/batch_processing.py`
   - 配置自定义规则
   - 优化 Token 使用

4. **高级** (1小时)
   - 运行 `examples/custom_rules.py`
   - 集成到现有项目
   - 自定义路由策略

## 🔄 维护计划

### 每日
- 查看配额报告
- 检查异常日志

### 每周
- 审查高风险操作
- 备份审计日志

### 每月
- 更新安全策略
- 优化配额分配
- 检查系统性能

---

**OpenClaw**: 解放双手，但绝不越过安全底线 🦞
