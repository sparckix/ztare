"""Read-only hypothesis projection over autoresearch run histories.

The autoresearch loop remains canonical. This module turns existing
``workspace/eval_history.jsonl`` records into a branch/accounting view that is
explicit about admitted score improvements, rejected attempts, branch cues,
and available admission evidence without granting the projection any authority
to mutate a run.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ztare.common.paths import PROJECTS_DIR


HELD_OUT_KEYS = ("heldout", "held_out", "holdout", "admission")
ACTION_IMPACT_REL = Path("analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl")


@dataclass(frozen=True)
class ProjectionNode:
    node_id: str
    parent_id: str | None
    project: str
    iteration: int | None
    ordinal: int
    status: str
    score: float | None
    timestamp: str
    hypothesis: str
    failure_signature: str
    weakest_point: str
    branch_cue: str | None
    worker_archetype: str
    worker_capability: str
    worker_state: str
    worker_identity: str
    transport: str
    worker_dispatch_receipts: list[dict[str, Any]]
    matched_run_id: str | None
    matched_run_role: str | None
    artifact_refs: list[str]
    gate_verdicts: dict[str, Any]
    gate_failure_count: int
    failed_gate_ids: list[str]
    held_out_evidence_present: bool
    action_intelligence_refs: list[dict[str, Any]]


@dataclass(frozen=True)
class ProjectionSummary:
    project: str
    node_count: int
    admitted_count: int
    rejected_count: int
    initial_score: float | None
    best_score: float | None
    score_gain: float | None
    branch_cue_count: int
    unique_branch_cue_count: int
    repeated_branch_cue_count: int
    repeated_failure_signature_count: int
    held_out_admission_evidence_count: int
    action_intelligence_link_count: int
    negative_constraint_count: int
    open_frontier_constraint_count: int


@dataclass(frozen=True)
class NegativeConstraint:
    failure_signature: str
    count: int
    node_ids: list[str]
    branch_cues: list[str]
    example_weakest_point: str


@dataclass(frozen=True)
class HypothesisProjection:
    schema_version: int
    projection_kind: str
    source_note: str
    summary: ProjectionSummary
    latest_eval_overlay: dict[str, Any]
    nodes: list[ProjectionNode]
    negative_constraints: list[NegativeConstraint]
    open_frontier_constraints: list[NegativeConstraint]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def build_projection(project_dir: Path) -> HypothesisProjection:
    project_dir = project_dir.resolve()
    project = project_dir.name
    try:
        rows = _read_eval_rows(project_dir)
    except FileNotFoundError:
        if not _latest_eval_path(project_dir):
            raise
        rows = []
    telemetry_rows = _read_iteration_telemetry_rows(project_dir / "workspace" / "iteration_telemetry.jsonl")
    branch_cues = _read_branch_cues(project_dir / "workspace" / "dag_steering_log.jsonl")
    action_rows = _read_action_intelligence_rows(_repo_root_for_project(project_dir))

    nodes: list[ProjectionNode] = []
    best_score: float | None = None
    best_node_id: str | None = None

    for idx, row in enumerate(rows, start=1):
        score = _as_number(row.get("score"))
        admitted = score is not None and (best_score is None or score > best_score)
        node_id = f"n{idx:04d}"
        parent_id = best_node_id
        status = "merged" if admitted else "pruned"
        iteration = _as_int(row.get("iteration"))
        weakest_point = str(row.get("weakest_point") or "")
        hypothesis = _hypothesis_label(row, iteration, idx)
        branch_cue = branch_cues[idx - 1] if idx - 1 < len(branch_cues) else None
        telemetry_row = _match_telemetry_row(row, telemetry_rows)
        gate_failure_count = _gate_failure_count(row, telemetry_row)
        failed_gate_ids = _failed_gate_ids(row, telemetry_row)
        artifact_refs = _artifact_refs(project_dir, iteration, score, row)
        node = ProjectionNode(
            node_id=node_id,
            parent_id=parent_id,
            project=project,
            iteration=iteration,
            ordinal=idx,
            status=status,
            score=score,
            timestamp=str(row.get("timestamp") or row.get("timestamp_utc") or ""),
            hypothesis=hypothesis,
            failure_signature=_failure_signature(weakest_point),
            weakest_point=weakest_point,
            branch_cue=branch_cue,
            worker_archetype=_worker_archetype(row),
            worker_capability=_worker_field(row, "worker_capability"),
            worker_state=_worker_field(row, "worker_state"),
            worker_identity=_worker_field(row, "worker_identity"),
            transport=_transport(row),
            worker_dispatch_receipts=_dispatch_receipts(row),
            matched_run_id=_optional_str(row.get("matched_run_id")),
            matched_run_role=_optional_str(row.get("matched_run_role")),
            artifact_refs=artifact_refs,
            gate_verdicts=dict(row.get("gate_verdicts") or {}),
            gate_failure_count=gate_failure_count,
            failed_gate_ids=failed_gate_ids,
            held_out_evidence_present=_has_held_out_evidence(row),
            action_intelligence_refs=_action_intelligence_links(
                project,
                artifact_refs,
                action_rows,
            ),
        )
        nodes.append(node)
        if admitted:
            best_score = score
            best_node_id = node_id

    summary = _summarize(project, nodes)
    return HypothesisProjection(
        schema_version=1,
        projection_kind="ztare_autoresearch_hypothesis_projection_v0",
        source_note=(
            "Read-only projection over existing eval_history/dag_steering or legacy history records; "
            "latest_eval_results is exposed as an overlay when it is not represented in history; "
            "canonical run state and artifact promotion remain owned by the run loop."
        ),
        summary=summary,
        latest_eval_overlay=_latest_eval_overlay(project_dir, rows),
        nodes=nodes,
        negative_constraints=_negative_constraints(nodes),
        open_frontier_constraints=_open_frontier_constraints(nodes),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing eval history: {path}")
    rows: list[dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {path}:{lineno}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"expected object in {path}:{lineno}")
        rows.append(parsed)
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _relative_to_repo(project_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_dir.parent.parent))
    except ValueError:
        return str(path)


def _latest_eval_path(project_dir: Path) -> Path | None:
    for path in (
        project_dir / "latest_eval_results.json",
        project_dir / "workspace" / "latest_eval_results.json",
    ):
        if path.exists():
            return path
    return None


def _latest_eval_overlay(project_dir: Path, history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    path = _latest_eval_path(project_dir)
    if path is None:
        return {
            "available": False,
            "status": "missing",
            "path": None,
            "history_row_count": len(history_rows),
            "matches_history": None,
            "warnings": [],
        }
    latest = _read_json(path)
    if not latest:
        return {
            "available": True,
            "status": "unreadable",
            "path": _relative_to_repo(project_dir, path),
            "history_row_count": len(history_rows),
            "matches_history": False,
            "warnings": ["latest_eval_results is present but not readable as a JSON object"],
        }
    match = _latest_eval_matches_history(latest, history_rows)
    if not history_rows:
        status = "latest_eval_without_eval_history"
        warnings = [
            "latest_eval_results exists but eval_history has no rows; projection nodes are empty"
        ]
    elif match:
        status = "covered_by_eval_history"
        warnings = []
    else:
        status = "latest_eval_not_in_eval_history"
        warnings = [
            "latest_eval_results is not represented by eval_history; treat projection nodes as stale"
        ]
    return {
        "available": True,
        "status": status,
        "path": _relative_to_repo(project_dir, path),
        "history_row_count": len(history_rows),
        "matches_history": bool(match),
        "iteration": _as_int(latest.get("iteration")),
        "score": _as_number(latest.get("score")),
        "timestamp": str(latest.get("timestamp") or latest.get("timestamp_utc") or ""),
        "weakest_point": str(latest.get("weakest_point") or ""),
        "gate_failure_count": _gate_failure_count(latest, {}),
        "failed_gate_ids": _failed_gate_ids(latest, {}),
        "warnings": warnings,
    }


def _latest_eval_matches_history(
    latest: dict[str, Any],
    history_rows: list[dict[str, Any]],
) -> bool:
    latest_iteration = _as_int(latest.get("iteration"))
    latest_score = _as_number(latest.get("score"))
    latest_weakest = str(latest.get("weakest_point") or "")
    latest_timestamp = str(latest.get("timestamp") or latest.get("timestamp_utc") or "")
    for row in history_rows:
        iteration_matches = (
            latest_iteration is not None
            and _as_int(row.get("iteration")) == latest_iteration
        )
        score_matches = (
            latest_score is not None
            and _as_number(row.get("score")) == latest_score
        )
        weakest_matches = (
            bool(latest_weakest)
            and str(row.get("weakest_point") or "") == latest_weakest
        )
        weakest_prefix_matches = _text_prefix_matches(
            latest_weakest,
            str(row.get("weakest_point") or ""),
        )
        timestamp_matches = (
            bool(latest_timestamp)
            and str(row.get("timestamp") or row.get("timestamp_utc") or "") == latest_timestamp
        )
        if iteration_matches and (
            score_matches
            or weakest_matches
            or weakest_prefix_matches
            or timestamp_matches
        ):
            return True
        if score_matches and (weakest_matches or weakest_prefix_matches):
            return True
    return False


def _text_prefix_matches(left: str, right: str, *, min_chars: int = 80) -> bool:
    left_clean = " ".join(str(left or "").split())
    right_clean = " ".join(str(right or "").split())
    if len(left_clean) < min_chars or len(right_clean) < min_chars:
        return False
    return left_clean.startswith(right_clean) or right_clean.startswith(left_clean)


def _read_eval_rows(project_dir: Path) -> list[dict[str, Any]]:
    eval_path = project_dir / "workspace" / "eval_history.jsonl"
    if eval_path.exists():
        return _read_jsonl(eval_path)
    rows = _read_history_meta_rows(project_dir)
    if rows:
        return rows
    raise FileNotFoundError(f"missing eval history: {eval_path}")


def _read_history_meta_rows(project_dir: Path) -> list[dict[str, Any]]:
    """Fallback for legacy runs that predate ``workspace/eval_history.jsonl``."""

    history_dir = project_dir / "history"
    if not history_dir.exists():
        return []
    project = project_dir.name
    rows: list[dict[str, Any]] = []
    for path in sorted(history_dir.glob("*_meta.json")):
        obj = _read_json(path)
        if not obj:
            continue
        rubric = str(obj.get("rubric") or "")
        if rubric and rubric != project:
            continue
        if not rubric and project not in path.name:
            continue
        obj.setdefault("artifact_refs", _history_artifact_ref(project_dir, path))
        rows.append(obj)
    return sorted(
        rows,
        key=lambda row: (
            _as_number(row.get("run_id")) or 0,
            _as_int(row.get("iteration")) if _as_int(row.get("iteration")) is not None else -1,
            str(row.get("timestamp") or row.get("timestamp_utc") or ""),
        ),
    )


def _history_artifact_ref(project_dir: Path, meta_path: Path) -> list[str]:
    md_path = meta_path.with_name(meta_path.name.removesuffix("_meta.json") + ".md")
    if md_path.exists():
        try:
            return [str(md_path.relative_to(project_dir.parent.parent))]
        except ValueError:
            return [str(md_path)]
    return []


def _read_branch_cues(path: Path) -> list[str | None]:
    if not path.exists():
        return []
    cues: list[str | None] = []
    for row in _read_jsonl(path):
        value = row.get("selected_node_id")
        cues.append(str(value) if value is not None else None)
    return cues


def _read_iteration_telemetry_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        rows = _read_jsonl(path)
    except (FileNotFoundError, ValueError):
        return []
    return [row for row in rows if row.get("record_type") == "iteration"]


def _repo_root_for_project(project_dir: Path) -> Path:
    parts = project_dir.resolve().parts
    for idx, part in enumerate(parts):
        if part == "projects":
            if idx == 0:
                return Path("/")
            return Path(*parts[:idx])
    return project_dir.parent.parent


def _read_action_intelligence_rows(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / ACTION_IMPACT_REL
    if not path.exists():
        return []
    try:
        return _read_jsonl(path)
    except ValueError:
        return []


def _source_refs_from_action_row(row: dict[str, Any]) -> list[str]:
    refs = (row.get("source_refs") or {}).get("source_refs")
    if not isinstance(refs, list):
        return []
    return [str(ref) for ref in refs if str(ref).strip()]


def _action_intelligence_links(
    project: str,
    artifact_refs: list[str],
    action_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifact_ref_set = set(artifact_refs)
    links: list[dict[str, Any]] = []
    for row in action_rows:
        decision = row.get("decision_point") or {}
        context = row.get("context_features") or {}
        source_refs = _source_refs_from_action_row(row)
        ref_matches = sorted(artifact_ref_set.intersection(source_refs))
        project_match = (
            str(decision.get("project_id") or "") == project
            or str(context.get("project_family") or "") == project
        )
        if not ref_matches and not project_match:
            continue
        links.append({
            "action_impact_id": row.get("action_impact_id"),
            "decision_id": decision.get("decision_id"),
            "selected_action": row.get("selected_action"),
            "workbench_router_decision": context.get("workbench_router_decision"),
            "match_kind": "artifact_ref" if ref_matches else "project",
            "matched_refs": ref_matches,
        })
    return links[:5]


def _match_telemetry_row(row: dict[str, Any], telemetry_rows: list[dict[str, Any]]) -> dict[str, Any]:
    iteration = _as_int(row.get("iteration"))
    if iteration is None:
        return {}
    row_dt = _parse_row_timestamp(row.get("timestamp") or row.get("timestamp_utc"))
    row_run_id = _optional_str(row.get("run_id"))
    candidates = [
        item
        for item in telemetry_rows
        if _as_int(item.get("iteration_index")) == iteration
        and (not row_run_id or _optional_str(item.get("run_id")) == row_run_id)
    ]
    if not candidates:
        return {}
    if row_dt:
        ranked: list[tuple[float, dict[str, Any]]] = []
        for item in candidates:
            item_dt = _parse_row_timestamp(item.get("iteration_end_utc") or item.get("timestamp_utc"))
            if item_dt is None:
                continue
            ranked.append((abs((item_dt - row_dt).total_seconds()), item))
        if ranked:
            seconds, item = min(ranked, key=lambda pair: pair[0])
            if seconds <= 600:
                return item
    return candidates[-1]


def _parse_row_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("America/New_York"))
    return parsed.astimezone(timezone.utc)


def _gate_failure_count(row: dict[str, Any], telemetry_row: dict[str, Any]) -> int:
    for source in (row, telemetry_row):
        value = source.get("gate_failure_count")
        parsed = _as_int(value)
        if parsed is not None:
            return max(0, parsed)
    failed = _failed_gate_ids(row, telemetry_row)
    return len(failed)


def _failed_gate_ids(row: dict[str, Any], telemetry_row: dict[str, Any]) -> list[str]:
    for source in (row, telemetry_row):
        value = source.get("failed_gate_ids")
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
    return []


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _hypothesis_label(row: dict[str, Any], iteration: int | None, ordinal: int) -> str:
    for key in ("hypothesis", "parametric_form", "claim_delta_type"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if iteration is not None:
        return f"autoresearch iteration {iteration}"
    return f"autoresearch row {ordinal}"


def _failure_signature(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return " ".join(words[:12])


def _artifact_refs(
    project_dir: Path,
    iteration: int | None,
    score: float | None,
    row: dict[str, Any],
) -> list[str]:
    existing = row.get("artifact_refs")
    if isinstance(existing, list):
        refs = [str(item) for item in existing if str(item).strip()]
        if refs:
            return refs
    if iteration is None or score is None:
        return []
    history_dir = project_dir / "history"
    if not history_dir.exists():
        return []
    score_token = str(int(score)) if score.is_integer() else str(score).replace(".", "_")
    pattern = f"*_iter{iteration}_score_{score_token}_{project_dir.name}.md"
    return [
        str(path.relative_to(project_dir.parent.parent))
        for path in sorted(history_dir.glob(pattern))[:5]
    ]


def _has_held_out_evidence(row: dict[str, Any]) -> bool:
    for key, value in row.items():
        lower = key.lower()
        if any(token in lower for token in HELD_OUT_KEYS) and value not in (None, "", [], {}):
            return True
    return False


def _worker_archetype(row: dict[str, Any]) -> str:
    value = row.get("worker_archetype") or row.get("worker_role_archetype")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unrecorded"


def _transport(row: dict[str, Any]) -> str:
    receipts = _dispatch_receipts(row)
    if receipts:
        values = sorted(
            str(item.get("transport") or "").strip()
            for item in receipts
            if item.get("completed") is True and str(item.get("transport") or "").strip()
        )
        if "subscription_cli" in values:
            return "subscription_cli"
        if values:
            return values[0]
    value = row.get("transport") or row.get("worker_transport")
    if isinstance(value, str) and value.strip():
        return value.strip()
    transport_set = row.get("worker_transport_set")
    if isinstance(transport_set, list):
        values = sorted(str(item).strip() for item in transport_set if str(item).strip())
        if "subscription_cli" in values:
            return "subscription_cli"
        if values:
            return values[0]
    by_call_site = row.get("worker_metadata_by_call_site")
    if isinstance(by_call_site, dict):
        values = sorted(
            str((meta or {}).get("transport") or "").strip()
            for meta in by_call_site.values()
            if isinstance(meta, dict) and str((meta or {}).get("transport") or "").strip()
        )
        if "subscription_cli" in values:
            return "subscription_cli"
        if values:
            return values[0]
    return "unrecorded"


def _dispatch_receipts(row: dict[str, Any]) -> list[dict[str, Any]]:
    receipts = row.get("worker_dispatch_receipts")
    if not isinstance(receipts, list):
        return []
    return [dict(item) for item in receipts if isinstance(item, dict)]


def _worker_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unrecorded"


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _summarize(project: str, nodes: list[ProjectionNode]) -> ProjectionSummary:
    admitted_count = sum(1 for node in nodes if node.status == "merged")
    branch_cues = [node.branch_cue for node in nodes if node.branch_cue]
    repeated_branch_cues = len(branch_cues) - len(set(branch_cues))
    failure_signatures = [
        node.failure_signature for node in nodes if node.failure_signature and node.status != "merged"
    ]
    repeated_failures = len(failure_signatures) - len(set(failure_signatures))
    scores = [node.score for node in nodes if node.score is not None]
    initial_score = scores[0] if scores else None
    best_score = max(scores) if scores else None
    score_gain = None
    if initial_score is not None and best_score is not None:
        score_gain = best_score - initial_score
    return ProjectionSummary(
        project=project,
        node_count=len(nodes),
        admitted_count=admitted_count,
        rejected_count=len(nodes) - admitted_count,
        initial_score=initial_score,
        best_score=best_score,
        score_gain=score_gain,
        branch_cue_count=len(branch_cues),
        unique_branch_cue_count=len(set(branch_cues)),
        repeated_branch_cue_count=repeated_branch_cues,
        repeated_failure_signature_count=repeated_failures,
        held_out_admission_evidence_count=sum(
            1 for node in nodes if node.held_out_evidence_present
        ),
        action_intelligence_link_count=sum(
            1 for node in nodes if node.action_intelligence_refs
        ),
        negative_constraint_count=len(_negative_constraints(nodes)),
        open_frontier_constraint_count=len(_open_frontier_constraints(nodes)),
    )


def _negative_constraints(nodes: list[ProjectionNode]) -> list[NegativeConstraint]:
    grouped: dict[str, list[ProjectionNode]] = {}
    for node in nodes:
        if node.status == "merged" or not node.failure_signature:
            continue
        grouped.setdefault(node.failure_signature, []).append(node)
    constraints: list[NegativeConstraint] = []
    for signature, members in sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        cues = sorted({cue for cue in (node.branch_cue for node in members) if cue})
        example = next(
            (node.weakest_point for node in members if node.weakest_point),
            signature,
        )
        constraints.append(
            NegativeConstraint(
                failure_signature=signature,
                count=len(members),
                node_ids=[node.node_id for node in members],
                branch_cues=cues,
                example_weakest_point=example,
            )
        )
    return constraints


def _open_frontier_constraints(nodes: list[ProjectionNode]) -> list[NegativeConstraint]:
    """Open constraint on the current admitted frontier.

    This is not a failed branch. It is the unresolved critique on the latest
    accepted spine, so the next worker should alter the mechanism or evidence
    boundary before polishing around the same weakness.
    """

    admitted = [node for node in nodes if node.status == "merged" and node.failure_signature]
    if not admitted:
        return []
    latest = admitted[-1]
    return [
        NegativeConstraint(
            failure_signature=latest.failure_signature,
            count=1,
            node_ids=[latest.node_id],
            branch_cues=[latest.branch_cue] if latest.branch_cue else [],
            example_weakest_point=latest.weakest_point,
        )
    ]


def _resolve_project(project_arg: str) -> Path:
    path = Path(project_arg)
    if path.exists():
        return path
    return PROJECTS_DIR / project_arg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a read-only hypothesis projection for a ZTARE autoresearch project."
    )
    parser.add_argument("project", help="Project slug or path under projects/")
    parser.add_argument("--out", type=Path, help="Optional JSON output path")
    args = parser.parse_args(argv)

    projection = build_projection(_resolve_project(args.project))
    text = projection.to_json() + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
