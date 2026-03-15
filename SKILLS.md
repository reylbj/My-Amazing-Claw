# SKILLS.md

> 更新时间：2026-03-11
> 根 `SKILLS.md` 只保留当前有效的技能路由、触发词、关键约束。详细执行细则优先看对应子目录 `SKILL.md` / `AGENTS.md`，避免重复维护和流程漂移。

## 全局规则

- 主模型：`openai-codex/gpt-5.4`；唯一自动备用：`openai-codex/gpt-5.3-codex`。
- `api123/*` 默认不进自动路由；需临时启用必须明确指令并同步检查 guardian/session 残留。
- 信息采集路由：X 用 `agent-reach + xreach`；非 X 用 `x-reader`；渠道补位和体检用 `agent-reach doctor`。
- 外部动作边界：公开发布、对外发送消息、安装/改权限/不确定外部操作先确认；生成草稿、写本地文件、推送微信草稿箱可直接执行。
- 成功口径：不报半成品成功。尤其公众号，未执行 `scripts/wechat_draft.py` 且未看到成功结果，不能说"草稿箱已更新"。
- 记忆口径：按当前 `MEMORY.md` 执行，稳定事实统一写 `MEMORY.md`，不再使用独立记忆目录。
- 路由原则：根文档负责"何时调用什么"；子系统文档负责"具体怎么做"。

## skill: 小红书增长官

- 触发：`小红书帖子` / `小红书笔记`
- 目标：产出可发布的小红书图文内容，默认先发"仅自己可见"。
- 稳定链路：Cookie 登录优先；MCP 固定在 `~/xhs_workspace/xiaohongshu-send`；浏览器 profile 固定复用。
- 执行顺序：更新 Cookie → 启动 MCP → 渲染 5-7 张图 → 生成 payload → 发布。
- 关键命令：

```bash
cd ~/xhs_workspace/xiaohongshu-send
COOKIES_PATH=./data/cookies.json ./bin/xiaohongshu-mcp -port :18060 -headless=true -rod "dir=./profile" > logs/mcp.log 2>&1 &
python3 skills/小红书笔记技能包/scripts/render_xhs.py content.md -o /tmp/xhs -t playful-geometric -m auto-split
python3 scripts/xiaohongshu_auto_publish.py --payload /tmp/xhs/payload.json --base-url http://127.0.0.1:18060
```

- 硬约束：`payload` 必须含 `content`；图片不超过 7 张；扫码通常意味着 Cookie 已失效；发前先检查 APP 创作中心。

## skill: 今日选题官

- 触发：`今日选题` / `选题` / `公众号选题`
- 输入来源：先读 `验证输出/ai_briefing_YYYY-MM-DD.txt` 或 `验证输出/ai_news_filtered_YYYY-MM-DD.json`。
- 输出目标：15 个选题，按方向分组。
- 配比规则：AI 资讯 5 条、产品运营 4 条、宠物行业 4 条、GTM 2 条；跨向题不超过 3 条。
- 硬约束：AI 资讯类必须基于真实当日信息并标注来源；不能凭空编热点。
- 输出格式：

```text
📝 今日选题(YYYY-MM-DD)
【AI资讯·5】1.[标题]｜[亮点≤60字] *基于:[源]*
【产品运营·4】
【宠物行业·4】
【产品GTM·2】
回复编号→初稿→草稿箱
```

## skill: AI战略官

- 触发：`AI简报` / `今日AI` / 定时 08:00
- 目标：输出 Top 5-10 条 AI 动态，并给出 1 条"今日关注"。
- 优先级：C 端 AI、AI × 宠物、产品工具更新；可带少量 B 端，但过滤纯学术、PR、重复信息。
- 来源口径：Twitter/X、36 氪、Hugging Face、The Verge、`agent-reach`、`x-reader`。
- 输出格式：

```text
📊 今日AI简报(YYYY-MM-DD 08:00)
1.[标题] 摘要:[≤50字] 影响:[≤20字]
...
---
今日关注:[编辑推荐≤100字]
```

## skill: 公众号成稿与排版草稿箱

- 触发：用户回复选题编号 / `初稿` / `草稿箱` / `公众号排版` / `微信文章格式化`
- 目标：完成公众号文章从成稿到排版再到草稿箱推送的整条链路。
- 模式 A：直接成稿推草稿箱。
  生成 888-1888 字 Markdown 成稿 → 写入 `drafts/YYYY-MM-DD_标题.md` → 执行推送脚本。
- 模式 B：排版后推草稿箱。
  按 `skills/wechat-article-formatter/SKILL.md` 将 Markdown 转为公众号兼容 HTML → 校验 → 直接推送草稿箱。
- 关键命令：

```bash
python3 scripts/wechat_draft.py --file "drafts/YYYY-MM-DD_标题.md" --title "标题" --digest "摘要"
```

- 排版入口：`skills/wechat-article-formatter/SKILL.md`
- 默认主题：橙韵风格；需要时可切 Claude 风格、蓝色专业、贴纸风格。
- 兼容铁律：白色卡片只放 hook；卡片结构用 `table + td`，不用 `box-shadow`；章节标题用橙色方块 + 中文序号；案例区优先 table 卡片。
- 当前状态：`wechat_draft.py` 已支持 HTML 直推，不会二次转换。
- 通知规则：只有在明确看到 `✅推送成功` 后，才允许发送"草稿箱已更新选题:[标题]"。
- 质量标准：标题 15-25 字；开头 3 秒抓注意力；金字塔结构；案例真实可验证；结尾可落地。
- 禁忌：黑话堆砌、观点模糊、案例陈旧、AI 式正确废话、只写文件不执行推送脚本。

## skill: 产品设计系统

- 触发：`产品需求` / `需求文档` / `产品原型` / `原型设计`
- 入口：`skills/product-design-system/AGENTS.md`
- 交付三件套：`HTML 原型 + 需求说明文档 + CHANGELOG`
- 工作顺序：先改原型，再更新需求文档，最后补 `CHANGELOG`。
- 文件约束：每个需求独立文件夹；HTML 为单文件、内联 CSS + JS；需求文档始终保持"最终态"。
- 适用场景：新功能设计、流程重构、页面改版、需求复盘。

## skill: 前端演示文稿生成器

- 触发：`演示文稿` / `PPT转网页` / `幻灯片` / `presentation`
- 入口：`skills/frontend-slides/SKILL.md`
- 能力：从零创建动画丰富 HTML 演示文稿 / 转换 PPT 为网页 / 视觉风格探索(12 种预设)
- 依赖：python-pptx 1.0.2(已安装)
- 交付产物：单文件 HTML，零依赖，内联 CSS/JS，响应式动画
- PPT 转换命令：`python3 scripts/extract-pptx.py input.pptx output_dir/`
- 硬约束：每张幻灯片必须 `height: 100vh; overflow: hidden`；所有字体用 `clamp()`；图片 `max-height: min(50vh, 400px)`；内容超限必须拆分幻灯片。

## skill: 多渠道公开情报采集

- 触发：`抓取链接` / `全网检索` / `跨平台抓取`
- 路由：X 走 `xreach tweet|user|search`；其它公开链接走 `x-reader`；可用性排查先跑 `agent-reach doctor`。
- 输出要求：给结构化摘要、来源链接、失败原因与下一步建议。
- 安全边界：仅抓公开内容；需要登录、Cookie 更新或不确定外部动作时先确认。

## skill: 水产市场资产

- 触发：手动点名，不自动触发
- 已装资产：`self-evolution`、`Multi Source Tech News Digest`、`Auto-Redbook-Skills`
- 使用顺序：先 `Multi Source Tech News Digest` 产摘要，再 `Auto-Redbook-Skills` 产内容。
- 限制：`self-evolution` 只用于复盘优化；涉及自动安装、自动发布、定时任务必须先确认。

## skill: 短视频编导

- 触发：`写脚本[主题]`
- 输出结构：标题 → 前 3 秒钩子 → 分镜（时间 + 景别 + 动作 + 口播）→ 结尾 CTA
- 时长目标：60-90 秒

## skill: AI短投研发

- 触发：`出素材[产品]`
- 输出要求：5 条差异化文案
- 固定格式：`序号 | 角度 | 标题(≤20字) | 正文(≤120字) | CTA(≤15字) | 目标人群`

## skill: 朋友圈运营

- 触发：`今日朋友圈`
- 输出要求：3-5 条朋友圈文案
- 固定格式：`[类型]正文(≤100字) | 配图建议 | 发布时间`

## skill: coding-agent-loops

- 触发：`长任务编码` / `持续跑agent` / `PRD执行` / `并行编码`
- 入口：`skills/coding-agent-loops/SKILL.md`
- 适用场景：长周期编码、自动重试、多 agent 并行、需要跨重启保活的任务。
- 硬约束：必须用 `tmux -S ~/.tmux/sock`；必须带 completion hook；结束后要核对 `git diff` / `git log`，不能只看 agent 自报完成。

## 废弃与收敛

- 根 `SKILLS.md` 不再保留大段系统提示词、重复 SOP、历史漂移命令。
- 详细玩法统一下沉到子系统入口文档，根文档只保留可路由、可执行、可验证的最小信息。
