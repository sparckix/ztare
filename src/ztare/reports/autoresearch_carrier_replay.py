"""Read-only replay audit for autoresearch projection carriers.

The projection carrier is useful only if repeated runs keep the same audit
fields available: latest-eval status, artifact refs, worker provenance,
action-intelligence links, and constraint summaries. This module replays those
carriers across one or more projects and reports carrier integrity gaps without
running the loop or changing project state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from ztare.common.paths import REPO_ROOT
from ztare.validator.hypothesis_projection import build_projection


SCHEMA = "ztare-autoresearch-carrier-replay-v1"
LATEST_ATTENTION_STATUSES = {
    "latest_eval_without_eval_history",
    "latest_eval_not_in_eval_history",
    "unreadable",
}
MISSING_FIELD_VALUES = {"", "none", "null", "unknown", "unrecorded"}


def build_carrier_replay(
    *,
    repo: Path | str | None = None,
    projects: Iterable[str | Path] | None = None,
    max_projects: int | None = 25,
) -> dict[str, Any]:
    """Build a read-only carrier replay report.

    ``projects`` may be project slugs under ``repo/projects`` or explicit paths.
    When omitted, the report discovers projects with eval history, latest eval
    files, or legacy history metadata.
    """

    repo_path = Path(repo or REPO_ROOT).resolve()
    project_dirs = (
        [_resolve_project(repo_path, project) for project in projects]
        if projects
        else _discover_projects(repo_path, max_projects=max_projects)
    )
    rows = [_audit_project(repo_path, project_dir) for project_dir in project_dirs]
    summary = _summarize(rows)
    return {
        "schema": SCHEMA,
        "repo": str(repo_path),
        "summary": summary,
        "projects": rows,
    }


def _resolve_project(repo: Path, project: str | Path) -> Path:
    path = Path(project)
    if path.is_absolute() or path.exists():
        return path.resolve()
    return (repo / "projects" / str(project)).resolve()


def _discover_projects(repo: Path, *, max_projects: int | None) -> list[Path]:
    projects_dir = repo / "projects"
    if not projects_dir.exists():
        return []
    out: list[Path] = []
    for child in sorted(projects_dir.iterdir()):
        if not child.is_dir():
            continue
        if _has_projection_surface(child):
            out.append(child.resolve())
        if max_projects is not None and len(out) >= max(0, max_projects):
            break
    return out


def _has_projection_surface(project_dir: Path) -> bool:
    if (project_dir / "workspace" / "eval_history.jsonl").exists():
        return True
    if (project_dir / "latest_eval_results.json").exists():
        return True
    if (project_dir / "workspace" / "latest_eval_results.json").exists():
        return True
    history = project_dir / "history"
    return history.exists() and any(history.glob("*_meta.json"))


def _audit_project(repo: Path, project_dir: Path) -> dict[str, Any]:
    project = project_dir.name
    base = {
        "project": project,
        "project_path": _rel(repo, project_dir),
    }
    try:
        projection = build_projection(project_dir)
    except Exception as exc:  # pragma: no cover - exact exception is surfaced.
        return {
            **base,
            "status": "error",
            "projection_kind": None,
            "node_count": 0,
            "attention_reasons": [f"projection_error:{type(exc).__name__}"],
            "error": str(exc),
            "next_action": "repair_or_restore_eval_history",
        }

    nodes = projection.nodes
    missing_fields = _missing_carrier_fields(nodes)
    current_carrier = _current_carrier_readiness(nodes)
    latest = dict(projection.latest_eval_overlay)
    latest_status = str(latest.get("status") or "unknown")
    attention_reasons = _attention_reasons(latest_status, missing_fields, len(nodes))
    status = "attention" if attention_reasons else "ok"
    failed_gate_ids = sorted({
        gate_id
        for node in nodes
        for gate_id in node.failed_gate_ids
        if str(gate_id).strip()
    })

    return {
        **base,
        "status": status,
        "projection_kind": projection.projection_kind,
        "node_count": projection.summary.node_count,
        "admitted_count": projection.summary.admitted_count,
        "rejected_count": projection.summary.rejected_count,
        "best_score": projection.summary.best_score,
        "score_gain": projection.summary.score_gain,
        "latest_eval_status": latest_status,
        "latest_eval_warnings": latest.get("warnings") or [],
        "latest_eval_matches_history": latest.get("matches_history"),
        "action_intelligence_link_count": projection.summary.action_intelligence_link_count,
        "negative_constraint_count": projection.summary.negative_constraint_count,
        "open_frontier_constraint_count": projection.summary.open_frontier_constraint_count,
        "held_out_admission_evidence_count": (
            projection.summary.held_out_admission_evidence_count
        ),
        "gate_failure_count_total": sum(node.gate_failure_count for node in nodes),
        "failed_gate_ids": failed_gate_ids,
        "missing_carrier_fields": missing_fields,
        "current_carrier": current_carrier,
        "attention_reasons": attention_reasons,
        "next_action": _next_action(
            attention_reasons,
            current_carrier=current_carrier,
        ),
    }


def _missing_carrier_fields(nodes: Iterable[Any]) -> dict[str, int]:
    counts = {
        "artifact_refs": 0,
        "failure_signature": 0,
        "worker_archetype": 0,
        "worker_capability": 0,
        "worker_state": 0,
        "worker_identity": 0,
        "transport": 0,
    }
    for node in nodes:
        if not getattr(node, "artifact_refs", None):
            counts["artifact_refs"] += 1
        if _missing_value(getattr(node, "failure_signature", "")):
            counts["failure_signature"] += 1
        for field in (
            "worker_archetype",
            "worker_capability",
            "worker_state",
            "worker_identity",
            "transport",
        ):
            if _missing_value(getattr(node, field, "")):
                counts[field] += 1
    return counts


def _missing_value(value: Any) -> bool:
    return str(value or "").strip().lower() in MISSING_FIELD_VALUES


def _current_carrier_readiness(nodes: Iterable[Any]) -> dict[str, Any]:
    node_list = list(nodes)
    if not node_list:
        return {
            "available": False,
            "status": "no_projection_nodes",
            "missing_fields": [],
        }
    node = node_list[-1]
    missing: list[str] = []
    if not getattr(node, "artifact_refs", None):
        missing.append("artifact_refs")
    if _missing_value(getattr(node, "failure_signature", "")):
        missing.append("failure_signature")
    for field in (
        "worker_archetype",
        "worker_capability",
        "worker_state",
        "worker_identity",
        "transport",
    ):
        if _missing_value(getattr(node, field, "")):
            missing.append(field)
    return {
        "available": True,
        "status": "complete" if not missing else "missing_fields",
        "node_id": getattr(node, "node_id", None),
        "iteration": getattr(node, "iteration", None),
        "timestamp": getattr(node, "timestamp", ""),
        "missing_fields": missing,
    }


def _attention_reasons(
    latest_status: str,
    missing_fields: dict[str, int],
    node_count: int,
) -> list[str]:
    reasons: list[str] = []
    if latest_status in LATEST_ATTENTION_STATUSES:
        reasons.append(f"latest_eval_overlay:{latest_status}")
    if node_count > 0 and missing_fields.get("artifact_refs", 0):
        reasons.append(f"missing_artifact_refs:{missing_fields['artifact_refs']}")
    if node_count > 0 and missing_fields.get("failure_signature", 0):
        reasons.append(f"missing_failure_signature:{missing_fields['failure_signature']}")
    worker_missing = sum(
        missing_fields.get(field, 0)
        for field in (
            "worker_archetype",
            "worker_capability",
            "worker_state",
            "worker_identity",
        )
    )
    if node_count > 0 and worker_missing:
        reasons.append(f"unrecorded_worker_context:{worker_missing}")
    if node_count > 0 and missing_fields.get("transport", 0):
        reasons.append(f"unrecorded_transport:{missing_fields['transport']}")
    return reasons


def _next_action(
    attention_reasons: list[str],
    *,
    current_carrier: dict[str, Any] | None = None,
) -> str:
    if not attention_reasons:
        return "none"
    if any(reason.startswith("latest_eval_overlay:unreadable") for reason in attention_reasons):
        return "repair_latest_eval_results_json"
    if any(
        reason.startswith("latest_eval_overlay:latest_eval_without_eval_history")
        for reason in attention_reasons
    ):
        return "append_latest_eval_to_eval_history_or_replay_iteration"
    if any(
        reason.startswith("latest_eval_overlay:latest_eval_not_in_eval_history")
        for reason in attention_reasons
    ):
        return "replay_or_append_latest_eval_before_using_projection"
    if (
        current_carrier
        and current_carrier.get("status") == "complete"
        and _only_legacy_carrier_debt(attention_reasons)
    ):
        return "legacy_carrier_backfill_optional_current_rows_ok"
    if any(reason.startswith("missing_artifact_refs") for reason in attention_reasons):
        return "add_artifact_refs_to_eval_history_rows"
    if any(reason.startswith("unrecorded_transport") for reason in attention_reasons):
        return "record_worker_transport_on_next_loop"
    if any(reason.startswith("unrecorded_worker_context") for reason in attention_reasons):
        return "record_worker_context_on_next_loop"
    if any(reason.startswith("missing_failure_signature") for reason in attention_reasons):
        return "write_weakest_point_or_failure_signature"
    return "inspect_projection_carrier"


def _only_legacy_carrier_debt(attention_reasons: list[str]) -> bool:
    if not attention_reasons:
        return False
    allowed_prefixes = (
        "missing_artifact_refs",
        "missing_failure_signature",
        "unrecorded_worker_context",
        "unrecorded_transport",
    )
    return all(reason.startswith(allowed_prefixes) for reason in attention_reasons)


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "project_count": len(rows),
        "ok_count": sum(1 for row in rows if row.get("status") == "ok"),
        "attention_count": sum(1 for row in rows if row.get("status") == "attention"),
        "error_count": sum(1 for row in rows if row.get("status") == "error"),
        "node_count": sum(int(row.get("node_count") or 0) for row in rows),
        "action_intelligence_link_count": sum(
            int(row.get("action_intelligence_link_count") or 0) for row in rows
        ),
        "latest_eval_attention_count": sum(
            1
            for row in rows
            if str(row.get("latest_eval_status") or "") in LATEST_ATTENTION_STATUSES
        ),
        "missing_artifact_project_count": sum(
            1
            for row in rows
            if ((row.get("missing_carrier_fields") or {}).get("artifact_refs") or 0) > 0
        ),
        "unrecorded_transport_project_count": sum(
            1
            for row in rows
            if ((row.get("missing_carrier_fields") or {}).get("transport") or 0) > 0
        ),
        "current_carrier_complete_count": sum(
            1
            for row in rows
            if (row.get("current_carrier") or {}).get("status") == "complete"
        ),
        "current_carrier_missing_count": sum(
            1
            for row in rows
            if (row.get("current_carrier") or {}).get("status") == "missing_fields"
        ),
    }


def _rel(repo: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def _render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        (
            "autoresearch carrier replay: "
            f"{summary['project_count']} projects, "
            f"{summary['ok_count']} ok, "
            f"{summary['attention_count']} attention, "
            f"{summary['error_count']} error"
        )
    ]
    for row in report["projects"]:
        reasons = ", ".join(row.get("attention_reasons") or [])
        suffix = f" [{reasons}]" if reasons else ""
        lines.append(
            "- "
            f"{row['project']}: {row['status']} "
            f"nodes={row.get('node_count', 0)} "
            f"latest={row.get('latest_eval_status', 'n/a')} "
            f"current={((row.get('current_carrier') or {}).get('status') or 'n/a')} "
            f"actions={row.get('action_intelligence_link_count', 0)}"
            f"{suffix}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay read-only autoresearch projection carriers across projects."
    )
    parser.add_argument(
        "--project",
        action="append",
        default=[],
        help="Project slug or path. Repeat for multiple projects. Defaults to discovery.",
    )
    parser.add_argument("--repo", type=Path, default=REPO_ROOT, help="Repo root")
    parser.add_argument("--max-projects", type=int, default=25, help="Discovery limit")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on attention/error")
    parser.add_argument("--out", type=Path, help="Optional output path")
    args = parser.parse_args(argv)

    report = build_carrier_replay(
        repo=args.repo,
        projects=args.project or None,
        max_projects=args.max_projects,
    )
    text = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.json or args.out
        else _render_text(report)
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.strict and (
        report["summary"]["attention_count"] or report["summary"]["error_count"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
