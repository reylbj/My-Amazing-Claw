#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_DIR="$ROOT_DIR/skills/xianyu-multi-agent"

cd "$SKILL_DIR"
exec ./venv/bin/python3 live_prepublish_debug.py --auto-publish "$@"
