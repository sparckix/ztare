#!/usr/bin/env python3
"""Register an external GPU/API run in the ZTARE kernel run registry."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ztare.orchestration.external_runs import (  # noqa: E402
    ExternalRunContract,
    ExternalRunState,
    new_run_id,
    register_run,
)


def load_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    candidate = Path(raw)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--run-kind", default="gpu_run")
    parser.add_argument("--host", required=True)
    parser.add_argument("--remote-user", default="ubuntu")
    parser.add_argument("--remote-dir", required=True)
    parser.add_argument("--launch-command", required=True)
    parser.add_argument("--label-prefix", default="external-gpu")
    parser.add_argument("--launcher-pid", type=int)
    parser.add_argument("--result-file", action="append", default=[])
    parser.add_argument("--artifact-file", action="append", default=[])
    parser.add_argument("--progress-hint")
    parser.add_argument("--notification-topic")
    parser.add_argument("--notification-server")
    parser.add_argument("--local-results-root")
    parser.add_argument("--metadata-json")
    parser.add_argument("--status", default="registered")
    args = parser.parse_args()

    run_id = new_run_id(args.project_slug, args.run_kind)
    contract = ExternalRunContract(
        run_id=run_id,
        project_slug=args.project_slug,
        run_kind=args.run_kind,
        host=args.host,
        remote_user=args.remote_user,
        remote_dir=args.remote_dir,
        launcher_pid=args.launcher_pid,
        label_prefix=args.label_prefix,
        launch_command=args.launch_command,
        result_files=args.result_file,
        artifact_files=args.artifact_file,
        progress_hint=args.progress_hint,
        notification_topic=args.notification_topic,
        notification_server=args.notification_server,
        local_results_root=args.local_results_root,
        metadata=load_metadata(args.metadata_json),
    )
    state = ExternalRunState(
        run_id=run_id,
        status=args.status,
        host=args.host,
        project_slug=args.project_slug,
        run_kind=args.run_kind,
        launcher_pid=args.launcher_pid,
        latest_marker=args.progress_hint,
        local_results_dir=args.local_results_root,
    )
    path = register_run(contract, state)
    print(path.relative_to(REPO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
