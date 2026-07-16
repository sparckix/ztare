"""SolverActionContract — upstream typed contract for the solver lane.

Mirrors the upstream typed pattern_action_contract structure, per the
epistemic-generation finding H32-H42 in
workingpapers/epistemic-generation/research_log.md: scope + goal_excerpt +
pattern_chain + anti_patterns + required_receipts + executable action_program
with program_counter_rule and stop_condition + source_cue_check +
downstream_consumer_check.

The contract IS the dispatch plan. Layer dispatch in the CLI worker advances
the program counter ONE LAYER per cycle, respects the stop_condition, and
validates each receipt named in required_receipts before declaring a closure
credit-ready at the solver layer (final credit decision is deferred to
leanmill_proof_audit).

Evidence basis (NOT decoration; this is what makes the contract load-bearing):
H32 free-form synthesis = 0.33 accuracy. H34 typed residual-class + source-cue
check + deterministic lowering = 1.0 accuracy. H37 closed-menu forcing hurts
at the boundary; open_set_refusal_status is required.
"""
from __future__ import annotations
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict, is_dataclass


SOLVER_CONTRACT_SCHEMA = "leanmill-solver-action-contract-v1"
DEFAULT_PROVER_CHAIN = ("native_hammer", "claude_opus_warm", "cold_shot_fanout")
DEFAULT_ANTI_PATTERNS = (
    "lean_closure_laundering",
    "gold_name_verbatim_confirmed",
    "single_lemma_exact_confirmed",
    "paraphrase_of_existing_mathlib_lemma",
    "scientific_amnesia",
    "tool_underuse_formal_satisficing",
    "category_conflation_strawman_shift",
    "premature_settled_negative",
    "vocabulary_chain_laundering",
)


def ratification_mnc_contract_projection() -> dict:
    """Contract text for the carried-artifact matched control.

    The executable verifier lives in ``proof_margin_of_safety``.  This
    projection is the single source for the contract bytes embedded by both
    solver builders, so certificates cannot describe the context-stripped
    search control while executing the source-aware ratification control.
    """

    return {
        "mode": "source_aware_conclusion_perturbation",
        "program_counter_condition": (
            "the source-aware matched control has status=pass, passed=true, "
            "and discriminating=true"
        ),
        "acceptance_check": (
            "Using the exact carried posed/closure source, preserve the "
            "namespace-qualified target identity, inherited declaration "
            "context, binders, and proof body. The positive target C must "
            "compile; replacing only C by ¬(C) must fail to compile. Accept "
            "only status=pass, passed=true, discriminating=true; "
            "status=inconclusive does not satisfy ratification."
        ),
        "reject_or_repair_behavior": {
            "matched_negative_control_pass": (
                "PROCEED past this receipt only when the calibrated positive "
                "compiles and the same proof fails on C → ¬(C)."
            ),
            "matched_negative_control_fail": (
                "REJECT ratification: the same proof closes both C and ¬(C) "
                "in the inherited context (zero differential)."
            ),
            "matched_negative_control_inconclusive": (
                "REJECT ratification with rejected_mnc_inconclusive; an "
                "unavailable, malformed, mismatched, or timed-out control "
                "cannot earn proof credit."
            ),
        },
    }


def source_cue_check(row: dict) -> dict:
    """Deterministic pre-execution check: does this row supply the cues a
    kernel-trust prover stack needs to run (file exists, goal parseable,
    target resolvable)? H34/H42 evidence: deterministic source-cue receipts
    before lowering are what take free-form synthesis from 0.33 to 1.0.
    """
    cues, missing = [], []
    src_str = row.get("source_file") or ""
    if src_str and Path(src_str).exists():
        cues.append("source_file_exists")
    else:
        missing.append("source_file_missing_or_nonexistent")
    if (row.get("goal") or "").strip():
        cues.append("goal_text_present")
    else:
        missing.append("goal_text_empty")
    if row.get("target_theorem_name"):
        cues.append("target_theorem_name_present")
    else:
        missing.append("target_theorem_name_missing")
    return {
        "source_cue_check_status": "passed" if not missing else "failed",
        "source_cue_receipts": cues,
        "missing_source_cues": missing,
    }


def build_solver_action_contract(row: dict, lean_root: Path, repo: Path) -> dict:
    """Build the upstream typed action contract for one solver row.

    Args:
        row: slice row with row_id, goal, source_file, target_theorem_name, sub_area
        lean_root: the Lean project root the audit will run against
        repo: repository root (needed to import RD modules)
    """
    target_name = row.get("target_theorem_name") or ""
    goal_excerpt = (row.get("goal") or "").strip()[:480]
    cue_result = source_cue_check(row)
    ratification_only = bool(row.get("_preverified_only"))
    ratification_mnc = (
        ratification_mnc_contract_projection() if ratification_only else None
    )
    action_program = [
        "layer2_native_hammer_cascade",
        "layer3_warm_agent_iterate",
        "layer4_cold_shot_multi_provider",
        "layer5_validate_against_contract",
    ]
    pattern_chain: list[str] = list(DEFAULT_PROVER_CHAIN)
    rd_evidence_basis = "local_default"
    try:
        if str(repo / "src") not in sys.path:
            sys.path.insert(0, str(repo / "src"))
        from ztare.research_director.pattern_action_contract import (  # type: ignore
            build_pattern_action_contract,
        )
        rd_contract = build_pattern_action_contract(
            scope="solver_lane_no_positive_family_template",
            goal_excerpt=goal_excerpt,
        )
        rd_dict = asdict(rd_contract) if is_dataclass(rd_contract) else (
            rd_contract if isinstance(rd_contract, dict) else {})
        rd_pattern_chain = list(rd_dict.get("pattern_chain") or [])
        if rd_pattern_chain:
            pattern_chain = rd_pattern_chain
            rd_evidence_basis = "rd_pattern_action_contract"
    except Exception:
        pass

    # RD primitive_tick_surface query: pull relevance-ranked primitives.
    rd_primitive_hits: list[dict] = []
    try:
        if str(repo / "src") not in sys.path:
            sys.path.insert(0, str(repo / "src"))
        from ztare.research_director.primitive_tick_surface import (  # type: ignore
            build_primitive_tick_surface,
        )
        raw = f"{target_name} {goal_excerpt} {row.get('sub_area') or ''}".lower()
        tokens = [
            t for t in "".join(ch if ch.isalnum() else " " for ch in raw).split()
            if len(t) >= 3
        ]
        seen, query_terms = set(), []
        for t in tokens:
            if t not in seen:
                seen.add(t); query_terms.append(t)
            if len(query_terms) >= 16:
                break
        if query_terms:
            surface = build_primitive_tick_surface(query_terms=query_terms, top_n=6, per_bucket=2)
            for hit in (surface.top_hits or []):
                rd_primitive_hits.append({
                    "id": hit.id, "kind": hit.kind, "score": hit.score,
                    "why": hit.why, "description": hit.description,
                })
    except Exception:
        pass

    return {
        "schema": SOLVER_CONTRACT_SCHEMA,
        "generated_at_epoch": int(time.time()),
        "row_id": row.get("row_id"),
        "target_theorem_name": target_name,
        "ratification_only": ratification_only,
        "matched_negative_control_mode": (
            ratification_mnc["mode"] if ratification_mnc else "context_stripped"
        ),
        "source_file": row.get("source_file"),
        "scope": "solver_lane_no_positive_family_template",
        "goal_excerpt": goal_excerpt,
        "requested_residual_class": "no_positive_family_template_closure",
        "accepted_residual_class": (
            "no_positive_family_template_closure"
            if cue_result["source_cue_check_status"] == "passed"
            else "outside_menu_source_cues_missing"
        ),
        "source_cue_check_status": cue_result["source_cue_check_status"],
        "source_cue_receipts": cue_result["source_cue_receipts"],
        "missing_source_cues": cue_result["missing_source_cues"],
        "rejected_nearest_confuser": (
            "pde_estimate_or_carrier_residual (rejected: target is not a PDE inequality)"
        ),
        "pattern_chain": pattern_chain,
        "anti_patterns": list(DEFAULT_ANTI_PATTERNS),
        "evidence_basis": rd_evidence_basis,
        "rd_primitive_hits": rd_primitive_hits,
        "action_program": action_program,
        "current_action_index": 0,
        "required_next_action": action_program[0],
        "program_counter_rule": (
            "advance current_action_index only after the current action has emitted "
            "its receipt; if the receipt is `closed` AND "
            + (
                ratification_mnc["program_counter_condition"]
                if ratification_mnc else
                "matched_negative_control passes"
            )
            + ", stop (credit_ready_at_solver_layer = true). Otherwise continue "
            "to the next action_program step until exhausted or stop_condition fires."
        ),
        "stop_condition": (
            "stop on first credit_ready_at_solver_layer = true; or when "
            "action_program is exhausted (last action's receipt recorded); or when "
            "the row exceeds MAX_FAILED_ATTEMPTS_PER_ROW across cycles (cooldown)."
        ),
        "required_receipts": [
            {
                "name": "kernel_compile_receipt",
                "required": True,
                "acceptance_check": "lake env lean over the enriched probe returns exit 0 with no error: lines.",
            },
            {
                "name": "matched_negative_control_receipt",
                "required": True,
                "acceptance_check": (
                    ratification_mnc["acceptance_check"]
                    if ratification_mnc else
                    "the same proof_text under bare `import Mathlib` (gold-bearing prelude STRIPPED) FAILS to compile. A negative-control PASS = leakage."
                ),
            },
            {
                "name": "axiom_allowlist_receipt",
                "required": True,
                "acceptance_check": "axioms ⊆ {propext, Classical.choice, Quot.sound}.",
                "deferred_to": "leanmill_proof_audit",
            },
            {
                "name": "l3_anti_pattern_receipt",
                "required": True,
                "acceptance_check": "v33 deep verifier returns no confirmed blocker.",
                "deferred_to": "leanmill_proof_audit",
            },
        ],
        "reject_or_repair_behavior": {
            "kernel_compile_fail": "advance to next action_program step; if exhausted, mark row failed_compile.",
            **(
                ratification_mnc["reject_or_repair_behavior"]
                if ratification_mnc else
                {"matched_negative_control_pass": "REJECT closure as leakage/laundering; do not credit."}
            ),
            "axiom_outside_allowlist": "REJECT closure.",
            "l3_confirmed_blocker": "REJECT closure; record the specific blocker class.",
            "clean_proceed_condition": "all required_receipts at solver_layer must pass AND downstream_consumer_check must accept.",
        },
        "downstream_consumer_check": (
            "leanmill_proof_audit emits a typed receipt that governance consumes; "
            "only payloads with all receipts passing become unratified_closure_candidate typed exits."
        ),
        "credit_boundary": "advisory_only_no_factory_credit",
    }


# NOTE: `verify_matched_negative_control` + `validate_against_contract` were REMOVED 2026-06-23 —
# both were dead/superseded (the typeless-stub MNC RCA'd 2026-06-18) with no live caller. The canonical,
# goal-type-aware MNC + contract validation live in `solver_core._verify_matched_negative_control` /
# `solver_core._validate_against_contract`. Removing the siblings kills the dup-class at the source.
