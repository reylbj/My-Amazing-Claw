# API用量操作控制手册

## 目录

本手册包含OpenClaw的API使用优化和部署相关的完整文档。

---

## 🔄 重要：配置更新后必须重启 Gateway

**关键提醒**：每当修改以下关键配置文件后，必须重启 Gateway 才能使配置生效：

### 需要重启 Gateway 的情况
- ✅ 修改 `SKILLS.md`（AI员工技能配置）
- ✅ 修改 `AGENTS.md`（Agent配置）
- ✅ 修改 `TOOLS.md`（工具配置）
- ✅ 修改 `openclaw.json`（模型配置、API配置）
- ✅ 修改 `api_config.yaml`（API策略配置）

### 重启 Gateway 命令
```bash
# 方法1：查找并重启
ps aux | grep openclaw-gateway | grep -v grep | awk '{print $2}' | xargs kill -TERM
sleep 3
openclaw gateway start

# 方法2：使用 openclaw 命令
openclaw gateway restart
```

### 验证 Gateway 是否成功重启
```bash
# 检查进程
ps aux | grep openclaw-gateway | grep -v grep

# 查看日志确认配置加载
openclaw logs | tail -20

# 验证模型配置
openclaw models list | grep -E "api123|claude"
```

### 为什么需要重启？
Gateway 在启动时会读取所有配置文件到内存中。如果不重启：
- ❌ 旧的配置仍在使用
- ❌ 新的模型配置不生效
- ❌ 字数限制等参数不更新
- ❌ AI员工仍按旧提示词工作

**最佳实践**：修改配置后立即重启 Gateway，确保配置生效。

---

## 📚 文档列表

### 1. [API_STRATEGY.md](API_STRATEGY.md)
**API调用策略详解**
-详细参考Stategy文档即可

### 2. [OpenClaw部署技术报告.md](OpenClaw部署技术报告.md)
**完整部署指南**
- 系统环境准备
- OpenClaw安装
- 基础配置
- Telegram频道配置
- Claude模型配置
- Gateway服务部署
- Dashboard访问配置
- 故障排查
- 安全建议
- 维护与更新

### 3. [Token优化指南.md](Token优化指南.md)
**降低API成本的核心策略**
- 精简系统提示词
- QMD语义搜索引擎
- Heartbeat频率控制
- 多Agent分流策略
- 实战优化案例

### 4. [GoogleDrive配置指南.md](GoogleDrive配置指南.md)
**Google Drive 云端备份配置**
- rclone 工具安装
- Google Drive API 配置
- 自动备份脚本
- 定时备份设置
- 备份恢复流程
- 故障排查

### 5. [Obsidian迁移与OpenClaw组合实战.md](Obsidian迁移与OpenClaw组合实战.md)
**Claude Code/Codex App + Obsidian 迁移与联动**
- 信息收录流转设计（插件 / 微信 / OpenClaw）
- OpenClaw 联网能力与 skills 安装清单
- Obsidian 软链接方案（`OpenClaw配置` 目录）
- 一键半自动脚本：`scripts/setup_obsidian_bridge.sh`
- 体检脚本：`scripts/doctor.sh`
- 公众号自动收录命令：`./scripts/openclaw.sh wx "<mp链接>" "<Vault路径>"`

### 6. [小红书配置指南.md](小红书配置指南.md)
**小红书图文自动发布（xiaohongshu-send）**
- 自动下载并安装官方二进制
- 登录状态检查与 cookies 复用
- MCP 服务启动、健康检查、工具连通性验证
- 发布参数校验与图文发布调用

---

## 🎯 快速导航

### 新手入门
1. 先阅读 [OpenClaw部署技术报告.md](OpenClaw部署技术报告.md) 完成部署
2. 再阅读 [API_STRATEGY.md](API_STRATEGY.md) 了解配额策略
3. 然后阅读 [GoogleDrive配置指南.md](GoogleDrive配置指南.md) 配置云端备份
4. 最后阅读 [Token优化指南.md](Token优化指南.md) 进行优化

### 已部署用户
- 需要优化成本 → [Token优化指南.md](Token优化指南.md)
- 需要调整策略 → [API_STRATEGY.md](API_STRATEGY.md)
- 需要配置备份 → [GoogleDrive配置指南.md](GoogleDrive配置指南.md)
- 需要配置小红书自动发布 → [小红书配置指南.md](小红书配置指南.md)
- 遇到问题 → [OpenClaw部署技术报告.md](OpenClaw部署技术报告.md) 的故障排查章节

---

## 💡 核心优化策略

### 第一招：优化上下文窗口
- 使用流式输出减少等待
- 限制历史对话长度
- 定期清理会话历史
- **效果**：减少30-50% Token消耗

### 第二招：精简系统提示词
- 压缩AGENTS.md到800 Token以内
- 精简SOUL.md到核心内容
- 定期清理MEMORY.md
- **效果**：从13000+ Token降到3000-5000 Token

### 第三招：上QMD
- 本地语义搜索引擎
- 只传递相关内容
- **效果**：Token消耗降低90-99%，响应速度提升5-50倍

### 第四招：控制Heartbeat频率
- 从10分钟改到30分钟
- 合并多个检查任务
- **效果**：节省75%上下文注入成本

### 第五招：多Agent分流
- 复杂任务用Opus/Sonnet
- 简单任务用Haiku/Flash
- 每个Agent独立记忆
- **效果**：避免记忆污染，提升响应速度

---


## 🔧 实施步骤

### 步骤1：部署系统
按照 [OpenClaw部署技术报告.md](OpenClaw部署技术报告.md) 完成基础部署

### 步骤2：配置策略
参考 [API_STRATEGY.md](API_STRATEGY.md) 

### 步骤3：优化Token
按照 [Token优化指南.md](Token优化指南.md) 进行系统优化

### 步骤4：监控调整
- 每日查看配额使用报告
- 根据实际情况调整策略
- 定期清理和优化

---

## 📈 预期效果

### 优化前
- 系统提示词：13000+ Token
- 每次调用成本：高
- 配额消耗：快速

### 优化后
- 系统提示词：3000-5000 Token
- 每次调用成本：降低60-80%
- 配额消耗：可持续使用
- 响应速度：提升3-5倍

---

## 🆘 获取帮助

### 常见问题
- 配额耗尽 → 检查批处理和缓存设置
- API密钥无效 → 验证环境变量
- 路由不合理 → 调整复杂度参数

### 文档索引
- 部署问题 → OpenClaw部署技术报告.md
- 策略问题 → API_STRATEGY.md
- 优化问题 → Token优化指南.md

---

**版本**：1.0.0
**更新日期**：2026-02-28
**维护者**：OpenClaw Team


🦞 **OpenClaw** - 解放双手，但绝不越过安全底线



# 配置与工具 🔧

## 📚 文档说明

本文件夹包含OpenClaw的配置文件、工具说明和引导文档。

---

## 📖 文档列表

### 1. [TOOLS.md](TOOLS.md) - 工具说明
**内容概览**：
- 可用工具列表
- 工具使用方法
- 工具配置说明
- 常用工具示例

**适合人群**：需要使用OpenClaw工具的用户

---

### 2. [BOOTSTRAP.md](BOOTSTRAP.md) - 引导配置
**内容概览**：
- 首次启动配置
- 初始化步骤
- 环境检查
- 基础设置

**适合人群**：首次安装OpenClaw的用户

---

### 3. [IDENTITY.md](IDENTITY.md) - 身份信息
**内容概览**：
- 设备身份
- 认证信息
- 配对状态
- 安全设置

**适合人群**：需要管理设备身份的用户

---

## 🛠️ 常用工具

### 命令行工具

#### openclaw.sh - 主管理工具
```bash
# 初始化环境
./scripts/openclaw.sh init

# 查看配额状态
./scripts/openclaw.sh status

# 生成每日报告
./scripts/openclaw.sh report

# 测试智能路由
./scripts/openclaw.sh test

# 清理旧数据
./scripts/openclaw.sh cleanup

# 环境检查
./scripts/openclaw.sh check
```

#### quota_monitor.py - 配额监控
```bash
# 查看当前状态
python3 scripts/quota_monitor.py --status

# 生成报告
python3 scripts/quota_monitor.py --report

# 记录请求
python3 scripts/quota_monitor.py --record flash 1500 true
```

#### smart_router.py - 智能路由
```bash
# 运行测试
python3 scripts/smart_router.py
```

---

## ⚙️ 配置文件

### 主配置文件
**位置**：`~/.openclaw/openclaw.json`

**关键配置**：
```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback"
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "YOUR_TOKEN"
    },
    "whatsapp": {
      "enabled": true
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "google/gemini-2.5-flash"
      }
    }
  }
}
```

### API配置文件
**位置**：`config/api_config.yaml`

**关键配置**：
```yaml
models:
  pro:
    quota:
      daily: 80
      emergency: 20
  flash:
    quota:
      daily: 200
      emergency: 50

routing:
  auto_routing:
    enabled: true

batch_processing:
  enabled: true
  max_wait_time: 30

caching:
  enabled: true
  backend: "file"
```

---

## 🔐 安全配置

### 权限设置
```bash
# 限制配置目录权限
chmod 700 ~/.openclaw

# 限制配置文件权限
chmod 600 ~/.openclaw/openclaw.json
```

### 配对策略
- **pairing**：需要配对（推荐）
- **open**：开放访问（不推荐）
- **allowlist**：白名单模式

---

## 📋 配置检查清单

### 基础配置
- [ ] OpenClaw已安装
- [ ] Gateway服务运行正常
- [ ] API密钥已配置
- [ ] 默认模型已设置

### 频道配置
- [ ] Telegram已配置（如需要）
- [ ] WhatsApp已配置（如需要）
- [ ] 配对已完成
- [ ] 测试消息成功

### 安全配置
- [ ] 配置文件权限正确
- [ ] 配对策略已设置
- [ ] 安全审计已运行
- [ ] 备份已创建

### 优化配置
- [ ] 批处理已启用
- [ ] 缓存已启用
- [ ] QMD已配置（如需要）
- [ ] 多Agent已配置（如需要）

---

## 🚀 快速配置命令

### 一键配置
```bash
# 运行配置向导
openclaw configure
```

### 分步配置
```bash
# 1. 初始化
openclaw setup

# 2. 配置模型
echo "YOUR_API_KEY" | openclaw models auth paste-token --provider google --profile-id google:default

# 3. 配置频道
openclaw channels add --channel telegram --token "YOUR_TOKEN"

# 4. 启动服务
openclaw gateway install
openclaw gateway start

# 5. 验证配置
openclaw status
```

---

## 🔗 相关文档

### 核心文档
- [OpenClaw核心养虾文档手册](../OpenClaw核心养虾文档手册/) - 核心四件套
- [API用量操作控制手册](../API用量操作控制手册/) - API优化和配置

### 入门文档
- [快速入门指南](../快速入门指南/) - 新手入门
- [README.md](../README.md) - 完整使用指南

### 项目文档
- [项目文档](../项目文档/) - 项目总结和结构

---

## 💡 配置技巧

### 技巧1：使用环境变量
```bash
# 设置API密钥
export Claude_API_KEY='your-key'
export TELEGRAM_BOT_TOKEN='your-token'

# 添加到shell配置
echo 'export Claude_API_KEY="your-key"' >> ~/.zshrc
```

### 技巧2：备份配置
```bash
# 备份配置文件
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup

# 备份整个配置目录
tar -czf openclaw-backup-$(date +%Y%m%d).tar.gz ~/.openclaw/
```

### 技巧3：多环境配置
```bash
# 开发环境
export OPENCLAW_ENV=development

# 生产环境
export OPENCLAW_ENV=production
```

---

## ❓ 常见问题

### Q: 配置文件在哪里？
A: 主配置文件在 `~/.openclaw/openclaw.json`

### Q: 如何重置配置？
A: 删除 `~/.openclaw/` 目录，然后运行 `openclaw setup`

### Q: 如何备份配置？
A: 复制 `~/.openclaw/` 目录到安全位置

### Q: 配置错误怎么办？
A: 运行 `openclaw security audit` 检查配置

---

## 📊 配置状态

| 配置项 | 状态 | 说明 |
|--------|------|------|
| 基础配置 | ✅ | 已完成 |
| API配置 | ✅ | 已完成 |
| 频道配置 | ⚠️ | 需要用户配置 |
| 安全配置 | ✅ | 已完成 |
| 优化配置 | ✅ | 已完成 |

---

**版本**：1.0.0
**更新日期**：2026-02-28

🦞 **OpenClaw** - 解放双手，但绝不越过安全底线
