#!/usr/bin/env python3
"""Generic watchdog for external GPU/API runs.

The monitor is intentionally project-agnostic. It watches a PID file and a
result file, logs progress snapshots, and sends remote-side notifications on
start, completion, and "process stopped without result". It is the reusable
version of the ad hoc Phase 5BP ntfy monitor pattern.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"{utc_now()} {message}\n")


def notify(
    *,
    topic: str | None,
    server: str,
    title: str,
    message: str,
    priority: str,
    tags: str,
    monitor_log: Path,
) -> None:
    append_log(monitor_log, f"{title}: {message}")
    if not topic:
        append_log(monitor_log, "WARN: topic missing; notification not sent")
        return
    req = urllib.request.Request(
        f"{server.rstrip('/')}/{topic}",
        data=message.encode("utf-8", errors="replace"),
        headers={"Title": title, "Priority": priority, "Tags": tags},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=12).read()
    except Exception as exc:  # noqa: BLE001
        append_log(monitor_log, f"WARN: notification failed: {exc}")


def pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text:
        return None
    try:
        return int(text.split()[0])
    except ValueError:
        return None


def summarize_json(path: Path, keys: list[str]) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return f"result={path}; summary_read_error={exc}"
    if not keys:
        keys = ["status", "classification", "returncode", "elapsed_seconds"]
    parts: list[str] = [f"result={path}"]
    for key in keys:
        value: Any = data
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = None
                break
        if value is not None:
            parts.append(f"{key}={value}")
    return " ".join(parts)


def result_is_terminal(path: Path, nonterminal_statuses: set[str]) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return True
    status = str(data.get("status", "")).strip().lower()
    return status not in nonterminal_statuses


def result_status(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "unknown"
    return str(data.get("status", "unknown")).strip().lower() or "unknown"


def tail(path: Path, lines: int) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return f"{path} missing"
    return "\n".join(data[-lines:])


def monitor(args: argparse.Namespace) -> int:
    run_name = args.run_name
    monitor_log = Path(args.monitor_log)
    result_file = Path(args.result_file)
    pid_file = Path(args.pid_file) if args.pid_file else None
    progress_file = Path(args.progress_file) if args.progress_file else None
    raw_log = Path(args.log_file) if args.log_file else None
    started = time.time()

    def send(title: str, message: str, priority: str, tags: str) -> None:
        notify(
            topic=args.topic,
            server=args.server,
            title=title,
            message=message,
            priority=priority,
            tags=tags,
            monitor_log=monitor_log,
        )

    def interrupted(signum: int, _frame: object) -> None:
        elapsed = (time.time() - started) / 60
        send(
            f"{run_name} monitor interrupted",
            f"signal={signum}; elapsed={elapsed:.1f} min; result={result_file}",
            "5",
            "warning",
        )
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, interrupted)

    send(
        f"{run_name} monitor started",
        f"host={os.uname().nodename}; pid_file={pid_file}; result={result_file}",
        "3",
        "hourglass_flowing_sand",
    )

    while True:
        if result_file.exists() and result_is_terminal(result_file, set(args.nonterminal_status)):
            elapsed = (time.time() - started) / 60
            summary = summarize_json(result_file, args.summary_key)
            status = result_status(result_file)
            if status in {"failed", "interrupted", "inadmissible", "error"}:
                send(f"{run_name} failed", f"{summary}; elapsed={elapsed:.1f} min", "5", "warning")
                return 1
            send(f"{run_name} complete", f"{summary}; elapsed={elapsed:.1f} min", "4", "white_check_mark")
            return 0

        pid = read_pid(pid_file) if pid_file else None
        if pid_file and pid is None and args.fail_if_pid_missing:
            send(
                f"{run_name} stopped without result",
                f"pid_file_missing_or_invalid={pid_file}; result_missing={result_file}",
                "5",
                "warning",
            )
            return 1
        if pid is not None and not pid_is_running(pid):
            log_tail = tail(raw_log, args.tail_lines) if raw_log else ""
            send(
                f"{run_name} stopped without result",
                f"pid={pid} not running; result_missing={result_file}; tail={log_tail}",
                "5",
                "warning",
            )
            return 1

        if progress_file and progress_file.exists():
            append_log(monitor_log, f"progress {summarize_json(progress_file, args.progress_key)}")

        if args.once:
            append_log(monitor_log, "once=true; monitor exiting after one healthy poll")
            return 0
        time.sleep(args.poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch an external run and notify on terminal state")
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--result-file", required=True)
    parser.add_argument("--pid-file", default=None)
    parser.add_argument("--progress-file", default=None)
    parser.add_argument("--log-file", default=None)
    parser.add_argument("--monitor-log", required=True)
    parser.add_argument("--topic", default=os.environ.get("ZTARE_NTFY_TOPIC") or os.environ.get("NTFY_TOPIC"))
    parser.add_argument("--server", default=os.environ.get("NTFY_SERVER", "https://ntfy.sh"))
    parser.add_argument("--poll-seconds", type=float, default=300.0)
    parser.add_argument("--tail-lines", type=int, default=20)
    parser.add_argument("--summary-key", action="append", default=[])
    parser.add_argument("--progress-key", action="append", default=[])
    parser.add_argument(
        "--nonterminal-status",
        action="append",
        default=["running"],
        help="JSON result.status values that mean the run is still active.",
    )
    parser.add_argument("--fail-if-pid-missing", action="store_true")
    parser.add_argument("--once", action="store_true")
    return monitor(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
