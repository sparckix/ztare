"""Read-only consequence audit for autoresearch/RD kernel mechanisms.

This report answers a narrower question than a benchmark:

    Does a mechanism have a concrete consequence, and is there current
    evidence that the consequence is observable in this scope?

It classifies mechanisms by what they do at the decision boundary:
``block``, ``route``, ``record``, ``diagnose``, ``advise``, or ``decorate``.
Only ``decorate`` is intrinsically suspect. A non-decorative mechanism with no
current evidence is not called bad; it is marked as unobserved for the selected
project/workspace so the operator can decide whether that absence is expected.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
MAX_EVIDENCE_PATHS = 12


@dataclass(frozen=True)
class MechanismDefinition:
    mechanism_id: str
    label: str
    consequence: str
    trigger: str
    consumer: str
    counterfactual_failure: str
    evidence_globs: tuple[str, ...]
    scope: str = "project"


@dataclass(frozen=True)
class MechanismAuditRow:
    mechanism_id: str
    label: str
    consequence: str
    trigger: str
    consumer: str
    counterfactual_failure: str
    evidence_status: str
    evidence_count: int
    usable_evidence_count: int
    placeholder_evidence_count: int
    evidence_paths: tuple[str, ...]
    placeholder_evidence_paths: tuple[str, ...]
    ceremony_risk: str


MECHANISMS: tuple[MechanismDefinition, ...] = (
    MechanismDefinition(
        mechanism_id="workbench_router",
        label="RD/autoresearch workbench router",
        consequence="route",
        trigger="RD task has bounded claim/evaluator/rubric/artifact signals.",
        consumer="RD brief, ztare autoresearch route, action-intelligence route rows.",
        counterfactual_failure="Ready workbench tasks stay in out-of-loop prose with no bypass reason.",
        evidence_globs=(
            "analytics/public/queries/rd/autoresearch_routes/*.json",
            "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
        ),
        scope="repo",
    ),
    MechanismDefinition(
        mechanism_id="subscription_dispatch",
        label="Subscription-backed worker dispatch",
        consequence="route",
        trigger="Scoped env/CLI flag selects agent capability for mutator, judge, committee, or inverter.",
        consumer="dispatch_model call sites and typed contract validators.",
        counterfactual_failure="A call site silently remains API-only or emits untyped subscription output.",
        evidence_globs=(
            "docs/internal/repo_audits/autoresearch_dispatch_parity_*.json",
        ),
        scope="repo",
    ),
    MechanismDefinition(
        mechanism_id="primitive_amnesia",
        label="Primitive amnesia / semantic catalog retrieval",
        consequence="route",
        trigger="A task may duplicate existing analytical or operator machinery.",
        consumer="RD brief, primitive tick surface, ztare primitive health.",
        counterfactual_failure="The agent rebuilds an existing primitive under new vocabulary.",
        evidence_globs=(
            "analytics/public/index/architecture_index.jsonl",
            "analytics/public/index/primitive_atlas_embeddings.json",
            "analytics/public/queries/rd_tick_primitive_surface.json",
        ),
        scope="repo",
    ),
    MechanismDefinition(
        mechanism_id="pattern_action_contract",
        label="Pattern-action contract",
        consequence="record",
        trigger="A task/problem surface maps to a known pattern or anti-pattern.",
        consumer="RD brief, pretick artifact contract, close payload receipts.",
        counterfactual_failure="A pattern is named in prose but no artifact/check is produced.",
        evidence_globs=(
            "analytics/public/queries/rd_pattern_action_contract.json",
            "projects/*/workspace/pattern_action_contract.json",
        ),
        scope="repo",
    ),
    MechanismDefinition(
        mechanism_id="tried_failed_digest",
        label="Tried/failed mutator briefing",
        consequence="record",
        trigger="R1 rejection, fit failure, contract mismatch, repeated branch, or frontier constraint.",
        consumer="Mutator briefing providers.",
        counterfactual_failure="Each retry sees the same context and repeats a killed branch.",
        evidence_globs=(
            "workspace/eval_history.jsonl",
            "workspace/dag_steering_log.jsonl",
            "workspace/latest_information_yield.json",
            "workspace/tried_failed_digest_audit.json",
        ),
    ),
    MechanismDefinition(
        mechanism_id="rubric_mode_contract",
        label="Rubric-mode contract",
        consequence="block",
        trigger="Rubric declares Newton, Kepler, calibration, or invariant-search mode.",
        consumer="autoresearch_loop launch path and rubric validator.",
        counterfactual_failure="A discovery-mode run launches without the scoring dimension that makes it meaningful.",
        evidence_globs=(
            "rubrics/*.json",
            "workspace/iteration_telemetry.jsonl",
        ),
    ),
    MechanismDefinition(
        mechanism_id="mutation_r1_contract",
        label="R1 mutation contract",
        consequence="block",
        trigger="Mutator returns candidate thesis/code for the runner.",
        consumer="mutation contract parser and candidate extraction gates.",
        counterfactual_failure="Bad code or mismatched artifact claims consume a full research iteration.",
        evidence_globs=(
            "workspace/latest_mutation_declaration.json",
            "workspace/latest_information_yield.json",
            "workspace/iteration_telemetry.jsonl",
        ),
    ),
    MechanismDefinition(
        mechanism_id="score_gates",
        label="Score caps and deterministic gates",
        consequence="block",
        trigger="Judge score or candidate artifacts violate declared evidence/gate contracts.",
        consumer="test_thesis, global gates, deterministic charter gates, telemetry.",
        counterfactual_failure="A high raw score promotes a candidate that lacks required evidence.",
        evidence_globs=(
            "workspace/latest_eval_results.json",
            "workspace/eval_history.jsonl",
            "workspace/cap_kind_iter_*.json",
        ),
    ),
    MechanismDefinition(
        mechanism_id="hill_climb_controls",
        label="Stagnation and breadth controls",
        consequence="route",
        trigger="Low information yield or repeated weakest point.",
        consumer="autoresearch loop-control state, pivot heuristics, dynamic committee refresh.",
        counterfactual_failure="The loop keeps making local edits after the signal says the search is flat.",
        evidence_globs=(
            "workspace/iteration_telemetry.jsonl",
            "workspace/loop_events.jsonl",
            "workspace/latest_information_yield.json",
        ),
    ),
    MechanismDefinition(
        mechanism_id="parallel_blitz",
        label="Parallel mutator / blitz selection",
        consequence="route",
        trigger="Rubric force flag or stagnation threshold enables K-way mutation.",
        consumer="blitz dispatcher, tournament selector, blitz survival report.",
        counterfactual_failure="A multi-basin problem is explored as one serial sample without survival telemetry.",
        evidence_globs=(
            "workspace/parallel_blitz_log.jsonl",
            "workspace/blitz_survival_report.json",
        ),
    ),
    MechanismDefinition(
        mechanism_id="primitive_class_rotation",
        label="Primitive-class rotation",
        consequence="record",
        trigger="Candidate proposes a structural class, gate, decomposition, or scaling-law move.",
        consumer="Next mutator prompt, RD eigenquestion generation, cross-substrate class ledger.",
        counterfactual_failure="Rejected and non-improving structural classes vanish from future prompts.",
        evidence_globs=(
            "workspace/explored_primitive_classes.jsonl",
            "analytics/public/queries/rd/cross_substrate_explored_classes.jsonl",
        ),
    ),
    MechanismDefinition(
        mechanism_id="eigenquestion_preflight",
        label="Eigenquestion proposal/preflight",
        consequence="advise",
        trigger="A newer advisory eigenquestion exists beside the project charter.",
        consumer="Launch preflight and operator review.",
        counterfactual_failure="A stale charter silently suppresses a reviewed orthogonal question.",
        evidence_globs=(
            "proposed_eigenquestion_*.md",
        ),
    ),
    MechanismDefinition(
        mechanism_id="operations_intelligence",
        label="Operations intelligence / action ledger",
        consequence="diagnose",
        trigger="Route rows, action-impact rows, forecast decision use, source health, or dashboard signals exist.",
        consumer="RD/operator allocation decisions.",
        counterfactual_failure="In-loop versus out-of-loop allocation is discussed but not measured.",
        evidence_globs=(
            "analytics/public/action_intelligence/state/*.json",
            "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
            "analytics/public/ledgers/reflexive/bifurcation_report.json",
        ),
        scope="repo",
    ),
)


def _scope_root(
    *,
    repo: Path,
    project: str | None = None,
    workspace: str | Path | None = None,
) -> Path:
    if workspace:
        path = Path(workspace)
        return path if path.is_absolute() else repo / path
    if project:
        return repo / "projects" / project
    return repo


def _candidate_roots(
    mechanism: MechanismDefinition,
    *,
    repo: Path,
    scope_root: Path,
) -> tuple[Path, ...]:
    if mechanism.scope == "repo":
        return (repo,)
    if scope_root == repo:
        project_roots = tuple(sorted(path for path in (repo / "projects").glob("*") if path.is_dir()))
        return (repo, *project_roots)
    return (scope_root,)


def _existing_paths_for_glob(root: Path, pattern: str) -> list[Path]:
    if pattern.startswith("workspace/") and root.name == "workspace":
        pattern = pattern.removeprefix("workspace/")
    try:
        return sorted(path for path in root.glob(pattern) if path.exists())
    except OSError:
        return []


def _is_placeholder_evidence(path: Path) -> bool:
    """Return true for files that exist but do not carry usable evidence."""

    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return True
    if not text:
        return True
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        return payload in ({}, [], None)
    if suffix == ".jsonl":
        return not any(line.strip() for line in text.splitlines())
    if suffix in {".md", ".txt"}:
        return not any(line.strip().strip("#-*` ") for line in text.splitlines())
    return False


def _relative(path: Path, repo: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _project_slug_from_scope(scope_root: Path, repo: Path, project: str | None) -> str | None:
    if project:
        return project
    projects_dir = repo / "projects"
    try:
        rel = scope_root.relative_to(projects_dir)
    except ValueError:
        return None
    return rel.parts[0] if rel.parts else None


def _project_rubric(repo: Path, scope_root: Path, project: str | None) -> dict[str, Any]:
    slug = _project_slug_from_scope(scope_root, repo, project)
    if not slug:
        return {}
    return _read_json(repo / "rubrics" / f"{slug}.json")


def _workspace_dir(scope_root: Path) -> Path:
    return scope_root if scope_root.name == "workspace" else scope_root / "workspace"


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _max_stagnation(workspace: Path) -> int:
    max_seen = 0
    for row in _jsonl_rows(workspace / "iteration_telemetry.jsonl"):
        for key in ("stagnation_count", "stagnant_window"):
            try:
                max_seen = max(max_seen, int(row.get(key) or 0))
            except (TypeError, ValueError):
                pass
    info = _read_json(workspace / "latest_information_yield.json")
    decision = info.get("decision") if isinstance(info.get("decision"), dict) else {}
    try:
        max_seen = max(max_seen, int(decision.get("stagnant_window") or 0))
    except (TypeError, ValueError):
        pass
    return max_seen


def _optional_mechanism_not_triggered(
    mechanism_id: str,
    *,
    repo: Path,
    scope_root: Path,
    project: str | None,
) -> bool:
    rubric = _project_rubric(repo, scope_root, project)
    workspace = _workspace_dir(scope_root)
    if mechanism_id == "parallel_blitz":
        try:
            k = int(rubric.get("parallel_mutator_k", 1) or 1)
        except (TypeError, ValueError):
            k = 1
        force = bool(rubric.get("parallel_mutator_force", False))
        force_iters = bool(rubric.get("parallel_mutator_force_iters") or [])
        try:
            min_stag = int(rubric.get("parallel_mutator_min_stagnation", 1) or 1)
        except (TypeError, ValueError):
            min_stag = 1
        return not (k > 1 and (force or force_iters or _max_stagnation(workspace) >= min_stag))
    if mechanism_id == "primitive_class_rotation":
        return not bool(rubric.get("enable_primitive_class_rotation", False))
    if mechanism_id == "eigenquestion_preflight":
        return not any(scope_root.glob("proposed_eigenquestion_*.md"))
    return False


def audit_mechanism_consequences(
    *,
    repo: Path = REPO,
    project: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    scope_root = _scope_root(repo=repo, project=project, workspace=workspace).resolve()
    rows: list[MechanismAuditRow] = []
    consequence_counts: dict[str, int] = {}
    evidence_status_counts: dict[str, int] = {}
    evidence_quality_counts: dict[str, int] = {}
    ceremony_risk_counts: dict[str, int] = {}

    for mechanism in MECHANISMS:
        evidence: list[Path] = []
        for root in _candidate_roots(mechanism, repo=repo, scope_root=scope_root):
            for pattern in mechanism.evidence_globs:
                evidence.extend(_existing_paths_for_glob(root, pattern))
        deduped_paths = tuple(sorted({path.resolve() for path in evidence}))
        usable_paths = tuple(path for path in deduped_paths if not _is_placeholder_evidence(path))
        placeholder_paths = tuple(path for path in deduped_paths if _is_placeholder_evidence(path))
        deduped = tuple(_relative(path, repo) for path in deduped_paths)
        usable = tuple(_relative(path, repo) for path in usable_paths)
        placeholders = tuple(_relative(path, repo) for path in placeholder_paths)
        evidence_paths = usable[:MAX_EVIDENCE_PATHS]
        placeholder_evidence_paths = placeholders[:MAX_EVIDENCE_PATHS]
        if mechanism.consequence == "decorate":
            status = "decorative_by_definition"
            risk = "high"
            quality = "decorative"
        elif usable:
            status = "observed"
            risk = "low"
            quality = "usable"
        elif placeholders:
            status = "placeholder_only"
            risk = "medium"
            quality = "placeholder_only"
        elif _optional_mechanism_not_triggered(
            mechanism.mechanism_id,
            repo=repo,
            scope_root=scope_root,
            project=project,
        ):
            status = "not_triggered"
            risk = "low"
            quality = "not_triggered"
        else:
            status = "unobserved_in_scope"
            risk = "medium"
            quality = "missing"
        row = MechanismAuditRow(
            mechanism_id=mechanism.mechanism_id,
            label=mechanism.label,
            consequence=mechanism.consequence,
            trigger=mechanism.trigger,
            consumer=mechanism.consumer,
            counterfactual_failure=mechanism.counterfactual_failure,
            evidence_status=status,
            evidence_count=len(deduped),
            usable_evidence_count=len(usable),
            placeholder_evidence_count=len(placeholders),
            evidence_paths=evidence_paths,
            placeholder_evidence_paths=placeholder_evidence_paths,
            ceremony_risk=risk,
        )
        rows.append(row)
        consequence_counts[row.consequence] = consequence_counts.get(row.consequence, 0) + 1
        evidence_status_counts[row.evidence_status] = (
            evidence_status_counts.get(row.evidence_status, 0) + 1
        )
        evidence_quality_counts[quality] = evidence_quality_counts.get(quality, 0) + 1
        ceremony_risk_counts[row.ceremony_risk] = (
            ceremony_risk_counts.get(row.ceremony_risk, 0) + 1
        )

    return {
        "schema": "ztare-mechanism-consequence-audit-v1",
        "scope": {
            "repo": str(repo),
            "project": project,
            "workspace": str(workspace) if workspace else None,
            "scope_root": _relative(scope_root, repo),
        },
        "summary": {
            "mechanism_count": len(rows),
            "consequence_counts": dict(sorted(consequence_counts.items())),
            "evidence_status_counts": dict(sorted(evidence_status_counts.items())),
            "evidence_quality_counts": dict(sorted(evidence_quality_counts.items())),
            "ceremony_risk_counts": dict(sorted(ceremony_risk_counts.items())),
            "intrinsic_decorative_count": consequence_counts.get("decorate", 0),
            "placeholder_only_count": evidence_status_counts.get("placeholder_only", 0),
        },
        "rows": [asdict(row) for row in rows],
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    scope = report["scope"]
    lines = [
        "Autoresearch mechanism consequence audit",
        f"scope={scope['scope_root']} mechanisms={summary['mechanism_count']}",
        "consequences=" + json.dumps(summary["consequence_counts"], sort_keys=True),
        "evidence_status=" + json.dumps(summary["evidence_status_counts"], sort_keys=True),
        "evidence_quality=" + json.dumps(summary.get("evidence_quality_counts", {}), sort_keys=True),
        "ceremony_risk=" + json.dumps(summary["ceremony_risk_counts"], sort_keys=True),
    ]
    for row in report["rows"]:
        lines.append(
            "- {mechanism_id} [{consequence}/{evidence_status}/risk={ceremony_risk}]: "
            "{label}; consumer={consumer}; prevents={counterfactual_failure}; "
            "evidence={evidence}; placeholders={placeholders}".format(
                evidence=", ".join(row["evidence_paths"][:3]) + (
                    f" (+{row['evidence_count'] - 3} more)" if row["evidence_count"] > 3 else ""
                )
                if row["evidence_paths"]
                else "none",
                placeholders=", ".join(row.get("placeholder_evidence_paths", [])[:3]) or "none",
                **row,
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Restrict project-scoped evidence to projects/<slug>.")
    parser.add_argument("--workspace", help="Restrict project-scoped evidence to a workspace path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)
    report = audit_mechanism_consequences(
        project=args.project,
        workspace=args.workspace,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
