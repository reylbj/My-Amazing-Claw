# MEMORY.md

> 长期记忆只保留稳定事实/偏好/固定解法；当前统一写`MEMORY.md`

## 1. 人与风格
- OpenClaw是Ray的AI员工团队，主做内容创作、产品运营、产品设计。
- Ray是资深C端产品经理；主语言中文；偏好简洁、直接、可落地；反感正确废话和形式主义。

## 2. 启动与节奏
- 启动顺序固定：`SOUL.md`→`IDENTITY.md`→`USER.md`→`MEMORY.md`。
- 默认节奏：08:00 AI简报，09:30 选题推送，30分钟心跳；无新信息回`HEARTBEAT_OK`。

## 3. 安全与原则
- 不泄露隐私/密钥；破坏性操作、外发、公开发布、安装与权限改动先确认。
- 不猜命令和配置；改配置前先备份，改后先验证再重启。
- 不报半成品成功；尤其公众号，未执行`wechat_draft.py`且确认成功，不能说"草稿箱已更新"。

## 4. 运行稳定面
- 工作区固定：`~/.openclaw/workspace-runtime-real`；避免Desktop中文/emoji路径，防`-11 read`。
- 网关优先`openclaw gateway restart`或`bash scripts/gateway_stable_start.sh`；禁手工kill、禁`stop+start`连击。
- `scripts/gateway_stable_start.sh`与guardian已修正为: 识别任意`Node 22`实际二进制路径，不再把`/opt/homebrew/opt/node@22/bin/node`误判为漂移；且会对"Service not installed"自动补做`openclaw gateway install --force`。
- 企业微信官方插件的真实插件ID是`wecom-openclaw-plugin`，不是频道名`wecom`；若`plugins.allow/entries/installs`误写成`wecom`会让整份`openclaw.json`变 invalid 并卡死网关。guardian `configure` 与 `scripts/gateway_stable_start.sh` 现已在启动前自动迁移旧键并修复。
- 清理QClaw后若掉线，先查`~/.openclaw/openclaw.json`是否残留`wechat-access`/`content-security`引用；删残留后再`restart`。
- `whatsapp/telegram`若`groupPolicy=allowlist`且名单为空会丢群消息；空名单时群策略应为`open`。
- 默认模型链路：`openai-codex/gpt-5.4` → `openai-codex/gpt-5.3-codex`；默认停用 `api123/*` 自动路由，避免后台探针与备用链路产生持续小额计费。
- `scripts/openclaw_guardian.py` 已接管模型熔断：20分钟内连续3次 overload/504/failover 即 promote 到第一备用；静默20分钟后用临时 probe agent 探测原主模型，成功再切回。
- 若原主模型已从当前 fallback 链移除，guardian 必须直接清空旧 failover 状态，不再继续探测或自动切回已下线模型。
- 若旧 channel session 仍绑定已下线模型，必须清理对应 `sessions.json` 条目，让下一条消息重新按当前默认路由建会话。
- guardian 模型恢复探针已兼容 provider 前缀被省略的模型回显（如请求`api123/claude-sonnet-4-6`，回传`claude-sonnet-4-6`），避免误判恢复失败。
- WhatsApp 若把 `400 Improperly formed request` 原样回给用户，按主模型故障处理；guardian 也要统计这类 400 并 promote 到 `gpt-5.4`，同时清掉对应私聊旧 session 再重建。

## 5. 内容与发布链路
- 信息采集：X优先`agent-reach + xreach`；非X用`x-reader`；必要时`agent-reach doctor`补位。
- 公众号流程：选题→成稿(888-1888字)→写`drafts/`→`scripts/wechat_draft.py`→确认成功后再通知。
- 微信凭证在`.credentials`；报`40164 invalid ip`先加公众号IP白名单。
- `skills/wechat-article-formatter/`已部署；默认橙韵风格；公众号兼容铁律：白卡用`table+td`、只放hook、章节标题用橙色方块+中文序号、案例用table卡片；`wechat_draft.py`已支持HTML直推不二次转换。
- 小红书链路已稳定：Cookie优先；MCP在`~/xhs_workspace/xiaohongshu-send`；默认先发"仅自己可见"再人工公开。
- 闲鱼接单当前走半自动：Ray手动发布/沟通，我负责生成交付；不承诺全自动上架。
- `skills/xianyu-multi-agent/` 已补齐到 `skills/` 并改成默认优先走本机 `openclaw agent`，直接复用 `openai-codex/gpt-5.4`；无单独 API_KEY 也可生成闲鱼文案，若配置 `API_KEY` 则回退走 OpenAI SDK。
- 闲鱼 Cookie 现统一三处存储并保持同步：根`.credentials`的`XIANYU_COOKIE`、`skills/xianyu-multi-agent/.env`的`COOKIES_STR`、`skills/xianyu-multi-agent/data/xianyu_cookies.json`；`scripts/xianyu_cookie_test.py` 改为走 `https://passport.goofish.com/newlogin/hasLogin.do` 校验，`XianyuApis.py` 调试日志不再打印 Cookie/Token 明文。
- 闲鱼 `goofish` 新版发布页已确认不是旧的“标题+textarea”结构：当前主文案输入是 `contenteditable` 描述区，描述后会动态出现 `预计工期` 与 `计价方式` 两个下拉；`xianyu_auto_publish.py` 已按这个结构适配并增加默认安全占位首图 `skills/xianyu-multi-agent/data/default_publish_cover.png`，但发布按钮仍可能受平台前端异步/业务校验影响，默认仍按“半自动发布”认知处理。
- 闲鱼新版发布页的 `发布` 按钮不能靠 class 名里是否含 `disabled` 来判断是否可点；真实状态要看 `disabled/aria-disabled/pointer-events` 等实际交互属性，否则会把已可发布的黄色按钮误判成灰态。
- 闲鱼当前真实阻塞细节不是按钮颜色，而是图片上传链路的尾部静默：即使按钮已变黄，只要 `stream-upload.goofish.com/api/upload.api` 还有残留请求，就可能点了也不会真正发出最终发布请求；可视化真发命令已固定为 `bash scripts/xianyu_live_publish.sh ...`，脚本会先等上传接口静默再自动点发布。
- 闲鱼发布文案当前固定四条约束：1）不做拼音首字母/缩写避审编码，只做合规改写；2）默认只传 1 张与主题相关的封面图；3）封面图在字段填写早期就先上传，让图片处理与表单填写并行；4）描述统一输出“适合需求/交付内容/服务亮点/下单前请发”结构，强调需求明确、排版清晰、便于成交。
- 根 `AGENTS.md` / `SKILLS.md` 已增加“咸鱼运营官”路由；触发词为`咸鱼运营/闲鱼运营/闲鱼发布`，统一入口固定为 `skills/xianyu-multi-agent/`，正式发布命令固定为 `bash scripts/xianyu_live_publish.sh --title "标题" --description "描述"`。

## 6. 已部署能力
- `skills/product-design-system/`：触发词"产品需求/需求文档/原型设计"，交付`HTML原型 + 需求说明文档 + CHANGELOG`。
- `skills/wechat-article-formatter/`：触发词"公众号排版/微信文章格式化"，默认橙韵风格。
- `skills/frontend-slides/`：触发词"演示文稿/PPT转网页/幻灯片/presentation"，零依赖HTML演示文稿生成器，支持PPT转换(python-pptx已装)、12种视觉预设、视觉风格探索。
- `skills/coding-agent-loops`已安装，适合长任务、自动重试、持续编码流程。
- 企业微信(WeCom)已于 2026-03-12 接入成功：官方插件 `@wecom/wecom-openclaw-plugin` 已安装并加载；配置走 `channels.wecom`，当前为 `dmPolicy=open`、`allowFrom=["*"]`、`groupPolicy=open`；已验证可正常收发消息。
- 2026-03-23 OpenClaw 网关/Weixin 稳态修复：`scripts/openclaw_guardian.py` 现会同时修三层兼容问题：1）恢复缺失的 `dist/control-ui` 资产；2）为宿主 `openclaw/plugin-sdk` 根入口补回旧版导出（如 `resolvePreferredOpenClawTmpDir` / `withFileLock` 等），确保 `npx -y @tencent-weixin/openclaw-weixin-cli@latest install` 在“首次连接”阶段不再因旧 SDK 导出缺失而崩；3）安装后再次重写 `~/.openclaw/extensions/openclaw-weixin` 与 `wecom` 插件源码到新子模块路径。当前验收标准仍是 `bash scripts/gateway_stable_start.sh` + Dashboard `http://127.0.0.1:18789/` 返回 200。

## 7. 记忆规则
- 这里只写长期有效的偏好、决策、稳定流程、复发故障解法。
- 用户说"记住这个"，必须落盘到 `MEMORY.md`，不能只靠会话记忆。
- 不使用独立记忆目录，所有记忆统一写入 `MEMORY.md`。
- 根 `SKILLS.md` 只保留技能路由与硬约束；详细执行细则下沉到各子系统 `SKILL.md` / `AGENTS.md`，避免重复维护。
- 以后凡是用户让我从 GitHub 部署新项目或应用 skills，项目包默认存到 `skills/` 文件夹,且必须完整仔细的配置细节然后验证产出结果，之后必须同步极度精炼的更新这几个大目录下的核心文档：`SKILL.md`,`AGENTS.md`,`MEMORY.md`,`TOOLS.md`

## 8. GitHub技能部署铁律
每次从GitHub部署新项目时，必须严格执行：
1. **完整配置**：克隆→读核心文档→安装依赖→设置权限→验证可用性
2. **产出验证**：运行测试命令/检查关键文件/确认依赖就绪，不能只克隆就算完
3. **文档同步**：验收通过后，必须极度精炼更新大目录下的四个核心文档：
   - `MEMORY.md`：已部署能力条目(路径/触发词/核心特性/依赖状态)
   - `AGENTS.md`：AI员工触发词段落(触发词/路径/规则文件/能力简述)
   - `TOOLS.md`：工具使用说明(CLI命令/适用场景/关键参数)
   - `SKILLS.md`(如存在)：技能路由条目
4. **更新原则**：只写关键信息，避免重复SKILL.md内容，保持核心文档精简可读
