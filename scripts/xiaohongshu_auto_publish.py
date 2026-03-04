#!/usr/bin/env python3
"""
小红书自动发布包装脚本
自动处理中文路径问题，确保发布成功
"""

import json
import os
import shutil
import sys
import hashlib
import subprocess
from pathlib import Path


def sanitize_path_for_xhs(original_path: str) -> tuple[str, bool]:
    """
    检查并处理路径中的中文字符
    返回: (安全路径, 是否进行了转换)
    """
    import re

    if re.search(r'[\u4e00-\u9fff]', original_path):
        # 生成安全的临时路径
        path_hash = hashlib.md5(original_path.encode()).hexdigest()[:8]
        safe_path = f"/tmp/xhs_safe_{path_hash}"
        return safe_path, True

    return original_path, False


def prepare_safe_payload(payload_file: str) -> str:
    """
    读取payload文件，处理所有中文路径，返回新的payload文件路径
    """
    with open(payload_file, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    # 创建安全的输出目录
    safe_dir = "/tmp/xhs_publish"
    os.makedirs(safe_dir, exist_ok=True)

    # 处理图片路径
    safe_images = []
    for img_path in payload.get('images', []):
        safe_path, converted = sanitize_path_for_xhs(img_path)

        if converted:
            # 复制文件到安全路径
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            if os.path.exists(img_path):
                shutil.copy2(img_path, safe_path)
                print(f"✅ 已复制: {os.path.basename(img_path)} -> {safe_path}")
            else:
                print(f"❌ 文件不存在: {img_path}")
                sys.exit(1)

        safe_images.append(safe_path)

    # 更新payload
    payload['images'] = safe_images

    # 保存新的payload
    safe_payload_path = os.path.join(safe_dir, "payload_safe.json")
    with open(safe_payload_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n📝 已生成安全payload: {safe_payload_path}")
    return safe_payload_path


def publish_to_xiaohongshu(payload_file: str, base_url: str = "http://127.0.0.1:18060", dry_run: bool = False):
    """
    发布到小红书
    """
    script_path = Path(__file__).parent / "xiaohongshu_send.py"

    cmd = [
        "python3",
        str(script_path),
        "publish",
        "--payload", payload_file,
        "--base-url", base_url,
        "--timeout", "600"
    ]

    if dry_run:
        cmd.append("--dry-run")

    print(f"\n🚀 开始发布...")
    print(f"命令: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode


def main():
    import argparse

    parser = argparse.ArgumentParser(description='小红书自动发布（自动处理中文路径）')
    parser.add_argument('--payload', required=True, help='payload JSON文件路径')
    parser.add_argument('--base-url', default='http://127.0.0.1:18060', help='MCP服务地址')
    parser.add_argument('--dry-run', action='store_true', help='仅测试，不实际发布')

    args = parser.parse_args()

    print("=" * 60)
    print("小红书自动发布工具")
    print("=" * 60)

    # 准备安全的payload
    safe_payload = prepare_safe_payload(args.payload)

    # 发布
    exit_code = publish_to_xiaohongshu(safe_payload, args.base_url, args.dry_run)

    if exit_code == 0:
        print("\n✅ 发布成功！")
    else:
        print(f"\n❌ 发布失败（退出码: {exit_code}）")

    # 清理临时文件（可选）
    # shutil.rmtree("/tmp/xhs_publish", ignore_errors=True)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
