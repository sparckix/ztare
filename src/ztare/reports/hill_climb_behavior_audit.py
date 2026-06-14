"""Read-only audit for autoresearch stagnation escape behavior.

The in-loop workbench has several breadth mechanisms: stagnation pivots,
parallel mutator blitzes, and primitive-class rotation ledgers. This report
joins the existing workspace artifacts and answers a narrower question:

When a run became stagnant, did any of those mechanisms leave evidence?

It does not claim the mechanism helped. It only makes missing or silent
activation visible.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.ztare.validator.utilities.pivot_heuristics import get_pivot_thresholds


REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"

PIVOT_EVENT_TYPES = {
    "topological_pivot_profile_injected",
    "topological_pivot_emergency",
    "v4_bounded_mutation_override",
    "pivot_skipped_gp149_i3",
}
PIVOT_ACTIONS = {"stagnation_pivot", "emergency_pivot"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except OSError:
        return []
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _workspace_label(workspace: Path, repo: Path) -> str:
    try:
        return str(workspace.relative_to(repo))
    except ValueError:
        return str(workspace)


def _workspace_project_slug(workspace: Path, repo: Path) -> str:
    try:
        rel = workspace.relative_to(repo / "projects")
    except ValueError:
        return ""
    return rel.parts[0] if rel.parts else ""


def _project_root_for_workspace(workspace: Path, repo: Path) -> Path | None:
    slug = _workspace_project_slug(workspace, repo)
    if slug:
        return repo / "projects" / slug
    parts = workspace.parts
    if "projects" not in parts:
        return None
    idx = parts.index("projects")
    if idx + 1 >= len(parts):
        return None
    return Path(*parts[: idx + 2])


def _pending_eigenquestion_count(project_root: Path | None) -> int:
    if project_root is None or not project_root.exists():
        return 0
    charter = project_root / "project_charter.md"
    try:
        charter_mtime = charter.stat().st_mtime if charter.exists() else 0.0
    except OSError:
        charter_mtime = 0.0
    pending = 0
    for proposal in project_root.glob("proposed_eigenquestion_*.md"):
        try:
            if proposal.stat().st_mtime > charter_mtime:
                pending += 1
        except OSError:
            continue
    return pending


def _rubric_name_from_telemetry(telemetry: list[dict[str, Any]], project_slug: str) -> str:
    for row in reversed(telemetry):
        if row.get("record_type") == "run_start" and row.get("rubric"):
            return str(row.get("rubric") or "")
    return project_slug


def _load_rubric(repo: Path, rubric_name: str) -> dict[str, Any]:
    if not rubric_name:
        return {}
    rubric_path = Path(rubric_name)
    candidates: list[Path] = []
    if rubric_path.suffix == ".json":
        candidates.append(rubric_path if rubric_path.is_absolute() else repo / rubric_path)
    else:
        candidates.append(repo / "rubrics" / f"{rubric_name}.json")
        candidates.append(repo / "rubrics" / rubric_name)
    for candidate in candidates:
        data = _read_json(candidate)
        if data:
            return data
    return {}


def _effective_pivot_threshold(
    *,
    repo: Path,
    workspace: Path,
    telemetry: list[dict[str, Any]],
    default_threshold: int,
) -> tuple[int, str, str]:
    project_slug = _workspace_project_slug(workspace, repo)
    rubric_name = _rubric_name_from_telemetry(telemetry, project_slug)
    rubric = _load_rubric(repo, rubric_name)
    if not rubric:
        return default_threshold, rubric_name, "fallback"
    override = rubric.get("composition_stagnation_threshold")
    try:
        override_i = int(override) if override is not None else None
    except (TypeError, ValueError):
        override_i = None
    threshold, _ = get_pivot_thresholds(
        is_v4_project=project_slug.startswith("ztare_on_ztare"),
        rubric_mode=str(rubric.get("rubric_mode") or ""),
        rubric_stagnation_override=override_i,
    )
    return max(default_threshold, threshold), rubric_name, "rubric"


def _row_iteration(row: dict[str, Any]) -> int | None:
    for key in ("iteration_index", "iteration", "iter"):
        if row.get(key) is None:
            continue
        try:
            return int(row.get(key))
        except (TypeError, ValueError):
            continue
    return None


def _row_run_id(row: dict[str, Any]) -> str:
    value = row.get("run_id")
    return str(value) if value is not None else ""


def _active_control_events(
    *,
    iter_rows: list[dict[str, Any]],
    loop_events: list[dict[str, Any]],
    blitz_rows: list[dict[str, Any]],
    primitive_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events_by_key: dict[tuple[str, int], set[str]] = {}

    def add(mechanism: str, row: dict[str, Any]) -> None:
        iteration = _row_iteration(row)
        if iteration is None:
            return
        run_id = _row_run_id(row)
        events_by_key.setdefault((run_id, iteration), set()).add(mechanism)

    for row in iter_rows:
        if str(row.get("loop_control_action") or "") in PIVOT_ACTIONS:
            add("pivot_action", row)
    for row in loop_events:
        if str(row.get("event_type") or "") in PIVOT_EVENT_TYPES:
            add("pivot_event", row)
    for row in blitz_rows:
        if _safe_int(row.get("k"), 1) > 1:
            add("parallel_blitz", row)
    for row in primitive_rows:
        if row.get("class_name") or row.get("primitive_class") or row.get("class"):
            add("primitive_class_rotation", row)
    events = [
        {
            "mechanisms": tuple(sorted(mechanisms)),
            "run_id": run_id,
            "iteration": iteration,
        }
        for (run_id, iteration), mechanisms in events_by_key.items()
    ]
    return sorted(events, key=lambda row: (row["run_id"], row["iteration"]))


def _active_control_outcomes(
    *,
    iter_rows: list[dict[str, Any]],
    control_events: list[dict[str, Any]],
    window: int = 3,
) -> dict[str, Any]:
    rows_by_run: dict[str, list[dict[str, Any]]] = {}
    for row in iter_rows:
        iteration = _row_iteration(row)
        if iteration is None:
            continue
        rows_by_run.setdefault(_row_run_id(row), []).append(row)
    for rows in rows_by_run.values():
        rows.sort(key=lambda row: _row_iteration(row) or 0)

    improved = 0
    champion = 0
    stagnation_drop = 0
    success = 0
    no_followup = 0
    windows = 0
    for event in control_events:
        run_rows = rows_by_run.get(str(event.get("run_id") or ""), [])
        event_iter = int(event["iteration"])
        current = next((row for row in run_rows if _row_iteration(row) == event_iter), {})
        current_score = _safe_float(current.get("score"))
        current_stagnation = _safe_int(current.get("stagnation_count"))
        followup = [
            row for row in run_rows
            if event_iter < (_row_iteration(row) or -1) <= event_iter + window
        ]
        if not followup:
            no_followup += 1
            continue
        windows += 1
        score_improved = any(bool(row.get("score_improved")) for row in followup)
        if not score_improved and current_score is not None:
            score_improved = any(
                (score is not None and score > current_score)
                for score in (_safe_float(row.get("score")) for row in followup)
            )
        champion_promoted = any(bool(row.get("champion_promoted")) for row in followup)
        stagnation_lowered = any(
            _safe_int(row.get("stagnation_count"), current_stagnation) < current_stagnation
            for row in followup
        )
        improved += int(score_improved)
        champion += int(champion_promoted)
        stagnation_drop += int(stagnation_lowered)
        success += int(score_improved or champion_promoted or stagnation_lowered)

    return {
        "window": window,
        "active_control_event_count": len(control_events),
        "post_control_window_count": windows,
        "post_control_no_followup_count": no_followup,
        "post_control_improvement_count": improved,
        "post_control_champion_count": champion,
        "post_control_stagnation_drop_count": stagnation_drop,
        "post_control_success_count": success,
        "post_control_success_rate": (success / windows) if windows else None,
    }


def discover_workspaces(repo: Path = REPO, project: str | None = None) -> list[Path]:
    """Return candidate autoresearch workspaces with known trace files."""

    projects_dir = repo / "projects"
    if project:
        roots = [projects_dir / project]
    else:
        roots = [projects_dir]
    workspaces: set[Path] = set()
    trace_names = {
        "iteration_telemetry.jsonl",
        "loop_events.jsonl",
        "parallel_blitz_log.jsonl",
        "explored_primitive_classes.jsonl",
    }
    for root in roots:
        if not root.exists():
            continue
        for trace in trace_names:
            for path in root.glob(f"**/workspace/{trace}"):
                workspaces.add(path.parent)
    return sorted(workspaces)


@dataclass(frozen=True)
class HillClimbWorkspaceAudit:
    workspace: str
    iteration_count: int
    max_stagnation_count: int
    effective_pivot_threshold: int
    threshold_source: str
    rubric: str
    pivot_event_count: int
    pivot_action_count: int
    blitz_iteration_count: int
    primitive_class_count: int
    pending_refresh_count: int
    pending_pivot_count: int
    pending_underidentified_count: int
    escape_signal_count: int
    active_control_signal_count: int
    advisory_signal_count: int
    diagnostic_signal_count: int
    mechanism_status_counts: dict[str, int]
    active_mechanisms: tuple[str, ...]
    advisory_mechanisms: tuple[str, ...]
    diagnostic_mechanisms: tuple[str, ...]
    active_control_event_count: int
    post_control_window_count: int
    post_control_no_followup_count: int
    post_control_success_count: int
    post_control_improvement_count: int
    post_control_champion_count: int
    post_control_stagnation_drop_count: int
    post_control_success_rate: float | None
    status: str
    latest_loop_action: str | None
    latest_pending_action: str | None
    latest_information_yield_rationale: str


def audit_workspace(
    workspace: Path,
    *,
    repo: Path = REPO,
    stagnation_threshold: int = 2,
) -> HillClimbWorkspaceAudit:
    telemetry = _read_jsonl(workspace / "iteration_telemetry.jsonl")
    iter_rows = [row for row in telemetry if row.get("record_type") == "iteration"]
    loop_events = _read_jsonl(workspace / "loop_events.jsonl")
    blitz_rows = _read_jsonl(workspace / "parallel_blitz_log.jsonl")
    primitive_rows = _read_jsonl(workspace / "explored_primitive_classes.jsonl")
    effective_threshold, rubric_name, threshold_source = _effective_pivot_threshold(
        repo=repo,
        workspace=workspace,
        telemetry=telemetry,
        default_threshold=stagnation_threshold,
    )

    max_stagnation = max(
        (_safe_int(row.get("stagnation_count")) for row in iter_rows),
        default=0,
    )
    pivot_event_count = sum(
        1 for row in loop_events if str(row.get("event_type") or "") in PIVOT_EVENT_TYPES
    )
    pivot_action_count = sum(
        1 for row in iter_rows if str(row.get("loop_control_action") or "") in PIVOT_ACTIONS
    )
    blitz_iteration_count = sum(1 for row in blitz_rows if _safe_int(row.get("k"), 1) > 1)
    primitive_class_count = len(primitive_rows)
    blitz_survival_report_count = int((workspace / "blitz_survival_report.json").exists())
    pending_eigenquestion_count = _pending_eigenquestion_count(
        _project_root_for_workspace(workspace, repo)
    )
    pending_refresh_count = sum(
        1
        for row in iter_rows
        if str(row.get("pending_loop_action") or "") == "REFRESH_SPECIALISTS"
    )
    pending_pivot_count = sum(
        1
        for row in iter_rows
        if str(row.get("pending_loop_action") or "") == "PIVOT_REQUIRED"
    )
    pending_underidentified_count = sum(
        1
        for row in iter_rows
        if str(row.get("pending_loop_action") or "") == "UNDERIDENTIFIED"
    )
    active_mechanisms = tuple(
        name
        for name, count in (
            ("pivot_events", pivot_event_count),
            ("pivot_actions", pivot_action_count),
            ("parallel_blitz", blitz_iteration_count),
            ("primitive_class_rotation", primitive_class_count),
        )
        if count > 0
    )
    advisory_mechanisms = tuple(
        name
        for name, count in (
            ("pending_eigenquestion_review", pending_eigenquestion_count),
        )
        if count > 0
    )
    diagnostic_mechanisms = tuple(
        name
        for name, count in (
            ("blitz_survival_report", blitz_survival_report_count),
        )
        if count > 0
    )
    active_control_signal_count = (
        pivot_event_count
        + pivot_action_count
        + blitz_iteration_count
        + primitive_class_count
    )
    advisory_signal_count = pending_eigenquestion_count
    diagnostic_signal_count = blitz_survival_report_count
    escape_signal_count = active_control_signal_count
    mechanism_status_counts = {
        "active": active_control_signal_count,
        "advisory": advisory_signal_count,
        "diagnostic": diagnostic_signal_count,
    }
    control_outcomes = _active_control_outcomes(
        iter_rows=iter_rows,
        control_events=_active_control_events(
            iter_rows=iter_rows,
            loop_events=loop_events,
            blitz_rows=blitz_rows,
            primitive_rows=primitive_rows,
        ),
    )
    if not iter_rows:
        status = "no_iteration_telemetry"
    elif max_stagnation < stagnation_threshold:
        status = "no_stagnation_signal"
    elif active_control_signal_count > 0:
        status = "escape_evidence_observed"
    elif max_stagnation <= effective_threshold:
        status = "stagnation_reached_no_next_control_boundary"
    else:
        status = "control_due_without_breadth_evidence"

    latest = iter_rows[-1] if iter_rows else {}
    return HillClimbWorkspaceAudit(
        workspace=_workspace_label(workspace, repo),
        iteration_count=len(iter_rows),
        max_stagnation_count=max_stagnation,
        effective_pivot_threshold=effective_threshold,
        threshold_source=threshold_source,
        rubric=rubric_name,
        pivot_event_count=pivot_event_count,
        pivot_action_count=pivot_action_count,
        blitz_iteration_count=blitz_iteration_count,
        primitive_class_count=primitive_class_count,
        pending_refresh_count=pending_refresh_count,
        pending_pivot_count=pending_pivot_count,
        pending_underidentified_count=pending_underidentified_count,
        escape_signal_count=escape_signal_count,
        active_control_signal_count=active_control_signal_count,
        advisory_signal_count=advisory_signal_count,
        diagnostic_signal_count=diagnostic_signal_count,
        mechanism_status_counts=mechanism_status_counts,
        active_mechanisms=active_mechanisms,
        advisory_mechanisms=advisory_mechanisms,
        diagnostic_mechanisms=diagnostic_mechanisms,
        active_control_event_count=control_outcomes["active_control_event_count"],
        post_control_window_count=control_outcomes["post_control_window_count"],
        post_control_no_followup_count=control_outcomes["post_control_no_followup_count"],
        post_control_success_count=control_outcomes["post_control_success_count"],
        post_control_improvement_count=control_outcomes["post_control_improvement_count"],
        post_control_champion_count=control_outcomes["post_control_champion_count"],
        post_control_stagnation_drop_count=control_outcomes["post_control_stagnation_drop_count"],
        post_control_success_rate=control_outcomes["post_control_success_rate"],
        status=status,
        latest_loop_action=latest.get("loop_control_action"),
        latest_pending_action=latest.get("pending_loop_action"),
        latest_information_yield_rationale=str(
            latest.get("information_yield_rationale") or ""
        ),
    )


def build_hill_climb_behavior_audit(
    *,
    repo: Path = REPO,
    project: str | None = None,
    stagnation_threshold: int = 2,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = [
        audit_workspace(
            workspace,
            repo=repo,
            stagnation_threshold=stagnation_threshold,
        )
        for workspace in discover_workspaces(repo=repo, project=project)
    ]
    rows.sort(
        key=lambda row: (
            row.status != "control_due_without_breadth_evidence",
            row.status != "stagnation_reached_no_next_control_boundary",
            -row.max_stagnation_count,
            row.workspace,
        )
    )
    shown = rows[:limit] if limit and limit > 0 else rows
    status_counts: dict[str, int] = {}
    mechanism_status_totals = {"active": 0, "advisory": 0, "diagnostic": 0}
    post_control_outcome_totals = {
        "active_control_event_count": 0,
        "post_control_window_count": 0,
        "post_control_no_followup_count": 0,
        "post_control_success_count": 0,
        "post_control_improvement_count": 0,
        "post_control_champion_count": 0,
        "post_control_stagnation_drop_count": 0,
        "post_control_success_rate": None,
    }
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        mechanism_status_totals["active"] += row.active_control_signal_count
        mechanism_status_totals["advisory"] += row.advisory_signal_count
        mechanism_status_totals["diagnostic"] += row.diagnostic_signal_count
        for key in (
            "active_control_event_count",
            "post_control_window_count",
            "post_control_no_followup_count",
            "post_control_success_count",
            "post_control_improvement_count",
            "post_control_champion_count",
            "post_control_stagnation_drop_count",
        ):
            post_control_outcome_totals[key] += getattr(row, key)
    windows = post_control_outcome_totals["post_control_window_count"]
    if windows:
        post_control_outcome_totals["post_control_success_rate"] = (
            post_control_outcome_totals["post_control_success_count"] / windows
        )
    stagnant_rows = [
        row for row in rows if row.max_stagnation_count >= stagnation_threshold
    ]
    return {
        "schema": "ztare-hill-climb-behavior-audit-v2",
        "project": project,
        "stagnation_threshold": stagnation_threshold,
        "workspace_count": len(rows),
        "stagnant_workspace_count": len(stagnant_rows),
        "status_counts": dict(sorted(status_counts.items())),
        "mechanism_status_totals": mechanism_status_totals,
        "post_control_outcome_totals": post_control_outcome_totals,
        "rows": [asdict(row) for row in shown],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "Autoresearch hill-climb behavior audit",
        f"workspaces={report['workspace_count']} stagnant_workspaces={report['stagnant_workspace_count']} threshold={report['stagnation_threshold']}",
        "status_counts=" + json.dumps(report["status_counts"], sort_keys=True),
        "mechanism_status_totals=" + json.dumps(report.get("mechanism_status_totals", {}), sort_keys=True),
        "post_control_outcomes=" + json.dumps(report.get("post_control_outcome_totals", {}), sort_keys=True),
    ]
    for row in report["rows"][:40]:
        lines.append(
            "- {status} {workspace}: iters={iteration_count} max_stag={max_stagnation_count} threshold={effective_pivot_threshold} "
            "pivot_events={pivot_event_count} pivot_actions={pivot_action_count} "
            "blitz={blitz_iteration_count} primitive_classes={primitive_class_count} "
            "active={active_control_signal_count} advisory={advisory_signal_count} diagnostic={diagnostic_signal_count} "
            "post_control_success={post_control_success_count}/{post_control_window_count} "
            "pending_refresh={pending_refresh_count} "
            "latest_yield={latest_information_yield_rationale}".format(
                **row
            )
        )
    if len(report["rows"]) > 40:
        lines.append(f"... {len(report['rows']) - 40} additional rows omitted")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Restrict to projects/<slug> and archives under it.")
    parser.add_argument(
        "--stagnation-threshold",
        type=int,
        default=2,
        help="Minimum stagnation count to include; rubric thresholds decide whether control was due.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit emitted rows; 0 means all.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    report = build_hill_climb_behavior_audit(
        project=args.project,
        stagnation_threshold=args.stagnation_threshold,
        limit=args.limit if args.limit > 0 else None,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
