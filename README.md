# OpenClaw Workspace

这是 Ray 的 OpenClaw 运行工作区，已经收敛成一套可直接使用的内容运营与产品协作环境。

你可以把它理解成一个已经接好常用链路的 AI 员工工作台，重点覆盖这些场景：

- `AI简报` / `今日选题` / 公众号成稿与草稿箱推送
- `小红书笔记` 图文生成与发布链路
- `闲鱼发布` 半自动运营链路
- `产品需求` / `原型设计` / `演示文稿`
- `投资复盘` / `投资周报` / `每日快检`

如果你是第一次接手这个项目，先按下面的 3 分钟流程跑通，再去看细节文档。

## 先知道这 6 件事

1. 运行时固定为 `Node 22 LTS`。
2. 工作区固定为 `~/.openclaw/workspace-runtime-real`，不要搬到 Desktop、中文路径或 emoji 路径。
3. 日常启动只推荐 `bash scripts/gateway_stable_start.sh`。
4. 禁止手工 `kill` 网关进程，禁止 `stop + start` 连击；优先 `restart`。
5. 敏感信息统一放 `.credentials`，不要写进仓库文件。
6. 长期记忆只写 `MEMORY.md`，不要再建独立记忆目录。

## 3 分钟快速上手

### 1. 一次性准备

```bash
npm install -g node@22
openclaw gateway install --force
```

### 2. 日常启动

```bash
bash scripts/gateway_stable_start.sh
```

通过标准：

- 终端里看到 `RPC probe: ok`
- Dashboard 可打开：`http://127.0.0.1:18789/`

### 3. 检查运行状态

```bash
openclaw gateway status
openclaw status
openclaw agent --agent main --message "只回OK" --json
```

通过标准：

- `openclaw gateway status` 正常
- `openclaw status` 正常
- 连跑 2 到 3 次 `openclaw agent`，都返回 `status=ok`，且不出现 fallback

### 4. 安装 24x7 守护

```bash
bash scripts/install_openclaw_guardian.sh
python3 scripts/openclaw_guardian.py status
```

这一步会做 4 件事：

- 给 OpenClaw runtime 打稳定性补丁
- 把 `heartbeat` 调整到更稳的口径
- 自动清理不兼容配置字段
- 安装 `guardian` 做周期巡检与自愈

## 核心文档怎么读

启动顺序以 [SOUL.md](SOUL.md)、[IDENTITY.md](IDENTITY.md)、[USER.md](USER.md)、[MEMORY.md](MEMORY.md) 为准。

真正上手时，建议按这个顺序看：

| 文件 | 作用 | 什么时候看 |
| --- | --- | --- |
| [SOUL.md](SOUL.md) | 风格、原则、底线 | 想知道这个系统怎么做判断时 |
| [IDENTITY.md](IDENTITY.md) | AI 员工身份与职责 | 想知道它主要能做什么时 |
| [USER.md](USER.md) | Ray 的偏好、内容风格、工作方式 | 生成内容前 |
| [MEMORY.md](MEMORY.md) | 长期有效的稳定事实、故障解法、已部署能力 | 执行前和复盘后 |
| [HEARTBEAT.md](HEARTBEAT.md) | 安全红线、哪些操作必须确认 | 动手改配置、发消息、推送前 |
| [AGENTS.md](AGENTS.md) | 运行 SOP、触发词、链路入口 | 不知道一句话该怎么触发时 |
| [SKILLS.md](SKILLS.md) | 当前有效技能路由和关键约束 | 想知道某类任务该走哪条链路时 |
| [TOOLS.md](TOOLS.md) | 本机工具、脚本入口、环境说明 | 需要执行具体命令时 |

## 新手最常用的触发词

| 你说什么 | 系统会做什么 |
| --- | --- |
| `AI简报` / `今日AI` | 输出当日 Top 5 到 10 条 AI 动态 |
| `今日选题` / `选题` | 生成 15 个公众号候选选题 |
| `回复编号` | 生成 888 到 1888 字文章并推公众号草稿箱 |
| `公众号排版` / `微信文章格式化` | 把 Markdown 转成公众号兼容 HTML |
| `小红书笔记` | 走小红书图文内容与发布链路 |
| `闲鱼发布` / `咸鱼运营` | 走闲鱼半自动发布链路 |
| `产品需求` / `原型设计` | 产出 HTML 原型、需求文档、CHANGELOG |
| `演示文稿` / `PPT转网页` | 生成零依赖 HTML 幻灯片 |
| `投资复盘` / `投资周报` / `每日快检` | 调用 `skills/ai-invest-agent/` 做投资复盘 |

## 关键 Skills 一览

| Skill | 路径 | 触发词 | 主要用途 | 入口 |
| --- | --- | --- | --- | --- |
| 小红书增长官 | `skills/小红书笔记技能包/` | `小红书笔记` / `小红书帖子` | 生成封面、卡片图、payload，并走小红书发布链路 | `README.md` / `SKILL.md` / `scripts/render_xhs.py` |
| 公众号排版工具 | `skills/wechat-article-formatter/` | `公众号排版` / `微信文章格式化` | 把 Markdown 转成公众号兼容 HTML | `SKILL.md` |
| 咸鱼运营官 | `skills/xianyu-multi-agent/` | `闲鱼发布` / `咸鱼运营` | 生成文案并走闲鱼半自动发布链路 | `README.md` / `SCRIPTS_README.md` |
| 产品设计系统 | `skills/product-design-system/` | `产品需求` / `产品原型` / `需求文档` | 输出 HTML 原型、需求说明文档、CHANGELOG | `AGENTS.md` |
| 前端演示文稿生成器 | `skills/frontend-slides/` | `演示文稿` / `PPT转网页` / `presentation` | 生成单文件 HTML 幻灯片，支持 PPT 转换 | `SKILL.md` |
| AI 投资复盘官 | `skills/ai-invest-agent/` | `投资复盘` / `投资周报` / `每日快检` | 做跨市场投资复盘、温度计检查、文档导出 | `README.md` / `prompts/*.md` |
| coding-agent-loops | `skills/coding-agent-loops/` | `长任务编码` / `持续跑agent` | 适合长周期编码、自动重试、多 agent 协作 | `SKILL.md` |

如果不知道一个任务该走哪个 skill，优先看 [SKILLS.md](SKILLS.md)。如果知道要做什么但不知道怎么执行，直接进对应 skill 目录读它自己的 `SKILL.md`、`README.md` 或 `AGENTS.md`。

## 开源项目引用与致谢

本工作区整合了多个开源项目与社区组件，用于补齐内容生成、发布自动化、公开信息读取和投资复盘能力。这里特别说明两点：

- 本仓库会保留原项目作者署名、许可证和必要的引用说明。
- 本仓库上的改动主要集中在 OpenClaw 工作区接入、稳定性加固、脚本编排、中文文档和使用流程收敛，不改变原项目的原始署名归属。

当前直接集成或显式引用的核心开源项目包括：

| 目录 / 能力 | 上游项目 | 说明 |
| --- | --- | --- |
| `skills/ai-invest-agent/` | [AIPMAndy/ai-invest-agent](https://github.com/AIPMAndy/ai-invest-agent) | 投资复盘与温度计分析能力 |
| `skills/小红书笔记技能包/` | [comeonzhj/Auto-Redbook-Skills](https://github.com/comeonzhj/Auto-Redbook-Skills) | 小红书卡片渲染与发布技能基础 |
| `skills/xianyu-multi-agent/` | [shaxiu/XianyuAutoAgent](https://github.com/shaxiu/XianyuAutoAgent)、[cv-cat/XianYuApis](https://github.com/cv-cat/XianYuApis) | 闲鱼自动化与接口能力参考来源 |
| 内容读取桥接 | [runesleo/x-reader](https://github.com/runesleo/x-reader) | 公开内容读取与信息抓取支持 |

感谢上述项目的作者、维护者与每一位贡献者。没有这些开源工作，这个工作区不会这么快形成可复用的稳定链路。

## 日常命令速查

### 网关与守护

```bash
# 推荐唯一日常入口
bash scripts/gateway_stable_start.sh

# 常规状态检查
openclaw gateway status
openclaw status

# 推荐复位方式
openclaw gateway restart
openclaw gateway status

# 守护状态
python3 scripts/openclaw_guardian.py status
```

### 安全基线

```bash
bash scripts/security_baseline.sh check
bash scripts/security_baseline.sh fix
```

### 公众号草稿箱

```bash
python3 scripts/wechat_draft.py --file "drafts/文章.md" --title "标题" --digest "摘要"
```

规则：

- 未执行脚本且未看到成功结果，不能说“草稿箱已更新”
- 报 `40164 invalid ip` 时，先去微信后台加 IP 白名单

### 小红书

```bash
python3 skills/小红书笔记技能包/scripts/render_xhs.py content.md -o /tmp/xhs -t playful-geometric -m auto-split
python3 skills/小红书笔记技能包/scripts/publish_xhs.py --payload /tmp/xhs/payload.json --browser-mode --browser-profile-dir ~/xhs_workspace/xiaohongshu-send/profile-persistent --cookies-path ~/xhs_workspace/xiaohongshu-send/data/cookies.json
```

规则：

- 默认先发“仅自己可见”
- `payload` 必须带 `content`
- 图不超过 8 张
- 出现扫码通常意味着 Cookie 已失效

### 闲鱼

```bash
bash scripts/xianyu_live_publish.sh --title "标题" --description "描述"
```

规则：

- 发布是外部动作，执行前必须确认
- 先准备好文案和首图

## 关键运行细节

这些是 README 必须保留的稳定事实：

- 默认模型链路：`openai-codex/gpt-5.4` -> `openai-codex/gpt-5.3-codex`
- 默认停用 `api123/*` 自动路由
- `wecom` 官方插件真实 ID 是 `wecom-openclaw-plugin`
- `guardian` 会处理坏 session、模型熔断和部分配置漂移
- `scripts/gateway_stable_start.sh` 是当前最稳的网关启动入口
- `MEMORY.md` 是唯一长期记忆落盘位置

## 安全边界

### 可以直接做

- 读文件、搜索、分析、生成草稿
- 推公众号草稿箱
- 抓公开内容

### 先确认再做

- WhatsApp 发送
- 公开发布
- Cookie 导入或更新
- 安装软件、改配置、推送 GitHub、外部 API 写操作

### 明确不要做

- `rm -rf`
- 手工改 `~/.openclaw/openclaw.json`
- 手工 kill 网关进程
- 泄露 `.credentials`、Token、Cookie、密钥

细节边界以 [HEARTBEAT.md](HEARTBEAT.md) 为准。

## 常见故障处理

### 1. 聊天框报 `-11 read`

先跑：

```bash
bash scripts/gateway_stable_start.sh
```

如果还异常，再跑：

```bash
openclaw gateway install --force
openclaw gateway restart
```

不要做：

- 不要手工 kill
- 不要 `stop + start` 连击
- 不要在 Dashboard 刚 warm-up 时急着新建 session

### 2. Dashboard 打不开

先检查：

```bash
openclaw gateway status
```

再回到推荐入口：

```bash
bash scripts/gateway_stable_start.sh
```

### 3. 小红书要求扫码

基本可以直接判断为 Cookie 失效。更新浏览器 Cookie 后重启对应链路，不要把扫码当常规登录方式。

### 4. 公众号推送失败

优先检查：

- `.credentials` 是否正确
- 微信后台 IP 白名单是否包含当前出口 IP
- `wechat_draft.py` 是否真的返回成功

## 目录说明

| 路径 | 作用 |
| --- | --- |
| `scripts/` | 常用运维、发布、诊断脚本 |
| `skills/` | 各技能包与子系统 |
| `drafts/` | 草稿与中间产物 |
| `MEMORY.md` | 长期记忆 |
| `.credentials.template` | 凭证模板 |
| `AGENTS.md` | AI 员工路由入口 |
| `SKILLS.md` | 技能总路由 |

## 已接入的重要能力

- 公众号选题、成稿、排版、草稿箱推送
- 小红书图文渲染与发布链路
- 闲鱼半自动发布链路
- 产品设计系统三件套
- HTML 演示文稿生成器
- AI 投资复盘技能包
- 企业微信 WeCom 插件

## 一句话建议

第一次使用，别上来就看完全部文档。先跑通：

1. `bash scripts/gateway_stable_start.sh`
2. `openclaw agent --agent main --message "只回OK" --json`
3. 选一个触发词直接试，比如 `AI简报`、`今日选题` 或 `产品需求`

跑通之后，再去看 [AGENTS.md](AGENTS.md)、[SKILLS.md](SKILLS.md) 和 [HEARTBEAT.md](HEARTBEAT.md)。
