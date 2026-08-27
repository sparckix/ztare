"""One trial census across investment search and model families.

Enumeration is useful only when the full search remains visible after a winner is
chosen.  This module records a trial family before its outcome boundary and
audits current workspace search surfaces against those immutable records.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.experiment_stats import bh_fdr
from ztare.worldmodel.evaluation import compile_evaluation_integrity_receipt

from .contracts import canonical_timestamp, require_refs, require_text, timestamp_key
from .closed_book import closed_book_status
from .golden_store import GoldenLeaf, GoldenStore
from .portfolio_policy import (
    _trial_family as _portfolio_policy_trial_family,
    portfolio_policy_status,
)


SEARCH_TRIAL_FAMILY_SCHEMA = "jaggedthoughts-search-trial-family-v1"
SEARCH_TRIAL_CENSUS_SCHEMA = "jaggedthoughts-search-trial-census-v1"
TRIAL_COUNT_SELECTION_GATE_SCHEMA = "jaggedthoughts-trial-count-selection-gate-v1"
_OBJECT_KIND = "search_trial_family"
_PURPOSES = {
    "alpha_evidence",
    "causal_law_evaluation",
    "model_falsification",
    "strategy_decision_search",
}


def _read(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return raw if isinstance(raw, dict) else None


def _store(root: Path) -> GoldenStore:
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    relative = Path(str((config or {}).get("golden_store") or "state/golden_store.sqlite3"))
    path = (root / relative).resolve()
    path.relative_to(root)
    return GoldenStore(path)


def compile_search_trial_family(
    *,
    owner: str,
    trial_family_id: str,
    research_question: str,
    purpose: str,
    model_family: str,
    selection_unit: str,
    candidate_ids: Iterable[str],
    declared_at: str,
    outcome_access_after: str,
    generator_receipts: Iterable[str],
    source_refs: Iterable[str],
) -> dict[str, Any]:
    """Compile an exact, immutable search family and its timing authority."""
    owner = require_text(owner, "trial family owner")
    family_id = require_text(trial_family_id, "trial_family_id")
    purpose = require_text(purpose, "trial family purpose")
    if purpose not in _PURPOSES:
        raise ValueError(f"unsupported trial family purpose: {purpose}")
    trials = tuple(sorted(require_text(value, "candidate id") for value in candidate_ids))
    if not trials or len(set(trials)) != len(trials):
        raise ValueError("candidate_ids must be a nonempty exact set")
    declared = canonical_timestamp(declared_at, "trial family declared_at")
    outcome_boundary = canonical_timestamp(
        outcome_access_after, "trial family outcome_access_after",
    )
    receipts = require_refs(generator_receipts, "trial generator receipt")
    refs = require_refs(source_refs, "trial family source ref")
    pre_outcome = timestamp_key(declared) < timestamp_key(outcome_boundary)
    body = {
        "schema": SEARCH_TRIAL_FAMILY_SCHEMA,
        "owner": owner,
        "trial_family_id": family_id,
        "research_question": require_text(research_question, "research question"),
        "purpose": purpose,
        "model_family": require_text(model_family, "model family"),
        "selection_unit": require_text(selection_unit, "selection unit"),
        "candidate_ids": list(trials),
        "trial_count": len(trials),
        "candidate_set_sha256": stable_sha256(list(trials)),
        "declared_at": declared,
        "outcome_access_after": outcome_boundary,
        "generator_receipts": list(receipts),
        "source_refs": list(refs),
        "commitment_status": (
            "pre_outcome_committed" if pre_outcome else "late_or_contemporaneous_census"
        ),
        "prospective_authority": pre_outcome,
        "capital_authority": False,
    }
    return {**body, "trial_family_sha256": stable_sha256(body)}


def register_search_trial_family(
    workspace: str | Path, family: Mapping[str, Any], *,
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Append one family to the workspace golden store; conflicting reuse fails."""
    root = Path(workspace).expanduser().resolve()
    payload = dict(family)
    digest = str(payload.pop("trial_family_sha256", ""))
    if payload.get("schema") != SEARCH_TRIAL_FAMILY_SCHEMA or stable_sha256(payload) != digest:
        raise ValueError("search trial family content hash mismatch")
    sealed = {**payload, "trial_family_sha256": digest}
    store = GoldenStore(store_path) if store_path is not None else _store(root)
    owner = str(sealed["owner"])
    family_id = str(sealed["trial_family_id"])
    try:
        prior = store.head(owner, _OBJECT_KIND, family_id)
    except KeyError:
        prior = None
    if prior:
        prior_payload = prior.get("payload") or {}
        if prior_payload.get("trial_family_sha256") != digest:
            raise ValueError(f"trial family identity already committed: {family_id}")
        return {"status": "already_registered", "golden_leaf": prior["leaf_sha256"], **sealed}
    leaf = GoldenLeaf(
        owner=owner,
        object_kind=_OBJECT_KIND,
        object_id=family_id,
        epoch=digest,
        occurred_at=str(sealed["declared_at"]),
        available_at=str(sealed["declared_at"]),
        payload=sealed,
        source_refs=tuple(sealed["source_refs"]),
    )
    store.append_leaf(leaf)
    return {"status": "registered", "golden_leaf": leaf.leaf_sha256, **sealed}


def register_prospective_search_surface(
    workspace: str | Path, *, owner: str, trial_family_id: str,
    research_question: str, model_family: str, selection_unit: str,
    candidate_ids: Iterable[str], declared_at: str, outcome_access_after: str,
    generator_receipts: Iterable[str], source_refs: Iterable[str],
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Register once at first use, then reuse the same exact candidate family."""
    root = Path(workspace).expanduser().resolve()
    candidates = tuple(sorted(require_text(value, "candidate id") for value in candidate_ids))
    family_id = require_text(trial_family_id, "trial_family_id")
    owner_id = require_text(owner, "trial family owner")
    store = GoldenStore(store_path) if store_path is not None else _store(root)
    try:
        prior = store.head(owner_id, _OBJECT_KIND, family_id)
    except KeyError:
        prior = None
    if prior:
        payload = prior.get("payload") or {}
        if (
            payload.get("purpose") == "alpha_evidence"
            and payload.get("model_family") == model_family
            and payload.get("candidate_set_sha256") == stable_sha256(candidates)
        ):
            return {"status": "already_registered", "golden_leaf": prior["leaf_sha256"], **payload}
        raise ValueError(f"trial family identity already committed: {family_id}")
    return register_search_trial_family(root, compile_search_trial_family(
        owner=owner_id, trial_family_id=family_id,
        research_question=research_question, purpose="alpha_evidence",
        model_family=model_family, selection_unit=selection_unit,
        candidate_ids=candidates, declared_at=declared_at,
        outcome_access_after=outcome_access_after,
        generator_receipts=generator_receipts, source_refs=source_refs,
    ), store_path=store_path)


def register_current_institutional_law_family(
    workspace: str | Path, state: Mapping[str, Any], *, owner: str,
) -> dict[str, Any]:
    """Commit the current law search while at least one outcome is still sealed."""
    pending_ends = sorted(
        canonical_timestamp(row["end_at"], "law episode end_at")
        for row in state.get("phenotype_episodes") or ()
        if row.get("settlement_status") != "settled" and row.get("end_at")
    )
    candidates = list(state.get("candidates") or ())
    if not pending_ends or not candidates:
        return {"status": "no_open_law_family", "capital_authority": False}
    family_id = f"institutional-strategy-laws:{state['input_sha256']}"
    candidate_ids = tuple(sorted(
        str(row.get("law_sha256") or row["law_key"]) for row in candidates
    ))
    try:
        prior = _store(Path(workspace).expanduser().resolve()).head(
            owner, _OBJECT_KIND, family_id,
        )
    except KeyError:
        prior = None
    if prior:
        payload = prior.get("payload") or {}
        if (
            payload.get("purpose") == "causal_law_evaluation"
            and payload.get("model_family") == "institutional_strategy_laws"
            and payload.get("candidate_set_sha256") == stable_sha256(candidate_ids)
        ):
            return {
                "status": "already_registered",
                "golden_leaf": prior["leaf_sha256"],
                **payload,
            }
        raise ValueError(f"trial family identity already committed: {family_id}")
    family = compile_search_trial_family(
        owner=owner,
        trial_family_id=family_id,
        research_question=(
            "Which declared investment and exact strategy-phenotype laws improve later "
            "outcomes across frozen cohorts after controls and multiplicity correction?"
        ),
        purpose="causal_law_evaluation",
        model_family="institutional_strategy_laws",
        selection_unit="law_candidate",
        candidate_ids=candidate_ids,
        declared_at=str(state["generated_at"]),
        outcome_access_after=pending_ends[0],
        generator_receipts=(
            f"institutional-learning-input:{state['input_sha256']}",
            f"institutional-learning-state:{state['state_sha256']}",
        ),
        source_refs=("institutional_learning/latest.json",),
    )
    return register_search_trial_family(workspace, family)


def _selection_gate_body(
    *, status: str, missing_inputs: Iterable[str], trial_count: int | None = None,
    **values: Any,
) -> dict[str, Any]:
    body = {
        "schema": TRIAL_COUNT_SELECTION_GATE_SCHEMA,
        "status": status,
        "method": "bonferroni_selected_economic_candidate_vs_declared_baseline",
        "trial_count": trial_count,
        "missing_inputs": sorted(set(missing_inputs)),
        "selection_adjusted_candidate_evidence": False,
        "alpha_claim_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
        "uncomputed_methods": {
            "deflated_sharpe_ratio": {
                "status": "not_computed",
                "required_inputs_not_carried_by_this_gate": [
                    "per_period_excess_returns_for_every_trial",
                    "selected_return_skewness_and_excess_kurtosis",
                    "effective_independent_trial_count",
                ],
            },
            "probability_of_backtest_overfitting": {
                "status": "not_computed",
                "required_inputs_not_carried_by_this_gate": [
                    "aligned_trial_by_period_return_matrix",
                    "predeclared_combinatorial_partition_scheme",
                    "sufficient_independent_period_blocks",
                ],
            },
        },
        "use_boundary": (
            "This is a conservative family-wise screen for a selected economic winner. "
            "Passing it does not establish persistent alpha or authorize a portfolio action."
        ),
        **values,
    }
    return {**body, "selection_gate_sha256": stable_sha256(body)}


def compile_institutional_law_selection_gate(
    *, family: Mapping[str, Any] | None, learning: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Settle one frozen law family without dropping unfinished trials."""

    if not family or not learning:
        return _selection_gate_body(
            status="unavailable",
            missing_inputs=(
                "pre_outcome_exact_trial_family" if not family else "settled_law_compilation",
            ),
            method="benjamini_hochberg_over_frozen_law_family",
        )
    candidate_ids = tuple(sorted(str(value) for value in family.get("candidate_ids") or ()))
    observed_ids = tuple(sorted(
        str(row.get("law_sha256") or "")
        for row in learning.get("candidates") or () if row.get("law_sha256")
    ))
    missing = []
    if (
        family.get("schema") != SEARCH_TRIAL_FAMILY_SCHEMA
        or family.get("purpose") != "causal_law_evaluation"
        or family.get("model_family") != "institutional_strategy_laws"
        or not family.get("prospective_authority")
    ):
        missing.append("valid_pre_outcome_law_family")
    if candidate_ids != observed_ids:
        missing.append("exact_trial_family_candidate_set_match")
    try:
        boundary_reached = timestamp_key(canonical_timestamp(
            learning.get("generated_at"), "law compilation generated_at",
        )) >= timestamp_key(canonical_timestamp(
            family.get("outcome_access_after"), "law family outcome boundary",
        ))
    except (TypeError, ValueError):
        boundary_reached = False
    if not boundary_reached:
        missing.append("trial_family_outcome_boundary_reached")
    if missing:
        return _selection_gate_body(
            status="unavailable", missing_inputs=missing,
            trial_count=len(candidate_ids) or None,
            method="benjamini_hochberg_over_frozen_law_family",
            trial_family_id=family.get("trial_family_id"),
            outcome_access_after=family.get("outcome_access_after"),
            generated_at=learning.get("generated_at"),
            eligible_law_ids=[],
        )

    evaluations = {
        str(row.get("law_sha256")): row
        for row in learning.get("evaluations") or () if row.get("law_sha256")
    }
    raw_rows = []
    for law_sha in candidate_ids:
        evaluation = evaluations.get(law_sha) or {}
        p_values = [
            float(row["pooled_two_sided_p_value"])
            for row in evaluation.get("environment_evaluations") or ()
            if row.get("pooled_two_sided_p_value") is not None
        ]
        # One frozen trial is one law. Multiple declared environments are an
        # internal search, so collapse them conservatively before family BH.
        omnibus_p = min(1.0, min(p_values) * len(p_values)) if p_values else 1.0
        raw_rows.append({
            "law_sha256": law_sha,
            "law_key": evaluation.get("law_key"),
            "evaluation_status": evaluation.get("status") or "awaiting_evaluation",
            "within_law_test_count": len(p_values),
            "omnibus_p_value": omnibus_p,
            "base_promotion_eligible": bool(evaluation.get("promotion_eligible")),
        })
    adjusted = {
        row["label"]: row for row in bh_fdr(
            ((row["law_sha256"], row["omnibus_p_value"]) for row in raw_rows),
            alpha=0.05,
        )
    }
    rows = [{**row, "family_bh": adjusted[row["law_sha256"]]} for row in raw_rows]
    eligible = [
        row["law_sha256"] for row in rows
        if row["base_promotion_eligible"] and row["family_bh"]["rejected_at_alpha"]
    ]
    return _selection_gate_body(
        status="passes_familywise_screen" if eligible else "fails_familywise_screen",
        missing_inputs=(), trial_count=len(candidate_ids),
        method="benjamini_hochberg_over_frozen_law_family",
        trial_family_id=family.get("trial_family_id"),
        outcome_access_after=family.get("outcome_access_after"),
        generated_at=learning.get("generated_at"),
        law_rows=rows, eligible_law_ids=eligible,
        unresolved_law_count=sum(not row["within_law_test_count"] for row in rows),
        selection_adjusted_candidate_evidence=bool(eligible),
        alpha_claim_eligible=bool(eligible),
        use_boundary=(
            "Passing permits paper learning-policy review only. It does not establish persistent "
            "alpha, change a security screen, size a position, or authorize capital."
        ),
    )


def compile_trial_count_selection_gate(
    *, family: Mapping[str, Any] | None, tournament: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Adjust a selected tournament winner against its full committed trial count.

    Bonferroni is deliberately used here: it is valid under arbitrary dependence
    and needs only the complete family count plus the tournament's existing paired
    block-permutation p-value. Richer backtest-overfitting methods remain typed as
    unavailable until their return-matrix inputs are carried by the contract.
    """
    missing = []
    if not family:
        missing.append("pre_outcome_exact_trial_family")
    if not tournament:
        missing.append("settled_tournament_result")
    if missing:
        return _selection_gate_body(status="unavailable", missing_inputs=missing)

    assert family is not None and tournament is not None
    candidates = tuple(sorted(str(row) for row in family.get("candidate_ids") or ()))
    trial_count = family.get("trial_count")
    if (
        family.get("schema") != SEARCH_TRIAL_FAMILY_SCHEMA
        or family.get("purpose") != "alpha_evidence"
        or family.get("model_family") != "world_model_tournament"
        or not isinstance(trial_count, int)
        or trial_count < 2
        or len(candidates) != trial_count
        or len(set(candidates)) != trial_count
    ):
        missing.append("valid_exact_alpha_trial_family")
    tracks = tuple(
        row for row in tournament.get("model_tracks") or () if isinstance(row, Mapping)
    )
    observed = tuple(sorted(
        str((row.get("model") or {}).get("model_sha256") or "")
        for row in tracks if (row.get("model") or {}).get("model_sha256")
    ))
    if candidates != observed:
        missing.append("exact_trial_family_candidate_set_match")
    if not family.get("prospective_authority"):
        missing.append("pre_outcome_family_commitment")
    as_of = tournament.get("as_of")
    outcome_boundary = family.get("outcome_access_after")
    try:
        boundary_reached = timestamp_key(canonical_timestamp(str(as_of), "tournament as_of")) >= timestamp_key(
            canonical_timestamp(str(outcome_boundary), "trial family outcome boundary")
        )
    except (TypeError, ValueError):
        boundary_reached = False
    if not boundary_reached:
        missing.append("trial_family_outcome_boundary_reached")
    integrity = tournament.get("evaluation_integrity") or {}
    if not isinstance(integrity, Mapping) or not integrity.get("alpha_evidence_eligible"):
        missing.append("eligible_point_in_time_or_matured_prospective_evaluation")
    matrix = tournament.get("evaluation_matrix") or {}
    if not isinstance(matrix, Mapping):
        matrix = {}
    track_model_ids = tuple(sorted(
        str((row.get("model") or {}).get("model_id") or "") for row in tracks
        if (row.get("model") or {}).get("model_id")
    ))
    matrix_models = tuple(sorted(str(value) for value in matrix.get("model_ids") or ()))
    matrix_episodes = tuple(str(value) for value in matrix.get("episode_ids") or ())
    matrix_forecasts = tuple(str(value) for value in matrix.get("forecast_sha256s") or ())
    if (
        not matrix.get("complete_matrix") or not matrix_episodes
        or matrix_models != track_model_ids
        or len(matrix_forecasts) != len(matrix_models) * len(matrix_episodes)
    ):
        missing.append("complete_candidate_by_episode_matrix")
    try:
        costs = float(tournament["transaction_cost_bps"])
    except (KeyError, TypeError, ValueError):
        costs = float("nan")
    if not math.isfinite(costs) or costs < 0:
        missing.append("declared_nonnegative_transaction_costs")
    try:
        minimum_blocks = int(tournament["min_inference_blocks"])
        observed_blocks = int(tournament["inference_block_count"])
    except (KeyError, TypeError, ValueError):
        minimum_blocks, observed_blocks = 0, 0
    if (
        minimum_blocks < 5 or observed_blocks < minimum_blocks
        or not tournament.get("inference_sufficient")
    ):
        missing.append("minimum_independent_inference_blocks")
    baseline = str(tournament.get("baseline_model_id") or "")
    metrics = {
        str(row.get("model_id") or ""): (row.get("net_excess_return") or {}).get("mean")
        for row in tournament.get("model_metrics") or () if isinstance(row, Mapping)
    }
    if set(metrics) != set(track_model_ids):
        missing.append("complete_candidate_metric_set")
    if not baseline or baseline not in metrics:
        missing.append("declared_baseline_metric")
    alternatives = []
    for model_id, value in metrics.items():
        if model_id == baseline:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric == numeric and numeric not in {float("inf"), float("-inf")}:
            alternatives.append((model_id, numeric))
    if not alternatives:
        missing.append("finite_alternative_economic_metrics")
    try:
        alpha = float(tournament["alpha"])
    except (KeyError, TypeError, ValueError):
        alpha = float("nan")
    if not 0 < alpha < 1:
        missing.append("valid_declared_alpha")
    if missing:
        return _selection_gate_body(
            status="unavailable", missing_inputs=missing,
            trial_count=trial_count if isinstance(trial_count, int) else None,
        )

    selected_id, selected_return = sorted(
        alternatives, key=lambda row: (-row[1], row[0]),
    )[0]
    baseline_return = float(metrics[baseline])
    comparison = next((
        row for row in tournament.get("paired_comparisons") or ()
        if isinstance(row, Mapping)
        and row.get("dimension") == "economic_loss"
        and {str(row.get("left_model_id")), str(row.get("right_model_id"))}
        == {baseline, selected_id}
    ), None)
    if comparison is None:
        return _selection_gate_body(
            status="unavailable", missing_inputs=("paired_block_permutation_p_value",),
            trial_count=trial_count, selected_candidate_id=selected_id,
            baseline_model_id=baseline,
        )
    try:
        raw_p = float(comparison["p_value"])
        delta = float(comparison["observed_delta"])
        paired_blocks = int(comparison["n_paired"])
    except (KeyError, TypeError, ValueError):
        return _selection_gate_body(
            status="unavailable", missing_inputs=("valid_paired_block_permutation_result",),
            trial_count=trial_count, selected_candidate_id=selected_id,
            baseline_model_id=baseline,
        )
    if (
        not 0 <= raw_p <= 1 or not math.isfinite(delta)
        or paired_blocks < minimum_blocks
    ):
        return _selection_gate_body(
            status="unavailable", missing_inputs=("valid_paired_block_permutation_result",),
            trial_count=trial_count, selected_candidate_id=selected_id,
            baseline_model_id=baseline,
        )
    selected_on_left = str(comparison.get("left_model_id")) == selected_id
    direction_favors_selected = delta < 0 if selected_on_left else delta > 0
    adjusted_p = min(1.0, raw_p * trial_count)
    passes = (
        selected_return > baseline_return
        and direction_favors_selected
        and adjusted_p <= alpha
    )
    return _selection_gate_body(
        status="passes_familywise_screen" if passes else "fails_familywise_screen",
        missing_inputs=(), trial_count=trial_count,
        selection_adjusted_candidate_evidence=passes,
        selected_candidate_id=selected_id, baseline_model_id=baseline,
        selected_mean_net_excess_return=selected_return,
        baseline_mean_net_excess_return=baseline_return,
        raw_two_sided_block_permutation_p_value=raw_p,
        familywise_adjusted_p_value=adjusted_p,
        familywise_alpha=alpha,
        direction_favors_selected=direction_favors_selected,
        paired_inference_block_count=paired_blocks,
        transaction_cost_bps=costs,
        evaluation_matrix_sha256=matrix.get("matrix_sha256"),
    )


def compile_closed_book_trial_count_selection_gate(
    *, family: Mapping[str, Any] | None, tournament: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Apply the shared selected-winner gate to one matured closed-book cohort."""
    if not family or not tournament:
        return _selection_gate_body(
            status="unavailable",
            missing_inputs=(
                "pre_outcome_exact_trial_family" if not family else "settled_closed_book_tournament",
            ),
            trial_count=(int(family["trial_count"]) if family else None),
        )
    integrity = tournament.get("evaluation_integrity") or {}
    missing = []
    if family.get("model_family") != "closed_book_world_models":
        missing.append("exact_closed_book_search_trial_family")
    if (
        tournament.get("mode") != "prospective_shadow"
        or integrity.get("evidence_authority") != "matured_prospective_evidence"
    ):
        missing.append("matured_prospective_temporal_receipt")
    if missing:
        return _selection_gate_body(
            status="unavailable", missing_inputs=missing,
            trial_count=int(family.get("trial_count") or 0) or None,
        )
    normalized_tracks = []
    for track in tournament.get("model_tracks") or ():
        if not isinstance(track, Mapping):
            continue
        model = dict(track.get("model") or {})
        model["model_sha256"] = str(model.get("trial_family_id") or "")
        normalized_tracks.append({**dict(track), "model": model})
    normalized_family = {**dict(family), "model_family": "world_model_tournament"}
    result = compile_trial_count_selection_gate(
        family=normalized_family,
        tournament={**dict(tournament), "model_tracks": normalized_tracks},
    )
    body = {
        **{key: value for key, value in result.items() if key != "selection_gate_sha256"},
        "settlement_adapter": "closed_book_world_model_tournament",
        "registered_model_family": "closed_book_world_models",
    }
    return {**body, "selection_gate_sha256": stable_sha256(body)}


def compile_portfolio_policy_trial_count_selection_gate(
    *, family: Mapping[str, Any] | None, review: Mapping[str, Any] | None,
    runs: Iterable[Mapping[str, Any]], settlements: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Screen one settled complete-policy family using its existing paired review."""
    trial_count = (family or {}).get("trial_count")
    if not family or not review:
        return _selection_gate_body(
            status="unavailable",
            missing_inputs=(
                "pre_outcome_exact_trial_family" if not family
                else "settled_complete_policy_review",
            ),
            trial_count=trial_count if isinstance(trial_count, int) else None,
        )
    assert family is not None and review is not None
    missing = []
    candidates = tuple(sorted(str(value) for value in family.get("candidate_ids") or ()))
    policy_ids = tuple(sorted(value.rsplit("@", 1)[0] for value in candidates))
    if (
        family.get("model_family") != "portfolio_policy"
        or len(set(policy_ids)) != len(policy_ids)
        or str((review.get("trial_family") or {}).get("trial_family_id") or "")
        != str(family.get("trial_family_id") or "")
    ):
        missing.append("exact_registered_policy_family_match")
    run_by_id = {str(row.get("run_id") or ""): dict(row) for row in runs if row.get("run_id")}
    settlement_by_run = {
        str(row.get("run_id") or ""): dict(row) for row in settlements if row.get("run_id")
    }
    run_ids = tuple(str(value) for value in review.get("run_ids") or ())
    pairs = [
        (run_by_id.get(run_id), settlement_by_run.get(run_id)) for run_id in run_ids
    ]
    if (
        not run_ids or len(set(run_ids)) != len(run_ids)
        or any(run is None or settlement is None for run, settlement in pairs)
    ):
        missing.append("complete_settled_policy_episode_set")
    blocks = set()
    seal_rows = []
    maturity_rows = []
    score_blocks: dict[str, dict[str, list[float]]] = {}
    forecast_receipts = []
    costs_seen = set()
    for run, settlement in pairs:
        if run is None or settlement is None:
            continue
        run_candidates = tuple(sorted(
            f"{row['policy_id']}@{row.get('version') or '1'}"
            for row in run.get("policies") or () if row.get("policy_id")
        ))
        if str((run.get("trial_family") or {}).get("trial_family_id") or "") != str(
            family.get("trial_family_id") or ""
        ) or str(settlement.get("trial_family_id") or "") != str(
            family.get("trial_family_id") or ""
        ):
            missing.append("exact_registered_policy_family_match")
        score_rows = tuple(settlement.get("policy_scores") or ())
        scores = {
            str(row.get("policy_id") or ""): row
            for row in score_rows if row.get("policy_id")
        }
        if (
            run_candidates != candidates or tuple(sorted(scores)) != policy_ids
            or len(score_rows) != len(policy_ids)
        ):
            missing.append("complete_exact_policy_by_episode_matrix")
        block_id = str(settlement.get("inference_block_id") or "")
        if not block_id:
            missing.append("paired_inference_block_identity")
        else:
            blocks.add(block_id)
        try:
            cost_bps = float((run.get("settlement_contract") or {})["transaction_cost_bps"])
        except (KeyError, TypeError, ValueError):
            cost_bps = float("nan")
        if not math.isfinite(cost_bps) or cost_bps < 0:
            missing.append("declared_nonnegative_transaction_costs")
        else:
            costs_seen.add(cost_bps)
        for policy_id, score in scores.items():
            try:
                value = float(score["portfolio_excess_return_after_cost"])
                charged = float(score["transaction_cost"])
            except (KeyError, TypeError, ValueError):
                missing.append("finite_after_cost_policy_scores")
                continue
            if not math.isfinite(value) or not math.isfinite(charged) or charged < 0:
                missing.append("finite_after_cost_policy_scores")
                continue
            score_blocks.setdefault(policy_id, {}).setdefault(block_id, []).append(value)
            forecast_receipts.append(stable_sha256({
                "run_id": run["run_id"], "policy_id": policy_id,
                "policy_sha256": score.get("policy_sha256"),
            }))
            seal_rows.append({
                "episode_id": f"{run['run_id']}:{policy_id}",
                "sealed_at": str(run.get("opened_at") or ""),
                "episode_start_at": str(run.get("opened_at") or ""),
            })
        available = [
            str((row or {}).get("available_at") or "")
            for row in (settlement.get("end_prices") or {}).values()
        ]
        if available and all(available):
            maturity_rows.append({
                "episode_id": str(run["run_id"]), "episode_end_at": str(run["end_at"]),
                "outcome_available_at": max(available),
                "evaluated_at": str(settlement.get("evaluated_at") or ""),
            })
        else:
            missing.append("outcome_availability_receipt")
    if len(costs_seen) != 1:
        missing.append("common_declared_transaction_costs")
    try:
        integrity = compile_evaluation_integrity_receipt(
            temporal_design="prospective_sealed", generation_processes=("deterministic",),
            seal_rows=seal_rows, maturity_rows=maturity_rows,
        )
    except (TypeError, ValueError):
        integrity = {}
    if integrity.get("evidence_authority") != "matured_prospective_evidence":
        missing.append("matured_prospective_temporal_receipt")
    survivor = review.get("survivor_set") or {}
    means = {
        policy_id: sum(sum(values) / len(values) for values in by_block.values()) / len(by_block)
        for policy_id, by_block in score_blocks.items() if by_block
    }
    if set(means) != set(policy_ids):
        missing.append("complete_candidate_metric_set")
    if "equal_weight_qualified" not in means:
        missing.append("declared_equal_weight_baseline")
    if missing:
        return _selection_gate_body(
            status="unavailable", missing_inputs=missing, trial_count=trial_count,
            evaluation_integrity=integrity or None,
        )
    version_by_id = {value.rsplit("@", 1)[0]: value for value in candidates}
    tracks = [{"model": {
        "model_id": policy_id, "model_sha256": version_by_id[policy_id],
    }} for policy_id in policy_ids]
    normalized = {
        "as_of": max(str(settlement["evaluated_at"]) for _run, settlement in pairs),
        "alpha": survivor.get("alpha"),
        "baseline_model_id": "equal_weight_qualified",
        "evaluation_integrity": integrity,
        "evaluation_matrix": {
            "complete_matrix": True, "model_ids": list(policy_ids),
            "episode_ids": list(run_ids), "forecast_sha256s": forecast_receipts,
            "matrix_sha256": stable_sha256(forecast_receipts),
        },
        "model_tracks": tracks,
        "model_metrics": [{
            "model_id": policy_id, "net_excess_return": {"mean": means[policy_id]},
        } for policy_id in policy_ids],
        "paired_comparisons": [
            {**dict(row), "dimension": "economic_loss"}
            for row in survivor.get("paired_comparisons") or ()
            if row.get("dimension") == "negative_portfolio_excess_return_after_cost"
        ],
        "transaction_cost_bps": next(iter(costs_seen)),
        "min_inference_blocks": survivor.get("min_inference_blocks"),
        "inference_block_count": len(blocks),
        "inference_sufficient": survivor.get("inference_sufficient"),
    }
    result = compile_trial_count_selection_gate(
        family={**dict(family), "model_family": "world_model_tournament"},
        tournament=normalized,
    )
    body = {
        **{key: value for key, value in result.items() if key != "selection_gate_sha256"},
        "settlement_adapter": "complete_portfolio_policy_review",
        "registered_model_family": "portfolio_policy",
        "evaluation_integrity": integrity,
    }
    return {**body, "selection_gate_sha256": stable_sha256(body)}


def _observed_surfaces(root: Path) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for path in sorted((root / "tournaments" / "results").glob("*.json")):
        row = _read(path)
        if not row:
            continue
        candidates = [
            str((track.get("model") or {}).get("model_sha256") or "")
            for track in row.get("model_tracks") or ()
        ]
        candidates = sorted(value for value in candidates if value)
        surfaces.append({
            "surface_id": f"tournament:{row.get('tournament_id')}",
            "purpose": "alpha_evidence",
            "model_family": "world_model_tournament",
            "observed_candidate_count": len(candidates),
            "observed_candidate_set_sha256": stable_sha256(candidates),
            "declared_family_ids": list(row.get("declared_trial_family_ids") or ()),
            "artifact_path": path.relative_to(root).as_posix(),
        })
    closed_book_groups: dict[tuple[int, tuple[str, ...]], list[tuple[Path, dict[str, Any]]]] = {}
    for path in sorted((root / "closed_book" / "runs").glob("*.json")):
        row = _read(path)
        if not row:
            continue
        candidates = tuple(sorted({
            str(candidate.get("trial_family_id") or "")
            for candidate in row.get("candidate_forecasts") or ()
            if isinstance(candidate, Mapping) and candidate.get("trial_family_id")
        }))
        if candidates:
            closed_book_groups.setdefault(
                (int(row.get("horizon_days") or 0), candidates), [],
            ).append((path, row))
    for (horizon_days, candidates), rows in sorted(closed_book_groups.items()):
        candidate_hash = stable_sha256(list(candidates))
        shared_family_ids = sorted({
            str(row.get("search_trial_family_id") or "")
            for _, row in rows if row.get("search_trial_family_id")
        })
        surfaces.append({
            "surface_id": f"closed-book:{horizon_days}d:{candidate_hash}",
            "purpose": "alpha_evidence",
            "model_family": "closed_book_world_models",
            "observed_candidate_count": len(candidates),
            "observed_candidate_set_sha256": candidate_hash,
            "observed_episode_count": len(rows),
            "pending_episode_count": sum(
                str(row.get("status")) == "pending_outcome" for _, row in rows
            ),
            "declared_candidate_trial_family_ids": list(candidates),
            "declared_family_ids": shared_family_ids,
            "registration_gap": (
                None if shared_family_ids else "shared_search_trial_family_not_registered"
            ),
            "first_declared_at": min(str(row.get("opened_at") or "") for _, row in rows),
            "first_outcome_access_after": min(str(row.get("end_at") or "") for _, row in rows),
            "artifact_path": "closed_book/runs/",
        })
    policy_groups: dict[str, list[tuple[Path, dict[str, Any], dict[str, Any]]]] = {}
    for path in sorted((root / "portfolio_policy" / "runs").glob("*.json")):
        row = _read(path)
        if not row:
            continue
        family = dict(row.get("trial_family") or _portfolio_policy_trial_family(row))
        family_id = str(family.get("trial_family_id") or "")
        if family_id:
            policy_groups.setdefault(family_id, []).append((path, row, family))
    for family_id, rows in sorted(policy_groups.items()):
        representative_ids = tuple(sorted({
            f"{policy.get('policy_id')}@{policy.get('version') or '1'}"
            for _, row, _ in rows for policy in row.get("policies") or ()
            if isinstance(policy, Mapping) and policy.get("policy_id")
        }))
        surfaces.append({
            "surface_id": f"portfolio-policy:{family_id}",
            "purpose": "alpha_evidence",
            "model_family": "portfolio_policy",
            "observed_candidate_count": len(representative_ids),
            "observed_candidate_set_sha256": stable_sha256(list(representative_ids)),
            "observed_episode_count": len(rows),
            "pending_episode_count": sum(
                str(row.get("status")) == "pending_outcome" for _, row, _ in rows
            ),
            "equivalent_alias_count": sum(
                len(row.get("equivalent_policies") or ()) for _, row, _ in rows
            ),
            "declared_family_ids": [family_id],
            "first_declared_at": min(str(row.get("opened_at") or "") for _, row, _ in rows),
            "first_outcome_access_after": min(str(row.get("end_at") or "") for _, row, _ in rows),
            "artifact_path": rows[0][0].relative_to(root).as_posix(),
        })
    for path in sorted((root / "experiments" / "results").glob("*.json")):
        row = _read(path)
        if not row or not row.get("experiment_id"):
            continue
        model_ids = [
            str(value.get("model_id") or "")
            for value in row.get("model_metrics") or () if isinstance(value, Mapping)
        ]
        model_ids = sorted(value for value in model_ids if value) or [
            str(row.get("profile_sha256") or row.get("experiment_id"))
        ]
        surfaces.append({
            "surface_id": f"experiment:{row['experiment_id']}",
            "purpose": "model_falsification",
            "model_family": str(row.get("implementation_id") or row.get("schema") or "experiment"),
            "observed_candidate_count": len(model_ids),
            "observed_candidate_set_sha256": stable_sha256(model_ids),
            "declared_family_ids": [],
            "artifact_path": path.relative_to(root).as_posix(),
        })
    learning = _read(root / "institutional_learning" / "latest.json")
    if learning and learning.get("candidates"):
        law_ids = sorted(
            str(row.get("law_sha256") or row.get("law_key"))
            for row in learning["candidates"]
        )
        surfaces.append({
            "surface_id": f"law-compilation:{learning.get('input_sha256') or learning.get('state_sha256')}",
            "purpose": "causal_law_evaluation",
            "model_family": "institutional_strategy_laws",
            "observed_candidate_count": len(law_ids),
            "observed_candidate_set_sha256": stable_sha256(law_ids),
            "declared_family_ids": [],
            "artifact_path": "institutional_learning/latest.json",
        })
    frontier = _read(root / "strategy_frontiers" / "latest.json")
    if frontier and (frontier.get("enumeration") or {}).get("program_count"):
        enumeration = frontier["enumeration"]
        program_ids = sorted(str(row["program_id"]) for row in frontier.get("programs") or ())
        surfaces.append({
            "surface_id": f"strategy-frontier:{enumeration.get('enumeration_digest')}",
            "purpose": "strategy_decision_search",
            "model_family": "recursive_strategy_grammar",
            "observed_candidate_count": int(enumeration["program_count"]),
            "observed_candidate_set_sha256": stable_sha256(program_ids),
            "declared_family_ids": [],
            "artifact_path": "strategy_frontiers/latest.json",
        })
    return surfaces


def compile_workspace_search_trial_census(workspace: str | Path) -> dict[str, Any]:
    """Audit observed search breadth against pre-outcome golden-store commitments."""
    root = Path(workspace).expanduser().resolve()
    store = _store(root)
    families = []
    for metadata in store.list_leaves(object_kind=_OBJECT_KIND, limit=10_000):
        payload = store.get_leaf(str(metadata["leaf_sha256"])).get("payload") or {}
        if payload.get("schema") == SEARCH_TRIAL_FAMILY_SCHEMA:
            families.append(dict(payload))
    registered = {str(row["trial_family_id"]): row for row in families}
    surfaces = _observed_surfaces(root)
    closed_book_projection = closed_book_status(root).get("world_model_tournament")
    policy_projection = portfolio_policy_status(root)
    policy_reviews = {
        str((row.get("trial_family") or {}).get("trial_family_id") or ""): row
        for row in (policy_projection.get("scoreboard") or {}).get("policy_reviews") or ()
    }
    policy_runs = tuple(
        row for path in sorted((root / "portfolio_policy" / "runs").glob("*.json"))
        if (row := _read(path))
    )
    policy_settlements = tuple(
        row for path in sorted((root / "portfolio_policy" / "settlements").glob("*.json"))
        if (row := _read(path))
    )
    for surface in surfaces:
        declared = set(map(str, surface.get("declared_family_ids") or ()))
        exact = {
            family_id for family_id, family in registered.items()
            if family.get("purpose") == surface.get("purpose")
            and family.get("model_family") == surface.get("model_family")
            and family.get("candidate_set_sha256")
            == surface.get("observed_candidate_set_sha256")
        }
        matched = (declared & registered.keys()) | exact
        surface["registered_family_ids"] = sorted(matched)
        surface["registry_covered"] = bool(matched) and (
            not declared or declared <= registered.keys()
        )
        surface["evidence_use"] = (
            "multiplicity_eligible_after_settlement"
            if surface["registry_covered"]
            and all(registered[value]["prospective_authority"] for value in matched)
            else "diagnostic_or_search_only"
        )
        if surface["purpose"] != "strategy_decision_search":
            exact_families = [
                registered[family_id] for family_id in sorted(matched)
                if registered[family_id].get("purpose") == surface.get("purpose")
                and registered[family_id].get("model_family") == surface.get("model_family")
                and registered[family_id].get("candidate_set_sha256")
                == surface.get("observed_candidate_set_sha256")
            ]
            if surface["model_family"] == "world_model_tournament":
                surface["trial_count_selection_gate"] = compile_trial_count_selection_gate(
                    family=exact_families[0] if exact_families else None,
                    tournament=_read(root / str(surface["artifact_path"])),
                )
            elif surface["model_family"] == "closed_book_world_models":
                tournament = closed_book_projection
                cohort = (tournament or {}).get("cohort") or {}
                cohort_trials = tuple(sorted(
                    str((track.get("model") or {}).get("trial_family_id") or "")
                    for track in (tournament or {}).get("model_tracks") or ()
                    if (track.get("model") or {}).get("trial_family_id")
                ))
                if (
                    not exact_families
                    or int(cohort.get("horizon_days") or 0)
                    != int(str(surface["surface_id"]).split(":", 2)[1][:-1])
                    or stable_sha256(list(cohort_trials))
                    != surface.get("observed_candidate_set_sha256")
                ):
                    tournament = None
                surface["trial_count_selection_gate"] = (
                    compile_closed_book_trial_count_selection_gate(
                        family=exact_families[0] if exact_families else None,
                        tournament=tournament,
                    )
                )
            elif surface["model_family"] == "portfolio_policy":
                family = exact_families[0] if exact_families else None
                family_id = str((family or {}).get("trial_family_id") or "")
                surface["trial_count_selection_gate"] = (
                    compile_portfolio_policy_trial_count_selection_gate(
                        family=family, review=policy_reviews.get(family_id),
                        runs=policy_runs, settlements=policy_settlements,
                    )
                )
            elif surface["model_family"] == "institutional_strategy_laws":
                family = min(
                    exact_families,
                    key=lambda row: (str(row.get("declared_at") or ""), str(row.get("trial_family_id") or "")),
                ) if exact_families else None
                surface["trial_count_selection_gate"] = compile_institutional_law_selection_gate(
                    family=family, learning=_read(root / str(surface["artifact_path"])),
                )
            else:
                adapter_missing = ["settled_family_evaluation_adapter"]
                if not exact_families:
                    adapter_missing.append("pre_outcome_exact_trial_family")
                surface["trial_count_selection_gate"] = _selection_gate_body(
                    status="unavailable",
                    missing_inputs=adapter_missing,
                    trial_count=(
                        int(exact_families[0]["trial_count"]) if exact_families else None
                    ),
                )
    empirical = [row for row in surfaces if row["purpose"] != "strategy_decision_search"]
    uncovered = [row for row in empirical if not row["registry_covered"]]
    selection_gates = [row["trial_count_selection_gate"] for row in empirical]
    body = {
        "schema": SEARCH_TRIAL_CENSUS_SCHEMA,
        "registered_family_count": len(families),
        "pre_outcome_family_count": sum(bool(row["prospective_authority"]) for row in families),
        "registered_trial_count": sum(int(row["trial_count"]) for row in families),
        "observed_search_surface_count": len(surfaces),
        "observed_candidate_count": sum(int(row["observed_candidate_count"]) for row in surfaces),
        "prospective_trial_episode_count": sum(
            int(row.get("observed_episode_count") or 0) for row in surfaces
            if row["model_family"] in {"closed_book_world_models", "portfolio_policy"}
        ),
        "pending_prospective_trial_episode_count": sum(
            int(row.get("pending_episode_count") or 0) for row in surfaces
            if row["model_family"] in {"closed_book_world_models", "portfolio_policy"}
        ),
        "uncovered_empirical_surface_count": len(uncovered),
        "selection_gate_available_count": sum(
            row["status"] != "unavailable" for row in selection_gates
        ),
        "selection_gate_pass_count": sum(
            row["status"] == "passes_familywise_screen" for row in selection_gates
        ),
        "census_complete": not uncovered,
        "families": sorted(families, key=lambda row: str(row["trial_family_id"])),
        "search_surfaces": surfaces,
        "alpha_claim_eligible": False,
        "capital_authority": False,
        "next_activation": (
            "Register every empirical search family before its first outcome boundary."
            if uncovered else
            "Settle registered families prospectively and apply the declared multiplicity method."
        ),
        "use_boundary": (
            "A complete census prevents selected-winner reporting. It does not establish alpha; "
            "the registered family must still settle prospectively against controls and costs."
        ),
    }
    return {**body, "census_sha256": stable_sha256(body)}


__all__ = [
    "SEARCH_TRIAL_CENSUS_SCHEMA",
    "SEARCH_TRIAL_FAMILY_SCHEMA",
    "TRIAL_COUNT_SELECTION_GATE_SCHEMA",
    "compile_institutional_law_selection_gate",
    "compile_search_trial_family",
    "compile_closed_book_trial_count_selection_gate",
    "compile_portfolio_policy_trial_count_selection_gate",
    "compile_trial_count_selection_gate",
    "compile_workspace_search_trial_census",
    "register_current_institutional_law_family",
    "register_prospective_search_surface",
    "register_search_trial_family",
]
