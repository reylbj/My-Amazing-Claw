# 微信公众号IP白名单配置

## 当前状态

✅ AppID 和 AppSecret 正确
❌ IP地址未加入白名单

**你的公网IP**: `81.79.171.56`

## 添加IP白名单步骤

1. 访问 https://mp.weixin.qq.com
2. 登录你的公众号
3. 左侧菜单：设置与开发 → 基本配置
4. 找到"IP白名单"部分
5. 点击"修改"
6. 添加IP：`81.79.171.56`
7. 保存

## 添加后测试

```bash
cd /Users/a8/Desktop/家养小龙虾🦞/openclaw-workspace/scripts
WECHAT_APPID="wx56412af2e7b23952" WECHAT_APPSECRET="WECHAT_APPSECRET_REDACTED" python3 wechat_draft.py
```

成功会显示：
```
✅ 连接成功，Token前20位: 67_xxxxxxxxxxxxx...
```

---

**添加完白名单后告诉我，我帮你测试。**
