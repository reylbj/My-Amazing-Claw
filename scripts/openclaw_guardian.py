#!/usr/bin/env python3
"""
OpenClaw guardian: runtime patching, standby tuning, and self-healing checks.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

EXPECTED_NODE_PATH = str(Path.home() / ".npm-global" / "lib" / "node_modules" / "node" / "bin" / "node")
EXPECTED_WEB_HEARTBEAT_SECONDS = 300
EXPECTED_WEB_MESSAGE_TIMEOUT_MS = 6 * 60 * 60 * 1000
EXPECTED_WEB_WATCHDOG_CHECK_MS = 5 * 60 * 1000
EXPECTED_CHANNEL_HEALTH_THRESHOLD_MS = 6 * 60 * 60 * 1000
EXPECTED_CHANNEL_HEALTH_CHECK_MINUTES = 5
EXPECTED_AGENT_HEARTBEAT_EVERY = "0m"
EXPECTED_GROUP_POLICY_FALLBACK = "open"
GROUP_POLICY_CHANNELS = ("whatsapp", "telegram")
RESTART_COOLDOWN_SECONDS = 15 * 60
MAX_RESTARTS_PER_HOUR = 6
INCIDENT_LOOKBACK_MINUTES = 180

PATTERN_UNKNOWN_READ = "Unknown system error -11"
PATTERN_ABNORMAL_CLOSE = "gateway closed (1006 abnormal closure"
PATTERN_FETCH_FAILED = "TypeError: fetch failed"
PATTERN_MAX_ATTEMPTS = "web reconnect: max attempts reached"
PATTERN_STALE_SOCKET = "health-monitor: restarting (reason: stale-socket)"

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
    try:
        return subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=check,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(list(args), 1, "", str(exc))


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


def prune_restart_times(times: Iterable[str], *, now: datetime) -> list[str]:
    kept: list[str] = []
    cutoff = now - timedelta(hours=1)
    for item in times:
        parsed = parse_iso(item)
        if parsed and parsed >= cutoff:
            kept.append(parsed.isoformat())
    return kept


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


def patch_text(path: Path, text: str) -> tuple[str, bool]:
    updated = text
    changed = False

    if path.name.startswith("channel-web-") or path.name.startswith("web-"):
        updated, did_change = replace_when_present(
            updated,
            "const MESSAGE_TIMEOUT_MS = tuning.messageTimeoutMs ?? 1800 * 1e3;",
            "const MESSAGE_TIMEOUT_MS = tuning.messageTimeoutMs ?? cfg.web?.messageTimeoutMs ?? 1800 * 1e3;",
        )
        changed = changed or did_change
        updated, did_change = replace_when_present(
            updated,
            "const WATCHDOG_CHECK_MS = tuning.watchdogCheckMs ?? 60 * 1e3;",
            "const WATCHDOG_CHECK_MS = tuning.watchdogCheckMs ?? cfg.web?.watchdogCheckMs ?? 60 * 1e3;",
        )
        changed = changed or did_change
        updated, did_change = replace_when_present(
            updated,
            "await processForRoute(msg, route, groupHistoryKey);",
            """try {\n\t\t\tawait processForRoute(msg, route, groupHistoryKey);\n\t\t} catch (err) {\n\t\t\tconst errText = String(err);\n\t\t\tconst transientReadFailure = errText.includes("Unknown system error -11") && errText.includes("read");\n\t\t\tif (!transientReadFailure) throw err;\n\t\t\tparams.replyLogger.warn({ error: errText, code: err?.code, errno: err?.errno, syscall: err?.syscall }, "transient inbound read failure; retrying once");\n\t\t\tawait sleepWithAbort(250);\n\t\t\tawait processForRoute(msg, route, groupHistoryKey);\n\t\t}""",
        )
        changed = changed or did_change

    if (
        path.name.startswith("auth-profiles-")
        or path.name.startswith("model-selection-")
        or path.name == "daemon-cli.js"
        or (path.parent.name == "plugin-sdk" and path.name.startswith("config-"))
    ):
        updated, did_change = replace_when_present(
            updated,
            """\tweb: z.object({\n\t\tenabled: z.boolean().optional(),\n\t\theartbeatSeconds: z.number().int().positive().optional(),\n\t\treconnect: z.object({""",
            """\tweb: z.object({\n\t\tenabled: z.boolean().optional(),\n\t\theartbeatSeconds: z.number().int().positive().optional(),\n\t\tmessageTimeoutMs: z.number().int().positive().optional(),\n\t\twatchdogCheckMs: z.number().int().positive().optional(),\n\t\treconnect: z.object({""",
        )
        changed = changed or did_change
        updated, did_change = replace_when_present(
            updated,
            "\t\tchannelHealthCheckMinutes: z.number().int().min(0).optional(),",
            """\t\tchannelHealthCheckMinutes: z.number().int().min(0).optional(),\n\t\tchannelHealth: z.object({\n\t\t\tmonitorStartupGraceMs: z.number().int().positive().optional(),\n\t\t\tchannelConnectGraceMs: z.number().int().positive().optional(),\n\t\t\tstaleEventThresholdMs: z.number().int().positive().optional()\n\t\t}).strict().optional(),""",
        )
        changed = changed or did_change

    if path.name.startswith("gateway-cli-"):
        updated, did_change = replace_when_present(
            updated,
            """\tlet channelHealthMonitor = healthCheckMinutes === 0 ? null : startChannelHealthMonitor({\n\t\tchannelManager,\n\t\tcheckIntervalMs: (healthCheckMinutes ?? 5) * 6e4\n\t});""",
            """\tlet channelHealthMonitor = healthCheckMinutes === 0 ? null : startChannelHealthMonitor({\n\t\tchannelManager,\n\t\tcheckIntervalMs: (healthCheckMinutes ?? 5) * 6e4,\n\t\ttiming: cfgAtStart.gateway?.channelHealth\n\t});""",
        )
        changed = changed or did_change
        updated, did_change = replace_when_present(
            updated,
            """\t\t\tcreateHealthMonitor: (checkIntervalMs) => startChannelHealthMonitor({\n\t\t\t\tchannelManager,\n\t\t\t\tcheckIntervalMs\n\t\t\t})""",
            """\t\t\tcreateHealthMonitor: (checkIntervalMs) => startChannelHealthMonitor({\n\t\t\t\tchannelManager,\n\t\t\t\tcheckIntervalMs,\n\t\t\t\ttiming: loadConfig().gateway?.channelHealth\n\t\t\t})""",
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

    schema_supports_web_ext = False
    schema_supports_channel_health_obj = False
    runtime_supports_web_ext = False
    runtime_supports_channel_health_obj = False
    if DIST_DIR.exists():
        schema_candidates = [DIST_DIR / "daemon-cli.js"]
        schema_candidates.extend(sorted(DIST_DIR.glob("auth-profiles-*.js")))
        schema_candidates.extend(sorted(DIST_DIR.glob("model-selection-*.js")))
        schema_candidates.extend(sorted(DIST_DIR.glob("plugin-sdk/config-*.js")))
        runtime_candidates = sorted(DIST_DIR.glob("channel-web-*.js"))
        runtime_candidates.extend(sorted(DIST_DIR.glob("web-*.js")))
        runtime_candidates.extend(sorted(DIST_DIR.glob("plugin-sdk/channel-web-*.js")))
        gateway_candidates = sorted(DIST_DIR.glob("gateway-cli-*.js"))
        for candidate in schema_candidates:
            if not candidate.exists():
                continue
            text = candidate.read_text(encoding="utf-8", errors="replace")
            if "messageTimeoutMs: z.number().int().positive().optional()" in text and "watchdogCheckMs: z.number().int().positive().optional()" in text:
                schema_supports_web_ext = True
            if "channelHealth: z.object({" in text:
                schema_supports_channel_health_obj = True
        for candidate in runtime_candidates:
            text = candidate.read_text(encoding="utf-8", errors="replace")
            if "cfg.web?.messageTimeoutMs" in text and "cfg.web?.watchdogCheckMs" in text:
                runtime_supports_web_ext = True
                break
        for candidate in gateway_candidates:
            text = candidate.read_text(encoding="utf-8", errors="replace")
            if "timing: cfgAtStart.gateway?.channelHealth" in text and "timing: loadConfig().gateway?.channelHealth" in text:
                runtime_supports_channel_health_obj = True
                break

    deep_set(payload, ["agents", "defaults", "heartbeat", "every"], EXPECTED_AGENT_HEARTBEAT_EVERY)
    deep_set(payload, ["web", "heartbeatSeconds"], EXPECTED_WEB_HEARTBEAT_SECONDS)
    deep_set(payload, ["gateway", "channelHealthCheckMinutes"], EXPECTED_CHANNEL_HEALTH_CHECK_MINUTES)
    normalize_group_policy(payload)

    if schema_supports_web_ext and runtime_supports_web_ext:
        deep_set(payload, ["web", "messageTimeoutMs"], EXPECTED_WEB_MESSAGE_TIMEOUT_MS)
        deep_set(payload, ["web", "watchdogCheckMs"], EXPECTED_WEB_WATCHDOG_CHECK_MS)
    else:
        deep_delete(payload, ["web", "messageTimeoutMs"])
        deep_delete(payload, ["web", "watchdogCheckMs"])

    if schema_supports_channel_health_obj and runtime_supports_channel_health_obj:
        deep_set(payload, ["gateway", "channelHealth", "monitorStartupGraceMs"], 60_000)
        deep_set(payload, ["gateway", "channelHealth", "channelConnectGraceMs"], 120_000)
        deep_set(payload, ["gateway", "channelHealth", "staleEventThresholdMs"], EXPECTED_CHANNEL_HEALTH_THRESHOLD_MS)
    else:
        deep_delete(payload, ["gateway", "channelHealth"])

    if not dry_run:
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


def tail_lines(path: Path, *, max_lines: int = 800) -> list[str]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=max_lines))


def collect_recent_incidents(paths: Iterable[Path], *, lookback_minutes: int) -> IncidentSummary:
    cutoff = now_utc() - timedelta(minutes=lookback_minutes)
    counts = {
        "unknown_read": 0,
        "abnormal_close": 0,
        "fetch_failed": 0,
        "max_attempts": 0,
        "stale_socket": 0,
    }
    latest = {key: None for key in counts}

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
            if PATTERN_ABNORMAL_CLOSE in line:
                counts["abnormal_close"] += 1
                latest["abnormal_close"] = timestamp.isoformat()
            if PATTERN_FETCH_FAILED in line:
                counts["fetch_failed"] += 1
                latest["fetch_failed"] = timestamp.isoformat()
            if PATTERN_MAX_ATTEMPTS in line:
                counts["max_attempts"] += 1
                latest["max_attempts"] = timestamp.isoformat()
            if PATTERN_STALE_SOCKET in line:
                counts["stale_socket"] += 1
                latest["stale_socket"] = timestamp.isoformat()

    return IncidentSummary(counts=counts, latest=latest)


def is_listener_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 18789), timeout=2):
            return True
    except OSError:
        return False


def is_launchagent_node22() -> bool:
    plist = Path.home() / "Library" / "LaunchAgents" / "ai.openclaw.gateway.plist"
    if not plist.exists():
        return False
    content = plist.read_text(encoding="utf-8", errors="replace")
    return EXPECTED_NODE_PATH in content


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
    return {
        "listener_up": is_listener_up(),
        "launchagent_node22": is_launchagent_node22(),
        "whatsapp_linked": whatsapp_linked(status_output),
        "incident_counts": incidents.counts,
        "incident_latest": incidents.latest,
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

    reasons: list[str] = []
    if force_restart:
        reasons.append("forced")
    if not is_listener_up():
        reasons.append("gateway-port-down")
    if not is_launchagent_node22():
        reasons.append("gateway-node-drift")
    if not whatsapp_linked(status_output):
        reasons.append("whatsapp-not-linked")
    if latest_incident_after(incidents, handled_after, "unknown_read"):
        reasons.append("unknown-system-error-11")
    if latest_incident_after(incidents, handled_after, "abnormal_close"):
        reasons.append("web-abnormal-closure")
    if latest_incident_after(incidents, handled_after, "fetch_failed"):
        reasons.append("gateway-fetch-failed")
    if latest_incident_after(incidents, handled_after, "max_attempts"):
        reasons.append("whatsapp-max-retry")
    if incidents.counts["stale_socket"] >= 3 and latest_incident_after(incidents, handled_after, "stale_socket"):
        reasons.append("whatsapp-stale-socket-loop")

    payload = {
        "listener_up": is_listener_up(),
        "launchagent_node22": is_launchagent_node22(),
        "whatsapp_linked": whatsapp_linked(status_output),
        "reasons": reasons,
        "incident_counts": incidents.counts,
    }
    if verbose:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not reasons:
        log_line("guardian check: healthy")
        return 0

    last_restart_at = parse_iso(state.get("last_restart_at"))
    if (
        not force_restart
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
        return 0

    if not stable_restart(verbose=verbose):
        recent_restarts.append(now.isoformat())
        state["restart_times"] = recent_restarts
        state["last_restart_at"] = now.isoformat()
        state["last_reasons"] = reasons
        save_guardian_state(state)
        return 1

    handled_mark = now_utc()
    recent_restarts.append(now.isoformat())
    state["restart_times"] = recent_restarts
    state["last_restart_at"] = now.isoformat()
    state["handled_through_ts"] = handled_mark.isoformat()
    state["last_reasons"] = reasons
    save_guardian_state(state)
    log_line(f"guardian check: recovered for {', '.join(reasons)}", also_stdout=verbose)
    return 0


def self_test() -> int:
    sample_web = """const MESSAGE_TIMEOUT_MS = tuning.messageTimeoutMs ?? 1800 * 1e3;\nconst WATCHDOG_CHECK_MS = tuning.watchdogCheckMs ?? 60 * 1e3;\n"""
    patched, _ = patch_text(DIST_DIR / "channel-web-sl83aqDv.js", sample_web)
    assert "cfg.web?.messageTimeoutMs" in patched
    assert "cfg.web?.watchdogCheckMs" in patched

    sample_schema = """\tweb: z.object({\n\t\tenabled: z.boolean().optional(),\n\t\theartbeatSeconds: z.number().int().positive().optional(),\n\t\treconnect: z.object({\n\t\tchannelHealthCheckMinutes: z.number().int().min(0).optional(),\n"""
    schema_patched, _ = patch_text(DIST_DIR / "model-selection-CjMYMtR0.js", sample_schema)
    assert "messageTimeoutMs" in schema_patched
    assert "channelHealth" in schema_patched

    sample_channels = {
        "channels": {
            "whatsapp": {"groupPolicy": "allowlist"},
            "telegram": {"groupPolicy": "allowlist", "allowFrom": ["123456"]},
        }
    }
    changed_channels = normalize_group_policy(sample_channels)
    assert changed_channels == ["whatsapp"]
    assert sample_channels["channels"]["whatsapp"]["groupPolicy"] == "open"

    config = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_config = Path(tmp) / "openclaw.json"
        save_json(tmp_config, config)
    summary = collect_recent_incidents([], lookback_minutes=5)
    assert summary.counts["unknown_read"] == 0
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

    if args.command == "check-once":
        return check_once(
            dry_run=args.dry_run,
            force_restart=args.force_restart,
            verbose=args.verbose,
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
