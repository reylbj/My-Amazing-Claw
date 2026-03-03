# 快速入门指南 🚀

## 📚 文档导航

本文件夹包含OpenClaw的快速入门文档，帮助你在最短时间内上手使用。

---

## 📖 文档列表

### 1. [START_HERE.md](START_HERE.md) - 3分钟快速开始
**适合人群**：完全新手，第一次使用OpenClaw

**内容概览**：
- 最简安装步骤
- 基础配置
- 第一次对话
- 常见问题

**阅读时间**：3分钟

---

### 2. [INDEX.md](INDEX.md) - 5分钟项目概览
**适合人群**：想快速了解OpenClaw全貌

**内容概览**：
- 项目介绍
- 核心功能
- 文档索引
- 快速链接

**阅读时间**：5分钟

---

### 3. [NAVIGATION.md](NAVIGATION.md) - 项目导航
**适合人群**：需要快速找到特定文档

**内容概览**：
- 按需求分类的文档导航
- 我是新手，从哪里开始？
- 我想深入学习
- 我需要快速查询
- 我想看代码示例
- 我想配置系统
- 我想使用工具

**使用场景**：当你不知道该看哪个文档时

---

### 4. [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - 快速参考卡
**适合人群**：已经熟悉OpenClaw，需要快速查询

**内容概览**：
- 常用命令速查
- 配额一览表
- 安全等级速查
- 故障排查清单
- 快捷键和技巧

**使用场景**：日常使用时的速查手册

---


## 📋 快速命令参考

### 安装
```bash
npm install -g openclaw
openclaw setup
```

### 配置
```bash
openclaw configure
```

### 启动服务
```bash
openclaw gateway start
```

### 查看状态
```bash
openclaw status
openclaw gateway status
```

### 配置频道
```bash
# Telegram
openclaw channels add --channel telegram --token "YOUR_TOKEN"

# WhatsApp
openclaw configure  # 选择 channels -> WhatsApp
```

---

## 🔗 相关文档链接（重要！）

### 核心文档（每次执行前必须核心阅读的文档）
- [核心养虾文件Token优化指南](openclaw-workspace/核心养虾文件Token优化指南.md) - 核心token优化指南
- [API_STRATEGY.md](openclaw-workspace/部署与部分app配置/API_STRATEGY.md) - API策略与效能优化
- [SKILLS.md](openclaw-workspace/SKILLS.md)- 你的各个技能树，解放双手的效率利器，对应各个软件的使用细则提示，请详细遵循
- [HEARTBEAT.md](openclaw-workspace/HEARTBEAT.md)- 你的风险与安全控制文档，代表权限底线，必须仔细遵循不犯错
- [AGENTS.md](openclaw-workspace/AGENTS.md)- 你的智能体运行合约与操作标准程序
- [IDENTITY.md](openclaw-workspace/IDENTITY.md)- 你的员工档案，请记住你的职责，高效完成任务不犯错
- [TOOLS.md](openclaw-workspace/TOOLS.md)- 你有权限各个工具的汇总
- [MEMORY.md](openclaw-workspace/MEMORY.md)- 你的长期记忆学习文件，每天不断进步，学无止境
- [SOUL.md](openclaw-workspace/SOUL.md)- 你的人类形态灵魂底色，不忘初心，方得始终


### 详细文档
- [README.md](../README.md) - 完整使用指南
- [项目完成总结](../项目完成总结/) - 项目总结和结构以及目前完成情况与流程
- [部署与部分app配置](../部署与部分app配置/) - 工具配置说明

---

## 🎓 学习资源

### 官方资源
- 官方文档：https://docs.openclaw.ai/
- GitHub仓库：https://github.com/openclaw/openclaw
- 问题反馈：https://github.com/openclaw/openclaw/issues

### 社区资源
- FAQ：https://docs.openclaw.ai/faq
- 故障排查：https://docs.openclaw.ai/troubleshooting
- 安全指南：https://docs.openclaw.ai/gateway/security

---

## 💡 使用技巧

### 技巧1：善用导航文档
不知道看什么？先看 [NAVIGATION.md](NAVIGATION.md)

### 技巧2：收藏快速参考
把 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) 加入书签，日常使用时快速查询

### 技巧3：循序渐进
不要一次看完所有文档，按需学习更高效

### 技巧4：实践为主
边看文档边实践，效果最好

---

## 📊 文档完成度

| 文档               | 状态 | 适合人群 | 阅读时间 |
| ------------------ | ---- | -------- | -------- |
| START_HERE.md      | ✅    | 完全新手 | 3分钟    |
| INDEX.md           | ✅    | 所有用户 | 5分钟    |
| NAVIGATION.md      | ✅    | 需要导航 | 3分钟    |
| QUICK_REFERENCE.md | ✅    | 熟练用户 | 1分钟    |

---

## 🔄 今日流程快照（2026-03-03）

### 目标
- 三平台抓取验证：小红书 / 公众号 / X（各3条）
- 结构化总结写入 Obsidian Vault
- 生成并推送 1 条小红书草稿态、1 条公众号草稿

### 标准执行顺序（精简版）
1. 预检：`agent-reach doctor` + 渠道登录态检查  
2. 抓取：X走 `agent-reach + xreach`，其余走 `x-reader`，小红书走 `xiaohongshu-mcp`  
3. 汇总：输出结构化 Markdown（含链接、互动数据、爆点）  
4. 入库：同步到 Obsidian 指定目录  
5. 发布：小红书先 `validate` + `dry-run`，再发布（可见性建议 `仅自己可见`）  
6. 公众号：`python3 scripts/wechat_draft.py --file ...` 推送草稿箱  

### 今日关键结论
- X 抓取主链路已切换：`xreach`（由 Agent Reach 路线承接），不再依赖 x-reader 抓 X  
- 小红书“已登录但不可用”的常见根因是会话隔离：`x-reader` 与 `xiaohongshu-send` 登录态不共享  
- 小红书登录已做持久化根治：统一 `COOKIES_PATH`，并把 `/tmp/cookies.json` 固定链接到工作区 cookies，避免会话漂移  
- 小红书浏览器 profile 已固定到 `xiaohongshu-send/profile`（`rod dir`），重启后优先复用同一会话  
- 公众号推送报 `40164 invalid ip` 时，先加微信后台 IP 白名单再重试  
- 先做登录态/环境预检，再抓取与发布，可显著减少卡顿与失败重跑  

### 小红书快速自检（30秒）
```bash
bash scripts/xiaohongshu_send_setup.sh status --port 18060
python3 scripts/xiaohongshu_send.py check-login --base-url http://127.0.0.1:18060
```

---



**版本**：1.0.1
**更新日期**：2026-03-03

🦞 **OpenClaw** - 解放双手，但绝不越过安全底线
