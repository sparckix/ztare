#!/usr/bin/env python3
"""Run the local forensic workbench API and React dev server together."""
from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO = Path(__file__).resolve().parents[3]
DEFAULT_API_URL = "http://127.0.0.1:8765"
DEFAULT_APP_URL = "http://127.0.0.1:5174"


def terminate(proc: subprocess.Popen[object]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def api_ready(api_url: str, *, timeout: float) -> bool:
    request = Request(f"{api_url.rstrip('/')}/api/projects", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local dev server readiness check.
            return 200 <= response.status < 500
    except HTTPError as exc:
        return 200 <= exc.code < 500
    except (OSError, URLError):
        return False


def wait_for_api(api_url: str, proc: subprocess.Popen[object], *, startup_timeout: float, poll_interval: float) -> bool:
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        if api_ready(api_url, timeout=min(0.5, max(0.05, poll_interval))):
            return True
        time.sleep(poll_interval)
    return False


def run_live(args: argparse.Namespace) -> int:
    api_cmd = [
        sys.executable,
        "scripts/public/control/forensic_workbench_server.py",
        "--host",
        args.api_host,
        "--port",
        str(args.api_port),
    ]
    dev_cmd = ["npm", "--prefix", "forensic-workbench", "run", "dev", "--", "--strictPort"]
    if args.host:
        dev_cmd.extend(["--host", args.host])
    if args.port:
        dev_cmd.extend(["--port", str(args.port)])

    print("forensic workbench live mode", flush=True)
    print(f"  API: {args.api_url}", flush=True)
    print(f"  App: {args.app_url}", flush=True)
    print("  Stop with Ctrl-C.", flush=True)

    api_proc = subprocess.Popen(api_cmd, cwd=REPO)
    try:
        if not wait_for_api(
            args.api_url,
            api_proc,
            startup_timeout=args.api_startup_timeout,
            poll_interval=args.api_poll_interval,
        ):
            if api_proc.poll() is not None:
                return api_proc.returncode or 1
            print(f"API did not become ready within {args.api_startup_timeout:.1f}s: {args.api_url}", file=sys.stderr, flush=True)
            return api_proc.returncode or 1
        dev_proc = subprocess.Popen(dev_cmd, cwd=REPO)
        try:
            return dev_proc.wait()
        finally:
            terminate(dev_proc)
    except KeyboardInterrupt:
        return 0
    finally:
        terminate(api_proc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8765)
    parser.add_argument("--host", default="", help="Optional Vite host override.")
    parser.add_argument("--port", type=int, default=0, help="Optional Vite port override.")
    parser.add_argument("--api-startup-timeout", type=float, default=8.0)
    parser.add_argument("--api-poll-interval", type=float, default=0.2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.api_url = f"http://{args.api_host}:{args.api_port}"
    app_host = args.host or "127.0.0.1"
    app_port = args.port or 5174
    args.app_url = f"http://{app_host}:{app_port}"
    signal.signal(signal.SIGTERM, lambda _signum, _frame: raise_keyboard_interrupt())
    return run_live(args)


def raise_keyboard_interrupt() -> None:
    raise KeyboardInterrupt


if __name__ == "__main__":
    raise SystemExit(main())
