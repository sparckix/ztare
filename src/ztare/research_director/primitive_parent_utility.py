"""Utility audit for primitive parent-node surfacing.

The primitive surface has two parent graphs:

- catalog families, derived from the architecture index;
- LLM-mediated worker families, derived from explicit call-site cards.

This module checks whether those parent nodes route held-out task descriptions
to the expected family and at least one useful child surface. It is deterministic
and read-only; the goal is to catch parent labels that look tidy but do not help
the next RD action.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ztare.research_director.primitive_family_registry import (
    build_registry_integrity_audit,
)
from ztare.research_director.primitive_tick_surface import build_primitive_tick_surface


@dataclass(frozen=True)
class ParentUtilityCase:
    case_id: str
    query_terms: tuple[str, ...]
    expected_catalog_family: str | None = None
    expected_worker_family: str | None = None
    expected_child_ids: tuple[str, ...] = ()
    max_family_rank: int = 2
    max_worker_rank: int = 1
    top_hit_k: int = 10


@dataclass(frozen=True)
class ParentUtilityResult:
    case_id: str
    ok: bool
    catalog_family_rank: int | None
    worker_family_rank: int | None
    expected_catalog_family: str | None
    expected_worker_family: str | None
    expected_child_ids: tuple[str, ...]
    matched_child_ids: tuple[str, ...]
    top_hit_ids: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ParentUtilityAudit:
    ok: bool
    case_count: int
    passed: int
    failed: int
    catalog_rank_recall: float
    worker_rank_recall: float
    child_recall: float
    registry_integrity_ok: bool
    registry_issue_count: int
    results: tuple[ParentUtilityResult, ...]


DEFAULT_CASES: tuple[ParentUtilityCase, ...] = (
    ParentUtilityCase(
        case_id="loop_stagnation_information_yield",
        query_terms=("stop", "loop", "stagnation", "no new information", "iteration", "yield"),
        expected_catalog_family="evidence_governance_gate",
        expected_child_ids=("ITERATIONSIGNAL", "EVALUATE-INFORMATION-YIELD", "INFORMATION-YIELD"),
    ),
    ParentUtilityCase(
        case_id="proof_remaining_goals",
        query_terms=("proof", "remaining goals", "lean", "unsolved", "what left to prove"),
        expected_catalog_family="proof_formalization_worker",
        expected_child_ids=("EXTRACT-UNSOLVED-GOALS", "PROOF-STATE-SIGNAL"),
    ),
    ParentUtilityCase(
        case_id="fit_residual_structure",
        query_terms=("fit", "residual", "regime", "distance", "structural fingerprint"),
        expected_catalog_family="model_fit_structure_probe",
        expected_child_ids=("BUILD-RESIDUAL-FINGERPRINT", "COMPUTE-FINGERPRINT", "FIT-PRIMITIVE"),
    ),
    ParentUtilityCase(
        case_id="operations_intelligence_source_health",
        query_terms=(
            "operations_intelligence",
            "action_intelligence",
            "source_health",
            "dashboard",
            "route_coverage",
            "bypass",
        ),
        expected_catalog_family="mining_operations_intelligence",
        expected_child_ids=("CROSS-SOURCE-DIVERGENCE-AUDIT",),
    ),
    ParentUtilityCase(
        case_id="cold_start_deanchor_seed",
        query_terms=("cold_start", "deanchor", "inversion", "cross-domain", "seed"),
        expected_worker_family="external_perspective_generator",
        expected_child_ids=("COLD-LLM-ERDOS-SEED", "COLD-SHOT-SEED-PROVIDER", "QUERY-COLD-LLM-ERDOS-SEED"),
    ),
    ParentUtilityCase(
        case_id="rubric_review_pre_run",
        query_terms=("rubric_review", "pre_run", "evidence_gap", "charter", "review"),
        expected_worker_family="review_governance_helper",
        expected_child_ids=("rubric_review",),
    ),
    ParentUtilityCase(
        case_id="natural_rd_eigenquestion_rotation",
        query_terms=(
            "The current project has pending eigenquestions and may need thesis rotation; "
            "show whether the research director should invoke an orthogonal question "
            "instead of continuing the same thesis.",
        ),
        expected_catalog_family="research_move_operator",
        expected_child_ids=("EIGENQUESTION-GENERATOR",),
        max_family_rank=3,
        top_hit_k=12,
    ),
    ParentUtilityCase(
        case_id="natural_rd_stagnation_control",
        query_terms=(
            "The loop has stagnated for several iterations with little information yield; "
            "inspect loop-control, pivot heuristics, thesis_control_mode, and whether "
            "breadth evidence exists before another iteration.",
        ),
        expected_catalog_family="evidence_governance_gate",
        expected_child_ids=("ITERATIONSIGNAL", "EVALUATE-INFORMATION-YIELD"),
        max_family_rank=3,
        top_hit_k=12,
    ),
    ParentUtilityCase(
        case_id="natural_rd_operations_source_health",
        query_terms=(
            "The RD needs an operations intelligence packet: route coverage, ready "
            "workbench bypass reasons, source health warnings, and cross source "
            "divergence before choosing the next workbench action.",
        ),
        expected_catalog_family="mining_operations_intelligence",
        expected_child_ids=("CROSS-SOURCE-DIVERGENCE-AUDIT",),
        max_family_rank=3,
        top_hit_k=12,
    ),
    ParentUtilityCase(
        case_id="natural_rd_proof_goal_surface",
        query_terms=(
            "Before editing the proof again, inspect the Lean state, remaining "
            "unsolved goals, and which theorem obligations are still open.",
        ),
        expected_catalog_family="proof_formalization_worker",
        expected_child_ids=("EXTRACT-UNSOLVED-GOALS", "PROOF-STATE-SIGNAL"),
        max_family_rank=3,
        top_hit_k=12,
    ),
    ParentUtilityCase(
        case_id="natural_rd_subscription_outcome_review",
        query_terms=(
            "Compare API versus subscription worker outcomes for autoresearch "
            "runs before claiming transport lift or changing the default worker.",
        ),
        expected_catalog_family="mining_operations_intelligence",
        expected_child_ids=("SUBSCRIPTION-OUTCOME-AUDIT",),
        max_family_rank=3,
        top_hit_k=12,
    ),
    ParentUtilityCase(
        case_id="natural_rd_failed_branch_constraints",
        query_terms=(
            "Surface tried failed branches and negative constraints from R1 "
            "retries, fit failures, and contract mismatches before the next "
            "mutator call.",
        ),
        expected_catalog_family="orchestration_briefing_provider",
        expected_child_ids=("TRIED-FAILED-DIGEST-PROVIDER",),
        max_family_rank=3,
        top_hit_k=12,
    ),
    ParentUtilityCase(
        case_id="natural_rd_rubric_mode_launch_review",
        query_terms=(
            "Check whether blitz and parallel mutator launch modes are allowed "
            "by rubric mode before running autoresearch.",
        ),
        expected_catalog_family="mining_operations_intelligence",
        expected_child_ids=("RUBRIC-MODE-CORPUS-AUDIT",),
        max_family_rank=3,
        top_hit_k=12,
    ),
    ParentUtilityCase(
        case_id="natural_rd_mechanism_consequence_review",
        query_terms=(
            "Audit whether mechanism carriers produce downstream consequence "
            "evidence or only add process around the loop.",
        ),
        expected_catalog_family="mining_operations_intelligence",
        expected_child_ids=("MECHANISM-CONSEQUENCE-AUDIT",),
        max_family_rank=3,
        top_hit_k=12,
    ),
)


def _family_rank(parent_nodes: list[dict[str, Any]], *, scope: str, family_id: str) -> int | None:
    scoped = [node for node in parent_nodes if node.get("scope") == scope]
    for idx, node in enumerate(scoped, start=1):
        if node.get("family_id") == family_id:
            return idx
    return None


def _child_ids_from_parent_nodes(parent_nodes: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for node in parent_nodes:
        for key in ("child_primitives", "example_ids"):
            value = node.get(key)
            if isinstance(value, (list, tuple)):
                out.update(str(item) for item in value)
    return out


def evaluate_parent_case(case: ParentUtilityCase) -> ParentUtilityResult:
    surface = build_primitive_tick_surface(
        query_terms=list(case.query_terms),
        top_n=max(case.top_hit_k, 1),
        per_bucket=2,
    )
    top_hit_ids = tuple(hit.id for hit in surface.top_hits[:case.top_hit_k])
    parent_child_ids = _child_ids_from_parent_nodes(surface.parent_nodes)
    top_hit_set = set(top_hit_ids)
    expected = set(case.expected_child_ids)
    matched = tuple(
        child_id
        for child_id in case.expected_child_ids
        if child_id in top_hit_set or child_id in parent_child_ids
    )

    catalog_rank = (
        _family_rank(surface.parent_nodes, scope="catalog", family_id=case.expected_catalog_family)
        if case.expected_catalog_family
        else None
    )
    worker_rank = (
        _family_rank(surface.parent_nodes, scope="llm_mediated", family_id=case.expected_worker_family)
        if case.expected_worker_family
        else None
    )

    notes: list[str] = []
    if case.expected_catalog_family and (catalog_rank is None or catalog_rank > case.max_family_rank):
        notes.append(
            f"catalog family {case.expected_catalog_family} ranked {catalog_rank}; "
            f"required <= {case.max_family_rank}"
        )
    if case.expected_worker_family and (worker_rank is None or worker_rank > case.max_worker_rank):
        notes.append(
            f"worker family {case.expected_worker_family} ranked {worker_rank}; "
            f"required <= {case.max_worker_rank}"
        )
    if expected and not matched:
        notes.append("no expected child primitive/card surfaced")

    return ParentUtilityResult(
        case_id=case.case_id,
        ok=not notes,
        catalog_family_rank=catalog_rank,
        worker_family_rank=worker_rank,
        expected_catalog_family=case.expected_catalog_family,
        expected_worker_family=case.expected_worker_family,
        expected_child_ids=case.expected_child_ids,
        matched_child_ids=matched,
        top_hit_ids=top_hit_ids,
        notes=tuple(notes),
    )


def build_parent_utility_audit(
    cases: tuple[ParentUtilityCase, ...] = DEFAULT_CASES,
) -> ParentUtilityAudit:
    case_by_id = {case.case_id: case for case in cases}
    results = tuple(evaluate_parent_case(case) for case in cases)
    registry_audit = build_registry_integrity_audit()
    case_count = len(results)
    passed = sum(1 for result in results if result.ok)
    catalog_cases = [result for result in results if result.expected_catalog_family]
    worker_cases = [result for result in results if result.expected_worker_family]
    child_cases = [result for result in results if result.expected_child_ids]

    def ratio(done: int, total: int) -> float:
        return round(done / total, 4) if total else 1.0

    catalog_ok = sum(
        1
        for result in catalog_cases
        if result.catalog_family_rank is not None
        and result.catalog_family_rank <= case_by_id[result.case_id].max_family_rank
    )
    worker_ok = sum(
        1
        for result in worker_cases
        if result.worker_family_rank is not None
        and result.worker_family_rank <= case_by_id[result.case_id].max_worker_rank
    )
    child_ok = sum(1 for result in child_cases if result.matched_child_ids)

    return ParentUtilityAudit(
        ok=passed == case_count and registry_audit.ok,
        case_count=case_count,
        passed=passed,
        failed=case_count - passed,
        catalog_rank_recall=ratio(catalog_ok, len(catalog_cases)),
        worker_rank_recall=ratio(worker_ok, len(worker_cases)),
        child_recall=ratio(child_ok, len(child_cases)),
        registry_integrity_ok=registry_audit.ok,
        registry_issue_count=len(registry_audit.issues),
        results=results,
    )


def render_parent_utility_audit(audit: ParentUtilityAudit) -> str:
    lines = [
        (
            "Primitive parent utility "
            f"status={'ok' if audit.ok else 'needs_attention'} "
            f"cases={audit.case_count} passed={audit.passed}"
        ),
        (
            f"catalog_rank_recall={audit.catalog_rank_recall:g} "
            f"worker_rank_recall={audit.worker_rank_recall:g} "
            f"child_recall={audit.child_recall:g} "
            f"registry_integrity={'ok' if audit.registry_integrity_ok else 'needs_attention'}"
        ),
    ]
    for result in audit.results:
        status = "ok" if result.ok else "needs_attention"
        lines.append(
            f"- {result.case_id}: {status}; "
            f"catalog_rank={result.catalog_family_rank}; worker_rank={result.worker_family_rank}; "
            f"matched={', '.join(result.matched_child_ids) or '(none)'}"
        )
        for note in result.notes:
            lines.append(f"  {note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    audit = build_parent_utility_audit()
    if args.json:
        print(json.dumps(asdict(audit), indent=2, sort_keys=True))
    else:
        print(render_parent_utility_audit(audit))
    return 0 if audit.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
