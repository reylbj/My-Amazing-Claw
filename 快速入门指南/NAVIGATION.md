# 📂 OpenClaw 项目导航

快速找到你需要的文件和信息。

---

## 🚀 我是新手，从哪里开始？

**推荐路径**：
1. 📖 [START_HERE.md](START_HERE.md) - 3分钟快速入门
2. 📖 [INDEX.md](INDEX.md) - 5分钟了解全貌
3. 💻 运行 `./scripts/install.sh` 安装
4. 💻 运行 `python3 examples/basic_usage.py` 看示例

---

## 📚 我想深入学习

### 完整文档
- [README.md](README.md) - 完整使用指南（15分钟）
- [HEARTBEAT.md](HEARTBEAT.md) - 安全约束详解
- [API_STRATEGY.md](API_STRATEGY.md) - API调用策略详解

### 项目理解
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 项目结构和数据流
- [SUMMARY.md](SUMMARY.md) - 项目总结
- [CHANGELOG.md](CHANGELOG.md) - 版本历史

---

## 🔍 我需要快速查询

- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速参考卡
  - 常用命令
  - 配额一览
  - 安全等级
  - 故障排查

---

## 💻 我想看代码示例

### 示例代码（按难度）
1. [examples/basic_usage.py](examples/basic_usage.py) - 基础使用（8个示例）
2. [examples/batch_processing.py](examples/batch_processing.py) - 批处理优化（7个示例）
3. [examples/custom_rules.py](examples/custom_rules.py) - 自定义规则（8个示例）

### 核心脚本
- [scripts/quota_monitor.py](scripts/quota_monitor.py) - 配额监控实现
- [scripts/smart_router.py](scripts/smart_router.py) - 智能路由实现

---

## ⚙️ 我想配置系统

### 配置文件
- [config/api_config.yaml](config/api_config.yaml) - API完整配置
  - 模型配置和配额
  - 路由策略
  - 批处理设置
  - 缓存策略

### 安全配置
- [HEARTBEAT.md](HEARTBEAT.md) - 安全约束配置
  - 禁止操作列表
  - 需要确认的操作
  - 自动允许的操作
  - 自定义规则区域

---

## 🛠️ 我想使用工具

### 命令行工具
```bash
# 主管理工具
./scripts/openclaw.sh [命令]

可用命令：
  init      - 初始化环境
  status    - 查看配额状态
  report    - 生成每日报告
  test      - 测试智能路由
  cleanup   - 清理旧数据
  check     - 环境检查
  help      - 显示帮助
```

### Python工具
```bash
# 配额监控
python3 scripts/quota_monitor.py --status
python3 scripts/quota_monitor.py --report

# 智能路由测试
python3 scripts/smart_router.py
```

---

## 🔒 我关心安全

### 安全相关文档
- [HEARTBEAT.md](HEARTBEAT.md) - 完整的安全约束定义
  - 三级安全体系
  - 智能数据识别
  - 应急响应流程

### 安全特性
- 🔴 绝对禁止：删除重要数据、未授权通信、系统权限、财务操作
- 🟡 需要确认：大规模修改、发送消息、安装软件、系统配置
- 🟢 自动允许：只读操作、临时文件、本地通知、数据分类

---

## 📊 我想优化性能

### 优化策略文档
- [API_STRATEGY.md](API_STRATEGY.md) - 完整的优化策略
  - 批处理优化（节省40-60%）
  - 缓存策略（减少20-40%）
  - 本地处理（节省50-70%）
  - 综合效果（节省60-80%）

### 优化示例
- [examples/batch_processing.py](examples/batch_processing.py) - 批处理实战

---

## 🐛 我遇到问题

### 故障排查
1. 查看 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) 的故障排查部分
2. 运行 `./scripts/openclaw.sh check` 检查环境
3. 查看日志：`tail -f ~/.openclaw/logs/api_usage.log`
4. 查看 [README.md](README.md) 的故障排查章节

### 常见问题
- **配额耗尽**：查看 status，等待重置（每天UTC 00:00）
- **API密钥问题**：检查 `echo $Claude_API_KEY`
- **路由异常**：运行 `python3 scripts/smart_router.py` 测试

---

## 📋 我想了解项目全貌

### 项目报告
- [FINAL_REPORT.md](FINAL_REPORT.md) - 完整的项目完成报告
  - 交付清单
  - 功能实现
  - 性能指标
  - 技术亮点

### 项目总结
- [SUMMARY.md](SUMMARY.md) - 项目总结
  - 核心功能
  - 系统架构
  - 使用场景
  - 未来规划

---

## 🎓 按学习阶段导航

### 第1天（30分钟）- 入门
1. ✅ [START_HERE.md](START_HERE.md)
2. ✅ [INDEX.md](INDEX.md)
3. ✅ 运行 `./scripts/install.sh`
4. ✅ 运行 `examples/basic_usage.py`

### 第2天（1小时）- 进阶
1. ✅ [README.md](README.md)
2. ✅ [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. ✅ 运行 `examples/batch_processing.py`
4. ✅ 尝试集成到项目

### 第3天（1小时）- 高级
1. ✅ [HEARTBEAT.md](HEARTBEAT.md)
2. ✅ [API_STRATEGY.md](API_STRATEGY.md)
3. ✅ 运行 `examples/custom_rules.py`
4. ✅ 自定义配置和规则

---

## 📁 按文件类型导航

### 📖 文档文件（16个）
| 文件 | 用途 | 阅读时间 |
|------|------|---------|
| START_HERE.md | 快速入门 | 3分钟 |
| INDEX.md | 项目概览 | 5分钟 |
| README.md | 完整指南 | 15分钟 |
| QUICK_REFERENCE.md | 快速参考 | 随时查阅 |
| HEARTBEAT.md | 安全约束 | 10分钟 |
| API_STRATEGY.md | API策略 | 15分钟 |
| PROJECT_STRUCTURE.md | 项目结构 | 5分钟 |
| SUMMARY.md | 项目总结 | 10分钟 |
| CHANGELOG.md | 更新日志 | 5分钟 |
| FINAL_REPORT.md | 完成报告 | 15分钟 |
| NAVIGATION.md | 项目导航 | 本文件 |
| LICENSE | MIT许可 | 1分钟 |

### 🛠️ 脚本文件（4个）
| 文件 | 功能 | 行数 |
|------|------|------|
| scripts/install.sh | 一键安装 | 291 |
| scripts/openclaw.sh | 主管理工具 | 301 |
| scripts/quota_monitor.py | 配额监控 | 466 |
| scripts/smart_router.py | 智能路由 | 314 |

### 📚 示例文件（3个）
| 文件 | 示例数 | 行数 |
|------|--------|------|
| examples/basic_usage.py | 8个 | 267 |
| examples/batch_processing.py | 7个 | 392 |
| examples/custom_rules.py | 8个 | 517 |

### ⚙️ 配置文件（1个）
| 文件 | 说明 | 行数 |
|------|------|------|
| config/api_config.yaml | API完整配置 | 424 |

---

## 🎯 按使用场景导航

### 场景1：日常办公助手
- 阅读：[README.md](README.md) - 使用场景章节
- 配置：[config/api_config.yaml](config/api_config.yaml) - 调整配额
- 示例：[examples/basic_usage.py](examples/basic_usage.py)

### 场景2：开发辅助工具
- 阅读：[API_STRATEGY.md](API_STRATEGY.md) - 开发场景
- 配置：[HEARTBEAT.md](HEARTBEAT.md) - 代码审查规则
- 示例：[examples/batch_processing.py](examples/batch_processing.py)

### 场景3：内容创作助手
- 阅读：[README.md](README.md) - 内容创作场景
- 配置：[config/api_config.yaml](config/api_config.yaml) - 路由策略
- 示例：[examples/custom_rules.py](examples/custom_rules.py)

---

## 🔗 快速链接

### 最常用的5个文件
1. [START_HERE.md](START_HERE.md) - 从这里开始
2. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 日常查询
3. [README.md](README.md) - 完整指南
4. [config/api_config.yaml](config/api_config.yaml) - 配置调整
5. [examples/basic_usage.py](examples/basic_usage.py) - 代码示例

### 命令速查
```bash
# 安装
./scripts/install.sh

# 日常使用
./scripts/openclaw.sh status
./scripts/openclaw.sh report

# 示例
python3 examples/basic_usage.py

# 帮助
./scripts/openclaw.sh help
```

---

## 📞 需要帮助？

1. **查看文档**：先查阅相关文档
2. **运行检查**：`./scripts/openclaw.sh check`
3. **查看日志**：`tail -f ~/.openclaw/logs/api_usage.log`
4. **查看帮助**：`./scripts/openclaw.sh help`

---

**提示**：建议将本文件加入书签，方便随时查找所需内容。

🦞 **OpenClaw** - 解放双手，但绝不越过安全底线
