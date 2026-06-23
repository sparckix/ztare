"""Compare autoresearch outcomes by worker transport.

This is an observational audit over existing run history. It does not launch
models and it does not claim causal lift. Its job is narrower: make it obvious
whether the repo has any actual API-vs-subscription outcome evidence yet.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ztare.validator.hypothesis_projection import ProjectionNode, build_projection


REPO = Path(__file__).resolve().parents[3]
DEFAULT_MATCHED_AGENT_TIMEOUT_SECONDS = 240


@dataclass(frozen=True)
class TransportOutcomeStats:
    transport: str
    node_count: int
    admitted_count: int
    rejected_count: int
    score_count: int
    mean_score: float | None
    best_score: float | None
    admitted_rate: float | None
    held_out_evidence_count: int
    held_out_evidence_rate: float | None
    gate_failure_count: int
    failed_gate_ids: list[str]


@dataclass(frozen=True)
class MatchedRunCandidate:
    project: str
    rubric: str
    rubric_path: str
    matched_run_id: str
    rubric_mode: str
    suitability_score: int
    risk_flags: list[str]
    existing_node_count: int
    existing_transport_counts: dict[str, int]
    matched_pair_command: str
    api_command: str
    subscription_command: str
    audit_command: str
    caution: str


@dataclass(frozen=True)
class MatchedRunGroup:
    matched_run_id: str
    node_count: int
    project_count: int
    transport_counts: dict[str, int]
    role_counts: dict[str, int]
    comparable: bool
    evidence_grade: str
    issue_flags: list[str]
    role_transport_mismatch_count: int
    completed_subscription_receipt_count: int
    gate_failure_count: int
    failed_gate_ids: list[str]


def _project_dirs(repo: Path, project: str | None = None) -> list[Path]:
    projects_root = repo / "projects"
    if project:
        return [projects_root / project]
    if not projects_root.exists():
        return []
    return sorted(path for path in projects_root.iterdir() if path.is_dir())


def _load_nodes(repo: Path, project: str | None) -> tuple[list[ProjectionNode], list[dict[str, str]]]:
    nodes: list[ProjectionNode] = []
    skipped: list[dict[str, str]] = []
    for project_dir in _project_dirs(repo, project):
        try:
            projection = build_projection(project_dir)
        except (FileNotFoundError, ValueError) as exc:
            skipped.append({"project": project_dir.name, "reason": str(exc)})
            continue
        nodes.extend(projection.nodes)
    return nodes, skipped


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    if not materialized:
        return None
    return round(sum(materialized) / len(materialized), 4)


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _stats_for_transport(transport: str, nodes: list[ProjectionNode]) -> TransportOutcomeStats:
    scores = [float(node.score) for node in nodes if node.score is not None]
    admitted = sum(1 for node in nodes if node.status == "merged")
    held_out = sum(1 for node in nodes if node.held_out_evidence_present)
    return TransportOutcomeStats(
        transport=transport,
        node_count=len(nodes),
        admitted_count=admitted,
        rejected_count=sum(1 for node in nodes if node.status != "merged"),
        score_count=len(scores),
        mean_score=_mean(scores),
        best_score=max(scores) if scores else None,
        admitted_rate=_rate(admitted, len(nodes)),
        held_out_evidence_count=held_out,
        held_out_evidence_rate=_rate(held_out, len(nodes)),
        gate_failure_count=sum(int(node.gate_failure_count or 0) for node in nodes),
        failed_gate_ids=sorted(
            {
                str(item)
                for node in nodes
                for item in node.failed_gate_ids
                if str(item).strip()
            }
        ),
    )


def _delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(a - b, 4)


def _shell_value(value: str) -> str:
    if not value:
        return "''"
    safe = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./:-")
    if all(ch in safe for ch in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _rel_to_repo(repo: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo.resolve()))
    except ValueError:
        return str(path)


def _first_existing_intake(repo: Path, project_dir: Path, slug: str) -> str | None:
    candidates = [
        project_dir / "project_packet.json",
        project_dir / f"{slug}_intake.json",
        project_dir / f"{slug}_packet.json",
        repo / f"{slug}_intake.json",
        repo / f"{slug}_packet.json",
        repo / "examples" / "project_packets" / f"{slug}_packet.json",
        repo / "examples" / "project_packets" / f"ready_{slug}_packet.json",
        repo / "examples" / "substrate_packets" / f"{slug}_packet.json",
        repo / "examples" / "substrate_packets" / f"ready_{slug}_packet.json",
    ]
    candidates.extend(sorted(project_dir.glob("*_intake.json")))
    candidates.extend(sorted(project_dir.glob("*_packet.json")))
    for path in candidates:
        if path.exists() and path.is_file():
            return _rel_to_repo(repo, path)
    return None


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_")


def _nodes_for_project(repo: Path, project: str) -> list[ProjectionNode]:
    nodes, _ = _load_nodes(repo, project)
    return nodes


def _next_matched_run_id(slug: str, nodes: list[ProjectionNode]) -> str:
    """Return the next non-colliding pair id visible in current run history."""

    base = f"pair_{_safe_id(slug)}"
    used = {
        str(node.matched_run_id).strip()
        for node in nodes
        if str(node.matched_run_id).strip()
    }
    index = 1
    while f"{base}_{index:03d}" in used:
        index += 1
    return f"{base}_{index:03d}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _transport_counts(nodes: list[ProjectionNode]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        transport = node.transport or "unrecorded"
        counts[transport] = counts.get(transport, 0) + 1
    return dict(sorted(counts.items()))


_HARD_RESEARCH_TERMS = (
    "navier",
    "ns_",
    "pde",
    "proofsearch",
    "theorem",
    "lean",
    "riemann",
    "clay",
)


def _matched_run_risk_flags(
    *,
    repo: Path,
    slug: str,
    project_path: str,
    rubric_path: str,
    rubric: dict[str, Any],
    nodes: list[ProjectionNode],
) -> list[str]:
    flags: list[str] = []
    project_dir = repo / project_path
    if not (project_dir / "test_model.py").exists():
        flags.append("no_project_test_model")
    if (project_dir / "gate_harness.py").exists() or rubric.get("pre_judge_gate_harness"):
        flags.append("gate_harness_surface")
    if rubric.get("holdout_hard_gate"):
        flags.append("holdout_hard_gate")
    blob = " ".join(
        str(part).lower()
        for part in (
            slug,
            rubric_path,
            rubric.get("name"),
            rubric.get("project"),
            rubric.get("description"),
            rubric.get("persona"),
        )
    )
    if any(term in blob for term in _HARD_RESEARCH_TERMS):
        flags.append("hard_research_or_proof_surface")
    if nodes and _transport_counts(nodes) == {"unrecorded": len(nodes)}:
        flags.append("legacy_transport_only")
    return flags


def _matched_run_suitability_score(flags: list[str], *, node_count: int) -> int:
    score = 100
    penalties = {
        "existing_clean_matched_group": 35,
        "holdout_hard_gate": 35,
        "hard_research_or_proof_surface": 30,
        "gate_harness_surface": 20,
        "no_project_test_model": 15,
        "legacy_transport_only": 5,
    }
    for flag in flags:
        score -= penalties.get(flag, 10)
    if 1 <= node_count <= 80:
        score += 8
    if node_count == 0:
        score -= 8
    return max(0, min(100, score))


def _has_clean_matched_run_group(nodes: list[ProjectionNode]) -> bool:
    return any(group.evidence_grade == "clean" for group in _matched_run_groups(nodes))


def _matched_run_plan(
    *,
    repo: Path,
    project: str | None,
    limit: int = 5,
) -> list[MatchedRunCandidate]:
    from ztare.reports.rubric_mode_corpus_audit import audit_rubric_mode_corpus

    rubric_report = audit_rubric_mode_corpus(repo=repo)
    candidates: list[MatchedRunCandidate] = []
    for row in rubric_report.get("rows") or []:
        if row.get("status") != "ok":
            continue
        slug = str(row.get("project_slug") or "")
        if not slug or (project and slug != project):
            continue
        if not row.get("project_path"):
            continue
        project_path = str(row.get("project_path") or "")
        rubric_path = str(row.get("rubric_path") or "")
        rubric_name = Path(rubric_path).stem
        if not rubric_name:
            continue
        nodes = _nodes_for_project(repo, slug)
        counts = _transport_counts(nodes)
        rubric = _read_json(repo / rubric_path)
        risk_flags = _matched_run_risk_flags(
            repo=repo,
            slug=slug,
            project_path=project_path,
            rubric_path=rubric_path,
            rubric=rubric,
            nodes=nodes,
        )
        if _has_clean_matched_run_group(nodes):
            risk_flags.append("existing_clean_matched_group")
        suitability_score = _matched_run_suitability_score(
            risk_flags,
            node_count=len(nodes),
        )
        matched_run_id = _next_matched_run_id(slug, nodes)
        intake = _first_existing_intake(repo, repo / project_path, slug)
        intake_arg = f" INTAKE={_shell_value(intake)}" if intake else ""
        no_fallback_arg = " MODEL_FALLBACK=0"
        api_command = (
            f"make experiment-loop PROJECT={_shell_value(slug)} "
            f"RUBRIC={_shell_value(rubric_name)} ITERS=1"
            f"{intake_arg}{no_fallback_arg} "
            f"MATCHED_RUN_ID={_shell_value(matched_run_id)} MATCHED_RUN_ROLE=api"
        )
        matched_pair_command = (
            f"make autoresearch-matched-transport-pair PROJECT={_shell_value(slug)} "
            f"RUBRIC={_shell_value(rubric_name)} ITERS=1"
            f"{intake_arg}{no_fallback_arg} "
            f"MATCHED_RUN_ID={_shell_value(matched_run_id)} "
            f"AGENT_TIMEOUT={DEFAULT_MATCHED_AGENT_TIMEOUT_SECONDS}"
        )
        subscription_command = (
            f"make experiment-loop PROJECT={_shell_value(slug)} "
            f"RUBRIC={_shell_value(rubric_name)} ITERS=1"
            f"{intake_arg}{no_fallback_arg} "
            f"MATCHED_RUN_ID={_shell_value(matched_run_id)} MATCHED_RUN_ROLE=subscription "
            "AGENT_MUTATOR=1 AGENT_JUDGE=1 AGENT_COMMITTEE=1 "
            "AGENT_INVERTER=1 AGENT_RUNTIME=codex "
            f"AGENT_TIMEOUT={DEFAULT_MATCHED_AGENT_TIMEOUT_SECONDS}"
        )
        audit_command = (
            "make autoresearch-subscription-outcome-audit "
            f"PROJECT={_shell_value(slug)} JSON=1"
        )
        candidates.append(
            MatchedRunCandidate(
                project=slug,
                rubric=rubric_name,
                rubric_path=rubric_path,
                matched_run_id=matched_run_id,
                rubric_mode=str(row.get("mode") or "unknown"),
                suitability_score=suitability_score,
                risk_flags=risk_flags,
                existing_node_count=len(nodes),
                existing_transport_counts=counts,
                matched_pair_command=matched_pair_command,
                api_command=api_command,
                subscription_command=subscription_command,
                audit_command=audit_command,
                caution=(
                    "Run the pair under the same project/rubric/iteration budget and "
                    "do not reuse the matched_run_id for a second transport trial. Treat "
                    "deltas as observational unless the task setup is otherwise matched."
                ),
            )
        )
    candidates.sort(
        key=lambda item: (
            1 if "existing_clean_matched_group" in item.risk_flags else 0,
            -item.suitability_score,
            -item.existing_node_count,
            item.project,
        )
    )
    return candidates[:limit]


def _matched_run_groups(nodes: list[ProjectionNode]) -> list[MatchedRunGroup]:
    grouped: dict[str, list[ProjectionNode]] = {}
    for node in nodes:
        if node.matched_run_id:
            grouped.setdefault(node.matched_run_id, []).append(node)
    groups: list[MatchedRunGroup] = []
    for matched_run_id, members in sorted(grouped.items()):
        transport_counts: dict[str, int] = {}
        role_counts: dict[str, int] = {}
        issue_flags: list[str] = []
        role_transport_mismatch_count = 0
        completed_subscription_receipt_count = 0
        gate_failure_count = 0
        failed_gate_ids: set[str] = set()
        for node in members:
            transport = node.transport or "unrecorded"
            transport_counts[transport] = transport_counts.get(transport, 0) + 1
            role = node.matched_run_role or "unrecorded"
            role_counts[role] = role_counts.get(role, 0) + 1
            if role == "api" and transport != "api":
                role_transport_mismatch_count += 1
            if role == "subscription" and transport != "subscription_cli":
                role_transport_mismatch_count += 1
            completed_subscription_receipt_count += sum(
                1
                for receipt in node.worker_dispatch_receipts
                if receipt.get("completed") is True
                and str(receipt.get("transport") or "").strip() == "subscription_cli"
            )
            gate_failure_count += int(node.gate_failure_count or 0)
            failed_gate_ids.update(str(item) for item in node.failed_gate_ids if str(item).strip())
        comparable = bool(
            transport_counts.get("api")
            and transport_counts.get("subscription_cli")
        ) or bool(role_counts.get("api") and role_counts.get("subscription"))
        if len({node.project for node in members}) != 1:
            issue_flags.append("multiple_projects")
        if "unrecorded" in transport_counts:
            issue_flags.append("unrecorded_transport")
        if "unrecorded" in role_counts:
            issue_flags.append("unrecorded_role")
        if role_transport_mismatch_count:
            issue_flags.append("role_transport_mismatch")
        if role_counts.get("api", 0) == 0:
            issue_flags.append("missing_api_role")
        if role_counts.get("subscription", 0) == 0:
            issue_flags.append("missing_subscription_role")
        if transport_counts.get("api", 0) == 0:
            issue_flags.append("missing_api_transport")
        if transport_counts.get("subscription_cli", 0) == 0:
            issue_flags.append("missing_subscription_transport")
        if role_counts.get("subscription", 0) and completed_subscription_receipt_count == 0:
            issue_flags.append("missing_completed_subscription_receipt")
        if not comparable:
            evidence_grade = "not_comparable"
        elif issue_flags:
            evidence_grade = "weak"
        else:
            evidence_grade = "clean"
        groups.append(
            MatchedRunGroup(
                matched_run_id=matched_run_id,
                node_count=len(members),
                project_count=len({node.project for node in members}),
                transport_counts=dict(sorted(transport_counts.items())),
                role_counts=dict(sorted(role_counts.items())),
                comparable=comparable,
                evidence_grade=evidence_grade,
                issue_flags=issue_flags,
                role_transport_mismatch_count=role_transport_mismatch_count,
                completed_subscription_receipt_count=completed_subscription_receipt_count,
                gate_failure_count=gate_failure_count,
                failed_gate_ids=sorted(failed_gate_ids),
            )
        )
    return groups


def audit_subscription_outcomes(
    *,
    repo: Path = REPO,
    project: str | None = None,
    min_rows: int = 1,
    plan_limit: int = 5,
) -> dict[str, Any]:
    """Return an observational transport-outcome comparison report."""

    repo = repo.resolve()
    nodes, skipped = _load_nodes(repo, project)
    by_transport: dict[str, list[ProjectionNode]] = {}
    for node in nodes:
        transport = node.transport or "unrecorded"
        by_transport.setdefault(transport, []).append(node)

    stats = {
        transport: asdict(_stats_for_transport(transport, transport_nodes))
        for transport, transport_nodes in sorted(by_transport.items())
    }
    api = stats.get("api")
    subscription = stats.get("subscription_cli")
    api_count = int((api or {}).get("node_count") or 0)
    subscription_count = int((subscription or {}).get("node_count") or 0)
    worker_dispatch_receipt_count = sum(len(node.worker_dispatch_receipts) for node in nodes)
    completed_subscription_receipt_count = sum(
        1
        for node in nodes
        for receipt in node.worker_dispatch_receipts
        if receipt.get("completed") is True
        and str(receipt.get("transport") or "").strip() == "subscription_cli"
    )

    if not nodes:
        status = "no_run_history"
        action = "run autoresearch or point PROJECT at a run with workspace/eval_history.jsonl"
    elif api_count == 0 and subscription_count == 0:
        status = "transport_metadata_missing"
        action = (
            "run fresh API and subscription-backed rows with worker metadata; "
            "legacy unrecorded rows cannot prove transport outcomes"
        )
    elif subscription_count < min_rows:
        status = "insufficient_subscription_evidence"
        action = "run a bounded subscription-backed autoresearch surface, then rerun this audit"
    elif api_count < min_rows:
        status = "insufficient_api_baseline"
        action = "compare against an API-backed baseline run before making transport claims"
    else:
        status = "comparable"
        action = "inspect deltas; treat them as observational until runs are matched"

    comparison: dict[str, Any] | None = None
    if api and subscription:
        comparison = {
            "api_transport": "api",
            "subscription_transport": "subscription_cli",
            "subscription_minus_api_mean_score": _delta(
                subscription.get("mean_score"), api.get("mean_score")
            ),
            "subscription_minus_api_best_score": _delta(
                subscription.get("best_score"), api.get("best_score")
            ),
            "subscription_minus_api_admitted_rate": _delta(
                subscription.get("admitted_rate"), api.get("admitted_rate")
            ),
            "subscription_minus_api_held_out_evidence_rate": _delta(
                subscription.get("held_out_evidence_rate"),
                api.get("held_out_evidence_rate"),
            ),
            "caveat": (
                "Observational run-history comparison only; use matched project, rubric, "
                "iteration budget, and seed/context before treating deltas as transport lift."
            ),
        }
    matched_run_plan = [asdict(row) for row in _matched_run_plan(
        repo=repo,
        project=project,
        limit=plan_limit,
    )]
    matched_run_groups = [asdict(row) for row in _matched_run_groups(nodes)]

    return {
        "schema": "ztare-autoresearch-subscription-outcome-audit-v1",
        "status": status,
        "ok": status == "comparable",
        "scope": {
            "repo": str(repo),
            "project": project,
            "min_rows": min_rows,
        },
        "summary": {
            "project_count": len({node.project for node in nodes}),
            "node_count": len(nodes),
            "skipped_project_count": len(skipped),
            "transport_counts": {
                transport: len(transport_nodes)
                for transport, transport_nodes in sorted(by_transport.items())
            },
            "api_rows": api_count,
            "subscription_rows": subscription_count,
            "comparison_present": comparison is not None,
            "matched_run_group_count": len(matched_run_groups),
            "comparable_matched_run_group_count": sum(
                1 for group in matched_run_groups if group.get("comparable")
            ),
            "clean_matched_run_group_count": sum(
                1 for group in matched_run_groups if group.get("evidence_grade") == "clean"
            ),
            "weak_matched_run_group_count": sum(
                1 for group in matched_run_groups if group.get("evidence_grade") == "weak"
            ),
            "matched_run_plan_count": len(matched_run_plan),
            "worker_dispatch_receipt_count": worker_dispatch_receipt_count,
            "completed_subscription_receipt_count": completed_subscription_receipt_count,
        },
        "by_transport": stats,
        "comparison": comparison,
        "matched_run_groups": matched_run_groups,
        "matched_run_plan": matched_run_plan,
        "skipped_projects": skipped[:50],
        "action": action,
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "Autoresearch subscription outcome audit",
        "model_calls=none",
        f"status={report['status']} ok={report['ok']}",
        "summary=" + json.dumps(summary, sort_keys=True),
        f"action={report['action']}",
    ]
    comparison = report.get("comparison")
    if comparison:
        lines.append("comparison=" + json.dumps(comparison, sort_keys=True))
    for group in report.get("matched_run_groups") or []:
        lines.append("matched_run_group=" + json.dumps(group, sort_keys=True))
    for idx, candidate in enumerate(report.get("matched_run_plan") or [], start=1):
        lines.append(
            "- matched_run_candidate[{idx}]: project={project} rubric={rubric} "
            "mode={mode} suitability={suitability} risks={risks}; "
            "matched_run_id={matched}".format(
                idx=idx,
                project=candidate.get("project"),
                rubric=candidate.get("rubric"),
                mode=candidate.get("rubric_mode"),
                suitability=candidate.get("suitability_score"),
                risks=",".join(candidate.get("risk_flags") or []) or "none",
                matched=candidate.get("matched_run_id"),
            )
        )
        lines.append(f"  matched-pair: {candidate.get('matched_pair_command')}")
        lines.append(f"  api: {candidate.get('api_command')}")
        lines.append(f"  subscription: {candidate.get('subscription_command')}")
        lines.append(f"  audit: {candidate.get('audit_command')}")
        lines.append(f"  caution: {candidate.get('caution')}")
    by_transport = report.get("by_transport") or {}
    for transport, stats in by_transport.items():
        lines.append(f"- {transport}: " + json.dumps(stats, sort_keys=True))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=None)
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--plan-limit", type=int, default=5)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = audit_subscription_outcomes(
        repo=REPO,
        project=args.project,
        min_rows=args.min_rows,
        plan_limit=args.plan_limit,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 1 if args.strict and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
