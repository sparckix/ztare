#!/usr/bin/env python3
"""Run the local Project Workbench API and React dev server together."""
from __future__ import annotations

import argparse
import os
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


def checkout_pythonpath(existing: str = "") -> str:
    """Prefer this checkout's source tree when the live server imports ZTARE."""
    parts = [str(REPO / "src"), str(REPO)]
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


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
    request = Request(f"{api_url.rstrip('/')}/api/status", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local dev server readiness check.
            return 200 <= response.status < 500
    except HTTPError as exc:
        return 200 <= exc.code < 500
    except (OSError, URLError):
        return False


def wait_for_api(api_url: str, proc: subprocess.Popen[object], *, startup_timeout: float, poll_interval: float) -> bool:
    deadline = time.monotonic() + startup_timeout
    readiness_timeout = min(3.0, max(1.0, poll_interval * 5))
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        if api_ready(api_url, timeout=readiness_timeout):
            return True
        time.sleep(poll_interval)
    return False


def ensure_web_deps() -> bool:
    """Install the React app's node_modules on first run so `make forensic-workbench-live` just works on a
    fresh clone (no separate install step to remember). No-op once installed."""
    if (REPO / "forensic-workbench" / "node_modules").is_dir():
        return True
    print("  First run: installing web dependencies (npm install)…", flush=True)
    result = subprocess.run(["npm", "--prefix", "forensic-workbench", "install"], cwd=REPO)
    if result.returncode != 0:
        print("  npm install failed — run `make forensic-workbench-install` and retry.", file=sys.stderr, flush=True)
        return False
    return True


def run_live(args: argparse.Namespace) -> int:
    if not ensure_web_deps():
        return 1
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

    print("Project Workbench live mode", flush=True)
    print(f"  API: {args.api_url}", flush=True)
    print(f"  App: {args.app_url}", flush=True)
    print("  Stop with Ctrl-C.", flush=True)

    api_proc: subprocess.Popen[object] | None = None
    try:
        if api_ready(args.api_url, timeout=min(3.0, max(0.5, args.api_startup_timeout / 3))):
            print("  Reusing already-running API.", flush=True)
        else:
            api_env = os.environ.copy()
            api_env["PYTHONPATH"] = checkout_pythonpath(api_env.get("PYTHONPATH", ""))
            api_proc = subprocess.Popen(api_cmd, cwd=REPO, env=api_env)
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
        dev_env = os.environ.copy()
        dev_env["ZTARE_WORKBENCH_API_TARGET"] = args.api_url
        dev_proc = subprocess.Popen(dev_cmd, cwd=REPO, env=dev_env)
        try:
            return dev_proc.wait()
        finally:
            terminate(dev_proc)
    except KeyboardInterrupt:
        return 0
    finally:
        if api_proc is not None:
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
