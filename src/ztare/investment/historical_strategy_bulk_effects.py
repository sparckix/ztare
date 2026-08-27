"""Compile diagnostic group-time panels from the market-wide strategy corpus."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .historical_strategy_bulk_outcomes import strategy_history_ready_at
from .institutional_learning import (
    CAUSAL_PANEL_ROW_SCHEMA,
    LAW_CANDIDATE_SCHEMA,
    compile_law_candidate,
    evaluate_difference_in_differences,
)


_ROOT = Path("institutional_learning/historical_strategy_bulk_outcomes")
_OUTCOME_VARIANTS = (
    {
        "metric_id": "owner_earnings_margin", "history_field": "owner_earnings_margin",
        "unit": "decimal", "role": "economic_primary",
        "definition": "(operating_cash_flow_fy - capital_expenditure_fy) / revenue_fy",
    },
    {
        "metric_id": "owner_earnings_balance", "history_field": "owner_earnings_balance",
        "unit": "score", "role": "unit_invariant_tail_stress",
        "definition": "owner_earnings_margin / (1 + abs(owner_earnings_margin))",
    },
)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _checked(path: Path, digest_field: str) -> dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8"))
    body = dict(row)
    declared = str(body.pop(digest_field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{path.name} content hash mismatch")
    return row


def _first_adoptions(histories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    first: dict[tuple[str, str], dict[str, Any]] = {}
    for row in histories:
        key = (str(row["cik"]), str(row["implementation_mode"]))
        if key not in first or (row["occurred_at"], row["accession_number"]) < (
            first[key]["occurred_at"], first[key]["accession_number"],
        ):
            first[key] = row
    return list(first.values())


def _ready_at(row: Mapping[str, Any], year: int) -> bool:
    return strategy_history_ready_at(row, year)


def _law(
    cell: Mapping[str, Any], panel_sha: str, generated_at: str,
    outcome: Mapping[str, str] = _OUTCOME_VARIANTS[0],
) -> dict[str, Any]:
    mode = str(cell["implementation_mode"])
    metric = str(outcome["metric_id"])
    return compile_law_candidate({
        "schema": LAW_CANDIDATE_SCHEMA,
        "law_id": f"historical-{mode}-{metric.replace('_', '-')}",
        "version": panel_sha[:12],
        "name": f"Historical {mode} completion and {metric.replace('_', ' ')}",
        "question": (
            f"Does a completed {mode} change {metric.replace('_', ' ')} relative to "
            "same-industry companies that adopt the same move later?"
        ),
        "created_at": generated_at, "not_before": generated_at,
        "origin": "historical_strategy_bulk_diagnostic",
        "estimator": {
            "kind": "difference_in_differences",
            "design": "group_time_att_unadjusted",
            "control_group": "not_yet_treated",
            "implementation_id": "ztare.investment.institutional_learning.group_time_att_v3",
            "expected_direction": "positive",
            "treatment_id": f"{mode}_completion",
            "parallel_trend_tolerance": 0.10,
            "bootstrap_iterations": 1000,
        },
        "cohort": {
            "entity_kinds": ["public_company"], "horizon_days": [],
            "conditions": [], "evaluation_environments": ["industry_id"],
            "counterexample_fields": ["industry_id", "strategy_phenotype"],
        },
        "outcome_metric_id": metric,
        "mechanism": {
            "antecedent_concepts": [f"{mode}_completion"],
            "consequence_concept": metric, "kind": "causal",
        },
        "decision_use": "strategy_law_diagnostic",
        "generation_receipt": {
            "panel_readiness_sha256": panel_sha,
            "cell": dict(cell),
            "outcome_variant": dict(outcome),
        },
        "validation": {
            "minimum_treated_units": 4, "minimum_control_units": 4,
            "minimum_pre_periods": 2, "minimum_post_periods": 1,
        },
        "trial_family_id": "historical-strategy-bulk-owner-earnings-v1",
        "authority": "diagnostic_only",
    })


def _rows(
    law: Mapping[str, Any], cell: Mapping[str, Any], first: list[dict[str, Any]],
    outcome: Mapping[str, str] = _OUTCOME_VARIANTS[0],
    bounded_controls: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    year = int(cell["adoption_year"])
    units = [
        row for row in first
        if row["sic2"] == cell["sic2"]
        and row["implementation_mode"] == cell["implementation_mode"]
        and int(row["event_year"]) >= year
        and _ready_at(row, year)
    ]
    rows = []
    for unit in units:
        by_year: dict[int, dict[str, Any]] = {}
        for observation in unit["annual_history"]:
            period = int(observation["observed_at"][:4])
            if period == int(unit["event_year"]):
                continue
            current = by_year.get(period)
            if current is None or observation["observed_at"] > current["observed_at"]:
                by_year[period] = observation
        for period, observation in sorted(by_year.items()):
            body = {
                "schema": CAUSAL_PANEL_ROW_SCHEMA,
                "law_id": law["law_id"], "unit_id": f"CIK{unit['cik']}",
                "period_index": period, "treated_group": True,
                "treatment_period": int(unit["event_year"]),
                "treatment_event_sha256": unit["event_sha256"],
                "treatment_event_sha256s": [unit["event_sha256"]],
                "treatment_timing_status": "exact_adoption_event",
                "treatment_occurred_at": unit["occurred_at"],
                "treatment_available_at": unit["treatment_available_at"],
                "outcome_metric_id": outcome["metric_id"],
                "outcome_unit": outcome["unit"],
                "outcome": observation[outcome["history_field"]],
                "observed_at": observation["observed_at"],
                "available_at": observation["available_at"],
                "environment": {
                    "industry_id": f"SIC2:{cell['sic2']}",
                    "strategy_phenotype": cell["implementation_mode"],
                },
                "observation_ids": observation["observation_ids"],
                "source_refs": [
                    f"sec-companyfacts-row:{value}"
                    for value in observation["observation_row_sha256s"]
                ] + [
                    f"sec-item-2.01-event:{unit['event_sha256']}",
                    f"classification:{unit['classification_evidence_sha256']}",
                ],
            }
            rows.append({**body, "panel_row_sha256": stable_sha256(body)})
    controls = bounded_controls or {}
    post = int((cell.get("joint_design") or {}).get("post_period") or 0)
    for control_id in (cell.get("joint_design") or {}).get("post_bounded_control_ids") or ():
        unit = controls.get(str(control_id))
        if unit is None:
            raise ValueError("group-time cell lost its bounded control identity")
        by_period = {}
        for observation in unit["annual_history"]:
            period = int(observation["observed_at"][:4])
            if period > post:
                continue
            current = by_period.get(period)
            if current is None or (
                observation["observed_at"], observation["available_at"],
                stable_sha256(observation),
            ) > (
                current["observed_at"], current["available_at"], stable_sha256(current),
            ):
                by_period[period] = observation
        observations = [by_period[period] for period in sorted(by_period)]
        if not observations:
            raise ValueError("bounded strategy control has no admitted observations")
        start = min(str(row["observed_at"]) for row in observations)
        end = max(str(row["observed_at"]) for row in observations)
        event_proofs = [
            row for row in unit["classified_events"]
            if int(row["occurred_at"][:4]) <= post
        ]
        if not event_proofs:
            raise ValueError("bounded strategy control has no typed event-history proof")
        for observation in observations:
            body = {
                "schema": CAUSAL_PANEL_ROW_SCHEMA,
                "law_id": law["law_id"], "unit_id": f"CIK{unit['cik']}",
                "period_index": int(observation["observed_at"][:4]),
                "treated_group": False, "treatment_period": None,
                "treatment_event_sha256": None, "treatment_event_sha256s": [],
                "treatment_timing_status": "not_yet_treated_bounded",
                "control_observation_start_at": start,
                "control_observation_end_at": end,
                "outcome_metric_id": outcome["metric_id"],
                "outcome_unit": outcome["unit"],
                "outcome": observation[outcome["history_field"]],
                "observed_at": observation["observed_at"],
                "available_at": observation["available_at"],
                "environment": {
                    "industry_id": f"SIC2:{cell['sic2']}",
                    "strategy_phenotype": cell["implementation_mode"],
                },
                "observation_ids": observation["observation_ids"],
                "source_refs": [
                    f"sec-companyfacts-row:{value}"
                    for value in observation["observation_row_sha256s"]
                ] + [
                    f"sec-item-2.01-corpus:{unit['bulk_corpus_sha256']}",
                    f"classification-set:{unit['classification_set_sha256']}",
                ] + [
                    ref for event in event_proofs for ref in (
                        f"sec-item-2.01-event:{event['event_sha256']}",
                        f"classification:{event['classification_evidence_sha256']}",
                    )
                ],
            }
            rows.append({**body, "panel_row_sha256": stable_sha256(body)})
    return rows


def compile_bulk_strategy_effect_diagnostics(workspace: str | Path) -> dict[str, Any]:
    """Run bounded post-hoc diagnostics only for panel-ready strategy cells."""
    root = Path(workspace).expanduser().resolve()
    panel = _checked(root / _ROOT / "panel-readiness.json", "readiness_sha256")
    compiler_sha = stable_sha256({
        "law": inspect.getsource(_law), "rows": inspect.getsource(_rows),
        "evaluate": inspect.getsource(evaluate_difference_in_differences),
        "compile": inspect.getsource(compile_bulk_strategy_effect_diagnostics),
    })
    destination = root / _ROOT / "effect-diagnostics.json"
    if destination.is_file():
        prior = _checked(destination, "diagnostics_sha256")
        if (
            prior.get("panel_readiness_sha256") == panel["readiness_sha256"]
            and prior.get("compiler_sha256") == compiler_sha
        ):
            return prior
    first = _first_adoptions(panel["history_status"])
    controls = {
        str(row["control_id"]): row for row in panel.get("bounded_control_status") or ()
    }
    results = []
    for cell in panel["adoption_cells"]:
        if not cell["structural_support_ready"]:
            continue
        law = _law(cell, panel["readiness_sha256"], panel["generated_at"])
        rows = _rows(law, cell, first, bounded_controls=controls)
        evaluation = evaluate_difference_in_differences(
            law, rows, generated_at=panel["generated_at"],
        )
        results.append({
            "cell": cell, "law": law, "panel_rows": rows,
            "evaluation": evaluation,
        })
    body = {
        "schema": "jaggedthoughts-historical-strategy-bulk-effect-diagnostics-v1",
        "generated_at": panel["generated_at"],
        "panel_readiness_sha256": panel["readiness_sha256"],
        "compiler_sha256": compiler_sha,
        "structural_diagnostic_count": len(results),
        "ready_cell_count": sum(row["cell"]["group_time_ready"] for row in results),
        "diagnostics": results,
        "multiplicity": {
            "family_id": "historical-strategy-bulk-owner-earnings-v1",
            "hypothesis_count": len(results),
            "status": "post_hoc_diagnostic_no_multiplicity_credit",
        },
        "status": "diagnostics_compiled" if results else "awaiting_ready_cell",
        "next_activation": (
            "Inspect support and pretrend failures; freeze surviving refinements before new evidence."
            if results else "Advance the source-bound panel frontier."
        ),
        "causal_claim": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    result = {**body, "diagnostics_sha256": stable_sha256(body)}
    _atomic_json(destination, result)
    return result


def compile_bulk_strategy_outcome_robustness(workspace: str | Path) -> dict[str, Any]:
    """Compare a fixed economic estimand with a unit-invariant tail stress."""
    root = Path(workspace).expanduser().resolve()
    panel = _checked(root / _ROOT / "panel-readiness.json", "readiness_sha256")
    compiler_sha = stable_sha256({
        "law": inspect.getsource(_law), "rows": inspect.getsource(_rows),
        "evaluate": inspect.getsource(evaluate_difference_in_differences),
        "compile": inspect.getsource(compile_bulk_strategy_outcome_robustness),
        "outcomes": _OUTCOME_VARIANTS,
    })
    destination = root / _ROOT / "outcome-robustness.json"
    if destination.is_file():
        prior = _checked(destination, "robustness_sha256")
        if (
            prior.get("panel_readiness_sha256") == panel["readiness_sha256"]
            and prior.get("compiler_sha256") == compiler_sha
        ):
            return prior
    first = _first_adoptions(panel["history_status"])
    controls = {
        str(row["control_id"]): row for row in panel.get("bounded_control_status") or ()
    }
    families = []
    for cell in panel["adoption_cells"]:
        if not cell["structural_support_ready"]:
            continue
        variants = []
        for outcome in _OUTCOME_VARIANTS:
            law = _law(cell, panel["readiness_sha256"], panel["generated_at"], outcome)
            rows = _rows(law, cell, first, outcome, controls)
            evaluation = evaluate_difference_in_differences(
                law, rows, generated_at=panel["generated_at"],
            )
            variants.append({
                "outcome": dict(outcome), "law": law, "evaluation": evaluation,
                "panel_row_count": len(rows),
            })
        estimates = [
            row["evaluation"].get("details", {}).get("aggregate_att") for row in variants
        ]
        nonzero = [float(value) for value in estimates if value not in (None, 0)]
        families.append({
            "cell": cell, "variants": variants,
            "direction_agreement": (
                len(nonzero) == len(variants)
                and len({1 if value > 0 else -1 for value in nonzero}) == 1
            ),
            "all_parallel_trend_gates_pass": all(
                row["evaluation"]["diagnostic_status"] != "challenged_parallel_trends"
                for row in variants
            ),
            "status": "post_hoc_scale_sensitivity_only",
        })
    body = {
        "schema": "jaggedthoughts-historical-strategy-outcome-robustness-v1",
        "generated_at": panel["generated_at"],
        "panel_readiness_sha256": panel["readiness_sha256"],
        "compiler_sha256": compiler_sha,
        "outcome_family": [dict(row) for row in _OUTCOME_VARIANTS],
        "family_count": len(families), "families": families,
        "future_evidence_contract": {
            "selection_rule": "evaluate_every_variant_no_best_variant_selection",
            "required_for_directional_support": [
                "same_effect_direction", "every_parallel_trend_gate_passes",
                "economic_primary_interval_excludes_rival_direction",
            ],
            "next_epoch_must_differ_from_panel_readiness_sha256": panel["readiness_sha256"],
            "interpretation": (
                "The bounded score diagnoses tail dependence; it cannot replace the "
                "economic owner-earnings-margin estimand."
            ),
        },
        "status": "future_outcome_family_frozen",
        "next_activation": (
            "Apply the whole family to a newly supported child cell or later evidence epoch; "
            "do not choose the variant with the better result."
        ),
        "causal_claim": False, "promotion_eligible": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    result = {**body, "robustness_sha256": stable_sha256(body)}
    _atomic_json(destination, result)
    return result


__all__ = [
    "compile_bulk_strategy_effect_diagnostics",
    "compile_bulk_strategy_outcome_robustness",
]
