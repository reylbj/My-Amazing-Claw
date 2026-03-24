#!/usr/bin/env python3
"""
OpenClaw guardian: runtime patching, standby tuning, and self-healing checks.
"""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence


ROOT_DIR = Path(__file__).resolve().parents[1]
OPENCLAW_HOME = Path.home() / ".openclaw"
OPENCLAW_CONFIG = OPENCLAW_HOME / "openclaw.json"
OPENCLAW_STATE_DIR = OPENCLAW_HOME / "state"
OPENCLAW_LOG_DIR = OPENCLAW_HOME / "logs"
OPENCLAW_BACKUP_DIR = OPENCLAW_HOME / "backups" / "guardian"
GUARDIAN_STATE_FILE = OPENCLAW_STATE_DIR / "guardian_state.json"
GUARDIAN_LOG_FILE = OPENCLAW_LOG_DIR / "guardian.log"
LAUNCH_AGENT_PATH = Path.home() / "Library" / "LaunchAgents" / "ai.openclaw.guardian.plist"
DIST_DIR = Path.home() / ".npm-global" / "lib" / "node_modules" / "openclaw" / "dist"
GATEWAY_STABLE_SCRIPT = ROOT_DIR / "scripts" / "gateway_stable_start.sh"
NODE22_BIN = Path.home() / ".npm-global" / "lib" / "node_modules" / "node" / "bin" / "node"
OPENCLAW_PACKAGE_ROOT = DIST_DIR.parent
CONTROL_UI_DIR = DIST_DIR / "control-ui"
CONTROL_UI_CACHE_DIR = OPENCLAW_HOME / "cache" / "control-ui"
CONTROL_UI_FALLBACK_DIRS = (
    CONTROL_UI_CACHE_DIR,
    Path("/tmp/openclaw-source/dist/control-ui"),
)
HOST_OPENCLAW_LINK = OPENCLAW_HOME / "extensions" / "node_modules" / "openclaw"
WEIXIN_PLUGIN_DIR = OPENCLAW_HOME / "extensions" / "openclaw-weixin"
WECOM_PLUGIN_DIR = OPENCLAW_HOME / "extensions" / "wecom"
HOST_PLUGIN_SDK_INDEX = OPENCLAW_PACKAGE_ROOT / "dist" / "plugin-sdk" / "index.js"

EXPECTED_WEB_HEARTBEAT_SECONDS = 300
EXPECTED_WEB_MESSAGE_TIMEOUT_MS = 24 * 60 * 60 * 1000
EXPECTED_WEB_STANDBY_WARN_MINUTES = 24 * 60
EXPECTED_CHANNEL_HEALTH_CHECK_MINUTES = 5
EXPECTED_AGENT_HEARTBEAT_EVERY = "0m"
EXPECTED_GROUP_POLICY_FALLBACK = "open"
GROUP_POLICY_CHANNELS = ("whatsapp", "telegram")
WECOM_CHANNEL_ID = "wecom"
WECOM_PLUGIN_ID = "wecom-openclaw-plugin"
WECOM_PLUGIN_PACKAGE = "@wecom/wecom-openclaw-plugin"
RESTART_COOLDOWN_SECONDS = 15 * 60
MAX_RESTARTS_PER_HOUR = 6
INCIDENT_LOOKBACK_MINUTES = 180
MODEL_FAILURE_LOOKBACK_MINUTES = 20
MODEL_FAILURE_PROMOTE_THRESHOLD = 3
MODEL_RECOVERY_QUIET_MINUTES = 20
MODEL_RECOVERY_PROBE_INTERVAL_MINUTES = 10
MODEL_PROBE_AGENT_ID = "guardian-probe"
MODEL_PROBE_MESSAGE = "Reply with OK only."
MODEL_PROBE_TIMEOUT_SECONDS = 90
MODEL_PROBE_WORKSPACE = Path(tempfile.gettempdir()) / "openclaw-guardian-probe"
MAIN_WEBCHAT_SESSION_KEY = "agent:main:main"
CHANNEL_DNS_LOOP_THRESHOLD = 6
CHANNEL_TIMEOUT_LOOP_THRESHOLD = 6

PATTERN_UNKNOWN_READ = "Unknown system error -11"
PATTERN_ABNORMAL_CLOSE = "gateway closed (1006 abnormal closure"
PATTERN_FETCH_FAILED = "TypeError: fetch failed"
PATTERN_MAX_ATTEMPTS = "web reconnect: max attempts reached"
PATTERN_STALE_SOCKET = "health-monitor: restarting (reason: stale-socket)"
PATTERN_DNS_LOOKUP = "getaddrinfo ENOTFOUND"
PATTERN_CONNECT_TIMEOUT = "UND_ERR_CONNECT_TIMEOUT"
PATTERN_MODEL_OVERLOADED = "The AI service is temporarily overloaded"
PATTERN_MODEL_HTTP_504 = "The AI service is temporarily unavailable (HTTP 504)"
PATTERN_MODEL_FAILOVER = "FailoverError:"
PATTERN_MODEL_BACKOFF = "overload backoff before failover for "
PATTERN_MODEL_IMPROPER_400 = "400 Improperly formed request."

RUNTIME_PATCH_GLOBS = (
    "channel-web-*.js",
    "web-*.js",
    "auth-profiles-*.js",
    "model-selection-*.js",
    "gateway-cli-*.js",
    "daemon-cli.js",
    "plugin-sdk/channel-web-*.js",
    "plugin-sdk/config-*.js",
)


@dataclass
class IncidentSummary:
    counts: dict[str, int]
    latest: dict[str, str | None]
    events: dict[str, list[str]]


@dataclass
class ModelFailureEvent:
    timestamp: str
    kind: str
    line: str
    model: str | None = None


@dataclass
class ModelFailureSummary:
    counts: dict[str, int]
    latest: str | None
    events: list[ModelFailureEvent]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def log_line(message: str, *, also_stdout: bool = False) -> None:
    ensure_parent(GUARDIAN_LOG_FILE)
    line = f"[{iso_now()}] {message}"
    with GUARDIAN_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    if also_stdout:
        print(line)


def run_command(
    args: Sequence[str],
    *,
    timeout: int = 30,
    check: bool = False,
    cwd: Path | None = ROOT_DIR,
) -> subprocess.CompletedProcess[str]:
    argv = list(args)
    if argv and Path(argv[0]).name == "openclaw":
        try:
            configure_openclaw(dry_run=False)
        except Exception as exc:
            return subprocess.CompletedProcess(argv, 1, "", f"config repair failed: {exc}")
    try:
        return subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=check,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 1, "", str(exc))


def load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def backup_file(path: Path, *, suffix: str) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = OPENCLAW_BACKUP_DIR / f"{stamp}-{suffix}"
    ensure_parent(backup_path)
    backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def ensure_shared_openclaw_package_link() -> bool:
    if not OPENCLAW_PACKAGE_ROOT.exists():
        return False

    if HOST_OPENCLAW_LINK.is_symlink():
        try:
            if HOST_OPENCLAW_LINK.resolve() == OPENCLAW_PACKAGE_ROOT.resolve():
                return False
        except FileNotFoundError:
            pass
        HOST_OPENCLAW_LINK.unlink()
    elif HOST_OPENCLAW_LINK.exists():
        package_json = HOST_OPENCLAW_LINK / "package.json"
        if package_json.exists():
            try:
                package_payload = json.loads(package_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                package_payload = {}
            if package_payload.get("name") == "openclaw":
                return False
        return False

    HOST_OPENCLAW_LINK.parent.mkdir(parents=True, exist_ok=True)
    HOST_OPENCLAW_LINK.symlink_to(OPENCLAW_PACKAGE_ROOT, target_is_directory=True)
    return True


def deep_set(target: dict, keys: Sequence[str], value) -> None:
    current = target
    for key in keys[:-1]:
        existing = current.get(key)
        if not isinstance(existing, dict):
            existing = {}
            current[key] = existing
        current = existing
    current[keys[-1]] = value


def load_guardian_state() -> dict:
    state = load_json(GUARDIAN_STATE_FILE, {})
    if not isinstance(state, dict):
        return {}
    return state


def save_guardian_state(state: dict) -> None:
    save_json(GUARDIAN_STATE_FILE, state)


def reset_model_failover_state(
    state: dict,
    *,
    handled_at: str,
    reason: str,
    detail: str | None = None,
) -> dict:
    previous = state.get("model_failover")
    if not isinstance(previous, dict):
        previous = {}

    payload = {
        "active": False,
        "handled_through_ts": handled_at,
        "last_action": "state-reset",
        "last_action_detail": detail or reason,
        "last_reset_at": iso_now(),
    }
    baseline_primary = str(previous.get("baseline_primary") or "").strip()
    promoted_primary = str(previous.get("promoted_primary") or "").strip()
    if baseline_primary:
        payload["previous_baseline_primary"] = baseline_primary
    if promoted_primary:
        payload["previous_promoted_primary"] = promoted_primary

    state["model_failover"] = payload
    return payload


def prune_restart_times(times: Iterable[str], *, now: datetime) -> list[str]:
    kept: list[str] = []
    cutoff = now - timedelta(hours=1)
    for item in times:
        parsed = parse_iso(item)
        if parsed and parsed >= cutoff:
            kept.append(parsed.isoformat())
    return kept


def normalize_model_keys(model_id: str, provider: str | None = None) -> set[str]:
    normalized: set[str] = set()
    model = str(model_id or "").strip()
    model_provider = str(provider or "").strip()
    if not model:
        return normalized
    normalized.add(model)
    if "/" in model:
        normalized.add(model.split("/", 1)[1])
    elif model_provider:
        normalized.add(f"{model_provider}/{model}")
    return normalized


def session_store_path(agent_id: str) -> Path:
    return OPENCLAW_HOME / "agents" / agent_id / "sessions" / "sessions.json"


def session_file_path(agent_id: str, session_id: str) -> Path:
    return OPENCLAW_HOME / "agents" / agent_id / "sessions" / f"{session_id}.jsonl"


def read_session_header(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, "missing-session-file"

    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            first_line = handle.readline().strip()
    except OSError as exc:
        return None, f"read-failed:{exc}"

    if not first_line:
        return None, "empty-session-file"

    try:
        payload = json.loads(first_line)
    except json.JSONDecodeError:
        return None, "invalid-session-header-json"

    if not isinstance(payload, dict):
        return None, "invalid-session-header-type"

    return payload, None


def inspect_main_webchat_session(*, agent_id: str = "main") -> dict[str, object]:
    store_path = session_store_path(agent_id)
    store = load_json(store_path, {})
    if not isinstance(store, dict):
        return {
            "healthy": False,
            "reason": "invalid-session-store",
            "storePath": str(store_path),
        }

    entry = store.get(MAIN_WEBCHAT_SESSION_KEY)
    if entry is None:
        return {
            "healthy": True,
            "present": False,
            "storePath": str(store_path),
        }
    if not isinstance(entry, dict):
        return {
            "healthy": False,
            "reason": "invalid-main-entry",
            "storePath": str(store_path),
        }

    session_id = str(entry.get("sessionId") or "").strip()
    session_file_raw = str(entry.get("sessionFile") or "").strip()
    session_file = Path(session_file_raw) if session_file_raw else session_file_path(agent_id, session_id)
    if not session_id:
        return {
            "healthy": False,
            "reason": "missing-session-id",
            "storePath": str(store_path),
            "sessionFile": str(session_file),
        }

    if session_file.name != f"{session_id}.jsonl":
        return {
            "healthy": False,
            "reason": "session-file-name-mismatch",
            "storePath": str(store_path),
            "sessionId": session_id,
            "sessionFile": str(session_file),
        }

    header, error = read_session_header(session_file)
    if error is not None:
        return {
            "healthy": False,
            "reason": error,
            "storePath": str(store_path),
            "sessionId": session_id,
            "sessionFile": str(session_file),
            "lockFile": str(session_file.with_suffix(session_file.suffix + ".lock")),
        }

    header_type = str(header.get("type") or "").strip()
    header_id = str(header.get("id") or "").strip()
    if header_type != "session":
        return {
            "healthy": False,
            "reason": "invalid-session-header-record",
            "storePath": str(store_path),
            "sessionId": session_id,
            "sessionFile": str(session_file),
            "headerType": header_type or None,
            "headerId": header_id or None,
            "lockFile": str(session_file.with_suffix(session_file.suffix + ".lock")),
        }
    if header_id != session_id:
        return {
            "healthy": False,
            "reason": "session-header-id-mismatch",
            "storePath": str(store_path),
            "sessionId": session_id,
            "sessionFile": str(session_file),
            "headerId": header_id or None,
            "lockFile": str(session_file.with_suffix(session_file.suffix + ".lock")),
        }

    return {
        "healthy": True,
        "present": True,
        "storePath": str(store_path),
        "sessionId": session_id,
        "sessionFile": str(session_file),
    }


def repair_main_webchat_session(*, agent_id: str = "main", dry_run: bool) -> dict[str, object]:
    health = inspect_main_webchat_session(agent_id=agent_id)
    if health.get("healthy"):
        return {"changed": False, "health": health}

    store_path = session_store_path(agent_id)
    store = load_json(store_path, {})
    if not isinstance(store, dict):
        raise ValueError(f"invalid session store: {store_path}")

    removed = MAIN_WEBCHAT_SESSION_KEY in store
    lock_file = str(health.get("lockFile") or "").strip()
    lock_path = Path(lock_file) if lock_file else None
    if dry_run:
        return {
            "changed": removed or bool(lock_path and lock_path.exists()),
            "health": health,
            "dryRun": True,
        }

    backup_path = None
    if removed:
        backup_path = backup_file(store_path, suffix=f"{agent_id}-sessions.json.bak")
        del store[MAIN_WEBCHAT_SESSION_KEY]
        save_json(store_path, store)

    lock_removed = False
    if lock_path and lock_path.exists():
        try:
            lock_path.unlink()
            lock_removed = True
        except OSError:
            lock_removed = False

    return {
        "changed": removed or lock_removed,
        "health": health,
        "backupPath": str(backup_path) if backup_path else None,
        "lockRemoved": lock_removed,
    }


def prune_model_sessions(
    *,
    agent_id: str,
    model_ids: Sequence[str],
    older_than_hours: int,
    dry_run: bool,
) -> dict[str, object]:
    store_path = session_store_path(agent_id)
    store = load_json(store_path, {})
    if not isinstance(store, dict):
        raise ValueError(f"invalid session store: {store_path}")

    cutoff_ms = int(time.time() * 1000) - (max(older_than_hours, 0) * 60 * 60 * 1000)
    target_aliases: set[str] = set()
    for model_id in model_ids:
        target_aliases.update(normalize_model_keys(str(model_id)))

    matched: list[dict[str, object]] = []
    kept: dict[str, object] = {}
    for key, value in store.items():
        if not isinstance(value, dict):
            kept[key] = value
            continue

        entry_aliases = normalize_model_keys(
            str(value.get("model") or ""),
            str(value.get("modelProvider") or ""),
        )
        updated_at = value.get("updatedAt")
        updated_at_ms = updated_at if isinstance(updated_at, int) else 0
        should_prune = bool(entry_aliases & target_aliases) and updated_at_ms <= cutoff_ms
        if should_prune:
            matched.append(
                {
                    "key": key,
                    "sessionId": value.get("sessionId"),
                    "updatedAt": updated_at,
                    "model": value.get("model"),
                    "modelProvider": value.get("modelProvider"),
                }
            )
            continue

        kept[key] = value

    if not dry_run and len(kept) != len(store):
        save_json(store_path, kept)

    return {
        "agentId": agent_id,
        "storePath": str(store_path),
        "beforeCount": len(store),
        "afterCount": len(kept),
        "olderThanHours": older_than_hours,
        "modelIds": list(model_ids),
        "pruned": matched,
        "dryRun": dry_run,
    }


def replace_once(text: str, old: str, new: str, *, description: str) -> tuple[str, bool]:
    if new in text:
        return text, False
    if old not in text:
        raise ValueError(f"patch target not found for {description}")
    return text.replace(old, new, 1), True


def replace_when_present(text: str, old: str, new: str) -> tuple[str, bool]:
    if new in text:
        return text, False
    if old not in text:
        return text, False
    return text.replace(old, new, 1), True


def rewrite_file_if_needed(path: Path, replacements: Sequence[tuple[str, str]]) -> bool:
    if not path.exists():
        return False

    updated = path.read_text(encoding="utf-8")
    changed = False
    for old, new in replacements:
        updated, did_change = replace_when_present(updated, old, new)
        changed = changed or did_change

    if changed:
        path.write_text(updated, encoding="utf-8")
    return changed


def sync_tree_if_needed(source: Path, target: Path) -> bool:
    if not (source / "index.html").exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    return (target / "index.html").exists()


def ensure_control_ui_assets() -> dict[str, str | None]:
    result = {"cached_from": None, "restored_from": None}

    if not (CONTROL_UI_CACHE_DIR / "index.html").exists():
        for candidate in (CONTROL_UI_DIR, Path("/tmp/openclaw-source/dist/control-ui")):
            if sync_tree_if_needed(candidate, CONTROL_UI_CACHE_DIR):
                result["cached_from"] = str(candidate)
                break

    if (CONTROL_UI_DIR / "index.html").exists():
        return result

    for candidate in CONTROL_UI_FALLBACK_DIRS:
        if sync_tree_if_needed(candidate, CONTROL_UI_DIR):
            result["restored_from"] = str(candidate)
            break

    return result


def patch_host_plugin_sdk_legacy_exports() -> list[str]:
    path = HOST_PLUGIN_SDK_INDEX
    if not path.exists():
        return []

    marker = "// guardian legacy plugin-sdk compatibility exports"
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return []

    export_line = (
        "export { buildFalImageGenerationProvider, buildGoogleImageGenerationProvider, "
        "buildOpenAIImageGenerationProvider, delegateCompactionToRuntime, "
        "emptyPluginConfigSchema, onDiagnosticEvent, registerContextEngine };"
    )
    if export_line not in text:
        return []

    compat_block = (
        f"{marker}\n"
        'import { normalizeAccountId, DEFAULT_ACCOUNT_ID } from "./account-id.js";\n'
        'import { buildChannelConfigSchema } from "./channel-config-schema.js";\n'
        'import { createTypingCallbacks } from "./channel-runtime.js";\n'
        'import {\n'
        "  resolveDirectDmAuthorizationOutcome,\n"
        "  resolveSenderCommandAuthorizationWithRuntime,\n"
        '} from "./command-auth.js";\n'
        'import { formatPairingApproveHint } from "./core.js";\n'
        'import { resolvePreferredOpenClawTmpDir } from "./diffs.js";\n'
        'import { withFileLock, writeJsonAtomic } from "./infra-runtime.js";\n'
        'import { readJsonFileWithFallback } from "./json-store.js";\n'
        'import { addWildcardAllowFrom } from "./setup.js";\n'
        'import { stripMarkdown } from "./text-runtime.js";\n'
    )
    replacement = (
        compat_block
        + "export { buildFalImageGenerationProvider, buildGoogleImageGenerationProvider, "
        + "buildOpenAIImageGenerationProvider, delegateCompactionToRuntime, "
        + "emptyPluginConfigSchema, onDiagnosticEvent, registerContextEngine, "
        + "DEFAULT_ACCOUNT_ID, addWildcardAllowFrom, buildChannelConfigSchema, "
        + "createTypingCallbacks, formatPairingApproveHint, normalizeAccountId, "
        + "readJsonFileWithFallback, resolveDirectDmAuthorizationOutcome, "
        + "resolvePreferredOpenClawTmpDir, resolveSenderCommandAuthorizationWithRuntime, "
        + "stripMarkdown, withFileLock, writeJsonAtomic as writeJsonFileAtomically };"
    )
    path.write_text(text.replace(export_line, replacement, 1), encoding="utf-8")
    return [str(path)]


def patch_openclaw_weixin_plugin_sdk_imports() -> list[str]:
    replacements: dict[Path, list[tuple[str, str]]] = {
        WEIXIN_PLUGIN_DIR / "index.ts": [
            (
                'import { buildChannelConfigSchema } from "openclaw/plugin-sdk";\n',
                'import { buildChannelConfigSchema } from "openclaw/plugin-sdk/channel-config-schema";\n',
            )
        ],
        WEIXIN_PLUGIN_DIR / "src" / "channel.ts": [
            (
                'import type { ChannelPlugin, OpenClawConfig } from "openclaw/plugin-sdk";\n'
                'import { normalizeAccountId, resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk";\n',
                'import type { ChannelPlugin, OpenClawConfig } from "openclaw/plugin-sdk";\n'
                'import { normalizeAccountId } from "openclaw/plugin-sdk/account-id";\n'
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk/diffs";\n',
            )
        ],
        WEIXIN_PLUGIN_DIR / "src" / "log-upload.ts": [
            (
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk";\n',
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk/diffs";\n',
            )
        ],
        WEIXIN_PLUGIN_DIR / "src" / "util" / "logger.ts": [
            (
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk";\n',
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk/diffs";\n',
            )
        ],
        WEIXIN_PLUGIN_DIR / "src" / "auth" / "accounts.ts": [
            (
                'import { normalizeAccountId } from "openclaw/plugin-sdk";\n',
                'import { normalizeAccountId } from "openclaw/plugin-sdk/account-id";\n',
            )
        ],
        WEIXIN_PLUGIN_DIR / "src" / "auth" / "pairing.ts": [
            (
                'import { withFileLock } from "openclaw/plugin-sdk";\n',
                'import { withFileLock } from "openclaw/plugin-sdk/infra-runtime";\n',
            )
        ],
        WEIXIN_PLUGIN_DIR / "src" / "messaging" / "send.ts": [
            (
                'import { stripMarkdown } from "openclaw/plugin-sdk";\n',
                'import { stripMarkdown } from "openclaw/plugin-sdk/text-runtime";\n',
            )
        ],
        WEIXIN_PLUGIN_DIR / "src" / "messaging" / "process-message.ts": [
            (
                'import {\n'
                '  createTypingCallbacks,\n'
                '  resolveSenderCommandAuthorizationWithRuntime,\n'
                '  resolveDirectDmAuthorizationOutcome,\n'
                '  resolvePreferredOpenClawTmpDir,\n'
                '} from "openclaw/plugin-sdk";\n'
                'import type { PluginRuntime } from "openclaw/plugin-sdk";\n',
                'import { createTypingCallbacks } from "openclaw/plugin-sdk/channel-runtime";\n'
                'import {\n'
                '  resolveSenderCommandAuthorizationWithRuntime,\n'
                '  resolveDirectDmAuthorizationOutcome,\n'
                '} from "openclaw/plugin-sdk/command-auth";\n'
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk/diffs";\n'
                'import type { PluginRuntime } from "openclaw/plugin-sdk";\n',
            )
        ],
    }

    changed_paths: list[str] = []
    for path, file_replacements in replacements.items():
        if rewrite_file_if_needed(path, file_replacements):
            changed_paths.append(str(path))
    return changed_paths


def patch_wecom_plugin_sdk_imports() -> list[str]:
    replacements: dict[Path, list[tuple[str, str]]] = {
        WECOM_PLUGIN_DIR / "dist" / "index.esm.js": [
            (
                "import { readJsonFileWithFallback, withFileLock, writeJsonFileAtomically, DEFAULT_ACCOUNT_ID, addWildcardAllowFrom, formatPairingApproveHint, emptyPluginConfigSchema } from 'openclaw/plugin-sdk';\n",
                "import { emptyPluginConfigSchema } from 'openclaw/plugin-sdk';\n"
                "import { readJsonFileWithFallback } from 'openclaw/plugin-sdk/json-store';\n"
                "import { withFileLock, writeJsonAtomic as writeJsonFileAtomically } from 'openclaw/plugin-sdk/infra-runtime';\n"
                "import { DEFAULT_ACCOUNT_ID } from 'openclaw/plugin-sdk/account-id';\n"
                "import { addWildcardAllowFrom } from 'openclaw/plugin-sdk/setup';\n"
                "import { formatPairingApproveHint } from 'openclaw/plugin-sdk/core';\n",
            )
        ],
        WECOM_PLUGIN_DIR / "dist" / "index.cjs.js": [
            (
                "var pluginSdk = require('openclaw/plugin-sdk');\n",
                "var pluginSdk = Object.assign(\n"
                "    {},\n"
                "    require('openclaw/plugin-sdk'),\n"
                "    require('openclaw/plugin-sdk/json-store'),\n"
                "    {\n"
                "        withFileLock: require('openclaw/plugin-sdk/infra-runtime').withFileLock,\n"
                "        writeJsonFileAtomically: require('openclaw/plugin-sdk/infra-runtime').writeJsonAtomic,\n"
                "        DEFAULT_ACCOUNT_ID: require('openclaw/plugin-sdk/account-id').DEFAULT_ACCOUNT_ID,\n"
                "        addWildcardAllowFrom: require('openclaw/plugin-sdk/setup').addWildcardAllowFrom,\n"
                "        formatPairingApproveHint: require('openclaw/plugin-sdk/core').formatPairingApproveHint\n"
                "    }\n"
                ");\n",
            )
        ],
    }

    changed_paths: list[str] = []
    for path, file_replacements in replacements.items():
        if rewrite_file_if_needed(path, file_replacements):
            changed_paths.append(str(path))
    return changed_paths


def ensure_plugin_sdk_compatibility_patches() -> list[str]:
    changed_paths: list[str] = []
    changed_paths.extend(patch_host_plugin_sdk_legacy_exports())
    changed_paths.extend(patch_openclaw_weixin_plugin_sdk_imports())
    changed_paths.extend(patch_wecom_plugin_sdk_imports())
    return changed_paths


def deep_delete(target: dict, keys: Sequence[str]) -> bool:
    current = target
    parents: list[tuple[dict, str]] = []
    for key in keys[:-1]:
        existing = current.get(key)
        if not isinstance(existing, dict):
            return False
        parents.append((current, key))
        current = existing
    leaf = keys[-1]
    if leaf not in current:
        return False
    del current[leaf]
    for parent, key in reversed(parents):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            del parent[key]
        else:
            break
    return True


def has_nonempty_string_items(value) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if isinstance(item, str) and item.strip():
            return True
    return False


def normalize_group_policy(payload: dict) -> list[str]:
    channels = payload.get("channels")
    if not isinstance(channels, dict):
        return []

    changed: list[str] = []
    for channel in GROUP_POLICY_CHANNELS:
        channel_cfg = channels.get(channel)
        if not isinstance(channel_cfg, dict):
            continue
        if channel_cfg.get("groupPolicy") != "allowlist":
            continue

        has_allowlist = has_nonempty_string_items(channel_cfg.get("allowFrom")) or has_nonempty_string_items(
            channel_cfg.get("groupAllowFrom")
        )
        if has_allowlist:
            continue

        channel_cfg["groupPolicy"] = EXPECTED_GROUP_POLICY_FALLBACK
        changed.append(channel)

    return changed


def plugin_installed_in_config(payload: dict, plugin_id: str) -> bool:
    installs = payload.get("plugins", {}).get("installs", {})
    if not isinstance(installs, dict):
        return False
    install = installs.get(plugin_id)
    return isinstance(install, dict)


def resolve_runtime_validator_module() -> Path | None:
    candidates = sorted(DIST_DIR.glob("io-*.js"))
    return candidates[-1] if candidates else None


def resolve_invalid_plugin_ids_via_runtime(payload: dict) -> set[str] | None:
    module_path = resolve_runtime_validator_module()
    if module_path is None:
        return None

    node_bin = NODE22_BIN if NODE22_BIN.exists() else Path("node")
    workspace_dir = payload.get("agents", {}).get("defaults", {}).get("workspace") if isinstance(payload.get("agents"), dict) else None
    script = """
import fs from "node:fs";

const validatorModule = await import(process.env.OPENCLAW_VALIDATOR_MODULE);
const validateConfig =
  validatorModule.validateConfigObjectWithPlugins ??
  Object.values(validatorModule).find(
    (value) => typeof value === "function" && value.name === "validateConfigObjectWithPlugins",
  );

if (typeof validateConfig !== "function") {
  throw new Error("validateConfigObjectWithPlugins export not found");
}

const cfg = JSON.parse(fs.readFileSync(process.env.OPENCLAW_CONFIG_JSON, "utf8"));
const result = validateConfig(cfg, { env: process.env });
const messages = [...(result?.issues ?? []), ...(result?.warnings ?? [])]
  .map((entry) => String(entry?.message ?? ""));
const invalidPluginIds = [...new Set(messages.map((message) => {
  const match = message.match(/^plugin (?:removed|not found): ([^ ]+)/);
  return match ? match[1] : null;
}).filter(Boolean))].sort();

console.log(JSON.stringify({ invalidPluginIds }));
"""

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        temp_config_path = Path(handle.name)

    env = os.environ.copy()
    env["OPENCLAW_VALIDATOR_MODULE"] = str(module_path)
    env["OPENCLAW_CONFIG_JSON"] = str(temp_config_path)
    if isinstance(workspace_dir, str) and workspace_dir.strip():
        env["OPENCLAW_WORKSPACE_DIR"] = workspace_dir.strip()

    try:
        result = subprocess.run(
            [str(node_bin), "--input-type=module", "-e", script],
            cwd=str(ROOT_DIR),
            text=True,
            capture_output=True,
            timeout=30,
            env=env,
            check=False,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
        log_line(f"guardian config normalize: runtime validator unavailable: {exc}")
        return None
    finally:
        try:
            temp_config_path.unlink()
        except FileNotFoundError:
            pass

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        log_line(f"guardian config normalize: runtime validator failed: {detail}")
        return None

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        log_line(f"guardian config normalize: runtime validator returned invalid JSON: {exc}")
        return None

    invalid_ids = payload.get("invalidPluginIds", [])
    if not isinstance(invalid_ids, list):
        return None
    return {str(item).strip() for item in invalid_ids if str(item).strip()}


def prune_invalid_plugin_references(payload: dict) -> list[str]:
    invalid_ids = resolve_invalid_plugin_ids_via_runtime(payload)
    if not invalid_ids:
        return []

    plugins = payload.get("plugins")
    if not isinstance(plugins, dict):
        return []

    changes: list[str] = []
    invalid = set(invalid_ids)

    for list_key in ("allow", "deny"):
        values = plugins.get(list_key)
        if not isinstance(values, list):
            continue
        filtered = [item for item in values if str(item).strip() not in invalid]
        if filtered != values:
            plugins[list_key] = filtered
            changes.append(f"plugins.{list_key}")

    for record_key in ("entries", "installs"):
        records = plugins.get(record_key)
        if not isinstance(records, dict):
            continue
        removed = [plugin_id for plugin_id in list(records.keys()) if plugin_id in invalid]
        if not removed:
            continue
        for plugin_id in removed:
            del records[plugin_id]
        changes.append(f"plugins.{record_key}")

    slots = plugins.get("slots")
    if isinstance(slots, dict):
        memory_slot = slots.get("memory")
        if isinstance(memory_slot, str) and memory_slot.strip() in invalid:
            del slots["memory"]
            changes.append("plugins.slots.memory")

    return changes


def merge_plugin_records(payload: dict, section: str, source_id: str, target_id: str) -> bool:
    plugins = payload.get("plugins")
    if not isinstance(plugins, dict):
        return False

    records = plugins.get(section)
    if not isinstance(records, dict) or source_id not in records:
        return False

    source_record = records.get(source_id)
    target_record = records.get(target_id)

    if isinstance(source_record, dict):
        merged = dict(source_record)
        if isinstance(target_record, dict):
            merged.update(target_record)
        records[target_id] = merged
    elif target_id not in records:
        records[target_id] = source_record

    if source_id != target_id:
        del records[source_id]
    return True


def normalize_plugin_allowlist(payload: dict, *, should_enable_wecom: bool) -> bool:
    plugins = payload.get("plugins")
    if not isinstance(plugins, dict):
        return False

    allow = plugins.get("allow")
    if not isinstance(allow, list):
        return False

    changed = False
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_item in allow:
        item = str(raw_item).strip()
        if not item:
            changed = True
            continue
        if item == WECOM_CHANNEL_ID:
            item = WECOM_PLUGIN_ID
            changed = True
        if item in seen:
            changed = True
            continue
        seen.add(item)
        normalized.append(item)

    if should_enable_wecom and WECOM_PLUGIN_ID not in seen:
        normalized.append(WECOM_PLUGIN_ID)
        changed = True

    if changed:
        plugins["allow"] = normalized
    return changed


def normalize_wecom_plugin_config(payload: dict) -> list[str]:
    changes: list[str] = []
    channels = payload.get("channels")
    wecom_channel = channels.get(WECOM_CHANNEL_ID) if isinstance(channels, dict) else None
    has_wecom_channel = isinstance(wecom_channel, dict) and bool(wecom_channel.get("enabled"))

    if merge_plugin_records(payload, "entries", WECOM_CHANNEL_ID, WECOM_PLUGIN_ID):
        changes.append("plugins.entries")
    if merge_plugin_records(payload, "installs", WECOM_CHANNEL_ID, WECOM_PLUGIN_ID):
        changes.append("plugins.installs")

    plugins = payload.get("plugins")
    if isinstance(plugins, dict):
        installs = plugins.get("installs")
        if isinstance(installs, dict):
            install = installs.get(WECOM_PLUGIN_ID)
            if isinstance(install, dict):
                if install.get("resolvedName") != WECOM_PLUGIN_PACKAGE:
                    install["resolvedName"] = WECOM_PLUGIN_PACKAGE
                    changes.append("plugins.installs.resolvedName")
                if install.get("resolvedSpec") != f"{WECOM_PLUGIN_PACKAGE}@{install.get('version')}" and install.get("version"):
                    install["resolvedSpec"] = f"{WECOM_PLUGIN_PACKAGE}@{install.get('version')}"
                    changes.append("plugins.installs.resolvedSpec")

        entries = plugins.get("entries")
        if isinstance(entries, dict):
            wecom_entry = entries.get(WECOM_PLUGIN_ID)
            if has_wecom_channel and not isinstance(wecom_entry, dict):
                entries[WECOM_PLUGIN_ID] = {"enabled": True}
                changes.append("plugins.entries.enable-wecom")
            elif has_wecom_channel and isinstance(wecom_entry, dict) and wecom_entry.get("enabled") is not True:
                wecom_entry["enabled"] = True
                changes.append("plugins.entries.enabled")

    should_enable_wecom = has_wecom_channel or plugin_installed_in_config(payload, WECOM_PLUGIN_ID)
    if normalize_plugin_allowlist(payload, should_enable_wecom=should_enable_wecom):
        changes.append("plugins.allow")

    return changes


def patch_text(path: Path, text: str) -> tuple[str, bool]:
    updated = text
    changed = False

    if path.name.startswith("channel-web-") or path.name.startswith("web-"):
        updated, did_change = replace_when_present(
            updated,
            "const MESSAGE_TIMEOUT_MS = tuning.messageTimeoutMs ?? 1800 * 1e3;",
            "const MESSAGE_TIMEOUT_MS = tuning.messageTimeoutMs ?? 24 * 60 * 60 * 1e3;",
        )
        changed = changed or did_change
        updated, did_change = replace_when_present(
            updated,
            "...minutesSinceLastMessage !== null && minutesSinceLastMessage > 30 ? { minutesSinceLastMessage } : {}",
            "...minutesSinceLastMessage !== null && minutesSinceLastMessage > 24 * 60 ? { minutesSinceLastMessage } : {}",
        )
        changed = changed or did_change
        updated, did_change = replace_when_present(
            updated,
            'if (minutesSinceLastMessage && minutesSinceLastMessage > 30) heartbeatLogger.warn(logData, "⚠️ web gateway heartbeat - no messages in 30+ minutes");',
            'if (minutesSinceLastMessage && minutesSinceLastMessage > 24 * 60) heartbeatLogger.warn(logData, "⚠️ web gateway heartbeat - no messages in 24h+ standby");',
        )
        changed = changed or did_change
        updated, did_change = replace_when_present(
            updated,
            "await processForRoute(msg, route, groupHistoryKey);",
            """try {\n\t\t\tawait processForRoute(msg, route, groupHistoryKey);\n\t\t} catch (err) {\n\t\t\tconst errText = String(err);\n\t\t\tconst transientReadFailure = errText.includes("Unknown system error -11") && errText.includes("read");\n\t\t\tif (!transientReadFailure) throw err;\n\t\t\tparams.replyLogger.warn({ error: errText, code: err?.code, errno: err?.errno, syscall: err?.syscall }, "transient inbound read failure; retrying once");\n\t\t\tawait sleepWithAbort(250);\n\t\t\tawait processForRoute(msg, route, groupHistoryKey);\n\t\t}""",
        )
        changed = changed or did_change

    return updated, changed


def patch_runtime(*, dry_run: bool) -> dict[str, list[str]]:
    targets: list[Path] = []
    seen: set[Path] = set()
    for pattern in RUNTIME_PATCH_GLOBS:
        for candidate in sorted(DIST_DIR.glob(pattern)):
            if candidate in seen:
                continue
            seen.add(candidate)
            targets.append(candidate)
    applied: list[str] = []
    skipped: list[str] = []

    if not DIST_DIR.exists():
        raise FileNotFoundError(f"OpenClaw dist not found: {DIST_DIR}")

    backup_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = OPENCLAW_BACKUP_DIR / backup_stamp

    for target in targets:
        rel = str(target.relative_to(DIST_DIR))
        if not target.exists():
            skipped.append(f"{rel}:missing")
            continue
        original = target.read_text(encoding="utf-8")
        updated, changed = patch_text(target, original)
        if not changed:
            skipped.append(f"{rel}:already-patched")
            continue
        if dry_run:
            applied.append(f"{rel}:would-patch")
            continue
        backup_target = backup_dir / rel
        ensure_parent(backup_target)
        backup_target.write_text(original, encoding="utf-8")
        target.write_text(updated, encoding="utf-8")
        applied.append(f"{rel}:patched")

    return {"applied": applied, "skipped": skipped}


def configure_openclaw(*, dry_run: bool) -> dict:
    payload = load_json(OPENCLAW_CONFIG, {})
    if not isinstance(payload, dict):
        raise ValueError(f"invalid config: {OPENCLAW_CONFIG}")
    original = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    deep_set(payload, ["agents", "defaults", "heartbeat", "every"], EXPECTED_AGENT_HEARTBEAT_EVERY)
    deep_set(payload, ["web", "heartbeatSeconds"], EXPECTED_WEB_HEARTBEAT_SECONDS)
    deep_set(payload, ["gateway", "channelHealthCheckMinutes"], EXPECTED_CHANNEL_HEALTH_CHECK_MINUTES)
    normalize_group_policy(payload)
    normalize_wecom_plugin_config(payload)
    prune_invalid_plugin_references(payload)

    # Keep config compatible across OpenClaw releases: never persist these
    # optional tuning keys because unsupported versions reject them as invalid.
    deep_delete(payload, ["web", "messageTimeoutMs"])
    deep_delete(payload, ["web", "watchdogCheckMs"])
    deep_delete(payload, ["gateway", "channelHealth"])
    if not dry_run:
        ensure_shared_openclaw_package_link()
        control_ui_assets = ensure_control_ui_assets()
        if control_ui_assets["cached_from"]:
            log_line(
                "guardian config normalize: cached Control UI assets from "
                + control_ui_assets["cached_from"]
            )
        if control_ui_assets["restored_from"]:
            log_line(
                "guardian config normalize: restored Control UI assets from "
                + control_ui_assets["restored_from"]
            )
        patched_plugins = ensure_plugin_sdk_compatibility_patches()
        if patched_plugins:
            log_line(
                "guardian config normalize: patched plugin-sdk imports for "
                + ", ".join(patched_plugins)
            )

    if not dry_run and json.dumps(payload, ensure_ascii=False, sort_keys=True) != original:
        backup_stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = OPENCLAW_BACKUP_DIR / backup_stamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        if OPENCLAW_CONFIG.exists():
            (backup_dir / OPENCLAW_CONFIG.name).write_text(OPENCLAW_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
        save_json(OPENCLAW_CONFIG, payload)

    return payload


def render_launch_agent_plist() -> str:
    python_bin = sys.executable or "/usr/bin/python3"
    stdout_path = OPENCLAW_LOG_DIR / "guardian.launchd.log"
    stderr_path = OPENCLAW_LOG_DIR / "guardian.launchd.err.log"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>ai.openclaw.guardian</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>WorkingDirectory</key>
    <string>{ROOT_DIR}</string>
    <key>ProgramArguments</key>
    <array>
      <string>{python_bin}</string>
      <string>{ROOT_DIR / "scripts" / "openclaw_guardian.py"}</string>
      <string>check-once</string>
      <string>--verbose</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
      <key>HOME</key>
      <string>{Path.home()}</string>
      <key>PATH</key>
      <string>{Path.home() / ".local" / "bin"}:{Path.home() / ".npm-global" / "bin"}:{Path.home() / "bin"}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>StandardOutPath</key>
    <string>{stdout_path}</string>
    <key>StandardErrorPath</key>
    <string>{stderr_path}</string>
  </dict>
</plist>
"""


def recent_log_paths() -> list[Path]:
    paths: list[Path] = []
    tmp_dir = Path("/tmp/openclaw")
    if tmp_dir.exists():
        paths.extend(sorted(tmp_dir.glob("openclaw-*.log"))[-2:])
    for candidate in [
        OPENCLAW_LOG_DIR / "gateway.log",
        OPENCLAW_LOG_DIR / "gateway.err.log",
        OPENCLAW_LOG_DIR / "guardian.launchd.err.log",
    ]:
        if candidate.exists():
            paths.append(candidate)
    return paths


def extract_line_timestamp(line: str) -> datetime | None:
    match = re.search(r'"time":"([^"]+)"', line)
    if match:
        return parse_iso(match.group(1))
    match = re.match(r"\[([^\]]+)\]", line)
    if match:
        return parse_iso(match.group(1))
    return None


def is_cli_diagnostic_line(line: str) -> bool:
    return '"name":"openclaw"' in line and (
        "Gateway not reachable" in line
        or PATTERN_FETCH_FAILED in line
        or PATTERN_ABNORMAL_CLOSE in line
    )


def tail_lines(path: Path, *, max_lines: int = 800) -> list[str]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=max_lines))


def extract_backoff_model(line: str) -> str | None:
    match = re.search(r"overload backoff before failover for ([^:\"]+)", line)
    if not match:
        return None
    return match.group(1).strip() or None


def collect_recent_incidents(paths: Iterable[Path], *, lookback_minutes: int) -> IncidentSummary:
    cutoff = now_utc() - timedelta(minutes=lookback_minutes)
    counts = {
        "unknown_read": 0,
        "abnormal_close": 0,
        "fetch_failed": 0,
        "max_attempts": 0,
        "stale_socket": 0,
        "dns_lookup": 0,
        "transport_timeout": 0,
    }
    latest = {key: None for key in counts}
    events = {key: [] for key in counts}

    for path in paths:
        for raw_line in tail_lines(path):
            line = raw_line.strip()
            if not line:
                continue
            timestamp = extract_line_timestamp(line)
            if timestamp is None:
                continue
            if timestamp < cutoff:
                continue
            if PATTERN_UNKNOWN_READ in line:
                counts["unknown_read"] += 1
                latest["unknown_read"] = timestamp.isoformat()
                events["unknown_read"].append(timestamp.isoformat())
            if PATTERN_ABNORMAL_CLOSE in line and not is_cli_diagnostic_line(line):
                counts["abnormal_close"] += 1
                latest["abnormal_close"] = timestamp.isoformat()
                events["abnormal_close"].append(timestamp.isoformat())
            if PATTERN_FETCH_FAILED in line and not is_cli_diagnostic_line(line):
                counts["fetch_failed"] += 1
                latest["fetch_failed"] = timestamp.isoformat()
                events["fetch_failed"].append(timestamp.isoformat())
            if PATTERN_MAX_ATTEMPTS in line:
                counts["max_attempts"] += 1
                latest["max_attempts"] = timestamp.isoformat()
                events["max_attempts"].append(timestamp.isoformat())
            if PATTERN_STALE_SOCKET in line:
                counts["stale_socket"] += 1
                latest["stale_socket"] = timestamp.isoformat()
                events["stale_socket"].append(timestamp.isoformat())
            if PATTERN_DNS_LOOKUP in line:
                counts["dns_lookup"] += 1
                latest["dns_lookup"] = timestamp.isoformat()
                events["dns_lookup"].append(timestamp.isoformat())
            if PATTERN_DNS_LOOKUP not in line and (
                PATTERN_CONNECT_TIMEOUT in line
                or 'statusCode":408' in line
                or "status 408" in line
                or "Request Time-out" in line
            ):
                counts["transport_timeout"] += 1
                latest["transport_timeout"] = timestamp.isoformat()
                events["transport_timeout"].append(timestamp.isoformat())

    return IncidentSummary(counts=counts, latest=latest, events=events)


def collect_recent_model_failures(paths: Iterable[Path], *, lookback_minutes: int) -> ModelFailureSummary:
    cutoff = now_utc() - timedelta(minutes=lookback_minutes)
    counts = {
        "overloaded": 0,
        "http_504": 0,
        "failover_error": 0,
        "backoff": 0,
        "improper_400": 0,
    }
    events: list[ModelFailureEvent] = []

    for path in paths:
        for raw_line in tail_lines(path):
            line = raw_line.strip()
            if not line:
                continue
            timestamp = extract_line_timestamp(line)
            if timestamp is None or timestamp < cutoff:
                continue

            kind: str | None = None
            model: str | None = None
            if PATTERN_MODEL_BACKOFF in line:
                kind = "backoff"
                model = extract_backoff_model(line)
            elif PATTERN_MODEL_IMPROPER_400 in line:
                kind = "improper_400"
            elif PATTERN_MODEL_HTTP_504 in line:
                kind = "http_504"
            elif PATTERN_MODEL_FAILOVER in line:
                kind = "failover_error"
            elif PATTERN_MODEL_OVERLOADED in line:
                kind = "overloaded"
            else:
                continue

            counts[kind] += 1
            events.append(
                ModelFailureEvent(
                    timestamp=timestamp.isoformat(),
                    kind=kind,
                    model=model,
                    line=line[:240],
                )
            )

    latest = max((event.timestamp for event in events), default=None)
    return ModelFailureSummary(counts=counts, latest=latest, events=events)


def count_model_events_after(summary: ModelFailureSummary, handled_after: datetime | None) -> int:
    total = 0
    for event in summary.events:
        timestamp = parse_iso(event.timestamp)
        if timestamp is None:
            continue
        if handled_after is None or timestamp > handled_after:
            total += 1
    return total


def normalize_fallback_chain(primary: str, fallbacks: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_model in fallbacks:
        model = str(raw_model).strip()
        if not model or model == primary or model in seen:
            continue
        seen.add(model)
        normalized.append(model)
    return normalized


def model_identity_matches(expected: str, actual: str) -> bool:
    expected_model = str(expected).strip()
    actual_model = str(actual).strip()
    if not expected_model or not actual_model:
        return False
    if expected_model == actual_model:
        return True
    if "/" in expected_model and "/" not in actual_model:
        return expected_model.split("/", 1)[1] == actual_model
    if "/" not in expected_model and "/" in actual_model:
        return expected_model == actual_model.split("/", 1)[1]
    return False


def compute_promoted_routing(primary: str, fallbacks: Sequence[str]) -> tuple[str, list[str]] | None:
    normalized = normalize_fallback_chain(primary, fallbacks)
    if not normalized:
        return None
    promoted_primary = normalized[0]
    promoted_fallbacks = normalize_fallback_chain(
        promoted_primary,
        [primary, *normalized[1:]],
    )
    return promoted_primary, promoted_fallbacks


def describe_model_failures(summary: ModelFailureSummary, *, handled_after: datetime | None) -> str:
    counts: dict[str, int] = {}
    for event in summary.events:
        timestamp = parse_iso(event.timestamp)
        if timestamp is None:
            continue
        if handled_after is not None and timestamp <= handled_after:
            continue
        counts[event.kind] = counts.get(event.kind, 0) + 1

    if not counts:
        return "none"

    parts = []
    for key in ("overloaded", "http_504", "failover_error", "backoff", "improper_400"):
        value = counts.get(key, 0)
        if value:
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def is_listener_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 18789), timeout=2):
            return True
    except OSError:
        return False


def is_node22_binary(node_path: str | None) -> bool:
    if not node_path:
        return False
    try:
        result = subprocess.run(
            [node_path, "-v"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    version = (result.stdout or result.stderr or "").strip()
    return result.returncode == 0 and bool(re.match(r"^v22\.", version))


def launchagent_node_path() -> str | None:
    plist = Path.home() / "Library" / "LaunchAgents" / "ai.openclaw.gateway.plist"
    if not plist.exists():
        return None
    try:
        with plist.open("rb") as handle:
            payload = plistlib.load(handle)
    except Exception:
        content = plist.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"<string>([^<]*/node(?:@22)?/bin/node|[^<]*/node)</string>", content)
        return match.group(1) if match else None

    argv = payload.get("ProgramArguments")
    if isinstance(argv, list) and argv:
        first = argv[0]
        if isinstance(first, str):
            return first
    return None


def is_launchagent_node22() -> bool:
    return is_node22_binary(launchagent_node_path())


def load_openclaw_status() -> str:
    result = run_command(["openclaw", "status"], timeout=20)
    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    return output


def whatsapp_linked(status_output: str) -> bool:
    for line in status_output.splitlines():
        if "WhatsApp" in line and "linked" in line:
            return True
    return False


def latest_incident_after(summary: IncidentSummary, handled_after: datetime | None, key: str) -> bool:
    latest = parse_iso(summary.latest.get(key))
    if latest is None:
        return False
    if handled_after is None:
        return True
    return latest > handled_after


def incident_count_after(summary: IncidentSummary, handled_after: datetime | None, key: str) -> int:
    total = 0
    for value in summary.events.get(key, []):
        timestamp = parse_iso(value)
        if timestamp is None:
            continue
        if handled_after is None or timestamp > handled_after:
            total += 1
    return total


def load_model_routing() -> dict[str, object]:
    result = run_command(["openclaw", "config", "get", "agents.defaults.model"], timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "openclaw config get failed")

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid model routing JSON: {exc}") from exc

    primary = str(payload.get("primary") or "").strip()
    if not primary:
        raise RuntimeError("agents.defaults.model.primary is empty")

    fallbacks = normalize_fallback_chain(primary, payload.get("fallbacks") or [])
    return {"primary": primary, "fallbacks": fallbacks}


def set_model_routing(primary: str, fallbacks: Sequence[str]) -> tuple[bool, str]:
    desired_fallbacks = normalize_fallback_chain(primary, fallbacks)
    current = load_model_routing()
    current_primary = str(current["primary"])
    current_fallbacks = normalize_fallback_chain(current_primary, current.get("fallbacks") or [])

    if current_primary != primary:
        result = run_command(["openclaw", "models", "set", primary], timeout=60)
        if result.returncode != 0:
            return False, result.stderr.strip() or result.stdout.strip() or "openclaw models set failed"

    if current_fallbacks != desired_fallbacks:
        result = run_command(["openclaw", "models", "fallbacks", "clear"], timeout=60)
        if result.returncode != 0:
            return False, result.stderr.strip() or result.stdout.strip() or "openclaw models fallbacks clear failed"
        for model in desired_fallbacks:
            add_result = run_command(["openclaw", "models", "fallbacks", "add", model], timeout=60)
            if add_result.returncode != 0:
                return False, add_result.stderr.strip() or add_result.stdout.strip() or f"failed to add fallback {model}"

    return True, "updated"


def cleanup_probe_agent() -> None:
    run_command(
        ["openclaw", "agents", "delete", "--force", "--json", MODEL_PROBE_AGENT_ID],
        timeout=60,
    )


def probe_model_with_agent(model_id: str) -> tuple[bool, str]:
    MODEL_PROBE_WORKSPACE.mkdir(parents=True, exist_ok=True)
    cleanup_probe_agent()

    add_result = run_command(
        [
            "openclaw",
            "agents",
            "add",
            MODEL_PROBE_AGENT_ID,
            "--workspace",
            str(MODEL_PROBE_WORKSPACE),
            "--model",
            model_id,
            "--non-interactive",
            "--json",
        ],
        timeout=60,
    )
    if add_result.returncode != 0:
        return False, add_result.stderr.strip() or add_result.stdout.strip() or "probe agent create failed"

    session_id = f"{MODEL_PROBE_AGENT_ID}-{int(time.time())}"
    probe_result = run_command(
        [
            "openclaw",
            "agent",
            "--agent",
            MODEL_PROBE_AGENT_ID,
            "--session-id",
            session_id,
            "--message",
            MODEL_PROBE_MESSAGE,
            "--timeout",
            str(MODEL_PROBE_TIMEOUT_SECONDS),
            "--json",
        ],
        timeout=MODEL_PROBE_TIMEOUT_SECONDS + 45,
        cwd=MODEL_PROBE_WORKSPACE,
    )
    cleanup_probe_agent()

    if probe_result.returncode != 0:
        return False, probe_result.stderr.strip() or probe_result.stdout.strip() or "probe run failed"

    try:
        payload = json.loads(probe_result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return False, f"probe returned invalid JSON: {exc}"

    status = str(payload.get("status") or "").strip()
    agent_meta = payload.get("result", {}).get("meta", {}).get("agentMeta", {})
    actual_model = str(agent_meta.get("model") or "").strip()
    if status != "ok":
        return False, str(payload.get("summary") or payload.get("error") or "probe status not ok")
    if not model_identity_matches(model_id, actual_model):
        return False, f"probe used unexpected model: {actual_model or 'unknown'}"
    return True, f"probe ok via {actual_model}"


def record_restart_state(state: dict, *, now: datetime, reasons: Sequence[str], handled_mark: datetime | None = None) -> None:
    recent_restarts = prune_restart_times(state.get("restart_times", []), now=now)
    recent_restarts.append(now.isoformat())
    state["restart_times"] = recent_restarts
    state["last_restart_at"] = now.isoformat()
    state["last_reasons"] = list(reasons)
    if handled_mark is not None:
        state["handled_through_ts"] = handled_mark.isoformat()


def handle_model_failover(*, state: dict, dry_run: bool, verbose: bool) -> tuple[bool, int, dict]:
    routing = load_model_routing()
    current_primary = str(routing["primary"])
    current_fallbacks = normalize_fallback_chain(current_primary, routing.get("fallbacks") or [])
    summary = collect_recent_model_failures(recent_log_paths(), lookback_minutes=MODEL_FAILURE_LOOKBACK_MINUTES)
    model_state = state.get("model_failover")
    if not isinstance(model_state, dict):
        model_state = {}
    state["model_failover"] = model_state
    now = now_utc()

    active = bool(model_state.get("active"))
    if not active:
        handled_after = parse_iso(model_state.get("handled_through_ts"))
        recent_failures = count_model_events_after(summary, handled_after)
        if recent_failures < MODEL_FAILURE_PROMOTE_THRESHOLD:
            return False, 0, {
                "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
                "recent_failures": recent_failures,
                "recent_counts": summary.counts,
                "latest_failure": summary.latest,
                "active": False,
            }

        promoted = compute_promoted_routing(current_primary, current_fallbacks)
        if promoted is None:
            model_state["handled_through_ts"] = summary.latest or now.isoformat()
            log_line("guardian model failover: primary unhealthy but no fallback configured", also_stdout=verbose)
            return False, 0, {
                "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
                "recent_failures": recent_failures,
                "recent_counts": summary.counts,
                "latest_failure": summary.latest,
                "active": False,
            }

        promoted_primary, promoted_fallbacks = promoted
        failure_detail = describe_model_failures(summary, handled_after=handled_after)
        if dry_run:
            log_line(
                f"guardian model failover: would promote {promoted_primary} over {current_primary} ({failure_detail})",
                also_stdout=verbose,
            )
            return True, 0, {
                "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
                "promotion_target": {"primary": promoted_primary, "fallbacks": promoted_fallbacks},
                "recent_failures": recent_failures,
                "recent_counts": summary.counts,
                "latest_failure": summary.latest,
                "active": False,
                "dry_run": True,
            }

        ok, detail = set_model_routing(promoted_primary, promoted_fallbacks)
        if not ok:
            model_state["last_action"] = "promote-failed"
            model_state["last_action_detail"] = detail
            log_line(
                f"guardian model failover: failed to promote {promoted_primary} over {current_primary}: {detail}",
                also_stdout=verbose,
            )
            return True, 1, {
                "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
                "promotion_target": {"primary": promoted_primary, "fallbacks": promoted_fallbacks},
                "recent_failures": recent_failures,
                "recent_counts": summary.counts,
                "latest_failure": summary.latest,
                "active": False,
                "error": detail,
            }

        model_state.update(
            {
                "active": True,
                "baseline_primary": current_primary,
                "baseline_fallbacks": current_fallbacks,
                "promoted_primary": promoted_primary,
                "promoted_fallbacks": promoted_fallbacks,
                "promoted_at": now.isoformat(),
                "last_failure_at": summary.latest or now.isoformat(),
                "handled_through_ts": summary.latest or now.isoformat(),
                "last_probe_at": None,
                "last_probe_result": None,
                "last_action": "promote",
                "last_action_detail": failure_detail,
            }
        )
        restart_ok = stable_restart(verbose=verbose)
        if restart_ok:
            handled_mark = now_utc()
            record_restart_state(state, now=now, reasons=["model-primary-promoted"], handled_mark=handled_mark)
            model_state["handled_through_ts"] = handled_mark.isoformat()
            log_line(
                f"guardian model failover: promoted {promoted_primary} over {current_primary} and restarted gateway",
                also_stdout=verbose,
            )
            return True, 0, {
                "routing": {"primary": promoted_primary, "fallbacks": promoted_fallbacks},
                "recent_failures": recent_failures,
                "recent_counts": summary.counts,
                "latest_failure": summary.latest,
                "active": True,
            }

        record_restart_state(state, now=now, reasons=["model-primary-promoted"])
        log_line(
            f"guardian model failover: promoted {promoted_primary} over {current_primary} but restart failed",
            also_stdout=verbose,
        )
        return True, 1, {
            "routing": {"primary": promoted_primary, "fallbacks": promoted_fallbacks},
            "recent_failures": recent_failures,
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": True,
        }

    promoted_primary = str(model_state.get("promoted_primary") or "").strip()
    baseline_primary = str(model_state.get("baseline_primary") or "").strip()
    baseline_fallbacks = normalize_fallback_chain(baseline_primary, model_state.get("baseline_fallbacks") or [])
    if not promoted_primary or current_primary != promoted_primary:
        reset_model_failover_state(
            state,
            handled_at=summary.latest or now.isoformat(),
            reason="routing-drift",
        )
        log_line("guardian model failover: routing drift detected; clearing promotion state", also_stdout=verbose)
        return False, 0, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": False,
        }

    if baseline_primary and baseline_primary != current_primary and baseline_primary not in current_fallbacks:
        reset_model_failover_state(
            state,
            handled_at=summary.latest or now.isoformat(),
            reason="baseline-removed-from-routing",
        )
        log_line(
            f"guardian model failover: baseline {baseline_primary} no longer in current routing; clearing promotion state",
            also_stdout=verbose,
        )
        return False, 0, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": False,
        }

    latest_failure = parse_iso(model_state.get("last_failure_at"))
    summary_latest = parse_iso(summary.latest)
    if summary_latest is not None and (latest_failure is None or summary_latest > latest_failure):
        latest_failure = summary_latest
        model_state["last_failure_at"] = summary_latest.isoformat()

    quiet_since = latest_failure or parse_iso(model_state.get("promoted_at")) or now
    last_probe_at = parse_iso(model_state.get("last_probe_at"))
    if (now - quiet_since) < timedelta(minutes=MODEL_RECOVERY_QUIET_MINUTES):
        return False, 0, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": True,
            "quiet_for_minutes": int((now - quiet_since).total_seconds() // 60),
        }

    if last_probe_at is not None and (now - last_probe_at) < timedelta(minutes=MODEL_RECOVERY_PROBE_INTERVAL_MINUTES):
        return False, 0, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": True,
            "last_probe_at": last_probe_at.isoformat(),
        }

    if not baseline_primary:
        reset_model_failover_state(
            state,
            handled_at=now.isoformat(),
            reason="missing-baseline",
        )
        log_line("guardian model failover: missing baseline primary; clearing promotion state", also_stdout=verbose)
        return False, 0, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": False,
        }

    if dry_run:
        log_line(f"guardian model failover: would probe {baseline_primary} for recovery", also_stdout=verbose)
        return True, 0, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recovery_target": {"primary": baseline_primary, "fallbacks": baseline_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": True,
            "dry_run": True,
        }

    probe_ok, probe_detail = probe_model_with_agent(baseline_primary)
    model_state["last_probe_at"] = now.isoformat()
    model_state["last_probe_result"] = probe_detail
    if not probe_ok:
        model_state["last_failure_at"] = now.isoformat()
        model_state["last_action"] = "probe-failed"
        model_state["last_action_detail"] = probe_detail
        log_line(
            f"guardian model failover: recovery probe failed for {baseline_primary}: {probe_detail}",
            also_stdout=verbose,
        )
        return True, 0, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recovery_target": {"primary": baseline_primary, "fallbacks": baseline_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": True,
            "probe_result": probe_detail,
        }

    ok, detail = set_model_routing(baseline_primary, baseline_fallbacks)
    if not ok:
        model_state["last_action"] = "restore-failed"
        model_state["last_action_detail"] = detail
        log_line(
            f"guardian model failover: probe succeeded but restore failed for {baseline_primary}: {detail}",
            also_stdout=verbose,
        )
        return True, 1, {
            "routing": {"primary": current_primary, "fallbacks": current_fallbacks},
            "recovery_target": {"primary": baseline_primary, "fallbacks": baseline_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": True,
            "error": detail,
        }

    restart_ok = stable_restart(verbose=verbose)
    handled_mark = now_utc()
    if restart_ok:
        record_restart_state(state, now=now, reasons=["model-primary-restored"], handled_mark=handled_mark)
    else:
        record_restart_state(state, now=now, reasons=["model-primary-restored"])
    state["model_failover"] = {
        "active": False,
        "handled_through_ts": handled_mark.isoformat(),
        "baseline_primary": baseline_primary,
        "baseline_fallbacks": baseline_fallbacks,
        "last_failure_at": model_state.get("last_failure_at"),
        "last_probe_at": now.isoformat(),
        "last_probe_result": probe_detail,
        "last_action": "restore",
        "last_action_detail": probe_detail,
        "last_restored_at": now.isoformat(),
        "previous_promoted_primary": promoted_primary,
    }
    if restart_ok:
        log_line(
            f"guardian model failover: restored {baseline_primary} after successful probe and restarted gateway",
            also_stdout=verbose,
        )
        return True, 0, {
            "routing": {"primary": baseline_primary, "fallbacks": baseline_fallbacks},
            "recent_counts": summary.counts,
            "latest_failure": summary.latest,
            "active": False,
            "probe_result": probe_detail,
        }

    log_line(
        f"guardian model failover: restored {baseline_primary} but restart failed",
        also_stdout=verbose,
    )
    return True, 1, {
        "routing": {"primary": baseline_primary, "fallbacks": baseline_fallbacks},
        "recent_counts": summary.counts,
        "latest_failure": summary.latest,
        "active": False,
        "probe_result": probe_detail,
    }


def stable_restart(*, verbose: bool) -> bool:
    log_line("guardian action: running gateway_stable_start.sh", also_stdout=verbose)
    result = run_command(["bash", str(GATEWAY_STABLE_SCRIPT)], timeout=120)
    if result.returncode == 0:
        if verbose and result.stdout.strip():
            print(result.stdout.strip())
        log_line("guardian action: gateway_stable_start.sh succeeded", also_stdout=verbose)
        return True

    log_line("guardian action: stable start failed, falling back to install --force", also_stdout=verbose)
    install_result = run_command(["openclaw", "gateway", "install", "--force"], timeout=120)
    if install_result.returncode != 0:
        log_line(f"guardian action: install --force failed: {install_result.stderr.strip()}", also_stdout=verbose)
        return False

    retry = run_command(["bash", str(GATEWAY_STABLE_SCRIPT)], timeout=120)
    if retry.returncode == 0:
        if verbose and retry.stdout.strip():
            print(retry.stdout.strip())
        log_line("guardian action: stable start retry succeeded", also_stdout=verbose)
        return True

    log_line(f"guardian action: retry failed: {retry.stderr.strip()}", also_stdout=verbose)
    return False


def guardian_status_payload() -> dict:
    status_output = load_openclaw_status()
    incidents = collect_recent_incidents(recent_log_paths(), lookback_minutes=INCIDENT_LOOKBACK_MINUTES)
    model_failures = collect_recent_model_failures(recent_log_paths(), lookback_minutes=MODEL_FAILURE_LOOKBACK_MINUTES)
    main_session = inspect_main_webchat_session()
    try:
        model_routing = load_model_routing()
    except RuntimeError as exc:
        model_routing = {"error": str(exc)}
    state = load_guardian_state()
    return {
        "listener_up": is_listener_up(),
        "launchagent_node22": is_launchagent_node22(),
        "whatsapp_linked": whatsapp_linked(status_output),
        "incident_counts": incidents.counts,
        "incident_latest": incidents.latest,
        "main_webchat_session": main_session,
        "model_routing": model_routing,
        "model_failover": state.get("model_failover", {}),
        "model_failure_counts": model_failures.counts,
        "model_failure_latest": model_failures.latest,
        "state_file": str(GUARDIAN_STATE_FILE),
        "guardian_log": str(GUARDIAN_LOG_FILE),
    }


def check_once(*, dry_run: bool, force_restart: bool, verbose: bool) -> int:
    state = load_guardian_state()
    now = now_utc()
    recent_restarts = prune_restart_times(state.get("restart_times", []), now=now)
    handled_after = parse_iso(state.get("handled_through_ts"))
    incidents = collect_recent_incidents(recent_log_paths(), lookback_minutes=INCIDENT_LOOKBACK_MINUTES)
    status_output = load_openclaw_status()
    main_session_health = inspect_main_webchat_session()
    try:
        model_handled, model_code, model_payload = handle_model_failover(state=state, dry_run=dry_run, verbose=verbose)
    except RuntimeError as exc:
        model_handled = False
        model_code = 1
        model_payload = {"error": str(exc)}
        log_line(f"guardian model failover: skipped due to runtime error: {exc}", also_stdout=verbose)

    reasons: list[str] = []
    if force_restart:
        reasons.append("forced")
    if not is_listener_up():
        reasons.append("gateway-port-down")
    if not is_launchagent_node22():
        reasons.append("gateway-node-drift")
    if latest_incident_after(incidents, handled_after, "unknown_read"):
        reasons.append("unknown-system-error-11")
    if latest_incident_after(incidents, handled_after, "abnormal_close"):
        reasons.append("web-abnormal-closure")
    if latest_incident_after(incidents, handled_after, "fetch_failed"):
        reasons.append("gateway-fetch-failed")
    if latest_incident_after(incidents, handled_after, "max_attempts"):
        reasons.append("whatsapp-max-retry")
    if incident_count_after(incidents, handled_after, "stale_socket") >= 3 and latest_incident_after(incidents, handled_after, "stale_socket"):
        reasons.append("whatsapp-stale-socket-loop")
    if not bool(main_session_health.get("healthy", True)):
        reasons.append("main-webchat-session-corrupt")
    if incident_count_after(incidents, handled_after, "dns_lookup") >= CHANNEL_DNS_LOOP_THRESHOLD and latest_incident_after(incidents, handled_after, "dns_lookup"):
        reasons.append("channel-dns-loop")
    if incident_count_after(incidents, handled_after, "transport_timeout") >= CHANNEL_TIMEOUT_LOOP_THRESHOLD and latest_incident_after(incidents, handled_after, "transport_timeout"):
        reasons.append("channel-timeout-loop")

    payload = {
        "listener_up": is_listener_up(),
        "launchagent_node22": is_launchagent_node22(),
        "whatsapp_linked": whatsapp_linked(status_output),
        "reasons": reasons,
        "incident_counts": incidents.counts,
        "main_webchat_session": main_session_health,
        "model": model_payload,
    }
    if verbose:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if model_handled:
        save_guardian_state(state)
        return model_code

    if not reasons:
        log_line("guardian check: healthy")
        save_guardian_state(state)
        return 0

    last_restart_at = parse_iso(state.get("last_restart_at"))
    if (
        "main-webchat-session-corrupt" not in reasons
        and not force_restart
        and last_restart_at is not None
        and (now - last_restart_at).total_seconds() < RESTART_COOLDOWN_SECONDS
    ):
        log_line(f"guardian check: cooldown active, skipping restart for {', '.join(reasons)}", also_stdout=verbose)
        return 0

    if len(recent_restarts) >= MAX_RESTARTS_PER_HOUR:
        log_line("guardian check: restart ceiling reached, skipping", also_stdout=verbose)
        return 1

    if dry_run:
        log_line(f"guardian check: would restart for {', '.join(reasons)}", also_stdout=verbose)
        save_guardian_state(state)
        return 0

    if "main-webchat-session-corrupt" in reasons:
        repair_result = repair_main_webchat_session(dry_run=False)
        payload["main_webchat_repair"] = repair_result
        log_line(
            f"guardian action: repaired main webchat session ({repair_result['health'].get('reason', 'unknown')})",
            also_stdout=verbose,
        )

    if not stable_restart(verbose=verbose):
        record_restart_state(state, now=now, reasons=reasons)
        save_guardian_state(state)
        return 1

    handled_mark = now_utc()
    record_restart_state(state, now=now, reasons=reasons, handled_mark=handled_mark)
    save_guardian_state(state)
    log_line(f"guardian check: recovered for {', '.join(reasons)}", also_stdout=verbose)
    return 0


def self_test() -> int:
    recent_base = now_utc() - timedelta(minutes=5)
    sample_web = """const MESSAGE_TIMEOUT_MS = tuning.messageTimeoutMs ?? 1800 * 1e3;
...minutesSinceLastMessage !== null && minutesSinceLastMessage > 30 ? { minutesSinceLastMessage } : {}
if (minutesSinceLastMessage && minutesSinceLastMessage > 30) heartbeatLogger.warn(logData, "⚠️ web gateway heartbeat - no messages in 30+ minutes");
await processForRoute(msg, route, groupHistoryKey);
"""
    patched, _ = patch_text(DIST_DIR / "channel-web-sl83aqDv.js", sample_web)
    assert f"tuning.messageTimeoutMs ?? 24 * 60 * 60 * 1e3" in patched
    assert "minutesSinceLastMessage > 24 * 60" in patched
    assert "no messages in 24h+ standby" in patched
    assert "transient inbound read failure; retrying once" in patched

    sample_channels = {
        "channels": {
            "whatsapp": {"groupPolicy": "allowlist"},
            "telegram": {"groupPolicy": "allowlist", "allowFrom": ["123456"]},
        }
    }
    changed_channels = normalize_group_policy(sample_channels)
    assert changed_channels == ["whatsapp"]
    assert sample_channels["channels"]["whatsapp"]["groupPolicy"] == "open"

    sample_plugins = {
        "channels": {
            "wecom": {"enabled": True}
        },
        "plugins": {
            "allow": ["telegram", "wecom", "whatsapp"],
            "entries": {"wecom": {"enabled": True}},
            "installs": {"wecom": {"version": "1.0.11", "resolvedName": "@wecom/wecom-openclaw-plugin"}}
        }
    }
    normalize_wecom_plugin_config(sample_plugins)
    assert sample_plugins["plugins"]["allow"] == ["telegram", "wecom-openclaw-plugin", "whatsapp"]
    assert "wecom" not in sample_plugins["plugins"]["entries"]
    assert "wecom-openclaw-plugin" in sample_plugins["plugins"]["entries"]
    assert "wecom" not in sample_plugins["plugins"]["installs"]
    assert "wecom-openclaw-plugin" in sample_plugins["plugins"]["installs"]
    sample_invalid_plugins = {
        "plugins": {
            "allow": ["telegram", "whatsapp", "wecom-openclaw-plugin"],
            "deny": ["whatsapp"],
            "entries": {
                "whatsapp": {"enabled": True},
                "copilot-proxy": {"enabled": True},
            },
            "installs": {
                "whatsapp": {"version": "2026.3.22"},
                "wecom-openclaw-plugin": {"version": "1.0.11"},
            },
            "slots": {"memory": "whatsapp"},
        }
    }
    original_invalid_resolver = globals()["resolve_invalid_plugin_ids_via_runtime"]
    try:
        globals()["resolve_invalid_plugin_ids_via_runtime"] = lambda payload: {"whatsapp"}
        changes = prune_invalid_plugin_references(sample_invalid_plugins)
        assert sample_invalid_plugins["plugins"]["allow"] == ["telegram", "wecom-openclaw-plugin"]
        assert sample_invalid_plugins["plugins"]["deny"] == []
        assert "whatsapp" not in sample_invalid_plugins["plugins"]["entries"]
        assert "copilot-proxy" in sample_invalid_plugins["plugins"]["entries"]
        assert "whatsapp" not in sample_invalid_plugins["plugins"]["installs"]
        assert "memory" not in sample_invalid_plugins["plugins"]["slots"]
        assert set(changes) == {
            "plugins.allow",
            "plugins.deny",
            "plugins.entries",
            "plugins.installs",
            "plugins.slots.memory",
        }
    finally:
        globals()["resolve_invalid_plugin_ids_via_runtime"] = original_invalid_resolver

    config = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_config = Path(tmp) / "openclaw.json"
        save_json(tmp_config, config)
    summary = collect_recent_incidents([], lookback_minutes=5)
    assert summary.counts["unknown_read"] == 0
    assert summary.counts["dns_lookup"] == 0
    assert normalize_fallback_chain("primary", ["", "primary", "backup", "backup", "secondary"]) == ["backup", "secondary"]
    assert model_identity_matches("api123/claude-sonnet-4-6", "claude-sonnet-4-6")
    assert not model_identity_matches("api123/claude-sonnet-4-6", "openai/gpt-5")
    assert normalize_model_keys("claude-sonnet-4-6", "api123") == {"claude-sonnet-4-6", "api123/claude-sonnet-4-6"}
    assert normalize_model_keys("api123/claude-sonnet-4-6") == {"api123/claude-sonnet-4-6", "claude-sonnet-4-6"}
    with tempfile.TemporaryDirectory() as tmp:
        incident_log = Path(tmp) / "incidents.log"
        incident_log.write_text(
            '\n'.join(
                [
                    f'[{(recent_base + timedelta(seconds=1)).isoformat()}] [whatsapp] channel exited {{"statusCode":408,"message":"Request Time-out"}}',
                    f'[{(recent_base + timedelta(seconds=2)).isoformat()}] [wecom] WebSocket error: getaddrinfo ENOTFOUND openws.work.weixin.qq.com',
                    f'[{(recent_base + timedelta(seconds=3)).isoformat()}] [telegram] fetch fallback: enabling sticky IPv4-only dispatcher (codes=UND_ERR_CONNECT_TIMEOUT)',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        incident_summary = collect_recent_incidents([incident_log], lookback_minutes=10_000)
        assert incident_summary.counts["dns_lookup"] == 1
        assert incident_summary.counts["transport_timeout"] == 2
    with tempfile.TemporaryDirectory() as tmp:
        cli_log = Path(tmp) / "cli.log"
        cli_log.write_text(
            '\n'.join(
                [
                    f'{{"0":"TypeError: fetch failed","_meta":{{"name":"openclaw"}},"time":"{(recent_base + timedelta(seconds=4)).isoformat()}"}}',
                    f'{{"0":"Gateway not reachable: Error: gateway closed (1006 abnormal closure (no close frame)): no close reason","_meta":{{"name":"openclaw"}},"time":"{(recent_base + timedelta(seconds=5)).isoformat()}"}}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        cli_summary = collect_recent_incidents([cli_log], lookback_minutes=10_000)
        assert cli_summary.counts["fetch_failed"] == 0
        assert cli_summary.counts["abnormal_close"] == 0
    with tempfile.TemporaryDirectory() as tmp:
        sessions_dir = Path(tmp) / "agents" / "main" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        broken_session = sessions_dir / "broken.jsonl"
        broken_session.write_text('{"type":"message","id":"oops"}\n', encoding="utf-8")
        broken_store = sessions_dir / "sessions.json"
        save_json(
            broken_store,
            {
                MAIN_WEBCHAT_SESSION_KEY: {
                    "sessionId": "broken",
                    "sessionFile": str(broken_session),
                }
            },
        )
        original_home = globals()["OPENCLAW_HOME"]
        try:
            globals()["OPENCLAW_HOME"] = Path(tmp)
            session_health = inspect_main_webchat_session()
            assert session_health["healthy"] is False
            assert session_health["reason"] == "invalid-session-header-record"
        finally:
            globals()["OPENCLAW_HOME"] = original_home
    with tempfile.TemporaryDirectory() as tmp:
        fake_openclaw_root = Path(tmp) / "openclaw"
        fake_openclaw_root.mkdir(parents=True, exist_ok=True)
        (fake_openclaw_root / "package.json").write_text('{"name":"openclaw"}\n', encoding="utf-8")
        original_home = globals()["OPENCLAW_HOME"]
        original_pkg_root = globals()["OPENCLAW_PACKAGE_ROOT"]
        original_link = globals()["HOST_OPENCLAW_LINK"]
        try:
            globals()["OPENCLAW_HOME"] = Path(tmp) / ".openclaw"
            globals()["OPENCLAW_PACKAGE_ROOT"] = fake_openclaw_root
            globals()["HOST_OPENCLAW_LINK"] = globals()["OPENCLAW_HOME"] / "extensions" / "node_modules" / "openclaw"
            created = ensure_shared_openclaw_package_link()
            assert created is True
            assert globals()["HOST_OPENCLAW_LINK"].is_symlink()
            assert globals()["HOST_OPENCLAW_LINK"].resolve() == fake_openclaw_root.resolve()
            assert ensure_shared_openclaw_package_link() is False
        finally:
            globals()["OPENCLAW_HOME"] = original_home
            globals()["OPENCLAW_PACKAGE_ROOT"] = original_pkg_root
            globals()["HOST_OPENCLAW_LINK"] = original_link
    with tempfile.TemporaryDirectory() as tmp:
        original_pkg_root = globals()["OPENCLAW_PACKAGE_ROOT"]
        original_sdk_index = globals()["HOST_PLUGIN_SDK_INDEX"]
        original_weixin_dir = globals()["WEIXIN_PLUGIN_DIR"]
        original_wecom_dir = globals()["WECOM_PLUGIN_DIR"]
        try:
            fake_openclaw_root = Path(tmp) / "openclaw-host"
            fake_sdk_dir = fake_openclaw_root / "dist" / "plugin-sdk"
            fake_sdk_dir.mkdir(parents=True, exist_ok=True)
            (fake_sdk_dir / "index.js").write_text(
                "export { buildFalImageGenerationProvider, buildGoogleImageGenerationProvider, "
                "buildOpenAIImageGenerationProvider, delegateCompactionToRuntime, "
                "emptyPluginConfigSchema, onDiagnosticEvent, registerContextEngine };",
                encoding="utf-8",
            )

            fake_weixin_dir = Path(tmp) / "openclaw-weixin"
            fake_weixin_src = fake_weixin_dir / "src"
            (fake_weixin_src / "auth").mkdir(parents=True, exist_ok=True)
            (fake_weixin_src / "messaging").mkdir(parents=True, exist_ok=True)
            (fake_weixin_src / "util").mkdir(parents=True, exist_ok=True)
            (fake_weixin_dir / "index.ts").write_text(
                'import type { OpenClawPluginApi } from "openclaw/plugin-sdk";\n'
                'import { buildChannelConfigSchema } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )
            (fake_weixin_src / "channel.ts").write_text(
                'import type { ChannelPlugin, OpenClawConfig } from "openclaw/plugin-sdk";\n'
                'import { normalizeAccountId, resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )
            (fake_weixin_src / "log-upload.ts").write_text(
                'import type { OpenClawConfig } from "openclaw/plugin-sdk";\n'
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )
            (fake_weixin_src / "util" / "logger.ts").write_text(
                'import { resolvePreferredOpenClawTmpDir } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )
            (fake_weixin_src / "auth" / "accounts.ts").write_text(
                'import { normalizeAccountId } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )
            (fake_weixin_src / "auth" / "pairing.ts").write_text(
                'import { withFileLock } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )
            (fake_weixin_src / "messaging" / "send.ts").write_text(
                'import { stripMarkdown } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )
            (fake_weixin_src / "messaging" / "process-message.ts").write_text(
                'import {\n'
                '  createTypingCallbacks,\n'
                '  resolveSenderCommandAuthorizationWithRuntime,\n'
                '  resolveDirectDmAuthorizationOutcome,\n'
                '  resolvePreferredOpenClawTmpDir,\n'
                '} from "openclaw/plugin-sdk";\n'
                'import type { PluginRuntime } from "openclaw/plugin-sdk";\n',
                encoding="utf-8",
            )

            fake_wecom_dir = Path(tmp) / "wecom" / "dist"
            fake_wecom_dir.mkdir(parents=True, exist_ok=True)
            (fake_wecom_dir / "index.esm.js").write_text(
                "import { readJsonFileWithFallback, withFileLock, writeJsonFileAtomically, DEFAULT_ACCOUNT_ID, addWildcardAllowFrom, formatPairingApproveHint, emptyPluginConfigSchema } from 'openclaw/plugin-sdk';\n",
                encoding="utf-8",
            )
            (fake_wecom_dir / "index.cjs.js").write_text(
                "var pluginSdk = require('openclaw/plugin-sdk');\n",
                encoding="utf-8",
            )

            globals()["OPENCLAW_PACKAGE_ROOT"] = fake_openclaw_root
            globals()["HOST_PLUGIN_SDK_INDEX"] = fake_sdk_dir / "index.js"
            globals()["WEIXIN_PLUGIN_DIR"] = fake_weixin_dir
            globals()["WECOM_PLUGIN_DIR"] = Path(tmp) / "wecom"
            patched_paths = ensure_plugin_sdk_compatibility_patches()
            assert len(patched_paths) == 11
            assert "guardian legacy plugin-sdk compatibility exports" in (fake_sdk_dir / "index.js").read_text(encoding="utf-8")
            assert "writeJsonFileAtomically" in (fake_sdk_dir / "index.js").read_text(encoding="utf-8")
            assert "channel-config-schema" in (fake_weixin_dir / "index.ts").read_text(encoding="utf-8")
            assert "plugin-sdk/diffs" in (fake_weixin_src / "channel.ts").read_text(encoding="utf-8")
            assert "plugin-sdk/command-auth" in (fake_weixin_src / "messaging" / "process-message.ts").read_text(encoding="utf-8")
            assert "plugin-sdk/json-store" in (fake_wecom_dir / "index.esm.js").read_text(encoding="utf-8")
            assert "writeJsonAtomic" in (fake_wecom_dir / "index.cjs.js").read_text(encoding="utf-8")
            assert ensure_plugin_sdk_compatibility_patches() == []
        finally:
            globals()["OPENCLAW_PACKAGE_ROOT"] = original_pkg_root
            globals()["HOST_PLUGIN_SDK_INDEX"] = original_sdk_index
            globals()["WEIXIN_PLUGIN_DIR"] = original_weixin_dir
            globals()["WECOM_PLUGIN_DIR"] = original_wecom_dir
    reset_sample = {
        "model_failover": {
            "active": True,
            "baseline_primary": "api123/claude-sonnet-4-6",
            "promoted_primary": "openai-codex/gpt-5.4",
        }
    }
    reset_payload = reset_model_failover_state(reset_sample, handled_at="2026-03-15T00:00:00+00:00", reason="manual-reset")
    assert reset_payload["active"] is False
    assert reset_payload["previous_baseline_primary"] == "api123/claude-sonnet-4-6"
    assert reset_payload["previous_promoted_primary"] == "openai-codex/gpt-5.4"
    assert compute_promoted_routing(
        "api123/claude-sonnet-4-6",
        ["openai-codex/gpt-5.4", "openai-codex/gpt-5.3-codex"],
    ) == (
        "openai-codex/gpt-5.4",
        ["api123/claude-sonnet-4-6", "openai-codex/gpt-5.3-codex"],
    )
    with tempfile.TemporaryDirectory() as tmp:
        model_log = Path(tmp) / "model.log"
        model_log.write_text(
            '\n'.join(
                [
                    f'{{"1":"overload backoff before failover for api123/claude-sonnet-4-6: attempt=1 delayMs=263","time":"{(recent_base + timedelta(seconds=6)).isoformat()}"}}',
                    f'{{"1":"lane task error: lane=main durationMs=24167 error=\\\"FailoverError: The AI service is temporarily unavailable (HTTP 504). Please try again in a moment.\\\"","time":"{(recent_base + timedelta(seconds=7)).isoformat()}"}}',
                    f'{{"1":"embedded run agent end: runId=abc isError=true error=400 Improperly formed request. (request id: foo)","time":"{(recent_base + timedelta(seconds=8)).isoformat()}"}}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        model_summary = collect_recent_model_failures([model_log], lookback_minutes=10_000)
        assert model_summary.counts["backoff"] == 1
        assert model_summary.counts["http_504"] == 1
        assert model_summary.counts["improper_400"] == 1
        assert model_summary.latest is not None
    print("guardian self-test: ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenClaw guardian")
    subparsers = parser.add_subparsers(dest="command", required=True)

    patch_cmd = subparsers.add_parser("patch-runtime", help="Patch installed OpenClaw dist")
    patch_cmd.add_argument("--dry-run", action="store_true")

    config_cmd = subparsers.add_parser("configure", help="Apply standby-safe config")
    config_cmd.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("render-plist", help="Print launchd plist")
    subparsers.add_parser("status", help="Print guardian status JSON")
    subparsers.add_parser("self-test", help="Run local self-test")
    reset_failover_cmd = subparsers.add_parser("reset-model-failover", help="Clear persisted model failover state")
    reset_failover_cmd.add_argument("--reason", default="manual-reset")
    prune_sessions_cmd = subparsers.add_parser("prune-model-sessions", help="Remove stale session-store entries for retired models")
    prune_sessions_cmd.add_argument("--agent", default="main")
    prune_sessions_cmd.add_argument("--model", action="append", required=True)
    prune_sessions_cmd.add_argument("--older-than-hours", type=int, default=24)
    prune_sessions_cmd.add_argument("--dry-run", action="store_true")

    check_cmd = subparsers.add_parser("check-once", help="Run one self-heal check")
    check_cmd.add_argument("--dry-run", action="store_true")
    check_cmd.add_argument("--force-restart", action="store_true")
    check_cmd.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    if args.command == "patch-runtime":
        result = patch_runtime(dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "configure":
        payload = configure_openclaw(dry_run=args.dry_run)
        print(json.dumps({
            "heartbeat_every": payload.get("agents", {}).get("defaults", {}).get("heartbeat", {}).get("every"),
            "web": payload.get("web", {}),
            "channel_health": payload.get("gateway", {}).get("channelHealth", {}),
            "group_policy": {
                channel: payload.get("channels", {}).get(channel, {}).get("groupPolicy")
                for channel in GROUP_POLICY_CHANNELS
            },
            "group_allowlist_sizes": {
                channel: {
                    "allowFrom": len(payload.get("channels", {}).get(channel, {}).get("allowFrom", []) or []),
                    "groupAllowFrom": len(payload.get("channels", {}).get(channel, {}).get("groupAllowFrom", []) or []),
                }
                for channel in GROUP_POLICY_CHANNELS
            },
        }, ensure_ascii=False, indent=2))
        return 0

    if args.command == "render-plist":
        sys.stdout.write(render_launch_agent_plist())
        return 0

    if args.command == "status":
        print(json.dumps(guardian_status_payload(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "self-test":
        return self_test()

    if args.command == "reset-model-failover":
        state = load_guardian_state()
        payload = reset_model_failover_state(
            state,
            handled_at=iso_now(),
            reason=str(args.reason or "manual-reset"),
        )
        save_guardian_state(state)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "prune-model-sessions":
        payload = prune_model_sessions(
            agent_id=str(args.agent or "main"),
            model_ids=args.model,
            older_than_hours=int(args.older_than_hours or 24),
            dry_run=bool(args.dry_run),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "check-once":
        return check_once(
            dry_run=args.dry_run,
            force_restart=args.force_restart,
            verbose=args.verbose,
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
