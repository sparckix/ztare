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
from datetime import datetime, timezone
import json
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ztare.validator.utilities.pivot_heuristics import get_pivot_thresholds


REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"

PIVOT_EVENT_TYPES = {
    "topological_pivot_profile_injected",
    "topological_pivot_emergency",
    "v4_bounded_mutation_override",
    "pivot_skipped_gp149_i3",
}
PIVOT_ACTIONS = {"stagnation_pivot", "emergency_pivot"}
RECOVERY_RESOLUTION_FILE = "control_episode_recovery_resolutions.jsonl"
RECOVERY_RESOLUTION_RECORD_TYPE = "control_episode_recovery_resolution"
RECOVERY_RESOLUTION_STATUSES = {
    "reason_recorded",
    "reviewed_no_lift",
    "superseded",
    "deferred",
}
RECOVERY_CLOSING_RESOLUTION_STATUSES = {
    "reason_recorded",
    "reviewed_no_lift",
    "superseded",
}


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


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


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


def _project_slug_from_workspace_label(label: str) -> str:
    parts = Path(label).parts
    if "projects" not in parts:
        return ""
    idx = parts.index("projects")
    if idx + 1 >= len(parts):
        return ""
    return parts[idx + 1]


def _rel(path: Path, repo: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _workspace_path_from_label(workspace: str | Path, repo: Path) -> Path:
    workspace_path = Path(workspace)
    if not workspace_path.is_absolute():
        workspace_path = repo / workspace_path
    return workspace_path


def _ensure_workspace_under_repo(workspace: str | Path, repo: Path) -> Path:
    workspace_path = _workspace_path_from_label(workspace, repo)
    repo_resolved = repo.resolve()
    workspace_resolved = workspace_path.resolve(strict=False)
    if workspace_resolved != repo_resolved and repo_resolved not in workspace_resolved.parents:
        raise ValueError(f"workspace must be inside repo: {workspace}")
    if not workspace_path.exists():
        raise ValueError(f"workspace does not exist: {_rel(workspace_path, repo)}")
    if not workspace_path.is_dir():
        raise ValueError(f"workspace is not a directory: {_rel(workspace_path, repo)}")
    return workspace_path


def _recovery_episode_key(item: dict[str, Any]) -> tuple[str, int, int, str]:
    iteration = _safe_int(item.get("iteration"), -1)
    return (
        str(item.get("run_id") or ""),
        iteration,
        _safe_int(item.get("last_control_iteration"), iteration),
        str(item.get("outcome_status") or ""),
    )


def _recovery_resolution_index(workspace: str, repo: Path) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    workspace_path = _workspace_path_from_label(workspace, repo)
    rows = _read_jsonl(workspace_path / RECOVERY_RESOLUTION_FILE)
    index: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("record_type") != RECOVERY_RESOLUTION_RECORD_TYPE:
            continue
        status = str(row.get("resolution_status") or "")
        if status not in RECOVERY_RESOLUTION_STATUSES:
            continue
        index[_recovery_episode_key(row)] = row
    return index


def _apply_recovery_resolution(
    candidate: dict[str, Any],
    resolution: dict[str, Any] | None,
) -> dict[str, Any]:
    if not resolution:
        return candidate
    resolved = dict(candidate)
    status = str(resolution.get("resolution_status") or "")
    resolved["resolution_status"] = status
    resolved["resolution_reason"] = str(resolution.get("reason") or "")
    resolved["resolution_recorded_at"] = str(resolution.get("recorded_at") or "")
    resolved["resolution_recorded_by"] = str(resolution.get("recorded_by") or "")
    resolved["resolution_closes_queue_item"] = (
        status in RECOVERY_CLOSING_RESOLUTION_STATUSES
    )
    return resolved


def record_control_episode_recovery_resolution(
    *,
    workspace: str | Path,
    repo: Path = REPO,
    run_id: str = "",
    iteration: int,
    last_control_iteration: int | None = None,
    outcome_status: str,
    resolution_status: str,
    reason: str,
    recorded_by: str = "local",
    event_iterations: Iterable[int] | None = None,
    mechanisms: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Append an explicit review receipt for one non-success control episode.

    The receipt resolves audit work items only. It does not change the measured
    post-control outcome counts and must not be interpreted as loop success.
    """

    workspace_path = _ensure_workspace_under_repo(workspace, repo)
    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("reason is required")
    if resolution_status not in RECOVERY_RESOLUTION_STATUSES:
        allowed = ", ".join(sorted(RECOVERY_RESOLUTION_STATUSES))
        raise ValueError(f"unknown resolution_status {resolution_status!r}; allowed: {allowed}")
    if not outcome_status:
        raise ValueError("outcome_status is required")
    last_iteration = iteration if last_control_iteration is None else last_control_iteration
    row = {
        "record_type": RECOVERY_RESOLUTION_RECORD_TYPE,
        "schema": "ztare-hill-climb-control-recovery-resolution-v1",
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace": _workspace_label(workspace_path, repo),
        "run_id": str(run_id or ""),
        "iteration": int(iteration),
        "last_control_iteration": int(last_iteration),
        "event_iterations": [int(value) for value in (event_iterations or [])],
        "mechanisms": [str(value) for value in (mechanisms or [])],
        "outcome_status": str(outcome_status),
        "resolution_status": resolution_status,
        "reason": clean_reason,
        "recorded_by": recorded_by.strip() or "local",
        "counts_as_control_success": False,
    }
    _append_jsonl(workspace_path / RECOVERY_RESOLUTION_FILE, row)
    return row


INTAKE_STATUS_LEGACY_ALIASES = {
    "ready": "ready",
    "compiled_evidence_without_project_intake": (
        "compiled_evidence_without_admission_packet"
    ),
    "missing_project_intake": "missing_admission_packet",
}
LEGACY_INTAKE_STATUS_ALIASES = {
    legacy: canonical for canonical, legacy in INTAKE_STATUS_LEGACY_ALIASES.items()
}


def _canonical_intake_status(value: str | None) -> str:
    item = str(value or "").strip()
    return LEGACY_INTAKE_STATUS_ALIASES.get(item, item)


def _legacy_admission_packet_status(value: str | None) -> str:
    item = _canonical_intake_status(value)
    return INTAKE_STATUS_LEGACY_ALIASES.get(item, item)


def _intake_path_for_recovery(*, project: str, repo: Path) -> str:
    if not project:
        return ""
    project_root = repo / "projects" / project
    candidates = [
        project_root / "project_intake.json",
        project_root / f"{project}_intake.json",
        repo / f"{project}_intake.json",
        repo / "examples" / "project_packets" / f"{project}_intake.json",
        repo / "examples" / "project_packets" / f"ready_{project}_intake.json",
        repo / "examples" / "substrate_packets" / f"{project}_intake.json",
        repo / "examples" / "substrate_packets" / f"ready_{project}_intake.json",
        project_root / "project_packet.json",
        project_root / f"{project}_packet.json",
        repo / f"{project}_packet.json",
        repo / "examples" / "project_packets" / f"{project}_packet.json",
        repo / "examples" / "project_packets" / f"ready_{project}_packet.json",
        repo / "examples" / "substrate_packets" / f"{project}_packet.json",
        repo / "examples" / "substrate_packets" / f"ready_{project}_packet.json",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return _rel(candidate, repo)
    return ""


def _packet_path_for_recovery(*, project: str, repo: Path) -> str:
    return _intake_path_for_recovery(project=project, repo=repo)


def _compiled_evidence_packet_path_for_recovery(*, project: str, repo: Path) -> str:
    if not project:
        return ""
    project_root = repo / "projects" / project
    candidates = [
        project_root / "compiled_evidence_packet.json",
        project_root / "workspace" / "compiled_evidence_packet.json",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return _rel(candidate, repo)
    return ""


def _project_intake_status(*, packet: str, compiled_evidence_packet: str) -> str:
    if packet:
        return "ready"
    if compiled_evidence_packet:
        return "compiled_evidence_without_project_intake"
    return "missing_project_intake"


def _admission_packet_status(*, packet: str, compiled_evidence_packet: str) -> str:
    return _legacy_admission_packet_status(
        _project_intake_status(
            packet=packet,
            compiled_evidence_packet=compiled_evidence_packet,
        )
    )


def _intake_status(*, packet: str, compiled_evidence_packet: str) -> str:
    return _project_intake_status(
        packet=packet,
        compiled_evidence_packet=compiled_evidence_packet,
    )


def _trace_command_for_recovery(project: str, rubric: str, *, packet: str = "") -> str:
    if not project:
        return "make autoresearch-hillclimb-audit RECOVERY_QUEUE=1 RECOVERY_LIMIT=20 JSON=1"
    parts = ["ztare", "autoresearch", "trace", "--project", project]
    if rubric:
        parts.extend(["--rubric", rubric])
    if packet:
        parts.extend(["--intake", packet])
    parts.append("--json")
    return " ".join(shlex.quote(part) for part in parts)


def _preflight_command_for_recovery(project: str, rubric: str, *, packet: str = "") -> str:
    if not project or not rubric or not packet:
        return ""
    parts = [
        "ztare",
        "autoresearch",
        "run",
        "--project",
        project,
        "--rubric",
        rubric,
        "--intake",
        packet,
        "--preflight-only",
    ]
    return " ".join(shlex.quote(part) for part in parts)


def _kernel_entry_trace_for_recovery(
    *,
    project: str,
    rubric: str,
    packet: str,
    repo: Path,
    trace_cache: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    if not project or not rubric or not packet:
        return {}
    key = (project, rubric, packet)
    if key in trace_cache:
        return trace_cache[key]
    try:
        from ztare.reports.autoresearch_trace import build_autoresearch_trace

        trace = build_autoresearch_trace(
            project=project,
            rubric=rubric,
            packet=packet,
            repo=repo,
            full_health=False,
        )
    except Exception as exc:  # noqa: BLE001
        summary = {
            "available": False,
            "trace_status": "trace_unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "next_command": _trace_command_for_recovery(project, rubric, packet=packet),
        }
        trace_cache[key] = summary
        return summary

    kernel_entry = trace.get("kernel_entry")
    if not isinstance(kernel_entry, dict):
        kernel_entry = {}
    blockers = [
        str(row.get("id") or "")
        for row in kernel_entry.get("blockers", []) or []
        if isinstance(row, dict) and row.get("id")
    ]
    blocker_commands = [
        str(row.get("next_command") or "").strip()
        for row in kernel_entry.get("blockers", []) or []
        if isinstance(row, dict) and str(row.get("next_command") or "").strip()
    ]
    next_commands = [
        str(command).strip()
        for command in trace.get("next_commands", []) or []
        if str(command).strip()
    ]
    can_enter = bool(kernel_entry.get("can_enter_kernel"))
    if can_enter:
        next_command = (
            str(kernel_entry.get("preflight_command") or "").strip()
            or str(kernel_entry.get("entry_command") or "").strip()
            or str(kernel_entry.get("run_command") or "").strip()
        )
    else:
        next_command = (
            blocker_commands[0]
            if blocker_commands
            else next_commands[0]
            if next_commands
            else _trace_command_for_recovery(project, rubric, packet=packet)
        )
    summary = {
        "available": True,
        "trace_status": trace.get("status"),
        "readiness": trace.get("readiness") or kernel_entry.get("readiness"),
        "status": kernel_entry.get("status"),
        "can_enter_kernel": can_enter,
        "blockers": blockers,
        "blocking_missing": list(trace.get("blocking_missing") or []),
        "next_command": next_command,
    }
    trace_cache[key] = summary
    return summary


def _packet_draft_command_for_recovery(
    project: str,
    *,
    compiled_evidence_packet: str = "",
) -> str:
    if not project or not compiled_evidence_packet:
        return ""
    parts = [
        "ztare",
        "project",
        "intake",
        "draft-from-compiled",
        "--project",
        project,
        "--path",
        f"projects/{project}/{project}_intake.json",
    ]
    return " ".join(shlex.quote(part) for part in parts)


def _fixture_like_project(project: str) -> bool:
    lowered = project.lower()
    return bool(
        lowered.startswith("autoresearch_control_demo")
        or "fixture" in lowered
        or lowered.startswith("dk0_")
    )


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
    observed_no_success = 0
    no_followup = 0
    windows = 0
    diagnostics: list[dict[str, Any]] = []
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
            diagnostics.append(
                {
                    "run_id": str(event.get("run_id") or ""),
                    "iteration": event_iter,
                    "mechanisms": list(event.get("mechanisms") or []),
                    "outcome_status": "control_fired_without_followup",
                    "routing_hint": "run_followup_or_record_no_followup_reason",
                    "followup_window": window,
                    "followup_iteration_count": 0,
                    "followup_iterations": [],
                    "current_score": current_score,
                    "best_followup_score": None,
                    "score_delta": None,
                    "current_stagnation_count": current_stagnation,
                    "min_followup_stagnation_count": None,
                    "score_improved": False,
                    "champion_promoted": False,
                    "stagnation_dropped": False,
                }
            )
            continue
        windows += 1
        score_improved = any(bool(row.get("score_improved")) for row in followup)
        followup_scores = [_safe_float(row.get("score")) for row in followup]
        numeric_followup_scores = [score for score in followup_scores if score is not None]
        best_followup_score = max(numeric_followup_scores) if numeric_followup_scores else None
        if not score_improved and current_score is not None:
            score_improved = bool(
                best_followup_score is not None and best_followup_score > current_score
            )
        champion_promoted = any(bool(row.get("champion_promoted")) for row in followup)
        followup_stagnation_counts = [
            _safe_int(row.get("stagnation_count"), current_stagnation)
            for row in followup
        ]
        min_followup_stagnation = (
            min(followup_stagnation_counts) if followup_stagnation_counts else None
        )
        stagnation_lowered = bool(
            min_followup_stagnation is not None
            and min_followup_stagnation < current_stagnation
        )
        event_succeeded = bool(score_improved or champion_promoted or stagnation_lowered)
        improved += int(score_improved)
        champion += int(champion_promoted)
        stagnation_drop += int(stagnation_lowered)
        success += int(event_succeeded)
        observed_no_success += int(not event_succeeded)
        diagnostics.append(
            {
                "run_id": str(event.get("run_id") or ""),
                "iteration": event_iter,
                "mechanisms": list(event.get("mechanisms") or []),
                "outcome_status": (
                    "control_success"
                    if event_succeeded
                    else "control_observed_no_success"
                ),
                "routing_hint": (
                    "preserve_or_replay_control"
                    if event_succeeded
                    else "review_control_selection_or_measurement"
                ),
                "followup_window": window,
                "followup_iteration_count": len(followup),
                "followup_iterations": [
                    iteration
                    for iteration in (_row_iteration(row) for row in followup)
                    if iteration is not None
                ],
                "current_score": current_score,
                "best_followup_score": best_followup_score,
                "score_delta": (
                    best_followup_score - current_score
                    if best_followup_score is not None and current_score is not None
                    else None
                ),
                "current_stagnation_count": current_stagnation,
                "min_followup_stagnation_count": min_followup_stagnation,
                "score_improved": bool(score_improved),
                "champion_promoted": bool(champion_promoted),
                "stagnation_dropped": bool(stagnation_lowered),
            }
        )

    return {
        "window": window,
        "active_control_event_count": len(control_events),
        "post_control_window_count": windows,
        "post_control_no_followup_count": no_followup,
        "post_control_observed_no_success_count": observed_no_success,
        "post_control_improvement_count": improved,
        "post_control_champion_count": champion,
        "post_control_stagnation_drop_count": stagnation_drop,
        "post_control_success_count": success,
        "post_control_success_rate": (success / windows) if windows else None,
        "post_control_diagnostics": diagnostics,
    }


def _control_episodes(
    control_events: list[dict[str, Any]],
    *,
    window: int = 3,
) -> list[dict[str, Any]]:
    """Group repeated controls into non-overlapping follow-up episodes."""

    episodes: list[dict[str, Any]] = []
    for event in sorted(
        control_events,
        key=lambda row: (str(row.get("run_id") or ""), int(row.get("iteration") or 0)),
    ):
        run_id = str(event.get("run_id") or "")
        iteration = int(event.get("iteration") or 0)
        mechanisms = set(str(mech) for mech in event.get("mechanisms") or ())
        if (
            episodes
            and episodes[-1]["run_id"] == run_id
            and iteration <= int(episodes[-1]["last_control_iteration"]) + window
        ):
            episodes[-1]["last_control_iteration"] = iteration
            episodes[-1]["event_iterations"].append(iteration)
            episodes[-1]["mechanisms"].update(mechanisms)
            episodes[-1]["event_count"] += 1
            continue
        episodes.append(
            {
                "run_id": run_id,
                "iteration": iteration,
                "last_control_iteration": iteration,
                "event_iterations": [iteration],
                "mechanisms": mechanisms,
                "event_count": 1,
            }
        )
    for episode in episodes:
        episode["mechanisms"] = tuple(sorted(episode["mechanisms"]))
        episode["event_iterations"] = tuple(episode["event_iterations"])
    return episodes


def _active_control_episode_outcomes(
    *,
    control_events: list[dict[str, Any]],
    event_outcomes: dict[str, Any],
    window: int = 3,
) -> dict[str, Any]:
    episodes = _control_episodes(control_events, window=window)
    event_diagnostics = list(event_outcomes.get("post_control_diagnostics") or [])
    diagnostics_by_key = {
        (str(row.get("run_id") or ""), int(row.get("iteration") or 0)): row
        for row in event_diagnostics
    }

    windows = 0
    no_followup = 0
    observed_no_success = 0
    success = 0
    improved = 0
    champion = 0
    stagnation_drop = 0
    diagnostics: list[dict[str, Any]] = []
    for episode in episodes:
        child = [
            diagnostics_by_key[(str(episode["run_id"]), iteration)]
            for iteration in episode["event_iterations"]
            if (str(episode["run_id"]), iteration) in diagnostics_by_key
        ]
        child_counts: dict[str, int] = {}
        for row in child:
            status = str(row.get("outcome_status") or "unknown")
            child_counts[status] = child_counts.get(status, 0) + 1
        has_followup = any(int(row.get("followup_iteration_count") or 0) > 0 for row in child)
        episode_success = any(row.get("outcome_status") == "control_success" for row in child)
        episode_observed_no_success = (
            not episode_success
            and any(row.get("outcome_status") == "control_observed_no_success" for row in child)
        )
        if has_followup:
            windows += 1
        else:
            no_followup += 1
        success += int(episode_success)
        observed_no_success += int(episode_observed_no_success)
        improved += int(any(bool(row.get("score_improved")) for row in child))
        champion += int(any(bool(row.get("champion_promoted")) for row in child))
        stagnation_drop += int(any(bool(row.get("stagnation_dropped")) for row in child))
        outcome_status = (
            "control_success"
            if episode_success
            else "control_observed_no_success"
            if episode_observed_no_success
            else "control_fired_without_followup"
        )
        diagnostics.append(
            {
                "run_id": str(episode["run_id"]),
                "iteration": int(episode["iteration"]),
                "last_control_iteration": int(episode["last_control_iteration"]),
                "event_iterations": list(episode["event_iterations"]),
                "event_count": int(episode["event_count"]),
                "mechanisms": list(episode["mechanisms"]),
                "outcome_status": outcome_status,
                "routing_hint": (
                    "preserve_or_replay_control"
                    if episode_success
                    else "review_control_episode_or_measurement"
                    if episode_observed_no_success
                    else "run_followup_or_record_no_followup_reason"
                ),
                "followup_window": window,
                "constituent_outcome_counts": dict(sorted(child_counts.items())),
            }
        )

    return {
        "window": window,
        "control_episode_count": len(episodes),
        "post_control_episode_window_count": windows,
        "post_control_episode_no_followup_count": no_followup,
        "post_control_episode_observed_no_success_count": observed_no_success,
        "post_control_episode_improvement_count": improved,
        "post_control_episode_champion_count": champion,
        "post_control_episode_stagnation_drop_count": stagnation_drop,
        "post_control_episode_success_count": success,
        "post_control_episode_success_rate": (success / windows) if windows else None,
        "post_control_episode_diagnostics": diagnostics,
    }


def _control_episode_recovery_candidate(
    row: HillClimbWorkspaceAudit,
    diagnostic: dict[str, Any],
    *,
    repo: Path,
    trace_cache: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any] | None:
    status = str(diagnostic.get("outcome_status") or "")
    if status == "control_success":
        return None
    project = _project_slug_from_workspace_label(row.workspace)
    if status == "control_fired_without_followup":
        action = "run_followup_or_record_no_followup_reason"
        reason = "control episode fired but no follow-up iteration was observed"
        priority = 0
    elif status == "control_observed_no_success":
        action = "review_control_selection_or_measurement"
        reason = "control episode had follow-up but no measured lift"
        priority = 1
    else:
        action = "inspect_control_episode"
        reason = "control episode has an unknown non-success status"
        priority = 2
    packet = _intake_path_for_recovery(project=project, repo=repo)
    compiled_evidence_packet = _compiled_evidence_packet_path_for_recovery(
        project=project,
        repo=repo,
    )
    intake_status = _intake_status(
        packet=packet,
        compiled_evidence_packet=compiled_evidence_packet,
    )
    trace_command = _trace_command_for_recovery(project, row.rubric, packet=packet)
    preflight_command = _preflight_command_for_recovery(
        project,
        row.rubric,
        packet=packet,
    )
    kernel_entry_trace = _kernel_entry_trace_for_recovery(
        project=project,
        rubric=row.rubric,
        packet=packet,
        repo=repo,
        trace_cache=trace_cache,
    )
    packet_draft_command = _packet_draft_command_for_recovery(
        project,
        compiled_evidence_packet=compiled_evidence_packet if not packet else "",
    )
    next_command = (
        str(kernel_entry_trace.get("next_command") or "").strip()
        or preflight_command
        or packet_draft_command
        or trace_command
    )
    return {
        "priority": priority,
        "workspace": row.workspace,
        "project": project,
        "fixture_like_project": _fixture_like_project(project),
        "rubric": row.rubric,
        "run_id": diagnostic.get("run_id"),
        "iteration": diagnostic.get("iteration"),
        "last_control_iteration": diagnostic.get("last_control_iteration"),
        "event_iterations": list(diagnostic.get("event_iterations") or []),
        "event_count": diagnostic.get("event_count"),
        "mechanisms": list(diagnostic.get("mechanisms") or []),
        "outcome_status": status,
        "routing_hint": diagnostic.get("routing_hint"),
        "action": action,
        "reason": reason,
        "followup_window": diagnostic.get("followup_window"),
        "constituent_outcome_counts": dict(
            diagnostic.get("constituent_outcome_counts") or {}
        ),
        "project_intake": packet or None,
        "packet": packet or None,
        "compiled_evidence_packet": compiled_evidence_packet or None,
        "intake_status": intake_status,
        "admission_packet_status": _legacy_admission_packet_status(intake_status),
        "intake_draft_command": packet_draft_command or None,
        "packet_draft_command": packet_draft_command or None,
        "trace_command": trace_command,
        "preflight_command": preflight_command or None,
        "kernel_entry_status": kernel_entry_trace.get("status"),
        "kernel_entry_trace_status": kernel_entry_trace.get("trace_status"),
        "kernel_entry_readiness": kernel_entry_trace.get("readiness"),
        "kernel_entry_can_enter": (
            kernel_entry_trace.get("can_enter_kernel")
            if kernel_entry_trace
            else None
        ),
        "kernel_entry_blockers": list(kernel_entry_trace.get("blockers") or []),
        "kernel_entry_blocking_missing": list(
            kernel_entry_trace.get("blocking_missing") or []
        ),
        "kernel_entry_trace_error": kernel_entry_trace.get("error"),
        "next_command": next_command,
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
        "control_followup_policy.jsonl",
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
    control_followup_decision_count: int
    control_followup_block_count: int
    control_followup_allow_count: int
    active_control_event_count: int
    control_episode_count: int
    post_control_window_count: int
    post_control_episode_window_count: int
    post_control_no_followup_count: int
    post_control_episode_no_followup_count: int
    post_control_observed_no_success_count: int
    post_control_episode_observed_no_success_count: int
    post_control_success_count: int
    post_control_episode_success_count: int
    post_control_improvement_count: int
    post_control_episode_improvement_count: int
    post_control_champion_count: int
    post_control_episode_champion_count: int
    post_control_stagnation_drop_count: int
    post_control_episode_stagnation_drop_count: int
    post_control_success_rate: float | None
    post_control_episode_success_rate: float | None
    post_control_diagnostics: tuple[dict[str, Any], ...]
    post_control_episode_diagnostics: tuple[dict[str, Any], ...]
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
    followup_policy_rows = _read_jsonl(workspace / "control_followup_policy.jsonl")
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
    control_followup_decision_count = len(followup_policy_rows)
    control_followup_block_count = sum(
        1
        for row in followup_policy_rows
        if row.get("allowed") is False
        or str(row.get("decision") or "") == "observe_prior_control_followup"
    )
    control_followup_allow_count = max(
        0,
        control_followup_decision_count - control_followup_block_count,
    )
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
            ("control_followup_policy", control_followup_decision_count),
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
        + control_followup_decision_count
    )
    advisory_signal_count = pending_eigenquestion_count
    diagnostic_signal_count = blitz_survival_report_count
    escape_signal_count = active_control_signal_count
    mechanism_status_counts = {
        "active": active_control_signal_count,
        "advisory": advisory_signal_count,
        "diagnostic": diagnostic_signal_count,
    }
    control_events = _active_control_events(
        iter_rows=iter_rows,
        loop_events=loop_events,
        blitz_rows=blitz_rows,
        primitive_rows=primitive_rows,
    )
    control_outcomes = _active_control_outcomes(
        iter_rows=iter_rows,
        control_events=control_events,
    )
    episode_outcomes = _active_control_episode_outcomes(
        control_events=control_events,
        event_outcomes=control_outcomes,
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
        control_followup_decision_count=control_followup_decision_count,
        control_followup_block_count=control_followup_block_count,
        control_followup_allow_count=control_followup_allow_count,
        active_control_event_count=control_outcomes["active_control_event_count"],
        control_episode_count=episode_outcomes["control_episode_count"],
        post_control_window_count=control_outcomes["post_control_window_count"],
        post_control_episode_window_count=episode_outcomes[
            "post_control_episode_window_count"
        ],
        post_control_no_followup_count=control_outcomes["post_control_no_followup_count"],
        post_control_episode_no_followup_count=episode_outcomes[
            "post_control_episode_no_followup_count"
        ],
        post_control_observed_no_success_count=control_outcomes[
            "post_control_observed_no_success_count"
        ],
        post_control_episode_observed_no_success_count=episode_outcomes[
            "post_control_episode_observed_no_success_count"
        ],
        post_control_success_count=control_outcomes["post_control_success_count"],
        post_control_episode_success_count=episode_outcomes[
            "post_control_episode_success_count"
        ],
        post_control_improvement_count=control_outcomes["post_control_improvement_count"],
        post_control_episode_improvement_count=episode_outcomes[
            "post_control_episode_improvement_count"
        ],
        post_control_champion_count=control_outcomes["post_control_champion_count"],
        post_control_episode_champion_count=episode_outcomes[
            "post_control_episode_champion_count"
        ],
        post_control_stagnation_drop_count=control_outcomes["post_control_stagnation_drop_count"],
        post_control_episode_stagnation_drop_count=episode_outcomes[
            "post_control_episode_stagnation_drop_count"
        ],
        post_control_success_rate=control_outcomes["post_control_success_rate"],
        post_control_episode_success_rate=episode_outcomes[
            "post_control_episode_success_rate"
        ],
        post_control_diagnostics=tuple(control_outcomes["post_control_diagnostics"]),
        post_control_episode_diagnostics=tuple(
            episode_outcomes["post_control_episode_diagnostics"]
        ),
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
        "post_control_observed_no_success_count": 0,
        "post_control_success_count": 0,
        "post_control_improvement_count": 0,
        "post_control_champion_count": 0,
        "post_control_stagnation_drop_count": 0,
        "post_control_success_rate": None,
    }
    post_control_episode_totals = {
        "control_episode_count": 0,
        "post_control_episode_window_count": 0,
        "post_control_episode_no_followup_count": 0,
        "post_control_episode_observed_no_success_count": 0,
        "post_control_episode_success_count": 0,
        "post_control_episode_improvement_count": 0,
        "post_control_episode_champion_count": 0,
        "post_control_episode_stagnation_drop_count": 0,
        "post_control_episode_success_rate": None,
    }
    control_followup_policy_totals = {
        "control_followup_decision_count": 0,
        "control_followup_block_count": 0,
        "control_followup_allow_count": 0,
    }
    post_control_diagnostic_counts: dict[str, int] = {}
    post_control_diagnostic_samples: list[dict[str, Any]] = []
    control_episode_recovery_counts: dict[str, int] = {}
    control_episode_recovery_unresolved_counts: dict[str, int] = {}
    control_episode_recovery_resolution_counts: dict[str, int] = {}
    control_episode_recovery_intake_counts: dict[str, int] = {}
    control_episode_recovery_admission_packet_counts: dict[str, int] = {}
    control_episode_recovery_candidates: list[dict[str, Any]] = []
    recovery_trace_cache: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
        mechanism_status_totals["active"] += row.active_control_signal_count
        mechanism_status_totals["advisory"] += row.advisory_signal_count
        mechanism_status_totals["diagnostic"] += row.diagnostic_signal_count
        for key in (
            "active_control_event_count",
            "post_control_window_count",
            "post_control_no_followup_count",
            "post_control_observed_no_success_count",
            "post_control_success_count",
            "post_control_improvement_count",
            "post_control_champion_count",
            "post_control_stagnation_drop_count",
        ):
            post_control_outcome_totals[key] += getattr(row, key)
        for key in (
            "control_episode_count",
            "post_control_episode_window_count",
            "post_control_episode_no_followup_count",
            "post_control_episode_observed_no_success_count",
            "post_control_episode_success_count",
            "post_control_episode_improvement_count",
            "post_control_episode_champion_count",
            "post_control_episode_stagnation_drop_count",
        ):
            post_control_episode_totals[key] += getattr(row, key)
        control_followup_policy_totals["control_followup_decision_count"] += (
            row.control_followup_decision_count
        )
        control_followup_policy_totals["control_followup_block_count"] += (
            row.control_followup_block_count
        )
        control_followup_policy_totals["control_followup_allow_count"] += (
            row.control_followup_allow_count
        )
        for diagnostic in row.post_control_diagnostics:
            outcome_status = str(diagnostic.get("outcome_status") or "unknown")
            post_control_diagnostic_counts[outcome_status] = (
                post_control_diagnostic_counts.get(outcome_status, 0) + 1
            )
            if (
                outcome_status != "control_success"
                and len(post_control_diagnostic_samples) < 12
            ):
                post_control_diagnostic_samples.append(
                    {
                        "workspace": row.workspace,
                        **diagnostic,
                    }
                )
        recovery_resolutions = _recovery_resolution_index(row.workspace, repo)
        for diagnostic in row.post_control_episode_diagnostics:
            candidate = _control_episode_recovery_candidate(
                row,
                diagnostic,
                repo=repo,
                trace_cache=recovery_trace_cache,
            )
            if candidate is None:
                continue
            candidate = _apply_recovery_resolution(
                candidate,
                recovery_resolutions.get(_recovery_episode_key(candidate)),
            )
            status = str(candidate.get("outcome_status") or "unknown")
            control_episode_recovery_counts[status] = (
                control_episode_recovery_counts.get(status, 0) + 1
            )
            intake_status = _canonical_intake_status(
                str(candidate.get("intake_status") or "unknown")
            )
            control_episode_recovery_intake_counts[intake_status] = (
                control_episode_recovery_intake_counts.get(intake_status, 0)
                + 1
            )
            legacy_intake_status = _legacy_admission_packet_status(intake_status)
            control_episode_recovery_admission_packet_counts[legacy_intake_status] = (
                control_episode_recovery_admission_packet_counts.get(legacy_intake_status, 0)
                + 1
            )
            resolution_status = str(candidate.get("resolution_status") or "")
            if resolution_status:
                control_episode_recovery_resolution_counts[resolution_status] = (
                    control_episode_recovery_resolution_counts.get(resolution_status, 0)
                    + 1
                )
            if candidate.get("resolution_closes_queue_item") is True:
                continue
            control_episode_recovery_unresolved_counts[status] = (
                control_episode_recovery_unresolved_counts.get(status, 0) + 1
            )
            control_episode_recovery_candidates.append(candidate)
    control_episode_recovery_candidates.sort(
        key=lambda item: (
            int(item.get("priority") or 0),
            bool(item.get("fixture_like_project")),
            item.get("intake_status") != "ready",
            item.get("intake_status")
            != "compiled_evidence_without_project_intake",
            str(item.get("workspace") or ""),
            int(item.get("iteration") or 0),
        )
    )
    windows = post_control_outcome_totals["post_control_window_count"]
    if windows:
        post_control_outcome_totals["post_control_success_rate"] = (
            post_control_outcome_totals["post_control_success_count"] / windows
        )
    episode_windows = post_control_episode_totals["post_control_episode_window_count"]
    if episode_windows:
        post_control_episode_totals["post_control_episode_success_rate"] = (
            post_control_episode_totals["post_control_episode_success_count"] / episode_windows
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
        "post_control_episode_totals": post_control_episode_totals,
        "control_followup_policy_totals": control_followup_policy_totals,
        "post_control_diagnostic_counts": dict(
            sorted(post_control_diagnostic_counts.items())
        ),
        "post_control_diagnostic_samples": post_control_diagnostic_samples,
        "control_episode_recovery_counts": dict(
            sorted(control_episode_recovery_counts.items())
        ),
        "control_episode_recovery_unresolved_counts": dict(
            sorted(control_episode_recovery_unresolved_counts.items())
        ),
        "control_episode_recovery_resolution_counts": dict(
            sorted(control_episode_recovery_resolution_counts.items())
        ),
        "control_episode_recovery_intake_counts": dict(
            sorted(control_episode_recovery_intake_counts.items())
        ),
        "control_episode_recovery_admission_packet_counts": dict(
            sorted(control_episode_recovery_admission_packet_counts.items())
        ),
        "control_episode_recovery_queue": control_episode_recovery_candidates,
        "rows": [asdict(row) for row in shown],
    }


def build_control_episode_recovery_report(
    report: dict[str, Any],
    *,
    limit: int | None = None,
    intake_status: str | None = None,
    packet_status: str | None = None,
) -> dict[str, Any]:
    if intake_status is None:
        intake_status = packet_status
    intake_status = _canonical_intake_status(intake_status)
    queue = list(report.get("control_episode_recovery_queue") or [])
    if intake_status:
        queue = [
            item for item in queue
            if _canonical_intake_status(
                str(item.get("intake_status") or item.get("admission_packet_status") or "")
            )
            == intake_status
        ]
    shown = queue[:limit] if limit and limit > 0 else queue
    return {
        "schema": "ztare-hill-climb-control-recovery-v1",
        "project": report.get("project"),
        "stagnation_threshold": report.get("stagnation_threshold"),
        "intake_status_filter": intake_status,
        "packet_status_filter": intake_status,
        "legacy_packet_status_filter": intake_status,
        "workspace_count": report.get("workspace_count", 0),
        "stagnant_workspace_count": report.get("stagnant_workspace_count", 0),
        "control_episode_recovery_counts": dict(
            report.get("control_episode_recovery_counts") or {}
        ),
        "control_episode_recovery_unresolved_counts": dict(
            report.get("control_episode_recovery_unresolved_counts") or {}
        ),
        "control_episode_recovery_resolution_counts": dict(
            report.get("control_episode_recovery_resolution_counts") or {}
        ),
        "control_episode_recovery_intake_counts": dict(
            report.get("control_episode_recovery_intake_counts") or {}
        ),
        "control_episode_recovery_admission_packet_counts": dict(
            report.get("control_episode_recovery_admission_packet_counts") or {}
        ),
        "post_control_episode_totals": dict(
            report.get("post_control_episode_totals") or {}
        ),
        "queue_count": len(queue),
        "queue_limit": limit if limit and limit > 0 else None,
        "queue": shown,
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        "Autoresearch hill-climb behavior audit",
        f"workspaces={report['workspace_count']} stagnant_workspaces={report['stagnant_workspace_count']} threshold={report['stagnation_threshold']}",
        "status_counts=" + json.dumps(report["status_counts"], sort_keys=True),
        "mechanism_status_totals=" + json.dumps(report.get("mechanism_status_totals", {}), sort_keys=True),
        "post_control_outcomes=" + json.dumps(report.get("post_control_outcome_totals", {}), sort_keys=True),
        "post_control_episodes=" + json.dumps(report.get("post_control_episode_totals", {}), sort_keys=True),
        "post_control_diagnostics=" + json.dumps(report.get("post_control_diagnostic_counts", {}), sort_keys=True),
        "control_episode_recovery_counts=" + json.dumps(report.get("control_episode_recovery_counts", {}), sort_keys=True),
        "control_episode_recovery_unresolved_counts=" + json.dumps(report.get("control_episode_recovery_unresolved_counts", {}), sort_keys=True),
        "control_episode_recovery_resolution_counts=" + json.dumps(report.get("control_episode_recovery_resolution_counts", {}), sort_keys=True),
        "control_episode_recovery_intake_counts=" + json.dumps(report.get("control_episode_recovery_intake_counts", {}), sort_keys=True),
        "control_episode_recovery_legacy_admission_packet_counts=" + json.dumps(report.get("control_episode_recovery_admission_packet_counts", {}), sort_keys=True),
        "control_followup_policy=" + json.dumps(report.get("control_followup_policy_totals", {}), sort_keys=True),
    ]
    for row in report["rows"][:40]:
        lines.append(
            "- {status} {workspace}: iters={iteration_count} max_stag={max_stagnation_count} threshold={effective_pivot_threshold} "
            "pivot_events={pivot_event_count} pivot_actions={pivot_action_count} "
            "blitz={blitz_iteration_count} primitive_classes={primitive_class_count} "
            "active={active_control_signal_count} advisory={advisory_signal_count} diagnostic={diagnostic_signal_count} "
            "followup_policy={control_followup_block_count}/{control_followup_decision_count} "
            "post_control_success={post_control_success_count}/{post_control_window_count} "
            "post_control_episode_success={post_control_episode_success_count}/{post_control_episode_window_count} "
            "post_control_observed_no_success={post_control_observed_no_success_count}/{post_control_window_count} "
            "pending_refresh={pending_refresh_count} "
            "latest_yield={latest_information_yield_rationale}".format(
                **row
            )
        )
    if len(report["rows"]) > 40:
        lines.append(f"... {len(report['rows']) - 40} additional rows omitted")
    return "\n".join(lines)


def render_recovery_text(report: dict[str, Any]) -> str:
    lines = [
        "Autoresearch loop-control recovery queue",
        f"workspaces={report['workspace_count']} stagnant_workspaces={report['stagnant_workspace_count']} threshold={report['stagnation_threshold']}",
        f"intake_status_filter={report.get('intake_status_filter') or 'all'}",
        "recovery_counts="
        + json.dumps(report.get("control_episode_recovery_counts", {}), sort_keys=True),
        "unresolved_counts="
        + json.dumps(report.get("control_episode_recovery_unresolved_counts", {}), sort_keys=True),
        "resolution_counts="
        + json.dumps(report.get("control_episode_recovery_resolution_counts", {}), sort_keys=True),
        "intake_counts="
        + json.dumps(report.get("control_episode_recovery_intake_counts", {}), sort_keys=True),
        "legacy_admission_packet_counts="
        + json.dumps(report.get("control_episode_recovery_admission_packet_counts", {}), sort_keys=True),
        "post_control_episodes="
        + json.dumps(report.get("post_control_episode_totals", {}), sort_keys=True),
    ]
    for item in report.get("queue") or []:
        lines.append(
            "- {outcome_status} {workspace}: run={run_id} iter={iteration} "
            "events={event_iterations} mechanisms={mechanisms} action={action} "
            "kernel={kernel_entry_status} blockers={kernel_entry_blockers} "
            "next={next_command}".format(**item)
        )
    if report.get("queue_limit") and report.get("queue_count", 0) > len(report.get("queue") or []):
        omitted = report["queue_count"] - len(report.get("queue") or [])
        lines.append(f"... {omitted} additional recovery rows omitted")
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
    parser.add_argument(
        "--recovery-queue",
        action="store_true",
        help="Emit only the loop-control recovery queue and aggregate episode counts.",
    )
    parser.add_argument(
        "--recovery-limit",
        type=int,
        default=20,
        help="Limit recovery queue rows when --recovery-queue is set; 0 means all.",
    )
    parser.add_argument(
        "--recovery-intake-status",
        "--recovery-packet-status",
        dest="recovery_intake_status",
        choices=[
            "ready",
            "compiled_evidence_without_project_intake",
            "missing_project_intake",
            "compiled_evidence_without_admission_packet",
            "missing_admission_packet",
        ],
        help=(
            "Filter --recovery-queue rows by project-intake status; "
            "this is not kernel-entry readiness."
        ),
    )
    parser.add_argument(
        "--record-resolution",
        action="store_true",
        help="Append a workspace receipt for one reviewed recovery queue row.",
    )
    parser.add_argument("--workspace", help="Workspace path for --record-resolution.")
    parser.add_argument("--run-id", default="", help="Run id for --record-resolution.")
    parser.add_argument("--iteration", type=int, help="First control iteration.")
    parser.add_argument("--last-control-iteration", type=int, help="Last control iteration.")
    parser.add_argument("--outcome-status", help="Queue outcome status being reviewed.")
    parser.add_argument(
        "--resolution-status",
        choices=sorted(RECOVERY_RESOLUTION_STATUSES),
        default="reason_recorded",
        help="Resolution receipt status.",
    )
    parser.add_argument("--reason", help="Why this queue row is resolved or deferred.")
    parser.add_argument("--recorded-by", default="local", help="Stable role label.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    if args.record_resolution:
        missing = [
            name
            for name, value in (
                ("--workspace", args.workspace),
                ("--iteration", args.iteration),
                ("--outcome-status", args.outcome_status),
                ("--reason", args.reason),
            )
            if value in (None, "")
        ]
        if missing:
            parser.error("--record-resolution requires " + ", ".join(missing))
        try:
            receipt = record_control_episode_recovery_resolution(
                workspace=args.workspace,
                run_id=args.run_id,
                iteration=args.iteration,
                last_control_iteration=args.last_control_iteration,
                outcome_status=args.outcome_status,
                resolution_status=args.resolution_status,
                reason=args.reason,
                recorded_by=args.recorded_by,
            )
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps(receipt, indent=2, sort_keys=True))
        else:
            print(
                "recorded hill-climb recovery resolution: "
                f"{receipt['workspace']} run={receipt['run_id']} "
                f"iter={receipt['iteration']} status={receipt['resolution_status']}"
            )
        return 0

    report = build_hill_climb_behavior_audit(
        project=args.project,
        stagnation_threshold=args.stagnation_threshold,
        limit=args.limit if args.limit > 0 else None,
    )
    if args.recovery_queue:
        report = build_control_episode_recovery_report(
            report,
            limit=args.recovery_limit if args.recovery_limit > 0 else None,
            intake_status=args.recovery_intake_status,
        )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.recovery_queue:
        print(render_recovery_text(report))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
