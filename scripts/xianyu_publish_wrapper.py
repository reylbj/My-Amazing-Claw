#!/usr/bin/env python3
"""
OpenClaw集成脚本 - 闲鱼自动发布
可以从OpenClaw直接调用
"""

import sys
import os
import asyncio
import json
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path


def workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_xianyu_home() -> Path:
    env = os.getenv("XIANYU_HOME")
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())

    root = workspace_root()
    candidates.extend(
        [
            root / "skills" / "xianyu-multi-agent",
            root / "xianyu-multi-agent",
            Path(__file__).resolve().parent / "xianyu-multi-agent",
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def ensure_project_python(project_dir: Path) -> None:
    if os.getenv("XIANYU_WRAPPER_BOOTSTRAPPED") == "1":
        return

    venv_dir = project_dir / "venv"
    current_prefix = Path(sys.prefix).resolve()
    if current_prefix == venv_dir.resolve():
        return

    venv_candidates = [
        venv_dir / "bin" / "python3",
        venv_dir / "bin" / "python",
    ]

    current = Path(sys.executable)
    for candidate in venv_candidates:
        if not candidate.exists():
            continue
        if candidate == current:
            return

        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(venv_dir)
        env["XIANYU_WRAPPER_BOOTSTRAPPED"] = "1"
        os.execve(str(candidate), [str(candidate), __file__, *sys.argv[1:]], env)


def load_xianyu_publisher_class():
    project_dir = resolve_xianyu_home()
    if not project_dir.exists():
        raise RuntimeError(f"未找到闲鱼项目目录: {project_dir}")

    entrypoint = project_dir / "xianyu_auto_publish.py"
    if not entrypoint.exists():
        raise RuntimeError(
            "闲鱼项目目录已找到，但缺少兼容入口 xianyu_auto_publish.py: "
            f"{project_dir}"
        )

    sys.path.insert(0, str(project_dir))
    module = import_module("xianyu_auto_publish")
    publisher_cls = getattr(module, "XianyuAutoPublisher", None)
    if publisher_cls is None:
        raise RuntimeError(
            "已加载闲鱼项目目录，但未找到 XianyuAutoPublisher 类: "
            f"{entrypoint}"
        )
    return publisher_cls


def ensure_runtime_dirs(project_dir: Path) -> None:
    for name in ("data", "logs"):
        (project_dir / name).mkdir(exist_ok=True)


@contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


async def publish_from_openclaw(service_type: str, custom_content: dict = None):
    """
    从OpenClaw调用的发布函数
    
    Args:
        service_type: 服务类型
        custom_content: 自定义内容（可选）
    """
    project_dir = resolve_xianyu_home()
    ensure_project_python(project_dir)
    ensure_runtime_dirs(project_dir)

    with pushd(project_dir):
        publisher_cls = load_xianyu_publisher_class()
        publisher = publisher_cls()

        try:
            # 生成或使用自定义文案
            if custom_content:
                content = custom_content
            else:
                content = publisher.generate_product_content(service_type)
            
            print(f"📝 文案: {content['title']}")
            
            # 初始化浏览器
            await publisher.init_browser(headless=False)
            await publisher.load_cookies()
            
            # 发布
            success = await publisher.publish_product(content)
            
            return {
                "success": success,
                "content": content
            }
            
        finally:
            await publisher.close()


if __name__ == "__main__":
    # 命令行调用示例
    # python3 scripts/xianyu_publish_wrapper.py "AI文案代写"
    
    if len(sys.argv) < 2:
        print("用法: python3 xianyu_publish_wrapper.py <服务类型>")
        sys.exit(1)
    
    service_type = sys.argv[1]
    result = asyncio.run(publish_from_openclaw(service_type))
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
