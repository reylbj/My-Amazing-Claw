#!/usr/bin/env python3
"""
Publish Xiaohongshu posts through a stability-first workflow.

The script keeps the original command-line contract but trims the control flow
into smaller stages so the fallback logic is easier to audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


DEFAULT_BASE_URL = "http://127.0.0.1:18060"
DEFAULT_TIMEOUT_SECONDS = 240
MAX_IMAGE_COUNT = 9
RECOMMENDED_MULTI_IMAGE_COUNT = 7
TARGET_IMAGE_WIDTH = 1080
TARGET_IMAGE_HEIGHT = 1440
TARGET_IMAGE_BYTES = 220 * 1024
POSTER_MAX_BYTES = 3 * 1024 * 1024
POSTER_GAP = 24
POSTER_PADDING = 24
KNOWN_MULTI_IMAGE_ERRORS = (
    "第2张图片上传超时",
    "上传超时",
    "查找标题输入框失败",
    "context canceled",
)
KNOWN_RECENT_FAILURE_MARKERS = (
    "第2张图片上传超时",
    "查找标题输入框失败: context canceled",
)


@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def combined(self) -> str:
        return "\n".join(part for part in (self.stdout.strip(), self.stderr.strip()) if part)


@dataclass
class PreparedPayload:
    label: str
    payload_path: Path
    images: list[Path]


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def publish_helper_script() -> Path:
    return Path(__file__).resolve().parent / "xiaohongshu_send.py"


def stable_start_script() -> Path:
    return Path(__file__).resolve().parent / "xiaohongshu_stable_start.sh"


def xhs_mcp_log() -> Path:
    return workspace_root() / "skills" / "xiaohongshu-send" / "logs" / "mcp.log"


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy aliases so the rest of the script uses one schema only."""
    normalized = dict(payload)
    normalized["content"] = normalized.get("content") or normalized.get("description") or normalized.get("desc") or ""
    normalized["images"] = normalized.get("images") or normalized.get("image_urls") or []
    normalized["tags"] = normalized.get("tags") or normalized.get("topics") or normalized.get("hashtags") or []
    if "visibility" not in normalized and "is_private" in normalized:
        normalized["visibility"] = "仅自己可见" if bool(normalized["is_private"]) else "公开可见"
    return normalized


def safe_ascii_name(index: int, source_path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", source_path.stem).strip("._") or f"image_{index:02d}"
    return f"{index:02d}_{stem}.jpg"


def ensure_rgb(image: Image.Image) -> Image.Image:
    """Flatten alpha channels onto white to avoid format-specific upload quirks."""
    image = ImageOps.exif_transpose(image)
    if image.mode == "RGB":
        return image
    background = Image.new("RGB", image.size, "white")
    alpha = image.getchannel("A") if image.mode in {"RGBA", "LA"} else None
    converted = image.convert("RGB")
    background.paste(converted, mask=alpha)
    return background


def constrain_image(image: Image.Image) -> Image.Image:
    """Keep oversized images inside the preferred upload box before JPEG encoding."""
    if image.width <= TARGET_IMAGE_WIDTH and image.height <= TARGET_IMAGE_HEIGHT:
        return image
    constrained = image.copy()
    constrained.thumbnail((TARGET_IMAGE_WIDTH, TARGET_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
    return constrained


def encode_jpeg_under_limit(image: Image.Image, output_path: Path, *, max_bytes: int) -> None:
    """
    Encode a JPEG using a small, deterministic ladder of quality and size steps.

    The sequence is intentionally conservative: it prefers preserving resolution
    first, then gradually scales down only when quality reduction is insufficient.
    """

    variants = (
        (92, 1.0),
        (88, 1.0),
        (84, 1.0),
        (80, 1.0),
        (76, 0.96),
        (72, 0.92),
        (68, 0.88),
    )
    current_image = image
    current_quality = 72
    for quality, scale in variants:
        candidate = current_image
        if scale < 0.999:
            candidate = candidate.resize(
                (
                    max(720, int(candidate.width * scale)),
                    max(960, int(candidate.height * scale)),
                ),
                Image.Resampling.LANCZOS,
            )
        candidate.save(output_path, format="JPEG", quality=quality, optimize=True, progressive=True)
        if output_path.stat().st_size <= max_bytes:
            return
        current_image = candidate
        current_quality = quality
    current_image.save(output_path, format="JPEG", quality=current_quality, optimize=True, progressive=True)


def optimize_images(image_paths: list[str], asset_dir: Path, *, max_bytes: int) -> list[Path]:
    """Copy every source image into an ASCII-safe, compressed working directory."""
    asset_dir.mkdir(parents=True, exist_ok=True)
    optimized: list[Path] = []
    for index, image_path in enumerate(image_paths, start=1):
        source = Path(image_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"图片不存在: {source}")
        destination = asset_dir / safe_ascii_name(index, source)
        with Image.open(source) as opened:
            prepared = constrain_image(ensure_rgb(opened))
            encode_jpeg_under_limit(prepared, destination, max_bytes=max_bytes)
        optimized.append(destination)
    return optimized


def build_long_poster(image_paths: list[Path], output_path: Path) -> Path:
    """Merge many images into a single tall poster for the fallback publishing mode."""
    prepared_images: list[Image.Image] = []
    try:
        for image_path in image_paths:
            with Image.open(image_path) as opened:
                image = ensure_rgb(opened)
                if image.width != TARGET_IMAGE_WIDTH:
                    new_height = max(1, int(image.height * (TARGET_IMAGE_WIDTH / image.width)))
                    image = image.resize((TARGET_IMAGE_WIDTH, new_height), Image.Resampling.LANCZOS)
                prepared_images.append(image.copy())

        total_height = POSTER_PADDING * 2 + sum(image.height for image in prepared_images)
        total_height += POSTER_GAP * max(0, len(prepared_images) - 1)
        poster = Image.new("RGB", (TARGET_IMAGE_WIDTH, total_height), "white")

        cursor_y = POSTER_PADDING
        for image in prepared_images:
            poster.paste(image, (0, cursor_y))
            cursor_y += image.height + POSTER_GAP

        encode_jpeg_under_limit(poster, output_path, max_bytes=POSTER_MAX_BYTES)
        return output_path
    finally:
        for image in prepared_images:
            image.close()


def write_payload(payload: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def make_run_dir(payload_path: Path) -> Path:
    digest = hashlib.md5(f"{payload_path.resolve()}:{time.time_ns()}".encode("utf-8")).hexdigest()[:10]
    run_dir = Path("/tmp/xhs_publish") / digest
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def recent_log_needs_poster(log_path: Path) -> bool:
    """Read only the tail of the MCP log because we only care about fresh instability."""
    if not log_path.is_file():
        return False
    try:
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-120:])
    except OSError:
        return False
    return any(marker in tail for marker in KNOWN_RECENT_FAILURE_MARKERS)


def run_command(cmd: list[str], cwd: Path | None = None) -> CommandResult:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(result.returncode, result.stdout, result.stderr)


def print_command_result(result: CommandResult, header: str) -> None:
    print(f"\n=== {header} ===")
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    print(f"[exit_code] {result.exit_code}")


def check_login(base_url: str) -> CommandResult:
    return run_command(
        ["python3", str(publish_helper_script()), "check-login", "--base-url", base_url],
        cwd=workspace_root(),
    )


def restart_service() -> CommandResult:
    return run_command(["bash", str(stable_start_script())], cwd=workspace_root())


def publish_payload(payload_path: Path, base_url: str, timeout: int, *, dry_run: bool) -> CommandResult:
    cmd = [
        "python3",
        str(publish_helper_script()),
        "publish",
        "--payload",
        str(payload_path),
        "--base-url",
        base_url,
        "--timeout",
        str(timeout),
    ]
    if dry_run:
        cmd.append("--dry-run")
    return run_command(cmd, cwd=workspace_root())


def is_recoverable_failure(result: CommandResult) -> bool:
    return any(marker in result.combined for marker in KNOWN_MULTI_IMAGE_ERRORS)


def build_publish_payload(base_payload: dict[str, Any], image_paths: list[Path]) -> dict[str, Any]:
    payload = dict(base_payload)
    payload["images"] = [str(path) for path in image_paths]
    payload["image_urls"] = payload["images"]
    return payload


def choose_initial_mode(requested_mode: str, optimized_images: list[Path]) -> str:
    """Prefer poster mode when history or image count suggests multi-image instability."""
    if requested_mode in {"multi", "poster"}:
        return requested_mode
    if len(optimized_images) > RECOMMENDED_MULTI_IMAGE_COUNT:
        return "poster"
    if len(optimized_images) > 1 and recent_log_needs_poster(xhs_mcp_log()):
        return "poster"
    return "multi"


def prepare_payload_file(
    payload: dict[str, Any],
    optimized_images: list[Path],
    run_dir: Path,
    mode: str,
) -> PreparedPayload:
    """Build the first payload file, using a poster immediately when required."""
    if mode == "poster" and len(optimized_images) > 1:
        images = [build_long_poster(optimized_images, run_dir / "poster_cover.jpg")]
        label = "poster"
    else:
        images = optimized_images
        label = "multi" if len(images) > 1 else "single"
    payload_path = write_payload(
        build_publish_payload(payload, images),
        run_dir / f"payload_{label}.json",
    )
    return PreparedPayload(label=label, payload_path=payload_path, images=images)


def validate_payload(payload: dict[str, Any]) -> None:
    title = str(payload.get("title", "")).strip()
    content = str(payload.get("content", "")).strip()
    images = payload.get("images") or []
    if not title:
        raise ValueError("title 不能为空")
    if not content:
        raise ValueError("content/description 不能为空")
    if not isinstance(images, list) or not images:
        raise ValueError("images 至少需要 1 张")
    if len(images) > MAX_IMAGE_COUNT:
        raise ValueError(f"images 不能超过 {MAX_IMAGE_COUNT} 张，当前 {len(images)}")
    if len(images) > RECOMMENDED_MULTI_IMAGE_COUNT:
        print(
            f"[warning] images 共 {len(images)} 张，超过 {RECOMMENDED_MULTI_IMAGE_COUNT} 张时默认改走长图模式以提升稳定性",
            file=sys.stderr,
        )


def maybe_restart_before_publish(base_url: str) -> int:
    """
    Restart the publishing service when login state is unhealthy or logs show
    fresh multi-image instability. Returning zero means the caller can proceed.
    """

    login_result = check_login(base_url)
    if login_result.exit_code == 0 and not recent_log_needs_poster(xhs_mcp_log()):
        return 0
    restart_result = restart_service()
    print_command_result(restart_result, "Service Restart")
    return restart_result.exit_code


def publish_with_optional_fallback(
    original_payload: dict[str, Any],
    optimized_images: list[Path],
    prepared: PreparedPayload,
    *,
    base_url: str,
    timeout: int,
    strict_multi: bool,
    run_dir: Path,
) -> int:
    """
    Run the publish flow once and only fall back to a poster when the failure
    looks like the known multi-image upload failure family.
    """

    first_result = publish_payload(prepared.payload_path, base_url, timeout, dry_run=False)
    print_command_result(first_result, "Publish Attempt 1")
    if first_result.exit_code == 0:
        return 0

    if strict_multi or len(optimized_images) <= 1 or prepared.label == "poster":
        return first_result.exit_code
    if not is_recoverable_failure(first_result):
        return first_result.exit_code

    print("\n检测到多图链路故障，切换到单张长图兜底。")
    restart_result = restart_service()
    print_command_result(restart_result, "Service Restart Before Poster Fallback")
    if restart_result.exit_code != 0:
        return restart_result.exit_code

    poster_path = build_long_poster(optimized_images, run_dir / "poster_fallback.jpg")
    fallback_payload_path = write_payload(
        build_publish_payload(original_payload, [poster_path]),
        run_dir / "payload_poster_fallback.json",
    )
    fallback_result = publish_payload(fallback_payload_path, base_url, timeout, dry_run=False)
    print_command_result(fallback_result, "Publish Attempt 2 Poster Fallback")
    return fallback_result.exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="小红书自动发布（稳态版）")
    parser.add_argument("--payload", required=True, help="payload JSON 文件路径")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="MCP 服务地址")
    parser.add_argument("--dry-run", action="store_true", help="仅生成安全 payload 并校验，不实际发布")
    parser.add_argument(
        "--publish-mode",
        choices=("auto", "multi", "poster"),
        default="auto",
        help="发布模式：auto=自动，multi=优先多图，poster=直接单张长图",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="发布接口超时秒数")
    parser.add_argument(
        "--max-image-bytes",
        type=int,
        default=TARGET_IMAGE_BYTES,
        help="单张图片压缩目标字节数",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload_path = Path(args.payload).expanduser().resolve()
    original_payload = normalize_payload(load_payload(payload_path))
    validate_payload(original_payload)

    run_dir = make_run_dir(payload_path)
    optimized_images = optimize_images(
        original_payload["images"],
        run_dir / "assets",
        max_bytes=args.max_image_bytes,
    )
    prepared = prepare_payload_file(
        original_payload,
        optimized_images,
        run_dir,
        choose_initial_mode(args.publish_mode, optimized_images),
    )

    print("=" * 60)
    print("小红书稳态发布器")
    print("=" * 60)
    print(f"run_dir: {run_dir}")
    print(f"source_payload: {payload_path}")
    print(f"prepared_payload: {prepared.payload_path}")
    print(f"mode: {prepared.label}")
    print(f"images: {len(prepared.images)}")

    if args.dry_run:
        dry_result = publish_payload(prepared.payload_path, args.base_url, args.timeout, dry_run=True)
        print_command_result(dry_result, "Dry Run")
        return dry_result.exit_code

    restart_exit_code = maybe_restart_before_publish(args.base_url)
    if restart_exit_code != 0:
        return restart_exit_code

    return publish_with_optional_fallback(
        original_payload,
        optimized_images,
        prepared,
        base_url=args.base_url,
        timeout=args.timeout,
        strict_multi=args.publish_mode == "multi",
        run_dir=run_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
