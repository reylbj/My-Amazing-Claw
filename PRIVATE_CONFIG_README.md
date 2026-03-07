# 私密配置文件说明

本仓库包含以下私密配置文件，已在 `.gitignore` 中排除：

- `MEMORY.md` - 长期记忆（包含凭证）
- `TOOLS.md` - 工具配置（包含API密钥）
- `USER.md` - 用户个人信息
- `HEARTBEAT.md` - 安全约束配置

## 首次使用设置

1. 复制模板文件：
```bash
cp MEMORY.md.template MEMORY.md
cp TOOLS.md.template TOOLS.md
```

2. 编辑 `MEMORY.md`，替换占位符：
   - `YOUR_WECHAT_APPID` → 你的微信公众号AppID
   - `YOUR_WECHAT_APPSECRET` → 你的微信公众号AppSecret

3. 编辑 `TOOLS.md`，替换相同的占位符

4. 这些文件只存在于本地，不会被提交到Git

## 安全提示

- ⚠️ 永远不要提交包含真实凭证的文件到公开仓库
- ⚠️ 定期检查 `.gitignore` 确保私密文件被排除
- ⚠️ 如果不小心提交了凭证，立即重置密钥并清理Git历史
