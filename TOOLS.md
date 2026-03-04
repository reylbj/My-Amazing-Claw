# TOOLS.md - 工具与环境配置

> Skills定义工具的运行方式，本文件记录Ray的具体环境配置——你的专属设置。

## 通信工具

### WhatsApp
- **用途**: 日常通知、选题推送、AI简报
- **通知格式**: 列表形式，不用表格
- **推送时间**: 由Ray自己决定
- **消息规范**: 简洁清晰，附行动指引

### 微信公众号
- **草稿箱API**: `scripts/wechat_draft.py`
- **推送条件**: 文章初稿生成完毕后自动调用
- **通知机制**: 推送成功后WhatsApp告知Ray

## 内容发布平台

### 微信公众号
- **定位**: 主内容输出平台
- **风格**: 专业深度 × 有温度有观点
- **发布频率**: 根据选题官产出节奏决定

### 微信视频号（暂记录）
- **用途**: 短视频内容配合公众号
- **脚本来源**: 短视频编导skill
- **状态**: 记录中，暂未自动化

### 小红书（xiaohongshu-send）
- **定位**: 图文自动发布链路（登录复用 + MCP 服务 + 发布调用）
- **安装与服务脚本**: `scripts/xiaohongshu_send_setup.sh`
- **校验与发布脚本**: `scripts/xiaohongshu_send.py`
- **运行目录**: `xiaohongshu-send/`（`bin/`、`data/cookies.json`、`logs/mcp.log`）
- **详细文档**: `部署与部分app配置/小红书配置指南.md`

## 水产市场（openclawmp）
- **CLI入口**: `openclawmp`
- **当前资产**: `experience/@u-3ce5e3aff0c34baaa034/self-evolution`、`experience/@u-a25e114956065150/Multi Source Tech News Digest`、`skill/@u-8d4b3846fb3c3e0c/Auto-Redbook-Skills`
- **调用策略**: 手动点名调用为主，`experience` 提供策略，`skill` 用于产出执行
- **常用命令**: `openclawmp list`
- **空格名称命令示例**: `openclawmp info "experience/@u-a25e114956065150/Multi Source Tech News Digest"`

## 跨平台信息抓取

### x-reader（主抓取）
- **覆盖渠道**: YT、某站、公众号、TG、RSS、播客、某书（非X）
- **定位**: 链接级内容读取与结构化摘要
- **运行方式**: `source scripts/activate_agent_tools.sh` 后调用 `x-reader <URL>`
- **登录策略**: 优先 Cookie 登录，不依赖扫码

### Agent Reach（X主链路 + 补强抓取）
- **X抓取主链路**: `xreach`（tweet/user/search）
- **补强渠道**: 某抖、Reddit、GitHub
- **定位**: X抓取执行 + 渠道可用性体检（`agent-reach doctor`）
- **运行方式**: `source scripts/activate_agent_tools.sh` 后调用 `xreach ...` / `agent-reach ...`
- **登录策略**: 优先 Cookie 导入（`xreach auth extract --browser chrome`）

### 常用命令
```bash
# 激活 Python 3.11 工具环境
source ./scripts/activate_agent_tools.sh

# X内容抓取（主链路）
xreach tweet 2027241615992225930
xreach user OpenAI

# 非X单链接抓取
x-reader "https://example.com"

# 全链路体检（哪些渠道已可用）
agent-reach doctor
```

## 信息源配置

### AI简报信息源
- Twitter/X（AI领域KOL）
- 36氪（科技创业资讯）
- HuggingFace博客（模型更新）
- The Verge（科技消费品报道）

### 宠物行业信息源
- 宠物行业白皮书（年度）
- 各大宠物电商平台（趋势）
- 宠物科技创业资讯

## 模型配置

### 主要模型
- **主力**: api123/claude-sonnet-4-6（承担95%任务）
- **顶级**: api123/claude-opus-4-6（极其复杂或需要极高想象力的任务，5%）

### 降级规则
```yaml
降级链: Opus → Sonnet → 队列等待

触发条件:
  - API请求失败或超时
  - 连续3次请求失败
  - 服务不可用
```


## 内容审核配置

### 自动推送前检查
- ✅ 文章字数在888-1888字之间
- ✅ 无敏感词汇
- ✅ 标题符合15-25字规范
- ✅ 有明确的结论和行动建议

### 禁止推送条件
- ❌ 含有未经验证的数据（标注来源后允许）
- ❌ 纯AI生成无人工审核的内容（需Ray确认）
- ❌ 含有竞品负面信息

## 时区与工作时间

- **时区**: Asia/Shanghai (UTC+8)
- **工作日**: 周一至周五
- **主动推送时间**: 08:00（简报）、09:30（选题）
- **静默时间**: 23:00 - 07:00（非紧急不打扰）

## Google Drive 云端存储

### 工具配置
- **工具**: rclone v1.73.1
- **远程名称**: gdrive
- **备份目录**: OpenClaw-Backups
- **项目目录**: petch（完整项目文件夹）

### 权限规则
**允许操作**：
- ✅ 读取所有文件和文件夹
- ✅ 下载文件到本地
- ✅ 列出目录结构
- ✅ 查看文件元数据
- ✅ 搜索文件内容

**需要批准的操作**：
- ⚠️ 创建新文件（需Ray批准）
- ⚠️ 修改现有文件（需Ray批准）
- ⚠️ 编辑文件内容（需Ray批准）

**禁止操作**：
- ❌ 删除任何文件
- ❌ 移动文件位置
- ❌ 重命名文件
- ❌ 修改文件权限

### 常用命令
```bash
# 读取操作（无需批准）
rclone ls gdrive:petch/                    # 列出petch目录
rclone lsd gdrive:petch/                   # 列出petch子目录
rclone cat gdrive:petch/文件名              # 查看文件内容
rclone copy gdrive:petch/ ./本地目录/       # 下载整个项目

# 需要批准的操作
rclone copy 本地文件 gdrive:petch/          # 上传新文件（需批准）
# 修改文件需先下载、编辑、再上传（需批准）

# 备份操作
./部署与部分app配置/google-drive-backup.sh   # 自动备份OpenClaw配置
```

### 安全检查
- 所有写入操作前必须通过 `AskUserQuestion` 获得Ray批准
- 禁止使用 `rclone delete`、`rclone purge`、`rclone move` 命令
- 禁止使用 `rclone sync`（会删除目标中多余的文件）
- 使用 `rclone copy` 而非 `rclone sync` 进行文件传输

### 配置文件
- **配置向导**: `./部署与部分app配置/setup-google-drive.sh`
- **备份脚本**: `./部署与部分app配置/google-drive-backup.sh`
- **完整文档**: `./部署与部分app配置/GoogleDrive配置指南.md`

---

_根据实际环境更新本文件 | 更新日期：2026-03-03_
