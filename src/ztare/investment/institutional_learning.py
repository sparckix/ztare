"""Cohort phenotypes and counterexample-guided investment-law learning.

The module adapts the world-model learning loop to finance without importing
grid or puzzle vocabulary.  Point-in-time forecast packets are observations;
the existing signal AST expresses conjectured predictors; exact market-date
blocks carry inference identity; later outcomes challenge the conjectures.

An investment "law" is always a versioned, domain-bounded regularity.  It is
never a universal theorem and it never receives capital authority here.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import random
from statistics import NormalDist, mean, stdev
from typing import Any, Iterable, Mapping, Sequence

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue
from ztare.experiment_stats import (
    bh_fdr,
    n_required_for_rho,
    ols_multichannel_r2,
    paired_permutation_test,
    power_aware_verdict,
    spearman_rho,
    spearman_rho_with_ci,
)
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .contracts import (
    MetricObservation, canonical_timestamp, require_finite, require_text, timestamp_key,
)
from .closed_book import CLOSED_BOOK_RUN_SCHEMA
from .company_quality import (
    compile_company_quality_histories,
    compile_company_quality_histories_from_observations,
    compile_company_quality_history,
)
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore
from .research_memory import candidate_strategy_phenotype
from .law_search import search_law_programs
from .signals import SIGNAL_OPERATOR_CONTRACT, SignalDefinition, derive_signals_partial
from .strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_MOVE_LIBRARY_SCHEMA,
    compile_strategy_phenotype_projection_frontier,
    resolve_strategy_cohort_results,
)
from .strategy_event_refinement import compile_interval_treatment_period_frontier


LAW_CATALOG_SCHEMA = "jaggedthoughts-investment-law-catalog-v1"
LAW_CANDIDATE_SCHEMA = "jaggedthoughts-investment-law-candidate-v1"
PHENOTYPE_EPISODE_SCHEMA = "jaggedthoughts-investment-phenotype-episode-v1"
COHORT_PHENOTYPE_SCHEMA = "jaggedthoughts-investment-cohort-phenotype-v1"
LAW_EVALUATION_SCHEMA = "jaggedthoughts-investment-law-evaluation-v1"
LEARNING_STATE_SCHEMA = "jaggedthoughts-institutional-learning-state-v1"
CAUSAL_PANEL_ROW_SCHEMA = "jaggedthoughts-causal-panel-row-v2"
LAW_POLICY_INFLUENCE_SCHEMA = "jaggedthoughts-law-policy-influence-v1"
STRATEGY_REGULARITY_SCHEMA = "jaggedthoughts-strategy-regularity-evidence-v1"
HISTORICAL_ACCOUNTING_REPLAY_SCHEMA = "jaggedthoughts-historical-accounting-replay-v1"
INSTITUTIONAL_LEARNING_ENGINE_VERSION = "2026-08-13.strategy-effect-contract-v5"
STRATEGY_LAW_COMPILER_AVAILABLE_AT = "2026-08-13T13:40:01Z"

_ASSOCIATION = "rank_association"
_DID = "difference_in_differences"
_NUMERIC_OPERATORS = {"gt", "ge", "lt", "le"}
_ALL_OPERATORS = _NUMERIC_OPERATORS | {"eq", "ne"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _next_epoch(prior: Any) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if prior:
        text = str(prior)
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
        now = max(now, parsed.astimezone(timezone.utc) + timedelta(seconds=1))
    return now.isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def default_law_catalog() -> dict[str, Any]:
    """Return the small editable seed catalog; the engine learns its scope."""

    common_validation = {
        "target_rho": 0.30,
        "alpha": 0.05,
        "power": 0.80,
        "minimum_cross_section": 4,
        "minimum_inference_blocks": 8,
        "holdout_fraction": 0.25,
        "counterexample_minimum_rows": 4,
        "counterexample_minimum_blocks": 2,
        "counterexample_abs_rho": 0.20,
    }
    equity_cohort = {
        "entity_kinds": ["public_equity"],
        "horizon_days": [21, 90],
        "conditions": [],
        "evaluation_environments": ["horizon_days"],
        "counterexample_fields": [
            "industry_id", "quality_band", "expectations_band", "momentum_regime",
        ],
    }
    return {
        "schema": LAW_CATALOG_SCHEMA,
        "version": "4",
        "updated_at": "2026-08-13T12:49:35Z",
        "purpose": (
            "Seed domain-bounded conjectures; counterexamples may narrow their future "
            "cohorts but cannot rewrite prior evidence."
        ),
        "candidates": [
            {
                "schema": LAW_CANDIDATE_SCHEMA,
                "law_id": "value-quality-predicts-active-return",
                "version": "4",
                "name": "Value × quality",
                "question": (
                    "Within a comparable public-equity opportunity set, does quality-adjusted "
                    "price-implied excess return rank later benchmark-relative return?"
                ),
                "created_at": "2026-08-13T12:49:35Z",
                "not_before": "2026-08-13T12:49:35Z",
                "origin": "jaggedthoughts_seed",
                "estimator": {"kind": _ASSOCIATION, "expected_direction": "positive"},
                "cohort": equity_cohort,
                "predictor_program": {
                    "output_metric_id": "law_value_quality_score",
                    "nodes": [{
                        "metric_id": "law_value_quality_score",
                        "operator": "multiply",
                        "arguments": [
                            {"metric": "earnings_durability"},
                            {"metric": "price_implied_excess_return"},
                        ],
                        "unit": "decimal",
                        "description": "Quality multiplied by price-implied excess return.",
                    }],
                },
                "outcome_metric_id": "active_return",
                "mechanism": {
                    "antecedent_concepts": ["earnings_durability", "price_implied_excess_return"],
                    "consequence_concept": "active_return",
                    "kind": "predictive",
                },
                "decision_use": "paper_candidate_ranking",
                "validation": common_validation,
                "trial_family_id": "fundamental-cross-sectional-laws-v1",
                "authority": "diagnostic_and_prospective_shadow",
            },
            {
                "schema": LAW_CANDIDATE_SCHEMA,
                "law_id": "low-expectations-durable-earnings",
                "version": "4",
                "name": "Low expectations × durable earnings",
                "question": (
                    "Do companies combining durable earnings with lower price-implied growth "
                    "rank later benchmark-relative return?"
                ),
                "created_at": "2026-08-13T12:49:35Z",
                "not_before": "2026-08-13T12:49:35Z",
                "origin": "jaggedthoughts_seed",
                "estimator": {"kind": _ASSOCIATION, "expected_direction": "positive"},
                "cohort": equity_cohort,
                "predictor_program": {
                    "output_metric_id": "law_low_expectations_quality_score",
                    "nodes": [
                        {
                            "metric_id": "law_negative_implied_growth",
                            "operator": "negative",
                            "arguments": [{"metric": "implied_growth"}],
                            "unit": "decimal",
                            "description": "Lower price-implied growth receives a higher score.",
                        },
                        {
                            "metric_id": "law_low_expectations_quality_score",
                            "operator": "multiply",
                            "arguments": [
                                {"metric": "earnings_durability"},
                                {"metric": "law_negative_implied_growth"},
                            ],
                            "unit": "decimal",
                            "description": "Durable earnings multiplied by low expectations.",
                        },
                    ],
                },
                "outcome_metric_id": "active_return",
                "mechanism": {
                    "antecedent_concepts": ["earnings_durability", "implied_growth"],
                    "consequence_concept": "active_return",
                    "kind": "predictive",
                },
                "decision_use": "paper_candidate_ranking",
                "validation": common_validation,
                "trial_family_id": "fundamental-cross-sectional-laws-v1",
                "authority": "diagnostic_and_prospective_shadow",
            },
            {
                "schema": LAW_CANDIDATE_SCHEMA,
                "law_id": "fund-net-yield-after-factor-price",
                "version": "4",
                "name": "Fund net yield after factor price",
                "question": (
                    "Among comparable public funds, does portfolio net earnings yield add "
                    "benchmark-relative return beyond priced factor exposure?"
                ),
                "created_at": "2026-08-13T12:49:35Z",
                "not_before": "2026-08-13T12:49:35Z",
                "origin": "jaggedthoughts_seed",
                "estimator": {"kind": _ASSOCIATION, "expected_direction": "positive"},
                "cohort": {
                    "entity_kinds": ["public_fund"],
                    "horizon_days": [90],
                    "conditions": [],
                    "evaluation_environments": ["horizon_days"],
                    "counterexample_fields": ["fund_category", "value_beta_band"],
                },
                "predictor_program": {
                    "output_metric_id": "law_fund_net_yield_residual_score",
                    "nodes": [{
                        "metric_id": "law_fund_net_yield_residual_score",
                        "operator": "subtract",
                        "arguments": [
                            {"metric": "portfolio_net_earnings_yield"},
                            {"metric": "factor_implied_return"},
                        ],
                        "unit": "decimal",
                        "description": "Net portfolio earnings yield less factor-implied return.",
                    }],
                },
                "outcome_metric_id": "active_return",
                "mechanism": {
                    "antecedent_concepts": ["portfolio_net_earnings_yield", "factor_implied_return"],
                    "consequence_concept": "active_return",
                    "kind": "predictive",
                },
                "decision_use": "paper_fund_ranking",
                "validation": common_validation,
                "trial_family_id": "fundamental-cross-sectional-laws-v1",
                "authority": "diagnostic_and_prospective_shadow",
            },
            {
                "schema": LAW_CANDIDATE_SCHEMA,
                "law_id": "reinforcing-strategy-choice-durability",
                "version": "8",
                "name": "Reinforcing strategy choice → durability",
                "question": (
                    "When a company adopts a source-observed reinforcing strategic choice, "
                    "does earnings durability improve relative to a comparable untreated cohort?"
                ),
                "created_at": "2026-08-13T12:49:35Z",
                "not_before": "2026-08-13T12:49:35Z",
                "origin": "jaggedthoughts_seed",
                "estimator": {
                    "kind": _DID,
                    "design": "group_time_att_unadjusted",
                    "control_group": "never_or_not_yet_treated",
                    "implementation_id": "ztare.investment.institutional_learning.group_time_att_v3",
                    "expected_direction": "positive",
                    "treatment_id": "reinforcing_strategy_choice_adoption",
                    "parallel_trend_tolerance": 0.10,
                    "bootstrap_iterations": 1000,
                },
                "cohort": {
                    "entity_kinds": ["public_equity", "private_company"],
                    "horizon_days": [],
                    "conditions": [],
                    "evaluation_environments": ["industry_id"],
                    "counterexample_fields": ["industry_id", "strategy_phenotype"],
                },
                "outcome_metric_id": "earnings_durability",
                "mechanism": {
                    "antecedent_concepts": ["strategic_choice_adoption"],
                    "consequence_concept": "earnings_durability",
                    "kind": "causal",
                },
                "decision_use": "strategy_option_learning",
                "validation": {
                    "minimum_treated_units": 4,
                    "minimum_control_units": 4,
                    "minimum_pre_periods": 2,
                    "minimum_post_periods": 1,
                },
                "trial_family_id": "strategy-causal-laws-v1",
                "authority": "diagnostic_and_prospective_shadow",
            },
        ],
    }


def _conditions(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("law cohort conditions must be a list")
    result = []
    for raw in payload:
        if not isinstance(raw, Mapping):
            raise ValueError("law cohort condition must be an object")
        path = require_text(raw.get("path"), "law cohort condition path")
        operator = require_text(raw.get("operator"), "law cohort condition operator")
        if operator not in _ALL_OPERATORS:
            raise ValueError(f"unsupported law cohort condition operator: {operator}")
        value = raw.get("value")
        if operator in _NUMERIC_OPERATORS:
            value = require_finite(value, f"law cohort condition {path}")
        elif not isinstance(value, (str, int, float, bool)):
            raise ValueError("eq/ne law conditions require a scalar value")
        result.append({"path": path, "operator": operator, "value": value})
    return result


def compile_law_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one bounded conjecture and its executable estimator grammar."""

    if payload.get("schema") != LAW_CANDIDATE_SCHEMA:
        raise ValueError(f"investment law schema must be {LAW_CANDIDATE_SCHEMA}")
    law_id = require_text(payload.get("law_id"), "law_id")
    version = require_text(payload.get("version"), "law version")
    estimator = dict(payload.get("estimator") or {})
    kind = require_text(estimator.get("kind"), "law estimator kind")
    if kind not in {_ASSOCIATION, _DID}:
        raise ValueError(f"unsupported law estimator: {kind}")
    direction = require_text(estimator.get("expected_direction"), "law expected direction")
    if direction not in {"positive", "negative"}:
        raise ValueError("law expected_direction must be positive or negative")
    outcome_metric_id = require_text(payload.get("outcome_metric_id"), "law outcome")
    created_at = canonical_timestamp(payload.get("created_at"), "law created_at")
    cohort = dict(payload.get("cohort") or {})
    entity_kinds = sorted({require_text(value, "law entity kind") for value in cohort.get("entity_kinds") or ()})
    if not entity_kinds:
        raise ValueError("law cohort entity_kinds must be nonempty")
    horizons = sorted({int(value) for value in cohort.get("horizon_days") or ()})
    if any(value < 1 for value in horizons):
        raise ValueError("law cohort horizon_days must be positive")
    cohort = {
        "entity_kinds": entity_kinds,
        "horizon_days": horizons,
        "conditions": _conditions(cohort.get("conditions") or []),
        "evaluation_environments": sorted({
            require_text(value, "law evaluation environment")
            for value in cohort.get("evaluation_environments") or ()
        }),
        "counterexample_fields": sorted({
            require_text(value, "law counterexample field")
            for value in cohort.get("counterexample_fields") or ()
        }),
    }
    predictor = None
    if kind == _ASSOCIATION:
        predictor = dict(payload.get("predictor_program") or {})
        output = require_text(predictor.get("output_metric_id"), "law predictor output")
        nodes = predictor.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise ValueError("association law predictor_program.nodes must be nonempty")
        compiled_nodes = []
        for index, raw in enumerate(nodes):
            if not isinstance(raw, Mapping):
                raise ValueError("law predictor node must be an object")
            node = SignalDefinition.from_dict({
                **dict(raw),
                "id": str(raw.get("id") or f"{law_id}:{version}:{index}"),
                "entity_id": "$EPISODE",
            })
            compiled_nodes.append({
                key: value for key, value in node.to_dict().items()
                if key not in {"definition_sha256", "entity_id"}
            })
        if output not in {str(row["metric_id"]) for row in compiled_nodes}:
            raise ValueError("law predictor output_metric_id is not produced by its nodes")
        predictor = {"output_metric_id": output, "nodes": compiled_nodes}
    validation = dict(payload.get("validation") or {})
    produced = {
        str(row.get("metric_id") or "")
        for row in (predictor or {}).get("nodes") or ()
    }
    inferred_antecedents = sorted({
        str(argument.get("metric") or "")
        for row in (predictor or {}).get("nodes") or ()
        for argument in row.get("arguments") or ()
        if isinstance(argument, Mapping)
        and argument.get("metric")
        and str(argument.get("metric")) not in produced
    })
    predictor_metric_ids = produced | set(inferred_antecedents)
    cohort_selection_fields = {
        str(row["path"]) for row in cohort["conditions"]
    } | set(cohort["evaluation_environments"]) | set(cohort["counterexample_fields"])
    if kind == _ASSOCIATION and outcome_metric_id in predictor_metric_ids:
        raise ValueError("law predictor cannot consume or produce its outcome metric")
    if outcome_metric_id in cohort_selection_fields:
        raise ValueError("law cohort cannot select or partition on its outcome metric")
    mechanism_raw = dict(payload.get("mechanism") or {})
    mechanism = {
        "antecedent_concepts": sorted({
            require_text(value, "law mechanism antecedent")
            for value in mechanism_raw.get("antecedent_concepts") or inferred_antecedents
        }),
        "consequence_concept": require_text(
            mechanism_raw.get("consequence_concept") or payload.get("outcome_metric_id"),
            "law mechanism consequence",
        ),
        "kind": require_text(
            mechanism_raw.get("kind") or ("causal" if kind == _DID else "predictive"),
            "law mechanism kind",
        ),
    }
    if not mechanism["antecedent_concepts"]:
        raise ValueError("law mechanism antecedent_concepts must be nonempty")
    if mechanism["kind"] not in {"predictive", "causal"}:
        raise ValueError("law mechanism kind must be predictive or causal")
    if mechanism["consequence_concept"] in mechanism["antecedent_concepts"]:
        raise ValueError("law mechanism cannot use its consequence as an antecedent without a typed lag")
    not_before = canonical_timestamp(
        payload.get("not_before") or created_at, "law not_before",
    )
    if timestamp_key(not_before) < timestamp_key(created_at):
        raise ValueError("law not_before cannot precede its creation time")
    body = {
        "schema": LAW_CANDIDATE_SCHEMA,
        "law_id": law_id,
        "version": version,
        "law_key": f"{law_id}@{version}",
        "name": require_text(payload.get("name"), "law name"),
        "question": require_text(payload.get("question"), "law question"),
        "created_at": created_at,
        "not_before": not_before,
        "origin": require_text(payload.get("origin"), "law origin"),
        "parent_law_sha256": str(payload.get("parent_law_sha256") or ""),
        "estimator": estimator,
        "cohort": cohort,
        "predictor_program": predictor,
        "outcome_metric_id": outcome_metric_id,
        "mechanism": mechanism,
        "decision_use": require_text(
            payload.get("decision_use") or "paper_candidate_ranking", "law decision use"
        ),
        "generation_receipt": dict(payload.get("generation_receipt") or {}),
        "validation": validation,
        "trial_family_id": require_text(payload.get("trial_family_id"), "law trial family"),
        "authority": require_text(payload.get("authority"), "law authority"),
        "capital_authority": False,
    }
    return {**body, "law_sha256": stable_sha256(body)}


def _strategy_phenotype_law_id(phenotype_sha256: str) -> str:
    return f"strategy-phenotype-{phenotype_sha256[:16]}-durability"


def compile_strategy_law_candidates(
    move_library: Mapping[str, Any], cohort_plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Compile exact strategy phenotypes into bounded causal-law candidates."""
    if move_library.get("schema") != STRATEGY_MOVE_LIBRARY_SCHEMA:
        return []
    if cohort_plan.get("schema") != STRATEGY_COHORT_PLAN_SCHEMA:
        return []
    candidates = []
    moves_by_sha = {
        str(row.get("move_sha256")): row
        for row in move_library.get("moves") or ()
        if isinstance(row, Mapping) and row.get("move_sha256")
    }
    phenotype_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for group in cohort_plan.get("mechanism_environments") or ():
        phenotype_groups[str(group.get("mechanism_phenotype_sha256") or "")].append(group)
    for phenotype_sha, groups in sorted(phenotype_groups.items()):
        focal_by_sha = {
            str(row.get("move_sha256")): dict(row)
            for group in groups
            for row in group.get("focal_moves") or ()
            if isinstance(row, Mapping)
            and row.get("move_sha256")
            and isinstance(row.get("implementation_event"), Mapping)
        }
        focal_moves = list(focal_by_sha.values())
        if len(phenotype_sha) != 64 or not focal_moves:
            continue
        phenotype = dict(groups[0].get("mechanism_phenotype") or {})
        action = require_text(phenotype.get("action"), "strategy phenotype action")
        bridge = require_text(
            phenotype.get("economic_bridge"), "strategy phenotype economic bridge",
        )
        availability = [
            canonical_timestamp(
                row["implementation_event"].get("available_at"),
                "strategy implementation available_at",
            )
            for row in focal_moves
        ]
        availability.extend(
            canonical_timestamp(
                moves_by_sha[str(row["move_sha256"])].get("evidence_epoch"),
                "strategy frontier evidence_epoch",
            )
            for row in focal_moves if str(row.get("move_sha256")) in moves_by_sha
        )
        availability.extend(
            canonical_timestamp(
                request.get("search_end_at") or request.get("created_at"),
                "strategy cohort availability",
            )
            for request in cohort_plan.get("requests") or ()
            if isinstance(request, Mapping)
            and str(request.get("mechanism_phenotype_sha256") or "") == phenotype_sha
        )
        availability.append(STRATEGY_LAW_COMPILER_AVAILABLE_AT)
        availability = sorted(set(availability), key=timestamp_key)
        evidence_boundary = max(availability, key=timestamp_key)
        regularity_identity = {
            "mechanism_phenotype_sha256": phenotype_sha,
            "unit_of_analysis": "company_strategy_phenotype_adoption",
            "outcome_metric_id": "earnings_durability",
            "estimator_kind": _DID,
        }
        evidence_version = stable_sha256({
            "phenotype_sha256": phenotype_sha,
            "move_sha256s": sorted(str(row.get("move_sha256") or "") for row in focal_moves),
            "available_at": availability,
        })[:12]
        raw = {
            "schema": LAW_CANDIDATE_SCHEMA,
            "law_id": _strategy_phenotype_law_id(phenotype_sha),
            "version": f"6-{evidence_version}",
            "name": f"{action.replace('_', ' ')} via {bridge.replace('_', ' ')}",
            "question": (
                f"When a company executes the exact {action.replace('_', ' ')} phenotype "
                f"through {bridge.replace('_', ' ')}, does earnings durability improve "
                "relative to comparable companies without that phenotype as of the same period?"
            ),
            "created_at": evidence_boundary,
            "not_before": evidence_boundary,
            "origin": "strategy_phenotype_compiler",
            "estimator": {
                "kind": _DID,
                "design": "group_time_att_unadjusted",
                "control_group": "never_or_not_yet_treated",
                "implementation_id": (
                    "ztare.investment.institutional_learning.group_time_att_v3"
                ),
                "expected_direction": "positive",
                "treatment_id": f"strategy_phenotype:{phenotype_sha}",
                "parallel_trend_tolerance": 0.10,
                "bootstrap_iterations": 1000,
            },
            "cohort": {
                "entity_kinds": ["public_equity", "private_company"],
                "horizon_days": [],
                "conditions": [],
                "evaluation_environments": ["industry_id"],
                "counterexample_fields": ["industry_id"],
            },
            "outcome_metric_id": "earnings_durability",
            "mechanism": {
                "antecedent_concepts": [
                    f"strategy_action:{action}",
                    f"economic_bridge:{bridge}",
                    f"strategy_phenotype:{phenotype_sha}",
                ],
                "consequence_concept": "earnings_durability",
                "kind": "causal",
            },
            "decision_use": "strategy_option_learning",
            "validation": {
                "minimum_treated_units": 4,
                "minimum_control_units": 4,
                "minimum_pre_periods": 2,
                "minimum_post_periods": 1,
                "minimum_transfer_environments": 2,
                "minimum_meaningful_effect": 0.05,
                "alpha": 0.05,
                "power": 0.80,
            },
            "trial_family_id": "strategy-phenotype-causal-laws-v1",
            "authority": "diagnostic_and_prospective_shadow",
            "generation_receipt": {
                "mechanism_signature_sha256s": sorted({
                    str(group.get("mechanism_signature_sha256")) for group in groups
                    if group.get("mechanism_signature_sha256")
                }),
                "mechanism_phenotype_sha256": phenotype_sha,
                "seed_industry_ids": sorted({
                    str(group.get("industry_id")) for group in groups if group.get("industry_id")
                }),
                "focal_move_sha256s": sorted(
                    str(row.get("move_sha256") or "") for row in focal_moves
                ),
                "implementation_event_sha256s": sorted(
                    str(row["implementation_event"].get("implementation_event_sha256") or "")
                    for row in focal_moves
                ),
                "evidence_available_at": availability,
                "evidence_boundary": evidence_boundary,
                "regularity_identity": regularity_identity,
                "regularity_identity_sha256": stable_sha256(regularity_identity),
                "promotion_boundary": (
                    "A compiled candidate is a conjecture. Promotion requires prospective "
                    "replication, controls, pretrend support, and multiplicity correction."
                ),
            },
        }
        candidates.append(compile_law_candidate(raw))
    return sorted(candidates, key=lambda row: row["law_key"])


def load_law_catalog(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or raw.get("schema") != LAW_CATALOG_SCHEMA:
        raise ValueError(f"law catalog schema must be {LAW_CATALOG_SCHEMA}")
    candidates = [
        compile_law_candidate(row)
        for row in raw.get("candidates") or ()
        if isinstance(row, Mapping)
    ]
    keys = [str(row["law_key"]) for row in candidates]
    if len(keys) != len(set(keys)):
        raise ValueError("law catalog contains duplicate law identities")
    body = {
        "schema": LAW_CATALOG_SCHEMA,
        "version": require_text(raw.get("version"), "law catalog version"),
        "updated_at": canonical_timestamp(raw.get("updated_at"), "law catalog updated_at"),
        "purpose": require_text(raw.get("purpose"), "law catalog purpose"),
        "candidates": candidates,
    }
    return {**body, "catalog_sha256": stable_sha256(body), "path": str(source)}


def _band(value: float | None, cuts: tuple[float, float], labels: tuple[str, str, str]) -> str:
    if value is None:
        return "unavailable"
    return labels[0] if value < cuts[0] else labels[1] if value < cuts[1] else labels[2]


def _candidate_payload(store: GoldenStore | None, packet: Mapping[str, Any]) -> dict[str, Any]:
    leaf = str((packet.get("subject") or {}).get("candidate_leaf") or "")
    if not leaf or store is None:
        return {}
    try:
        result = store.get_leaf(leaf).get("payload")
    except KeyError:
        return {}
    return dict(result) if isinstance(result, Mapping) else {}


def _phenotype_episode(
    run: Mapping[str, Any], settlement: Mapping[str, Any] | None,
    store: GoldenStore | None, entity_metadata: Mapping[str, Any], owner: str,
) -> dict[str, Any]:
    packet = dict(run.get("evidence_packet") or {})
    subject = dict(packet.get("subject") or {})
    candidate = _candidate_payload(store, packet)
    discovery = dict((packet.get("discovery_summary") or {}).get("metrics") or {})
    quality = dict((packet.get("company_quality") or {}).get("scores") or {})
    valuation = dict(packet.get("valuation_summary") or {})
    fund_metrics = dict((packet.get("fund_characteristics") or {}).get("metrics") or {})
    market = dict(packet.get("starting_market") or {})
    beta = dict(((candidate.get("beta_receipt") or {}).get("analysis") or {}))
    historical = dict(beta.get("historical") or {})
    factor_assumption = dict(beta.get("assumption_implied") or {})
    metrics: dict[str, float] = {}
    for source in (
        discovery, quality, valuation, fund_metrics, market, historical, factor_assumption,
    ):
        for key, value in source.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
                metrics[str(key)] = float(value)
    if "net_earnings_yield" in metrics:
        metrics.setdefault("portfolio_net_earnings_yield", metrics["net_earnings_yield"])
    coefficients = dict(beta.get("coefficients") or {})
    betas = dict(coefficients.get("betas") or {})
    for key, value in betas.items():
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            metrics[f"factor_beta_{key}"] = float(value)
    durability = metrics.get("durable_earnings_power", metrics.get("quality"))
    if durability is not None:
        metrics.setdefault("earnings_durability", durability)
    predictor_metric_ids = sorted(metrics)
    actual = dict((settlement or {}).get("actual_values") or {})
    outcome_metric_ids = []
    for key, value in actual.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            metrics[str(key)] = float(value)
            outcome_metric_ids.append(str(key))
    entity_id = require_text((packet.get("entity") or {}).get("entity_id"), "phenotype entity_id")
    candidate_leaf = str((packet.get("subject") or {}).get("candidate_leaf") or "")
    frozen_strategy = dict(packet.get("strategy_snapshot") or {})
    strategy_phenotype = (
        dict(frozen_strategy["phenotype"])
        if isinstance(frozen_strategy.get("phenotype"), Mapping) else None
    )
    strategy_refs = tuple(map(str, frozen_strategy.get("source_refs") or ()))
    if strategy_phenotype is None and store is not None and candidate_leaf:
        strategy_phenotype, strategy_refs = candidate_strategy_phenotype(
            store, owner=owner, candidate_leaf=candidate_leaf,
            as_of=str(run.get("opened_at") or ""),
        )
    catalog_row = dict(entity_metadata.get(entity_id) or {})
    entity_kind = str(candidate.get("entity_kind") or "")
    if not entity_kind:
        candidate_id = str(candidate.get("candidate_id") or subject.get("subject_id") or "")
        entity_kind = "public_fund" if candidate_id.startswith("fund:") else "public_equity"
    quality_value = metrics.get("quality", metrics.get("durable_earnings_power"))
    implied_growth = metrics.get("implied_growth", metrics.get("implied_growth_median"))
    implied_excess = metrics.get("price_implied_excess_return")
    momentum = metrics.get("active_return_6m")
    categories = {
        "entity_kind": entity_kind,
        "horizon_days": str(int(run.get("horizon_days") or 0)),
        "sector_id": str(catalog_row.get("sector") or candidate.get("sector") or "unclassified"),
        "industry_id": str(
            catalog_row.get("industry") or candidate.get("industry_id") or "unclassified"
        ),
        "fund_category": str(
            catalog_row.get("industry") or candidate.get("category") or "unclassified"
        ),
        "quality_band": _band(quality_value, (0.45, 0.75), ("fragile", "mixed", "durable")),
        "expectations_band": _band(implied_growth, (0.0, 0.03), ("negative", "restrained", "demanding")),
        "value_band": _band(implied_excess, (0.03, 0.06), ("thin", "positive", "wide")),
        "momentum_regime": (
            "unavailable" if momentum is None else "negative" if momentum < 0 else "positive"
        ),
        "value_beta_band": _band(metrics.get("factor_beta_value"), (0.25, 0.75), ("low", "mixed", "high")),
        "strategy_phenotype": (
            strategy_phenotype["phenotype_id"] if strategy_phenotype else "unclassified"
        ),
    }
    source_refs = sorted({
        *(
            str(value)
            for value in (packet.get("company_quality") or {}).get("source_refs", ())
            if value
        ),
        str(((packet.get("starting_market") or {}).get("entity_price") or {}).get("source_ref") or ""),
        str(((packet.get("starting_market") or {}).get("benchmark_price") or {}).get("source_ref") or ""),
    } - {""})
    source_refs = sorted({
        *source_refs,
        str(run.get("run_id") or ""),
        str((packet.get("subject") or {}).get("candidate_leaf") or ""),
        str((settlement or {}).get("settlement_sha256") or ""),
        str(catalog_row.get("source_id") or ""),
        *strategy_refs,
    } - {""})
    body = {
        "schema": PHENOTYPE_EPISODE_SCHEMA,
        "episode_id": require_text(run.get("episode_id"), "phenotype episode_id"),
        "run_id": require_text(run.get("run_id"), "phenotype run_id"),
        "inference_block_id": require_text(run.get("inference_block_id"), "phenotype block"),
        "entity_id": entity_id,
        "entity_kind": entity_kind,
        "horizon_days": int(run.get("horizon_days") or 0),
        "opened_at": canonical_timestamp(run.get("opened_at"), "phenotype opened_at"),
        "end_at": canonical_timestamp(run.get("end_at"), "phenotype end_at"),
        "outcome_available_at": (
            canonical_timestamp(settlement.get("evaluated_at"), "phenotype outcome available_at")
            if settlement else None
        ),
        "settlement_status": "settled" if settlement else "pending",
        "metrics": dict(sorted(metrics.items())),
        "metric_roles": {
            "predictor_metric_ids": predictor_metric_ids,
            "outcome_metric_ids": sorted(outcome_metric_ids),
        },
        "categories": categories,
        "source_refs": source_refs or [f"closed-book:{run['run_id']}"],
        "point_in_time": True,
    }
    return {**body, "phenotype_episode_sha256": stable_sha256(body)}


def _episode_value(episode: Mapping[str, Any], path: str) -> Any:
    if path in episode:
        return episode[path]
    categories = episode.get("categories") or {}
    if path in categories:
        return categories[path]
    return (episode.get("metrics") or {}).get(path)


def _matches(value: Any, operator: str, target: Any) -> bool:
    if value is None:
        return False
    if operator == "eq":
        return value == target
    if operator == "ne":
        return value != target
    observed = float(value)
    declared = float(target)
    return {
        "gt": observed > declared,
        "ge": observed >= declared,
        "lt": observed < declared,
        "le": observed <= declared,
    }[operator]


def _in_cohort(candidate: Mapping[str, Any], episode: Mapping[str, Any]) -> bool:
    cohort = candidate["cohort"]
    if episode.get("entity_kind") not in cohort["entity_kinds"]:
        return False
    horizons = cohort.get("horizon_days") or []
    if horizons and int(episode.get("horizon_days") or 0) not in horizons:
        return False
    not_before = candidate.get("not_before")
    if not_before and str(episode.get("opened_at")) <= str(not_before):
        return False
    return all(
        _matches(_episode_value(episode, row["path"]), row["operator"], row["value"])
        for row in cohort.get("conditions") or ()
    )


def _cohort_phenotype(candidate: Mapping[str, Any], episodes: Sequence[Mapping[str, Any]], generated_at: str) -> dict[str, Any]:
    members = [row for row in episodes if _in_cohort(candidate, row)]
    metric_coverage = Counter(
        metric for row in members for metric in (row.get("metrics") or {})
    )
    category_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in members:
        for field, value in (row.get("categories") or {}).items():
            category_counts[str(field)][str(value)] += 1
    body = {
        "schema": COHORT_PHENOTYPE_SCHEMA,
        "cohort_id": f"cohort:{candidate['law_key']}",
        "law_key": candidate["law_key"],
        "law_sha256": candidate["law_sha256"],
        "generated_at": generated_at,
        "definition": candidate["cohort"],
        "episode_count": len(members),
        "settled_episode_count": sum(row.get("settlement_status") == "settled" for row in members),
        "pending_episode_count": sum(row.get("settlement_status") != "settled" for row in members),
        "inference_block_count": len({row["inference_block_id"] for row in members}),
        "entity_count": len({row["entity_id"] for row in members}),
        "member_episode_ids": [row["episode_id"] for row in members],
        "member_episode_sha256s": [row["phenotype_episode_sha256"] for row in members],
        "metric_coverage": dict(sorted(metric_coverage.items())),
        "category_counts": {
            field: dict(sorted(counts.items())) for field, counts in sorted(category_counts.items())
        },
        "cross_industry_ready": len({
            str((row.get("categories") or {}).get("industry_id")) for row in members
            if (row.get("categories") or {}).get("industry_id") not in {None, "unclassified"}
        }) >= 2,
        "capital_authority": False,
    }
    return {**body, "cohort_sha256": stable_sha256(body)}


def _predictor(candidate: Mapping[str, Any], episode: Mapping[str, Any]) -> tuple[float | None, list[dict[str, Any]], list[dict[str, str]]]:
    entity = str(episode["episode_id"])
    opened_at = str(episode["opened_at"])
    observations = []
    for metric_id, value in (episode.get("metrics") or {}).items():
        unit = (
            "score" if metric_id in {"quality", "durable_earnings_power", "earnings_quality", "revenue_durability"}
            else "multiple" if metric_id.startswith("factor_beta_")
            else "decimal"
        )
        observations.append(MetricObservation(
            observation_id=f"phenotype:{episode['phenotype_episode_sha256'][:16]}:{metric_id}",
            entity_id=entity,
            metric_id=str(metric_id),
            value=float(value),
            unit=unit,
            observed_at=opened_at,
            available_at=opened_at,
            source_ref=f"phenotype:{episode['phenotype_episode_sha256']}",
        ))
    definitions = []
    for raw in (candidate.get("predictor_program") or {}).get("nodes") or ():
        definitions.append(SignalDefinition.from_dict({
            **dict(raw), "entity_id": entity,
            "id": f"law:{candidate['law_key']}:{entity}:{raw['metric_id']}",
        }))
    rows, receipts, blocks = derive_signals_partial(
        observations, definitions, as_of=opened_at,
    )
    output = str((candidate.get("predictor_program") or {}).get("output_metric_id") or "")
    value = next(
        (row.value for row in rows if row.entity_id == entity and row.metric_id == output),
        None,
    )
    return value, [row.to_dict() for row in receipts], [dict(row) for row in blocks]


def compile_law_policy_influence(
    candidates: Sequence[Mapping[str, Any]],
    learning_state: Mapping[str, Any] | None,
    *,
    generated_at: str | None = None,
    max_law_adjustment: float = 0.05,
    max_total_adjustment: float = 0.10,
) -> dict[str, Any]:
    """Turn eligible laws into bounded paper-research ordering evidence."""

    at = canonical_timestamp(generated_at or _utc_now(), "law influence generated_at")
    maximum = require_finite(max_law_adjustment, "max law adjustment")
    total_maximum = require_finite(max_total_adjustment, "max total adjustment")
    if not 0 < maximum <= total_maximum <= 0.25:
        raise ValueError("law influence bounds must satisfy 0 < per-law <= total <= 0.25")
    state = dict(learning_state or {})
    laws = {str(row.get("law_key") or ""): row for row in state.get("candidates") or ()}
    identities = [
        str(row.get("candidate_id") or row.get("entity_id") or f"candidate-{index}")
        for index, row in enumerate(candidates)
    ]
    contributions: dict[str, list[dict[str, Any]]] = {identity: [] for identity in identities}
    suppressed: list[dict[str, Any]] = []
    active_laws: list[dict[str, Any]] = []
    for evaluation in state.get("evaluations") or ():
        law_key = str(evaluation.get("law_key") or "")
        law = laws.get(law_key)
        if not evaluation.get("promotion_eligible") or not law:
            suppressed.append({
                "law_key": law_key,
                "reason": "missing_law" if not law else f"not_promotion_eligible:{evaluation.get('status')}",
            })
            continue
        if (law.get("estimator") or {}).get("kind") != _ASSOCIATION:
            suppressed.append({"law_key": law_key, "reason": "causal_law_requires_separate_policy_compiler"})
            continue
        scored: list[tuple[str, float, list[dict[str, Any]]]] = []
        for identity, candidate in zip(identities, candidates, strict=True):
            if candidate.get("entity_kind") not in (law.get("cohort") or {}).get("entity_kinds", ()):
                continue
            episode = {
                "episode_id": f"paper-ranking:{identity}",
                "phenotype_episode_sha256": str(
                    candidate.get("candidate_sha256") or stable_sha256(candidate)
                ),
                "opened_at": at,
                "metrics": dict(candidate.get("metrics") or {}),
                "categories": dict(candidate.get("categories") or {}),
                **{key: candidate.get(key) for key in ("entity_id", "entity_kind")},
            }
            if not all(
                _matches(_episode_value(episode, row["path"]), row["operator"], row["value"])
                for row in (law.get("cohort") or {}).get("conditions") or ()
            ):
                continue
            value, receipts, blocks = _predictor(law, episode)
            if value is not None and not blocks:
                scored.append((identity, float(value), receipts))
        if len(scored) < 2:
            suppressed.append({"law_key": law_key, "reason": "insufficient_current_cross_section"})
            continue
        direction = 1.0 if (law.get("estimator") or {}).get("expected_direction") == "positive" else -1.0
        directional = [direction * row[1] for row in scored]
        for identity, value, receipts in scored:
            directed = direction * value
            lower = sum(other < directed for other in directional)
            equal = sum(other == directed for other in directional)
            percentile = (lower + 0.5 * (equal - 1)) / (len(directional) - 1)
            contributions[identity].append({
                "law_key": law_key,
                "law_sha256": law["law_sha256"],
                "predictor_value": value,
                "directional_percentile": percentile,
                "adjustment": maximum * (2 * percentile - 1),
                "signal_receipt_sha256s": [row["receipt_sha256"] for row in receipts],
            })
        active_laws.append({
            "law_key": law_key,
            "law_sha256": law["law_sha256"],
            "decision_use": law.get("decision_use"),
            "current_cross_section": len(scored),
        })
    rows = []
    for identity in identities:
        unbounded = sum(row["adjustment"] for row in contributions[identity])
        adjustment = max(-total_maximum, min(total_maximum, unbounded))
        rows.append({
            "candidate_identity": identity,
            "adjustment": adjustment,
            "active_law_count": len(contributions[identity]),
            "contributions": contributions[identity],
        })
    body = {
        "schema": LAW_POLICY_INFLUENCE_SCHEMA,
        "generated_at": at,
        "learning_state_sha256": state.get("state_sha256"),
        "bounds": {"per_law": maximum, "total": total_maximum},
        "active_law_count": len(active_laws),
        "active_laws": active_laws,
        "suppressed_laws": suppressed,
        "candidates": rows,
        "authority": "paper_research_priority_only",
        "screen_status_mutable": False,
        "capital_authority": False,
    }
    return {**body, "influence_sha256": stable_sha256(body)}


def _environment_key(candidate: Mapping[str, Any], episode: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    fields = candidate["cohort"].get("evaluation_environments") or []
    return tuple((field, str(_episode_value(episode, field))) for field in fields)


def _rho_p_value(rho: float | None, n: int) -> float | None:
    if rho is None or n <= 3:
        return None
    if abs(rho) >= 1:
        return 0.0
    z = abs(0.5 * math.log((1 + rho) / (1 - rho)) * math.sqrt(n - 3))
    return math.erfc(z / math.sqrt(2.0))


def _association_environment(
    candidate: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], environment: Mapping[str, str],
) -> dict[str, Any]:
    validation = candidate["validation"]
    target = float(validation.get("target_rho", 0.30))
    expected_sign = 1 if candidate["estimator"]["expected_direction"] == "positive" else -1
    settled = [row for row in rows if row.get("outcome") is not None and row.get("predictor") is not None]
    by_block: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in settled:
        by_block[str(row["inference_block_id"])].append(row)
    minimum_cross_section = int(validation.get("minimum_cross_section", 4))
    block_rows = []
    for block_id, members in sorted(by_block.items()):
        if len(members) < minimum_cross_section:
            continue
        rho = spearman_rho(
            [float(row["predictor"]) for row in members],
            [float(row["outcome"]) for row in members],
        )
        block_rows.append({
            "inference_block_id": block_id,
            "episode_count": len(members),
            "rho": rho,
            "opened_at": max(str(row["opened_at"]) for row in members),
        })
    pooled_rho, ci_lo, ci_hi = spearman_rho_with_ci(
        [float(row["predictor"]) for row in settled],
        [float(row["outcome"]) for row in settled],
    ) if len(settled) >= 4 else (None, None, None)
    power_verdict = ("invalid_run", "fewer than four settled rows")
    if pooled_rho is not None:
        power_verdict = power_aware_verdict(
            pooled_rho, len(settled), target_rho=target,
            alpha=float(validation.get("alpha", 0.05)),
            power=float(validation.get("power", 0.80)),
        )
    min_blocks = int(validation.get("minimum_inference_blocks", 8))
    holdout_fraction = float(validation.get("holdout_fraction", 0.25))
    ordered_blocks = sorted(block_rows, key=lambda row: (row["opened_at"], row["inference_block_id"]))
    holdout_count = max(1, math.ceil(len(ordered_blocks) * holdout_fraction)) if len(ordered_blocks) >= min_blocks else 0
    holdout = ordered_blocks[-holdout_count:] if holdout_count else []
    training = ordered_blocks[:-holdout_count] if holdout_count else ordered_blocks
    train_mean = mean([float(row["rho"]) for row in training]) if training else None
    holdout_mean = mean([float(row["rho"]) for row in holdout]) if holdout else None
    counterexamples = []
    refinement_proposals = []
    minimum_rows = int(validation.get("counterexample_minimum_rows", 4))
    minimum_blocks = int(validation.get("counterexample_minimum_blocks", 2))
    reversal = float(validation.get("counterexample_abs_rho", 0.20))
    for field in candidate["cohort"].get("counterexample_fields") or ():
        groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in settled:
            groups[str(row.get("categories", {}).get(field, "unavailable"))].append(row)
        for value, members in sorted(groups.items()):
            if value in {"unavailable", "unclassified"} or len(members) < minimum_rows:
                continue
            blocks = {str(row["inference_block_id"]) for row in members}
            if len(blocks) < minimum_blocks:
                continue
            rho = spearman_rho(
                [float(row["predictor"]) for row in members],
                [float(row["outcome"]) for row in members],
            )
            if rho is None or expected_sign * rho > -reversal:
                continue
            witness = {
                "field": field,
                "value": value,
                "rho": rho,
                "episode_count": len(members),
                "inference_block_count": len(blocks),
                "episode_ids": sorted(str(row["episode_id"]) for row in members),
            }
            counterexamples.append(witness)
            refinement_proposals.append({
                "kind": "future_domain_exclusion",
                "condition": {"path": field, "operator": "ne", "value": value},
                "selection_episode_ids": witness["episode_ids"],
                "activation_rule": "Only episodes opened after this counterexample was available may test the refinement.",
            })
    if not settled:
        status = "awaiting_outcomes"
    elif not block_rows:
        status = "awaiting_complete_cross_section"
    elif counterexamples:
        status = "challenged_by_counterexample"
    elif len(block_rows) < min_blocks:
        status = "inconclusive_under_inference_block_gate"
    elif holdout_mean is None or expected_sign * holdout_mean <= 0:
        status = "holdout_not_supportive"
    elif power_verdict[0] != "h1_supported":
        status = "inconclusive_power_aware"
    else:
        status = "prospective_transfer_candidate"
    return {
        "environment": dict(environment),
        "status": status,
        "eligible_episode_count": len(rows),
        "settled_episode_count": len(settled),
        "scored_inference_block_count": len(block_rows),
        "minimum_inference_blocks": min_blocks,
        "pooled_rank_correlation": pooled_rho,
        "pooled_rank_correlation_ci": [ci_lo, ci_hi],
        "pooled_two_sided_p_value": _rho_p_value(pooled_rho, len(settled)),
        "power_aware_verdict": power_verdict[0],
        "power_note": power_verdict[1],
        "target_rho": target,
        "n_required_for_target_rho": n_required_for_rho(
            target,
            alpha=float(validation.get("alpha", 0.05)),
            power=float(validation.get("power", 0.80)),
        ),
        "block_information_coefficients": block_rows,
        "chronological_holdout": {
            "training_block_count": len(training),
            "holdout_block_count": len(holdout),
            "training_mean_rho": train_mean,
            "holdout_mean_rho": holdout_mean,
            "direction_pass": holdout_mean is not None and expected_sign * holdout_mean > 0,
        },
        "counterexamples": counterexamples,
        "refinement_proposals": refinement_proposals,
    }


def _association_evaluation(
    candidate: Mapping[str, Any], cohort: Mapping[str, Any], episodes: Sequence[Mapping[str, Any]], generated_at: str,
) -> dict[str, Any]:
    members = [row for row in episodes if row["episode_id"] in set(cohort["member_episode_ids"])]
    scored = []
    blocked = []
    for episode in members:
        value, receipts, blocks = _predictor(candidate, episode)
        if value is None:
            blocked.append({"episode_id": episode["episode_id"], "blocks": blocks})
            continue
        scored.append({
            "episode_id": episode["episode_id"],
            "entity_id": episode["entity_id"],
            "opened_at": episode["opened_at"],
            "inference_block_id": episode["inference_block_id"],
            "categories": episode["categories"],
            "predictor": value,
            "outcome": (episode.get("metrics") or {}).get(candidate["outcome_metric_id"]),
            "settlement_status": episode["settlement_status"],
            "signal_receipts": receipts,
        })
    environments: dict[tuple[tuple[str, str], ...], list[dict[str, Any]]] = defaultdict(list)
    by_episode = {str(row["episode_id"]): row for row in members}
    for row in scored:
        environments[_environment_key(candidate, by_episode[row["episode_id"]])].append(row)
    results = [
        _association_environment(candidate, rows, dict(key))
        for key, rows in sorted(environments.items())
    ]
    if not results:
        status = "awaiting_compatible_phenotypes"
    elif any(row["status"] == "challenged_by_counterexample" for row in results):
        status = "challenged_by_counterexample"
    elif any(row["status"] == "prospective_transfer_candidate" for row in results):
        status = "prospective_transfer_candidate"
    elif all(row["status"] == "awaiting_outcomes" for row in results):
        status = "awaiting_outcomes"
    else:
        status = "collecting_or_inconclusive"
    body = {
        "schema": LAW_EVALUATION_SCHEMA,
        "law_key": candidate["law_key"],
        "law_sha256": candidate["law_sha256"],
        "cohort_sha256": cohort["cohort_sha256"],
        "generated_at": generated_at,
        "estimator_kind": _ASSOCIATION,
        "status": status,
        "phenotype_episode_count": len(members),
        "predictor_scored_count": len(scored),
        "predictor_blocked_count": len(blocked),
        "blocked_episodes": blocked,
        "environment_evaluations": results,
        "multiplicity": {"status": "awaiting_family_compilation"},
        "promotion_eligible": False,
        "capital_authority": False,
    }
    return body


def _validated_panel_row(raw: Mapping[str, Any], law: Mapping[str, Any]) -> dict[str, Any]:
    if raw.get("schema") != CAUSAL_PANEL_ROW_SCHEMA:
        raise ValueError(f"causal panel row schema must be {CAUSAL_PANEL_ROW_SCHEMA}")
    law_id = str(law["law_id"])
    if str(raw.get("law_id")) != law_id:
        raise ValueError("causal panel row crossed law identity")
    period = int(raw.get("period_index"))
    treatment_period = raw.get("treatment_period")
    treated = bool(raw.get("treated_group"))
    treatment_event_sha = raw.get("treatment_event_sha256")
    treatment_timing_status = str(raw.get("treatment_timing_status") or "")
    treatment_occurred_at = None
    treatment_available_at = None
    control_start_at = None
    control_end_at = None
    if treated:
        if treatment_period is None:
            raise ValueError("treated causal panel rows require a treatment_period")
        if (
            not isinstance(treatment_event_sha, str) or len(treatment_event_sha) != 64
            or any(value not in "0123456789abcdef" for value in treatment_event_sha)
        ):
            raise ValueError("treated causal panel rows require an exact implementation-event hash")
        if treatment_timing_status != "exact_adoption_event":
            raise ValueError("treated causal panel rows require exact adoption timing")
        event_shas = sorted({
            require_text(value, "causal panel implementation-event hash")
            for value in raw.get("treatment_event_sha256s") or ()
        })
        if event_shas != [treatment_event_sha]:
            raise ValueError("treated causal panel rows must bind one exact adoption event")
        treatment_occurred_at = canonical_timestamp(
            raw.get("treatment_occurred_at"), "causal panel treatment_occurred_at",
        )
        treatment_available_at = canonical_timestamp(
            raw.get("treatment_available_at"), "causal panel treatment_available_at",
        )
        if timestamp_key(treatment_available_at) < timestamp_key(treatment_occurred_at):
            raise ValueError("causal treatment cannot be available before it occurred")
    elif treatment_period is not None or treatment_event_sha is not None:
        raise ValueError("never-treated causal panel rows cannot carry treatment identity")
    elif treatment_timing_status in {
        "never_treated_as_of_panel", "not_yet_treated_bounded",
    } and (raw.get("control_observation_start_at") or raw.get("control_observation_end_at")):
        control_start_at = canonical_timestamp(
            raw.get("control_observation_start_at"), "causal panel control start",
        )
        control_end_at = canonical_timestamp(
            raw.get("control_observation_end_at"), "causal panel control end",
        )
        if timestamp_key(control_end_at) < timestamp_key(control_start_at):
            raise ValueError("causal panel control window ends before it starts")
    elif treatment_timing_status != "never_treated_as_of_panel":
        raise ValueError("untreated causal panel rows require an explicit control identity")
    outcome_metric_id = require_text(raw.get("outcome_metric_id"), "causal panel outcome_metric_id")
    if outcome_metric_id != law["outcome_metric_id"]:
        raise ValueError("causal panel outcome metric crossed law identity")
    observed_at = canonical_timestamp(raw.get("observed_at"), "causal panel observed_at")
    available_at = canonical_timestamp(raw.get("available_at"), "causal panel available_at")
    if timestamp_key(available_at) < timestamp_key(observed_at):
        raise ValueError("causal panel outcome cannot be available before it was observed")
    if control_start_at and not (
        timestamp_key(control_start_at) <= timestamp_key(observed_at) <= timestamp_key(control_end_at)
    ):
        raise ValueError("bounded control outcome lies outside its non-adoption search window")
    observation_ids = sorted({
        require_text(value, "causal panel observation id")
        for value in raw.get("observation_ids") or ()
    })
    if not observation_ids:
        raise ValueError("causal panel rows require source observation identities")
    cohort_provenance = {}
    for field in ("cohort_plan_sha256", "cohort_query_sha256", "cohort_result_sha256"):
        value = str(raw.get(field) or "")
        if value and (len(value) != 64 or any(character not in "0123456789abcdef" for character in value)):
            raise ValueError(f"causal panel {field} must be a SHA-256 digest")
        cohort_provenance[field] = value or None
    row = {
        "schema": CAUSAL_PANEL_ROW_SCHEMA,
        "law_id": law_id,
        "unit_id": require_text(raw.get("unit_id"), "causal panel unit_id"),
        "period_index": period,
        "treated_group": treated,
        "treatment_period": int(treatment_period) if treatment_period is not None else None,
        "treatment_event_sha256": treatment_event_sha,
        "treatment_event_sha256s": [treatment_event_sha] if treated else [],
        "treatment_timing_status": treatment_timing_status,
        "treatment_occurred_at": treatment_occurred_at,
        "treatment_available_at": treatment_available_at,
        "control_observation_start_at": control_start_at,
        "control_observation_end_at": control_end_at,
        "control_identity": (
            "bounded_not_yet_treated" if control_start_at else
            "never_treated_as_of_panel" if not treated else None
        ),
        "outcome_metric_id": outcome_metric_id,
        "outcome_unit": require_text(raw.get("outcome_unit"), "causal panel outcome_unit"),
        "outcome": require_finite(raw.get("outcome"), "causal panel outcome"),
        "observed_at": observed_at,
        "available_at": available_at,
        "environment": dict(raw.get("environment") or {}),
        "observation_ids": observation_ids,
        "source_refs": sorted({require_text(value, "causal panel source ref") for value in raw.get("source_refs") or ()}),
        **cohort_provenance,
    }
    if not row["source_refs"]:
        raise ValueError("causal panel rows require source refs")
    return row


def _panel_index(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[int, float]], dict[str, int | None], dict[str, dict[str, Any]]]:
    panel: dict[str, dict[int, float]] = defaultdict(dict)
    adoption: dict[str, int | None] = {}
    environments: dict[str, dict[str, Any]] = {}
    units: dict[str, tuple[Any, ...]] = {}
    for row in rows:
        unit = str(row["unit_id"])
        period = int(row["period_index"])
        if period in panel[unit]:
            raise ValueError("causal panel has duplicate unit-period observations")
        identity = (
            bool(row["treated_group"]), row.get("treatment_event_sha256"),
            row.get("treatment_timing_status"), row.get("control_observation_start_at"),
            row.get("control_observation_end_at"),
        )
        if unit in units and units[unit] != identity:
            raise ValueError("causal panel treatment identity changes within a unit")
        current_adoption = row.get("treatment_period")
        if unit in adoption and adoption[unit] != current_adoption:
            raise ValueError("causal panel treatment period changes within a unit")
        environment = dict(row["environment"])
        if unit in environments and environments[unit] != environment:
            raise ValueError("causal panel environment changes within a unit")
        units[unit] = identity
        adoption[unit] = int(current_adoption) if current_adoption is not None else None
        environments[unit] = environment
        panel[unit][period] = float(row["outcome"])
    return panel, adoption, environments


def _panel_effect(
    panel: Mapping[str, Mapping[int, float]], treated_ids: Sequence[str], control_ids: Sequence[str],
    base_period: int, post_periods: Sequence[int],
) -> float:
    effects = []
    for period in post_periods:
        treated_change = mean(panel[unit][period] - panel[unit][base_period] for unit in treated_ids)
        control_change = mean(panel[unit][period] - panel[unit][base_period] for unit in control_ids)
        effects.append(treated_change - control_change)
    return mean(effects)


def _centered_bootstrap_p_value(samples: Sequence[float], estimate: float) -> float:
    """Approximate a two-sided null test from a centered bootstrap distribution."""
    return (1 + sum(abs(value - estimate) >= abs(estimate) for value in samples)) / (
        len(samples) + 1
    )


def _group_time_did(
    law: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
) -> tuple[str, str, dict[str, Any]]:
    """Unadjusted group-time ATT diagnostic with never/not-yet-treated controls."""
    panel, adoption, environments = _panel_index(rows)
    row_by_unit_period = {
        (str(row["unit_id"]), int(row["period_index"])): row for row in rows
    }
    validation = law["validation"]
    required_pre = max(2, int(validation.get("minimum_pre_periods", 2)))
    required_post = int(validation.get("minimum_post_periods", 1))
    required_treated = int(validation.get("minimum_treated_units", 4))
    required_control = int(validation.get("minimum_control_units", 4))
    tolerance = float(law["estimator"].get("parallel_trend_tolerance", 0.10))
    iterations = int(law["estimator"].get("bootstrap_iterations", 1000))
    groups = sorted({
        (int(period), stable_sha256(environments[unit]))
        for unit, period in adoption.items() if period is not None
    })
    all_periods = sorted({period for values in panel.values() for period in values})
    cells = []
    pretrend_rows = []
    for cohort, environment_sha in groups:
        treated = sorted(
            unit for unit, period in adoption.items()
            if period == cohort and stable_sha256(environments[unit]) == environment_sha
        )
        environment = environments[treated[0]]
        pre_periods = [period for period in all_periods if period < cohort]
        if len(pre_periods) < required_pre:
            continue
        supported_windows = []
        for end in range(required_pre - 1, len(pre_periods)):
            window = pre_periods[end - required_pre + 1:end + 1]
            pre_treated = [unit for unit in treated if set(window).issubset(panel[unit])]
            pre_controls = sorted(
                unit for unit, period in adoption.items()
                if unit not in treated
                and stable_sha256(environments[unit]) == environment_sha
                and (period is None or period > cohort)
                and set(window).issubset(panel[unit])
            )
            if len(pre_treated) < required_treated or len(pre_controls) < required_control:
                continue
            base = window[-1]
            window_cells = []
            for period in (value for value in all_periods if value >= cohort):
                group = [unit for unit in treated if {base, period}.issubset(panel[unit])]
                controls = sorted(
                    unit for unit, adoption_period in adoption.items()
                    if stable_sha256(environments[unit]) == environment_sha
                    and (adoption_period is None or adoption_period > period)
                    and {base, period}.issubset(panel[unit])
                )
                if len(group) < required_treated or len(controls) < required_control:
                    continue
                effect = (
                    mean(panel[unit][period] - panel[unit][base] for unit in group)
                    - mean(panel[unit][period] - panel[unit][base] for unit in controls)
                )
                horizon_days = sorted({
                    max(0, (
                        timestamp_key(str(row_by_unit_period[(unit, period)]["observed_at"]))
                        - timestamp_key(str(
                            row_by_unit_period[(unit, period)]["treatment_occurred_at"]
                        ))
                    ).days)
                    for unit in group
                })
                window_cells.append({
                    "cohort": cohort, "environment": environment,
                    "environment_sha256": environment_sha,
                    "period": period, "base_period": base,
                    "event_time": period - cohort, "effect": effect,
                    "horizon_days": horizon_days,
                    "treated_unit_count": len(group), "control_unit_count": len(controls),
                    "treated_units": group, "control_units": controls,
                })
            supported_windows.append((window, pre_treated, pre_controls, window_cells))
        if not supported_windows:
            continue
        window, pre_treated, pre_controls, window_cells = max(
            supported_windows,
            key=lambda value: (
                len(value[3]) >= required_post, len(value[3]),
                min(len(value[1]), len(value[2])), value[0][-1], value[0][0],
            ),
        )
        prior, base = window[-2], window[-1]
        gap = (
            mean(panel[unit][base] - panel[unit][prior] for unit in pre_treated)
            - mean(panel[unit][base] - panel[unit][prior] for unit in pre_controls)
        )
        pretrend_rows.append({
            "cohort": cohort, "environment": environment,
            "environment_sha256": environment_sha, "pretrend_gap": gap,
            "parallel": abs(gap) <= tolerance,
            "pre_periods": list(window),
            "treated_unit_count": len(pre_treated), "control_unit_count": len(pre_controls),
        })
        cells.extend(window_cells)
    cell_counts = Counter((row["cohort"], row["environment_sha256"]) for row in cells)
    qualified_groups = {
        key for key, count in cell_counts.items() if count >= required_post
    }
    cells = [
        row for row in cells
        if (row["cohort"], row["environment_sha256"]) in qualified_groups
    ]
    if not cells:
        return (
            "inconclusive_underpowered_panel",
            "No group-time cell meets the declared treated, control, pre-period, and post-period floors.",
            {
                "adoption_environment_groups": len(groups),
                "eligible_group_time_cell_count": len(cells),
            },
        )
    rng = random.Random(int(law["law_sha256"][:16], 16))
    weights = [row["treated_unit_count"] for row in cells]
    total_weight = sum(weights)
    effect = sum(row["effect"] * weight for row, weight in zip(cells, weights, strict=True)) / total_weight
    boot = []
    boot_by_environment: dict[str, list[float]] = defaultdict(list)
    cluster_units = sorted({unit for row in cells for unit in (
        *row["treated_units"], *row["control_units"],
    )})
    attempts = 0
    while len(boot) < iterations and attempts < iterations * 10:
        attempts += 1
        cluster_weights = Counter(rng.choice(cluster_units) for _ in cluster_units)
        estimates = []
        for cell in cells:
            group = cell["treated_units"]
            controls = cell["control_units"]
            base = cell["base_period"]
            period = cell["period"]
            group_weight = sum(cluster_weights[unit] for unit in group)
            control_weight = sum(cluster_weights[unit] for unit in controls)
            if not group_weight or not control_weight:
                estimates = []
                break
            estimates.append(
                sum(
                    cluster_weights[unit] * (panel[unit][period] - panel[unit][base])
                    for unit in group
                ) / group_weight
                - sum(
                    cluster_weights[unit] * (panel[unit][period] - panel[unit][base])
                    for unit in controls
                ) / control_weight
            )
        if len(estimates) != len(cells):
            continue
        boot.append(sum(value * weight for value, weight in zip(estimates, weights, strict=True)) / total_weight)
        for environment_sha in sorted({str(row["environment_sha256"]) for row in cells}):
            indices = [
                index for index, row in enumerate(cells)
                if str(row["environment_sha256"]) == environment_sha
            ]
            environment_weight = sum(weights[index] for index in indices)
            boot_by_environment[environment_sha].append(sum(
                estimates[index] * weights[index] for index in indices
            ) / environment_weight)
    if len(boot) < iterations:
        return (
            "inconclusive_underpowered_panel",
            "Unit-cluster resampling could not preserve support in every qualified group-time cell.",
            {
                "adoption_environment_groups": len(groups),
                "eligible_group_time_cell_count": len(cells),
                "cluster_unit_count": len(cluster_units),
                "completed_bootstrap_iterations": len(boot),
                "required_bootstrap_iterations": iterations,
            },
        )
    boot.sort()
    lo = boot[int(0.025 * iterations)]
    hi = boot[min(iterations - 1, int(0.975 * iterations))]
    p_value = _centered_bootstrap_p_value(boot, effect)
    expected_sign = 1 if law["estimator"]["expected_direction"] == "positive" else -1
    pretrend_by_group = {
        (row["cohort"], row["environment_sha256"]): row for row in pretrend_rows
    }
    parallel = (
        qualified_groups.issubset(pretrend_by_group)
        and all(pretrend_by_group[key]["parallel"] for key in qualified_groups)
    )
    supported = expected_sign * lo > 0 if expected_sign > 0 else expected_sign * hi > 0
    status = (
        "challenged_parallel_trends" if not parallel
        else "diagnostic_direction_supported" if supported
        else "inconclusive_effect"
    )
    reason = (
        "At least one adoption cohort lacks a passing pre-treatment trend diagnostic."
        if not parallel else
        "The diagnostic resampling interval supports the declared direction."
        if supported else
        "The diagnostic resampling interval includes zero or the rival direction."
    )
    transport_effects = []
    for environment_sha, environment_boot in sorted(boot_by_environment.items()):
        environment_cells = [
            row for row in cells if str(row["environment_sha256"]) == environment_sha
        ]
        environment_weights = [int(row["treated_unit_count"]) for row in environment_cells]
        environment_estimate = sum(
            float(row["effect"]) * weight
            for row, weight in zip(environment_cells, environment_weights, strict=True)
        ) / sum(environment_weights)
        environment_boot.sort()
        transport_effects.append({
            "environment": dict(environment_cells[0]["environment"]),
            "environment_sha256": environment_sha,
            "estimate": environment_estimate,
            "resampling_interval_95": [
                environment_boot[int(0.025 * iterations)],
                environment_boot[min(iterations - 1, int(0.975 * iterations))],
            ],
            "bootstrap_standard_error": (
                stdev(environment_boot) if len(environment_boot) > 1 else None
            ),
            "group_time_cell_sha256s": sorted(stable_sha256(row) for row in environment_cells),
            "horizon": {
                "kind": "calendar_days_after_adoption",
                "minimum": min(
                    value for row in environment_cells for value in row["horizon_days"]
                ),
                "maximum": max(
                    value for row in environment_cells for value in row["horizon_days"]
                ),
            },
            "treated_unit_ids": sorted({
                unit for row in environment_cells for unit in row["treated_units"]
            }),
            "control_unit_ids": sorted({
                unit for row in environment_cells for unit in row["control_units"]
            }),
        })
    return status, reason, {
        "adoption_environment_groups": len(groups),
        "group_time_effects": [
            {
                **{key: value for key, value in row.items() if key not in {"treated_units", "control_units"}},
                "treated_unit_ids": list(row["treated_units"]),
                "control_unit_ids": list(row["control_units"]),
            }
            for row in cells
        ],
        "pretrend_diagnostics": pretrend_rows,
        "aggregate_att": effect,
        "diagnostic_resampling_interval_95": [lo, hi],
        "transport_effects": transport_effects,
        "bootstrap_standard_error": stdev(boot) if len(boot) > 1 else None,
        "two_sided_p_value": p_value,
        "p_value_method": (
            "centered company-cluster bootstrap preserving each unit path across group-time cells "
            "with finite-sample correction"
        ),
        "bootstrap_iterations": iterations,
        "cluster_unit_count": len(cluster_units),
        "bootstrap_attempt_count": attempts,
        "aggregation": "treated-unit-weighted available group-time cells",
        "control_group": "never or not yet treated at each group-time cell",
        "inference_status": "diagnostic_only_unadjusted",
    }


def _panel_value(row: Mapping[str, Any], path: str) -> Any:
    return row.get(path, (row.get("environment") or {}).get(path))


def _strategy_regularity_evidence(
    law: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
    details: Mapping[str, Any], diagnostic_status: str, epoch: str,
) -> dict[str, Any] | None:
    """Compile future-only transfer evidence for a generated strategy conjecture."""
    if law.get("origin") != "strategy_phenotype_compiler":
        return None
    boundary = str(law.get("not_before") or law["created_at"])
    receipt = dict(law.get("generation_receipt") or {})
    seed_events = set(receipt.get("implementation_event_sha256s") or ())
    by_unit: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_unit[str(row["unit_id"])].append(row)
    required_pre = int(law["validation"].get("minimum_pre_periods", 2))
    required_post = int(law["validation"].get("minimum_post_periods", 1))
    transfer_units: dict[str, str] = {}
    for unit, unit_rows in by_unit.items():
        first = unit_rows[0]
        treatment_period = first.get("treatment_period")
        if first["treated_group"]:
            event_sha = str(first.get("treatment_event_sha256") or "")
            pre = [row for row in unit_rows if int(row["period_index"]) < int(treatment_period)]
            post = [
                row for row in unit_rows
                if int(row["period_index"]) >= int(treatment_period)
                and timestamp_key(str(row["available_at"])) > timestamp_key(boundary)
            ]
            if (
                event_sha not in seed_events
                and timestamp_key(str(first["treatment_available_at"])) > timestamp_key(boundary)
                and len(pre) >= required_pre
                and len(post) >= required_post
            ):
                transfer_units[unit] = event_sha
    first_transfer_period = min(
        (
            int(by_unit[unit][0]["treatment_period"])
            for unit in transfer_units
        ),
        default=None,
    )
    control_units = {
        unit for unit, unit_rows in by_unit.items()
        if first_transfer_period is not None
        and not unit_rows[0]["treated_group"]
        and unit_rows[0].get("control_identity") == "bounded_not_yet_treated"
        and timestamp_key(str(unit_rows[0]["control_observation_end_at"])) > timestamp_key(boundary)
        and sum(
            int(row["period_index"]) >= first_transfer_period
            and timestamp_key(str(row["available_at"])) > timestamp_key(boundary)
            for row in unit_rows
        ) >= required_post
    }
    prospective_rows = [
        row for row in rows
        if (
            row["unit_id"] in transfer_units
            and (
                int(row["period_index"]) < int(row["treatment_period"])
                or timestamp_key(str(row["available_at"])) > timestamp_key(boundary)
            )
        ) or (
            row["unit_id"] in control_units
            and (
                int(row["period_index"]) < first_transfer_period
                or timestamp_key(str(row["available_at"])) > timestamp_key(boundary)
            )
        )
    ]
    prospective_status, _prospective_reason, prospective_details = (
        _group_time_did(law, prospective_rows)
        if transfer_units and control_units
        else ("inconclusive_underpowered_panel", "", {})
    )
    cells = [dict(row) for row in prospective_details.get("group_time_effects") or ()]
    environments = {
        stable_sha256(dict(row.get("environment") or {})) for row in cells
    }
    effect_treated_units = {
        unit for row in cells for unit in row.get("treated_unit_ids") or ()
    }
    effect_control_units = {
        unit for row in cells for unit in row.get("control_unit_ids") or ()
    }
    required_treated = int(law["validation"].get("minimum_treated_units", 4))
    required_control = int(law["validation"].get("minimum_control_units", 4))
    required_environments = int(law["validation"].get("minimum_transfer_environments", 1))
    meaningful_effect = law["validation"].get("minimum_meaningful_effect")
    standard_error = prospective_details.get("bootstrap_standard_error")
    alpha = float(law["validation"].get("alpha", 0.05))
    target_power = float(law["validation"].get("power", 0.80))
    detectable_effect = (
        (
            NormalDist().inv_cdf(1 - alpha / 2)
            + NormalDist().inv_cdf(target_power)
        ) * float(standard_error)
        if standard_error is not None and 0 < alpha < 1 and 0.5 < target_power < 1
        else None
    )
    precision_gate = (
        meaningful_effect is not None
        and detectable_effect is not None
        and detectable_effect <= float(meaningful_effect)
    )
    power_gate = (
        len(effect_treated_units) >= required_treated
        and len(effect_control_units) >= required_control
        and len(environments) >= required_environments
        and bool(cells)
        and precision_gate
    )
    expected_sign = 1 if law["estimator"]["expected_direction"] == "positive" else -1
    counterexamples, refinements = [], []
    for field in law["cohort"].get("counterexample_fields") or ():
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for cell in cells:
            value = str((cell.get("environment") or {}).get(field, "unavailable"))
            if value not in {"unavailable", "unclassified"}:
                grouped[value].append(cell)
        for value, group in sorted(grouped.items()):
            weight = sum(int(row["treated_unit_count"]) for row in group)
            effect = sum(float(row["effect"]) * int(row["treated_unit_count"]) for row in group) / weight
            if meaningful_effect is None or expected_sign * effect > -float(meaningful_effect):
                continue
            witness = {
                "field": field, "value": value, "effect": effect,
                "minimum_meaningful_effect": float(meaningful_effect),
                "group_time_cell_count": len(group),
                "treated_unit_ids": sorted({
                    unit for row in group for unit in row.get("treated_unit_ids") or ()
                }),
                "effect_cell_sha256s": sorted(stable_sha256(row) for row in group),
            }
            counterexamples.append(witness)
            refinements.append({
                "kind": "future_domain_exclusion",
                "condition": {"path": field, "operator": "ne", "value": value},
                "selection_effect_cell_sha256s": witness["effect_cell_sha256s"],
                "activation_rule": "Only panel outcomes available after this witness may test the refinement.",
            })
    p_value = prospective_details.get("two_sided_p_value")
    direction_supported = prospective_status == "diagnostic_direction_supported"
    eligible = power_gate and direction_supported and not counterexamples
    status = (
        "challenged_by_counterexample" if counterexamples else
        prospective_status if prospective_status.startswith("challenged_") else
        "prospective_transfer_candidate" if eligible else
        "awaiting_prospective_business_outcomes" if not transfer_units else
        "inconclusive_power_aware_holdout"
    )
    identity = dict(receipt.get("regularity_identity") or {
        "mechanism_phenotype_sha256": receipt.get("mechanism_phenotype_sha256"),
        "unit_of_analysis": "company_strategy_phenotype_adoption",
        "outcome_metric_id": law["outcome_metric_id"],
        "estimator_kind": _DID,
    })
    body = {
        "schema": STRATEGY_REGULARITY_SCHEMA,
        "regularity_identity": identity,
        "regularity_identity_sha256": stable_sha256(identity),
        "law_key": law["law_key"], "law_sha256": law["law_sha256"],
        "generated_at": epoch, "not_before": boundary,
        "status": status,
        "prospective_holdout": {
            "eligible": eligible,
            "power_status": (
                "declared_effect_resolved" if power_gate else "under_declared_power_or_sample_floor"
            ),
            "required": {
                "treated_units": required_treated, "control_units": required_control,
                "pre_periods": required_pre, "post_periods": required_post,
                "transfer_environments": required_environments,
                "minimum_meaningful_effect": meaningful_effect,
                "alpha": alpha, "power": target_power,
            },
            "observed": {
                "independent_treated_units": len(effect_treated_units),
                "bounded_control_units": len(effect_control_units),
                "transfer_environments": len(environments),
                "group_time_cells": len(cells),
                "bootstrap_standard_error": standard_error,
                "minimum_detectable_effect_at_declared_power": detectable_effect,
            },
            "independent_treatment_event_sha256s": sorted(set(transfer_units.values())),
            "two_sided_p_value": p_value,
            "p_value_method": prospective_details.get("p_value_method"),
            "uncertainty_basis": "declared unit/period floors plus unit-resampled effect interval",
        },
        "diagnostics": {
            "discovery_panel_status": diagnostic_status,
            "prospective_panel_status": prospective_status,
            "aggregate_att": prospective_details.get("aggregate_att"),
            "resampling_interval_95": prospective_details.get(
                "diagnostic_resampling_interval_95"
            ),
            "pretrend_diagnostics": prospective_details.get("pretrend_diagnostics") or [],
            "group_time_effects": prospective_details.get("group_time_effects") or [],
            "transport_effects": prospective_details.get("transport_effects") or [],
        },
        "outcome_unit": (
            next(iter({str(row["outcome_unit"]) for row in prospective_rows}), None)
        ),
        "counterexamples": counterexamples,
        "refinement_proposals": refinements,
        "provenance": {
            "seed_implementation_event_sha256s": sorted(seed_events),
            "seed_industry_ids": list(receipt.get("seed_industry_ids") or ()),
            "seed_mechanism_signature_sha256s": list(
                receipt.get("mechanism_signature_sha256s") or ()
            ),
            "panel_row_sha256s": sorted(stable_sha256(row) for row in rows),
            "prospective_panel_row_sha256s": sorted(
                stable_sha256(row) for row in prospective_rows
            ),
            "observation_ids": sorted({
                value for row in rows for value in row.get("observation_ids") or ()
            }),
            "source_refs": sorted({
                value for row in rows for value in row.get("source_refs") or ()
            }),
            "cohort_plan_sha256s": sorted({
                str(row["cohort_plan_sha256"]) for row in prospective_rows
                if row.get("cohort_plan_sha256")
            }),
            "cohort_query_sha256s": sorted({
                str(row["cohort_query_sha256"]) for row in prospective_rows
                if row.get("cohort_query_sha256")
            }),
            "cohort_result_sha256s": sorted({
                str(row["cohort_result_sha256"]) for row in prospective_rows
                if row.get("cohort_result_sha256")
            }),
        },
        "capital_authority": False,
    }
    return {**body, "regularity_evidence_sha256": stable_sha256(body)}


def evaluate_difference_in_differences(
    candidate: Mapping[str, Any], panel_rows: Iterable[Mapping[str, Any]], *, generated_at: str | None = None,
) -> dict[str, Any]:
    """Evaluate a common-adoption panel; staggered treatment is typed unavailable."""

    law = compile_law_candidate(candidate) if "law_sha256" not in candidate else dict(candidate)
    if law["estimator"]["kind"] != _DID:
        raise ValueError("difference-in-differences evaluator requires a DiD law")
    epoch = canonical_timestamp(generated_at or _utc_now(), "DiD generated_at")
    if timestamp_key(epoch) < timestamp_key(str(law.get("not_before") or law["created_at"])):
        raise ValueError("causal evaluation predates the law evidence boundary")
    rows = [_validated_panel_row(row, law) for row in panel_rows]
    rows = [
        row for row in rows
        if all(
            _matches(_panel_value(row, condition["path"]), condition["operator"], condition["value"])
            for condition in law["cohort"].get("conditions") or ()
        )
    ]
    if any(timestamp_key(row["available_at"]) > timestamp_key(epoch) for row in rows):
        raise ValueError("causal panel contains an outcome unavailable at the evaluation epoch")
    if any(
        row["treated_group"]
        and timestamp_key(str(row["treatment_available_at"])) > timestamp_key(epoch)
        for row in rows
    ):
        raise ValueError("causal panel contains a treatment unavailable at the evaluation epoch")
    if len({row["outcome_unit"] for row in rows}) > 1:
        raise ValueError("causal panel outcome unit changes within a law")
    treatment_periods = {row["treatment_period"] for row in rows if row["treated_group"]}
    if not rows:
        status, reason = "awaiting_causal_panel", "No source-bound treatment panel is available."
        details: dict[str, Any] = {}
    elif not treatment_periods:
        status, reason = "awaiting_treated_panel", "No exact treated unit is available."
        details = {}
    elif law["estimator"].get("design") == "group_time_att_unadjusted" or len(treatment_periods) > 1:
        status, reason, details = _group_time_did(law, rows)
    else:
        treatment_period = int(next(iter(treatment_periods)))
        panel, adoption, _ = _panel_index(rows)
        treated_flags = {unit: period is not None for unit, period in adoption.items()}
        common_periods = sorted(set.intersection(*(set(values) for values in panel.values()))) if panel else []
        pre = [period for period in common_periods if period < treatment_period]
        post = [period for period in common_periods if period >= treatment_period]
        treated_ids = sorted(unit for unit, treated in treated_flags.items() if treated)
        control_ids = sorted(unit for unit, treated in treated_flags.items() if not treated)
        validation = law["validation"]
        required_pre = int(validation.get("minimum_pre_periods", 2))
        required_post = int(validation.get("minimum_post_periods", 1))
        required_treated = int(validation.get("minimum_treated_units", 4))
        required_control = int(validation.get("minimum_control_units", 4))
        sufficient = (
            len(pre) >= required_pre and len(post) >= required_post
            and len(treated_ids) >= required_treated and len(control_ids) >= required_control
        )
        if not sufficient:
            status, reason = "inconclusive_underpowered_panel", "The panel does not meet its declared unit and period floors."
            details = {
                "treated_unit_count": len(treated_ids), "control_unit_count": len(control_ids),
                "pre_period_count": len(pre), "post_period_count": len(post),
                "required": {
                    "treated_units": required_treated, "control_units": required_control,
                    "pre_periods": required_pre, "post_periods": required_post,
                },
            }
        else:
            base = pre[-1]
            effect = _panel_effect(panel, treated_ids, control_ids, base, post)
            treated_pretrend = mean(panel[unit][pre[-1]] - panel[unit][pre[-2]] for unit in treated_ids)
            control_pretrend = mean(panel[unit][pre[-1]] - panel[unit][pre[-2]] for unit in control_ids)
            pretrend_gap = treated_pretrend - control_pretrend
            tolerance = float(law["estimator"].get("parallel_trend_tolerance", 0.10))
            iterations = int(law["estimator"].get("bootstrap_iterations", 1000))
            rng = random.Random(int(law["law_sha256"][:16], 16))
            boot = []
            for _ in range(iterations):
                treated_sample = [rng.choice(treated_ids) for _ in treated_ids]
                control_sample = [rng.choice(control_ids) for _ in control_ids]
                boot.append(_panel_effect(panel, treated_sample, control_sample, base, post))
            boot.sort()
            lo = boot[int(0.025 * iterations)]
            hi = boot[min(iterations - 1, int(0.975 * iterations))]
            p_value = _centered_bootstrap_p_value(boot, effect)
            expected_sign = 1 if law["estimator"]["expected_direction"] == "positive" else -1
            parallel = abs(pretrend_gap) <= tolerance
            supported = expected_sign * lo > 0 if expected_sign > 0 else expected_sign * hi > 0
            status = (
                "challenged_parallel_trends" if not parallel
                else "diagnostic_direction_supported" if supported
                else "inconclusive_effect"
            )
            reason = (
                "Pre-treatment trends exceed the declared tolerance." if not parallel
                else "Cluster bootstrap interval supports the declared direction." if supported
                else "The cluster bootstrap interval includes zero or the rival direction."
            )
            details = {
                "treated_unit_count": len(treated_ids), "control_unit_count": len(control_ids),
                "common_periods": common_periods, "treatment_period": treatment_period,
                "pretrend_gap": pretrend_gap, "parallel_trend_tolerance": tolerance,
                "average_treatment_effect_on_treated": effect,
                "cluster_bootstrap_ci_95": [lo, hi], "bootstrap_iterations": iterations,
                "bootstrap_standard_error": stdev(boot) if len(boot) > 1 else None,
                "two_sided_p_value": p_value,
                "p_value_method": "centered unit-resampling bootstrap with finite-sample correction",
                "treated_unit_ids": treated_ids, "control_unit_ids": control_ids,
            }
    diagnostic_status = status
    regularity = _strategy_regularity_evidence(law, rows, details, status, epoch)
    if regularity is not None:
        status = str(regularity["status"])
        reason = {
            "prospective_transfer_candidate": "Independent post-boundary strategy outcomes pass the declared transfer floors and direction test.",
            "challenged_by_counterexample": "A transport moderator contains a qualified effect in the rival direction.",
            "awaiting_prospective_business_outcomes": "No independent treated unit has a post-boundary business outcome yet.",
            "inconclusive_power_aware_holdout": "Prospective treated, control, environment, or effect-cell support remains below the declared floors.",
        }.get(status, reason)
    trial_p = (
        (regularity.get("prospective_holdout") or {}).get("two_sided_p_value")
        if regularity is not None else details.get("two_sided_p_value")
    )
    environment_evaluations = ([{
        "environment": {"scope": "declared_strategy_regularity"},
        "status": status,
        "pooled_two_sided_p_value": trial_p,
        "counterexamples": list((regularity or {}).get("counterexamples") or ()),
        "refinement_proposals": list((regularity or {}).get("refinement_proposals") or ()),
    }] if regularity is not None and trial_p is not None else [])
    body = {
        "schema": LAW_EVALUATION_SCHEMA,
        "law_key": law["law_key"], "law_sha256": law["law_sha256"],
        "cohort_sha256": None,
        "generated_at": epoch,
        "estimator_kind": _DID, "status": status, "reason": reason,
        "diagnostic_status": diagnostic_status,
        "design": (
            "unadjusted group-time ATT with never/not-yet-treated controls"
            if len(treatment_periods) > 1
            or law["estimator"].get("design") == "group_time_att_unadjusted" else
            "common-adoption difference-in-differences with unit-cluster bootstrap"
        ),
        "details": details, "panel_row_count": len(rows),
        "environment_evaluations": environment_evaluations,
        "strategy_regularity": regularity,
        "counterexamples": list((regularity or {}).get("counterexamples") or ()),
        "refinement_proposals": list((regularity or {}).get("refinement_proposals") or ()),
        "promotion_eligible": False, "capital_authority": False,
    }
    return {**body, "evaluation_sha256": stable_sha256(body)}


def evaluate_investment_law(
    candidate: Mapping[str, Any], episodes: Sequence[Mapping[str, Any]], *,
    generated_at: str | None = None, panel_rows: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Evaluate one law against explicit phenotype or causal-panel evidence."""

    law = compile_law_candidate(candidate) if "law_sha256" not in candidate else dict(candidate)
    epoch = canonical_timestamp(generated_at or _utc_now(), "law evaluation generated_at")
    cohort = _cohort_phenotype(law, episodes, epoch)
    evaluation = (
        _association_evaluation(law, cohort, episodes, epoch)
        if law["estimator"]["kind"] == _ASSOCIATION
        else evaluate_difference_in_differences(law, panel_rows, generated_at=epoch)
    )
    if evaluation.get("cohort_sha256") is None:
        evaluation["cohort_sha256"] = cohort["cohort_sha256"]
        evaluation.pop("evaluation_sha256", None)
        evaluation["evaluation_sha256"] = stable_sha256(evaluation)
    return {"law": law, "cohort": cohort, "evaluation": evaluation}


def _load_panel_rows(root: Path, law_id: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((root / "institutional_learning" / "panels").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict) and str(value.get("law_id") or "") == law_id:
                rows.append(value)
    return rows


def _terminal_strategy_cohort_gaps(root: Path) -> set[str]:
    queue_path = root / "state" / "research_jobs.sqlite3"
    if not queue_path.exists():
        return set()
    connection = work_queue.connect(str(queue_path))
    try:
        rows = connection.execute(
            "SELECT payload_json FROM work_items WHERE kind=? AND status='dead_letter'",
            ("jaggedthoughts_strategy_cohort_research",),
        ).fetchall()
    finally:
        connection.close()
    gaps = set()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(payload, Mapping) and payload.get("request_sha256"):
            gaps.add(str(payload["request_sha256"]))
    return gaps


def _full_fiscal_treatment_period(
    event_at: datetime, fiscal_heads: Sequence[datetime],
) -> tuple[int, int]:
    """Return the partial-exposure FY and the first fully exposed FY."""
    same_year = [value for value in fiscal_heads if value.year == event_at.year]
    if same_year:
        partial = event_at.year + (max(same_year) < event_at)
    else:
        fiscal_month_day = max(value.strftime("%m-%d") for value in fiscal_heads)
        partial = event_at.year + (event_at.strftime("%m-%d") > fiscal_month_day)
    return partial, partial + 1


def _compile_strategy_causal_panel(root: Path) -> dict[str, Any]:
    """Derive a point-in-time diagnostic panel from classified strategy events."""
    plan = _read_json(root / "institutional_learning" / "strategy_cohorts" / "latest.json") or {}
    result_by_request = {
        str(row["request_sha256"]): row
        for path in sorted((root / "institutional_learning" / "strategy_cohorts" / "results").glob("*.json"))
        if (row := _read_json(path)) and row.get("request_sha256")
    }
    historical_requests = [
        row for path in sorted(
            (root / "research_jobs" / "strategy_cohorts" / "requests").glob("*.json")
        ) if (row := _read_json(path))
    ]
    assignments: dict[tuple[str, str], dict[str, Any]] = {}
    requests = {
        str(row["request_sha256"]): row for row in plan.get("requests") or ()
        if isinstance(row, Mapping) and row.get("request_sha256")
    }
    current_results, coverage_chain = resolve_strategy_cohort_results(
        plan, result_by_request.values(), historical_requests=historical_requests,
    )
    coverage_path = (
        root / "institutional_learning" / "strategy_cohorts" / "coverage-chain.json"
    )
    _atomic_json(coverage_path, coverage_chain)
    terminal_gaps = (_terminal_strategy_cohort_gaps(root) & set(requests)) - set(current_results)
    projection_frontier = compile_strategy_phenotype_projection_frontier(
        plan, result_by_request.values(), source_gap_request_sha256s=terminal_gaps,
        historical_requests=historical_requests,
    )
    projection_path = (
        root / "institutional_learning" / "strategy_cohorts" / "projection-frontier.json"
    )
    _atomic_json(projection_path, projection_frontier)
    excluded_status = []
    for group in plan.get("mechanism_environments") or ():
        phenotype_sha = str(group.get("mechanism_phenotype_sha256") or "")
        mechanism_sha = str(group.get("mechanism_signature_sha256") or "")
        industry = str(group.get("industry_id") or "")
        group_as_of = min(
            (
                str(row["search_end_at"]) for row in requests.values()
                if str(row.get("mechanism_phenotype_sha256") or "") == phenotype_sha
                and str(row.get("industry_id") or "") == industry
            ),
            default=max(
                (
                    str((row.get("implementation_event") or {}).get("available_at") or "")
                    for row in group.get("focal_moves") or ()
                ),
                default=_utc_now(),
            ),
        )
        focal_by_entity: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for move in group.get("focal_moves") or ():
            focal_by_entity[str(move.get("entity_id") or "").upper()].append(move)
        for entity, moves in focal_by_entity.items():
            events = [dict(row["implementation_event"]) for row in moves]
            assignments[(phenotype_sha, entity)] = {
                "entity_id": entity, "industry_id": industry, "treated": True,
                "events": events, "classification_authority": "filed_exact_adoption",
                "mechanism_signature_sha256": mechanism_sha,
                "panel_as_of": group_as_of,
                "cohort_plan_sha256": plan.get("plan_sha256"),
            }
    for request_sha, result in current_results.items():
        request = requests[request_sha]
        entity = str(request["peer_entity_id"]).upper()
        phenotype_sha = str(request["mechanism_phenotype_sha256"])
        key = (phenotype_sha, entity)
        classification = result.get("classification")
        if classification == "phenotype_adoption_found":
            phenotype_event_shas = set(result.get("phenotype_event_sha256s") or ())
            if not phenotype_event_shas:
                phenotype_event_shas = {
                    str(row.get("event_sha256")) for row in result.get("events") or ()
                    if set((row.get("focal_relation") or {}).values()) == {"same"}
                    and row.get("implementation_state") in {"operational", "completed"}
                }
            assignments[key] = {
                "entity_id": entity, "industry_id": request["industry_id"],
                "treated": True, "events": [
                    row for row in result.get("events") or ()
                    if row.get("event_sha256") in phenotype_event_shas
                ],
                "classification_authority": result.get("classification_authority"),
                "mechanism_signature_sha256": request["mechanism_signature_sha256"],
                "panel_as_of": result["coverage"]["search_end_at"],
                "cohort_plan_sha256": plan.get("plan_sha256"),
                "cohort_query_sha256": request.get("query_sha256"),
                "cohort_result_sha256": result.get("result_sha256"),
            }
        elif classification == "no_family_adoption_found":
            assignments[key] = {
                "entity_id": entity, "industry_id": request["industry_id"],
                "treated": False, "events": [],
                "classification_authority": result.get("classification_authority"),
                "mechanism_signature_sha256": request["mechanism_signature_sha256"],
                "panel_as_of": result["coverage"]["search_end_at"],
                "control_observation_start_at": request["search_start_at"],
                "control_observation_end_at": result["coverage"]["search_end_at"],
                "cohort_plan_sha256": plan.get("plan_sha256"),
                "cohort_query_sha256": request.get("query_sha256"),
                "cohort_result_sha256": result.get("result_sha256"),
            }
        else:
            excluded_status.append({
                "entity_id": entity,
                "status": (
                    "excluded_family_only" if classification == "family_adoption_only"
                    else "excluded_source_gap"
                ),
                "mechanism_phenotype_sha256": phenotype_sha,
            })
    for request_sha in sorted(terminal_gaps):
        request = requests[request_sha]
        excluded_status.append({
            "entity_id": str(request["peer_entity_id"]).upper(),
            "status": "excluded_source_gap",
            "mechanism_phenotype_sha256": str(request["mechanism_phenotype_sha256"]),
        })
    rows = []
    history_status = []
    history_entities: set[str] = set()
    for (phenotype_sha, entity), assignment in sorted(assignments.items()):
        as_of = str(assignment.get("panel_as_of") or _utc_now())
        try:
            reports = compile_company_quality_history(
                entity_id=entity, observations_path=root / "data" / "observations.csv",
                as_of=as_of, min_years=3,
            )
        except (FileNotFoundError, OSError, TypeError, ValueError) as error:
            reports = ()
            history_status.append({"entity_id": entity, "status": "blocked", "reason": str(error)})
        if not reports:
            history_status.append({"entity_id": entity, "status": "awaiting_history", "period_count": 0})
            history_entities.add(entity)
            continue
        events = sorted(assignment["events"], key=lambda row: (
            timestamp_key(str(row.get("occurred_at"))),
            str(row.get("implementation_event_sha256") or row.get("event_sha256") or ""),
        ))
        adoption_event = events[0] if events else None
        event_sha = str(
            (adoption_event or {}).get("implementation_event_sha256")
            or (adoption_event or {}).get("event_sha256") or ""
        ) or None
        if assignment["treated"] and (
            event_sha is None or len(event_sha) != 64
            or any(value not in "0123456789abcdef" for value in event_sha)
            or timestamp_key(str(adoption_event["available_at"])) > timestamp_key(as_of)
        ):
            history_status.append({
                "entity_id": entity, "status": "excluded_treatment_identity_or_time",
                "period_count": len(reports),
            })
            history_entities.add(entity)
            continue
        if not assignment["treated"]:
            control_start = timestamp_key(str(assignment["control_observation_start_at"]))
            control_end = timestamp_key(str(assignment["control_observation_end_at"]))
            reports = tuple(
                report for report in reports
                if control_start
                <= timestamp_key(str(report["history"][-1]["observed_at"]))
                <= control_end
            )
            if not reports:
                history_status.append({
                    "entity_id": entity, "status": "awaiting_bounded_control_history",
                    "period_count": 0,
                })
                history_entities.add(entity)
                continue
        treatment_period = None
        partial_treatment_period = None
        treatment_occurred_at = None
        treatment_available_at = None
        if adoption_event:
            event_at = timestamp_key(str(adoption_event["occurred_at"]))
            treatment_occurred_at = event_at.isoformat(timespec="seconds").replace("+00:00", "Z")
            treatment_available_at = canonical_timestamp(
                adoption_event["available_at"], "strategy treatment available_at",
            )
            fiscal_heads = [
                timestamp_key(str(report["history"][-1]["observed_at"])) for report in reports
            ]
            partial_treatment_period, treatment_period = _full_fiscal_treatment_period(
                event_at, fiscal_heads,
            )
        for report in reports:
            fiscal_head = str(report["history"][-1]["observed_at"])
            body = {
                "schema": CAUSAL_PANEL_ROW_SCHEMA,
                "law_id": _strategy_phenotype_law_id(phenotype_sha),
                "unit_id": f"{phenotype_sha[:12]}:{entity}",
                "period_index": int(fiscal_head[:4]),
                "treated_group": bool(assignment["treated"]),
                "treatment_period": treatment_period,
                "treatment_event_sha256": event_sha,
                "treatment_event_sha256s": [event_sha] if event_sha else [],
                "treatment_timing_status": (
                    "exact_adoption_event" if assignment["treated"] else "never_treated_as_of_panel"
                ),
                "treatment_occurred_at": treatment_occurred_at,
                "treatment_available_at": treatment_available_at,
                "control_observation_start_at": assignment.get("control_observation_start_at"),
                "control_observation_end_at": assignment.get("control_observation_end_at"),
                "outcome_metric_id": "earnings_durability", "outcome_unit": "score",
                "outcome": float(report["scores"]["durable_earnings_power"]),
                "observed_at": fiscal_head, "available_at": report["available_at"],
                "environment": {
                    "industry_id": assignment["industry_id"],
                    "mechanism_signature_sha256": assignment["mechanism_signature_sha256"],
                    "mechanism_phenotype_sha256": phenotype_sha,
                },
                "observation_ids": list(report["observation_ids"]),
                "source_refs": list(report["source_refs"]),
                "cohort_plan_sha256": assignment.get("cohort_plan_sha256"),
                "cohort_query_sha256": assignment.get("cohort_query_sha256"),
                "cohort_result_sha256": assignment.get("cohort_result_sha256"),
            }
            rows.append(body)
        period_indices = [int(str(report["history"][-1]["observed_at"])[:4]) for report in reports]
        post_period_count = sum(
            treatment_period is not None and period >= treatment_period for period in period_indices
        )
        history_status.append({
            "entity_id": entity,
            "status": (
                "history_ready_awaiting_post_treatment_outcome"
                if assignment["treated"] and post_period_count == 0
                else "history_ready"
            ),
            "period_count": len(reports),
            "treated_group": bool(assignment["treated"]),
            "treatment_period": treatment_period,
            "partial_treatment_period": partial_treatment_period,
            "treatment_period_basis": (
                "first_full_entity_fiscal_year_after_exact_adoption"
                if assignment["treated"] else None
            ),
            "treatment_occurred_at": treatment_occurred_at,
            "treatment_available_at": treatment_available_at,
            "pre_treatment_period_count": sum(
                treatment_period is not None and period < treatment_period for period in period_indices
            ),
            "post_treatment_period_count": post_period_count,
            "partial_treatment_period_count": sum(
                partial_treatment_period is not None and period == partial_treatment_period
                for period in period_indices
            ),
        })
        history_entities.add(entity)
    history_status.extend(excluded_status)
    history_entities.update(str(row["entity_id"]) for row in excluded_status)
    pending_peers = sorted({
        str(row.get("peer_entity_id") or "").upper() for row in requests.values()
        if row.get("peer_entity_id") and str(row.get("peer_entity_id")).upper() not in history_entities
    })
    for entity in pending_peers:
        pending_as_of = min(
            str(row["search_end_at"]) for row in requests.values()
            if str(row.get("peer_entity_id") or "").upper() == entity
        )
        try:
            reports = compile_company_quality_history(
                entity_id=entity, observations_path=root / "data" / "observations.csv",
                as_of=pending_as_of, min_years=3,
            )
            history_status.append({
                "entity_id": entity,
                "status": "history_ready_pending_event_classification" if reports else "awaiting_history",
                "period_count": len(reports),
            })
        except (FileNotFoundError, OSError, TypeError, ValueError) as error:
            history_status.append({"entity_id": entity, "status": "blocked", "reason": str(error)})
    destination = root / "institutional_learning" / "panels" / "reinforcing-strategy-choice-durability--auto.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temporary.replace(destination)
    pending_intervals = sum(
        bool(row.get("pending_delta")) for row in coverage_chain.get("bindings") or ()
    )
    pending = len(requests) - len(current_results) - len(terminal_gaps)
    move_library = _read_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json"
    ) or {}
    interval_timing_frontiers = []
    for move in move_library.get("moves") or ():
        if not isinstance(move, Mapping) or not isinstance(
            (move.get("timing_refinement") or {}).get("censored_interval"), Mapping,
        ):
            continue
        try:
            reports = compile_company_quality_history(
                entity_id=str(move.get("entity_id") or ""),
                observations_path=root / "data" / "observations.csv",
                as_of=str((move.get("timing_refinement") or {}).get("assessed_at") or _utc_now()),
                min_years=3,
            )
            frontier = compile_interval_treatment_period_frontier(
                move,
                fiscal_period_ends=[
                    str(report["history"][-1]["observed_at"]) for report in reports
                ],
            )
        except (FileNotFoundError, OSError, TypeError, ValueError):
            frontier = None
        if frontier:
            interval_timing_frontiers.append(frontier)
    body = {
        "schema": "jaggedthoughts-strategy-causal-panel-readiness-v1",
        "plan_sha256": plan.get("plan_sha256"),
        "panel_path": destination.relative_to(root).as_posix(),
        "panel_row_count": len(rows),
        "treated_unit_count": len({row["unit_id"] for row in rows if row["treated_group"]}),
        "control_unit_count": len({row["unit_id"] for row in rows if not row["treated_group"]}),
        "research_request_count": len(requests),
        "research_result_count": len(current_results),
        "recovered_compatible_result_count": coverage_chain[
            "recovered_compatible_result_count"
        ],
        "pending_interval_refresh_count": pending_intervals,
        "interval_timing_frontiers": interval_timing_frontiers,
        "coarse_period_identified_interval_count": sum(
            bool(row["coarse_period_identified"]) for row in interval_timing_frontiers
        ),
        "coverage_chain_path": coverage_path.relative_to(root).as_posix(),
        "coverage_chain_sha256": coverage_chain["coverage_chain_sha256"],
        "projection_frontier_path": projection_path.relative_to(root).as_posix(),
        "projection_frontier_sha256": projection_frontier["projection_frontier_sha256"],
        "projection_frontier_count": len(
            projection_frontier["certificate"]["frontier_program_ids"]
        ),
        "projection_selection_status": projection_frontier["selection_status"],
        "family_only_excluded_count": sum(
            row["status"] == "excluded_family_only" for row in excluded_status
        ),
        "source_gap_excluded_count": sum(
            row["status"] == "excluded_source_gap" for row in excluded_status
        ),
        "pending_research_count": max(0, pending),
        "history_status": history_status,
        "history_ready_unit_count": sum(
            str(row.get("status") or "").startswith("history_ready") for row in history_status
        ),
        "post_outcome_ready_unit_count": sum(
            row.get("status") == "history_ready" and row.get("treated_group") is True
            for row in history_status
        ),
        "awaiting_post_outcome_unit_count": sum(
            row.get("status") == "history_ready_awaiting_post_treatment_outcome"
            for row in history_status
        ),
        "next_activation": (
            f"Settle {pending} queued peer event classifications."
            if pending else
            f"Monitor {pending_intervals} covered peer intervals for material source changes."
            if pending_intervals else
            "Run the group-time diagnostic and inspect support, pretrends, and coverage gaps."
        ),
        "inference_boundary": "Agent classifications feed a diagnostic panel only; promotion remains disabled.",
        "capital_authority": False,
    }
    readiness = {**body, "readiness_sha256": stable_sha256(body)}
    _atomic_json(root / "institutional_learning" / "strategy_cohorts" / "panel-readiness.json", readiness)
    return readiness


def compile_workspace_strategy_causal_panel(workspace: str | Path) -> dict[str, Any]:
    """Refresh the strategy panel after its cohort plan or results change."""
    return _compile_strategy_causal_panel(Path(workspace).expanduser().resolve())


def _compile_refinement(
    candidate: Mapping[str, Any], proposal: Mapping[str, Any], available_at: str,
) -> dict[str, Any]:
    condition = dict(proposal["condition"])
    identity = stable_sha256({
        "parent": candidate["law_sha256"], "condition": condition, "available_at": available_at,
    })
    raw = {
        **{key: value for key, value in candidate.items() if key != "law_sha256"},
        "version": f"{candidate['version']}.cegar-{identity[:8]}",
        "created_at": available_at,
        "not_before": available_at,
        "origin": "cegar_counterexample_refinement",
        "parent_law_sha256": candidate["law_sha256"],
        "cohort": {
            **candidate["cohort"],
            "conditions": [*candidate["cohort"].get("conditions", ()), condition],
        },
    }
    raw.pop("law_key", None)
    raw.pop("capital_authority", None)
    return compile_law_candidate(raw)


def _load_generated_candidates(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((root / "institutional_learning" / "laws" / "generated").glob("*.json")):
        raw = _read_json(path)
        if raw:
            rows.append(compile_law_candidate({key: value for key, value in raw.items() if key != "law_sha256"}))
    return rows


def _record_learning_graph(
    store: GoldenStore, owner: str, candidates: Sequence[Mapping[str, Any]],
    cohorts: Sequence[Mapping[str, Any]], evaluations: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]], law_search: Mapping[str, Any],
    mechanism_graph: Mapping[str, Any], generated_at: str,
) -> dict[str, tuple[str, ...]]:
    leaves: list[GoldenLeaf] = []
    law_leaves: dict[str, GoldenLeaf] = {}
    cohort_leaves: dict[str, GoldenLeaf] = {}
    evaluation_leaves: dict[str, GoldenLeaf] = {}
    for candidate in candidates:
        leaf = GoldenLeaf(
            owner=owner, object_kind="investment_law_candidate",
            object_id=str(candidate["law_key"]), epoch=str(candidate["law_sha256"]),
            occurred_at=str(candidate["created_at"]), available_at=str(candidate["created_at"]),
            payload=dict(candidate), source_refs=(f"law-catalog:{candidate['law_sha256']}",),
        )
        law_leaves[str(candidate["law_key"])] = leaf
        leaves.append(leaf)
    episode_by_id = {str(row["episode_id"]): row for row in episodes}
    for cohort in cohorts:
        refs = tuple(
            str(episode_by_id[episode_id]["run_id"])
            for episode_id in cohort["member_episode_ids"] if episode_id in episode_by_id
        ) or (f"law:{cohort['law_sha256']}",)
        leaf = GoldenLeaf(
            owner=owner, object_kind="investment_cohort_phenotype",
            object_id=str(cohort["cohort_id"]), epoch=str(cohort["cohort_sha256"]),
            occurred_at=generated_at, available_at=generated_at,
            payload=dict(cohort), source_refs=refs,
        )
        cohort_leaves[str(cohort["law_key"])] = leaf
        leaves.append(leaf)
    for evaluation in evaluations:
        leaf = GoldenLeaf(
            owner=owner, object_kind="investment_law_evaluation",
            object_id=str(evaluation["law_key"]), epoch=str(evaluation["evaluation_sha256"]),
            occurred_at=generated_at, available_at=generated_at,
            payload=dict(evaluation), source_refs=(f"law:{evaluation['law_sha256']}",),
        )
        evaluation_leaves[str(evaluation["law_key"])] = leaf
        leaves.append(leaf)
    search_leaf = GoldenLeaf(
        owner=owner, object_kind="investment_law_search",
        object_id="current-investment-law-search",
        epoch=str(law_search["law_search_sha256"]),
        occurred_at=generated_at, available_at=generated_at,
        payload=dict(law_search),
        source_refs=tuple(
            f"phenotype:{row['phenotype_episode_sha256']}" for row in episodes
        ) or ("phenotype-set:empty",),
    )
    mechanism_identity = (
        owner, "investment_mechanism_graph", "current-investment-mechanism-graph",
        str(mechanism_graph["mechanism_graph_sha256"]),
    )
    existing_mechanism = store.identity(*mechanism_identity)
    mechanism_leaf = GoldenLeaf(
        owner=mechanism_identity[0], object_kind=mechanism_identity[1],
        object_id=mechanism_identity[2], epoch=mechanism_identity[3],
        occurred_at=(existing_mechanism or {}).get("occurred_at", generated_at),
        available_at=(existing_mechanism or {}).get("available_at", generated_at),
        payload=dict(mechanism_graph),
        source_refs=tuple((existing_mechanism or {}).get("source_refs") or (
            f"law:{row['law_sha256']}" for row in candidates
        )),
    )
    leaves.extend((search_leaf, mechanism_leaf))
    edges: list[GoldenEdge] = []
    for key, evaluation_leaf in evaluation_leaves.items():
        edges.append(GoldenEdge(evaluation_leaf.leaf_sha256, law_leaves[key].leaf_sha256, "scores"))
        cohort_leaf = cohort_leaves.get(key)
        if cohort_leaf:
            edges.append(GoldenEdge(evaluation_leaf.leaf_sha256, cohort_leaf.leaf_sha256, "based_on"))
    for key, cohort_leaf in cohort_leaves.items():
        edges.append(GoldenEdge(cohort_leaf.leaf_sha256, law_leaves[key].leaf_sha256, "derived_from"))
    for key, law_leaf in law_leaves.items():
        edges.append(GoldenEdge(mechanism_leaf.leaf_sha256, law_leaf.leaf_sha256, "contains"))
        if (law_leaf.payload.get("generation_receipt") or {}).get("frontier_certificate_sha256"):
            edges.append(GoldenEdge(search_leaf.leaf_sha256, law_leaf.leaf_sha256, "selects"))
    return store.append_bundle(leaves, edges, make_heads=True)


def _mechanism_graph(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compile the reusable strategy-to-portfolio consequence graph."""

    edges = []
    producers: dict[str, list[str]] = defaultdict(list)
    consumers: dict[str, list[str]] = defaultdict(list)
    for law in candidates:
        mechanism = law["mechanism"]
        consequence = str(mechanism["consequence_concept"])
        producers[consequence].append(str(law["law_key"]))
        for antecedent in mechanism["antecedent_concepts"]:
            antecedent = str(antecedent)
            consumers[antecedent].append(str(law["law_key"]))
            edges.append({
                "law_key": law["law_key"],
                "law_sha256": law["law_sha256"],
                "kind": mechanism["kind"],
                "from": antecedent,
                "to": consequence,
                "decision_use": law["decision_use"],
            })
    concepts = sorted(set(producers) | set(consumers))
    body = {
        "schema": "jaggedthoughts-investment-mechanism-graph-v1",
        "concepts": [
            {
                "concept_id": concept,
                "producer_law_keys": sorted(producers.get(concept, ())),
                "consumer_law_keys": sorted(consumers.get(concept, ())),
            }
            for concept in concepts
        ],
        "edges": sorted(edges, key=lambda row: (row["from"], row["to"], row["law_key"])),
        "composable_paths": [
            {
                "via_concept": concept,
                "producer_law_key": producer,
                "consumer_law_key": consumer,
            }
            for concept in concepts
            for producer in sorted(producers.get(concept, ()))
            for consumer in sorted(consumers.get(concept, ()))
            if producer != consumer
        ],
        "policy_sink": "paper_portfolio_utility_after_costs",
        "capital_authority": False,
    }
    return {**body, "mechanism_graph_sha256": stable_sha256(body)}


def institutional_learning_status(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    state = _read_json(root / "institutional_learning" / "latest.json")
    if state and state.get("schema") == LEARNING_STATE_SCHEMA:
        return state
    return {
        "schema": LEARNING_STATE_SCHEMA,
        "enabled": True,
        "status": "not_compiled",
        "candidate_count": 0,
        "phenotype_episode_count": 0,
        "settled_episode_count": 0,
        "transfer_candidate_count": 0,
        "promotion_eligible_count": 0,
        "next_activation": "Run the institutional learning cycle.",
        "capital_authority": False,
    }


def _historical_accounting_scope(root: Path) -> dict[str, Any]:
    snapshots = [
        row for path in sorted((root / "quality").glob("*.json"))
        if (row := _read_json(path)) and row.get("entity_id") and row.get("as_of")
    ]
    source_run = _read_json(root / "data" / "latest_source_run.json") or {}
    epochs = [str(row["as_of"]) for row in snapshots]
    if source_run.get("as_of"):
        epochs.append(str(source_run["as_of"]))
    as_of = max(epochs, default=_utc_now())
    body = {
        "as_of": as_of,
        "entity_ids": sorted({str(row["entity_id"]).upper() for row in snapshots}),
        "quality_report_sha256s": sorted({
            str(row.get("quality_report_sha256")) for row in snapshots
            if row.get("quality_report_sha256")
        }),
        "source_run_sha256": str(source_run.get("run_sha256") or ""),
    }
    return {**body, "input_sha256": stable_sha256(body)}


def _historical_rank_evaluation(
    episodes: Sequence[Mapping[str, Any]], metric_id: str,
) -> dict[str, Any]:
    candidate = {
        "estimator": {"expected_direction": "positive"},
        "validation": {
            "target_rho": 0.30, "alpha": 0.05, "power": 0.80,
            "minimum_cross_section": 4, "minimum_inference_blocks": 8,
            "holdout_fraction": 0.25, "counterexample_minimum_rows": 4,
            "counterexample_minimum_blocks": 2, "counterexample_abs_rho": 0.20,
        },
        "cohort": {"counterexample_fields": []},
    }
    scored = [{
        "episode_id": row["episode_id"], "entity_id": row["entity_id"],
        "opened_at": row["opened_at"], "inference_block_id": row["inference_block_id"],
        "categories": row["categories"],
        "predictor": row["metrics"][metric_id],
        "outcome": row["metrics"]["next_owner_earnings_margin"],
    } for row in episodes]
    result = _association_environment(candidate, scored, {"scope": "current_quality_cohort"})
    statistical_status = str(result.pop("status"))
    result["status"] = {
        "prospective_transfer_candidate": "retrospective_rank_signal_detected",
        "holdout_not_supportive": "retrospective_tail_not_supportive",
    }.get(statistical_status, statistical_status)
    result["estimator_status"] = statistical_status
    result["prospective_transfer_eligible"] = False
    result["formula_selected_before_sample"] = False
    return result


def _rank_percentiles(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        rank = (start + end + 1) / (2 * len(values))
        for position in range(start, end + 1):
            ranks[order[position]] = rank
        start = end + 1
    return ranks


def _incremental_durability_replay(
    episodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare persistence with persistence plus durability on later fiscal blocks."""

    by_block: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in episodes:
        by_block[str(row["inference_block_id"])].append(row)
    block_ids = sorted(by_block)
    rows = []
    for index, test_block_id in enumerate(block_ids):
        training_block_ids = block_ids[:index]
        training = [row for block_id in training_block_ids for row in by_block[block_id]]
        test = by_block[test_block_id]
        if len(training_block_ids) < 3 or len(training) < 30 or len(test) < 4:
            continue
        current = [float(row["metrics"]["current_owner_earnings_margin"]) for row in training]
        durability = [float(row["metrics"]["durable_earnings_power"]) for row in training]
        current_mean, durability_mean = mean(current), mean(durability)
        current_sd, durability_sd = stdev(current), stdev(durability)
        if min(current_sd, durability_sd) <= 1e-12:
            continue
        current = [(value - current_mean) / current_sd for value in current]
        durability = [(value - durability_mean) / durability_sd for value in durability]
        outcome_rank = []
        for block_id in training_block_ids:
            outcome_rank.extend(_rank_percentiles([
                float(row["metrics"]["next_owner_earnings_margin"])
                for row in by_block[block_id]
            ]))
        try:
            control_fit = ols_multichannel_r2(
                [current], outcome_rank, ["current_owner_earnings_margin"],
            )
            augmented_fit = ols_multichannel_r2(
                [current, durability], outcome_rank,
                ["current_owner_earnings_margin", "durable_earnings_power"],
            )
        except ValueError:
            continue
        if control_fit.get("error") or augmented_fit.get("error"):
            continue
        control_beta = control_fit["beta_exact"]
        augmented_beta = augmented_fit["beta_exact"]
        test_current = [
            (float(row["metrics"]["current_owner_earnings_margin"]) - current_mean) / current_sd
            for row in test
        ]
        test_durability = [
            (float(row["metrics"]["durable_earnings_power"]) - durability_mean) / durability_sd
            for row in test
        ]
        outcome = [float(row["metrics"]["next_owner_earnings_margin"]) for row in test]
        control_prediction = [control_beta[0] + control_beta[1] * value for value in test_current]
        augmented_prediction = [
            augmented_beta[0] + augmented_beta[1] * current_value
            + augmented_beta[2] * durability_value
            for current_value, durability_value in zip(test_current, test_durability, strict=True)
        ]
        control_rho = spearman_rho(control_prediction, outcome)
        augmented_rho = spearman_rho(augmented_prediction, outcome)
        if control_rho is None or augmented_rho is None:
            continue
        rows.append({
            "inference_block_id": test_block_id,
            "training_cutoff_block_id": training_block_ids[-1],
            "training_block_count": len(training_block_ids),
            "training_episode_count": len(training),
            "holdout_episode_count": len(test),
            "persistence_control_rho": control_rho,
            "persistence_plus_durability_rho": augmented_rho,
            "incremental_rho": augmented_rho - control_rho,
            "prior_fit_durability_coefficient": augmented_beta[2],
        })
    control = [float(row["persistence_control_rho"]) for row in rows]
    augmented = [float(row["persistence_plus_durability_rho"]) for row in rows]
    paired = paired_permutation_test(augmented, control, n_perm=20_000)
    deltas = [float(row["incremental_rho"]) for row in rows]
    detectable = None
    if len(deltas) > 1 and stdev(deltas) > 0:
        detectable = (
            NormalDist().inv_cdf(0.975) + NormalDist().inv_cdf(0.80)
        ) * stdev(deltas) / math.sqrt(len(deltas))
    estimate = mean(deltas) if deltas else None
    p_value = paired.get("p_value")
    status = "insufficient_prior_blocks"
    if estimate is not None:
        status = (
            "incremental_rank_information_supported"
            if p_value is not None and p_value < 0.05 and estimate > 0
            else "incremental_rank_information_harmful"
            if p_value is not None and p_value < 0.05 and estimate < 0
            else "no_supported_incremental_rank_information"
        )
    return {
        "status": status,
        "design": "expanding_prior_fiscal_blocks",
        "target": "within-prior-block next-owner-earnings-margin percentile",
        "cheap_control": "prior-fit current-owner-earnings-margin persistence",
        "augmented_model": "cheap_control plus durable-earnings-power",
        "minimum_training_blocks": 3,
        "minimum_training_episodes": 30,
        "holdout_block_count": len(rows),
        "holdout_episode_count": sum(int(row["holdout_episode_count"]) for row in rows),
        "mean_persistence_control_rho": mean(control) if control else None,
        "mean_persistence_plus_durability_rho": mean(augmented) if augmented else None,
        "mean_incremental_rho": estimate,
        "paired_block_test": paired,
        "power": {
            "alpha": 0.05,
            "target_power": 0.80,
            "minimum_detectable_mean_incremental_rho": detectable,
            "status": (
                "resolved" if estimate is not None and detectable is not None
                and abs(estimate) >= detectable else "underpowered_for_observed_difference"
            ),
        },
        "rows": rows,
        "adverse_transition_follow_up": {
            "status": (
                "eligible_for_separate_prior_frozen_test"
                if status == "incremental_rank_information_supported" else "not_activated"
            ),
            "activation_rule": "incremental rank information must first be supported",
            "reason": (
                "The incremental rank gate did not pass; testing another outcome now would be post-result search."
                if status != "incremental_rank_information_supported" else
                "Freeze an adverse-transition target and scoring rule before evaluating it."
            ),
        },
        "formula_selection_boundary": (
            "The model family and durable-earnings formula were selected after this history; only each "
            "block's coefficients and standardization were frozen on earlier fiscal blocks."
        ),
    }


def compile_historical_accounting_replay(
    workspace: str | Path, *, as_of: str | None = None,
    entity_ids: Iterable[str] | None = None,
    observations: Iterable[MetricObservation] | None = None,
) -> dict[str, Any]:
    """Replay deterministic quality formulas over filing-time accounting histories.

    The replay challenges a business-understanding mechanism.  It excludes market
    returns, records current-universe selection, and cannot promote a law or policy.
    """
    root = Path(workspace).expanduser().resolve()
    scope = _historical_accounting_scope(root)
    epoch = canonical_timestamp(as_of or scope["as_of"], "historical accounting replay as_of")
    entities = sorted({
        require_text(value, "historical accounting entity_id").upper()
        for value in (entity_ids if entity_ids is not None else scope["entity_ids"])
    })
    packet_rows = tuple(observations) if observations is not None else None
    histories = (
        compile_company_quality_histories_from_observations(
            entity_ids=entities, observations=packet_rows, as_of=epoch,
        ) if packet_rows is not None else compile_company_quality_histories(
            entity_ids=entities, observations_path=root / "data" / "observations.csv",
            as_of=epoch,
        )
    )
    episodes = []
    source_rows = []
    for entity, reports in histories.items():
        for current, future in zip(reports, reports[1:]):
            opened_at = str(current["available_at"])
            outcome_available_at = str(future["available_at"])
            if timestamp_key(outcome_available_at) <= timestamp_key(opened_at):
                continue
            current_margin = (current["history"][-1] or {}).get("owner_earnings_margin")
            future_margin = (future["history"][-1] or {}).get("owner_earnings_margin")
            durability = (current.get("scores") or {}).get("durable_earnings_power")
            if any(
                value is None or not math.isfinite(float(value))
                for value in (current_margin, future_margin, durability)
            ):
                continue
            next_fiscal_head = str(future["history"][-1]["observed_at"])
            episode_body = {
                "schema": PHENOTYPE_EPISODE_SCHEMA,
                "episode_id": f"accounting-replay:{entity}:{next_fiscal_head}",
                "inference_block_id": f"fiscal-year:{next_fiscal_head[:4]}",
                "entity_id": entity, "entity_kind": "public_equity",
                "horizon_days": max(1, (
                    timestamp_key(outcome_available_at) - timestamp_key(opened_at)
                ).days),
                "opened_at": opened_at, "end_at": outcome_available_at,
                "outcome_available_at": outcome_available_at,
                "settlement_status": "settled",
                "metrics": {
                    "durable_earnings_power": float(durability),
                    "current_owner_earnings_margin": float(current_margin),
                    "next_owner_earnings_margin": float(future_margin),
                },
                "metric_roles": {
                    "predictor_metric_ids": [
                        "durable_earnings_power", "current_owner_earnings_margin",
                    ],
                    "outcome_metric_ids": ["next_owner_earnings_margin"],
                },
                "categories": {
                    "cohort_scope": "current_quality_coverage",
                    "next_fiscal_year": next_fiscal_head[:4],
                },
                "source_refs": sorted({
                    *(str(value) for value in current.get("source_refs") or ()),
                    *(str(value) for value in future.get("source_refs") or ()),
                    f"quality-report:{current['quality_report_sha256']}",
                    f"quality-report:{future['quality_report_sha256']}",
                }),
                "point_in_time": True,
            }
            episode = {
                **episode_body,
                "phenotype_episode_sha256": stable_sha256(episode_body),
            }
            episodes.append(episode)
            source_rows.extend((
                {
                    "source_id": f"predictor:{current['quality_report_sha256']}",
                    "available_at": opened_at, "as_of": opened_at,
                },
                {
                    "source_id": f"outcome:{future['quality_report_sha256']}",
                    "available_at": outcome_available_at, "as_of": outcome_available_at,
                },
            ))
    episodes.sort(key=lambda row: (row["inference_block_id"], row["entity_id"]))
    integrity_receipt = compile_evaluation_integrity_receipt(
        temporal_design="historical_replay", generation_processes=("deterministic",),
        source_availability_rows=source_rows,
    )
    integrity = {
        key: value for key, value in integrity_receipt.items()
        if key != "evaluation_integrity_sha256"
    }
    integrity.update({
        "outcome_domain": "business_accounting",
        "alpha_evidence_eligible": False,
        "sufficient_for_alpha_claim": False,
        "paper_policy_authority": False,
        "capital_authority": False,
        "reason": (
            f"{integrity['reason']} This replay evaluates a business-accounting "
            "mechanism and contains no security-return outcome."
        ),
    })
    integrity["evaluation_integrity_sha256"] = stable_sha256(integrity)
    durability = _historical_rank_evaluation(episodes, "durable_earnings_power")
    persistence = _historical_rank_evaluation(episodes, "current_owner_earnings_margin")
    incremental = _incremental_durability_replay(episodes)
    durability_blocks = {
        str(row["inference_block_id"]): float(row["rho"])
        for row in durability["block_information_coefficients"] if row.get("rho") is not None
    }
    persistence_blocks = {
        str(row["inference_block_id"]): float(row["rho"])
        for row in persistence["block_information_coefficients"] if row.get("rho") is not None
    }
    common_blocks = sorted(set(durability_blocks) & set(persistence_blocks))
    block_deltas = [{
        "inference_block_id": block,
        "durability_rho": durability_blocks[block],
        "persistence_rho": persistence_blocks[block],
        "durability_minus_persistence": durability_blocks[block] - persistence_blocks[block],
    } for block in common_blocks]
    mean_delta = (
        mean(row["durability_minus_persistence"] for row in block_deltas)
        if block_deltas else None
    )
    body = {
        "schema": HISTORICAL_ACCOUNTING_REPLAY_SCHEMA,
        "generated_at": epoch,
        "input_sha256": stable_sha256({
            **scope, "as_of": epoch, "entity_ids": entities,
            "observation_ids": (
                sorted(row.observation_id for row in packet_rows)
                if packet_rows is not None else "workspace_observations_csv"
            ),
        }),
        "question": (
            "Does the deterministic durable-earnings score rank next-fiscal-year owner-earnings "
            "margin better than the current-margin persistence control?"
        ),
        "temporal_design": "deterministic_filing_time_replay",
        "model_selection_status": "current_formula_replayed_over_prior_filings",
        "cohort_sampling": "current_quality_coverage_conditioned",
        "entity_count": len({row["entity_id"] for row in episodes}),
        "episode_count": len(episodes),
        "inference_block_count": len({row["inference_block_id"] for row in episodes}),
        "evaluation_integrity": integrity,
        "durability_model": durability,
        "persistence_control": persistence,
        "paired_block_comparison": {
            "block_count": len(block_deltas), "rows": block_deltas,
            "mean_durability_minus_persistence": mean_delta,
            "verdict": (
                "durability_ranked_the_target_better" if mean_delta is not None and mean_delta > 0
                else "persistence_ranked_the_target_better" if mean_delta is not None
                else "insufficient_common_blocks"
            ),
        },
        "incremental_out_of_time_comparison": incremental,
        "episodes": episodes,
        "status": "settled_mechanism_diagnostic" if episodes else "insufficient_history",
        "return_outcome_included": False,
        "llm_generation_process_included": False,
        "survivorship_controlled": False,
        "promotion_eligible": False,
        "capital_authority": False,
        "boundaries": [
            "The source packet is point-in-time; the current formula was selected after the historical sample.",
            "Incremental coefficients and feature standardization use earlier fiscal blocks only; the tested model family remains post-period selected.",
            "The cohort is conditioned on companies with current quality coverage and does not control survivorship.",
            "The outcome is an accounting margin, not a security return or benchmark-relative alpha.",
            "Subscription-model historical answers are excluded because source timestamps cannot remove parameter memory.",
        ],
    }
    return {**body, "replay_sha256": stable_sha256(body)}


def _historical_accounting_projection(replay: Mapping[str, Any]) -> dict[str, Any]:
    durability = dict(replay.get("durability_model") or {})
    persistence = dict(replay.get("persistence_control") or {})
    return {
        key: replay.get(key) for key in (
            "schema", "generated_at", "status", "replay_sha256", "question",
            "entity_count", "episode_count", "inference_block_count",
            "model_selection_status", "cohort_sampling", "return_outcome_included",
            "survivorship_controlled", "promotion_eligible", "capital_authority",
        )
    } | {
        "evaluation_integrity": dict(replay.get("evaluation_integrity") or {}),
        "durability_model": {
            "status": durability.get("status"),
            "pooled_rank_correlation": durability.get("pooled_rank_correlation"),
            "chronological_holdout": durability.get("chronological_holdout"),
        },
        "persistence_control": {
            "status": persistence.get("status"),
            "pooled_rank_correlation": persistence.get("pooled_rank_correlation"),
            "chronological_holdout": persistence.get("chronological_holdout"),
        },
        "paired_block_comparison": {
            key: (replay.get("paired_block_comparison") or {}).get(key)
            for key in ("block_count", "mean_durability_minus_persistence", "verdict")
        },
        "incremental_out_of_time_comparison": {
            key: (replay.get("incremental_out_of_time_comparison") or {}).get(key)
            for key in (
                "status", "design", "cheap_control", "augmented_model",
                "holdout_block_count", "holdout_episode_count",
                "mean_persistence_control_rho",
                "mean_persistence_plus_durability_rho", "mean_incremental_rho",
                "paired_block_test", "power", "adverse_transition_follow_up",
                "formula_selection_boundary",
            )
        },
        "artifact": "institutional_learning/historical_accounting_replay/latest.json",
        "boundaries": list(replay.get("boundaries") or ()),
    }


def run_institutional_learning_cycle(
    workspace: str | Path, *, owner: str, store_path: str | Path,
    catalog_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compile phenotype cohorts, challenge laws, and persist learning state."""

    root = Path(workspace).expanduser().resolve()
    catalog_source = Path(catalog_path) if catalog_path else root / "institutional_learning" / "laws.yaml"
    catalog = load_law_catalog(catalog_source)
    move_library = _read_json(
        root / "institutional_learning" / "strategy_moves" / "latest.json"
    ) or {}
    strategy_plan = _read_json(
        root / "institutional_learning" / "strategy_cohorts" / "latest.json"
    ) or {}
    strategy_candidates = compile_strategy_law_candidates(move_library, strategy_plan)
    candidates = [
        *catalog["candidates"], *_load_generated_candidates(root), *strategy_candidates,
    ]
    store = GoldenStore(store_path) if Path(store_path).exists() else None
    settlements = {
        str(row["run_id"]): row
        for path in sorted((root / "closed_book" / "settlements").glob("*.json"))
        if (row := _read_json(path)) and row.get("run_id")
    }
    market_catalog = _read_json(root / "universe" / "catalog-latest.json") or {}
    entity_metadata = {
        str(row.get("symbol") or "").upper(): row
        for row in market_catalog.get("securities") or ()
        if isinstance(row, Mapping) and row.get("symbol")
    }
    episodes = [
        _phenotype_episode(
            run, settlements.get(str(run.get("run_id") or "")), store,
            entity_metadata, owner,
        )
        for path in sorted((root / "closed_book" / "runs").glob("*.json"))
        if (run := _read_json(path)) and run.get("schema") == CLOSED_BOOK_RUN_SCHEMA
    ]
    strategy_causal_panel = _compile_strategy_causal_panel(root)
    prior = institutional_learning_status(root)
    generated_at = _next_epoch(prior.get("generated_at"))
    law_search = search_law_programs(episodes, candidates, generated_at)
    new_abduced_laws = []
    generated_dir = root / "institutional_learning" / "laws" / "generated"
    existing_hashes = {row["law_sha256"] for row in candidates}
    for raw in law_search.get("proposals") or ():
        proposal = compile_law_candidate(raw)
        if proposal["law_sha256"] in existing_hashes:
            continue
        existing_hashes.add(proposal["law_sha256"])
        _atomic_json(generated_dir / f"{proposal['law_key'].replace('@', '--')}.json", proposal)
        candidates.append(proposal)
        new_abduced_laws.append(proposal)
    mechanism_graph = _mechanism_graph(candidates)
    historical_accounting_scope = _historical_accounting_scope(root)
    input_body = {
        "engine_version": INSTITUTIONAL_LEARNING_ENGINE_VERSION,
        "catalog_sha256": catalog["catalog_sha256"],
        "law_search_policy": law_search["policy"],
        "law_sha256s": [row["law_sha256"] for row in candidates],
        "phenotype_episode_sha256s": [row["phenotype_episode_sha256"] for row in episodes],
        "panel_sha256s": [
            stable_sha256(_load_panel_rows(root, str(row["law_id"])))
            for row in candidates if row["estimator"]["kind"] == _DID
        ],
        "strategy_panel_readiness_sha256": strategy_causal_panel["readiness_sha256"],
        "historical_accounting_input_sha256": historical_accounting_scope["input_sha256"],
    }
    input_sha = stable_sha256(input_body)
    if prior.get("input_sha256") == input_sha:
        return {"ok": True, "status": "replayed", "state": prior, "capital_authority": False}
    historical_accounting_replay = compile_historical_accounting_replay(
        root, as_of=historical_accounting_scope["as_of"],
        entity_ids=historical_accounting_scope["entity_ids"],
    )
    cohorts = [_cohort_phenotype(row, episodes, generated_at) for row in candidates]
    cohort_by_key = {str(row["law_key"]): row for row in cohorts}
    evaluations = []
    for candidate in candidates:
        if candidate["estimator"]["kind"] == _ASSOCIATION:
            evaluation = _association_evaluation(
                candidate, cohort_by_key[candidate["law_key"]], episodes, generated_at,
            )
        else:
            evaluation = evaluate_difference_in_differences(
                candidate, _load_panel_rows(root, str(candidate["law_id"])), generated_at=generated_at,
            )
            evaluation["cohort_sha256"] = cohort_by_key[candidate["law_key"]]["cohort_sha256"]
        evaluations.append(evaluation)
    p_values = []
    for evaluation in evaluations:
        for index, environment in enumerate(evaluation.get("environment_evaluations") or ()):
            p_value = environment.get("pooled_two_sided_p_value")
            if p_value is not None:
                p_values.append((f"{evaluation['law_key']}::{index}", float(p_value)))
    fdr = {row["label"]: row for row in bh_fdr(p_values, alpha=0.05)}
    finalized = []
    for evaluation in evaluations:
        labels = [
            f"{evaluation['law_key']}::{index}"
            for index, _row in enumerate(evaluation.get("environment_evaluations") or ())
        ]
        family_rows = [fdr[label] for label in labels if label in fdr]
        eligible = (
            evaluation.get("status") == "prospective_transfer_candidate"
            and bool(family_rows)
            and all(row["rejected_at_alpha"] for row in family_rows)
            and (
                evaluation.get("strategy_regularity") is None
                or bool((evaluation["strategy_regularity"].get("prospective_holdout") or {}).get("eligible"))
            )
        )
        body = {
            **evaluation,
            "multiplicity": {
                "method": "Benjamini-Hochberg",
                "family": "all scored law × environment trials in this compilation",
                "trial_count": len(p_values),
                "rows": family_rows,
            },
            "promotion_eligible": eligible,
            "capital_authority": False,
        }
        body.pop("evaluation_sha256", None)
        finalized.append({**body, "evaluation_sha256": stable_sha256(body)})
    new_refinements = []
    for candidate, evaluation in zip(candidates, finalized, strict=True):
        proposals = [
            *(evaluation.get("refinement_proposals") or ()),
            *(
            proposal
            for environment in evaluation.get("environment_evaluations") or ()
            for proposal in environment.get("refinement_proposals") or ()
            ),
        ]
        unique_proposals = {
            stable_sha256(proposal): proposal for proposal in proposals
        }
        for proposal in list(unique_proposals.values())[:3]:
            refinement = _compile_refinement(candidate, proposal, generated_at)
            if refinement["law_sha256"] in existing_hashes:
                continue
            existing_hashes.add(refinement["law_sha256"])
            _atomic_json(generated_dir / f"{refinement['law_key'].replace('@', '--')}.json", refinement)
            new_refinements.append(refinement)
    if not episodes:
        status = "awaiting_point_in_time_episodes"
        next_activation = "Open closed-book episodes for compatible public-market candidates."
    elif not any(row["settlement_status"] == "settled" for row in episodes):
        status = "prospective_cohorts_frozen"
        next_end = min(str(row["end_at"]) for row in episodes)
        next_activation = f"Settle the first matured cohort at or after {next_end}."
    elif any(row["status"] == "challenged_by_counterexample" for row in finalized):
        status = "counterexample_refinement_generated"
        next_activation = "Collect post-counterexample episodes for the generated domain refinement."
    else:
        status = "learning_from_settled_cohorts"
        next_activation = "Keep settling exact-version blocks until holdout and power gates discriminate laws."
    state_body = {
        "schema": LEARNING_STATE_SCHEMA,
        "enabled": True,
        "generated_at": generated_at,
        "status": status,
        "input_sha256": input_sha,
        "engine_version": INSTITUTIONAL_LEARNING_ENGINE_VERSION,
        "catalog_sha256": catalog["catalog_sha256"],
        "candidate_count": len(candidates),
        "seed_candidate_count": len(catalog["candidates"]),
        "strategy_candidate_count": len(strategy_candidates),
        "generated_candidate_count": len(candidates) - len(catalog["candidates"]),
        "new_abduced_law_count": len(new_abduced_laws),
        "new_refinement_count": len(new_refinements),
        "phenotype_episode_count": len(episodes),
        "settled_episode_count": sum(row["settlement_status"] == "settled" for row in episodes),
        "pending_episode_count": sum(row["settlement_status"] != "settled" for row in episodes),
        "inference_block_count": len({row["inference_block_id"] for row in episodes}),
        "cross_industry_cohort_count": sum(bool(row["cross_industry_ready"]) for row in cohorts),
        "transfer_candidate_count": sum(row["status"] == "prospective_transfer_candidate" for row in finalized),
        "promotion_eligible_count": sum(bool(row["promotion_eligible"]) for row in finalized),
        "strategy_regularity_count": sum(row.get("strategy_regularity") is not None for row in finalized),
        "prospective_strategy_regularity_count": sum(
            (row.get("strategy_regularity") or {}).get("status") == "prospective_transfer_candidate"
            for row in finalized
        ),
        "candidates": candidates,
        "cohorts": cohorts,
        "evaluations": finalized,
        "strategy_regularities": [
            row["strategy_regularity"] for row in finalized if row.get("strategy_regularity")
        ],
        "phenotype_episodes": episodes,
        "law_search": law_search,
        "mechanism_graph": mechanism_graph,
        "strategy_causal_panel": strategy_causal_panel,
        "historical_accounting_replay": _historical_accounting_projection(
            historical_accounting_replay
        ),
        "new_abduced_laws": new_abduced_laws,
        "new_refinements": new_refinements,
        "law_grammar": {
            "predictor_ast": "jaggedthoughts-signal-definition-v1",
            "operators": list(SIGNAL_OPERATOR_CONTRACT),
            "estimators": [_ASSOCIATION, _DID],
            "soundness": {
                "prospective_activation": "not_before is at or after law creation",
                "target_separation": "outcome metrics cannot enter predictors or cohort selection",
                "mechanism_separation": "a consequence cannot be its own unlagged antecedent",
            },
            "lifecycle": [
                "observed", "phenotyped", "conjectured", "challenged",
                "prospectively_tested", "transfer_candidate", "policy_review",
            ],
            "cegar": (
                "A reversed subgroup or environment is preserved as a counterexample. "
                "Any narrower candidate starts after that evidence became available."
            ),
        },
        "next_activation": next_activation,
        "authority": "paper_shadow_learning_only",
        "capital_authority": False,
        "boundaries": [
            "One inference block is one market-history epoch; a cross-section does not create many independent histories.",
            "A supported association is predictive evidence, not a causal effect.",
            "Difference-in-differences requires a source-bound treatment panel and a parallel-trend diagnostic.",
            "Generated refinements cannot reuse the counterexample sample for promotion.",
        ],
    }
    state = {**state_body, "state_sha256": stable_sha256(state_body)}
    for candidate in candidates:
        _atomic_json(root / "institutional_learning" / "laws" / "compiled" / f"{candidate['law_key'].replace('@', '--')}.json", candidate)
    for cohort in cohorts:
        _atomic_json(root / "institutional_learning" / "cohorts" / f"{cohort['law_key'].replace('@', '--')}.json", cohort)
    for evaluation in finalized:
        _atomic_json(root / "institutional_learning" / "evaluations" / f"{evaluation['law_key'].replace('@', '--')}.json", evaluation)
    _atomic_json(
        root / "institutional_learning" / "historical_accounting_replay" / "latest.json",
        historical_accounting_replay,
    )
    golden_record = _record_learning_graph(
        GoldenStore(store_path), owner, candidates, cohorts, finalized, episodes,
        law_search, mechanism_graph, generated_at,
    )
    state = {**state, "golden_record": golden_record}
    _atomic_json(root / "institutional_learning" / "runs" / f"learning-{state['state_sha256'][:20]}.json", state)
    _atomic_json(root / "institutional_learning" / "latest.json", state)
    from .search_trial_census import register_current_institutional_law_family

    trial_family = register_current_institutional_law_family(root, state, owner=owner)
    return {
        "ok": True, "status": "compiled", "state": state,
        "golden_record": golden_record, "trial_family": trial_family,
        "capital_authority": False,
    }


__all__ = [
    "CAUSAL_PANEL_ROW_SCHEMA",
    "COHORT_PHENOTYPE_SCHEMA",
    "LAW_CANDIDATE_SCHEMA",
    "LAW_CATALOG_SCHEMA",
    "LAW_EVALUATION_SCHEMA",
    "LAW_POLICY_INFLUENCE_SCHEMA",
    "INSTITUTIONAL_LEARNING_ENGINE_VERSION",
    "HISTORICAL_ACCOUNTING_REPLAY_SCHEMA",
    "LEARNING_STATE_SCHEMA",
    "PHENOTYPE_EPISODE_SCHEMA",
    "STRATEGY_REGULARITY_SCHEMA",
    "compile_historical_accounting_replay",
    "compile_law_candidate",
    "compile_strategy_law_candidates",
    "compile_workspace_strategy_causal_panel",
    "compile_law_policy_influence",
    "default_law_catalog",
    "evaluate_difference_in_differences",
    "evaluate_investment_law",
    "institutional_learning_status",
    "load_law_catalog",
    "run_institutional_learning_cycle",
]
