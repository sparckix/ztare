"""Aggregate health surface for the autoresearch/RD workbench.

This report reuses the narrow validators and read-only audits. It is meant as
the first operator page: run it to see whether the kernel is ready, needs review,
or has a blocking integrity problem before launching more autoresearch.
"""
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]

STATUS_RANK = {"ok": 0, "attention": 1, "needs_attention": 2}


def _make_command(target: str, **vars_: Any) -> str:
    parts = ["make", target]
    for key, value in vars_.items():
        if value is None or value == "":
            continue
        parts.append(f"{key}={shlex.quote(str(value))}")
    return " ".join(parts)


def _dispatch_validate(repo: Path) -> dict[str, Any]:
    from scripts.public.validators.validate_autoresearch_llm_dispatch import validate

    return validate(repo=repo)


def _catalog_health(repo: Path):
    from src.ztare.research_director.primitive_catalog_taxonomy import catalog_health

    return catalog_health(
        catalog_path=repo / "analytics" / "public" / "index" / "architecture_index.jsonl",
        atlas_path=repo / "analytics" / "public" / "index" / "primitive_atlas_embeddings.json",
        rendered_index_path=repo / "src" / "ztare" / "architecture_index" / "INDEX.md",
    )


def _mechanism_consequences(
    *,
    repo: Path,
    project: str | None,
    workspace: str | Path | None,
) -> dict[str, Any]:
    from src.ztare.reports.mechanism_consequence_audit import audit_mechanism_consequences

    return audit_mechanism_consequences(repo=repo, project=project, workspace=workspace)


def _rubric_modes(*, repo: Path, rubric: str | Path | None) -> dict[str, Any]:
    from src.ztare.reports.rubric_mode_corpus_audit import audit_rubric_mode_corpus

    return audit_rubric_mode_corpus(repo=repo, rubric=rubric)


def _hill_climb(
    *,
    repo: Path,
    project: str | None,
    stagnation_threshold: int,
) -> dict[str, Any]:
    from src.ztare.reports.hill_climb_behavior_audit import build_hill_climb_behavior_audit

    return build_hill_climb_behavior_audit(
        repo=repo,
        project=project,
        stagnation_threshold=stagnation_threshold,
        limit=0,
    )


def _subscription_outcomes(*, repo: Path, project: str | None) -> dict[str, Any]:
    from src.ztare.reports.subscription_outcome_audit import audit_subscription_outcomes

    return audit_subscription_outcomes(repo=repo, project=project)


def _operations_intelligence(repo: Path) -> dict[str, Any]:
    from src.ztare.reports.operations_intelligence import build

    return build(repo=repo)


def _fixtures() -> dict[str, Any]:
    from scripts.public.validators.validate_inloop_mechanism_fixtures import run_fixtures

    return run_fixtures()


def _primitive_parent_utility() -> dict[str, Any]:
    from src.ztare.research_director.primitive_parent_utility import build_parent_utility_audit

    return asdict(build_parent_utility_audit())


def _primitive_miss_queue(repo: Path) -> dict[str, Any]:
    from src.ztare.research_director.primitive_amnesia import miss_queue_status

    return miss_queue_status(
        repo / "analytics" / "public" / "queries" / "primitive_amnesia_miss_queue.jsonl"
    )


def _component(
    *,
    component: str,
    status: str,
    summary: dict[str, Any],
    action: str,
    next_command: str,
) -> dict[str, Any]:
    return {
        "component": component,
        "status": status,
        "summary": summary,
        "action": action,
        "next_command": next_command,
    }


def _overall_status(components: list[dict[str, Any]]) -> str:
    rank = max((STATUS_RANK.get(str(row["status"]), 2) for row in components), default=0)
    for status, value in STATUS_RANK.items():
        if value == rank:
            return status
    return "needs_attention"


def build_autoresearch_kernel_health(
    *,
    repo: Path = REPO,
    project: str | None = None,
    workspace: str | Path | None = None,
    rubric: str | Path | None = None,
    stagnation_threshold: int = 2,
) -> dict[str, Any]:
    repo = repo.resolve()
    components: list[dict[str, Any]] = []

    dispatch = _dispatch_validate(repo)
    dispatch_summary = dict(dispatch.get("summary") or {})
    direct_allowed = list(dispatch.get("direct_allowed") or [])
    dispatch_findings = int(dispatch_summary.get("findings") or 0)
    components.append(
        _component(
            component="dispatch",
            status="ok" if dispatch_findings == 0 else "needs_attention",
            summary={
                "findings": dispatch_findings,
                "dispatch_sites": dispatch_summary.get("dispatch_sites", 0),
                "wrapped_sites": dispatch_summary.get("wrapped_sites", 0),
                "direct_allowed_sites": dispatch_summary.get("direct_allowed_sites", 0),
                "direct_allowed": direct_allowed[:8],
            },
            action="fix dispatch findings before relying on subscription workers"
            if dispatch_findings
            else "no action",
            next_command=_make_command("autoresearch-dispatch-validate", JSON=1),
        )
    )

    catalog = _catalog_health(repo)
    parent_utility = _primitive_parent_utility()
    miss_queue = _primitive_miss_queue(repo)
    open_misses = int(miss_queue.get("open_count") or 0)
    malformed_misses = int(miss_queue.get("malformed_count") or 0)
    catalog_needs_attention = (
        not bool(catalog.ok)
        or not bool(parent_utility.get("ok"))
        or malformed_misses > 0
    )
    catalog_status = (
        "needs_attention"
        if catalog_needs_attention
        else "attention" if open_misses else "ok"
    )
    components.append(
        _component(
            component="primitive_catalog",
            status=catalog_status,
            summary={
                "ok": bool(catalog.ok),
                "row_count": catalog.row_count,
                "warnings": list(catalog.warnings),
                "stale_outputs": list(catalog.stale_outputs),
                "parent_utility": {
                    "ok": parent_utility.get("ok"),
                    "case_count": parent_utility.get("case_count", 0),
                    "passed": parent_utility.get("passed", 0),
                    "catalog_rank_recall": parent_utility.get("catalog_rank_recall"),
                    "worker_rank_recall": parent_utility.get("worker_rank_recall"),
                    "child_recall": parent_utility.get("child_recall"),
                },
                "miss_queue": {
                    "path": miss_queue.get("path"),
                    "row_count": miss_queue.get("row_count", 0),
                    "open_count": open_misses,
                    "malformed_count": malformed_misses,
                    "status_counts": miss_queue.get("status_counts", {}),
                    "latest_open": miss_queue.get("latest_open", []),
                },
            },
            action=(
                "repair malformed primitive-amnesia miss-queue rows"
                if malformed_misses
                else "refresh/repair the catalog, atlas, or parent-node utility before adding new primitive machinery"
                if not catalog.ok or not bool(parent_utility.get("ok"))
                else "review and close primitive-amnesia miss-queue rows"
                if open_misses
                else "no action"
            ),
            next_command=_make_command("primitive-parent-utility", JSON=1)
            if not bool(parent_utility.get("ok"))
            else _make_command("primitive-amnesia-eval", RECORD_MISSES=1)
            if open_misses or malformed_misses
            else _make_command("primitive-catalog-health", JSON=1),
        )
    )

    mechanism = _mechanism_consequences(repo=repo, project=project, workspace=workspace)
    mechanism_summary = dict(mechanism.get("summary") or {})
    evidence_counts = dict(mechanism_summary.get("evidence_status_counts") or {})
    unobserved = int(evidence_counts.get("unobserved_in_scope") or 0)
    not_triggered = int(evidence_counts.get("not_triggered") or 0)
    placeholder_only = int(mechanism_summary.get("placeholder_only_count") or 0)
    decorative = int(mechanism_summary.get("intrinsic_decorative_count") or 0)
    components.append(
        _component(
            component="mechanism_consequences",
            status="ok" if unobserved == 0 and placeholder_only == 0 and decorative == 0 else "needs_attention",
            summary={
                "mechanism_count": mechanism_summary.get("mechanism_count", 0),
                "evidence_status_counts": evidence_counts,
                "evidence_quality_counts": mechanism_summary.get("evidence_quality_counts", {}),
                "not_triggered_count": not_triggered,
                "intrinsic_decorative_count": decorative,
                "placeholder_only_count": placeholder_only,
            },
            action="inspect unobserved, placeholder-only, or decorative mechanisms in the consequence audit"
            if unobserved or placeholder_only or decorative
            else "no action",
            next_command=_make_command(
                "autoresearch-consequence-audit",
                PROJECT=project,
                WORKSPACE=workspace,
                JSON=1,
            ),
        )
    )

    fixture_report = _fixtures()
    fixture_passed = bool(fixture_report.get("passed"))
    components.append(
        _component(
            component="inloop_fixtures",
            status="ok" if fixture_passed else "needs_attention",
            summary={
                "passed": fixture_passed,
                "num_passed": fixture_report.get("num_passed", 0),
                "num_fixtures": fixture_report.get("num_fixtures", 0),
                "by_status": ((fixture_report.get("mechanism_status") or {}).get("by_status") or {}),
            },
            action="repair failing in-loop mechanism fixtures before launch"
            if not fixture_passed
            else "no action",
            next_command=_make_command("inloop-fixture-validate", JSON=1),
        )
    )

    rubric_report = _rubric_modes(repo=repo, rubric=rubric)
    rubric_summary = dict(rubric_report.get("summary") or {})
    rubric_attention = int(rubric_summary.get("attention_count") or 0)
    legacy_unset = dict(rubric_summary.get("legacy_unset") or {})
    components.append(
        _component(
            component="rubric_modes",
            status="attention" if rubric_attention else "ok",
            summary={
                "attention_count": rubric_attention,
                "status_counts": rubric_summary.get("status_counts", {}),
                "mode_counts": rubric_summary.get("mode_counts", {}),
                "legacy_unset_count": legacy_unset.get("count", 0),
                "legacy_unset_with_project_count": legacy_unset.get("with_project_count", 0),
            },
            action="repair Newton/Kepler rubric attention before serious runs"
            if rubric_attention
            else "no action",
            next_command=_make_command(
                "autoresearch-rubric-mode-audit",
                RUBRIC=rubric,
                LIMIT=20,
            ),
        )
    )

    hill = _hill_climb(repo=repo, project=project, stagnation_threshold=stagnation_threshold)
    hill_status_counts = dict(hill.get("status_counts") or {})
    control_due = int(hill_status_counts.get("control_due_without_breadth_evidence") or 0)
    post_control = dict(hill.get("post_control_outcome_totals") or {})
    components.append(
        _component(
            component="hill_climb_controls",
            status="needs_attention" if control_due else "ok",
            summary={
                "workspace_count": hill.get("workspace_count", 0),
                "stagnant_workspace_count": hill.get("stagnant_workspace_count", 0),
                "status_counts": hill_status_counts,
                "active_control_event_count": post_control.get("active_control_event_count", 0),
                "post_control_success_rate": post_control.get("post_control_success_rate"),
            },
            action="inspect workspaces where stagnation had no active breadth-control evidence"
            if control_due
            else "no action",
            next_command=_make_command(
                "autoresearch-hillclimb-audit",
                PROJECT=project,
                STAGNATION_THRESHOLD=stagnation_threshold if stagnation_threshold != 2 else "",
                LIMIT=20,
            ),
        )
    )

    operations = _operations_intelligence(repo)
    agentic_workbench = dict(operations.get("agentic_workbench") or {})
    subscription_outcomes = dict(agentic_workbench.get("subscription_outcomes") or {})
    subscription_summary = dict(subscription_outcomes.get("summary") or {})
    route_coverage = dict(agentic_workbench.get("route_row_coverage") or {})
    source_health = dict(operations.get("source_health_summary") or {})
    source_health_issues = int(source_health.get("issue_count") or 0)
    blocking_source_issues = int(source_health.get("blocking_count") or 0)
    warning_source_issues = int(source_health.get("warning_count") or 0)
    route_rows_needed = int(route_coverage.get("additional_route_rows_needed") or 0)
    unexplained_bypasses = int(
        agentic_workbench.get("ready_workbench_bypasses_without_reason") or 0
    )
    route_needs_attention = bool(route_coverage.get("needs_logging_attention"))
    operations_needs_attention = (
        route_needs_attention
        or blocking_source_issues > 0
        or unexplained_bypasses > 0
    )
    components.append(
        _component(
            component="operations_intelligence",
            status="needs_attention" if operations_needs_attention else "ok",
            summary={
                "agentic_workbench_rows": agentic_workbench.get("rows", 0),
                "route_row_coverage_status": route_coverage.get("status"),
                "route_rows": route_coverage.get("route_rows", 0),
                "recommended_min_route_rows": route_coverage.get("recommended_min_route_rows", 0),
                "additional_route_rows_needed": route_rows_needed,
                "ready_workbench_bypasses": agentic_workbench.get("ready_workbench_bypasses", 0),
                "ready_workbench_bypasses_without_reason": unexplained_bypasses,
                "missing_surface_preparations": agentic_workbench.get("missing_surface_preparations", 0),
                "source_health_issues": source_health_issues,
                "source_health_blockers": blocking_source_issues,
                "source_health_warnings": warning_source_issues,
                "source_health_issue_type_counts": source_health.get("issue_type_counts", {}),
                "subscription_outcome_status": subscription_outcomes.get("status"),
                "clean_matched_run_group_count": subscription_summary.get(
                    "clean_matched_run_group_count", 0
                ),
                "weak_matched_run_group_count": subscription_summary.get(
                    "weak_matched_run_group_count", 0
                ),
            },
            action="record routed RD decisions or repair blocking action-intelligence sources"
            if operations_needs_attention
            else "no action",
            next_command=_make_command("operations-intelligence"),
        )
    )

    component_status = _overall_status(components)
    subscription_outcomes = _subscription_outcomes(repo=repo, project=project)
    evidence_gaps: list[dict[str, Any]] = []
    if not_triggered:
        dormant_rows = [
            {
                "mechanism_id": row.get("mechanism_id"),
                "label": row.get("label"),
                "trigger": row.get("trigger"),
            }
            for row in list(mechanism.get("rows") or [])
            if row.get("evidence_status") == "not_triggered"
        ][:8]
        evidence_gaps.append(
            {
                "id": "not_triggered_mechanisms",
                "status": "not_triggered",
                "summary": {
                    "count": not_triggered,
                    "examples": dormant_rows,
                },
                "action": (
                    "run a project or fixture that exercises these optional controls "
                    "before treating them as outcome-evidenced"
                ),
                "next_command": _make_command(
                    "autoresearch-consequence-audit",
                    PROJECT=project,
                    WORKSPACE=workspace,
                    JSON=1,
                ),
            }
        )
    if not bool(subscription_outcomes.get("ok")):
        matched_plan = list(subscription_outcomes.get("matched_run_plan") or [])
        first_candidate = matched_plan[0] if matched_plan else {}
        evidence_gaps.append(
            {
                "id": "subscription_outcomes",
                "status": subscription_outcomes.get("status"),
                "summary": {
                    **dict(subscription_outcomes.get("summary") or {}),
                    "suggested_matched_pair_command": first_candidate.get("matched_pair_command"),
                    "suggested_matched_pair_project": first_candidate.get("project"),
                    "suggested_matched_pair_rubric": first_candidate.get("rubric"),
                    "suggested_matched_pair_suitability": first_candidate.get("suitability_score"),
                },
                "action": subscription_outcomes.get("action"),
                "next_command": _make_command(
                    "autoresearch-subscription-outcome-audit",
                    PROJECT=project,
                    JSON=1,
                ),
            }
        )
    status = (
        "attention"
        if evidence_gaps and component_status == "ok"
        else component_status
    )
    return {
        "schema": "ztare-autoresearch-kernel-health-v1",
        "scope": {
            "repo": str(repo),
            "project": project,
            "workspace": str(workspace) if workspace else None,
            "rubric": str(rubric) if rubric else None,
            "stagnation_threshold": stagnation_threshold,
        },
        "summary": {
            "overall_status": status,
            "component_status": component_status,
            "component_counts": {
                state: sum(1 for row in components if row["status"] == state)
                for state in ("ok", "attention", "needs_attention")
            },
            "component_count": len(components),
            "evidence_gap_count": len(evidence_gaps),
        },
        "components": components,
        "evidence_gaps": evidence_gaps,
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    scope = report["scope"]
    lines = [
        "Autoresearch kernel health",
        f"status={summary['overall_status']} components={summary['component_count']}",
        "component_counts=" + json.dumps(summary["component_counts"], sort_keys=True),
        f"evidence_gaps={summary.get('evidence_gap_count', 0)}",
        (
            "scope="
            + json.dumps(
                {
                    "project": scope.get("project"),
                    "workspace": scope.get("workspace"),
                    "rubric": scope.get("rubric"),
                    "stagnation_threshold": scope.get("stagnation_threshold"),
                },
                sort_keys=True,
            )
        ),
    ]
    for row in report["components"]:
        lines.append(
            "- {component}: {status}; action={action}; next={next_command}; summary={summary}".format(
                component=row["component"],
                status=row["status"],
                action=row["action"],
                next_command=row["next_command"],
                summary=json.dumps(row["summary"], sort_keys=True),
            )
        )
    for row in report.get("evidence_gaps") or []:
        lines.append(
            "- evidence_gap:{id}: {status}; action={action}; next={next_command}; "
            "summary={summary}".format(
                id=row["id"],
                status=row["status"],
                action=row["action"],
                next_command=row["next_command"],
                summary=json.dumps(row["summary"], sort_keys=True),
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Restrict project-scoped health where supported.")
    parser.add_argument("--workspace", help="Restrict mechanism evidence to one workspace.")
    parser.add_argument("--rubric", help="Restrict rubric-mode audit to one rubric path.")
    parser.add_argument("--stagnation-threshold", type=int, default=2)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when overall status is not ok.",
    )
    args = parser.parse_args(argv)

    report = build_autoresearch_kernel_health(
        project=args.project,
        workspace=args.workspace,
        rubric=args.rubric,
        stagnation_threshold=args.stagnation_threshold,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 1 if args.strict and report["summary"]["overall_status"] != "ok" else 0


if __name__ == "__main__":
    raise SystemExit(main())
