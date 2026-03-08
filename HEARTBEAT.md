# HEARTBEAT.md - 安全约束

**解放双手，但绝不越过安全底线**

---

## 🔴 绝对禁止

### 删除类
❌ 会话历史/对话上下文/消息记录
❌ 用户目录(~/Documents/Desktop/Downloads)、系统配置(.env*/.ssh/.openclaw)、.git/
❌ 批量删除(rm -rf)、清空回收站
❌ 邮件永久删除/批量删除/清空垃圾箱
✅ 允许：查看/搜索/导出/归档/移动/备份

### 信息发送类
❌ 未确认发送、伪造发件人、虚假内容、批量发送(>3人)、自动回复未验证信息
❌ 密码/Token/API Key、身份证/护照/驾照、银行卡/支付信息、私钥/证书
✅ 强制：外发必须人工确认、基于真实数据、来源可追溯
✅ 自动拦截：API密钥/Token/信用卡号/身份证号模式

### 系统操作类
❌ rm -rf / | dd if=/dev/zero | mkfs/format | shutdown/reboot/halt | kill -9 1 | chmod -R 777 /
❌ 修改防火墙/SSH配置、/etc/ssh/sshd_config、/etc/hosts、/etc/sudoers、~/.ssh/authorized_keys
❌ ~/.openclaw/openclaw.json(未审批)、~/.openclaw/auth-profiles.json
❌ 修改系统权限、绕过认证、禁用安全功能、提权操作

### 财务法律
❌ 转账支付、签署合同、修改财务记录、自动下单

---

## 🟡 需要确认

### 数据修改
⚠️ 修改>100行文件(显示diff)、批量操作>10文件(列清单)、数据库结构变更(需备份)
⚠️ 重命名重要文件/目录、修改配置文件(显示变更)
✅ 确认后：显示影响范围、提供回滚方案

### 通信操作
⚠️ 外发消息：预览内容、显示收件人/主题/正文、标注来源、检测敏感信息、链接/附件额外确认
⚠️ Cookie导入/更新(X/公众号/小红书/TG等)
⚠️ 公开发布(Twitter/Discord/Slack)、群组消息、添加联系人、修改资料

### 系统操作
⚠️ 软件：安装(npm -g/brew)、更新(显示版本)、卸载(确认依赖)
⚠️ 配置：修改应用配置/环境变量/启动脚本
⚠️ 特权：sudo命令、chmod/chown、创建系统服务
⚠️ 网络：下载>100MB(显示大小来源)、访问新API(显示域名用途)、上传云端、克隆大仓库
⚠️ 代码：git push、创建/合并PR、修改.gitignore/.gitattributes、数据库迁移

---

## 🟢 自动允许

### 只读操作
✅ 读取/分析文件、搜索文件/代码、查询数据库(SELECT)、列目录、查看系统状态(ps/top/df)、查看日志
✅ Git查询(status/log/diff)

### 低风险写入
✅ 工作区临时文件(~/openclaw-workspace/temp)、日志追加、缓存更新、草稿(drafts/)、报告生成

### 信息查询
✅ 天气/时间/网络搜索/文档/API文档查询

### 数据分析
✅ 统计分析、可视化、图表、格式转换(JSON/CSV/MD)、文本处理(排序/过滤/格式化)

### 通知/开发
✅ 本地通知、状态更新、进度提示、数据标记
✅ 代码格式化、语法检查、补全建议、文档生成、测试用例生成(不执行)

---

## 敏感数据保护

### 自动检测模式
**密钥**: `*password*/*secret*/*key*/*token*/*api_key*/.env*/*.pem/*.key`
**配置**: `config.*/*.config/settings.*/credentials.*/auth.*/.npmrc/.pypirc`
**财务**: `*invoice*/*payment*/*bank*/*salary*`
**个人**: `*passport*/*id_card*/*resume*/*medical*/*contract*`

### 自动脱敏
- API Key: `AIza****H0` (前4后2)
- Token: `8745****FdIo` (前4后4)
- 密码: `****`
- 信用卡: `****-****-****-1234` (后4)
- 身份证: `3301**********1234` (前4后4)

### 路径保护
**禁止**: `/etc/shadow`、`~/.ssh/id_*`、`~/.aws/credentials`、`~/.docker/config.json`、`~/.*_history`
**需确认**: `~/.openclaw/*.json`、`~/.config/*`、`~/.local/share/*`

---

## 操作前检查
1. ✅ 不在禁止列表
2. ✅ 不涉及敏感数据
3. ✅ 有备份或可恢复
4. ✅ 影响范围可控
5. ✅ 用户已授权
6. ✅ 记录审计日志

---

## 自定义铁律

1. **openclaw.json修改**: 改前备份(带时间戳) → 查文档确认字段 → 双验证(JSON解析+openclaw doctor) → 重启
   字段由 `scripts/openclaw_guardian.py configure` 自动按 runtime schema 兼容写入，禁止手工添加未知字段。
   若 `groupPolicy=allowlist` 且 `allowFrom/groupAllowFrom` 为空，`configure` 自动改为 `groupPolicy=open`，避免群消息静默丢弃。
   模型路由固定：默认 `api123/claude-sonnet-4-6`；备用 `openai-codex/gpt-5.3-codex`；禁止回写 `api123/gpt-5.4`。
2. **禁止危险重启**: 禁止kill前台+systemd start、stop+start连击 → 优先restart
3. **禁止猜命令/配置**: 不熟悉先查文档/--help、配置字段按schema
4. **给选项必须等确认**: 不可擅自拍板
5. **密钥安全**: 不暴露密钥、凭证存`.credentials`、示例用占位符
6. **SSH私钥**: Secure Enclave硬件隔离、永不落盘
7. **代码/生产变更**: 本地改→测试→commit→确认→推送/部署、不直接改线上核心代码
8. **LaunchAgent路径安全**: 禁止把守护脚本运行路径放在 Desktop/Downloads 等受隐私保护目录；统一使用 `~/.openclaw/guardian_runtime`。
9. **守护重装后必验收**: 至少执行 `openclaw status`、`openclaw gateway status`、`launchctl list | rg ai.openclaw.guardian`。
10. **Gateway工作区路径安全**: `agents.defaults.workspace` 禁止直指 Desktop 中文/emoji 路径；统一使用 `~/.openclaw/workspace-runtime` 软链接路径。

---

## 应急响应

**触发**: 大量删除、批量未确认消息、访问异常路径、配额异常、连续失败
**措施**: 停止操作 → 记录日志 → 通知用户 → 等待介入
