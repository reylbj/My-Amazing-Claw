# 🚀 从这里开始

欢迎使用 OpenClaw！这是你的快速入门指南。

---

## ⚡ 3分钟快速开始

### 步骤 1: 安装
```bash
./scripts/install.sh
```

### 步骤 2: 设置 API 密钥
```bash
export CLAUDE_API_KEY='your-claude-api-key-here'
```

### 步骤 3: 验证安装
```bash
./scripts/openclaw.sh status
```

✅ 完成！现在你可以开始使用了。

---

## 📖 接下来做什么？

### 🎯 如果你想快速了解功能
👉 阅读 [INDEX.md](INDEX.md) - 项目概览（5分钟）

### 📚 如果你想深入学习
👉 阅读 [README.md](README.md) - 完整使用指南（15分钟）

### 🔍 如果你想快速查询
👉 查看 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速参考卡（随时查阅）

### 💻 如果你想看代码示例
👉 运行示例：
```bash
python3 examples/basic_usage.py
python3 examples/batch_processing.py
python3 examples/custom_rules.py
```

### 🔒 如果你关心安全
👉 阅读 [HEARTBEAT.md](HEARTBEAT.md) - 安全约束详解

### 📊 如果你想优化配额
👉 阅读 [API_STRATEGY.md](API_STRATEGY.md) - API 调用策略

---

## 🎓 学习路径推荐

```
第1天 (30分钟)
├─ 运行 install.sh 安装
├─ 阅读 INDEX.md 了解概览
├─ 运行 basic_usage.py 看示例
└─ 尝试 openclaw.sh status 查看配额

第2天 (1小时)
├─ 阅读 README.md 完整指南
├─ 运行 batch_processing.py 学习优化
├─ 查看 QUICK_REFERENCE.md 作为速查表
└─ 尝试集成到你的项目

第3天 (1小时)
├─ 阅读 HEARTBEAT.md 理解安全机制
├─ 运行 custom_rules.py 学习自定义
├─ 根据需求调整 api_config.yaml
└─ 设置定时任务生成报告
```

---


## 🆘 遇到问题？

### 检查环境
```bash
./scripts/openclaw.sh check
```

### 查看日志
```bash
tail -f ~/.openclaw/logs/api_usage.log
```

### 查看帮助
```bash
./scripts/openclaw.sh help
```

---

## 📞 快速命令参考

```bash
# 查看配额状态
./scripts/openclaw.sh status

# 生成每日报告
./scripts/openclaw.sh report

# 测试智能路由
./scripts/openclaw.sh test

# 清理旧数据
./scripts/openclaw.sh cleanup

# 运行示例
python3 examples/basic_usage.py
```

---

## 🎯 核心概念速览

### 三级安全
- 🔴 **禁止**: 删除重要数据、未授权通信
- 🟡 **确认**: 大规模修改、发送消息
- 🟢 **允许**: 只读操作、临时文件

### 三模型策略
- **Pro** (80/天): 复杂任务（架构设计、安全审计）
- **Flash** (200/天): 常规任务（代码审查、功能开发）
- **Flash-Lite** (900/天): 简单任务（文本分类、监控）

### 三大优化
- **批处理**: 合并任务，节省 40-60%
- **缓存**: 避免重复，节省 20-40%
- **本地处理**: 优先本地，节省 50-70%

---

## 🌟 开始你的 OpenClaw 之旅

OpenClaw 的设计理念：**解放双手，但绝不越过安全底线** 🦞

现在，选择一个入口开始吧：

- 📖 [INDEX.md](INDEX.md) - 项目概览
- 📚 [README.md](README.md) - 完整指南
- 🔍 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速参考
- 💻 [examples/](examples/) - 代码示例

祝使用愉快！
