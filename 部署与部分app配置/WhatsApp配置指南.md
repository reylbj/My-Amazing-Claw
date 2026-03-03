# WhatsApp 配置指南

## 概述
本指南详细说明如何在OpenClaw中配置WhatsApp频道，让你可以通过WhatsApp与AI助手互动。

---

## 前提条件

### 系统要求
- OpenClaw 已安装并运行
- Gateway 服务正常运行
- 有可用的手机和WhatsApp账号

### 检查环境
```bash
# 检查OpenClaw版本
openclaw --version

# 检查Gateway状态
openclaw gateway status
```

---

## 配置步骤

### 步骤1：启用WhatsApp插件

打开终端，输入配置命令：
```bash
openclaw configure
```

在配置界面中：
1. 选择 **channels**（通道）
2. 选择 **WhatsApp**

### 步骤2：扫描二维码

系统会生成一个二维码。

**在手机上操作**：
1. 打开 WhatsApp 应用
2. 点击右上角的 **三个点** 或 **设置**
3. 选择 **已连接的设备**（或 **WhatsApp Web**）
4. 点击 **关联设备**
5. 扫描终端显示的二维码

### 步骤3：确认关联

扫描后：
1. 手机上会显示"关联一个新设备"
2. 确认关联
3. 手机上会显示你关联了一个 **Chrome 浏览器**（OpenClaw模拟浏览器登录）

### 步骤4：填写手机号

在OpenClaw配置界面中：
```bash
# 输入你的手机号（国际格式）
Phone: +86 138 xxxx xxxx  # 中国
Phone: +1 xxx xxx xxxx     # 美国
Phone: +44 xxxx xxxx       # 英国
```

完成后显示 **linked**（已连接）即可退出。

---

## 使用方法

### 开始对话

1. 在手机上打开 WhatsApp
2. 使用自己的手机号搜索自己
3. 给自己发送消息
4. OpenClaw 会自动回复

### 示例对话
```
你: 你好
AI: 你好！我是你的AI助手，有什么可以帮你的吗？

你: 帮我总结一下今天的邮件
AI: [AI会读取你的邮件并生成摘要]

你: 提醒我明天下午3点开会
AI: 好的，已为你设置提醒：明天下午3点开会
```

---

## 配置文件

### 查看配置
```bash
cat ~/.openclaw/openclaw.json | grep -A 10 whatsapp
```

### 配置示例
```json
{
  "channels": {
    "whatsapp": {
      "enabled": true,
      "dmPolicy": "pairing",
      "streaming": "off",
      "phoneNumber": "+86138xxxxxxxx"
    }
  }
}
```

---

## 功能对比

### WhatsApp vs Telegram

| 功能 | WhatsApp | Telegram |
|------|----------|----------|
| 基础对话 | ✅ | ✅ |
| 文件发送 | ✅ | ✅ |
| 语音消息 | ✅ | ✅ |
| 群组支持 | ⚠️ 有限 | ✅ 完整 |
| Bot命令 | ❌ | ✅ |
| 内联查询 | ❌ | ✅ |
| 流式输出 | ❌ | ✅ |
| 配置复杂度 | 🟢 简单 | 🟡 中等 |

### 推荐使用场景

**适合使用WhatsApp**：
- 日常快速对话
- 简单任务处理
- 不需要高级功能
- 已有WhatsApp使用习惯

**适合使用Telegram**：
- 需要群组协作
- 需要Bot命令
- 需要流式输出
- 需要高级功能

---

## 安全配置

### 配对策略

默认使用 `dmPolicy: "pairing"`，这意味着：
- 只有你自己可以与AI对话
- 其他人无法访问你的AI助手
- 保护你的隐私和数据

### 修改配对策略
```bash
openclaw configure
# 选择 channels -> whatsapp -> dmPolicy
# 可选：pairing（需配对）、open（开放）、allowlist（白名单）
```

**建议**：保持 `pairing` 模式以确保安全

---

## 故障排查

### 问题1：无法生成二维码

**症状**：运行配置命令后没有显示二维码

**解决方案**：
```bash
# 1. 检查Gateway是否运行
openclaw gateway status

# 2. 重启Gateway
openclaw gateway restart

# 3. 重新配置
openclaw configure
```

### 问题2：扫码后无法连接

**症状**：扫码成功但显示连接失败

**解决方案**：
```bash
# 1. 检查网络连接
ping google.com

# 2. 检查防火墙设置
# 确保OpenClaw可以访问WhatsApp服务器

# 3. 查看日志
openclaw logs --follow
```

### 问题3：AI不回复消息

**症状**：发送消息后没有回复

**解决方案**：
```bash
# 1. 检查频道状态
openclaw channels status

# 2. 检查配对状态
openclaw pairing list

# 3. 查看实时日志
openclaw logs --follow

# 4. 重启服务
openclaw gateway restart
```

### 问题4：连接断开

**症状**：使用一段时间后连接断开

**解决方案**：
```bash
# 1. 检查手机WhatsApp是否在线
# 2. 重新扫码连接
openclaw configure
# 选择 channels -> whatsapp -> reconnect
```

---

## 高级配置

### 启用通知
```json
{
  "channels": {
    "whatsapp": {
      "notifications": {
        "enabled": true,
        "sound": true,
        "vibrate": true
      }
    }
  }
}
```

### 自定义回复延迟
```json
{
  "channels": {
    "whatsapp": {
      "responseDelay": 1000,  // 毫秒
      "typingIndicator": true
    }
  }
}
```

### 消息过滤
```json
{
  "channels": {
    "whatsapp": {
      "filters": {
        "ignoreGroups": true,      // 忽略群组消息
        "ignoreBroadcast": true,   // 忽略广播消息
        "minMessageLength": 2      // 最小消息长度
      }
    }
  }
}
```

---

## 使用技巧

### 1. 快速命令
虽然WhatsApp不支持Bot命令，但你可以使用自然语言：
```
"帮我总结邮件" 而不是 "/summarize-email"
"查看日程" 而不是 "/calendar"
"提醒我..." 而不是 "/remind"
```

### 2. 语音消息
可以发送语音消息，AI会自动转录并回复：
```
[语音消息] "明天的天气怎么样？"
AI: 明天北京晴，温度15-25度，适合出行。
```

### 3. 发送文件
可以发送文档、图片等文件让AI分析：
```
[发送PDF文件]
你: 帮我总结这个文档
AI: [生成文档摘要]
```

---

## 多设备支持

### 同时使用多个设备
WhatsApp支持多设备登录，你可以：
1. 手机上使用WhatsApp
2. 电脑上使用WhatsApp Web
3. OpenClaw作为另一个设备

**注意**：最多支持4个关联设备

### 切换设备
如果需要在另一台电脑上配置：
```bash
# 在新电脑上
openclaw configure
# 重新扫码即可
```

---

## 维护建议

### 定期检查
```bash
# 每周检查一次连接状态
openclaw channels status

# 查看使用统计
openclaw stats --channel whatsapp
```

### 日志管理
```bash
# 查看WhatsApp相关日志
openclaw logs --channel whatsapp --limit 100

# 清理旧日志
openclaw logs clean --older-than 30d
```

---

## 与Telegram对比配置

### 如果你已经配置了Telegram

**同时使用两个频道**：
```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "your-telegram-token"
    },
    "whatsapp": {
      "enabled": true,
      "phoneNumber": "+86138xxxxxxxx"
    }
  }
}
```

**选择主频道**：
```bash
openclaw configure
# 选择 channels -> default -> whatsapp 或 telegram
```

---

## 常见问题

### Q: WhatsApp会消耗手机流量吗？
A: 不会。OpenClaw直接连接WhatsApp服务器，不经过你的手机。

### Q: 手机关机后还能用吗？
A: 可以。关联后，OpenClaw独立运行，不依赖手机在线。

### Q: 可以在群组中使用吗？
A: 功能有限。建议使用Telegram进行群组协作。

### Q: 如何断开连接？
```bash
openclaw channels remove --channel whatsapp
# 或在手机WhatsApp中移除关联设备
```

### Q: 配置比Telegram简单吗？
A: 是的。WhatsApp不需要创建Bot，只需扫码即可。

---

## 下一步

### 配置完成后
1. ✅ 测试基础对话功能
2. ✅ 配置安全策略（参考 HEARTBEAT.md）
3. ✅ 设置API配额管理（参考 API_STRATEGY.md）
4. ✅ 优化Token使用（参考 Token优化指南.md）

### 进阶配置
- 配置多Agent分流
- 设置自动化任务
- 集成其他服务

---

## 相关文档

- [Telegram配置指南](../OpenClaw部署技术报告.md) - Telegram配置说明
- [HEARTBEAT.md](../HEARTBEAT.md) - 安全约束配置
- [API_STRATEGY.md](API_STRATEGY.md) - API调用策略
- [README.md](../README.md) - 完整使用指南

---

**版本**：1.0.0
**更新日期**：2026-02-28
**适用版本**：OpenClaw 2026.2.2+

🦞 **OpenClaw** - 解放双手，但绝不越过安全底线
