# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## CLI-Anything

### 激活环境
```bash
source scripts/cli-anything-activate.sh
```

### 已安装工具
- **cli-anything-gimp**: 图像编辑CLI
  - 创建项目: `cli-anything-gimp --json project new --width W --height H -o file.json`
  - 添加图层: `cli-anything-gimp --project file.json layer new -n "Name" --fill "#color"`
  - 渲染输出: `cli-anything-gimp --project file.json export render output.png`
  - REPL模式: `cli-anything-gimp` (交互式)

### 适用场景
- 批量图像处理
- 自动化设计生成
- 图像工作流脚本

---

## Frontend Slides

### PPT转换
```bash
cd ~/.openclaw/workspace-runtime-real/skills/frontend-slides
python3 scripts/extract-pptx.py input.pptx output_dir/
```

### 依赖
- python-pptx 1.0.2 (已安装)

### 适用场景
- PowerPoint转HTML演示文稿
- 零依赖单文件网页幻灯片
- 视觉风格探索(12种预设)

---

## AI Invest Agent

### 快速使用
```bash
cd ~/.openclaw/workspace-runtime-real/skills/ai-invest-agent
pip install -r requirements.txt
```

### 主要入口
- 周度复盘: `prompts/weekly_review.md`
- 每日快检: `prompts/quick_check.md`
- 文档导出: `python3 tools/md2docx.py`
- 表格导出: `python3 tools/create_excel.py`

### 适用场景
- A股/港股/美股周度复盘
- 33指数估值温度计检查
- 持仓深度分析与复盘报告输出

---

## 企业微信 WeCom

### 当前接入方式
- 官方插件: `@wecom/wecom-openclaw-plugin`
- 配置路径: `channels.wecom`
- 启用前提: `plugins.allow` 里放行 `wecom-openclaw-plugin`

### 关键字段
- `channels.wecom.botId`
- `channels.wecom.secret`
- `channels.wecom.enabled`
- `channels.wecom.dmPolicy`
- `channels.wecom.allowFrom`
- `channels.wecom.groupPolicy`

### 已验证状态
- 2026-03-12 已完成接入并验证可正常收发

---

## Gateway / Weixin

### 推荐入口
```bash
bash scripts/gateway_stable_start.sh
bash scripts/doctor.sh
```

### 当前约定
- 网关只用 `restart` / `gateway_stable_start.sh`，不手工 `kill`
- `openclaw-weixin` 已登录但 `openclaw channels status` 只见 `configured` 时，直接重跑 `bash scripts/gateway_stable_start.sh`
- `doctor.sh` 会额外检查 Weixin 启动锚点是否缺失

---

## 模型路由

### 当前默认
- 主模型: `openai-codex/gpt-5.4`
- 唯一自动备用: `openai-codex/gpt-5.3-codex`
- `skills/xianyu-multi-agent/` 默认优先复用本机 `openclaw agent`，无单独 `API_KEY` 也可生成闲鱼文案

### 成本控制
- 默认不走 `api123/*`
- 若手动恢复 `api123/*`，同时检查并清空 guardian 旧 failover 状态，避免后台恢复探针继续打旧模型

---

## 闲鱼 Goofish

### 可视化真发命令
```bash
bash scripts/xianyu_live_publish.sh --title "AI文案代写｜自动发布实测" --description "自动化联调验证单，支持小红书笔记、公众号文章、商品详情页和短视频脚本。出稿快，可按需求修改。"
```

### 关键约束
- 命令会打开本机可视化 Chrome，完整填写发布页并自动点击 `发布`
- 真正点发布前，会等待图片上传接口 `stream-upload.goofish.com/api/upload.api` 静默，避免“按钮已黄但点了不发”
- 默认只上传 1 张主题封面图，而且会尽早上传，减少最后一步等待
- 文案统一走合规改写，不做首字母缩写或其他避审编码；标题和描述会被整理成清晰、适合成交的结构
- 逻辑脚本在 `skills/xianyu-multi-agent/live_prepublish_debug.py`
- 包装入口在 `scripts/xianyu_live_publish.sh`

---

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
