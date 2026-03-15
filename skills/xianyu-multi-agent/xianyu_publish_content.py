#!/usr/bin/env python3
"""
闲鱼发布内容的统一约束：
- 规避常见敏感/导流词
- 统一单张主题封面策略
- 统一清晰、好读、偏转化的文案结构
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


RISKY_REPLACEMENTS = [
    (r"公众号", "图文平台"),
    (r"小红书", "种草平台"),
    (r"私信", "平台沟通"),
    (r"(?i)微信|v信|vx|wx", "平台沟通"),
    (r"(?i)qq|Q\s*Q", "平台沟通"),
    (r"(?i)支付宝|zfb", "平台担保"),
    (r"银行卡|卡号|转账", "平台担保"),
    (r"手机号|电话|联系我|加我|私聊", "平台沟通"),
    (r"线下|绕过平台|脱离平台", "平台内"),
    (r"最便宜|全网最低|最低价", "价格透明"),
    (r"稳赚|包过|百分百|绝对", "尽量优化"),
    (r"破解版|破解", "正式版"),
    (r"洗稿", "内容优化"),
    (r"代写", "撰写支持"),
    (r"爆文", "高转化内容"),
]

TITLE_FALLBACK_SUFFIX = "｜需求明确｜交付清晰"


def build_publish_prompt(service_type: str) -> str:
    return f"""
你是一个懂闲鱼审核规则、也懂高转化服务型商品文案的运营。

请为下面的服务生成一份“可直接发布到闲鱼 goofish 新版页面”的文案：
服务类型：{service_type}

必须同时满足这些要求：
1. 严格规避审核风险，不要出现任何导流/联系方式/支付绕平台/绝对化承诺/灰产/违规服务表述。
2. 标题要吸睛但克制，18-28字，结构清晰，可用 `｜` 分隔，不要浮夸，不要用“最便宜/包过/全网最低/稳赚/破解版/代写/爆文”等敏感或高风险词。
3. 描述必须明确需求、排版美观、适合直接粘贴。统一输出成以下结构：
   开场一句（1行）

   【适合需求】
   • 需求1
   • 需求2
   • 需求3

   【交付内容】
   • 交付1
   • 交付2
   • 交付3

   【服务亮点】
   • 亮点1
   • 亮点2
   • 亮点3

   【下单前请发】
   • 信息1
   • 信息2
   • 信息3
4. 描述总长度控制在 160-320 字之间，中文为主，不要 emoji，不要夸张标点，不要废话。
5. 价格给一个真实、容易成交的起步价。
6. 标签给 3 个，必须安全、通用、和服务强相关。

只返回 JSON：
{{
  "title": "标题",
  "description": "描述",
  "price": "价格",
  "tags": ["标签1", "标签2", "标签3"]
}}
""".strip()


def _apply_replacements(text: str) -> str:
    result = text or ""
    for pattern, replacement in RISKY_REPLACEMENTS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _clean_line(text: str) -> str:
    text = _apply_replacements(text or "")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[【】<>「」『』]", "", text)
    return text.strip()


def _clean_title(text: str, service_type: str) -> str:
    safe_service = _clean_line(service_type).replace("代写", "撰写支持")
    standard_title = f"{safe_service}｜需求明确｜交付清晰"
    title = _clean_line(text).replace("\n", " ")
    title = re.sub(r"[^\w\u4e00-\u9fff｜/·\-\s]", "", title)
    title = re.sub(r"\s+", "", title)
    if not title:
        title = standard_title
    if len(title) < 10:
        title = standard_title
    if title.count("｜") > 2 or "平台沟通" in title or title.endswith("平台"):
        title = standard_title
    if len(title) > 28:
        title = title[:28]
    return title


def _pick_bullets(lines: Iterable[str], defaults: Sequence[str], count: int = 3) -> List[str]:
    cleaned: List[str] = []
    for line in lines:
        item = re.sub(r"^[\-\d\.\s•]+", "", _clean_line(line))
        if len(item) > 28:
            continue
        if item and item not in cleaned:
            cleaned.append(item)
    for item in defaults:
        safe_item = _clean_line(item)
        if safe_item and safe_item not in cleaned:
            cleaned.append(safe_item)
    return cleaned[:count]


def _default_description(service_type: str) -> str:
    safe_service = _clean_line(service_type).replace("代写", "撰写支持")
    return (
        f"想把{safe_service}需求讲清楚、交付更省心，可以直接拍下沟通。\n\n"
        "【适合需求】\n"
        "• 种草平台内容策划与整理\n"
        "• 图文平台内容结构梳理\n"
        "• 商品详情页文案优化\n\n"
        "【交付内容】\n"
        "• 1版可直接使用的完整文案\n"
        "• 重点卖点与结构梳理\n"
        "• 1次细节微调\n\n"
        "【服务亮点】\n"
        "• 先确认需求再开写，减少返工\n"
        "• 表达清楚，适合直接复制使用\n"
        "• 交付节奏明确，沟通直接\n\n"
        "【下单前请发】\n"
        "• 产品或业务信息\n"
        "• 目标人群与使用场景\n"
        "• 希望语气与交付时间"
    )


def _clean_description(text: str, service_type: str) -> str:
    raw = _clean_line(text)
    if not raw:
        return _default_description(service_type)

    sections = ["【适合需求】", "【交付内容】", "【服务亮点】", "【下单前请发】"]
    if all(section in raw for section in sections):
        return raw

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    safe_service = _clean_line(service_type).replace("代写", "撰写支持")
    opener = lines[0] if lines else f"想把{safe_service}需求讲清楚、交付更省心，可以直接拍下沟通。"
    opener = opener.rstrip("。；;，,") + "。"

    payload_lines = lines[1:] if len(lines) > 1 else []
    needs = _pick_bullets(
        payload_lines,
        [
            "种草平台内容策划与整理",
            "图文平台内容结构梳理",
            "商品详情页文案优化",
        ],
    )
    deliverables = _pick_bullets(
        payload_lines,
        [
            "1版可直接使用的完整文案",
            "重点卖点与结构梳理",
            "1次细节微调",
        ],
    )
    advantages = _pick_bullets(
        payload_lines,
        [
            "先确认需求再开写，减少返工",
            "表达清楚，适合直接复制使用",
            "交付节奏明确，沟通直接",
        ],
    )
    requests = _pick_bullets(
        payload_lines,
        [
            "产品或业务信息",
            "目标人群与使用场景",
            "希望语气与交付时间",
        ],
    )

    return "\n".join(
        [
            opener,
            "",
            "【适合需求】",
            *(f"• {item}" for item in needs),
            "",
            "【交付内容】",
            *(f"• {item}" for item in deliverables),
            "",
            "【服务亮点】",
            *(f"• {item}" for item in advantages),
            "",
            "【下单前请发】",
            *(f"• {item}" for item in requests),
        ]
    )


def _clean_price(value: object) -> str:
    text = str(value or "").strip()
    match = re.search(r"\d+(?:\.\d{1,2})?", text)
    if not match:
        return "19.9"
    price = float(match.group(0))
    if price <= 0:
        price = 19.9
    if price > 9999:
        price = 9999
    normalized = f"{price:.2f}".rstrip("0").rstrip(".")
    return normalized


def _clean_tags(tags: object, service_type: str) -> List[str]:
    items = tags if isinstance(tags, list) else []
    cleaned: List[str] = []
    for item in items:
        tag = _clean_line(str(item)).replace(" ", "")
        if not tag:
            continue
        if len(tag) > 8:
            tag = tag[:8]
        if tag not in cleaned:
            cleaned.append(tag)
    safe_service = _clean_line(service_type).replace("代写", "撰写支持").replace("服务", "")
    fallbacks = [safe_service[:8], "文案优化", "内容整理"]
    for tag in fallbacks:
        if tag and tag not in cleaned:
            cleaned.append(tag)
    return cleaned[:3]


def normalize_publish_content(content: Dict[str, object], service_type: str) -> Dict[str, object]:
    return {
        "title": _clean_title(str(content.get("title", "")), service_type),
        "description": _clean_description(str(content.get("description", "")), service_type),
        "price": _clean_price(content.get("price")),
        "tags": _clean_tags(content.get("tags"), service_type),
    }


def select_cover_images(candidate_paths: Sequence[str], workdir: Optional[str] = None) -> List[str]:
    base_dir = Path(workdir or os.getcwd())
    existing: List[str] = []

    for raw_path in candidate_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = base_dir / path
        if path.exists():
            existing.append(str(path.resolve()))

    if existing:
        return [existing[0]]

    defaults = [
        base_dir / "data" / "default_publish_cover.png",
        base_dir / "data" / "publish_preview.png",
    ]
    for path in defaults:
        if path.exists():
            return [str(path.resolve())]

    image_dir = base_dir / "images"
    blocked_keywords = ("qr", "wechat", "wx_", "alipay", "pay")
    if image_dir.is_dir():
        for path in sorted(image_dir.iterdir()):
            lowered = path.name.lower()
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            if any(keyword in lowered for keyword in blocked_keywords):
                continue
            return [str(path.resolve())]

    return []
