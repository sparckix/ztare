"""Lower one source-bound strategy program into conditional valuation paths."""

from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import (
    canonical_timestamp,
    require_finite,
    require_refs,
    require_text,
    timestamp_key,
)
from .valuation import (
    ValuationAssumption,
    ValuationEnvelope,
    ValuationScenario,
    compile_hurdle_price_frontier,
    compile_valuation_envelope,
)


SCHEMA = "jaggedthoughts-strategy-valuation-bridge-v1"
CONTINGENT_POLICY_PAYOFF_SCHEMA = (
    "jaggedthoughts-contingent-policy-payoff-frontier-v1"
)
_COORDINATES = (
    "revenue_growth_delta",
    "owner_earnings_margin_delta",
    "reinvestment_growth_delta",
    "durability_terminal_growth_delta",
)
_DIRECT_EFFECT_IDENTITIES = {
    "revenue_growth_delta": ("revenue_growth", "decimal"),
    "owner_earnings_margin_delta": ("owner_earnings_margin", "decimal"),
    "reinvestment_growth_delta": ("reinvestment_growth", "decimal"),
    "durability_terminal_growth_delta": ("terminal_growth", "decimal"),
}


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _verified_payload(value: Mapping[str, Any], hash_field: str, label: str) -> dict[str, Any]:
    row = dict(value)
    digest = _digest(row.pop(hash_field, None), f"{label} {hash_field}")
    if stable_sha256(row) != digest:
        raise ValueError(f"{label} content hash mismatch")
    return {**row, hash_field: digest}


def _range(
    raw: Any, coordinate: str, allowed_refs: set[str],
    *, bound_metric_id: str, bound_unit: str,
    bound_effects: tuple[Mapping[str, Any], ...],
) -> tuple[float, float, tuple[str, ...], dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{coordinate} must be a mapping")
    if raw.get("unit") != "decimal":
        raise ValueError(f"{coordinate} unit must be decimal")
    low = require_finite(raw.get("low"), f"{coordinate} low")
    high = require_finite(raw.get("high"), f"{coordinate} high")
    if not -0.95 <= low <= high <= 0.95:
        raise ValueError(f"{coordinate} bounds must satisfy -0.95 <= low <= high <= 0.95")
    refs = require_refs(raw.get("source_refs") or (), f"{coordinate} source ref")
    unknown = set(refs) - allowed_refs
    if unknown:
        raise ValueError(f"{coordinate} cites evidence outside the bound strategy program: {sorted(unknown)}")
    kind = require_text(raw.get("translation_kind"), f"{coordinate} translation_kind")
    metric_id = require_text(raw.get("metric_id"), f"{coordinate} metric_id")
    metric_unit = require_text(raw.get("metric_unit"), f"{coordinate} metric_unit")
    if (metric_id, metric_unit) != (bound_metric_id, bound_unit):
        raise ValueError(f"{coordinate} crossed the bound effect metric or unit")
    if kind == "direct_effect":
        raise ValueError(
            f"{coordinate} direct effect requires a price-epoch-bound expectation residual"
        )
    if kind == "conditional_conjecture":
        translation = {
            "translation_kind": kind, "metric_id": metric_id,
            "metric_unit": metric_unit,
            "conjecture_id": require_text(raw.get("conjecture_id"), f"{coordinate} conjecture_id"),
            "falsifier": require_text(raw.get("falsifier"), f"{coordinate} falsifier"),
            "causal_translation_earned": False,
        }
    else:
        raise ValueError(f"{coordinate} translation_kind is unsupported")
    return low, high, refs, translation


def compile_strategy_valuation_bridge(
    *,
    candidate_leaf: str,
    candidate: Mapping[str, Any],
    strategy_frontier: Mapping[str, Any],
    strategy_move: Mapping[str, Any],
    effect_contract: Mapping[str, Any],
    effect_binding: Mapping[str, Any],
    program_id: str,
    baseline_envelope: ValuationEnvelope | Mapping[str, Any],
    baseline_scenario_id: str,
    coordinate_ranges: Mapping[str, Mapping[str, Any]],
    excess_return_hurdle: float,
) -> dict[str, Any]:
    """Compile bounded agent proposals; retain all decision authority upstream."""

    leaf = _digest(candidate_leaf, "candidate_leaf")
    candidate_row = _verified_payload(candidate, "candidate_sha256", "candidate")
    frontier = _verified_payload(
        strategy_frontier, "strategy_frontier_sha256", "strategy frontier",
    )
    contract = _verified_payload(effect_contract, "effect_contract_sha256", "effect contract")
    binding = _verified_payload(effect_binding, "binding_sha256", "effect binding")
    baseline = (
        baseline_envelope.to_dict()
        if isinstance(baseline_envelope, ValuationEnvelope)
        else _verified_payload(baseline_envelope, "envelope_sha256", "baseline envelope")
    )

    entity_id = require_text(candidate_row.get("entity_id"), "candidate entity_id")
    candidate_sha = candidate_row["candidate_sha256"]
    epoch = canonical_timestamp(candidate_row.get("as_of"), "candidate as_of")
    company = dict(frontier.get("company") or {})
    move_sha = _digest(strategy_move.get("move_sha256"), "strategy move_sha256")
    choice_sha = _digest(
        strategy_move.get("strategy_choice_identity_sha256"),
        "strategy choice_identity_sha256",
    )
    phenotype_sha = _digest(
        strategy_move.get("mechanism_phenotype_sha256"), "mechanism phenotype_sha256",
    )
    if (
        company.get("candidate_leaf") != leaf
        or company.get("candidate_sha256") != candidate_sha
        or strategy_move.get("candidate_leaf") != leaf
        or strategy_move.get("candidate_sha256") != candidate_sha
        or str(company.get("id") or "").upper() != entity_id.upper()
        or str(strategy_move.get("entity_id") or "").upper() != entity_id.upper()
        or strategy_move.get("strategy_frontier_sha256") != frontier["strategy_frontier_sha256"]
    ):
        raise ValueError("strategy valuation inputs crossed candidate identity")
    if any(str(value) != epoch for value in (
        frontier.get("evidence_epoch"), strategy_move.get("evidence_epoch"),
        baseline.get("evidence_epoch"), (binding.get("antecedent_assessment") or {}).get("as_of"),
    )):
        raise ValueError("strategy valuation inputs crossed evidence epoch")
    if str(baseline.get("entity_id") or "").upper() != entity_id.upper():
        raise ValueError("baseline valuation crossed entity identity")
    bound_effects = list(binding.get("transported_effects") or ())
    contract_effects = list(contract.get("estimates") or ())
    bound_target = dict(binding.get("target") or {})
    if (
        binding.get("status") != "bound_for_model_proposal"
        or (binding.get("target") or {}).get("move_sha256") != move_sha
        or ((binding.get("target") or {}).get("environment") or {}).get(
            "mechanism_phenotype_sha256"
        ) != phenotype_sha
        or (binding.get("antecedent_assessment") or {}).get("target_move_sha256") != move_sha
        or not bound_effects
        or any(effect not in contract_effects for effect in bound_effects)
        or contract.get("metric_id") != bound_target.get("metric_id")
        or contract.get("unit") != bound_target.get("unit")
    ):
        raise ValueError("strategy effect is not bound to the target move")

    selected_program = next((
        dict(row) for row in frontier.get("programs") or ()
        if row.get("program_id") == program_id
    ), None)
    if selected_program is None:
        raise ValueError("strategy program is absent from the exact frontier")
    if strategy_move.get("option_id") not in set(selected_program.get("unique_option_ids") or ()):
        raise ValueError("target strategy move is absent from the selected program")
    frontier_option = next((
        row for row in frontier.get("option_catalog") or ()
        if row.get("option_id") == strategy_move.get("option_id")
    ), None)
    if not frontier_option or frontier_option.get("option_sha256") != strategy_move.get("option_sha256"):
        raise ValueError("strategy move crossed option identity")

    allowed_refs = {
        str(ref) for ref in (
            *selected_program.get("evidence_refs", ()), *strategy_move.get("evidence_refs", ()),
            *(ref for row in bound_effects for ref in row.get("source_refs") or ()),
        ) if ref
    }
    unknown_coordinates = sorted(set(coordinate_ranges) - set(_COORDINATES))
    parsed = {
        coordinate: _range(
            coordinate_ranges[coordinate], coordinate, allowed_refs,
            bound_metric_id=str(bound_target["metric_id"]),
            bound_unit=str(bound_target["unit"]),
            bound_effects=tuple(bound_effects),
        )
        for coordinate in _COORDINATES if coordinate in coordinate_ranges
    }
    gaps = [
        {"coordinate": coordinate, "reason": "unsupported_coordinate"}
        for coordinate in unknown_coordinates
    ] + [
        {"coordinate": coordinate, "reason": "source_bound_range_missing"}
        for coordinate in _COORDINATES if coordinate not in parsed
    ]

    baseline_scenario = next((
        row for row in baseline.get("scenarios") or ()
        if row.get("scenario_id") == baseline_scenario_id
    ), None)
    if baseline_scenario is None:
        raise ValueError("baseline scenario is absent from the exact valuation envelope")
    assumptions = {
        str(row["assumption_id"]): row for row in baseline.get("assumptions") or ()
    }
    scenario_assumptions = [assumptions[value] for value in baseline_scenario["assumption_ids"]]
    base_owner = next((row for row in scenario_assumptions if row["assumption_type"] == "OwnerEarnings"), None)
    if base_owner is None:
        owner_rows = [row for row in assumptions.values() if row["assumption_type"] == "OwnerEarnings"]
        base_owner = owner_rows[0] if len(owner_rows) == 1 else None
    base_growth = next((row for row in scenario_assumptions if row["assumption_type"] == "ForecastGrowth"), None)
    base_terminal = next((row for row in scenario_assumptions if row["assumption_type"] == "TerminalGrowth"), None)
    if not all((base_owner, base_growth, base_terminal)):
        raise ValueError("baseline scenario must resolve one owner-earnings, forecast-growth, and terminal-growth path")

    invariant_rows = [
        row for row in assumptions.values()
        if row["assumption_type"] not in {"OwnerEarnings", "ForecastGrowth", "TerminalGrowth"}
    ]
    range_corners = tuple(dict.fromkeys((
        tuple(parsed.get(coordinate, (0.0, 0.0, ()))[0] for coordinate in _COORDINATES),
        tuple(parsed.get(coordinate, (0.0, 0.0, ()))[1] for coordinate in _COORDINATES),
    )))
    generated_assumptions = [
        ValuationAssumption(
            str(row["assumption_id"]), str(row["assumption_type"]), float(row["value"]),
            str(row["unit"]), tuple(row.get("source_refs") or ()),
        ) for row in invariant_rows
    ]
    scenarios = []
    coordinates = []
    for index, values in enumerate(range_corners, 1):
        revenue, margin, reinvestment, durability = values
        scenario_id = f"strategy-{program_id[:12]}-{index}"
        refs = sorted({
            *baseline_scenario.get("source_refs", ()),
            *(ref for coordinate in _COORDINATES for ref in parsed.get(coordinate, (0, 0, ()))[2]),
        })
        ids = (f"{scenario_id}-owner-earnings", f"{scenario_id}-growth", f"{scenario_id}-terminal")
        generated_assumptions.extend((
            ValuationAssumption(ids[0], "OwnerEarnings", float(base_owner["value"]) * (1 + margin), "currency/year", tuple(refs)),
            ValuationAssumption(ids[1], "ForecastGrowth", float(base_growth["value"]) + revenue + reinvestment, "decimal", tuple(refs)),
            ValuationAssumption(ids[2], "TerminalGrowth", float(base_terminal["value"]) + durability, "decimal", tuple(refs)),
        ))
        scenarios.append(ValuationScenario(
            scenario_id, move_sha, ids, tuple(refs),
        ))
        coordinates.append({
            "scenario_id": scenario_id,
            "revenue_growth_delta": revenue,
            "owner_earnings_margin_delta": margin,
            "reinvestment_growth_delta": reinvestment,
            "durability_terminal_growth_delta": durability,
            "lowered_owner_earnings": float(base_owner["value"]) * (1 + margin),
            "lowered_forecast_growth": float(base_growth["value"]) + revenue + reinvestment,
            "lowered_terminal_growth": float(base_terminal["value"]) + durability,
        })

    envelope = compile_valuation_envelope(
        envelope_id=f"strategy:{leaf[:12]}:{program_id}", entity_id=entity_id,
        evidence_epoch=epoch, grammar_id="jaggedthoughts.strategy-valuation",
        grammar_version="1", assumptions=generated_assumptions, scenarios=scenarios,
        max_depth=4, max_programs=100,
    )
    hurdle = compile_hurdle_price_frontier(
        envelope, excess_return_hurdle=excess_return_hurdle,
    )
    body = {
        "schema": SCHEMA,
        "candidate_leaf": leaf, "candidate_sha256": candidate_sha,
        "entity_id": entity_id, "evidence_epoch": epoch,
        "strategy_frontier_sha256": frontier["strategy_frontier_sha256"],
        "strategy_program_id": program_id, "move_sha256": move_sha,
        "strategy_choice_identity_sha256": choice_sha,
        "mechanism_phenotype_sha256": phenotype_sha,
        "effect_contract_sha256": contract["effect_contract_sha256"],
        "effect_binding_sha256": binding["binding_sha256"],
        "baseline_envelope_sha256": baseline["envelope_sha256"],
        "baseline_scenario_id": baseline_scenario_id,
        "coordinate_contract": {
            "owner_earnings": "baseline_owner_earnings * (1 + owner_earnings_margin_delta)",
            "forecast_growth": "baseline_forecast_growth + revenue_growth_delta + reinvestment_growth_delta",
            "terminal_growth": "baseline_terminal_growth + durability_terminal_growth_delta",
            "corner_policy": "joint_low_and_joint_high",
        },
        "coordinate_ranges": {
            coordinate: {"low": values[0], "high": values[1], "unit": "decimal",
                         "source_refs": list(values[2]), **values[3]}
            for coordinate, values in parsed.items()
        },
        "causal_translation_earned": bool(parsed) and all(
            values[3]["causal_translation_earned"] for values in parsed.values()
        ),
        "scenario_coordinates": coordinates,
        "unsupported_coordinate_gaps": gaps,
        "status": "compiled_with_gaps" if gaps else "compiled",
        "valuation_envelope": envelope.to_dict(),
        "hurdle_price_frontier": hurdle,
        "authority": {
            "security_rank": False, "decision": False, "portfolio": False,
            "order": False, "capital": False,
        },
    }
    return {**body, "bridge_sha256": stable_sha256(body)}


def compile_strategy_valuation_bridge_readiness(
    law_induction: Mapping[str, Any], *, generated_at: str,
) -> dict[str, Any]:
    """Expose the exact activation point before any cash-flow translation is requested."""

    epoch = canonical_timestamp(generated_at, "strategy valuation bridge generated_at")
    rows = [
        dict(row) for row in law_induction.get("candidates") or ()
        if isinstance(row, Mapping)
    ]
    transported = [
        row for row in rows
        if (row.get("effect_estimate") or {}).get("status")
        == "transported_magnitude_available"
        and (row.get("effect_estimate") or {}).get("estimates")
    ]
    direct = [
        row for row in transported
        if any(
            (estimate.get("metric_id"), estimate.get("unit"))
            in set(_DIRECT_EFFECT_IDENTITIES.values())
            for estimate in (row.get("effect_estimate") or {}).get("estimates") or ()
        )
    ]
    blockers = sorted({
        str(blocker)
        for row in rows
        for blocker in (row.get("effect_estimate") or {}).get("blockers") or ()
    })
    if direct:
        blockers.append("priced_effect_residual_required")
    blockers = sorted(set(blockers))
    body = {
        "schema": "jaggedthoughts-strategy-valuation-bridge-readiness-v1",
        "generated_at": epoch,
        "law_induction_sha256": law_induction.get("induction_sha256"),
        "law_candidate_count": len(rows),
        "transported_effect_count": len(transported),
        "direct_financial_effect_count": len(direct),
        "conditional_translation_request_count": len(transported) - len(direct),
        "status": (
            "priced_effect_residual_required" if direct else
            "conditional_translation_conjecture_required" if transported else
            "blocked_awaiting_transported_strategy_effect"
        ),
        "blockers": blockers,
        "priced_effect_residual_required": bool(direct),
        "activation_point": (
            "Bind the exact target move, effect comparator, baseline valuation, and price "
            "information cutoff; only the unpriced expectation residual may enter a direct path."
        ),
        "ordinal_frontier_is_financial_magnitude": False,
        "rank_authority": False, "decision_authority": False,
        "portfolio_authority": False, "capital_authority": False,
    }
    return {**body, "readiness_sha256": stable_sha256(body)}


def compile_direct_strategy_expectation_residual(
    root: Path,
    *,
    candidate: Mapping[str, Any],
    quality: Mapping[str, Any],
    dual_outcome_contract: Mapping[str, Any],
    horizon_days: int,
) -> dict[str, Any]:
    """Price the null and one declared operating hurdle; leave its probability open."""

    candidate_row = _verified_payload(candidate, "candidate_sha256", "candidate")
    quality_row = _verified_payload(quality, "quality_report_sha256", "quality report")
    dual = _verified_payload(
        dual_outcome_contract,
        "dual_outcome_contract_sha256",
        "dual outcome contract",
    )
    entity_id = require_text(candidate_row.get("entity_id"), "candidate entity_id").upper()
    if (
        str(dual.get("entity_id") or "").upper() != entity_id
        or dual.get("candidate_sha256") != candidate_row["candidate_sha256"]
        or str(quality_row.get("entity_id") or "").upper() != entity_id
        or quality_row["quality_report_sha256"]
        != candidate_row.get("quality_report_sha256")
        or canonical_timestamp(quality_row.get("as_of"), "quality as_of")
        != canonical_timestamp(candidate_row.get("as_of"), "candidate as_of")
    ):
        raise ValueError("strategy expectation residual crossed candidate identity")
    if isinstance(horizon_days, bool) or int(horizon_days) <= 0:
        raise ValueError("strategy expectation residual horizon_days must be positive")

    contract = dict(dual.get("operating_outcome") or {})
    contract_sha = _digest(contract.pop("contract_sha256", None), "operating contract_sha256")
    if contract.get("unit") != "decimal" or contract.get("comparator") != "pre_move_baseline":
        raise ValueError("strategy expectation residual requires a decimal pre-move operating hurdle")
    metric_id = require_text(contract.get("metric_id"), "operating metric_id")
    if metric_id not in {identity[0] for identity in _DIRECT_EFFECT_IDENTITIES.values()}:
        raise ValueError("strategy expectation residual operating metric has no direct valuation coordinate")
    direction = require_text(contract.get("direction"), "operating direction")
    if direction not in {"increase", "decrease"}:
        raise ValueError("strategy expectation residual direction is unsupported")
    minimum_effect = require_finite(contract.get("minimum_effect"), "operating minimum_effect")
    if minimum_effect <= 0:
        raise ValueError("strategy expectation residual minimum_effect must be positive")
    signed_effect = minimum_effect if direction == "increase" else -minimum_effect
    contract_refs = require_refs(dual.get("source_refs") or (), "frozen episode source ref")

    valuation = dict(candidate_row.get("valuation") or {})
    relative_path = require_text(valuation.get("artifact_path"), "valuation artifact_path")
    workspace = root.resolve()
    envelope_path = (workspace / relative_path).resolve()
    if not envelope_path.is_relative_to(workspace):
        raise ValueError("valuation artifact escapes the investment workspace")
    try:
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read valuation artifact: {error}") from error
    if (
        not isinstance(envelope, Mapping)
        or envelope.get("envelope_sha256") != valuation.get("envelope_sha256")
        or stable_sha256({
            key: value for key, value in envelope.items() if key != "envelope_sha256"
        }) != envelope.get("envelope_sha256")
        or str(envelope.get("entity_id") or "").upper() != entity_id
        or canonical_timestamp(envelope.get("evidence_epoch"), "valuation evidence_epoch")
        != canonical_timestamp(candidate_row.get("as_of"), "candidate as_of")
    ):
        raise ValueError("strategy expectation residual valuation artifact is not candidate-bound")

    affected_type = {
        "revenue_growth": "ForecastGrowth",
        "owner_earnings_margin": "OwnerEarnings",
        "reinvestment_growth": "ForecastGrowth",
        "terminal_growth": "TerminalGrowth",
    }[metric_id]
    baseline_margin = (quality_row.get("metrics") or {}).get("median_owner_earnings_margin")
    if metric_id == "owner_earnings_margin":
        baseline_margin = require_finite(baseline_margin, "median owner-earnings margin")
        if baseline_margin <= 0 or baseline_margin + signed_effect <= 0:
            raise ValueError("owner-earnings-margin hurdle cannot be lowered from this baseline")

    assumptions = []
    for row in envelope.get("assumptions") or ():
        value = float(row["value"])
        refs = tuple(row.get("source_refs") or ())
        if row.get("assumption_type") == affected_type:
            value = (
                value * (1.0 + signed_effect / baseline_margin)
                if metric_id == "owner_earnings_margin"
                else value + signed_effect
            )
            refs = tuple(sorted({*refs, *contract_refs}))
        assumptions.append(ValuationAssumption(
            str(row["assumption_id"]), str(row["assumption_type"]), value,
            str(row["unit"]), refs,
        ))
    scenarios = tuple(ValuationScenario(
        str(row["scenario_id"]), str(row["mechanism_id"]),
        tuple(row.get("assumption_ids") or ()), tuple(row.get("source_refs") or ()),
    ) for row in envelope.get("scenarios") or ())
    hurdle_envelope = compile_valuation_envelope(
        envelope_id=f"strategy-hurdle:{entity_id}:{contract_sha[:16]}",
        entity_id=entity_id,
        evidence_epoch=str(envelope["evidence_epoch"]),
        grammar_id="jaggedthoughts.strategy-expectation-residual",
        grammar_version="1",
        assumptions=tuple(assumptions),
        scenarios=scenarios,
        max_depth=4,
        max_programs=5000,
    ).to_dict()
    baseline_annual = require_finite(
        (envelope.get("summary") or {}).get("price_implied_excess_return"),
        "baseline price-implied excess return",
    )
    hurdle_annual = require_finite(
        (hurdle_envelope.get("summary") or {}).get("price_implied_excess_return"),
        "hurdle price-implied excess return",
    )
    if min(baseline_annual, hurdle_annual) <= -1:
        raise ValueError("strategy expectation residual cannot annualize a return at or below -100%")
    years = int(horizon_days) / 365.25
    baseline_return = (1.0 + baseline_annual) ** years - 1.0
    hurdle_return = (1.0 + hurdle_annual) ** years - 1.0
    body = {
        "schema": "jaggedthoughts-direct-strategy-expectation-residual-v1",
        "entity_id": entity_id,
        "candidate_sha256": candidate_row["candidate_sha256"],
        "dual_outcome_contract_sha256": dual["dual_outcome_contract_sha256"],
        "move_sha256": dual.get("move_sha256"),
        "strategy_choice_identity_sha256": dual.get("strategy_choice_identity_sha256"),
        "implementation_event_sha256": dual.get("implementation_event_sha256"),
        "operating_contract_sha256": contract_sha,
        "operating_hurdle": {**contract, "contract_sha256": contract_sha},
        "translation": {
            "kind": "direct_operating_hurdle_payoff",
            "metric_id": metric_id,
            "affected_valuation_type": affected_type,
            "signed_effect": signed_effect,
            "baseline_owner_earnings_margin": (
                baseline_margin if metric_id == "owner_earnings_margin" else None
            ),
            "causal_effect_earned": False,
            "conditional_probability_required": True,
        },
        "horizon_days": int(horizon_days),
        "baseline": {
            "valuation_envelope_sha256": envelope["envelope_sha256"],
            "annual_active_return": baseline_annual,
            "horizon_active_return": baseline_return,
        },
        "hurdle_world": {
            "valuation_envelope_sha256": hurdle_envelope["envelope_sha256"],
            "annual_active_return": hurdle_annual,
            "horizon_active_return": hurdle_return,
        },
        "incremental_horizon_payoff": hurdle_return - baseline_return,
        "mixture_formula": "durability_control + P(operating_hurdle) * incremental_horizon_payoff",
        "return_bridge": {
            "source_quantity": "price_implied_annualized_excess_return",
            "horizon_lowering": "smooth_compounding_over_declared_security_horizon",
            "expected_realized_return_claim": False,
            "mark_to_market_effect_identified": False,
            "settlement_role": "prospective_challenger_only",
        },
        "failure_world": {
            "incremental_payoff": 0.0,
            "implementation_cost_model_present": False,
            "downside_state_model_present": False,
            "interpretation": "failure returns to the value-quality control",
        },
        "source_refs": sorted({*contract_refs, *(envelope.get("summary") or {}).get("source_refs", ())}),
        "status": "compiled",
        "capital_authority": False,
    }
    return {**body, "residual_sha256": stable_sha256(body)}


def _sourced_return(
    raw: Mapping[str, Any], label: str, *, information_cutoff: str,
) -> tuple[float, str, tuple[str, ...]]:
    if raw.get("unit") != "horizon_active_return_decimal":
        raise ValueError(f"{label} unit must be horizon_active_return_decimal")
    value = require_finite(raw.get("value"), f"{label} value")
    if not -1.0 <= value <= 3.0:
        raise ValueError(f"{label} value must be in [-1, 3]")
    available_at = canonical_timestamp(raw.get("available_at"), f"{label} available_at")
    if available_at > information_cutoff:
        raise ValueError(f"{label} was unavailable at the information cutoff")
    return value, available_at, require_refs(raw.get("source_refs") or (), label)


def extreme_interval_mixture(
    rows: list[dict[str, Any]], *, payoff_field: str, maximize: bool,
) -> tuple[float, dict[str, float]]:
    probabilities = {row["region_sha256"]: float(row["probability_low"]) for row in rows}
    remainder = max(0.0, 1.0 - sum(probabilities.values()))
    ordered = sorted(
        rows, key=lambda row: (float(row[payoff_field]), row["region_sha256"]),
        reverse=maximize,
    )
    for row in ordered:
        room = float(row["probability_high"]) - probabilities[row["region_sha256"]]
        addition = min(remainder, room)
        probabilities[row["region_sha256"]] += addition
        remainder -= addition
        if remainder <= 1e-12:
            break
    if remainder > 1e-9:
        raise ValueError("region probability intervals do not contain a distribution")
    value = sum(
        probabilities[row["region_sha256"]] * float(row[payoff_field])
        for row in rows
    )
    return value, dict(sorted(probabilities.items()))


def compile_contingent_policy_payoff_frontier(
    *,
    strategy_frontier: Mapping[str, Any],
    contingent_policy: Mapping[str, Any],
    branch_valuations: Mapping[str, Mapping[str, Any]],
    region_probability_intervals: Mapping[str, Mapping[str, Any]],
    control_horizon_return: Mapping[str, Any],
    horizon_days: int,
    information_cutoff: str,
) -> dict[str, Any]:
    """Compile a conditional price-implied hurdle proxy for certified recourse regions."""

    cutoff = canonical_timestamp(information_cutoff, "policy payoff information_cutoff")
    if isinstance(horizon_days, bool) or not 7 <= int(horizon_days) <= 730:
        raise ValueError("policy payoff horizon_days must be in [7, 730]")
    policy = _verified_payload(
        contingent_policy, "contingent_policy_sha256", "contingent policy",
    )
    frontier = _verified_payload(
        strategy_frontier, "strategy_frontier_sha256", "strategy frontier",
    )
    regions = _verified_payload(
        dict(policy.get("policy_action_regions") or {}),
        "policy_action_regions_sha256", "policy action regions",
    )
    if (
        policy.get("schema") != "jaggedthoughts-company-contingent-policy-v1"
        or frontier.get("schema")
        != "jaggedthoughts-company-strategy-frontier-v1"
        or str((frontier.get("company") or {}).get("id") or "")
        != str(policy.get("company_id") or "")
        or policy not in (frontier.get("contingent_policy_catalog") or ())
        or timestamp_key(canonical_timestamp(
            policy.get("frozen_at"), "contingent policy frozen_at",
        )) > timestamp_key(cutoff)
        or not regions.get("scope_closed")
        or not regions.get("total_over_condition_space")
        or not regions.get("deterministic_over_condition_space")
        or (policy.get("feasibility_receipt") or {}).get("method")
        != "membership_in_z3_closed_static_choice_space"
    ):
        raise ValueError("contingent policy lacks a closed certified action partition")
    frontier_company = dict(frontier.get("company") or {})
    frontier_epoch = canonical_timestamp(
        frontier.get("evidence_epoch"), "strategy frontier evidence_epoch",
    )
    frontier_identity = (
        _digest(frontier_company.get("candidate_leaf"), "strategy frontier candidate_leaf"),
        _digest(frontier_company.get("candidate_sha256"), "strategy frontier candidate_sha256"),
        frontier_epoch,
    )
    if (
        timestamp_key(frontier_epoch) > timestamp_key(cutoff)
        or (policy.get("feasibility_receipt") or {}).get("choice_space_sha256")
        != (frontier.get("choice_space_certificate") or {}).get("choice_space_sha256")
    ):
        raise ValueError("contingent policy crossed frontier identity or information cutoff")
    final_ids = {
        str(row.get("program_id") or "") for row in policy.get("final_programs") or ()
    }
    region_rows = list(regions.get("regions") or ())
    verified_regions = []
    for region in region_rows:
        verified_regions.append(_verified_payload(
            dict(region), "region_sha256", "policy action region",
        ))
    region_ids = [str(row["region_sha256"]) for row in verified_regions]
    reachable_ids = {
        str(value) for value in regions.get("reachable_action_ids") or ()
    }
    action_ids = {str(row.get("action_id") or "") for row in verified_regions}
    if (
        not reachable_ids
        or len(region_ids) != len(set(region_ids))
        or action_ids != reachable_ids
        or not reachable_ids.issubset(final_ids)
        or set(branch_valuations) != reachable_ids
    ):
        raise ValueError("every and only reachable policy program must have a valuation")

    branch_rows = []
    branch_identity = None
    for program_id in sorted(reachable_ids):
        raw = dict(branch_valuations[program_id])
        bridge = _verified_payload(
            dict(raw.get("valuation_bridge") or {}), "bridge_sha256",
            f"{program_id} valuation bridge",
        )
        if (
            bridge.get("schema") != SCHEMA
            or bridge.get("entity_id") != policy.get("company_id")
            or bridge.get("strategy_program_id") != program_id
            or bridge.get("strategy_frontier_sha256")
            != frontier.get("strategy_frontier_sha256")
        ):
            raise ValueError("policy branch valuation crossed program or company identity")
        envelope = _verified_payload(
            dict(bridge.get("valuation_envelope") or {}), "envelope_sha256",
            f"{program_id} valuation envelope",
        )
        identity = (
            str(bridge.get("candidate_leaf") or ""),
            str(bridge.get("candidate_sha256") or ""),
            canonical_timestamp(bridge.get("evidence_epoch"), "bridge evidence_epoch"),
        )
        if (
            identity != frontier_identity
            or envelope.get("schema") != "jaggedthoughts-valuation-envelope-v1"
            or str(envelope.get("entity_id") or "") != str(bridge.get("entity_id") or "")
            or canonical_timestamp(
                envelope.get("evidence_epoch"), "branch valuation evidence_epoch",
            ) != identity[2]
            or timestamp_key(identity[2]) > timestamp_key(cutoff)
            or (branch_identity is not None and identity != branch_identity)
        ):
            raise ValueError("policy branch valuations crossed candidate or evidence epoch")
        branch_identity = identity
        risk_free_values = {
            float(row["value"]) for row in envelope.get("assumptions") or ()
            if row.get("assumption_type") == "RiskFreeRate"
        }
        implied_returns = [
            float(row["value"]) for row in envelope.get("results") or ()
            if row.get("result_type") == "ImpliedReturn"
        ]
        if len(risk_free_values) != 1 or not implied_returns:
            raise ValueError("policy branch valuation lacks one priced return basis")
        risk_free = next(iter(risk_free_values))
        if risk_free <= -1.0 or any(value <= -1.0 for value in implied_returns):
            raise ValueError("policy branch cannot compound an annual return at or below -100%")
        years = int(horizon_days) / 365.25
        hurdle_spreads = [
            (1.0 + value) ** years - (1.0 + risk_free) ** years
            for value in implied_returns
        ]
        cost, cost_at, cost_refs = _sourced_return(
            dict(raw.get("implementation_cost") or {}),
            f"{program_id} implementation_cost", information_cutoff=cutoff,
        )
        if cost < 0:
            raise ValueError("implementation cost cannot be negative")
        downside, downside_at, downside_refs = _sourced_return(
            dict(raw.get("downside_active_return") or {}),
            f"{program_id} downside_active_return", information_cutoff=cutoff,
        )
        low = min(min(hurdle_spreads), downside) - cost
        high = max(hurdle_spreads) - cost
        branch_rows.append({
            "program_id": program_id,
            "valuation_bridge_sha256": bridge["bridge_sha256"],
            "valuation_envelope_sha256": envelope["envelope_sha256"],
            "horizon_hurdle_spread_low": low,
            "horizon_hurdle_spread_high": high,
            "implementation_cost_return": cost,
            "downside_active_return": downside,
            "available_at": max(cost_at, downside_at),
            "source_refs": sorted({*cost_refs, *downside_refs}),
        })
    branches = {row["program_id"]: row for row in branch_rows}

    region_id_set = set(region_ids)
    if set(region_probability_intervals) != region_id_set:
        raise ValueError("probability intervals must exactly cover certified policy regions")
    mixtures = []
    for region in sorted(verified_regions, key=lambda row: str(row["region_sha256"])):
        region_sha = str(region["region_sha256"])
        probability = dict(region_probability_intervals[region_sha])
        if probability.get("unit") != "probability_decimal":
            raise ValueError("region probability unit must be probability_decimal")
        low = require_finite(probability.get("low"), "region probability low")
        high = require_finite(probability.get("high"), "region probability high")
        if not 0.0 <= low <= high <= 1.0:
            raise ValueError("region probability bounds must satisfy 0 <= low <= high <= 1")
        available_at = canonical_timestamp(
            probability.get("available_at"), "region probability available_at",
        )
        if available_at > cutoff:
            raise ValueError("region probability was unavailable at the information cutoff")
        program_id = str(region.get("action_id") or "")
        branch = branches.get(program_id)
        if branch is None:
            raise ValueError("certified policy region points to an unvalued program")
        mixtures.append({
            "region_sha256": region_sha, "program_id": program_id,
            "probability_low": low, "probability_high": high,
            "horizon_hurdle_spread_low": branch["horizon_hurdle_spread_low"],
            "horizon_hurdle_spread_high": branch["horizon_hurdle_spread_high"],
            "available_at": available_at,
            "source_refs": list(require_refs(
                probability.get("source_refs") or (), "region probability source ref",
            )),
        })
    if sum(row["probability_low"] for row in mixtures) > 1.0 + 1e-12 or sum(
        row["probability_high"] for row in mixtures
    ) < 1.0 - 1e-12:
        raise ValueError("region probability intervals do not contain a distribution")
    expected_low, low_witness = extreme_interval_mixture(
        mixtures, payoff_field="horizon_hurdle_spread_low", maximize=False,
    )
    expected_high, high_witness = extreme_interval_mixture(
        mixtures, payoff_field="horizon_hurdle_spread_high", maximize=True,
    )
    control, control_at, control_refs = _sourced_return(
        control_horizon_return, "control_horizon_return", information_cutoff=cutoff,
    )
    excess_low, excess_high = expected_low - control, expected_high - control
    body = {
        "schema": CONTINGENT_POLICY_PAYOFF_SCHEMA,
        "company_id": policy["company_id"], "policy_id": policy["policy_id"],
        "contingent_policy_sha256": policy["contingent_policy_sha256"],
        "policy_action_regions_sha256": regions["policy_action_regions_sha256"],
        "choice_space_sha256": policy["feasibility_receipt"]["choice_space_sha256"],
        "horizon_days": int(horizon_days), "information_cutoff": cutoff,
        "branch_hurdles": branch_rows, "region_probability_intervals": mixtures,
        "price_implied_hurdle_mixture_bounds": {
            "low": expected_low, "high": expected_high,
        },
        "price_implied_hurdle_minus_control_bounds": {
            "low": excess_low, "high": excess_high,
        },
        "control_horizon_active_return": {
            "value": control, "available_at": control_at,
            "source_refs": list(control_refs),
        },
        "worst_case_branch_hurdle_minus_control": min(
            row["horizon_hurdle_spread_low"] - control for row in branch_rows
        ),
        "probability_witnesses": {
            "hurdle_mixture_low": low_witness,
            "hurdle_mixture_high": high_witness,
        },
        "conditional_hurdle_status": (
            "policy_interval_above_control" if excess_low > 0 else
            "policy_interval_below_control" if excess_high < 0 else
            "policy_interval_crosses_control"
        ),
        "quantity_identity": (
            "probability_weighted_price_implied_hurdle_proxy_not_expected_realized_return"
        ),
        "research_priority_use": "conditional_price_implied_hurdle_challenger_only",
        "causal_effect_earned": False,
        "expected_realized_return_claim": False,
        "mark_to_market_effect_identified": False,
        "conditional_on_supplied_probability_intervals": True,
        "interval_geometry": "rectangular_relaxation",
        "rank_authority": False, "decision_authority": False,
        "portfolio_authority": False, "capital_authority": False,
    }
    return {**body, "payoff_frontier_sha256": stable_sha256(body)}


__all__ = [
    "SCHEMA", "CONTINGENT_POLICY_PAYOFF_SCHEMA",
    "compile_contingent_policy_payoff_frontier",
    "compile_direct_strategy_expectation_residual",
    "compile_strategy_valuation_bridge",
    "compile_strategy_valuation_bridge_readiness",
    "extreme_interval_mixture",
]
