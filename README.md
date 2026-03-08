# OpenClaw 快速入门 🚀

## 核心文档（每次执行前必读）
- [SKILLS.md](SKILLS.md) - 技能树与软件使用细则
- [HEARTBEAT.md](HEARTBEAT.md) - 安全控制与权限底线
- [AGENTS.md](AGENTS.md) - 智能体运行标准
- [IDENTITY.md](IDENTITY.md) - 员工档案与职责
- [TOOLS.md](TOOLS.md) - 工具权限汇总
- [MEMORY.md](MEMORY.md) - 长期记忆学习
- [SOUL.md](SOUL.md) - 灵魂底色

## 快速开始（3分钟）
1. 查看技能列表：`openclaw skills check`
2. 启动服务（稳定版）：
   - 一次性固化：`npm install -g node@22 && openclaw gateway install --force`
   - 日常启动（推荐唯一入口）：`bash scripts/gateway_stable_start.sh`
   - 或兼容方式：`openclaw gateway restart && openclaw gateway status`
3. 测试对话：发送消息到配置的频道

### 网关查看地址
- Dashboard：`http://127.0.0.1:18789/`

### 聊天框 `-11` 快速恢复
```bash
bash scripts/gateway_stable_start.sh
# 若仍异常（手动兜底）：
openclaw gateway install --force && openclaw gateway restart
```
通过标准：脚本输出 `可安全新建会话`（内部已做连续探针稳定性检查）
注意：点刷新后先跑一次稳定脚本，再开 `new session`，避免在 Warm-up 窗口触发 `-11 read`

### 24x7 待命守护
```bash
bash scripts/install_openclaw_guardian.sh
# 或统一入口：
bash scripts/openclaw.sh guard install
```
这会做 4 件事：
- 给已安装的 OpenClaw runtime 打补丁，让 WhatsApp idle/watchdog 阈值可配置
- 把 `agents.defaults.heartbeat.every` 调整为 `0m`，避免周期性触发 `-11`
- 将 WhatsApp 待机阈值调整到 6 小时，避免 30 分钟静默就误判断线
- 安装 `ai.openclaw.guardian` LaunchAgent，每分钟巡检一次，命中 `-11` / 异常关闭时自动自愈

2026-03-08 补充：
- 补丁改为按内容自动发现（覆盖 `daemon-cli` / `plugin-sdk`），避免版本文件名漂移导致补丁漏打。
- 收到 `Unknown system error -11, read` 时，入站处理会自动重试 1 次（250ms），降低偶发读错误对回复链路的影响。

查看守护状态：
```bash
python3 scripts/openclaw_guardian.py status
```

---

## 🔐 安全加固（2026-03-07，基于 openclaw-security 落地）

### 一键巡检
```bash
bash scripts/security_baseline.sh check
# 或
bash scripts/openclaw.sh security
```

### 权限收敛（建议首次执行一次）
```bash
bash scripts/security_baseline.sh fix
```

### 已落地的低侵入安全增强
- 移除 `scripts/activate_agent_tools.sh` 中的 `eval` 直接执行路径（保留兼容 `--run`）。
- `scripts/xiaohongshu_send_setup.sh` 增加 `umask 077`、关键目录/文件权限收敛、端口与布尔参数校验。
- `小红书笔记技能包/scripts/render_xhs_v2.js` 将 YAML 解析收敛到 `JSON_SCHEMA`。
- `scripts/wechat_draft.py` 不再输出 token 片段，避免凭证侧漏。
- `scripts/doctor.sh` 新增安全基线检查步骤，统一纳入体检流程。

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
openclaw gateway restart
openclaw gateway status
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

### 水产市场（手动点名调用）
```bash
# 查看已安装资产
openclawmp list

# 查看具体资产（名称含空格时必须加引号）
openclawmp info "experience/@u-a25e114956065150/Multi Source Tech News Digest"

# 直接让 agent 按已安装资产产出内容
openclaw agent --message "按 Multi Source Tech News Digest + Auto-Redbook-Skills 产出过去24小时科技摘要、3个选题、1篇成稿"
```

## 小红书增长官技能（已验证）
```bash
# 1. 内容创作 → 生成Markdown文件
# 2. 渲染卡片
python3 小红书笔记技能包/scripts/render_xhs.py content.md -t playful-geometric -m separator -o output/

# 3. 发布验证
bash scripts/xiaohongshu_send_setup.sh start --port 18060 --headless true
python3 scripts/xiaohongshu_send.py check-login --base-url http://127.0.0.1:18060
python3 scripts/xiaohongshu_send.py validate --payload payload.json
python3 scripts/xiaohongshu_send.py publish --dry-run --payload payload.json --base-url http://127.0.0.1:18060
```

---

## 🔗 相关文档链接（重要！）

### 核心文档（你每次执行项目前必须核心阅读的文档）
- [核心养虾文件Token优化指南](openclaw-workspace/核心养虾文件Token优化指南.md) - 核心token优化指南
- [API_STRATEGY.md](openclaw-workspace/部署与部分app配置/API_STRATEGY.md) - API策略与效能优化
- [SKILLS.md](openclaw-workspace/SKILLS.md)- 你的各个技能树，解放双手的效率利器，对应各个软件的使用细则提示，请详细遵循
- [HEARTBEAT.md](openclaw-workspace/HEARTBEAT.md)- 你的风险与安全控制文档，代表权限底线，必须仔细遵循不犯错
- [AGENTS.md](openclaw-workspace/AGENTS.md)- 你的智能体运行合约与操作标准程序
- [IDENTITY.md](openclaw-workspace/IDENTITY.md)- 你的员工档案，请记住你的职责，高效完成任务不犯错
- [TOOLS.md](openclaw-workspace/TOOLS.md)- 你有的权限各个工具的汇总
- [MEMORY.md](openclaw-workspace/MEMORY.md)- 你的长期记忆学习文件，每天不断进步，学无止境
- [SOUL.md](openclaw-workspace/SOUL.md)- 你的人类形态灵魂底色，不忘初心，方得始终


### 详细文档（你每次执行项目前必须核心阅读的文档）
- [README.md](../README.md) - 完整使用指南
- [项目完成总结](../项目完成总结/) - 项目总结和结构以及目前完成情况与流程
- [部署与部分app配置](../部署与部分app配置/) - 工具配置说明
- [Token优化指南](openclaw-workspace/Token优化指南.md) - 核心文件的token优化，帮我省钱

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

## 💡 新人使用技巧

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

### 目标
- 三平台抓取验证：小红书 / 公众号 / X（各6条）
- 结构化总结写入 Obsidian Vault
- 生成并推送 3 条小红书草稿态、3 条公众号草稿

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
- MCP服务在 `~/xhs_workspace`（无中文路径，避免崩溃）
- Cookie从浏览器导入（长期有效，无需扫码）
- 中文路径自动转换（发布时处理）
- 默认"仅自己可见"（手动审核后公开）

### 小红书快速自检（30秒）
```bash
bash scripts/xiaohongshu_send_setup.sh status --port 18060
python3 scripts/xiaohongshu_send.py check-login --base-url http://127.0.0.1:18060
```

---



**版本**：1.0.1
**更新日期**：2026-03-03

🦞 **OpenClaw** - 解放双手，但绝不越过安全底线
