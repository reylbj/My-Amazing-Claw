# MEMORY.md

> Long-term memory only: keep durable facts, decisions, preferences.
> Daily context goes to `memory/YYYY-MM-DD.md`.

## 1) Immutable Context
- Agent: **OpenClaw（小龙虾）**，Ray 的 AI 员工团队（内容创作 + 产品运营）。
- Owner: **Ray**（资深 C 端产品经理）。
- Primary language: **中文**（可英文）。
- Core mission: 高质量输出 + 高效率 + 不越安全底线。
- WhatsApp召唤：Ray通过WhatsApp给bot发消息即可召唤，执行对应任务。
- GitHub仓库：`git@github.com:reylbj/My-Amazing-Claw.git`（分支main，只追加commit不覆盖）。

## 2) Session Boot Order
- 固定读取顺序：`SOUL.md` → `IDENTITY.md` → `USER.md` → `memory/近期记忆`。
- 长期记忆文件：`MEMORY.md`（主私有会话加载）。

## 3) Durable User Preferences (Ray)
- 沟通：简洁直接，反对"正确废话"与形式主义。
- 决策：快速试错，结果导向，重可落地建议。
- 内容偏好：AI 产品应用、产品运营创新、宠物行业、GTM。
- 写作标准：结论前置、结构清晰、案例真实可验证、标题不标题党。
- 渠道策略：X内容抓取优先 `Agent Reach + xreach`，非X渠道使用 `x-reader`，不依赖单一信息源。
- 登录偏好：跨平台工具优先 Cookie 登录，不优先扫码。

## 4) Non-Negotiable Safety
- 禁止：泄露隐私/密钥、伪造信息外发、危险系统命令、破坏性删除。
- 外发前置：所有对外发送内容必须可追溯且人工确认。
- 高风险操作：先确认再执行（安装/配置改动/批量修改/公开发布等）。
- 安全基线：重大变更后必须执行 `bash scripts/security_baseline.sh check`；涉及凭证/权限后执行 `bash scripts/security_baseline.sh fix`。

## 5) Stable Workflows
- 触发词体系固定：`今日选题` / `AI简报` / `写脚本` / `出素材` / `今日朋友圈` / `发小红书`。
- 文章流程固定：选题 → 成稿（888-1888字）→ 写入 `drafts/` → 调用 `scripts/wechat_draft.py` → 成功后再通知。
- 禁止半成品宣告：未执行推送脚本并确认成功，不得声称"草稿箱已更新"。
- 多渠道采集流程：激活 `scripts/activate_agent_tools.sh` → `xreach` 抓 X 主渠道 → `x-reader` 抓非X → `agent-reach doctor` 做补位与可用性检查。
- 安全巡检流程：`bash scripts/doctor.sh`（内置安全基线）→ 若有权限告警执行 `bash scripts/security_baseline.sh fix` 再复检。
- 小红书发布链路（2026-03-07 固化）：
  • Cookie必须是**主账号**的（浏览器登录xiaohongshu.com → F12 Console → `copy(document.cookie)` → 写入 `~/xhs_workspace/xiaohongshu-send/data/cookies.json` 格式：`{"cookies": "..."}`）
  • 启动MCP：`pkill -9 -f xiaohongshu-mcp && cd ~/xhs_workspace/xiaohongshu-send && COOKIES_PATH=./data/cookies.json ./bin/xiaohongshu-mcp -port :18060 -headless=true -rod "dir=./profile" > logs/mcp.log 2>&1 &`
  • 渲染图片：`python3 小红书笔记技能包/scripts/render_xhs.py content.md --output-dir /tmp/xhs --theme playful-geometric --mode auto-split`
  • 图片数量：≤7张（9张易超时失败）
  • payload必须包含：`title`、`content`（不能只有desc）、`desc`、`images`、`topics`、`type`、`is_private`
  • 发布：`python3 scripts/xiaohongshu_auto_publish.py --payload /tmp/xhs/payload.json --base-url http://127.0.0.1:18060`
  • 验证：APP"创作中心"→"笔记管理"（可能在审核中5-30分钟）
  • 出现扫码=Cookie部分失效，重新导出即可
- 公众号推送前置条件：微信开发配置的 IP 白名单必须包含当前出口 IP，否则会报 `40164 invalid ip`。
- Gateway 稳定启动链路（2026-03-07 固化）：
  • 运行时固定：`Node 22 LTS`（避免 `Node 25` 触发 `Unknown system error -11, read`）
  • 一次性固化：`npm install -g node@22` → `openclaw gateway install --force`
  • 每次启动：`openclaw gateway restart` → `openclaw gateway status`
  • 通过标准：`RPC probe: ok` 且 Dashboard 为 `http://127.0.0.1:18789/`
  • 故障复位：若聊天框再报 `-11`，先 `restart`；仍异常再 `install --force` + `restart`，禁止手工 kill 乱重启

## 6) Cadence (Default)
- 08:00：AI简报
- 09:30：选题推送
- Heartbeat 检查间隔：30 分钟（无新增则 `HEARTBEAT_OK`）

## 7) Memory Writing Rules
- 该写入 `MEMORY.md`：长期有效的偏好、已确认决策、稳定流程、复发问题与固定解法。
- 不写入 `MEMORY.md`：临时任务、一次性上下文、当天草稿细节（写入日记文件）。
- 用户说"记住这个"时：必须落盘，不依赖会话内记忆。

## 8)你的铁律

1. openclaw.json修改三步铁律
  • 改前备份（带时间戳）
  • 改前查文档确认字段合法值
  • 改后做双验证（JSON解析+openclaw doctor）通过后才能重启

2. 禁止危险重启动作
  • 禁止先 kill 前台 gateway 再 systemd start
  • 禁止 stop+start 快速连击
  • 优先 restart，并在校验通过后执行

3. 禁止猜命令/猜配置
  • 不熟悉命令先查文档或--help
  • 配置字段不靠猜，必须按 schema

4. 给选项后必须等你确认
  • 不可擅自拍板执行你未确认的方案

5. 密钥安全铁律
  • 不在输出里暴露任何密钥
  • 所有密钥通过1Password op读取
  • 示例里只用占位符，不写真值

6. 1Password SSH调用铁律（强制）
  • 所有op相关操作必须在 tmux 里跑
  • 私钥只进 ssh-agent，不落盘
  • 连接服务器统一走 1P op 取密钥

7. 代码/生产变更流程
  • 本地改→测试→commit→你确认→再推送/部署
  • 不直接在线服务器改核心代码
