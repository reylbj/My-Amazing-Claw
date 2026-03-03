# Google Drive 配置指南

## 项目概述

本指南记录了如何配置 Google Drive 与 OpenClaw 集成，实现自动备份和文件同步功能。

**配置日期：** 2026-03-03
**系统环境：** macOS 26.3 (x86_64)
**rclone 版本：** v1.73.1

---

## 一、前置准备

### 1.1 系统要求

- macOS 系统
- 已安装 OpenClaw
- 有效的 Google 账号
- 网络连接

### 1.2 工具安装

#### 安装 rclone

rclone 是一个强大的命令行工具，用于管理云存储文件。

**方法1：手动安装（推荐，无需 sudo）**

```bash
# 下载 rclone
cd /tmp
curl -O https://downloads.rclone.org/rclone-current-osx-amd64.zip

# 解压并安装到用户目录
unzip rclone-current-osx-amd64.zip
cd rclone-*-osx-amd64
cp rclone ~/.npm-global/bin/
chmod +x ~/.npm-global/bin/rclone

# 验证安装
rclone version
```

**方法2：使用 Homebrew（需要 sudo）**

```bash
brew install rclone
```

---

## 二、配置 Google Drive

### 2.1 运行 rclone 配置向导

```bash
rclone config
```

### 2.2 配置步骤

1. **选择新建远程**
   ```
   n) New remote
   ```

2. **输入远程名称**
   ```
   name> gdrive
   ```

3. **选择存储类型**
   ```
   Storage> drive
   或输入数字（通常是 15 或 16）
   ```

4. **配置 Google Application Client ID**
   ```
   client_id> （直接回车，使用默认）
   client_secret> （直接回车，使用默认）
   ```

5. **配置访问范围**
   ```
   scope> 1
   （选择 "Full access all files"）
   ```

6. **配置 root_folder_id**
   ```
   root_folder_id> （直接回车）
   ```

7. **配置 service_account_file**
   ```
   service_account_file> （直接回车）
   ```

8. **高级配置**
   ```
   Edit advanced config? (y/n)
   n
   ```

9. **自动配置**
   ```
   Use auto config? (y/n)
   y
   ```

   此时会自动打开浏览器，要求你登录 Google 账号并授权。

10. **配置团队盘**
    ```
    Configure this as a team drive? (y/n)
    n
    ```

11. **确认配置**
    ```
    y) Yes this is OK
    ```

12. **退出配置**
    ```
    q) Quit config
    ```

### 2.3 验证配置

```bash
# 列出所有远程
rclone listremotes

# 测试连接
rclone lsd gdrive:

# 查看 Google Drive 根目录文件
rclone ls gdrive: --max-depth 1
```

---

## 三、基本使用

### 3.1 常用命令

#### 列出文件

```bash
# 列出根目录
rclone ls gdrive:

# 列出指定目录
rclone ls gdrive:OpenClaw-Backups/

# 列出目录结构
rclone lsd gdrive:
```

#### 上传文件

```bash
# 上传单个文件
rclone copy /path/to/file.txt gdrive:目标文件夹/

# 上传整个目录
rclone copy /path/to/directory gdrive:目标文件夹/ --progress

# 同步目录（删除目标中多余的文件）
rclone sync /path/to/directory gdrive:目标文件夹/ --progress
```

#### 下载文件

```bash
# 下载单个文件
rclone copy gdrive:文件路径 /本地目录/

# 下载整个目录
rclone copy gdrive:远程目录/ /本地目录/ --progress
```

#### 删除文件

```bash
# 删除文件
rclone delete gdrive:文件路径

# 删除目录
rclone purge gdrive:目录路径
```

---

## 四、自动备份配置

### 4.1 备份脚本

已创建自动备份脚本：`google-drive-backup.sh`

**脚本位置：**
```
~/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置/google-drive-backup.sh
```

**脚本功能：**
- 自动备份 `~/.openclaw` 配置目录
- 自动备份 OpenClaw 工作区
- 压缩备份文件
- 上传到 Google Drive
- 清理本地临时文件

### 4.2 手动运行备份

```bash
cd ~/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置
./google-drive-backup.sh
```

### 4.3 配置定时备份

#### 方法1：使用 crontab

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 2 点备份）
0 2 * * * /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置/google-drive-backup.sh >> /tmp/openclaw-backup.log 2>&1

# 或每周日凌晨 2 点备份
0 2 * * 0 /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置/google-drive-backup.sh >> /tmp/openclaw-backup.log 2>&1
```

#### 方法2：使用 launchd（macOS 推荐）

创建 plist 文件：

```bash
cat > ~/Library/LaunchAgents/com.openclaw.backup.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置/google-drive-backup.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/openclaw-backup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/openclaw-backup.err.log</string>
</dict>
</plist>
EOF

# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.openclaw.backup.plist

# 验证任务
launchctl list | grep openclaw.backup
```

---

## 五、恢复备份

### 5.1 查看可用备份

```bash
rclone ls gdrive:OpenClaw-Backups/
```

### 5.2 下载备份文件

```bash
# 下载最新备份
rclone copy gdrive:OpenClaw-Backups/openclaw-backup-YYYYMMDD-HHMMSS.tar.gz /tmp/

# 解压备份
cd /tmp
tar -xzf openclaw-backup-YYYYMMDD-HHMMSS.tar.gz
```

### 5.3 恢复配置

```bash
# 备份当前配置（可选）
mv ~/.openclaw ~/.openclaw.old

# 恢复配置文件
cp -r /tmp/openclaw-backup-YYYYMMDD-HHMMSS/openclaw-config ~/.openclaw

# 恢复工作区
cp -r /tmp/openclaw-backup-YYYYMMDD-HHMMSS/openclaw-workspace ~/Desktop/家养小龙虾🦞/

# 重启 Gateway
openclaw gateway restart

# 验证恢复
openclaw status
```

---

## 六、高级配置

### 6.1 配置多个 Google 账号

```bash
# 添加第二个账号
rclone config

# 使用不同的名称，如 gdrive2
name> gdrive2
```

### 6.2 配置加密

```bash
# 创建加密远程
rclone config

# 选择 crypt 类型
Storage> crypt

# 指定要加密的远程
remote> gdrive:OpenClaw-Backups-Encrypted

# 设置密码
password> （输入强密码）
password2> （再次输入密码）
```

### 6.3 限速配置

```bash
# 上传限速（例如 10MB/s）
rclone copy /path/to/file gdrive: --bwlimit 10M

# 下载限速
rclone copy gdrive:file /path/ --bwlimit 10M
```

### 6.4 过滤规则

创建过滤文件 `~/.config/rclone/filter-rules.txt`：

```
# 排除日志文件
- *.log
- *.err.log

# 排除临时文件
- .DS_Store
- *.tmp

# 只包含特定文件
+ *.json
+ *.md
```

使用过滤：

```bash
rclone copy /path/to/dir gdrive: --filter-from ~/.config/rclone/filter-rules.txt
```

---

## 七、与 OpenClaw 集成

### 7.1 在 TOOLS.md 中添加 Google Drive 工具

编辑 `openclaw-workspace/TOOLS.md`，添加：

```markdown
## Google Drive 工具

### 备份到 Google Drive
使用 rclone 自动备份配置和数据到 Google Drive。

命令：
- 手动备份：`./部署与部分app配置/google-drive-backup.sh`
- 查看备份：`rclone ls gdrive:OpenClaw-Backups/`
- 恢复备份：参考 GoogleDrive配置指南.md
```

### 7.2 创建快捷命令

在 `~/.zshrc` 或 `~/.bash_profile` 中添加：

```bash
# OpenClaw Google Drive 快捷命令
alias ocbackup='~/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置/google-drive-backup.sh'
alias oclist='rclone ls gdrive:OpenClaw-Backups/'
alias ocdrive='rclone lsd gdrive:'
```

重新加载配置：

```bash
source ~/.zshrc
```

---

## 八、故障排查

### 8.1 授权失败

**症状：** 浏览器授权后仍然失败

**解决方案：**
```bash
# 删除旧配置
rclone config delete gdrive

# 重新配置
rclone config
```

### 8.2 上传速度慢

**症状：** 上传速度很慢

**解决方案：**
```bash
# 增加并发传输
rclone copy /path/to/file gdrive: --transfers 8 --checkers 16
```

### 8.3 配额限制

**症状：** 提示 "User rate limit exceeded"

**解决方案：**
```bash
# 降低传输速率
rclone copy /path/to/file gdrive: --tpslimit 10 --tpslimit-burst 0
```

### 8.4 文件未同步

**症状：** 文件上传后在 Google Drive 网页版看不到

**解决方案：**
```bash
# 等待几分钟后刷新
# 或使用 --drive-acknowledge-abuse 参数
rclone copy /path/to/file gdrive: --drive-acknowledge-abuse
```

---

## 九、安全建议

### 9.1 保护配置文件

```bash
# 限制 rclone 配置文件权限
chmod 600 ~/.config/rclone/rclone.conf
```

### 9.2 使用加密

对敏感数据使用 rclone crypt 加密后再上传。

### 9.3 定期审计

```bash
# 查看最近上传的文件
rclone ls gdrive:OpenClaw-Backups/ --max-age 7d

# 检查存储空间
rclone about gdrive:
```

### 9.4 备份 rclone 配置

```bash
# 备份 rclone 配置
cp ~/.config/rclone/rclone.conf ~/.config/rclone/rclone.conf.backup
```

---

## 十、常用命令速查

### 文件操作

```bash
# 列出文件
rclone ls gdrive:路径/

# 列出目录
rclone lsd gdrive:路径/

# 上传文件
rclone copy 本地路径 gdrive:远程路径/ --progress

# 下载文件
rclone copy gdrive:远程路径/ 本地路径 --progress

# 同步目录
rclone sync 本地路径 gdrive:远程路径/ --progress

# 删除文件
rclone delete gdrive:文件路径

# 删除目录
rclone purge gdrive:目录路径
```

### 信息查询

```bash
# 查看存储空间
rclone about gdrive:

# 查看文件详情
rclone lsl gdrive:文件路径

# 检查文件差异
rclone check 本地路径 gdrive:远程路径/

# 查看传输统计
rclone size gdrive:路径/
```

### 高级操作

```bash
# 挂载 Google Drive（需要 macFUSE）
rclone mount gdrive: ~/GoogleDrive --vfs-cache-mode writes

# 清理回收站
rclone cleanup gdrive:

# 去重文件
rclone dedupe gdrive:路径/
```

---

## 十一、性能优化

### 11.1 并发传输

```bash
# 增加并发数（默认 4）
rclone copy /path gdrive: --transfers 8

# 增加检查器数量（默认 8）
rclone copy /path gdrive: --checkers 16
```

### 11.2 缓存配置

```bash
# 使用内存缓存
rclone copy /path gdrive: --buffer-size 256M

# 使用磁盘缓存
rclone copy /path gdrive: --cache-dir /tmp/rclone-cache
```

### 11.3 断点续传

```bash
# 自动跳过已存在的文件
rclone copy /path gdrive: --ignore-existing

# 只传输新文件和修改的文件
rclone copy /path gdrive: --update
```

---

## 十二、监控与日志

### 12.1 启用详细日志

```bash
# 详细日志
rclone copy /path gdrive: -v

# 调试日志
rclone copy /path gdrive: -vv

# 保存日志到文件
rclone copy /path gdrive: --log-file /tmp/rclone.log
```

### 12.2 实时监控

```bash
# 显示传输进度
rclone copy /path gdrive: --progress

# 显示统计信息
rclone copy /path gdrive: --stats 5s
```

---

## 十三、配置总结

### 13.1 已完成配置

✅ rclone 已安装（v1.73.1）
✅ Google Drive 远程已配置（gdrive）
✅ 自动备份脚本已创建
✅ 配置文档已更新

### 13.2 配置信息

| 项目 | 值 |
|------|-----|
| rclone 版本 | v1.73.1 |
| 远程名称 | gdrive |
| 备份目录 | OpenClaw-Backups |
| 脚本路径 | ~/Desktop/家养小龙虾🦞/openclaw-workspace/部署与部分app配置/google-drive-backup.sh |
| 配置文件 | ~/.config/rclone/rclone.conf |

### 13.3 下一步操作

1. 运行 `rclone config` 完成 Google 账号授权
2. 测试备份脚本：`./google-drive-backup.sh`
3. 配置定时备份（可选）
4. 验证备份文件可正常恢复

---

## 十四、相关文档

- [OpenClaw部署技术报告.md](OpenClaw部署与部分app配置技术报告.md) - 完整部署指南
- [API_STRATEGY.md](API_STRATEGY.md) - API调用策略
- [README.md](README.md) - 配置总览

---

## 十五、参考资源

### 官方文档

- **rclone 官网：** https://rclone.org/
- **rclone 文档：** https://rclone.org/docs/
- **Google Drive 配置：** https://rclone.org/drive/
- **rclone 论坛：** https://forum.rclone.org/

### 常见问题

- **FAQ：** https://rclone.org/faq/
- **故障排查：** https://rclone.org/troubleshooting/
- **性能优化：** https://rclone.org/docs/#performance

---

**文档版本：** 1.0
**创建日期：** 2026-03-03
**维护者：** OpenClaw Team
**状态：** ✅ 已完成

🦞 **OpenClaw** - 解放双手，但绝不越过安全底线
