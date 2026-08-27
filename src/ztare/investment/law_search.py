"""Typed recursive search for future-dated investment-law conjectures."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
from statistics import mean
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import bh_fdr, spearman_rho
from ztare.strategy import (
    CandidateEvaluation,
    FrontierScope,
    Neighborhood,
    OperatorGrammar,
    Program,
    RepresentationAudit,
    TypedOperator,
    TypedTerminal,
    compile_jaggedthoughts_frontier,
    enumerate_typed_programs,
)


LAW_SEARCH_SCHEMA = "jaggedthoughts-investment-law-search-v1"
LAW_SEARCH_POLICY_VERSION = "3"
_LAW_SCHEMA = "jaggedthoughts-investment-law-candidate-v1"
_OUTCOME = "active_return"


def _law_inputs(law: Mapping[str, Any]) -> set[str]:
    nodes = (law.get("predictor_program") or {}).get("nodes") or ()
    produced = {str(row.get("metric_id") or "") for row in nodes}
    return {
        str(argument.get("metric"))
        for row in nodes
        for argument in row.get("arguments") or ()
        if isinstance(argument, Mapping)
        and argument.get("metric")
        and str(argument.get("metric")) not in produced
    }


def _select_features(
    episodes: Sequence[Mapping[str, Any]], laws: Sequence[Mapping[str, Any]],
    entity_kind: str, cap: int,
) -> list[str]:
    rows = [row for row in episodes if row.get("entity_kind") == entity_kind]
    coverage: Counter[str] = Counter()
    values: dict[str, set[float]] = defaultdict(set)
    for row in rows:
        roles = row.get("metric_roles") or {}
        eligible = set(roles.get("predictor_metric_ids") or (row.get("metrics") or {}))
        for metric_id in eligible:
            value = (row.get("metrics") or {}).get(metric_id)
            if isinstance(value, (int, float)) and math.isfinite(float(value)):
                coverage[str(metric_id)] += 1
                values[str(metric_id)].add(float(value))
    minimum = min(4, len(rows))
    available = {
        metric_id for metric_id, count in coverage.items()
        if count >= minimum
        and (len(rows) == 1 or len(values[metric_id]) >= 2)
        and metric_id != _OUTCOME
    }
    inherited = sorted({
        metric_id
        for law in laws
        if entity_kind in (law.get("cohort") or {}).get("entity_kinds", ())
        for metric_id in _law_inputs(law)
        if metric_id in available
    })
    ranked = sorted(
        available - set(inherited),
        key=lambda metric_id: (-coverage[metric_id], -len(values[metric_id]), metric_id),
    )
    return (inherited + ranked)[:cap]


def _grammar(entity_kind: str, features: Sequence[str]) -> OperatorGrammar:
    return OperatorGrammar(
        grammar_id=f"jaggedthoughts-law-search:{entity_kind}",
        version="1",
        terminals=tuple(
            TypedTerminal(metric_id, "feature", description=f"Point-in-time metric {metric_id}.")
            for metric_id in features
        ),
        operators=(
            TypedOperator("identity_feature", ("feature",), "score"),
            TypedOperator("negative_feature", ("feature",), "score"),
            TypedOperator("multiply_features", ("feature", "feature"), "score", commutative=True),
            TypedOperator("spread_features", ("feature", "feature"), "score"),
            TypedOperator("multiply_score_feature", ("score", "feature"), "score"),
        ),
    )


def _value(program: Program, metrics: Mapping[str, Any]) -> float | None:
    if program.terminal_id is not None:
        value = metrics.get(program.terminal_id)
        return float(value) if isinstance(value, (int, float)) and math.isfinite(float(value)) else None
    children = [_value(child, metrics) for child in program.children]
    if any(value is None for value in children):
        return None
    values = [float(value) for value in children if value is not None]
    value = {
        "identity_feature": lambda: values[0],
        "negative_feature": lambda: -values[0],
        "multiply_features": lambda: values[0] * values[1],
        "spread_features": lambda: values[0] - values[1],
        "multiply_score_feature": lambda: values[0] * values[1],
    }[str(program.operator_id)]()
    return value if math.isfinite(value) else None


def _complexity(program: Program) -> int:
    return 1 + sum(_complexity(child) for child in program.children)


def _block_correlations(
    program: Program, episodes: Sequence[Mapping[str, Any]], minimum_cross_section: int,
) -> list[dict[str, Any]]:
    blocks: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    for row in episodes:
        if row.get("settlement_status") != "settled":
            continue
        predictor = _value(program, row.get("metrics") or {})
        outcome = (row.get("metrics") or {}).get(_OUTCOME)
        if predictor is None or not isinstance(outcome, (int, float)):
            continue
        blocks[str(row["inference_block_id"])].append(
            (predictor, float(outcome), str(row["opened_at"]))
        )
    result = []
    for block_id, rows in sorted(blocks.items()):
        if len(rows) < minimum_cross_section:
            continue
        rho = spearman_rho([row[0] for row in rows], [row[1] for row in rows])
        if rho is not None:
            result.append({
                "inference_block_id": block_id,
                "opened_at": max(row[2] for row in rows),
                "episode_count": len(rows),
                "rho": rho,
            })
    return sorted(result, key=lambda row: (row["opened_at"], row["inference_block_id"]))


def _chronological_partition(
    episodes: Sequence[Mapping[str, Any]], minimum_blocks: int,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    opened_by_block: dict[str, str] = {}
    for row in episodes:
        block_id = str(row["inference_block_id"])
        opened_by_block[block_id] = max(
            str(row["opened_at"]), opened_by_block.get(block_id, ""),
        )
    blocks = tuple(sorted(opened_by_block, key=lambda key: (opened_by_block[key], key)))
    holdout_count = max(1, math.ceil(len(blocks) * 0.25)) if len(blocks) >= minimum_blocks else 0
    return (
        blocks[:-holdout_count] if holdout_count else blocks,
        blocks[-holdout_count:] if holdout_count else (),
    )


def _sign_flip_p(values: Sequence[float]) -> float | None:
    """Exact two-sided sign-flip p-value for the small discovery block set."""

    if not values or len(values) > 16:
        return None
    observed = abs(mean(values))
    extreme = 0
    total = 1 << len(values)
    for mask in range(total):
        trial = mean(value if mask & (1 << index) else -value for index, value in enumerate(values))
        extreme += abs(trial) >= observed - 1e-12
    return extreme / total


def _formula(program: Program) -> str:
    if program.terminal_id is not None:
        return program.terminal_id
    children = [_formula(child) for child in program.children]
    if program.operator_id == "identity_feature":
        return children[0]
    if program.operator_id == "negative_feature":
        return f"-({children[0]})"
    symbol = "−" if program.operator_id == "spread_features" else "×"
    return f"({children[0]} {symbol} {children[1]})"


def _signal_program(program: Program) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    emitted: set[str] = set()
    operator = {
        "identity_feature": "identity",
        "negative_feature": "negative",
        "multiply_features": "multiply",
        "spread_features": "spread",
        "multiply_score_feature": "multiply",
    }

    def emit(node: Program) -> str:
        if node.terminal_id is not None:
            return node.terminal_id
        metric_id = f"abduced_{node.program_id[:16]}"
        arguments = [{"metric": emit(child)} for child in node.children]
        if metric_id not in emitted:
            nodes.append({
                "metric_id": metric_id,
                "operator": operator[str(node.operator_id)],
                "arguments": arguments,
                "unit": "decimal",
                "description": f"Grammar-abduced score: {_formula(node)}.",
            })
            emitted.add(metric_id)
        return metric_id

    output = emit(program)
    return {"output_metric_id": output, "nodes": nodes}


def _proposal(
    program: Program, entity_kind: str, horizons: Sequence[int], direction: str,
    generated_at: str, receipt: Mapping[str, Any],
) -> dict[str, Any]:
    formula = _formula(program)
    antecedents = sorted({
        node.terminal_id for node in _walk(program) if node.terminal_id is not None
    })
    return {
        "schema": _LAW_SCHEMA,
        "law_id": f"abduced-{entity_kind.replace('_', '-')}-{program.program_id[:16]}",
        "version": "1",
        "name": f"Abduced {formula}",
        "question": f"Does {formula} rank later benchmark-relative return?",
        "created_at": generated_at,
        "not_before": generated_at,
        "origin": "typed_recursive_law_search",
        "estimator": {"kind": "rank_association", "expected_direction": direction},
        "cohort": {
            "entity_kinds": [entity_kind],
            "horizon_days": sorted(set(int(value) for value in horizons)),
            "conditions": [],
            "evaluation_environments": ["horizon_days"],
            "counterexample_fields": [
                "industry_id", "quality_band", "expectations_band", "momentum_regime",
            ],
        },
        "predictor_program": _signal_program(program),
        "outcome_metric_id": _OUTCOME,
        "mechanism": {
            "antecedent_concepts": antecedents,
            "consequence_concept": _OUTCOME,
            "kind": "predictive",
        },
        "decision_use": "paper_candidate_ranking",
        "validation": {
            "target_rho": 0.30, "alpha": 0.05, "power": 0.80,
            "minimum_cross_section": 4, "minimum_inference_blocks": 8,
            "holdout_fraction": 0.25, "counterexample_minimum_rows": 4,
            "counterexample_minimum_blocks": 2, "counterexample_abs_rho": 0.20,
        },
        "trial_family_id": "grammar-abduced-cross-sectional-laws-v1",
        "authority": "diagnostic_and_prospective_shadow",
        "generation_receipt": dict(receipt),
    }


def _walk(program: Program) -> tuple[Program, ...]:
    return (program, *(node for child in program.children for node in _walk(child)))


def _search_kind(
    episodes: Sequence[Mapping[str, Any]], laws: Sequence[Mapping[str, Any]], entity_kind: str,
    generated_at: str, *, feature_cap: int, max_depth: int, max_programs: int,
    minimum_cross_section: int, minimum_blocks: int, minimum_directional_ic: float,
    max_new_laws: int,
) -> dict[str, Any]:
    local = [row for row in episodes if row.get("entity_kind") == entity_kind]
    training_ids, holdout_ids = _chronological_partition(local, minimum_blocks)
    training_set, holdout_set = set(training_ids), set(holdout_ids)
    training_rows = [row for row in local if str(row["inference_block_id"]) in training_set]
    holdout_rows = [row for row in local if str(row["inference_block_id"]) in holdout_set]
    features = _select_features(training_rows, laws, entity_kind, feature_cap)
    if not features:
        return {"entity_kind": entity_kind, "status": "awaiting_predictor_metrics", "features": []}
    grammar = _grammar(entity_kind, features)
    enumeration = enumerate_typed_programs(grammar, max_depth=max_depth, max_programs=max_programs)
    programs = enumeration.programs_of_type("score")
    evidence_epoch = stable_sha256(sorted(
        str(row["phenotype_episode_sha256"]) for row in training_rows
    ))
    holdout_epoch = stable_sha256(sorted(
        str(row["phenotype_episode_sha256"]) for row in holdout_rows
    )) if holdout_rows else None
    rows = []
    evaluations = []
    for program in programs:
        training = _block_correlations(program, training_rows, minimum_cross_section)
        holdout = _block_correlations(program, holdout_rows, minimum_cross_section)
        train_mean = mean(row["rho"] for row in training) if training else None
        direction = 1 if train_mean is None or train_mean >= 0 else -1
        holdout_mean = mean(row["rho"] for row in holdout) if holdout else None
        train_score = direction * train_mean if train_mean is not None else -2.0
        coverage = len(training) / len(training_ids) if training_ids else 0.0
        objectives = (train_score, coverage, -float(_complexity(program)))
        row = {
            "program_id": program.program_id,
            "formula": _formula(program),
            "direction": "positive" if direction > 0 else "negative",
            "block_count": len(training) + len(holdout),
            "training_block_count": len(training),
            "holdout_block_count": len(holdout),
            "training_mean_rho": train_mean,
            "holdout_mean_rho": holdout_mean,
            "holdout_pass": (
                train_mean is not None and holdout_mean is not None
                and direction * train_mean >= minimum_directional_ic
                and direction * holdout_mean >= minimum_directional_ic
            ),
            "discovery_p_value": _sign_flip_p([float(item["rho"]) for item in training]),
            "objectives": objectives,
            "complexity": _complexity(program),
        }
        rows.append(row)
        evaluations.append(CandidateEvaluation(
            program_id=program.program_id,
            objective_values=objectives,
            behavior_signature=(program.program_id,),
            evidence_refs=(f"phenotype-set:{evidence_epoch}",),
        ))
    neighborhood = Neighborhood(
        neighborhood_id=f"law-search-edits:{entity_kind}:v1",
        edges=tuple(
            (child.program_id, program.program_id)
            for program in programs for child in program.children
            if child.output_type == "score"
        ),
    )
    scope = FrontierScope(
        grammar_id=grammar.grammar_id, grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest, target_type="score",
        max_depth=max_depth, max_programs=max_programs,
        evaluation_model_id="training-only-chronological-block-ic-v2", landscape_mode="fixed",
        evidence_epoch=evidence_epoch,
        objective_names=("training_directional_ic", "training_block_coverage", "simplicity"),
        neighborhood_id=neighborhood.neighborhood_id,
    )
    audit = RepresentationAudit(
        audit_id=f"law-search-grammar:{grammar.grammar_digest}",
        status="passed" if enumeration.exhausted_within_scope else "residual",
        residuals=() if enumeration.exhausted_within_scope else ("program_budget_exhausted",),
        evidence_refs=(f"grammar:{grammar.grammar_digest}",) if enumeration.exhausted_within_scope else (),
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope, enumeration=enumeration, evaluations=evaluations,
        neighborhood=neighborhood, representation_audit=audit,
    )
    by_id = {row["program_id"]: row for row in rows}
    fdr_rows = bh_fdr(
        [(row["program_id"], row["discovery_p_value"]) for row in rows if row["discovery_p_value"] is not None],
        alpha=0.05,
    )
    fdr = {row["label"]: row for row in fdr_rows}
    prior_program_ids = {
        str((law.get("generation_receipt") or {}).get("program_id") or "") for law in laws
    }
    frozen_selection = sorted(
        (
            by_id[program_id] for program_id in certificate.frontier_program_ids
            if by_id[program_id]["training_block_count"] == len(training_ids)
            and abs(float(by_id[program_id]["training_mean_rho"])) >= minimum_directional_ic
            and program_id not in prior_program_ids
        ),
        key=lambda row: tuple(-float(value) for value in row["objectives"]),
    )[:max_new_laws]
    selection_contract = {
        "schema": "jaggedthoughts-frozen-law-selection-v1",
        "entity_kind": entity_kind,
        "training_evidence_epoch": evidence_epoch,
        "training_block_ids": list(training_ids),
        "holdout_block_ids": list(holdout_ids),
        "program_ids": [row["program_id"] for row in frozen_selection],
        "grammar_digest": grammar.grammar_digest,
        "enumeration_digest": enumeration.enumeration_digest,
        "frontier_certificate_sha256": certificate.certificate_sha256,
    }
    selection_contract = {
        **selection_contract,
        "selection_sha256": stable_sha256(selection_contract),
    }
    selected = [row for row in frozen_selection if row["holdout_pass"]]
    program_by_id = {program.program_id: program for program in programs}
    proposals = []
    for row in selected:
        receipt = {
            "schema": "jaggedthoughts-law-generation-receipt-v1",
            "program_id": row["program_id"],
            "grammar_digest": grammar.grammar_digest,
            "enumeration_digest": enumeration.enumeration_digest,
            "frontier_certificate_sha256": certificate.certificate_sha256,
            "selection_evidence_epoch": evidence_epoch,
            "selection_block_count": row["training_block_count"],
            "selection_sha256": selection_contract["selection_sha256"],
            "holdout_evidence_epoch": holdout_epoch,
            "holdout_block_count": row["holdout_block_count"],
            "discovery_p_value": row["discovery_p_value"],
            "discovery_fdr": fdr.get(row["program_id"]),
            "activation_rule": "Only episodes opened after generated_at may evaluate this law.",
        }
        proposals.append(_proposal(
            program_by_id[row["program_id"]], entity_kind,
            [int(item["horizon_days"]) for item in local], row["direction"], generated_at, receipt,
        ))
    status = (
        "future_laws_generated" if proposals
        else "awaiting_settled_inference_blocks"
        if not holdout_ids
        else "sealed_holdout_rejected_frozen_programs"
        if frozen_selection
        else "training_frontier_has_no_directionally_stable_program"
    )
    return {
        "entity_kind": entity_kind,
        "status": status,
        "features": features,
        "settled_inference_block_floor": minimum_blocks,
        "minimum_directional_information_coefficient": minimum_directional_ic,
        "maximum_scored_block_count": max((row["block_count"] for row in rows), default=0),
        "chronological_partition": {
            "training_block_ids": list(training_ids),
            "holdout_block_ids": list(holdout_ids),
            "training_evidence_epoch": evidence_epoch,
            "holdout_evidence_epoch": holdout_epoch,
        },
        "grammar": grammar.to_dict(),
        "enumeration": {
            "program_count": len(enumeration.programs),
            "score_program_count": len(programs),
            "max_depth": max_depth,
            "max_programs": max_programs,
            "exhausted_within_scope": enumeration.exhausted_within_scope,
            "residuals": [row.to_dict() for row in enumeration.residuals],
            "enumeration_digest": enumeration.enumeration_digest,
        },
        "frontier": {
            "certificate_sha256": certificate.certificate_sha256,
            "frontier_program_ids": list(certificate.frontier_program_ids),
            "local_peak_count": len(certificate.local_peak_program_ids),
            "sample_local_peak_program_ids": list(certificate.local_peak_program_ids[:20]),
            "dominated_count": len(certificate.dominated),
            "scope_closed": certificate.scope_closed,
            "decision_closed": certificate.decision_closed,
            "evidence_ready": bool(holdout_ids),
            "closure_boundary": (
                "Closure covers the training-only grammar and objectives. The holdout can "
                "reject frozen programs but cannot select a replacement or establish economic validity."
            ),
        },
        "frozen_selection": selection_contract,
        "selected_diagnostics": selected,
        "proposals": proposals,
        "selection_sample_authority": "conjecture_generation_only",
        "capital_authority": False,
    }


def search_law_programs(
    episodes: Sequence[Mapping[str, Any]], laws: Sequence[Mapping[str, Any]], generated_at: str,
    *, feature_cap: int = 5, max_depth: int = 2, max_programs: int = 400,
    minimum_cross_section: int = 4, minimum_blocks: int = 8,
    minimum_directional_ic: float = 0.15, max_new_laws: int = 3,
) -> dict[str, Any]:
    """Enumerate, frontier-close, and future-date bounded law conjectures."""

    if not 0 <= minimum_directional_ic <= 1:
        raise ValueError("minimum_directional_ic must be in [0, 1]")
    entity_kinds = sorted({str(row.get("entity_kind")) for row in episodes if row.get("entity_kind")})
    searches = [
        _search_kind(
            episodes, laws, entity_kind, generated_at,
            feature_cap=feature_cap, max_depth=max_depth, max_programs=max_programs,
            minimum_cross_section=minimum_cross_section, minimum_blocks=minimum_blocks,
            minimum_directional_ic=minimum_directional_ic,
            max_new_laws=max_new_laws,
        )
        for entity_kind in entity_kinds
    ]
    proposals = [proposal for search in searches for proposal in search.get("proposals") or ()]
    body = {
        "schema": LAW_SEARCH_SCHEMA,
        "generated_at": generated_at,
        "searches": searches,
        "proposal_count": len(proposals),
        "proposals": proposals,
        "policy": {
            "version": LAW_SEARCH_POLICY_VERSION,
            "feature_cap": feature_cap, "max_depth": max_depth, "max_programs": max_programs,
            "minimum_cross_section": minimum_cross_section, "minimum_blocks": minimum_blocks,
            "minimum_directional_ic": minimum_directional_ic,
            "max_new_laws_per_entity_kind": max_new_laws,
            "historical_selection": "training_only_then_frozen_before_holdout_veto",
        },
        "boundary": (
            "A chronological holdout may reject the frozen training-selected programs but cannot "
            "choose a replacement. The historical sample may generate a conjecture only; each "
            "proposal starts afterward and needs later evidence before any policy review."
        ),
        "capital_authority": False,
    }
    return {**body, "law_search_sha256": stable_sha256(body)}


__all__ = ["LAW_SEARCH_POLICY_VERSION", "LAW_SEARCH_SCHEMA", "search_law_programs"]
