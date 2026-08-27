#!/usr/bin/env python3
"""Install or inspect the local JaggedThoughts workbench launch agent."""
from __future__ import annotations

import argparse
import os
import plistlib
import re
import shutil
import subprocess
from pathlib import Path


LABEL = "com.jaggedthoughts.capital-workbench"
REPO = Path(__file__).resolve().parents[3]
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library" / "Logs" / "JaggedThoughtsCapital"
DOMAIN = f"gui/{os.getuid()}"


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def _definition() -> dict[str, object]:
    python = REPO / "venv" / "bin" / "python"
    if not python.exists():
        raise SystemExit(f"workspace Python is missing: {python}")
    codex = shutil.which("codex")
    if not codex:
        raise SystemExit("Codex subscription executable is not on PATH")
    path_parts = [
        str(python.parent), str(Path(codex).parent), "/opt/homebrew/bin",
        "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin",
    ]
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(python),
            str(REPO / "scripts/public/control/forensic_workbench_server.py"),
            "--host", "127.0.0.1", "--port", "8080",
        ],
        "WorkingDirectory": str(REPO),
        "EnvironmentVariables": {
            "PATH": ":".join(dict.fromkeys(path_parts)),
            "PYTHONPATH": str(REPO / "src"),
            "OPENAI_API_KEY": "",
            "ZTARE_INVESTMENT_WORKSPACE": str(
                REPO / "projects/jaggedthoughts_capital/workspace/investment"
            ),
        },
        "RunAtLoad": True,
        "KeepAlive": True,
        "ProcessType": "Background",
        "ThrottleInterval": 10,
        "StandardOutPath": str(LOG_DIR / "workbench.out.log"),
        "StandardErrorPath": str(LOG_DIR / "workbench.err.log"),
    }


def install() -> None:
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = PLIST.with_suffix(".plist.tmp")
    with temporary.open("wb") as handle:
        plistlib.dump(_definition(), handle, sort_keys=False)
    temporary.replace(PLIST)
    _run("launchctl", "bootout", DOMAIN, str(PLIST), check=False)
    result = _run("launchctl", "bootstrap", DOMAIN, str(PLIST), check=False)
    if result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip())
    _run("launchctl", "kickstart", "-k", f"{DOMAIN}/{LABEL}")
    print(f"installed {DOMAIN}/{LABEL}")
    print("http://127.0.0.1:8080/?workspace=investment")


def status() -> None:
    result = _run("launchctl", "print", f"{DOMAIN}/{LABEL}", check=False)
    if result.returncode:
        raise SystemExit(f"not installed: {DOMAIN}/{LABEL}")
    state = re.search(r"^\s*state = (.+)$", result.stdout, re.MULTILINE)
    pid = re.search(r"^\s*pid = (\d+)$", result.stdout, re.MULTILINE)
    print(f"{LABEL}: {state.group(1) if state else 'unknown'}"
          f"{f' (pid {pid.group(1)})' if pid else ''}")
    print("http://127.0.0.1:8080/?workspace=investment")
    print(f"logs: {LOG_DIR}")


def uninstall() -> None:
    _run("launchctl", "bootout", DOMAIN, str(PLIST), check=False)
    PLIST.unlink(missing_ok=True)
    print(f"removed {DOMAIN}/{LABEL}; logs remain in {LOG_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "status", "uninstall"))
    action = parser.parse_args().action
    {"install": install, "status": status, "uninstall": uninstall}[action]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
