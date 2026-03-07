# TOOLS.md - 工具与环境配置

> Skills定义运行方式，本文件记录Ray的环境配置

## 通信工具

### WhatsApp
**用途**: 日常通知/选题推送/AI简报
**格式**: 列表形式(不用表格)，简洁清晰+行动指引
**推送**: Ray决定时间

### 微信公众号
**草稿箱API**: `scripts/wechat_draft.py`
**推送条件**: 文章初稿生成完毕后自动调用
**通知**: 推送成功后WhatsApp告知Ray

## 内容发布平台

### 微信公众号
**定位**: 主内容输出平台
**风格**: 专业深度×有温度有观点
**频率**: 根据选题官产出节奏

### 微信视频号(暂记录)
**用途**: 短视频配合公众号
**脚本**: 短视频编导skill
**状态**: 暂未自动化

### 小红书(xiaohongshu-send)
**定位**: 图文自动发布(登录复用+MCP服务+发布调用)
**脚本**: `scripts/xiaohongshu_send_setup.sh` / `scripts/xiaohongshu_send.py`
**目录**: `xiaohongshu-send/`(`bin/`、`data/cookies.json`、`logs/mcp.log`)
**文档**: `部署与部分app配置/小红书配置指南.md`

## 水产市场(openclawmp)
**CLI**: `openclawmp`
**资产**: `self-evolution` / `Multi Source Tech News Digest` / `Auto-Redbook-Skills`
**策略**: 手动点名，`experience`提供策略，`skill`产出执行
**命令**: `openclawmp list` / `openclawmp info "experience/@u-xxx/Name"`

## 跨平台信息抓取

### x-reader(主抓取)
**渠道**: YT/某站/公众号/TG/RSS/播客/某书(非X)
**定位**: 链接级内容读取+结构化摘要
**运行**: `source scripts/activate_agent_tools.sh` → `x-reader <URL>`
**登录**: 优先Cookie，不依赖扫码

### Agent Reach(X主链路+补强)
**X主链路**: `xreach`(tweet/user/search)
**补强**: 某抖/Reddit/GitHub
**定位**: X抓取执行+渠道体检(`agent-reach doctor`)
**运行**: `source scripts/activate_agent_tools.sh` → `xreach ...` / `agent-reach ...`
**登录**: Cookie导入(`xreach auth extract --browser chrome`)

### 常用命令
```bash
source ./scripts/activate_agent_tools.sh
xreach tweet 2027241615992225930  # X抓取
x-reader "https://example.com"    # 非X抓取
agent-reach doctor                # 全链路体检
```

## 信息源

### AI简报
Twitter/X(AI KOL) / 36氪(科技创业) / HuggingFace(模型更新) / The Verge(科技消费)

### 宠物行业
宠物行业白皮书(年度) / 宠物电商平台(趋势) / 宠物科技创业资讯

## 模型配置

**主力**: api123/claude-sonnet-4-6 (95%任务)
**顶级**: api123/claude-opus-4-6 (极复杂/高想象力任务，5%)

**降级链**: Opus → Sonnet → 队列等待
**触发**: API失败/超时、连续3次失败、服务不可用

## 内容审核

### 推送前检查
✅ 字数888-1888 / 无敏感词 / 标题15-25字 / 有明确结论+行动建议

### 禁止推送
❌ 未验证数据(标注源后允许) / 纯AI生成无审核(需Ray确认) / 竞品负面信息

## 时区与工作时间

**时区**: Asia/Shanghai (UTC+8)
**工作日**: 周一至周五
**推送**: 08:00(简报) / 09:30(选题)
**静默**: 23:00-07:00(非紧急不打扰)

## Google Drive

### 配置
**工具**: rclone v1.73.1
**远程**: gdrive
**目录**: OpenClaw-Backups / petch(项目)

### 权限
**允许**: ✅读取/下载/列目录/查元数据/搜索
**需批准**: ⚠️创建/修改/编辑文件
**禁止**: ❌删除/移动/重命名/改权限

### 命令
```bash
# 读取(无需批准)
rclone ls gdrive:petch/
rclone cat gdrive:petch/文件名
rclone copy gdrive:petch/ ./本地/

# 需批准
rclone copy 本地文件 gdrive:petch/

# 备份
./部署与部分app配置/google-drive-backup.sh
```

### 安全
写入前必须`AskUserQuestion`获Ray批准；禁用`delete/purge/move/sync`；用`copy`不用`sync`

### 配置文件
`./部署与部分app配置/setup-google-drive.sh` / `google-drive-backup.sh` / `GoogleDrive配置指南.md`

---
_更新:2026-03-03_
