#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
exec ./venv/bin/python3 live_prepublish_debug.py --auto-publish "$@"
