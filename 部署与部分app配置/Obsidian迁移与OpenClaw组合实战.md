# Obsidian + OpenClaw 迁移实战（Claude Code / Codex App）

我决定迁移到 Claude Code + Obsidian，这件事本身不简单。  
我以前常用的搭配是：所有信息先走微信，再发到滴答清单。这个兼容度很高：

- 能走链接就走链接
- 群聊信息等多文本行难复制，就做截图
- 每条信息留一句用途（是选题，还是深入学习）

但这个流程有个无解缺点：只是把知识点从一片海搬到一个湖里。  
过几天还是要继续收录到飞书，文本去重、视频文案提取、内容排期等流程还要再来一遍。

要无痛迁移到 Obsidian，核心就是先解决两件事：

1. 信息怎么流动到 Obsidian
2. Obsidian 里的信息怎么有合理结构，让我和 AI 都看得懂

> 💡 这篇的超高速打开方式：全篇丢给 OpenClaw，把安装和配置的半自动搞定。

---

## 1. 文件结构与基础认知

本质上可以把 Obsidian 看成一个大的 Markdown 阅读器。  
它有很丰富的插件体系，也可以内置 Claude Code（Claudian）。

我后面把 Claudian 换成了 Codex App，主要因为：

- Claudian 对话窗口上限是 3 个
- 没有可视化定时任务管理
- Codex App 在表现和对话管理上更稳

如果你是从 Claude Code 迁移记忆到 Codex App：

1. 把本地 `Claude.md` 复制一份
2. 放到同目录
3. 改名为 `Agent.md`

---

## 2. 先装 Obsidian，再补必要插件

刚安装的 Obsidian 只是纯阅读器，先装社区插件：

- `Claudian`（把本地 Claude Code 内置到侧栏）
- `笔记同步助手`（让 Obsidian 能同步微信消息）
- `Image auto upload`（配合 PicGo 上传到 GitHub，降低本地图片存储压力）
- `ObShare`（上传同步到飞书，方便团队分享）

不需要手动逐个点，直接在 Claude Code 或 Codex App 输入插件名即可。

---

## 3. 同步方式与目录策略

我直接把 Obsidian 文件目录放 iCloud，不用额外配置定时同步。  
Claude Code 安装可看你已有教程；也可以直接上 Codex App，基本免配置。

我踩过一个坑：  
所谓“最适合 Obsidian + Claude Code 记忆的文件系统”太多，GitHub 一搜 5000+ 项目。  
还有个常见误区：目录一定要和 Claude Code 强绑定，不然记不住。

我实际用下来是：

- 批量移动或改文件时，让模型录入 memory
- 把关键路径和“每次启动必读文件”写进 `Claude.md`
- 新对话默认会读取这些关键记忆

我的目录基于：

- `MarsWang42/OrbitOS`
- 融合 `heyitsnoah/claudesidian` 的 `metadata`（提示词 + 工作流模板）

另外我加了一条硬规则：每次对话结束主动更新知识。  
目录深度限制 3 层子目录，AI 遗漏文件时再把路径和用途补回记忆文件。

---

## 4. 信息进入 Obsidian 的三条路径

信息收录基本分三类：

1. 插件
2. 微信
3. OpenClaw（专门啃难解析链接和视频）

### 4.1 Web / GPT 导出

- GPT 导出到 Obsidian：快速生成 `USER.md`，后面 OpenClaw 也能用
- Obsidian Web Clipper / HoverNotes：网页、公众号、视频笔记都能剪藏
- 图片偶尔抓不全，但正文 + 原链接仍在，整体效果优于手工搬运
- 抓 X 时还能顺带抓评论区

### 4.2 手机端分流

我做过快捷指令，按收录时间自动分流到不同文件夹。  
但共享表单接收不是所有场景都稳定，这时会怀念“微信 + 滴答”那套。

### 4.3 微信同步助手

后来用 Deep Research 找到一个微信里的“笔记同步助手”：  
支持 OneNote / Obsidian / Notion 同步，还能把小红书视频转图文笔记。  
这类工具可以明显减少中转损耗。

---

## 5. OpenClaw 与 Obsidian 打通（关键）

OpenClaw 可以把“信息录入 + 信息整理”合并为一步。  
配置完成后，就能在 Obsidian 里直接维护 OpenClaw 的核心配置。

### 5.1 先装联网与解析能力

1. 联网搜索与链接解析
   - x-reader: `https://github.com/runesleo/x-reader`
   - Agent Reach: `https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md`
   - BrowserWing: `https://raw.githubusercontent.com/browserwing/browserwing/main/INSTALL.md`

2. Obsidian 连接能力（让 OpenClaw 可写入 Obsidian）
```bash
npx clawhub@latest install obsidian
```

3. 主动找 skill 解决问题
```bash
npx clawhub@latest install find-skills
```

4. 主动迭代 Agent
```bash
npx clawhub install proactive-agent-1-2-4
```

### 5.2 建软链接（你最关心的动作）

目标：在 Obsidian 仓库里创建 `OpenClaw配置`，并把工作区映射进去。  
这样在 Obsidian 里编辑 `SOUL.md`，OpenClaw 可以立即生效。

已提供半自动脚本：

```bash
bash scripts/setup_obsidian_bridge.sh --vault "你的Obsidian仓库路径"
```

示例：

```bash
bash scripts/setup_obsidian_bridge.sh --vault "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/MyVault"
```

只建链接不安装 skills：

```bash
bash scripts/setup_obsidian_bridge.sh --vault "你的Obsidian仓库路径" --skip-install
```

配置体检（推荐每次改完后执行）：

```bash
bash scripts/doctor.sh --vault "你的Obsidian仓库路径"
```

公众号链接自动收录到 Obsidian：

```bash
./scripts/openclaw.sh wx "https://mp.weixin.qq.com/s?..." "你的Obsidian仓库路径"
```

---

## 6. 联网搜索高级化（中级到高级的第一步）

先把联网搜索做到极致，再谈“龙虾分身”。

OpenClaw 目前内置搜索是 Brave / Perplexity，一个绑卡一个付费。  
所以我先换成 Tavily + Multi Search Engine v2.0.1。

### Tavily

- 每月 1000 次免费调用
- 不绑卡
- 面向 Agent 设计，返回内容结构化处理过

### Multi Search Engine v2.0.1

- 集成 17 个搜索引擎（8 个中文 + 9 个全球）
- 不需要 API
- 安装时记好搜索规则即可

### 难解析链接补位

- `x-reader`：YT、某站、X、公众号、TG、RSS、播客、某书
- `Agent Reach`：在 x-reader 基础上增加某抖、Reddit、GitHub
- 建议：优先 Cookie 登录，尽量用小号

### 浏览器自动化补位

常见场景：点确认、滑页面、登录态跳转。

- Playwright 是基础
- BrowserWing 可以录制浏览器操作并固化成 skill，下次精确重放

### Gemini 相关增强（可选）

- ModSearch：把 Gemini CLI 变成搜索能力，走 Google 信息源
- Gemini Deep Research：把 Gemini Deep Research 能力带进 OpenClaw（Gemini 3.1 Pro）

### 生态增强

- `find-skills` / `Clawhub`：遇到问题主动找合适 skills
- `ClawFeed`：被动更新信息源（X / RSS / HackerNews / Reddit / GitHub Trending），每 4 小时更新
- `Free Ride`：OpenRouter 免费模型兜底，避免长任务半夜停机

---

## 7. 使用结论

后续会有更多 OpenClaw + Obsidian 专题。  
现在 skills 变多，多群组 + 多实例案例也在变多。

把 Obsidian 作为本地知识管理数据层，是当前最稳妥的选择之一。  
信息管理别太心疼损耗，能落本地就做备份：

- 图床会失效
- 链接会过期
- 文字最耐久

用久了你会发现，同一份数据会被 OpenClaw 总结沉淀到不同位置。  
刚开始会不理解它为什么这么分，但实际用下来这是对的：

- 你主要管“可用性”
- 来源链路交给 AI 记忆系统

这就是和 AI 共用知识体系的独特体验：  
你在写它的技能和记忆，它也在主动记录你的偏好，双方持续进化。

---

## 8. 一句话执行版

- 先搭 Obsidian 目录和插件
- 再打通 OpenClaw 的写入和联网
- 最后把“收录 + 整理 + 复用”做成一个闭环

如果你已经在本仓库里操作，直接从这条命令开始：

```bash
bash scripts/setup_obsidian_bridge.sh --vault "你的Obsidian仓库路径"
```
