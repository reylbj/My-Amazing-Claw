# Token优化指南 - 降低API成本的核心策略

## 概述
本指南提供了降低OpenClaw API调用成本的实战策略，通过优化系统提示词、使用QMD、控制Heartbeat频率等方法，可以将Token消耗降低60-90%。

---

## 第一招：优化上下文窗口

### 问题分析
每次API调用都会发送完整的对话历史，随着对话增长，Token消耗急剧上升。

### 优化策略

#### 1. 使用流式输出
```yaml
# 在配置中启用流式输出
streaming: true
```
**效果**：减少等待时间，提升用户体验

#### 2. 限制历史对话长度
```yaml
# 只保留最近10轮对话
max_history_turns: 10
```
**效果**：减少30-50% Token消耗

#### 3. 定期清理会话
```bash
# 每周清理一次旧会话
openclaw sessions clean --older-than 7d
```

---

## 第二招：精简系统提示词

### 目标
将系统提示词从13000+ Token压缩到3000-5000 Token

### 优化文件

#### AGENTS.md
**优化前**：212行，包含大量群聊规则、TTS配置、详细说明
**优化后**：压缩到800 Token以内

**删除内容**：
- 不使用的群聊规则
- TTS语音配置（如果不用）
- 冗长的示例说明
- 重复的功能描述

#### SOUL.md
**优化前**：36行，包含大段性格描述
**优化后**：精简到核心理念

**保留内容**：
- 核心行为准则（2-3句）
- 关键安全边界
- 基本工作方式

**删除内容**：
- 冗长的性格描述
- 重复的说明
- 非必要的示例

#### MEMORY.md
**优化策略**：
- 定期归档过期内容
- 只保留当前活跃的记忆
- 使用简洁的表达方式

**建议**：
```bash
# 每月归档一次
mv memory/MEMORY.md memory/archive/MEMORY-2026-02.md
# 创建新的精简版本
```

---

## 第三招：上QMD（核武器级优化）

### 什么是QMD
QMD（Quantum Memory Database）是Shopify联合创始人Tobi开发的本地语义搜索引擎，从OpenClaw 2026.2.2版本开始内置支持。

### 工作原理
传统方式：整个MEMORY.md文件（可能几千Token）全部塞进上下文
QMD方式：先在本地用语义搜索找到最相关的2-3句话，只传递这些精准内容

### 效果数据
- Token消耗降低：90-99%
- 响应速度提升：5-50倍
- 精准度提高：93%（因为AI不再被无关信息干扰）

### 安装使用
```bash
# OpenClaw 2026.2.2以上版本自动内置
openclaw --version  # 检查版本

# 启用QMD
openclaw configure
# 选择 memory -> enable QMD

# 验证
openclaw status | grep QMD
```

### 适用场景
- 记忆文件已膨胀到几千Token以上
- 需要频繁访问历史记忆
- 对响应速度有要求

**重要**：QMD完全本地运行，零API成本，零隐私泄露

---

## 第四招：控制Heartbeat频率

### 问题分析
默认每5-10分钟检查一次邮件、日历等，每次检查都要重新注入完整上下文。

### 优化策略

#### 1. 调整检查频率
```yaml
# 在配置中调整
heartbeat:
  interval: 30m  # 从10分钟改到30分钟

system_checks:
  version_check: 1  # 从3次/天改到1次/天
```

#### 2. 合并检查任务
**优化前**：
- 检查邮件（单独调用）
- 检查日历（单独调用）
- 检查待办（单独调用）

**优化后**：
```yaml
# 创建"每日晨报"任务
morning_briefing:
  schedule: "0 8 * * *"  # 每天8点
  tasks:
    - check_email
    - check_calendar
    - check_todos
```

**效果**：节省75%的上下文注入成本

#### 3. 按需推送
```yaml
notifications:
  mode: "on_demand"  # 而非"定时播报"
  triggers:
    - urgent_email
    - calendar_reminder
    - important_mention
```

---

## 第五招：多Agent分流

### 核心思路
不同复杂度的任务分配给不同的Agent，每个Agent有独立的会话、记忆和工作空间。

### 实施方案

#### 1. 创建专用Agent
```bash
# 创建简单任务Agent（使用Sonnet）
openclaw agent create --name simple-tasks --model claude-sonnet-4.6

# 创建复杂任务Agent（使用Opus）
openclaw agent create --name complex-tasks --model claude-opus-4.6

# 创建翻译Agent（使用Haiku）
openclaw agent create --name translator --model claude-haiku-4.6
```
```

#### 3. 路由规则
```yaml
routing:
  rules:
    - pattern: "翻译|translate"
      agent: translator
    - pattern: "代码|架构|设计"
      agent: complex-tasks
    - pattern: ".*"  # 默认
      agent: simple-tasks
```

### 优势
1. **避免记忆污染**：每个Agent记忆独立，不会互相干扰
2. **成本优化**：简单任务用便宜模型
3. **性能提升**：轻量级Agent响应更快
4. **配额管理**：分散配额使用，避免单点耗尽

---

## 综合优化案例

### 案例：日常办公助手

#### 优化前
- 系统提示词：13000 Token
- 每次调用：15000-20000 Token
- 每日配额消耗：Flash 150次（60%）

#### 优化步骤
1. 精简AGENTS.md和SOUL.md → 3000 Token
2. 启用QMD → 只传递相关记忆（200 Token）
3. Heartbeat从10分钟改到30分钟 → 减少66%调用
4. 创建邮件分类专用Agent（Flash-Lite）

#### 优化后
- 系统提示词：3000 Token
- 每次调用：5000-8000 Token（减少60%）
- 每日配额消耗：Flash 50次（20%），Flash-Lite 60次（6%）

#### 效果
- Token消耗降低：70%
- 配额使用降低：67%
- 响应速度提升：3倍
- 成本节省：显著

---

## 监控与调整

### 监控指标
```bash
# 查看Token使用统计
openclaw stats --token-usage

# 查看Agent使用分布
openclaw stats --agent-usage

# 查看配额使用趋势
openclaw stats --quota-trend
```

### 调整建议
1. **每周检查**：Token使用趋势
2. **每月优化**：清理冗余记忆
3. **季度审查**：Agent配置合理性

---

## 最佳实践总结

### 必做优化（高优先级）
1. ✅ 精简系统提示词（AGENTS.md, SOUL.md）
2. ✅ 限制历史对话长度（max 10轮）
3. ✅ 调整Heartbeat频率（30分钟）

### 推荐优化（中优先级）
1. ✅ 启用QMD（如果记忆>2000 Token）
2. ✅ 合并定时任务
3. ✅ 定期清理会话

### 进阶优化（低优先级）
1. ✅ 多Agent分流
2. ✅ 自定义路由规则
3. ✅ 细粒度配额管理

---

## 预期效果

### 轻度优化（只做必做项）
- Token消耗降低：40-50%
- 配额节省：30-40%
- 实施时间：1小时

### 中度优化（必做+推荐）
- Token消耗降低：60-70%
- 配额节省：50-60%
- 实施时间：2-3小时

### 深度优化（全部实施）
- Token消耗降低：80-90%
- 配额节省：70-80%
- 实施时间：4-6小时

---

## 常见问题

### Q: QMD会影响AI的理解能力吗？
A: 不会。官方数据显示精准度反而提高到93%，因为AI不再被无关信息干扰。

### Q: 多Agent会增加管理复杂度吗？
A: 初期会有学习成本，但长期来看收益远大于成本。建议从2-3个Agent开始。

### Q: 精简提示词会影响AI的性格吗？
A: 不会。AI不需要长篇大论来定义性格，2-3句核心准则就够了。

### Q: 优化后还能恢复吗？
A: 可以。建议优化前备份所有配置文件。

---

**版本**：1.0.0
**更新日期**：2026-02-28
**适用版本**：OpenClaw 2026.2.2+

🦞 **OpenClaw** - 解放双手，但绝不越过安全底线
