#!/usr/bin/env python3
"""First-run setup check for the ZTARE org runtime.

This is the low-friction first-run entry point: verify the local
research-company runtime without executing work. It composes the narrower
preflight/smoke tools and emits one JSON report that a human or CI job can
read.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _json_run(cmd: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    result = _run(cmd, env=env)
    if result["stdout"]:
        try:
            result["json"] = json.loads(result["stdout"])
        except json.JSONDecodeError as exc:
            result["ok"] = False
            result["json_error"] = str(exc)
    return result


def _path_exists(rel: str) -> dict[str, Any]:
    path = REPO_ROOT / rel
    return {"path": rel, "ok": path.exists()}


def _init_private_file(template_rel: str, target_rel: str) -> dict[str, Any]:
    template = REPO_ROOT / template_rel
    target = REPO_ROOT / target_rel
    result: dict[str, Any] = {
        "template": template_rel,
        "target": target_rel,
        "ok": False,
        "created": False,
        "skipped": False,
    }
    if target.exists():
        result["ok"] = True
        result["skipped"] = True
        result["reason"] = "target_exists"
        return result
    if target.is_symlink():
        target.unlink()
    if not template.exists():
        result["reason"] = "missing_template"
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, target)
    result["ok"] = True
    result["created"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the local ZTARE research-company boot path without executing work."
    )
    parser.add_argument("--member-id", default=os.environ.get("ZTARE_MEMBER_ID", "codex"))
    parser.add_argument("--agent-cli", default=os.environ.get("ZTARE_AGENT_CLI", "codex"))
    parser.add_argument(
        "--agent-adapter",
        default=os.environ.get("ZTARE_AGENT_ADAPTER", "auto"),
        choices=["auto", "claude_print", "codex_exec"],
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip daemon dry-run smoke checks; still validates files and inboxes.",
    )
    parser.add_argument(
        "--init-private",
        action="store_true",
        help="Create missing local private mandates/preferences from public templates before checking.",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env["ZTARE_MEMBER_ID"] = args.member_id
    env["ZTARE_AGENT_CLI"] = args.agent_cli
    env["ZTARE_AGENT_ADAPTER"] = args.agent_adapter

    report: dict[str, Any] = {
        "schema_version": 1,
        "ok": False,
        "member_id": args.member_id,
        "agent_cli": args.agent_cli,
        "agent_adapter": args.agent_adapter,
        "checks": {},
        "advice": [],
    }

    if args.init_private:
        report["checks"]["init_private"] = [
            _init_private_file(
                "org/mandates/templates/manager_mandate.md",
                "org/mandates/manager_mandate.md",
            ),
            _init_private_file(
                "org/mandates/templates/research_director_mandate.md",
                "org/mandates/research_director_mandate.md",
            ),
            _init_private_file(
                "org/mandates/templates/forecasting_agent_mandate.md",
                "org/mandates/forecasting_agent_mandate.md",
            ),
            _init_private_file(
                "org/mandates/templates/debate_runner_mandate.md",
                "org/mandates/debate_runner_mandate.md",
            ),
            _init_private_file(
                "org/preferences/templates/principal.yaml",
                "org/preferences/principal.yaml",
            ),
            _init_private_file(
                "org/roles/templates/research_director.yaml",
                "org/roles/research_director.yaml",
            ),
            _init_private_file(
                "org/roles/templates/product_manager.yaml",
                "org/roles/product_manager.yaml",
            ),
            _init_private_file(
                "org/roles/templates/debate_runner.yaml",
                "org/roles/debate_runner.yaml",
            ),
        ]

    report["checks"]["filesystem_contract"] = [
        _path_exists("AGENTS.md"),
        _path_exists("org/roles/research_director.yaml"),
        _path_exists("org/mandates/research_director_mandate.md"),
        _path_exists("org/preferences/principal.yaml"),
        _path_exists("docs/guides/org_runtime_quickstart.md"),
        _path_exists("docker-compose.yml"),
    ]

    report["checks"]["agent_runtime_available"] = {
        "cli": args.agent_cli,
        "ok": shutil.which(args.agent_cli) is not None,
        "path": shutil.which(args.agent_cli),
    }
    if not report["checks"]["agent_runtime_available"]["ok"]:
        report["advice"].append(
            f"Agent CLI '{args.agent_cli}' is not on PATH. Preflight can pass, but live execution needs this runtime installed/authenticated."
        )
    missing_private = [
        item["path"]
        for item in report["checks"]["filesystem_contract"]
        if not item["ok"]
        and item["path"] in {
            "org/mandates/research_director_mandate.md",
            "org/preferences/principal.yaml",
        }
    ]
    if missing_private and not args.init_private:
        report["advice"].append(
            "Missing local private bootstrap files. Run: "
            "python scripts/public/control/org_first_run_setup.py --init-private --skip-smoke"
        )

    report["checks"]["docker_available"] = {
        "ok": shutil.which("docker") is not None,
        "path": shutil.which("docker"),
    }
    if not report["checks"]["docker_available"]["ok"]:
        report["advice"].append("Docker is not on PATH. Install Docker Desktop if you want containerized daemons.")

    report["checks"]["research_director_preflight"] = _json_run(
        [
            sys.executable,
            "scripts/public/control/org_role_preflight.py",
            "--role",
            "research_director",
            "--agent-cli",
            args.agent_cli,
            "--json",
        ],
        env=env,
    )
    report["checks"]["manager_preflight"] = _json_run(
        [
            sys.executable,
            "scripts/public/control/org_role_preflight.py",
            "--role",
            "manager",
            "--agent-cli",
            args.agent_cli,
            "--json",
        ],
        env=env,
    )
    report["checks"]["a2a_agent_cards"] = _json_run(
        [sys.executable, "scripts/public/control/export_a2a_agent_cards.py"],
        env=env,
    )
    report["checks"]["inbox_status"] = _json_run(
        [sys.executable, "scripts/public/control/org_inbox_status.py"],
        env=env,
    )

    if not args.skip_smoke:
        report["checks"]["research_director_smoke"] = _run(
            [
                sys.executable,
                "scripts/public/control/org_runtime_smoke.py",
                "--role",
                "research_director",
                "--member-id",
                args.member_id,
                "--agent-cli",
                args.agent_cli,
                "--agent-adapter",
                args.agent_adapter,
            ],
            env=env,
        )

    required_ok = all(
        item["ok"]
        for item in report["checks"]["filesystem_contract"]
    ) and all(
        check.get("ok", False)
        for key, check in report["checks"].items()
        if key not in {
            "filesystem_contract",
            "agent_runtime_available",
            "docker_available",
            "init_private",
        }
    )
    if args.init_private:
        required_ok = required_ok and all(item["ok"] for item in report["checks"]["init_private"])
    report["ok"] = bool(required_ok)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
