"""Persist the Workbench receipt for a completed evidence-fetch command."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from ztare.common.paths import REPO_ROOT


SCHEMA = "ztare-forensic-workbench-evidence-fetch-receipt-v1"


def validate_project(project: str) -> str:
    project = str(project or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", project):
        raise ValueError(f"invalid project slug: {project!r}")
    return project


def record_receipt(*, project: str, receipt: dict[str, Any], root: Path = REPO_ROOT) -> dict[str, Any]:
    project = validate_project(project)
    if receipt.get("schema") != SCHEMA:
        raise ValueError(f"receipt schema must be {SCHEMA}")
    if str(receipt.get("project") or "") != project:
        raise ValueError("receipt project does not match --project")
    workspace = root.resolve() / "projects" / project / "workspace"
    ledger = workspace / "forensic_workbench_evidence_fetches.jsonl"
    latest = workspace / "forensic_workbench_latest_evidence_fetch.json"
    workspace.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True) + "\n")
    latest.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "project": project,
        "receipt_path": ledger.relative_to(root.resolve()).as_posix(),
        "latest": latest.relative_to(root.resolve()).as_posix(),
        "receipt": receipt,
        "write_paths": [
            ledger.relative_to(root.resolve()).as_posix(),
            latest.relative_to(root.resolve()).as_posix(),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--from", dest="receipt_path", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        receipt = json.loads(args.receipt_path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be a JSON object")
        result = record_receipt(project=args.project, receipt=receipt, root=args.repo)
    except Exception as exc:  # noqa: BLE001 - concise CLI boundary.
        print(f"ztare forensic-workbench record-evidence-fetch: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else result["latest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
