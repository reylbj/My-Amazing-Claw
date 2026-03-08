#!/usr/bin/env bash
# Install standby-safe runtime tuning and a launchd guardian.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_PATH="$HOME/Library/LaunchAgents/ai.openclaw.guardian.plist"
UID_VALUE="$(id -u)"
RUNTIME_DIR="$HOME/.openclaw/guardian_runtime"
RUNTIME_SCRIPTS_DIR="$RUNTIME_DIR/scripts"

mkdir -p "$HOME/.openclaw/logs" "$HOME/.openclaw/state" "$HOME/Library/LaunchAgents" "$RUNTIME_SCRIPTS_DIR"

# Avoid macOS Desktop privacy blocks in launchd by running guardian from ~/.openclaw.
cp "$SCRIPT_DIR/openclaw_guardian.py" "$RUNTIME_SCRIPTS_DIR/openclaw_guardian.py"
cp "$SCRIPT_DIR/gateway_stable_start.sh" "$RUNTIME_SCRIPTS_DIR/gateway_stable_start.sh"
chmod 755 "$RUNTIME_SCRIPTS_DIR/openclaw_guardian.py" "$RUNTIME_SCRIPTS_DIR/gateway_stable_start.sh"

python3 "$RUNTIME_SCRIPTS_DIR/openclaw_guardian.py" patch-runtime
python3 "$RUNTIME_SCRIPTS_DIR/openclaw_guardian.py" configure
python3 "$RUNTIME_SCRIPTS_DIR/openclaw_guardian.py" render-plist > "$PLIST_PATH"

launchctl bootout "gui/$UID_VALUE" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$UID_VALUE" "$PLIST_PATH"
launchctl kickstart -k "gui/$UID_VALUE/ai.openclaw.guardian"

bash "$RUNTIME_SCRIPTS_DIR/gateway_stable_start.sh"
python3 "$RUNTIME_SCRIPTS_DIR/openclaw_guardian.py" check-once --verbose
