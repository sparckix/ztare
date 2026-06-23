#!/usr/bin/env python3
"""Run the local forensic workbench API and React dev server together."""
from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


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


def run_live(args: argparse.Namespace) -> int:
    api_cmd = [
        sys.executable,
        "scripts/public/control/forensic_workbench_server.py",
        "--host",
        args.api_host,
        "--port",
        str(args.api_port),
    ]
    dev_cmd = ["npm", "--prefix", "forensic-workbench", "run", "dev"]
    if args.host:
        dev_cmd.extend(["--", "--host", args.host])
    if args.port:
        separator = "--" if "--" not in dev_cmd else None
        if separator:
            dev_cmd.append(separator)
        dev_cmd.extend(["--port", str(args.port)])

    print("forensic workbench live mode", flush=True)
    print(f"  API: {args.api_url}", flush=True)
    print(f"  App: {args.app_url}", flush=True)
    print("  Stop with Ctrl-C.", flush=True)

    api_proc = subprocess.Popen(api_cmd, cwd=REPO)
    try:
        time.sleep(args.api_startup_delay)
        if api_proc.poll() is not None:
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
    parser.add_argument("--api-startup-delay", type=float, default=0.6)
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
