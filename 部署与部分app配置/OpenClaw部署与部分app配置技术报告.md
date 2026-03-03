# OpenClaw 部署技术报告

## 项目概述

本报告记录了 OpenClaw 多渠道 AI 网关的完整部署流程，包括 Telegram 机器人配置、Gemini 模型集成以及 Gateway 服务的安装与配置。

**部署日期：** 2026-02-28
**系统环境：** macOS 26.3 (arm64)
**OpenClaw 版本：** 2026.2.26

---

## 一、系统环境准备

### 1.1 环境检查

首先验证系统已安装 Node.js 和 npm：

```bash
node --version  # v25.4.0
npm --version   # 11.7.0
```

### 1.2 配置 npm 全局安装目录

为避免权限问题，配置 npm 使用用户目录作为全局安装位置：

```bash
mkdir -p ~/.npm-global
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH
```

**建议：** 将 `export PATH=~/.npm-global/bin:$PATH` 添加到 `~/.zshrc` 或 `~/.bash_profile` 中以永久生效。

---

## 二、OpenClaw 安装

### 2.1 全局安装 OpenClaw

```bash
npm install -g openclaw
```

### 2.2 验证安装

```bash
openclaw --version  # 2026.2.26
```

---

## 三、基础配置

### 3.1 初始化配置

运行 setup 命令初始化配置文件和工作区：

```bash
openclaw setup
```

**生成的文件：**
- 配置文件：`~/.openclaw/openclaw.json`
- 工作区：`~/Desktop/家养小龙虾🦞/openclaw-workspace`
- 会话目录：`~/.openclaw/agents/main/sessions`

---

## 四、Telegram 频道配置

### 4.1 启用 Telegram 插件

```bash
openclaw plugins enable telegram
```

### 4.2 添加 Telegram Bot

使用你的 Telegram Bot Token 配置频道：

```bash
openclaw channels add --channel telegram --token "TELEGRAM_BOT_TOKEN_REDACTED"
```

**Bot Token：** `TELEGRAM_BOT_TOKEN_REDACTED`

### 4.3 验证频道配置

```bash
openclaw channels list
```

---


## 六、Gateway 服务部署

### 6.1 停止旧服务（如果存在）

```bash
openclaw gateway stop
```

### 6.2 安装 Gateway 服务

```bash
openclaw gateway install
```

**服务类型：** macOS LaunchAgent
**服务文件：** `~/Library/LaunchAgents/ai.openclaw.gateway.plist`
**日志位置：**
- 标准输出：`/Users/a8/.openclaw/logs/gateway.log`
- 错误输出：`/Users/a8/.openclaw/logs/gateway.err.log`
- 文件日志：`/tmp/openclaw/openclaw-2026-02-28.log`

### 6.3 验证服务状态

```bash
openclaw gateway status
```

**预期输出：**
- Runtime: running (pid 48361, state active)
- RPC probe: ok
- Listening: 127.0.0.1:18789

---

## 七、Telegram 配对

### 7.1 触发配对请求

在 Telegram 中找到你的 Bot，发送任意消息。Bot 会返回一个配对码。

**示例配对码：** `BFKXK5VE`

### 7.2 查看配对请求

```bash
openclaw pairing list
```

### 7.3 批准配对

```bash
openclaw pairing approve telegram BFKXK5VE
```

**输出示例：**
```
Approved telegram sender 8334640972.
```

---

## 八、Dashboard 访问配置

### 8.1 获取 Dashboard URL

```bash
openclaw dashboard
```

### 8.2 访问地址

**完整 URL（包含 token）：**
```
http://127.0.0.1:18789/#token=GATEWAY_TOKEN_REDACTED
```

**基础 URL：** `http://127.0.0.1:18789/`
**Gateway Token：** `GATEWAY_TOKEN_REDACTED`

### 8.3 手动配置 Token（如需要）

如果访问基础 URL 显示 "gateway token missing"，需要：
1. 打开 Dashboard 设置（Settings）
2. 找到 "Gateway Token" 或 "Control UI settings"
3. 粘贴 token：`GATEWAY_TOKEN_REDACTED`
4. 保存

---

## 九、系统状态检查

### 9.1 查看完整状态

```bash
openclaw status
```

### 9.2 查看实时日志

```bash
openclaw logs --follow --limit 50
```

### 9.3 安全审计

```bash
openclaw security audit
```

**建议修复：**
```bash
chmod 700 /Users/a8/.openclaw
```

---

## 十、重要配置文件

### 10.1 主配置文件

**路径：** `~/.openclaw/openclaw.json`

**关键配置项：**
```json
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "GATEWAY_TOKEN_REDACTED"
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "dmPolicy": "pairing",
      "botToken": "TELEGRAM_BOT_TOKEN_REDACTED",
      "groupPolicy": "allowlist",
      "streaming": "off"
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "google/gemini-2.5-flash"
      },
      "workspace": "/Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace"
    }
  }
}
```

---

## 十一、常用命令速查

### 服务管理
```bash
# 启动服务
openclaw gateway start

# 停止服务
openclaw gateway stop

# 重启服务
openclaw gateway restart

# 查看状态
openclaw gateway status
```

### 频道管理
```bash
# 列出频道
openclaw channels list

# 查看频道状态
openclaw channels status

# 添加频道
openclaw channels add --channel <type> --token <token>
```

### 配对管理
```bash
# 查看配对请求
openclaw pairing list

# 批准配对
openclaw pairing approve <channel> <code>
```

### 模型管理
```bash
# 列出模型
openclaw models list

# 设置默认模型
openclaw models set <model-id>

# 查看模型状态
openclaw models status
```

### 日志查看
```bash
# 实时日志
openclaw logs --follow

# 查看最近日志
openclaw logs --limit 100
```

---

## 十二、重要 URL 汇总

| 名称 | URL | 说明 |
|------|-----|------|
| Dashboard（带 token） | http://127.0.0.1:18789/#token=GATEWAY_TOKEN_REDACTED | 完整访问地址 |
| Dashboard（基础） | http://127.0.0.1:18789/ | 需手动输入 token |
| Gateway WebSocket | ws://127.0.0.1:18789 | WebSocket 连接地址 |
| 官方文档 | https://docs.openclaw.ai/ | OpenClaw 官方文档 |
| CLI 文档 | https://docs.openclaw.ai/cli | 命令行工具文档 |
| 故障排查 | https://docs.openclaw.ai/troubleshooting | 问题排查指南 |
| 安全指南 | https://docs.openclaw.ai/gateway/security | 安全配置指南 |
| FAQ | https://docs.openclaw.ai/faq | 常见问题 |

---

## 十三、关键信息汇总

### 13.1 认证信息

| 项目 | 值 |
|------|-----|
| Gateway Token | GATEWAY_TOKEN_REDACTED |
| Telegram Bot Token | TELEGRAM_BOT_TOKEN_REDACTED |
| Google API Key | GOOGLE_API_KEY_REDACTED |
| 已配对用户 ID | 8334640972 |

### 13.2 服务信息

| 项目 | 值 |
|------|-----|
| Gateway 端口 | 18789 |
| 绑定地址 | 127.0.0.1 (loopback) |
| 服务类型 | LaunchAgent |
| 进程 ID | 48361 |
| 默认模型 | google/gemini-2.5-flash |
| 上下文窗口 | 1024k tokens |

### 13.3 目录结构

```
~/.openclaw/
├── openclaw.json              # 主配置文件
├── agents/                    # 代理配置
│   └── main/
│       └── sessions/          # 会话数据
├── logs/                      # 日志文件
│   ├── gateway.log           # Gateway 标准输出
│   └── gateway.err.log       # Gateway 错误输出
├── devices/                   # 设备配对信息
├── memory/                    # 记忆存储
└── identity/                  # 身份认证
    ├── device.json
    └── device-auth.json

~/Desktop/家养小龙虾🦞/
└── openclaw-workspace/        # 工作区目录
```

---

## 十四、故障排查

### 14.1 Gateway 无法启动

**症状：** 端口已被占用

**解决方案：**
```bash
# 停止现有服务
openclaw gateway stop

# 或强制停止
launchctl bootout gui/$UID/ai.openclaw.gateway

# 重新安装
openclaw gateway install
```

### 14.2 Dashboard 无法连接

**症状：** "gateway token missing"

**解决方案：**
使用完整 URL 访问：
```
http://127.0.0.1:18789/#token=GATEWAY_TOKEN_REDACTED
```

### 14.3 Telegram Bot 无响应

**检查步骤：**
```bash
# 1. 检查服务状态
openclaw status

# 2. 检查频道状态
openclaw channels status

# 3. 查看日志
openclaw logs --follow

# 4. 验证配对
openclaw pairing list
```

### 14.4 模型调用失败

**检查步骤：**
```bash
# 1. 验证模型配置
openclaw models list

# 2. 检查 API Key
cat ~/.openclaw/openclaw.json | grep -A 5 "google:default"

# 3. 测试模型连接
openclaw agent --message "test" --deliver
```

---

## 十五、安全建议

### 15.1 权限设置

```bash
# 限制配置目录权限
chmod 700 ~/.openclaw

# 限制配置文件权限
chmod 600 ~/.openclaw/openclaw.json
```

### 15.2 配对策略

当前配置使用 `dmPolicy: "pairing"`，这意味着：
- 新用户必须先发送消息获取配对码
- 管理员需要手动批准配对
- 只有已配对用户可以与 Bot 交互

### 15.3 定期审计

```bash
# 运行安全审计
openclaw security audit --deep

# 自动修复问题
openclaw security audit --fix
```

---

## 十六、维护与更新

### 16.1 更新 OpenClaw

```bash
# 检查更新
openclaw update status

# 更新到最新版本
npm update -g openclaw

# 重启服务
openclaw gateway restart
```

### 16.2 备份配置

```bash
# 备份配置文件
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup

# 备份整个配置目录
tar -czf openclaw-backup-$(date +%Y%m%d).tar.gz ~/.openclaw/
```

### 16.3 日志清理

```bash
# 查看日志大小
du -sh ~/.openclaw/logs/
du -sh /tmp/openclaw/

# 清理旧日志（手动）
rm -f /tmp/openclaw/openclaw-*.log
```

---

## 十七、测试验证

### 17.1 Telegram 功能测试

1. 在 Telegram 中找到你的 Bot
2. 发送测试消息："你好"
3. 验证 Bot 使用 Gemini 模型回复

### 17.2 Dashboard 功能测试

1. 访问 Dashboard URL
2. 在聊天界面发送消息
3. 验证实时响应

### 17.3 系统健康检查

```bash
# 完整状态检查
openclaw status --deep

# 频道探测
openclaw channels status --probe

# Gateway 探测
openclaw gateway probe
```

---

## 十八、部署总结

### 18.1 部署成果

✅ OpenClaw 2026.2.26 已成功安装
✅ Gemini 2.5 Flash 模型已配置并可用
✅ Telegram Bot 已配置并完成配对
✅ Gateway 服务运行正常（pid 48361）
✅ Dashboard 可正常访问
✅ 服务已设置为开机自启动

### 18.2 核心流程回顾

1. **环境准备** → 配置 npm 全局目录
2. **安装程序** → npm 全局安装 openclaw
3. **基础配置** → openclaw setup 初始化
4. **启用插件** → 启用 telegram 插件
5. **配置频道** → 添加 Telegram Bot token
6. **配置模型** → 设置 Claude API key（Gemini 兼容）
7. **启动服务** → 安装并启动 Gateway
8. **完成配对** → 批准 Telegram 配对请求
9. **访问 Dashboard** → 使用完整 URL 访问

### 18.3 关键成功因素

- 使用用户级 npm 全局安装避免权限问题
- 通过 setup 命令快速初始化配置
- 使用非交互式命令完成配置
- 正确配置 LaunchAgent 实现自启动
- 使用完整 URL（含 token）访问 Dashboard

---

## 十九、后续扩展建议

### 19.1 添加更多频道

```bash
# 启用其他频道插件
openclaw plugins enable discord
openclaw plugins enable slack
openclaw plugins enable whatsapp

# 配置频道
openclaw channels add --channel discord --token <token>
```

### 19.2 配置更多模型

```bash
# 添加 Anthropic Claude
openclaw models auth paste-token --provider anthropic --profile-id anthropic:manual

# 设置模型别名
openclaw models aliases set claude anthropic/claude-sonnet-4-5
```

### 19.3 启用技能（Skills）

```bash
# 查看可用技能
openclaw skills list

# 启用特定技能
openclaw plugins enable <skill-name>
```

---

## 二十、联系与支持

### 20.1 官方资源

- **GitHub 仓库：** https://github.com/openclaw/openclaw
- **官方文档：** https://docs.openclaw.ai/
- **问题反馈：** https://github.com/openclaw/openclaw/issues

### 20.2 社区支持

- 查看 FAQ：https://docs.openclaw.ai/faq
- 故障排查指南：https://docs.openclaw.ai/troubleshooting
- 安全最佳实践：https://docs.openclaw.ai/gateway/security

---

**报告生成时间：** 2026-02-28
**报告版本：** 1.0
**部署状态：** ✅ 成功
