# 微信公众号API配置指南

## 安全警告

**你的 AppSecret 已在对话中暴露，必须立即重置！**

## 第一步：重置 AppSecret（必须）

1. 访问 https://mp.weixin.qq.com
2. 设置与开发 → 基本配置
3. AppSecret → 点击"重置"
4. 验证身份后获取新的 AppSecret
5. **立即复制保存**（只显示一次）

## 第二步：配置环境变量

重置后，编辑配置文件：

```bash
nano ~/.zshrc
```

找到最后添加的这两行，替换为新的 AppSecret：

```bash
export WECHAT_APPID="wx56412af2e7b23952"
export WECHAT_APPSECRET="你重置后的新AppSecret"  # 替换这里
```

保存后生效：

```bash
source ~/.zshrc
```

## 第三步：测试连接

```bash
cd /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/scripts
python3 wechat_draft.py
```

成功会显示：
```
✅ 连接成功，Token前20位: 67_xxxxxxxxxxxxx...
```

## 第四步：配置IP白名单

1. 微信公众平台 → 基本配置 → IP白名单
2. 添加你的公网IP：

```bash
curl ifconfig.me
```

3. 将显示的IP添加到白名单

## 使用方法

### Python调用示例

```python
from scripts.wechat_draft import push_draft

# 推送文章到草稿箱
media_id = push_draft(
    title="今日AI简报",
    content="<p>这是文章内容，支持HTML格式</p>",
    author="RaysPianoLive",
    digest="这是摘要"
)
print(f"草稿已创建，media_id: {media_id}")
```

### 集成到AI员工

在 `SKILLS.md` 中的选题官skill，添加推送逻辑：

```python
# 生成初稿后自动推送
from scripts.wechat_draft import push_draft

draft_content = ai_generate_article(topic)
media_id = push_draft(
    title=draft_content['title'],
    content=draft_content['content'],
    author="RaysPianoLive"
)
```

## 重要限制

**你的账号类型**：需要确认是否为认证服务号

检查方法：
1. 登录公众平台
2. 查看左上角账号类型
3. 如果是"订阅号"或"未认证服务号"，**无法使用草稿箱API**

| 功能 | 订阅号 | 未认证服务号 | 认证服务号 |
|------|--------|-------------|-----------|
| 草稿箱API | ❌ | ❌ | ✅ |
| 群发API | ✅ 1次/天 | ❌ | ✅ 4次/月 |
| 认证费用 | 免费 | 免费 | 300元/年 |

**如果不是认证服务号**：
- 方案A：升级为认证服务号（需企业资质，300元/年）
- 方案B：AI生成内容保存到本地，手动复制到公众号后台

## 安全检查清单

- [ ] 已重置 AppSecret
- [ ] 环境变量已配置（不在代码中硬编码）
- [ ] IP白名单已添加
- [ ] 测试连接成功
- [ ] 确认账号类型支持草稿箱API
- [ ] 旧的 AppSecret 已失效

---

**下一步**：重置 AppSecret 后告诉我，我帮你测试连接。
