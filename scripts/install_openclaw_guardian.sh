#!/usr/bin/env bash
# Install standby-safe runtime tuning and a launchd guardian.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_PATH="$HOME/Library/LaunchAgents/ai.openclaw.guardian.plist"
UID_VALUE="$(id -u)"

mkdir -p "$HOME/.openclaw/logs" "$HOME/.openclaw/state" "$HOME/Library/LaunchAgents"

python3 "$SCRIPT_DIR/openclaw_guardian.py" patch-runtime
python3 "$SCRIPT_DIR/openclaw_guardian.py" configure
python3 "$SCRIPT_DIR/openclaw_guardian.py" render-plist > "$PLIST_PATH"

launchctl bootout "gui/$UID_VALUE" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID_VALUE" "$PLIST_PATH"
launchctl kickstart -k "gui/$UID_VALUE/ai.openclaw.guardian"

bash "$SCRIPT_DIR/gateway_stable_start.sh"
python3 "$SCRIPT_DIR/openclaw_guardian.py" check-once --verbose
