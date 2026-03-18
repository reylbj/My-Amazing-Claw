#!/usr/bin/env python3
"""
xiaohongshu-send 发布辅助脚本

能力：
1) 发布参数校验（标题/正文/图片路径/标签）
2) 检查登录状态
3) 调用发布接口
4) MCP 可用性验证（initialize/tools/list/tools/call）
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import error, request


VISIBILITY_SET = {"公开可见", "仅自己可见", "仅互关好友可见"}


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def candidate_xhs_homes() -> List[Path]:
    env = os.getenv("XHS_HOME")
    candidates: List[Path] = []
    if env:
        candidates.append(Path(env).expanduser())

    root = workspace_root()
    candidates.extend(
        [
            root / "skills" / "xiaohongshu-send",
            root / "xiaohongshu-send",
        ]
    )
    return candidates


def default_xhs_home() -> Path:
    candidates = candidate_xhs_homes()
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def calc_title_length(text: str) -> int:
    # 与官方项目标题长度规则保持一致：ASCII 按 1，非 ASCII 按 2，最后除以 2 向上取整
    byte_len = 0
    for ch in text:
        byte_len += 1 if ord(ch) <= 127 else 2
    return (byte_len + 1) // 2


def has_cjk_path_chars(path: str) -> bool:
    return re.search(r"[\u4e00-\u9fff]", path) is not None


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    content = data.get("content")
    if content is None:
        content = data.get("description")
    if content is None:
        content = data.get("desc", "")

    images = data.get("images")
    if images is None:
        images = data.get("image_urls", [])

    tags = data.get("tags")
    if tags is None:
        tags = data.get("topics")
    if tags is None:
        tags = data.get("hashtags", [])

    visibility = data.get("visibility")
    if visibility is None and "is_private" in data:
        visibility = "仅自己可见" if bool(data.get("is_private")) else "公开可见"

    normalized = {
        "title": data.get("title", ""),
        "content": content,
        "images": images,
        "tags": tags,
    }

    if "schedule_at" in data:
        normalized["schedule_at"] = data["schedule_at"]
    if "is_original" in data:
        normalized["is_original"] = data["is_original"]
    if visibility is not None:
        normalized["visibility"] = visibility

    return normalized


def validate_schedule_at(schedule_at: str) -> Tuple[bool, str]:
    try:
        iso_input = schedule_at.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(iso_input)
    except ValueError:
        return False, "schedule_at 格式不合法，需为 ISO8601（例如 2026-03-03T10:00:00+08:00）"

    if parsed.tzinfo is None:
        return False, "schedule_at 必须带时区"

    now = dt.datetime.now(dt.timezone.utc)
    in_one_hour = now + dt.timedelta(hours=1)
    in_14_days = now + dt.timedelta(days=14)
    parsed_utc = parsed.astimezone(dt.timezone.utc)

    if parsed_utc < in_one_hour:
        return False, "schedule_at 必须至少晚于当前时间 1 小时"
    if parsed_utc > in_14_days:
        return False, "schedule_at 不能晚于当前时间 14 天"
    return True, ""


def validate_payload(payload: Dict[str, Any], check_urls: bool = False) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    title = payload.get("title")
    content = payload.get("content")
    images = payload.get("images")
    tags = payload.get("tags")

    if not isinstance(title, str) or not title.strip():
        errors.append("title 必填且必须为非空字符串")
    else:
        title_len = calc_title_length(title)
        if title_len > 20:
            errors.append(f"title 长度超限：当前 {title_len}，上限 20")

    if not isinstance(content, str) or not content.strip():
        errors.append("content/description 必填且必须为非空字符串")
    else:
        # README 写明正文上限 1000，这里提前校验，避免发布阶段失败
        content_len = len(content)
        if content_len > 1000:
            errors.append(f"content 长度超限：当前 {content_len}，上限 1000")

    if not isinstance(images, list) or len(images) == 0:
        errors.append("images/image_urls 必填，至少 1 张")
    else:
        for i, image in enumerate(images, start=1):
            if not isinstance(image, str) or not image.strip():
                errors.append(f"images[{i}] 不能为空")
                continue
            s = image.strip()
            if s.startswith("http://") or s.startswith("https://"):
                if check_urls:
                    ok, msg = check_url_accessible(s)
                    if not ok:
                        warnings.append(f"images[{i}] URL 可能不可访问: {msg}")
            else:
                p = Path(s)
                if not p.is_absolute():
                    errors.append(f"images[{i}] 必须是本地绝对路径或 URL: {s}")
                elif not p.exists() or not p.is_file():
                    errors.append(f"images[{i}] 本地文件不存在: {s}")
                if has_cjk_path_chars(s):
                    warnings.append(f"images[{i}] 路径包含中文，官方提示可能导致上传失败: {s}")

    if tags is None:
        tags = []
    if not isinstance(tags, list):
        errors.append("tags 必须为数组")
    else:
        for i, tag in enumerate(tags, start=1):
            if not isinstance(tag, str) or not tag.strip():
                errors.append(f"tags[{i}] 必须为非空字符串")
        if len(tags) > 10:
            warnings.append(f"tags 数量为 {len(tags)}，服务端会截断到前 10 个")
    if isinstance(images, list) and len(images) > 7:
        warnings.append(f"images 数量为 {len(images)}，当前链路建议控制在 7 张以内以提升稳定性")

    visibility = payload.get("visibility")
    if visibility is not None and visibility not in VISIBILITY_SET:
        errors.append(f"visibility 不合法: {visibility}，可选值: {sorted(VISIBILITY_SET)}")

    schedule_at = payload.get("schedule_at")
    if schedule_at is not None:
        if not isinstance(schedule_at, str) or not schedule_at.strip():
            errors.append("schedule_at 必须是 ISO8601 字符串")
        else:
            ok, msg = validate_schedule_at(schedule_at.strip())
            if not ok:
                errors.append(msg)

    return errors, warnings


def check_url_accessible(url: str) -> Tuple[bool, str]:
    req = request.Request(url=url, method="HEAD")
    try:
        with request.urlopen(req, timeout=12) as resp:
            status = getattr(resp, "status", 200)
            if 200 <= status < 400:
                return True, f"HTTP {status}"
            return False, f"HTTP {status}"
    except Exception as ex:  # noqa: BLE001
        return False, str(ex)


def http_json_full(
    method: str,
    url: str,
    body: Dict[str, Any] | None = None,
    extra_headers: Dict[str, str] | None = None,
    timeout: int = 45,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    data = None
    headers = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            payload = json.loads(content) if content else {}
            return payload, dict(resp.headers.items())
    except error.HTTPError as ex:
        content = ex.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> HTTP {ex.code}: {content}") from ex
    except error.URLError as ex:
        raise RuntimeError(f"{method} {url} -> 网络错误: {ex}") from ex
    except socket.timeout as ex:
        raise RuntimeError(f"{method} {url} -> 请求超时（{timeout}s）") from ex


def http_json(
    method: str,
    url: str,
    body: Dict[str, Any] | None = None,
    extra_headers: Dict[str, str] | None = None,
    timeout: int = 45,
) -> Dict[str, Any]:
    payload, _ = http_json_full(method, url, body, extra_headers, timeout)
    return payload


def mcp_request(
    base_url: str,
    method: str,
    params: Dict[str, Any],
    req_id: int | None = None,
    session_id: str | None = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    headers = {
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    body: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    if req_id is not None:
        body["id"] = req_id

    return http_json_full("POST", f"{base_url.rstrip('/')}/mcp", body, headers)


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_validate(args: argparse.Namespace) -> int:
    payload = normalize_payload(load_json(Path(args.payload)))
    errors, warnings = validate_payload(payload, check_urls=args.check_urls)

    print("=== Normalized Payload ===")
    print_json(payload)
    print("\n=== Validation Result ===")
    print(f"errors={len(errors)}, warnings={len(warnings)}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"- {w}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"- {e}")
        return 1

    print("Payload 校验通过")
    return 0


def cmd_check_login(args: argparse.Namespace) -> int:
    url = f"{args.base_url.rstrip('/')}/api/v1/login/status"
    resp = http_json("GET", url)
    print_json(resp)
    try:
        logged_in = bool(resp.get("data", {}).get("is_logged_in"))
    except Exception:  # noqa: BLE001
        logged_in = False
    return 0 if logged_in else 2


def cmd_publish(args: argparse.Namespace) -> int:
    payload = normalize_payload(load_json(Path(args.payload)))
    errors, warnings = validate_payload(payload, check_urls=args.check_urls)

    if warnings:
        for w in warnings:
            print(f"[warning] {w}")

    if errors:
        for e in errors:
            print(f"[error] {e}")
        return 1

    if args.dry_run:
        print("dry-run 模式：仅校验，不调用发布接口")
        print_json(payload)
        return 0

    url = f"{args.base_url.rstrip('/')}/api/v1/publish"
    resp = http_json("POST", url, payload, timeout=args.timeout)
    print_json(resp)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    xhs_home = default_xhs_home()
    mcp_bin = xhs_home / "bin" / "xiaohongshu-mcp"
    login_bin = xhs_home / "bin" / "xiaohongshu-login"

    print("=== Step 0: Environment ===")
    print(f"- xhs_home: {xhs_home}")
    print(f"- mcp_bin_exists: {mcp_bin.exists()}")
    print(f"- login_bin_exists: {login_bin.exists()}")
    if not (mcp_bin.exists() and login_bin.exists()):
        print("缺少二进制文件，请先执行: bash scripts/xiaohongshu_send_setup.sh setup")
        return 1

    base_url = args.base_url.rstrip("/")
    print("\n=== Step 2: MCP Service Health ===")
    health = http_json("GET", f"{base_url}/health")
    print_json(health)

    print("\n=== Step 3: Login Status (HTTP API) ===")
    login_status = http_json("GET", f"{base_url}/api/v1/login/status")
    print_json(login_status)

    print("\n=== MCP Verify: initialize ===")
    init_resp, init_headers = mcp_request(base_url, "initialize", {}, req_id=1)
    print_json(init_resp)

    session_id = init_headers.get("Mcp-Session-Id") or init_headers.get("mcp-session-id")
    if not session_id:
        print("\n[error] initialize 响应缺少 Mcp-Session-Id，无法继续 MCP 工具验证")
        return 1

    print(f"\nMCP Session ID: {session_id}")
    print("\n=== MCP Verify: notifications/initialized ===")
    initialized_resp, _ = mcp_request(
        base_url,
        "notifications/initialized",
        {},
        req_id=None,
        session_id=session_id,
    )
    # notification 常见返回为空对象，保持可视化输出
    print_json(initialized_resp)

    print("\n=== MCP Verify: tools/list ===")
    tools_list_resp, _ = mcp_request(
        base_url,
        "tools/list",
        {},
        req_id=2,
        session_id=session_id,
    )
    print_json(tools_list_resp)
    if "error" in tools_list_resp:
        return 1

    print("\n=== MCP Verify: tools/call(check_login_status) ===")
    tools_call_resp, _ = mcp_request(
        base_url,
        "tools/call",
        {"name": "check_login_status", "arguments": {}},
        req_id=3,
        session_id=session_id,
    )
    print_json(tools_call_resp)
    if "error" in tools_call_resp:
        return 1

    if args.payload:
        print("\n=== Step 4: Payload Validation ===")
        payload = normalize_payload(load_json(Path(args.payload)))
        errors, warnings = validate_payload(payload, check_urls=args.check_urls)
        print(f"errors={len(errors)}, warnings={len(warnings)}")
        for w in warnings:
            print(f"- warning: {w}")
        for e in errors:
            print(f"- error: {e}")
        if errors:
            return 1

    print("\n验证完成")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="xiaohongshu-send automation helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="校验发布参数")
    p_validate.add_argument("--payload", required=True, help="JSON 文件路径")
    p_validate.add_argument("--check-urls", action="store_true", help="尝试检查图片 URL 可访问性")
    p_validate.set_defaults(func=cmd_validate)

    p_check_login = sub.add_parser("check-login", help="调用登录状态接口")
    p_check_login.add_argument("--base-url", default="http://127.0.0.1:18060", help="服务地址")
    p_check_login.set_defaults(func=cmd_check_login)

    p_publish = sub.add_parser("publish", help="发布图文内容")
    p_publish.add_argument("--payload", required=True, help="JSON 文件路径")
    p_publish.add_argument("--base-url", default="http://127.0.0.1:18060", help="服务地址")
    p_publish.add_argument("--dry-run", action="store_true", help="仅校验，不提交发布")
    p_publish.add_argument("--check-urls", action="store_true", help="发布前检查图片 URL 可访问性")
    p_publish.add_argument("--timeout", type=int, default=600, help="发布接口超时时间（秒），默认 600")
    p_publish.set_defaults(func=cmd_publish)

    p_verify = sub.add_parser("verify", help="端到端验证（环境+服务+MCP+登录状态）")
    p_verify.add_argument("--base-url", default="http://127.0.0.1:18060", help="服务地址")
    p_verify.add_argument("--payload", help="可选：附加发布参数校验 JSON")
    p_verify.add_argument("--check-urls", action="store_true", help="附加校验时检查 URL 可访问性")
    p_verify.set_defaults(func=cmd_verify)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except RuntimeError as ex:
        print(f"[error] {ex}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
