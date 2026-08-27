"""Observe future SEC strategy paths under one frozen representation trial."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, timestamp_key
from .factor_analysis import (
    FactorDefinition,
    InsufficientFactorHistoryError,
    PricePoint,
    compile_historical_factor_control,
    load_price_points,
)
from .historical_strategy_event_replay import (
    canonicalize_strategy_event_phenotype,
    classify_sec_item_201,
)
from .sources import fetch_sec_filing_document
from .tournament import (
    BacktestEpisode,
    ObservableSpec,
    WorldModelCandidate,
    WorldModelForecast,
    evaluate_world_model_tournament,
)
from .strategy_representation_learning import (
    STRATEGY_SECURITY_REPRESENTATION_LEARNING_SCHEMA,
)
from .strategy_walk_forward import (
    STRATEGY_SECURITY_WALK_FORWARD_SCHEMA,
    extract_filing_trading_symbols,
)


STRATEGY_PATH_SHADOW_SCHEMA = "jaggedthoughts-strategy-path-shadow-v1"
_BULK_EFFECT_DIAGNOSTICS_SCHEMA = (
    "jaggedthoughts-historical-strategy-bulk-effect-diagnostics-v1"
)
_ROOT = Path("institutional_learning/strategy_path_shadow")
_ELIGIBLE = {
    "operating_strategy_event", "operating_strategy_bundle_event",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _checked(value: Mapping[str, Any], schema: str, digest: str) -> dict[str, Any]:
    row = dict(value)
    claimed = str(row.pop(digest, ""))
    if row.get("schema") != schema or not claimed or stable_sha256(row) != claimed:
        raise ValueError(f"invalid {schema} artifact")
    return {**row, digest: claimed}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cell(row: Mapping[str, Any]) -> tuple[str, ...]:
    phenotype = row.get("transaction_phenotype")
    phenotype = phenotype if isinstance(phenotype, Mapping) else row
    return tuple(str(value or "indeterminate") for value in (
        row.get("implementation_mode"), phenotype.get("transaction_form"),
        phenotype.get("operating_object_scope"), phenotype.get("issuer_role"),
    ))


def _frozen_models(tournament: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        dict(row) for row in tournament.get("security_outcomes") or ()
        if isinstance(row, Mapping)
    ]
    if not rows:
        raise ValueError("strategy path shadow requires historical control outcomes")
    global_value = median(float(row["estimated_effect"]) for row in rows)
    by_mode: dict[str, list[float]] = defaultdict(list)
    by_cell: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row in rows:
        value = float(row["estimated_effect"])
        by_mode[_cell(row)[0]].append(value)
        by_cell[_cell(row)].append(value)
    body = {
        "target_metric_id": (tournament.get("execution_contract") or {}).get(
            "return_target"
        ),
        "training_tournament_sha256": tournament["tournament_sha256"],
        "training_episode_sha256s": sorted(str(row["episode_sha256"]) for row in rows),
        "models": [
            {
                "model_id": "untyped_global_median",
                "rule": "median of every admitted historical control outcome",
                "global_prediction": global_value,
            },
            {
                "model_id": "isolated_final_move",
                "rule": "exact final-move cell median; implementation-mode median; global median",
                "cell_medians": {"|".join(key): median(values) for key, values in sorted(by_cell.items())},
                "mode_medians": {key: median(values) for key, values in sorted(by_mode.items())},
                "global_prediction": global_value,
            },
            {
                "model_id": "ordered_path_composition",
                "rule": (
                    "recency-weighted mean of frozen isolated-move predictions with integer "
                    "weights 1..path_length"
                ),
                "fallback_model_id": "isolated_final_move",
            },
        ],
        "fit_authority": "frozen_research_control_only",
        "capital_authority": False,
    }
    return {**body, "model_set_sha256": stable_sha256(body)}


def _move_prediction(models: Mapping[str, Any], cell: tuple[str, ...]) -> float:
    isolated = models["models"][1]
    return float(
        isolated["cell_medians"].get("|".join(cell),
            isolated["mode_medians"].get(cell[0], isolated["global_prediction"]))
    )


def _frozen_operating_models(
    replay: Mapping[str, Any], diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows = [
        dict(row) for row in replay.get("episodes") or ()
        if isinstance(row, Mapping) and row.get("estimated_effect") is not None
    ]
    if not rows:
        raise ValueError("strategy operating shadow requires historical operating outcomes")
    global_value = median(float(row["estimated_effect"]) for row in rows)
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cell: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_mode[_cell(row)[0]].append(row)
        by_cell[_cell(row)].append(row)
    models = [
        {
            "model_id": "untyped_operating_global_median",
            "global_prediction": global_value,
        },
        {
            "model_id": "typed_operating_phenotype",
            "cell_medians": {
                "|".join(key): median(float(row["estimated_effect"]) for row in values)
                for key, values in sorted(by_cell.items())
            },
            "mode_medians": {
                key: median(float(row["estimated_effect"]) for row in values)
                for key, values in sorted(by_mode.items())
            },
            "cell_support": {
                "|".join(key): {
                    "episode_count": len(values),
                    "entity_count": len({str(row["entity_id"]) for row in values}),
                }
                for key, values in sorted(by_cell.items())
            },
            "mode_support": {
                key: {
                    "episode_count": len(values),
                    "entity_count": len({str(row["entity_id"]) for row in values}),
                }
                for key, values in sorted(by_mode.items())
            },
            "global_prediction": global_value,
            "backoff_order": "exact phenotype; implementation mode; global median",
        },
    ]
    diagnostic_sha = None
    if diagnostics:
        checked = _checked(
            diagnostics, _BULK_EFFECT_DIAGNOSTICS_SCHEMA, "diagnostics_sha256",
        )
        diagnostic_sha = checked["diagnostics_sha256"]
        family_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in checked.get("diagnostics") or ():
            cell = row.get("cell") or {}
            evaluation = row.get("evaluation") or {}
            value = (evaluation.get("details") or {}).get("aggregate_att")
            if (
                cell.get("group_time_ready")
                and evaluation.get("diagnostic_status") != "challenged_parallel_trends"
                and value is not None and math.isfinite(float(value))
            ):
                family_rows[(str(cell["sic2"]), str(cell["implementation_mode"]))].append({
                    "adoption_year": int(cell["adoption_year"]),
                    "aggregate_att": float(value),
                    "evaluation_sha256": evaluation["evaluation_sha256"],
                })
        if family_rows:
            models.append({
                "model_id": "group_time_strategy_family",
                "family_predictions": {
                    "|".join(key): median(row["aggregate_att"] for row in values)
                    for key, values in sorted(family_rows.items())
                },
                "family_support": {
                    "|".join(key): {
                        "cohort_count": len(values),
                        "adoption_years": sorted(row["adoption_year"] for row in values),
                        "evaluation_sha256s": sorted(
                            row["evaluation_sha256"] for row in values
                        ),
                    }
                    for key, values in sorted(family_rows.items())
                },
                "aggregation": "median_across_adoption_cohorts",
                "identity": "sic2_by_implementation_mode; adoption_year_is_evaluation_block",
                "eligibility": "group_time_ready_and_parallel_trend_gate_not_challenged",
                "fallback_model_id": "typed_operating_phenotype",
                "source_diagnostics_sha256": diagnostic_sha,
                "claim_boundary": "prospective predictive challenger; no historical causal credit",
            })
    body = {
        "target_metric_id": "owner_earnings_margin_delta",
        "training_replay_sha256": replay["replay_sha256"],
        "training_bulk_effect_diagnostics_sha256": diagnostic_sha,
        "training_episode_sha256s": sorted(str(row["episode_sha256"]) for row in rows),
        "models": models,
        "capital_authority": False,
    }
    return {**body, "model_set_sha256": stable_sha256(body)}


def _operating_prediction(
    models: Mapping[str, Any], phenotype: Mapping[str, Any], *, sic2: str,
) -> dict[str, Any]:
    typed = models["models"][1]
    cell = _cell(phenotype)
    cell_key = "|".join(cell)
    cell_support = dict(typed["cell_support"].get(cell_key) or {})
    mode_support = dict(typed["mode_support"].get(cell[0]) or {})
    supported = lambda row: (
        int(row.get("episode_count") or 0) >= 3
        and int(row.get("entity_count") or 0) >= 2
    )
    if supported(cell_support):
        prediction = float(typed["cell_medians"][cell_key])
        basis, support = "exact_phenotype", cell_support
    elif supported(mode_support):
        prediction = float(typed["mode_medians"][cell[0]])
        basis, support = "implementation_mode_backoff", mode_support
    else:
        prediction = float(typed["global_prediction"])
        basis, support = "global_median_backoff", {
            "episode_count": len(models["training_episode_sha256s"]),
            "entity_count": None,
        }
    predictions = {
        "untyped_operating_global_median": float(
            models["models"][0]["global_prediction"]
        ),
        "typed_operating_phenotype": prediction,
    }
    family = next((
        row for row in models["models"]
        if row["model_id"] == "group_time_strategy_family"
    ), None)
    family_key = f"{sic2}|{cell[0]}"
    family_supported = bool(
        family and family_key in family.get("family_predictions", {})
    )
    if family:
        predictions["group_time_strategy_family"] = float(
            family["family_predictions"].get(family_key, prediction)
        )
    return {
        "predicted_deltas": predictions,
        "typed_prediction_basis": basis,
        "typed_prediction_support": support,
        "group_time_prediction_basis": (
            "sic2_implementation_mode_family"
            if family_supported else "typed_operating_phenotype_backoff"
            if family else None
        ),
        "group_time_prediction_support": (
            dict(family["family_support"][family_key]) if family_supported else {}
        ),
    }


def _event_research_queue(
    moves: Iterable[Mapping[str, Any]],
    operating_forecasts: Iterable[Mapping[str, Any]],
    return_forecasts: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Prioritize evidence acquisition by model disagreement, never expected return."""

    operating = {
        str(row["move_observation_sha256"]): dict(row)
        for row in operating_forecasts
    }
    returns = {
        str(row["target_move_observation_sha256"]): dict(row)
        for row in return_forecasts if int(row.get("path_length") or 0) == 1
    }
    rows = []
    for raw in moves:
        move = dict(raw)
        move_sha = str(move["move_observation_sha256"])
        operating_forecast = operating.get(move_sha)
        return_forecast = returns.get(move_sha)
        if operating_forecast is None or return_forecast is None:
            continue
        operating_values = operating_forecast["predicted_deltas"]
        return_values = return_forecast["predicted_values"]
        operating_predictions = {
            str(key): float(value) for key, value in operating_values.items()
        }
        typed_operating = operating_predictions["typed_operating_phenotype"]
        untyped_operating = operating_predictions["untyped_operating_global_median"]
        isolated_return = float(return_values["isolated_final_move"])
        untyped_return = float(return_values["untyped_global_median"])
        body = {
            "schema": "jaggedthoughts-strategy-event-research-request-v1",
            "move_observation_sha256": move_sha,
            "entity_id": move["entity_id"], "cik": move["cik"],
            "accession_number": move["accession_number"],
            "occurred_at": move["occurred_at"],
            "available_at": move["available_at"],
            "phenotype": move["phenotype"],
            "operating_model_predictions": operating_predictions,
            "operating_model_disagreement": (
                max(operating_predictions.values())
                - min(operating_predictions.values())
            ),
            "operating_direction_disagreement": (
                min(operating_predictions.values()) < 0.0
                < max(operating_predictions.values())
            ),
            "return_model_disagreement": abs(isolated_return - untyped_return),
            "return_direction_disagreement": isolated_return * untyped_return < 0.0,
            "priority_contract": (
                "operating direction disagreement; absolute operating disagreement; "
                "event recency; stable entity id"
            ),
            "selection_use": "evidence_acquisition_only",
            "required_public_source_classes": [
                "sec_companyfacts", "sec_submissions", "adjusted_daily_price",
            ],
            "next_state": "public_source_enrichment",
            "security_ranking_use": False, "paper_policy_authority": False,
            "capital_authority": False,
        }
        rows.append({**body, "research_request_sha256": stable_sha256(body)})
    rows.sort(key=lambda row: (
        not bool(row["operating_direction_disagreement"]),
        -float(row["operating_model_disagreement"]),
        -timestamp_key(str(row["available_at"])).timestamp(),
        str(row["entity_id"]),
    ))
    return [{**row, "research_priority_rank": index} for index, row in enumerate(rows, 1)]


def _operating_baseline(
    history: Iterable[Mapping[str, Any]], *, occurred_at: str, issued_at: str,
) -> dict[str, Any] | None:
    eligible = [
        dict(row) for row in history
        if timestamp_key(str(row["observed_at"])) < timestamp_key(occurred_at)
        and timestamp_key(str(row["available_at"])) <= timestamp_key(issued_at)
    ]
    return max(eligible, key=lambda row: (
        timestamp_key(str(row["observed_at"])), timestamp_key(str(row["available_at"])),
    )) if eligible else None


def _classification_rows(root: Path) -> dict[str, dict[str, Any]]:
    deterministic: dict[str, dict[str, Any]] = {}
    for directory in (
        root / "institutional_learning/historical_strategy_event_replay/filings",
        root / "institutional_learning/historical_strategy_bulk_learning/classifications",
    ):
        for path in directory.glob("*.json"):
            row = json.loads(path.read_text(encoding="utf-8"))
            body = dict(row)
            claimed = str(body.pop("classification_receipt_sha256", ""))
            receipt = row.get("filing_source_receipt")
            receipt = receipt if isinstance(receipt, Mapping) else {}
            raw_path = (root / str(receipt.get("raw_path") or "")).resolve()
            try:
                raw_path.relative_to(root)
                content = raw_path.read_bytes()
            except (OSError, ValueError):
                content = b""
            if (
                claimed and stable_sha256(body) == claimed and row.get("accession_number")
                and content and hashlib.sha256(content).hexdigest()
                == receipt.get("content_sha256")
            ):
                deterministic[str(row["accession_number"])] = {
                    **row,
                    "filing_trading_symbols": extract_filing_trading_symbols(content),
                }
    semantic_dir = root / "institutional_learning/historical_strategy_bulk_learning/semantic_resolutions"
    for path in semantic_dir.glob("*.json"):
        semantic = json.loads(path.read_text(encoding="utf-8"))
        body = dict(semantic)
        claimed = str(body.pop("semantic_resolution_sha256", ""))
        source = deterministic.get(str(semantic.get("accession_number") or ""))
        if (
            source and claimed and stable_sha256(body) == claimed
            and semantic.get("event_sha256") == source.get("event_sha256")
            and semantic.get("deterministic_classification_receipt_sha256")
            == source.get("classification_receipt_sha256")
        ):
            deterministic[str(semantic["accession_number"])] = {
                **source, **canonicalize_strategy_event_phenotype(semantic),
                "classification_receipt_sha256": claimed,
                "classification_transport": "codex_subscription_cli",
            }
    return deterministic


def _event_rows(root: Path, corpus: Mapping[str, Any]) -> list[dict[str, Any]]:
    path = (root / str(corpus["event_lake_path"])).resolve()
    path.relative_to(root)
    if _file_sha256(path) != corpus.get("event_lake_sha256"):
        raise ValueError("strategy path event lake hash mismatch")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _selection_accessions(
    replay: Mapping[str, Any], conjecture: Mapping[str, Any],
) -> set[str]:
    selected = set(map(str, (conjecture.get("trial_identity") or {}).get(
        "consumed_counterexample_sha256s", ()
    )))
    return {
        str(row["accession_number"]) for row in replay.get("episodes") or ()
        if str(row.get("episode_sha256") or "") in selected
    }


def _event_key(event: Mapping[str, Any]) -> str:
    return stable_sha256({
        "cik": str(event["cik"]),
        "accession_number": str(event["accession_number"]),
        "item": "2.01",
    })


def _postcutoff_events(
    events: Iterable[Mapping[str, Any]], *, cutoff: str, as_of: str,
    excluded_accessions: set[str],
) -> list[dict[str, Any]]:
    return sorted((
        dict(row) for row in events
        if row.get("current_common_equity_member")
        and timestamp_key(str(row["available_at"])) > timestamp_key(cutoff)
        and timestamp_key(str(row["available_at"])) <= timestamp_key(as_of)
        and str(row["accession_number"]) not in excluded_accessions
    ), key=lambda row: (row["available_at"], row["cik"], row["accession_number"]))


def _security_identity(
    event: Mapping[str, Any], classification: Mapping[str, Any], *, catalog_sha256: str,
) -> dict[str, Any]:
    current = sorted({str(value).upper() for value in event.get(
        "current_common_equity_symbols", ()
    )})
    filing = sorted({str(value).upper() for value in classification.get(
        "filing_trading_symbols", ()
    )})
    matched = sorted(set(current) & set(filing))
    reasons = []
    if len(current) != 1:
        reasons.append("catalog_cik_maps_to_zero_or_multiple_common_equities")
    if len(matched) != 1:
        reasons.append("filing_symbol_not_bound_to_exact_catalog_security")
    body = {
        "cik": str(event["cik"]), "sec_event_key": _event_key(event),
        "market_catalog_sha256": catalog_sha256,
        "catalog_common_equity_symbols": current,
        "filing_trading_symbols": filing, "matched_symbols": matched,
        "entity_id": matched[0] if len(matched) == 1 else None,
        "status": "exact_filing_symbol_match" if not reasons else "excluded",
        "reasons": reasons,
    }
    return {**body, "security_identity_receipt_sha256": stable_sha256(body)}


def _paths(moves: Iterable[Mapping[str, Any]], *, trial_id: str, horizon_days: int) -> list[dict[str, Any]]:
    by_security: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in moves:
        by_security[str(row["security_entity_key"])].append(dict(row))
    paths = []
    for rows in by_security.values():
        ordered = sorted(rows, key=lambda row: (
            row["occurred_at"], row["available_at"], row["sec_event_key"],
        ))
        for end in range(len(ordered)):
            for length in (1, 2, 3):
                if end + 1 < length:
                    continue
                members = ordered[end + 1 - length:end + 1]
                gaps = [
                    timestamp_key(str(right["occurred_at"]))
                    - timestamp_key(str(left["occurred_at"]))
                    for left, right in zip(members, members[1:], strict=False)
                ]
                if any(gap <= timedelta(0) or gap > timedelta(days=horizon_days) for gap in gaps):
                    continue
                identity = {
                    "trial_id": trial_id, "entity_id": members[-1]["entity_id"],
                    "security_entity_key": members[-1]["security_entity_key"],
                    "ordered_move_observation_sha256s": [
                        row["move_observation_sha256"] for row in members
                    ],
                }
                paths.append({
                    **identity, "path_id": stable_sha256(identity),
                    "members": members, "path_length": length,
                    "sequence_type": (
                        "single_move" if length == 1 else "connected_strategy_path"
                    ),
                    "path_signature": [row["phenotype"] for row in members],
                    "occurred_interval": {
                        "start": members[0]["occurred_at"],
                        "end": members[-1]["occurred_at"],
                    },
                    "terminal_available_at": members[-1]["available_at"],
                    "discovered_at": members[-1]["observed_at"],
                    "target_move_observation_sha256": members[-1][
                        "move_observation_sha256"
                    ],
                    "inference_block_id": members[-1]["inference_block_id"],
                })
    return paths


def compile_strategy_path_shadow(
    representation: Mapping[str, Any], replay: Mapping[str, Any],
    tournament: Mapping[str, Any], corpus: Mapping[str, Any],
    events: Iterable[Mapping[str, Any]], classifications: Mapping[str, Mapping[str, Any]],
    *, prior: Mapping[str, Any] | None = None, as_of: str | None = None,
    operating_histories: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    bulk_effect_diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze or advance one future-only connected strategy-path observer."""

    learning = _checked(
        representation, STRATEGY_SECURITY_REPRESENTATION_LEARNING_SCHEMA, "learning_sha256",
    )
    replay = _checked(replay, "jaggedthoughts-historical-strategy-event-replay-v1", "replay_sha256")
    tournament = _checked(tournament, STRATEGY_SECURITY_WALK_FORWARD_SCHEMA, "tournament_sha256")
    corpus = _checked(corpus, "jaggedthoughts-historical-strategy-bulk-event-corpus-v2", "corpus_sha256")
    prior_forecasts = {}
    prior_settlements = []
    prior_settlement_blocks = []
    prior_diagnostic_settlements = []
    prior_diagnostic_blocks = []
    prior_operating_forecasts = {}
    prior_operating_settlements = []
    superseded_operating_forecasts = []
    if prior:
        checked_prior = _checked(prior, STRATEGY_PATH_SHADOW_SCHEMA, "shadow_sha256")
        frozen_trial = dict(checked_prior["frozen_trial"])
        frozen_models = dict(checked_prior["frozen_models"])
        trial_id = str(frozen_trial["trial_id"])
        prior_forecasts = {
            str(row["path_id"]): dict(row) for row in checked_prior.get("forecasts") or ()
        }
        prior_settlements = [dict(row) for row in checked_prior.get("settlements") or ()]
        prior_settlement_blocks = [
            dict(row) for row in checked_prior.get("settlement_blocks") or ()
        ]
        prior_diagnostic_settlements = [
            dict(row) for row in checked_prior.get("diagnostic_settlements") or ()
        ]
        prior_diagnostic_blocks = [
            dict(row) for row in checked_prior.get("diagnostic_blocks") or ()
        ]
        prior_operating_forecasts = {
            str(row["move_observation_sha256"]): dict(row)
            for row in checked_prior.get("operating_forecasts") or ()
        }
        prior_operating_settlements = [
            dict(row) for row in checked_prior.get("operating_settlements") or ()
        ]
        superseded_operating_forecasts = [
            dict(row) for row in checked_prior.get("superseded_operating_forecasts") or ()
        ]
        if frozen_trial.get("factor_basis_sha256") is None:
            if frozen_trial.get("selection_tournament_sha256") != tournament[
                "tournament_sha256"
            ]:
                raise ValueError("cannot migrate factor basis from another tournament")
            execution_contract = dict(tournament.get("execution_contract") or {})
            factor_definitions = [
                FactorDefinition.from_dict(row).to_dict()
                for row in execution_contract.get("factor_definitions") or ()
            ]
            factor_basis_sha256 = stable_sha256(factor_definitions)
            if execution_contract.get("factor_basis_sha256") not in {
                None, factor_basis_sha256,
            }:
                raise ValueError("strategy path selection factor basis identity is invalid")
            frozen_trial.update({
                "factor_definitions": factor_definitions,
                "factor_basis_sha256": factor_basis_sha256,
            })
        frozen_trial.setdefault("diagnostic_horizon_days", 90)
    else:
        conjectures = [
            dict(row) for row in learning.get("conjectures") or ()
            if row.get("trial_state") == "same_epoch_behavior_qualified"
            and (row.get("future_evaluation_contract") or {}).get("activation_status")
            == "eligible_to_freeze"
        ]
        if len(conjectures) != 1:
            raise ValueError("strategy path shadow requires exactly one qualified trial")
        conjecture = conjectures[0]
        trial_id = str(conjecture["trial_id"])
        frozen_models = _frozen_models(tournament)
        execution_contract = dict(tournament.get("execution_contract") or {})
        factor_definitions = [
            FactorDefinition.from_dict(row).to_dict()
            for row in execution_contract.get("factor_definitions") or ()
        ]
        factor_basis_sha256 = stable_sha256(factor_definitions)
        if (
            execution_contract.get("factor_basis_sha256") is not None
            and execution_contract["factor_basis_sha256"] != factor_basis_sha256
        ):
            raise ValueError("strategy path selection factor basis identity is invalid")
        frozen_trial = {
            "trial_id": trial_id,
            "conjecture_sha256": conjecture["conjecture_sha256"],
            "qualification_sha256": (
                conjecture.get("same_epoch_behavior_qualification") or {}
            ).get("qualification_sha256"),
            "selection_cutoff": (conjecture.get("trial_identity") or {})[
                "selection_cutoff"
            ],
            "evaluation_surface_sha256": (conjecture.get("trial_identity") or {}).get(
                "evaluation_surface_sha256"
            ),
            "challenger_grammar_digest": (conjecture.get("trial_identity") or {}).get(
                "challenger_grammar_digest"
            ),
            "selection_tournament_sha256": tournament["tournament_sha256"],
            "execution_contract_sha256": stable_sha256(
                execution_contract
            ),
            "factor_definitions": factor_definitions,
            "factor_basis_sha256": factor_basis_sha256,
            "horizon_days": int(
                (tournament.get("execution_contract") or {}).get("horizon_days") or 365
            ),
            "diagnostic_horizon_days": 90,
            "entry_lag_sessions": int(
                (tournament.get("execution_contract") or {}).get(
                    "entry_lag_sessions"
                ) or 2
            ),
            "round_trip_cost_bps": float(
                (tournament.get("execution_contract") or {}).get(
                    "round_trip_cost_bps"
                ) or 0.0
            ),
            "selection_accession_numbers": sorted(
                _selection_accessions(replay, conjecture)
            ),
            "minimum_independent_blocks": int(
                (conjecture.get("future_evaluation_contract") or {}).get(
                    "minimum_independent_blocks"
                ) or 8
            ),
        }
    cutoff = canonical_timestamp(
        str(frozen_trial["selection_cutoff"]), "strategy path selection cutoff",
    )
    epoch = canonical_timestamp(as_of or _now(), "strategy path shadow as_of")
    if timestamp_key(epoch) < timestamp_key(cutoff):
        raise ValueError("strategy path shadow cannot precede its selection cutoff")
    frozen_operating_models = (
        dict(checked_prior.get("frozen_operating_models") or {})
        if prior else {}
    )
    desired_operating_models = _frozen_operating_models(
        replay, bulk_effect_diagnostics,
    )
    if (
        not ((frozen_operating_models.get("models") or [{}, {}])[1].get("cell_support"))
        or frozen_operating_models.get("model_set_sha256")
        != desired_operating_models["model_set_sha256"]
    ):
        superseded_operating_forecasts.extend(prior_operating_forecasts.values())
        prior_operating_forecasts = {}
        prior_operating_settlements = []
        frozen_operating_models = desired_operating_models
    horizon = int(frozen_trial["horizon_days"])
    postcutoff = _postcutoff_events(
        events, cutoff=cutoff, as_of=epoch,
        excluded_accessions=set(map(str, frozen_trial["selection_accession_numbers"])),
    )
    acquisition: dict[str, dict[str, Any]] = {}
    sic2_by_event_key = {
        _event_key(row): str(row.get("sic") or "")[:2] or "unknown"
        for row in postcutoff
    }
    prior_moves = {
        str(row["sec_event_key"]): {
            **dict(row),
            "sic2": str(row.get("sic2") or sic2_by_event_key.get(
                str(row["sec_event_key"]), "unknown",
            )),
        }
        for row in (checked_prior.get("moves") or () if prior else ())
    }
    moves = dict(prior_moves)
    identity_blocks = []
    for event in postcutoff:
        accession = str(event["accession_number"])
        if accession not in classifications:
            acquisition[accession] = {
                key: event[key] for key in (
                    "event_sha256", "accession_number", "cik", "primary_document",
                    "available_at", "company_name", "current_common_equity_symbols",
                )
            }
            continue
        event_key = _event_key(event)
        if event_key in moves:
            continue
        classification = classifications[accession]
        identity = _security_identity(
            event, classification, catalog_sha256=str(corpus["market_catalog_sha256"]),
        )
        if identity["status"] != "exact_filing_symbol_match":
            identity_blocks.append(identity)
            continue
        phenotype = canonicalize_strategy_event_phenotype(classification)
        if phenotype["strategy_event_eligibility"] not in _ELIGIBLE:
            continue
        observed = {
            "sec_event_key": event_key, "event_snapshot_sha256": event["event_sha256"],
            "cik": str(event["cik"]), "entity_id": identity["entity_id"],
            "accession_number": accession, "occurred_at": event["occurred_at"],
            "available_at": event["available_at"], "observed_at": epoch,
            "sic2": str(event.get("sic") or "")[:2] or "unknown",
            "filing_document_sha256": classification["filing_document_sha256"],
            "classification_receipt_sha256": classification[
                "classification_receipt_sha256"
            ],
            "security_identity_receipt_sha256": identity[
                "security_identity_receipt_sha256"
            ],
            "security_entity_key": stable_sha256({
                "cik": str(event["cik"]), "entity_id": identity["entity_id"],
            }),
            "security_identity": identity, "phenotype": phenotype,
            "inference_block_id": (
                f"event-quarter:{event['filing_date'][:4]}-"
                f"Q{(int(event['filing_date'][5:7]) - 1) // 3 + 1}"
            ),
        }
        moves[event_key] = {
            **observed, "move_observation_sha256": stable_sha256(observed),
        }
    sequences = _paths(moves.values(), trial_id=trial_id, horizon_days=horizon)
    typed_paths = [row for row in sequences if int(row["path_length"]) >= 2]
    forecasts_by_id = dict(prior_forecasts)
    for path in sorted({row["path_id"]: row for row in sequences}.values(), key=lambda row: row["path_id"]):
        if path["path_id"] in prior_forecasts:
            continue
        cells = [_cell(row["phenotype"]) for row in path["members"]]
        isolated = _move_prediction(frozen_models, cells[-1])
        member_predictions = [_move_prediction(frozen_models, cell) for cell in cells]
        weights = list(range(1, len(member_predictions) + 1))
        predictions = {
            "untyped_global_median": frozen_models["models"][0]["global_prediction"],
            "isolated_final_move": isolated,
        }
        if int(path["path_length"]) >= 2:
            predictions["ordered_path_composition"] = sum(
                weight * value for weight, value in zip(weights, member_predictions, strict=True)
            ) / sum(weights)
        body = {
            **path, "issued_at": epoch, "trained_through": cutoff,
            "model_set_sha256": frozen_models["model_set_sha256"],
            "predicted_values": predictions,
            "settlement_contract": {
                "entry_rule": "shared market-session index after issued_at",
                "entry_lag_sessions": frozen_trial["entry_lag_sessions"],
                "benchmark_id": "SPY", "horizon_days": horizon,
                "round_trip_cost_bps": frozen_trial["round_trip_cost_bps"],
                "target_metric_id": frozen_models["target_metric_id"],
                "not_before": (
                    timestamp_key(epoch) + timedelta(days=horizon)
                ).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "diagnostic_horizon_days": frozen_trial[
                    "diagnostic_horizon_days"
                ],
                "diagnostic_not_before": (
                    timestamp_key(epoch) + timedelta(
                        days=int(frozen_trial["diagnostic_horizon_days"])
                    )
                ).isoformat(timespec="seconds").replace("+00:00", "Z"),
            },
            "status": "forecast_open", "security_ranking_use": False,
            "paper_policy_authority": False, "capital_authority": False,
        }
        forecasts_by_id[path["path_id"]] = {
            **body, "forecast_sha256": stable_sha256(body),
        }
    forecasts = [forecasts_by_id[key] for key in sorted(forecasts_by_id)]
    histories = {
        str(key): [dict(row) for row in values]
        for key, values in (operating_histories or {}).items()
    }
    operating_forecasts_by_id = dict(prior_operating_forecasts)
    operating_blocks = []
    for sequence in sorted(sequences, key=lambda row: row["path_id"]):
        if int(sequence["path_length"]) != 1:
            continue
        move = sequence["members"][0]
        move_sha = str(move["move_observation_sha256"])
        if move_sha in operating_forecasts_by_id:
            continue
        baseline = _operating_baseline(
            histories.get(str(move["cik"]), ()),
            occurred_at=str(move["occurred_at"]), issued_at=epoch,
        )
        if baseline is None:
            operating_blocks.append({
                "move_observation_sha256": move_sha,
                "entity_id": move["entity_id"],
                "reason": "point_in_time_operating_baseline_unavailable",
            })
            continue
        due = (
            timestamp_key(str(move["occurred_at"])) + timedelta(days=365)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        body = {
            "schema": "jaggedthoughts-strategy-operating-shadow-forecast-v1",
            "trial_id": trial_id,
            "move_observation_sha256": move_sha,
            "entity_id": move["entity_id"], "cik": move["cik"],
            "accession_number": move["accession_number"],
            "phenotype": move["phenotype"],
            "sic2": move["sic2"],
            "occurred_at": move["occurred_at"], "issued_at": epoch,
            "trained_through": cutoff,
            "model_set_sha256": frozen_operating_models["model_set_sha256"],
            **_operating_prediction(
                frozen_operating_models, move["phenotype"], sic2=str(move["sic2"]),
            ),
            "baseline": baseline,
            "settlement_contract": {
                "metric_id": "owner_earnings_margin", "unit": "decimal",
                "target": "owner_earnings_margin_delta",
                "comparator": "latest_public_pre_move_baseline",
                "horizon_days": 365, "not_before": due,
                "outcome_rule": "earliest public annual observation at or after not_before",
            },
            "status": "forecast_open", "security_ranking_use": False,
            "paper_policy_authority": False, "capital_authority": False,
        }
        operating_forecasts_by_id[move_sha] = {
            **body, "operating_forecast_sha256": stable_sha256(body),
        }
    operating_forecasts = [
        operating_forecasts_by_id[key] for key in sorted(operating_forecasts_by_id)
    ]
    operating_settlements_by_id = {
        str(row["operating_forecast_sha256"]): dict(row)
        for row in prior_operating_settlements
    }
    for forecast in operating_forecasts:
        forecast_sha = str(forecast["operating_forecast_sha256"])
        if forecast_sha in operating_settlements_by_id or timestamp_key(epoch) < timestamp_key(
            str(forecast["settlement_contract"]["not_before"])
        ):
            continue
        outcomes = [
            dict(row) for row in histories.get(str(forecast["cik"]), ())
            if timestamp_key(str(row["observed_at"])) >= timestamp_key(
                str(forecast["settlement_contract"]["not_before"])
            ) and timestamp_key(str(row["available_at"])) <= timestamp_key(epoch)
        ]
        if not outcomes:
            operating_blocks.append({
                "operating_forecast_sha256": forecast_sha,
                "entity_id": forecast["entity_id"],
                "reason": "post_horizon_operating_observation_unavailable",
            })
            continue
        outcome = min(outcomes, key=lambda row: (
            timestamp_key(str(row["observed_at"])), timestamp_key(str(row["available_at"])),
        ))
        actual = float(outcome["owner_earnings_margin"]) - float(
            forecast["baseline"]["owner_earnings_margin"]
        )
        body = {
            "schema": "jaggedthoughts-strategy-operating-shadow-settlement-v1",
            "operating_forecast_sha256": forecast_sha,
            "move_observation_sha256": forecast["move_observation_sha256"],
            "entity_id": forecast["entity_id"], "settled_at": epoch,
            "issued_at": forecast["issued_at"],
            "outcome": outcome, "actual_delta": actual,
            "model_results": {
                model_id: {
                    "prediction": float(prediction),
                    "absolute_error": abs(float(prediction) - actual),
                }
                for model_id, prediction in forecast["predicted_deltas"].items()
            },
            "inference_block_id": f"fiscal-year:{str(outcome['observed_at'])[:4]}",
            "security_ranking_use": False, "paper_policy_authority": False,
            "capital_authority": False,
        }
        operating_settlements_by_id[forecast_sha] = {
            **body, "operating_settlement_sha256": stable_sha256(body),
        }
    operating_settlements = [
        operating_settlements_by_id[key] for key in sorted(operating_settlements_by_id)
    ]
    operating_tournament = _strategy_operating_tournament(
        operating_settlements,
        forecasts=operating_forecasts,
        minimum_blocks=int(frozen_trial["minimum_independent_blocks"]),
        as_of=epoch,
        model_set_sha256=str(frozen_operating_models["model_set_sha256"]),
    )
    event_research_queue = _event_research_queue(
        moves.values(), operating_forecasts, forecasts,
    )
    minimum_blocks = int(frozen_trial["minimum_independent_blocks"])
    body = {
        "schema": STRATEGY_PATH_SHADOW_SCHEMA, "compiled_at": epoch,
        "trial_id": trial_id, "conjecture_sha256": frozen_trial["conjecture_sha256"],
        "frozen_trial": frozen_trial,
        "selection_cutoff": cutoff,
        "evaluation_surface_sha256": frozen_trial["evaluation_surface_sha256"],
        "corpus_sha256": corpus["corpus_sha256"],
        "bulk_source_receipt_sha256": corpus["bulk_source_receipt_sha256"],
        "model_set_sha256": frozen_models["model_set_sha256"],
        "frozen_models": frozen_models,
        "frozen_operating_models": frozen_operating_models,
        "postcutoff_event_count": len(postcutoff),
        "moves": [moves[key] for key in sorted(moves)],
        "move_count": len(moves),
        "typed_path_count": len(typed_paths),
        "single_move_sequence_count": sum(
            int(row["path_length"]) == 1 for row in sequences
        ),
        "identity_blocks": identity_blocks,
        "acquisition_queue": sorted(
            acquisition.values(), key=lambda row: (row["available_at"], row["accession_number"]),
            reverse=True,
        ),
        "forecasts": forecasts, "forecast_count": len(forecasts),
        "single_move_forecast_count": sum(
            int(row["path_length"]) == 1 for row in forecasts
        ),
        "connected_path_forecast_count": sum(
            int(row["path_length"]) >= 2 for row in forecasts
        ),
        "operating_forecasts": operating_forecasts,
        "superseded_operating_forecasts": superseded_operating_forecasts,
        "operating_forecast_count": len(operating_forecasts),
        "operating_settlements": operating_settlements,
        "operating_settled_forecast_count": len(operating_settlements),
        "operating_blocks": operating_blocks,
        "operating_tournament": operating_tournament,
        "event_research_queue": event_research_queue,
        "event_research_queue_count": len(event_research_queue),
        "settlements": prior_settlements,
        "settlement_blocks": prior_settlement_blocks,
        "settled_forecast_count": len(prior_settlements),
        "diagnostic_settlements": prior_diagnostic_settlements,
        "diagnostic_blocks": prior_diagnostic_blocks,
        "diagnostic_settled_forecast_count": len(prior_diagnostic_settlements),
        "diagnostic_horizon_days": frozen_trial["diagnostic_horizon_days"],
        "diagnostic_promotion_authority": False,
        "independent_block_count": 0,
        "issued_forecast_time_block_count": len({
            str(row["inference_block_id"]) for row in forecasts
        }),
        "minimum_independent_blocks": minimum_blocks,
        "status": (
            "prospective_shadow_issued_awaiting_settlement" if forecasts
            else "prospective_shadow_acquiring" if acquisition
            else "prospective_shadow_frozen_collecting"
        ),
        "next_activation": (
            "Acquire and type the newest path-candidate filings."
            if acquisition else
            "Settle due operating and return forecasts under their separate frozen model sets."
            if forecasts else
            "Refresh the nightly SEC submissions archive and observe the first post-freeze path."
        ),
        "historical_retrofit_allowed": False, "automatic_model_refit": False,
        "security_ranking_use": False, "security_alpha_claim": False,
        "paper_policy_authority": False, "capital_authority": False,
    }
    return {**body, "shadow_sha256": stable_sha256(body)}


def _price_series(
    points: Iterable[PricePoint], entity_id: str,
) -> dict[str, PricePoint]:
    rows: dict[str, PricePoint] = {}
    for point in points:
        if point.entity_id != entity_id:
            continue
        current = rows.get(point.date_key)
        if current is None or (
            point.available_at, point.observed_at, point.observation_id
        ) > (current.available_at, current.observed_at, current.observation_id):
            rows[point.date_key] = point
    return rows


def _purged_horizon_cohorts(
    rows: Iterable[Mapping[str, Any]], *, selection_cutoff: str, horizon_days: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Admit only outcome windows contained in disjoint two-horizon cohorts."""

    anchor = timestamp_key(selection_cutoff)
    stride = timedelta(days=2 * horizon_days)
    admitted, purged = [], []
    for raw in rows:
        row = dict(raw)
        entry = timestamp_key(str(row["entry_observed_at"]))
        exit_at = timestamp_key(str(row["exit_observed_at"]))
        cohort_index = max(
            0, int((entry - anchor).total_seconds() // stride.total_seconds()),
        )
        cohort_start = anchor + cohort_index * stride
        cohort_end = cohort_start + stride
        if entry < cohort_start or exit_at > cohort_end:
            purged.append(str(row["forecast_sha256"]))
            continue
        row["inference_block_id"] = (
            f"purged-horizon:{cohort_start.date().isoformat()}:"
            f"{cohort_end.date().isoformat()}"
        )
        admitted.append(row)
    return admitted, sorted(purged)


def _strategy_operating_tournament(
    settlements: Iterable[Mapping[str, Any]], *,
    forecasts: Iterable[Mapping[str, Any]], minimum_blocks: int,
    as_of: str, model_set_sha256: str,
) -> dict[str, Any]:
    rows = [dict(row) for row in settlements]
    forecast_rows = [dict(row) for row in forecasts]
    model_ids = tuple(sorted({
        str(model_id) for row in forecast_rows
        for model_id in (row.get("predicted_deltas") or {})
    }, key=lambda value: (
        value != "untyped_operating_global_median",
        value != "typed_operating_phenotype", value,
    )))
    if "untyped_operating_global_median" not in model_ids:
        raise ValueError("strategy operating tournament lost its baseline model")
    if not rows:
        body = {
            "schema": "jaggedthoughts-strategy-operating-shadow-tournament-v1",
            "settled_forecast_count": 0, "independent_block_count": 0,
            "minimum_independent_blocks": minimum_blocks,
            "model_ids": list(model_ids),
            "status": "collecting_operating_outcomes",
            "operating_representation_credit": False,
            "security_ranking_use": False, "paper_policy_authority": False,
            "capital_authority": False,
        }
        return {**body, "tournament_sha256": stable_sha256(body)}
    forecasts_by_sha = {
        str(row["operating_forecast_sha256"]): row for row in forecast_rows
    }
    if any(set(row.get("model_results") or {}) != set(model_ids) for row in rows):
        raise ValueError("strategy operating tournament requires a complete model matrix")
    models = tuple(
        WorldModelCandidate(
            model_id=model_id, version="frozen-v1",
            model_family=(
                "control" if model_id == "untyped_operating_global_median"
                else "strategy_operating"
            ),
            trial_family_id=f"strategy-operating:{model_id}",
            mechanism_ids=(model_id,), linked_observable_ids=(),
            source_refs=(f"frozen-strategy-operating-model-set:{model_set_sha256}",),
            generation_process="deterministic",
        )
        for model_id in model_ids
    )
    episodes = tuple(
        BacktestEpisode(
            episode_id=str(row["operating_forecast_sha256"]),
            inference_block_id=str(row["inference_block_id"]),
            entity_id=str(row["entity_id"]),
            start_at=str(row["issued_at"]), end_at=str(row["outcome"]["observed_at"]),
            outcome_available_at=str(row["outcome"]["available_at"]),
            starting_weight=0.0, asset_return=0.0, benchmark_return=0.0,
            cash_return=0.0,
            actual_values={"owner_earnings_margin_delta": float(row["actual_delta"])},
            source_refs=(f"operating-settlement:{row['operating_settlement_sha256']}",),
        )
        for row in rows
    )
    predictions = tuple(
        WorldModelForecast(
            model_id=model_id,
            episode_id=str(row["operating_forecast_sha256"]),
            trained_through=str(forecasts_by_sha[str(row["operating_forecast_sha256"])][
                "trained_through"
            ]),
            issued_at=str(row["issued_at"]),
            predicted_values={
                "owner_earnings_margin_delta": float(row["model_results"][model_id]["prediction"]),
            },
            target_weight=0.0,
            source_refs=(f"operating-forecast:{row['operating_forecast_sha256']}:{model_id}",),
        )
        for row in rows for model_id in model_ids
    )
    shared = evaluate_world_model_tournament(
        tournament_id="strategy-operating-shadow-v1", owner="jaggedthoughts-capital",
        as_of=as_of, mode="prospective_shadow",
        baseline_model_id="untyped_operating_global_median",
        observables=(ObservableSpec(
            observable_id="owner_earnings_margin_delta", unit="decimal",
            loss="absolute", scale=0.1, weight=1.0,
        ),),
        models=models, episodes=episodes, forecasts=predictions,
        transaction_cost_bps=0.0,
        declared_trial_family_ids=tuple(model.trial_family_id for model in models),
        source_refs=(f"frozen-strategy-operating-model-set:{model_set_sha256}",),
        min_inference_blocks=minimum_blocks, periods_per_year=1.0,
    )
    direct_blocks = {
        "typed_operating_phenotype": len({
            str(row["inference_block_id"]) for row in rows
            if forecasts_by_sha[str(row["operating_forecast_sha256"])].get(
                "typed_prediction_basis"
            ) == "exact_phenotype"
        }),
        "group_time_strategy_family": len({
            str(row["inference_block_id"]) for row in rows
            if forecasts_by_sha[str(row["operating_forecast_sha256"])].get(
                "group_time_prediction_basis"
            ) == "sic2_implementation_mode_family"
        }),
    }
    supported_models = (
        [
            model_id for model_id in shared["survivor_model_ids"]
            if model_id != "untyped_operating_global_median"
            and direct_blocks.get(model_id, 0) >= minimum_blocks
        ] if shared["inference_sufficient"] else []
    )
    supported = bool(supported_models)
    body = {
        "schema": "jaggedthoughts-strategy-operating-shadow-tournament-v1",
        "settled_forecast_count": len(rows),
        "independent_block_count": shared["inference_block_count"],
        "minimum_independent_blocks": minimum_blocks,
        "model_ids": list(model_ids),
        "shared_world_model_evaluation": shared,
        "direct_model_inference_block_count": direct_blocks,
        "status": (
            "operating_challenger_supported_for_manual_review" if supported else
            "operating_challengers_not_supported" if shared["inference_sufficient"] else
            "collecting_independent_operating_blocks"
        ),
        "supported_model_ids": supported_models,
        "operating_representation_credit": supported,
        "security_ranking_use": False, "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "tournament_sha256": stable_sha256(body)}


def _strategy_path_tournament(
    settlements: Iterable[Mapping[str, Any]], *, minimum_blocks: int, as_of: str,
    selection_cutoff: str, horizon_days: int, model_set_sha256: str,
    model_ids: tuple[str, ...] = (
        "untyped_global_median", "isolated_final_move", "ordered_path_composition",
    ),
    challenger: str = "ordered_path_composition",
    tournament_id: str = "strategy-path-shadow-v2",
    schema: str = "jaggedthoughts-strategy-path-shadow-tournament-v2",
) -> dict[str, Any]:
    rows = [dict(row) for row in settlements]
    admitted, purged = _purged_horizon_cohorts(
        rows, selection_cutoff=selection_cutoff, horizon_days=horizon_days,
    )
    if not admitted:
        body = {
            "schema": schema,
            "settled_forecast_count": 0,
            "observed_settled_forecast_count": len(rows),
            "purged_overlapping_window_count": len(purged),
            "purged_forecast_sha256s": purged,
            "independent_block_count": 0,
            "minimum_independent_blocks": minimum_blocks,
            "complete_model_episode_matrix": True,
            "shared_world_model_evaluation": None,
            "status": "collecting_non_overlapping_horizon_cohorts",
            "representation_credit": False,
            "automatic_grammar_activation": False,
            "security_ranking_use": False,
            "paper_policy_authority": False,
            "capital_authority": False,
        }
        return {**body, "tournament_sha256": stable_sha256(body)}
    rows = admitted
    if any(set(row.get("model_results") or {}) != set(model_ids) for row in rows):
        raise ValueError("strategy path tournament requires a complete model matrix")
    settlement_source_ref = f"strategy-path-settlements:{stable_sha256(rows)}"
    model_source_ref = f"frozen-strategy-path-model-set:{model_set_sha256}"
    models = tuple(
        WorldModelCandidate(
            model_id=model_id, version="frozen-v1",
            model_family=("strategy_path" if model_id == challenger else "control"),
            trial_family_id=f"strategy-path:{model_id}",
            mechanism_ids=(model_id,), linked_observable_ids=(),
            source_refs=(model_source_ref,), generation_process="deterministic",
        )
        for model_id in model_ids
    )
    episodes = tuple(
        BacktestEpisode(
            episode_id=str(row["forecast_sha256"]),
            inference_block_id=str(row["inference_block_id"]),
            entity_id=str(row["entity_id"]),
            start_at=str(row["entry_observed_at"]),
            end_at=str(row["exit_observed_at"]),
            outcome_available_at=str(row["settled_at"]),
            starting_weight=0.0,
            asset_return=math.expm1(float(row["target_value"])),
            benchmark_return=0.0, cash_return=0.0,
            actual_values={"factor_controlled_log_return": float(row["target_value"])},
            source_refs=(f"settlement:{row['settlement_sha256']}",),
        )
        for row in rows
    )
    forecasts = tuple(
        WorldModelForecast(
            model_id=model_id,
            episode_id=str(row["forecast_sha256"]),
            trained_through=str(row["trained_through"]),
            issued_at=str(row["issued_at"]),
            predicted_values={
                "factor_controlled_log_return": float(
                    row["model_results"][model_id]["prediction"]
                ),
            },
            target_weight=(
                1.0 if float(row["model_results"][model_id]["prediction"]) > 0 else 0.0
            ),
            source_refs=(f"forecast:{row['forecast_sha256']}:{model_id}",),
        )
        for row in rows for model_id in model_ids
    )
    shared = evaluate_world_model_tournament(
        tournament_id=tournament_id, owner="jaggedthoughts-capital",
        as_of=as_of, mode="prospective_shadow",
        baseline_model_id="untyped_global_median",
        observables=(ObservableSpec(
            observable_id="factor_controlled_log_return", unit="log_return",
            loss="absolute", scale=1.0, weight=1.0,
        ),),
        models=models, episodes=episodes, forecasts=forecasts,
        transaction_cost_bps=0.0,
        declared_trial_family_ids=tuple(model.trial_family_id for model in models),
        source_refs=(model_source_ref, settlement_source_ref),
        min_inference_blocks=minimum_blocks,
        periods_per_year=1.0,
    )
    supported = bool(
        shared["inference_sufficient"]
        and shared["survivor_model_ids"] == [challenger]
    )
    body = {
        "schema": schema,
        "settled_forecast_count": len(rows),
        "observed_settled_forecast_count": len(rows) + len(purged),
        "purged_overlapping_window_count": len(purged),
        "purged_forecast_sha256s": purged,
        "independent_block_count": shared["inference_block_count"],
        "minimum_independent_blocks": minimum_blocks,
        "complete_model_episode_matrix": True,
        "temporal_independence_contract": (
            "two-horizon fixed cohorts; outcome windows crossing a cohort boundary are purged"
        ),
        "shared_world_model_evaluation": shared,
        "status": (
            "challenger_supported_for_manual_grammar_default_review" if supported
            else "challenger_not_supported" if shared["inference_sufficient"]
            else "collecting_independent_blocks"
        ),
        "representation_credit": supported,
        "automatic_grammar_activation": False,
        "security_ranking_use": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "tournament_sha256": stable_sha256(body)}


def _factor_controlled_horizon_outcome(
    forecast: Mapping[str, Any], *, points: tuple[PricePoint, ...],
    factors: tuple[FactorDefinition, ...], evidence_as_of: str,
    checked_at: str, horizon_days: int, analysis_suffix: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    entity_id = str(forecast["entity_id"])
    entity_ids = {entity_id, *(
        value for factor in factors
        for value in (factor.long_entity_id, factor.short_entity_id) if value
    )}
    series = {key: _price_series(points, key) for key in entity_ids}
    shared = sorted(set.intersection(*(set(series[key]) for key in sorted(entity_ids))))
    eligible = [day for day in shared if day > str(forecast["issued_at"])[:10]]
    lag = int(forecast["settlement_contract"]["entry_lag_sessions"])
    if len(eligible) <= lag:
        return None, {"reason": "shared_entry_price_unavailable", "checked_at": checked_at}
    entry = series[entity_id][eligible[lag]]
    target = timestamp_key(entry.observed_at) + timedelta(days=horizon_days)
    exits = [
        day for day in shared
        if timestamp_key(series[entity_id][day].observed_at) >= target
    ]
    if not exits:
        return None, {"reason": "shared_exit_price_unavailable", "checked_at": checked_at}
    exit_point = series[entity_id][exits[0]]
    try:
        control = compile_historical_factor_control(
            analysis_id=f"strategy-path:{analysis_suffix}:{forecast['forecast_sha256']}",
            candidate_entity_id=entity_id, factors=factors,
            price_points=points, evidence_as_of=evidence_as_of,
            calibration_end=str(forecast["issued_at"]),
            settlement_start=entry.observed_at,
            settlement_end=exit_point.observed_at,
            round_trip_cost_bps=float(
                forecast["settlement_contract"]["round_trip_cost_bps"]
            ),
        )
    except (InsufficientFactorHistoryError, ValueError) as error:
        return None, {
            "reason": "factor_control_unavailable", "detail": str(error)[:1_000],
            "checked_at": checked_at,
        }
    return {
        "entity_id": entity_id,
        "entry_observed_at": entry.observed_at,
        "exit_observed_at": exit_point.observed_at,
        "target_value": float(
            control["realized"]["factor_controlled_log_return_after_cost"]
        ),
        "factor_control": control,
    }, None


def _short_horizon_diagnostic(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    settlements = [dict(row) for row in rows]
    model_ids = sorted({
        str(model_id) for row in settlements
        for model_id in (row.get("model_results") or {})
    })
    summaries = []
    for model_id in model_ids:
        results = [row["model_results"][model_id] for row in settlements]
        summaries.append({
            "model_id": model_id,
            "mean_horizon_scaled_absolute_error": sum(
                float(row["horizon_scaled_absolute_error"]) for row in results
            ) / len(results),
            "direction_accuracy": sum(bool(row["direction_correct"]) for row in results)
            / len(results),
            "mean_long_cash_paper_return": sum(
                float(row["long_cash_paper_return"]) for row in results
            ) / len(results),
        })
    body = {
        "schema": "jaggedthoughts-strategy-path-short-horizon-diagnostic-v1",
        "settlement_count": len(settlements), "model_summaries": summaries,
        "status": "observed_dependent_diagnostic" if settlements else "collecting",
        "dependence_boundary": (
            "event-level observations may overlap; no independent-block inference"
        ),
        "representation_credit": False, "routing_authority": False,
        "security_ranking_use": False, "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "diagnostic_sha256": stable_sha256(body)}


def settle_strategy_path_shadow(
    shadow: Mapping[str, Any], price_points: Iterable[PricePoint],
    factors: Iterable[FactorDefinition], *, evidence_as_of: str,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Settle due immutable forecasts against a pre-issue factor fit."""

    checked = _checked(shadow, STRATEGY_PATH_SHADOW_SCHEMA, "shadow_sha256")
    epoch = canonical_timestamp(as_of or _now(), "strategy path settlement as_of")
    evidence_epoch = canonical_timestamp(
        evidence_as_of, "strategy path settlement evidence_as_of",
    )
    points = tuple(price_points)
    factor_rows = tuple(factors)
    if stable_sha256([row.to_dict() for row in factor_rows]) != (
        checked.get("frozen_trial") or {}
    ).get("factor_basis_sha256"):
        raise ValueError("strategy path settlement crossed its frozen factor basis")
    settlements = {}
    for row in checked.get("settlements") or ():
        body = dict(row)
        claimed = str(body.pop("settlement_sha256", ""))
        if not claimed or stable_sha256(body) != claimed:
            raise ValueError("invalid strategy path settlement receipt")
        settlements[str(row["forecast_sha256"])] = dict(row)
    blocks = {
        str(row["forecast_sha256"]): dict(row)
        for row in checked.get("settlement_blocks") or ()
    }
    diagnostic_settlements = {}
    for row in checked.get("diagnostic_settlements") or ():
        body = dict(row)
        claimed = str(body.pop("diagnostic_settlement_sha256", ""))
        if not claimed or stable_sha256(body) != claimed:
            raise ValueError("invalid strategy path diagnostic settlement receipt")
        diagnostic_settlements[str(row["forecast_sha256"])] = dict(row)
    diagnostic_blocks = {
        str(row["forecast_sha256"]): dict(row)
        for row in checked.get("diagnostic_blocks") or ()
    }
    diagnostic_horizon = int(checked["frozen_trial"]["diagnostic_horizon_days"])
    primary_horizon = int(checked["frozen_trial"]["horizon_days"])
    for forecast in checked.get("forecasts") or ():
        forecast_sha = str(forecast["forecast_sha256"])
        if forecast_sha in diagnostic_settlements:
            continue
        diagnostic_due = (forecast.get("settlement_contract") or {}).get(
            "diagnostic_not_before"
        ) or (
            timestamp_key(str(forecast["issued_at"]))
            + timedelta(days=diagnostic_horizon)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        if timestamp_key(epoch) < timestamp_key(str(diagnostic_due)):
            continue
        outcome, failure = _factor_controlled_horizon_outcome(
            forecast, points=points, factors=factor_rows,
            evidence_as_of=evidence_epoch, checked_at=epoch,
            horizon_days=diagnostic_horizon, analysis_suffix="short-diagnostic",
        )
        if failure is not None:
            diagnostic_blocks[forecast_sha] = {
                "forecast_sha256": forecast_sha, **failure,
            }
            continue
        assert outcome is not None
        scaled_target = float(outcome["target_value"]) * (
            primary_horizon / diagnostic_horizon
        )
        body = {
            "schema": "jaggedthoughts-strategy-path-short-horizon-settlement-v1",
            "forecast_sha256": forecast_sha, "path_id": forecast["path_id"],
            "path_length": int(forecast["path_length"]),
            "sequence_type": forecast["sequence_type"],
            "entity_id": outcome["entity_id"], "settled_at": epoch,
            "evidence_as_of": evidence_epoch,
            "diagnostic_horizon_days": diagnostic_horizon,
            "primary_horizon_days": primary_horizon,
            "entry_observed_at": outcome["entry_observed_at"],
            "exit_observed_at": outcome["exit_observed_at"],
            "raw_target_value": outcome["target_value"],
            "horizon_scaled_target_value": scaled_target,
            "scaling_rule": "diagnostic_log_return_times_primary_over_diagnostic_days",
            "model_results": {
                model_id: {
                    "prediction": float(prediction),
                    "horizon_scaled_absolute_error": abs(
                        float(prediction) - scaled_target
                    ),
                    "direction_correct": (float(prediction) >= 0) == (
                        float(outcome["target_value"]) >= 0
                    ),
                    "long_cash_paper_return": (
                        math.expm1(float(outcome["target_value"]))
                        if float(prediction) > 0 else 0.0
                    ),
                }
                for model_id, prediction in forecast["predicted_values"].items()
            },
            "factor_control": outcome["factor_control"],
            "representation_credit": False, "routing_authority": False,
            "security_ranking_use": False, "paper_policy_authority": False,
            "capital_authority": False,
        }
        diagnostic_settlements[forecast_sha] = {
            **body, "diagnostic_settlement_sha256": stable_sha256(body),
        }
        diagnostic_blocks.pop(forecast_sha, None)
    for forecast in checked.get("forecasts") or ():
        forecast_sha = str(forecast["forecast_sha256"])
        if forecast_sha in settlements:
            continue
        if timestamp_key(epoch) < timestamp_key(
            str(forecast["settlement_contract"]["not_before"])
        ):
            continue
        outcome, failure = _factor_controlled_horizon_outcome(
            forecast, points=points, factors=factor_rows,
            evidence_as_of=evidence_epoch, checked_at=epoch,
            horizon_days=primary_horizon, analysis_suffix="primary",
        )
        if failure is not None:
            blocks[forecast_sha] = {"forecast_sha256": forecast_sha, **failure}
            continue
        assert outcome is not None
        target_value = float(outcome["target_value"])
        body = {
            "schema": "jaggedthoughts-strategy-path-settlement-v1",
            "forecast_sha256": forecast_sha,
            "path_id": forecast["path_id"],
            "path_length": int(forecast["path_length"]),
            "sequence_type": forecast["sequence_type"],
            "entity_id": outcome["entity_id"],
            "inference_block_id": forecast["inference_block_id"],
            "trained_through": forecast["trained_through"],
            "issued_at": forecast["issued_at"],
            "settled_at": epoch,
            "evidence_as_of": evidence_epoch,
            "entry_observed_at": outcome["entry_observed_at"],
            "exit_observed_at": outcome["exit_observed_at"],
            "target_metric_id": forecast["settlement_contract"]["target_metric_id"],
            "target_value": target_value,
            "model_results": {
                model_id: {
                    "prediction": float(prediction),
                    "absolute_error": abs(float(prediction) - target_value),
                    "long_cash_paper_return": (
                        math.expm1(target_value) if float(prediction) > 0 else 0.0
                    ),
                }
                for model_id, prediction in forecast["predicted_values"].items()
            },
            "factor_control": outcome["factor_control"],
            "security_ranking_use": False,
            "paper_policy_authority": False,
            "capital_authority": False,
        }
        settlements[forecast_sha] = {
            **body, "settlement_sha256": stable_sha256(body),
        }
        blocks.pop(forecast_sha, None)
    settled_rows = [settlements[key] for key in sorted(settlements)]
    diagnostic_rows = [
        diagnostic_settlements[key] for key in sorted(diagnostic_settlements)
    ]
    short_horizon_diagnostic = _short_horizon_diagnostic(diagnostic_rows)
    path_tournament = _strategy_path_tournament(
        [row for row in settled_rows if int(row.get("path_length") or 0) >= 2],
        minimum_blocks=int(checked["minimum_independent_blocks"]),
        as_of=epoch,
        selection_cutoff=str(checked["selection_cutoff"]),
        horizon_days=int(checked["frozen_trial"]["horizon_days"]),
        model_set_sha256=str(checked["model_set_sha256"]),
    )
    move_tournament = _strategy_path_tournament(
        [row for row in settled_rows if int(row.get("path_length") or 0) == 1],
        minimum_blocks=int(checked["minimum_independent_blocks"]),
        as_of=epoch,
        selection_cutoff=str(checked["selection_cutoff"]),
        horizon_days=int(checked["frozen_trial"]["horizon_days"]),
        model_set_sha256=str(checked["model_set_sha256"]),
        model_ids=("untyped_global_median", "isolated_final_move"),
        challenger="isolated_final_move",
        tournament_id="strategy-single-move-shadow-v1",
        schema="jaggedthoughts-strategy-single-move-shadow-tournament-v1",
    )
    body = {
        **{
            key: value for key, value in checked.items()
            if key != "shadow_sha256"
        },
        "compiled_at": epoch,
        "settlements": settled_rows,
        "settlement_blocks": [blocks[key] for key in sorted(blocks)],
        "settled_forecast_count": len(settled_rows),
        "diagnostic_settlements": diagnostic_rows,
        "diagnostic_blocks": [
            diagnostic_blocks[key] for key in sorted(diagnostic_blocks)
        ],
        "diagnostic_settled_forecast_count": len(diagnostic_rows),
        "short_horizon_diagnostic": short_horizon_diagnostic,
        "tournament": path_tournament,
        "single_move_tournament": move_tournament,
        "status": (
            path_tournament["status"]
            if path_tournament["observed_settled_forecast_count"] else
            move_tournament["status"]
            if move_tournament["observed_settled_forecast_count"] else checked["status"]
        ),
        "next_activation": (
            "Review the frozen representation trial; no automatic grammar or capital change."
            if path_tournament["representation_credit"] else
            "Review the frozen single-move trial; no automatic grammar or capital change."
            if move_tournament["representation_credit"] else
            "Continue the 90-day return diagnostic and the separated 365-day operating and return trials."
            if checked.get("forecasts") else checked["next_activation"]
        ),
    }
    return {**body, "shadow_sha256": stable_sha256(body)}


def compile_workspace_strategy_path_shadow(
    workspace: str | Path, *, as_of: str | None = None,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    replay_root = root / "institutional_learning/historical_strategy_event_replay"
    representation = json.loads((replay_root / "representation-learning.json").read_text())
    replay = json.loads((replay_root / "latest.json").read_text())
    tournament = json.loads((replay_root / "security-walk-forward.json").read_text())
    corpus_path = root / "institutional_learning/historical_strategy_bulk_corpus/latest.json"
    corpus = json.loads(corpus_path.read_text())
    panel = json.loads((
        root / "institutional_learning/historical_strategy_bulk_outcomes/panel-readiness.json"
    ).read_text())
    diagnostics = json.loads((
        root / "institutional_learning/historical_strategy_bulk_outcomes/effect-diagnostics.json"
    ).read_text())
    operating_histories = {
        str(row["cik"]): row.get("annual_history") or ()
        for row in panel.get("history_status") or ()
    }
    destination = root / _ROOT / "latest.json"
    prior = json.loads(destination.read_text()) if destination.is_file() else None
    shadow = compile_strategy_path_shadow(
        representation, replay, tournament, corpus, _event_rows(root, corpus),
        _classification_rows(root), prior=prior, as_of=as_of,
        operating_histories=operating_histories,
        bulk_effect_diagnostics=diagnostics,
    )
    factors = tuple(
        FactorDefinition.from_dict(row)
        for row in shadow["frozen_trial"].get("factor_definitions") or ()
    )
    settled_ids = {
        str(row["forecast_sha256"]) for row in shadow.get("settlements") or ()
    }
    diagnostic_ids = {
        str(row["forecast_sha256"])
        for row in shadow.get("diagnostic_settlements") or ()
    }
    due = any(
        (
            str(row["forecast_sha256"]) not in settled_ids
            and timestamp_key(str(shadow["compiled_at"])) >= timestamp_key(
                str(row["settlement_contract"]["not_before"])
            )
        ) or (
            str(row["forecast_sha256"]) not in diagnostic_ids
            and timestamp_key(str(shadow["compiled_at"])) >= timestamp_key(str(
                row["settlement_contract"].get("diagnostic_not_before")
                or (
                    timestamp_key(str(row["issued_at"])) + timedelta(
                        days=int(shadow["frozen_trial"]["diagnostic_horizon_days"])
                    )
                ).isoformat(timespec="seconds").replace("+00:00", "Z")
            ))
        )
        for row in shadow.get("forecasts") or ()
    )
    points: tuple[PricePoint, ...] = ()
    source_run = json.loads((root / "data" / "latest_source_run.json").read_text())
    if due:
        entities = {
            str(row["entity_id"]) for row in shadow.get("forecasts") or ()
        } | {
            value for factor in factors
            for value in (factor.long_entity_id, factor.short_entity_id) if value
        }
        points = load_price_points(
            root / "data" / "observations.csv", as_of=str(source_run["as_of"]),
            metric_id="adjusted_price", entity_ids=entities,
        )
    return settle_strategy_path_shadow(
        shadow, points, factors, evidence_as_of=str(source_run["as_of"]),
        as_of=str(shadow["compiled_at"]),
    )


def acquire_workspace_strategy_path_shadow(
    workspace: str | Path, shadow: Mapping[str, Any], *, limit: int = 8,
) -> dict[str, Any]:
    """Hydrate and deterministically type the exact current shadow queue."""

    root = Path(workspace).expanduser().resolve()
    selected = list(shadow.get("acquisition_queue") or ())[:max(0, limit)]
    acquired, errors = [], []
    destination = root / "institutional_learning/historical_strategy_bulk_learning/classifications"
    destination.mkdir(parents=True, exist_ok=True)
    for event in selected:
        try:
            filing = fetch_sec_filing_document(
                root, source_id=f"sec_strategy_path_{event['cik']}_{str(event['accession_number'])[-6:]}",
                cik=str(event["cik"]), accession_number=str(event["accession_number"]),
                primary_document=str(event["primary_document"]),
                accepted_at=str(event["available_at"]),
            )
            classification = classify_sec_item_201(
                (root / str(filing["receipt"]["raw_path"])).read_bytes()
            )
            body = {
                "schema": "jaggedthoughts-historical-strategy-bulk-classification-v1",
                "event_sha256": event["event_sha256"],
                "accession_number": event["accession_number"], "cik": event["cik"],
                "filing_document_sha256": filing["filing_document_sha256"],
                "filing_source_receipt": filing["receipt"], **classification,
            }
            receipt = {**body, "classification_receipt_sha256": stable_sha256(body)}
            path = destination / f"{str(event['accession_number']).replace('-', '')}.json"
            temporary = path.with_name(f".{path.name}.tmp")
            temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            temporary.replace(path)
            acquired.append(receipt)
        except (OSError, TypeError, ValueError) as error:
            errors.append({
                "accession_number": event.get("accession_number"),
                "error": f"{type(error).__name__}: {error}"[:1_000],
            })
    body = {
        "schema": "jaggedthoughts-strategy-path-acquisition-v1", "executed_at": _now(),
        "trial_id": shadow.get("trial_id"), "selected_count": len(selected),
        "acquired_count": len(acquired), "error_count": len(errors),
        "acquired_classification_sha256s": [
            row["classification_receipt_sha256"] for row in acquired
        ],
        "ambiguous_accessions": [
            row["accession_number"] for row in acquired if row["classification"] == "ambiguous"
        ],
        "errors": errors, "capital_authority": False,
    }
    return {**body, "acquisition_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_PATH_SHADOW_SCHEMA", "acquire_workspace_strategy_path_shadow",
    "compile_strategy_path_shadow", "compile_workspace_strategy_path_shadow",
    "settle_strategy_path_shadow",
]
