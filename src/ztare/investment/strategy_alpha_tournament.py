"""Nested point-in-time ablation for strategy-derived investment forecasts."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import (
    canonical_timestamp,
    require_finite,
    require_refs,
    require_text,
    timestamp_key,
)
from .closed_book import overlap_cluster_ids
from .strategy_dual_outcome import compile_strategy_security_outcome
from .tournament import (
    BacktestEpisode,
    ObservableSpec,
    WorldModelCandidate,
    WorldModelForecast,
    evaluate_world_model_tournament,
)


STRATEGY_ALPHA_TOURNAMENT_SCHEMA = "jaggedthoughts-strategy-alpha-tournament-v1"
STRATEGY_ALPHA_BINDING_SCHEMA = "jaggedthoughts-strategy-alpha-binding-v1"
STRATEGY_ALPHA_EVIDENCE_SCHEMA = "jaggedthoughts-strategy-alpha-evidence-v1"
VALUATION_CONTROL = "valuation_only_control"
DURABILITY_CONTROL = "durability_valuation_control"
STRATEGY_MODEL = "strategy_phenotype_durability_valuation"
NULL_CONTROL = "zero_factor_residual_control"
MOMENTUM_CONTROL = "six_month_active_momentum_control"
_MODEL_MECHANISMS = {
    NULL_CONTROL: ("zero_active_return",),
    MOMENTUM_CONTROL: ("active_momentum_persistence",),
    VALUATION_CONTROL: ("price_implied_expectations",),
    DURABILITY_CONTROL: ("durable_earnings_expectation", "price_implied_expectations"),
    STRATEGY_MODEL: (
        "durable_earnings_expectation",
        "price_implied_expectations",
        "source_bound_strategy_phenotype",
        "typed_strategy_expectation_residual",
    ),
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _valid_hash(payload: dict[str, Any], field: str) -> bool:
    claimed = str(payload.get(field) or "")
    return bool(claimed) and claimed == stable_sha256({
        key: value for key, value in payload.items() if key != field
    })


def _gap(code: str, **context: Any) -> dict[str, Any]:
    body = {"code": code, **context}
    return {**body, "gap_sha256": stable_sha256(body)}


def strategy_alpha_tournament_surface(
    strategy_transfer: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe the registered nested alpha test and its current activation state."""

    transfer = strategy_transfer or {}
    evidence_state = evidence or {}
    outcome_count = int(transfer.get("settled_operating_outcome_count") or 0)
    eligible_count = int(evidence_state.get("eligible_count") or 0)
    tournament_ready = bool(evidence_state.get("tournament_ready"))
    gap_counts = dict(evidence_state.get("gap_counts") or {})
    return {
        "schema": "jaggedthoughts-strategy-alpha-tournament-surface-v1",
        "registered": True,
        "question": (
            "Does a typed strategy-choice expectation residual improve later active-return "
            "prediction beyond null, momentum, valuation, and value-quality controls?"
        ),
        "nested_model_ids": list(_MODEL_MECHANISMS),
        "same_information_control": True,
        "settled_operating_outcome_count": outcome_count,
        "eligible_episode_count": eligible_count,
        "eligible_issuer_count": int(evidence_state.get("eligible_issuer_count") or 0),
        "independent_block_count": int(evidence_state.get("independent_block_count") or 0),
        "compatible_family_count": int(evidence_state.get("compatible_family_count") or 0),
        "tournament_ready": tournament_ready,
        "gap_counts": gap_counts,
        "status": (
            "ready_to_run" if tournament_ready
            else "insufficient_independent_blocks" if eligible_count
            else "awaiting_settlements_and_typed_residual_bindings"
        ),
        "next_activation": (
            "Run the nested same-information strategy-alpha tournament."
            if tournament_ready
            else "Accumulate at least eight compatible frozen strategy-alpha blocks."
            if eligible_count
            else "Settle closed-book returns and freeze deterministic controls plus one typed strategy residual."
        ),
        "capital_authority": False,
    }


def _sha256(value: Any, label: str) -> str:
    text = require_text(value, label).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{label} must be a full SHA-256 digest")
    return text


def validate_strategy_alpha_binding_abi(binding: Mapping[str, Any]) -> None:
    """Reject bindings that cannot become a current nested-alpha episode."""

    if (
        binding.get("schema") != STRATEGY_ALPHA_BINDING_SCHEMA
        or not _valid_hash(dict(binding), "binding_sha256")
    ):
        raise ValueError("binding schema or hash is invalid")
    for field in (
        "arm_isolation_sha256", "strategy_expectation_residual_sha256",
        "strategy_procedure_sha256", "action_sha256",
    ):
        _sha256(binding.get(field), f"binding.{field}")
    arm_views = dict(binding.get("arm_view_sha256s") or {})
    if set(arm_views) != {"valuation", "durability", "strategy"}:
        raise ValueError("binding requires three masked arm-view identities")
    for role, digest in arm_views.items():
        _sha256(digest, f"binding.{role}_arm_view_sha256")
    candidate_ids = dict(binding.get("forecast_candidate_ids") or {})
    if set(candidate_ids) != {"valuation", "durability", "strategy"}:
        raise ValueError("binding requires three nested forecast candidate ids")
    if binding.get("strategy_translation_kind") != "direct_operating_hurdle_payoff":
        raise ValueError("binding requires the direct operating-hurdle translation")
    probability = require_finite(
        binding.get("operating_hurdle_probability"),
        "binding operating_hurdle_probability",
    )
    if not 0 <= probability <= 1:
        raise ValueError("binding operating-hurdle probability must be in [0, 1]")
    _sha256(binding.get("operating_contract_sha256"), "binding.operating_contract_sha256")


def _binding_abi_is_current(binding: Mapping[str, Any]) -> bool:
    try:
        validate_strategy_alpha_binding_abi(binding)
        return True
    except ValueError:
        return False


@dataclass(frozen=True, slots=True)
class StrategyAlphaEpisode:
    """One frozen information packet and its later security outcome."""

    episode_id: str
    inference_block_id: str
    entity_id: str
    issuer_identity: str
    cohort_family_sha256: str
    information_set_sha256: str
    information_available_at: str
    phenotype_sha256: str
    strategy_expectation_residual_sha256: str
    strategy_translation_kind: str
    strategy_causal_effect_earned: bool
    strategy_procedure_sha256: str
    phenotype_available_at: str
    trained_through: str
    issued_at: str
    start_at: str
    end_at: str
    outcome_available_at: str
    valuation_expected_active_return: float
    momentum_expected_active_return: float
    durability_return_adjustment: float
    phenotype_return_adjustment: float
    asset_return: float
    benchmark_return: float
    information_source_refs: tuple[str, ...]
    phenotype_source_refs: tuple[str, ...]
    outcome_source_refs: tuple[str, ...]
    cash_return: float = 0.0
    security_target_return: float | None = None

    def __post_init__(self) -> None:
        for attribute in ("episode_id", "inference_block_id", "entity_id", "issuer_identity"):
            object.__setattr__(self, attribute, require_text(getattr(self, attribute), attribute))
        object.__setattr__(
            self, "cohort_family_sha256",
            _sha256(self.cohort_family_sha256, "cohort_family_sha256"),
        )
        object.__setattr__(
            self, "information_set_sha256", _sha256(self.information_set_sha256, "information_set_sha256")
        )
        object.__setattr__(self, "phenotype_sha256", _sha256(self.phenotype_sha256, "phenotype_sha256"))
        object.__setattr__(
            self, "strategy_expectation_residual_sha256",
            _sha256(
                self.strategy_expectation_residual_sha256,
                "strategy_expectation_residual_sha256",
            ),
        )
        if self.strategy_translation_kind != "direct_operating_hurdle_payoff":
            raise ValueError("strategy_translation_kind is unsupported")
        if not isinstance(self.strategy_causal_effect_earned, bool):
            raise ValueError("strategy_causal_effect_earned must be boolean")
        if self.strategy_causal_effect_earned:
            raise ValueError("direct operating-hurdle episodes cannot claim a causal effect")
        object.__setattr__(
            self, "strategy_procedure_sha256",
            _sha256(self.strategy_procedure_sha256, "strategy_procedure_sha256"),
        )
        for attribute in (
            "information_available_at", "phenotype_available_at", "trained_through", "issued_at",
            "start_at", "end_at", "outcome_available_at",
        ):
            object.__setattr__(self, attribute, canonical_timestamp(getattr(self, attribute), attribute))
        for attribute in (
            "valuation_expected_active_return", "durability_return_adjustment",
            "phenotype_return_adjustment", "momentum_expected_active_return",
            "asset_return", "benchmark_return", "cash_return",
        ):
            object.__setattr__(self, attribute, require_finite(getattr(self, attribute), attribute))
        if self.security_target_return is not None:
            object.__setattr__(
                self, "security_target_return",
                require_finite(self.security_target_return, "security_target_return"),
            )
        information_refs = require_refs(self.information_source_refs, "information source ref")
        phenotype_refs = require_refs(self.phenotype_source_refs, "phenotype source ref")
        outcome_refs = require_refs(self.outcome_source_refs, "outcome source ref")
        if not set(phenotype_refs) <= set(information_refs):
            raise ValueError("phenotype sources must belong to the frozen information set")
        if set(information_refs) & set(outcome_refs):
            raise ValueError("forecast information and later outcome sources must be disjoint")
        if timestamp_key(self.phenotype_available_at) > timestamp_key(self.information_available_at):
            raise ValueError("phenotype was unavailable when the information set froze")
        if timestamp_key(self.information_available_at) > timestamp_key(self.issued_at):
            raise ValueError("information set was unavailable when the forecast issued")
        if timestamp_key(self.trained_through) > timestamp_key(self.issued_at):
            raise ValueError("forecast issued before its training cutoff")
        for prediction in self.predictions().values():
            if not -1 <= prediction <= 3:
                raise ValueError("expected active return must be in [-1, 3]")
        object.__setattr__(self, "information_source_refs", information_refs)
        object.__setattr__(self, "phenotype_source_refs", phenotype_refs)
        object.__setattr__(self, "outcome_source_refs", outcome_refs)

    def predictions(self) -> dict[str, float]:
        valuation = self.valuation_expected_active_return
        durability = valuation + self.durability_return_adjustment
        return {
            NULL_CONTROL: 0.0,
            MOMENTUM_CONTROL: self.momentum_expected_active_return,
            VALUATION_CONTROL: valuation,
            DURABILITY_CONTROL: durability,
            STRATEGY_MODEL: durability + self.phenotype_return_adjustment,
        }


def _strategy_alpha_cohort_family(
    run: Mapping[str, Any], binding: Mapping[str, Any], dual: Mapping[str, Any],
) -> str:
    """Identity of episodes whose estimand and scoring contract may be pooled."""
    window = dict((run.get("settlement_contract") or {}).get(
        "prospective_return_window"
    ) or {})
    operating = dict(dual.get("operating_outcome") or {})
    control = dict((dual.get("security_outcome") or {}).get("control") or {})
    body = {
        "schema": "jaggedthoughts-strategy-alpha-cohort-family-v1",
        "strategy_procedure_sha256": binding.get("strategy_procedure_sha256"),
        "mechanism_phenotype_sha256": binding.get("phenotype_sha256"),
        "strategy_translation_kind": binding.get("strategy_translation_kind"),
        "forecast_formula_contract": "nested-strategy-alpha-ablation-v1",
        "horizon_days": window.get("horizon_days"),
        "price_identity": window.get("price_identity"),
        "transaction_cost_bps": window.get("transaction_cost_bps"),
        "benchmark_entity_id": control.get("benchmark_entity_id"),
        "factor_basis": sorted(
            str(row.get("factor_id") or "")
            for row in control.get("factors") or () if isinstance(row, Mapping)
        ),
        "operating_hurdle": {
            key: operating.get(key) for key in (
                "metric_id", "unit", "direction", "comparator", "outcome_role",
            )
        },
    }
    return stable_sha256(body)


def _episode_from_workspace(
    root: Path,
    run: dict[str, Any],
    settlement: dict[str, Any],
    binding: dict[str, Any],
    statistical_block_id: str,
) -> StrategyAlphaEpisode:
    if run.get("schema") != "jaggedthoughts-closed-book-forecast-run-v1" or not _valid_hash(run, "run_sha256"):
        raise ValueError("run schema or hash is invalid")
    if (
        settlement.get("schema") != "jaggedthoughts-closed-book-settlement-v1"
        or not _valid_hash(settlement, "settlement_sha256")
    ):
        raise ValueError("settlement schema or hash is invalid")
    if binding.get("schema") != STRATEGY_ALPHA_BINDING_SCHEMA or not _valid_hash(binding, "binding_sha256"):
        raise ValueError("strategy-alpha binding schema or hash is invalid")
    packet = dict(run.get("evidence_packet") or {})
    entity_id = str((packet.get("entity") or {}).get("entity_id") or "")
    for observed, expected, label in (
        (settlement.get("run_id"), run.get("run_id"), "settlement run"),
        (settlement.get("run_sha256"), run.get("run_sha256"), "settlement run hash"),
        (binding.get("run_id"), run.get("run_id"), "binding run"),
        (binding.get("run_sha256"), run.get("run_sha256"), "binding run hash"),
        (binding.get("packet_sha256"), packet.get("packet_sha256"), "binding packet"),
        (binding.get("entity_id"), entity_id, "binding entity"),
    ):
        if str(observed or "") != str(expected or ""):
            raise ValueError(f"{label} identity does not match")
    bound_at = canonical_timestamp(binding.get("bound_at"), "binding.bound_at")
    opened_at = canonical_timestamp(run.get("opened_at"), "run.opened_at")
    request_frozen_at = canonical_timestamp(
        binding.get("request_frozen_at"), "binding.request_frozen_at",
    )
    if timestamp_key(bound_at) != timestamp_key(opened_at):
        raise ValueError("strategy-alpha binding must be sealed at the forecast open")
    nomination = dict((packet.get("discovery_summary") or {}).get(
        "strategy_experiment_nomination"
    ) or {})
    dual = dict(nomination.get("dual_outcome_contract") or {})
    for observed, expected, label in (
        (binding.get("nomination_sha256"), nomination.get("nomination_sha256"), "nomination"),
        (binding.get("dual_outcome_contract_sha256"), dual.get("dual_outcome_contract_sha256"), "dual outcome contract"),
        (binding.get("candidate_leaf"), nomination.get("candidate_leaf"), "candidate leaf"),
        (binding.get("move_sha256"), dual.get("move_sha256"), "strategy move"),
        (
            binding.get("strategy_choice_identity_sha256"),
            dual.get("strategy_choice_identity_sha256"),
            "strategy choice identity",
        ),
        (binding.get("implementation_event_sha256"), dual.get("implementation_event_sha256"), "implementation event"),
    ):
        if not expected or str(observed or "") != str(expected):
            raise ValueError(f"binding {label} identity does not match")
    phenotype_sha = _sha256(binding.get("phenotype_sha256"), "binding.phenotype_sha256")
    information_sha = _sha256(binding.get("information_set_sha256"), "binding.information_set_sha256")
    roles = dict(binding.get("forecast_candidate_ids") or {})
    if set(roles) != {"valuation", "durability", "strategy"} or len(set(roles.values())) != 3:
        raise ValueError("binding requires three distinct nested forecast candidate ids")
    candidates = {
        str(row.get("candidate_id") or ""): row
        for row in (binding.get("candidate_forecasts") or run.get("candidate_forecasts") or ())
        if isinstance(row, dict)
    }
    selected = {}
    isolation_sha = _sha256(
        binding.get("arm_isolation_sha256"), "binding.arm_isolation_sha256",
    )
    arm_view_shas = dict(binding.get("arm_view_sha256s") or {})
    if set(arm_view_shas) != {"valuation", "durability", "strategy"}:
        raise ValueError("binding requires three masked arm-view identities")
    required_mechanisms = {
        "valuation": set(_MODEL_MECHANISMS[VALUATION_CONTROL]),
        "durability": set(_MODEL_MECHANISMS[DURABILITY_CONTROL]),
        "strategy": set(_MODEL_MECHANISMS[STRATEGY_MODEL]),
    }
    for role, candidate_id in roles.items():
        candidate = candidates.get(str(candidate_id))
        if candidate is None:
            raise ValueError(f"{role} forecast candidate is missing")
        if not _valid_hash(candidate, "forecast_sha256"):
            raise ValueError(f"{role} forecast hash is invalid")
        refs = {str(value) for value in candidate.get("source_refs") or ()}
        if information_sha not in refs and f"information-set:{information_sha}" not in refs:
            raise ValueError(f"{role} forecast does not bind the common information set")
        generated_at = canonical_timestamp(candidate.get("generated_at"), f"{role}.generated_at")
        if not timestamp_key(request_frozen_at) <= timestamp_key(generated_at) <= timestamp_key(bound_at):
            raise ValueError(f"{role} forecast falls outside the request-to-binding interval")
        mechanisms = {str(value) for value in candidate.get("mechanism_ids") or ()}
        if not required_mechanisms[role] <= mechanisms:
            raise ValueError(f"{role} forecast lacks its declared mechanisms")
        if role != "strategy" and "source_bound_strategy_phenotype" in mechanisms:
            raise ValueError(f"{role} control leaks the strategy phenotype")
        producer = dict(candidate.get("producer") or {})
        view_sha = _sha256(arm_view_shas.get(role), f"binding.{role}_arm_view_sha256")
        if (
            producer.get("arm_isolation_sha256") != isolation_sha
            or producer.get("arm_view_sha256") != view_sha
            or f"arm-view:{view_sha}" not in refs
        ):
            raise ValueError(f"{role} forecast lacks its isolated evidence-view receipt")
        selected[role] = candidate

    predictions = {
        role: require_finite((candidate.get("predicted_values") or {}).get("active_return"), f"{role} forecast")
        for role, candidate in selected.items()
    }
    actual = dict(settlement.get("actual_values") or {})
    phenotype_refs = require_refs(binding.get("phenotype_source_refs") or (), "binding phenotype source ref")
    information_refs = tuple(sorted(
        set(phenotype_refs)
        | {str(ref) for candidate in selected.values() for ref in candidate.get("source_refs") or ()}
    ))
    entity_end = dict(settlement.get("entity_end_price") or {})
    benchmark_end = dict(settlement.get("benchmark_end_price") or {})
    security = compile_strategy_security_outcome(root, run=run, settlement=settlement)
    if security.get("status") == "factor_endpoint_unavailable":
        raise ValueError("factor-controlled return endpoint is unavailable")
    primary_return = (
        security.get("factor_controlled_return")
        if security.get("status") == "factor_controlled"
        else security.get("benchmark_active_return")
    )
    starting_market = dict(packet.get("starting_market") or {})
    if starting_market.get("active_return_6m") is None:
        raise ValueError("frozen packet lacks the pre-open momentum control")
    return StrategyAlphaEpisode(
        episode_id=require_text(run.get("episode_id"), "run.episode_id"),
        inference_block_id=require_text(statistical_block_id, "statistical_block_id"),
        entity_id=entity_id,
        issuer_identity=f"public_equity:{entity_id.upper()}",
        cohort_family_sha256=_strategy_alpha_cohort_family(run, binding, dual),
        information_set_sha256=information_sha,
        information_available_at=opened_at,
        phenotype_sha256=phenotype_sha,
        strategy_expectation_residual_sha256=_sha256(
            binding.get("strategy_expectation_residual_sha256"),
            "binding.strategy_expectation_residual_sha256",
        ),
        strategy_translation_kind=require_text(
            binding.get("strategy_translation_kind"),
            "binding.strategy_translation_kind",
        ),
        strategy_causal_effect_earned=bool(
            binding.get("strategy_causal_effect_earned")
        ),
        strategy_procedure_sha256=_sha256(
            binding.get("strategy_procedure_sha256"),
            "binding.strategy_procedure_sha256",
        ),
        phenotype_available_at=binding.get("phenotype_available_at"),
        trained_through=opened_at,
        issued_at=opened_at,
        start_at=(settlement.get("return_window_binding") or {}).get("entry_observed_at"),
        end_at=(settlement.get("return_window_settlement") or {}).get("exit_observed_at"),
        outcome_available_at=settlement.get("evaluated_at"),
        valuation_expected_active_return=predictions["valuation"],
        momentum_expected_active_return=require_finite(
            starting_market.get("active_return_6m"),
            "starting six-month active return",
        ),
        durability_return_adjustment=predictions["durability"] - predictions["valuation"],
        phenotype_return_adjustment=predictions["strategy"] - predictions["durability"],
        asset_return=require_finite(actual.get("entity_return"), "settlement entity return"),
        benchmark_return=require_finite(actual.get("benchmark_return"), "settlement benchmark return"),
        information_source_refs=information_refs,
        phenotype_source_refs=phenotype_refs,
        outcome_source_refs=(
            require_text(entity_end.get("source_ref"), "entity outcome source"),
            require_text(benchmark_end.get("source_ref"), "benchmark outcome source"),
            *tuple(sorted(str(value) for value in security.get("source_refs") or ())),
        ),
        cash_return=require_finite((run.get("settlement_contract") or {}).get("cash_return", 0), "cash return"),
        security_target_return=require_finite(primary_return, "primary security return"),
    )


def compile_strategy_alpha_evidence(root: Path) -> tuple[tuple[StrategyAlphaEpisode, ...], dict[str, Any]]:
    """Lower eligible workspace artifacts and explain every exclusion."""

    runs: dict[str, dict[str, Any]] = {}
    settlements: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    gaps: list[dict[str, Any]] = []
    for directory, target in (
        (root / "closed_book" / "runs", runs),
        (root / "closed_book" / "settlements", settlements),
        (root / "closed_book" / "strategy_alpha_bindings", bindings),
    ):
        for path in sorted(directory.glob("*.json")):
            try:
                row = _read_json(path)
                run_id = require_text(row.get("run_id"), f"{path} run_id")
                if run_id in target:
                    raise ValueError(f"duplicate artifact for run {run_id}")
                target[run_id] = row
            except ValueError as error:
                gaps.append(_gap("invalid_artifact", artifact_path=path.relative_to(root).as_posix(), detail=str(error)))

    strategy_run_ids = {
        run_id for run_id, run in runs.items()
        if isinstance((
            ((run.get("evidence_packet") or {}).get("discovery_summary") or {}).get(
                "strategy_experiment_nomination"
            )
        ), Mapping)
    }
    strategy_settlements = {
        run_id: row for run_id, row in settlements.items() if run_id in strategy_run_ids
    }
    strategy_bindings = {
        run_id: row for run_id, row in bindings.items() if run_id in strategy_run_ids
    }
    raw_episodes: list[tuple[str, StrategyAlphaEpisode]] = []
    statistical_blocks = overlap_cluster_ids(tuple(strategy_settlements.values()))
    for run_id, run in sorted(runs.items()):
        if run_id not in strategy_run_ids:
            continue
        packet = dict(run.get("evidence_packet") or {})
        entity_id = str((packet.get("entity") or {}).get("entity_id") or "")
        subject_id = str((packet.get("subject") or {}).get("subject_id") or "")
        if subject_id.startswith("fund:"):
            gaps.append(_gap("entity_kind_not_public_equity", run_id=run_id, entity_id=entity_id))
            continue
        settlement = strategy_settlements.get(run_id)
        raw_binding = strategy_bindings.get(run_id)
        binding = raw_binding
        if binding is not None and not _binding_abi_is_current(binding):
            try:
                validate_strategy_alpha_binding_abi(binding)
            except ValueError as error:
                gaps.append(_gap(
                    "strategy_alpha_binding_ineligible", run_id=run_id,
                    entity_id=entity_id, detail=str(error),
                ))
            binding = None
        if settlement is None:
            gaps.append(_gap("settlement_missing", run_id=run_id, entity_id=entity_id, end_at=run.get("end_at")))
        if raw_binding is None:
            gaps.append(_gap(
                "strategy_alpha_binding_missing",
                run_id=run_id,
                entity_id=entity_id,
                required_candidate_roles=["valuation", "durability", "strategy"],
            ))
        if settlement is None or binding is None:
            continue
        if run_id not in statistical_blocks:
            gaps.append(_gap(
                "tradable_return_window_missing", run_id=run_id, entity_id=entity_id,
            ))
            continue
        try:
            raw_episodes.append((run_id, _episode_from_workspace(
                root, run, settlement, binding, statistical_blocks[run_id],
            )))
        except ValueError as error:
            gaps.append(_gap("strategy_alpha_binding_ineligible", run_id=run_id, entity_id=entity_id, detail=str(error)))

    for run_id in sorted(set(bindings) - set(runs)):
        gaps.append(_gap("orphan_strategy_alpha_binding", run_id=run_id))

    families: dict[str, list[tuple[str, StrategyAlphaEpisode]]] = {}
    for run_id, episode in raw_episodes:
        families.setdefault(episode.cohort_family_sha256, []).append((run_id, episode))
    cohorts = []
    for family_sha, rows in sorted(families.items()):
        primaries = []
        seen_issuers: dict[str, str] = {}
        for run_id, episode in sorted(
            rows, key=lambda row: (timestamp_key(row[1].issued_at), row[1].episode_id),
        ):
            if episode.issuer_identity in seen_issuers:
                gaps.append(_gap(
                    "within_issuer_replication", run_id=run_id,
                    issuer_identity=episode.issuer_identity,
                    primary_run_id=seen_issuers[episode.issuer_identity],
                    cohort_family_sha256=family_sha,
                ))
                continue
            seen_issuers[episode.issuer_identity] = run_id
            primaries.append((run_id, episode))
        blocks = overlap_cluster_ids(tuple(
            strategy_settlements[run_id] for run_id, _episode in primaries
        ))
        primary_episodes = tuple(
            replace(episode, inference_block_id=blocks[run_id])
            for run_id, episode in primaries if run_id in blocks
        )
        cohorts.append({
            "cohort_family_sha256": family_sha,
            "raw_episode_count": len(rows),
            "primary_episode_count": len(primary_episodes),
            "issuer_count": len({row.issuer_identity for row in primary_episodes}),
            "independent_block_count": len({row.inference_block_id for row in primary_episodes}),
            "episodes": primary_episodes,
        })
    selected = max(
        cohorts,
        key=lambda row: (
            row["independent_block_count"], row["issuer_count"],
            row["primary_episode_count"], row["cohort_family_sha256"],
        ),
        default=None,
    )
    episodes = tuple(selected["episodes"]) if selected else ()

    gap_counts: dict[str, int] = {}
    for gap in gaps:
        gap_counts[gap["code"]] = gap_counts.get(gap["code"], 0) + 1
    calibration = compile_strategy_hurdle_calibration(
        root, bindings=tuple(strategy_bindings.values()),
    )
    report = {
        "schema": STRATEGY_ALPHA_EVIDENCE_SCHEMA,
        "workspace": str(root),
        "run_count": len(strategy_run_ids),
        "settlement_count": len(strategy_settlements),
        "binding_count": len(strategy_bindings),
        "current_binding_count": sum(
            _binding_abi_is_current(binding) for binding in strategy_bindings.values()
        ),
        "ineligible_binding_count": sum(
            not _binding_abi_is_current(binding) for binding in strategy_bindings.values()
        ),
        "raw_eligible_count": len(raw_episodes),
        "eligible_count": len(episodes),
        "eligible_episode_ids": sorted(episode.episode_id for episode in episodes),
        "eligible_issuer_count": len({episode.issuer_identity for episode in episodes}),
        "independent_block_count": len({episode.inference_block_id for episode in episodes}),
        "compatible_family_count": len(cohorts),
        "selected_cohort_family_sha256": (
            selected["cohort_family_sha256"] if selected else None
        ),
        "cohort_families": [
            {key: value for key, value in cohort.items() if key != "episodes"}
            for cohort in cohorts
        ],
        "gap_counts": dict(sorted(gap_counts.items())),
        "gaps": sorted(gaps, key=lambda row: (row["code"], str(row.get("run_id") or row.get("entity_id") or ""))),
        "tournament_ready": (
            len({episode.issuer_identity for episode in episodes}) >= 8
            and len({episode.inference_block_id for episode in episodes}) >= 8
        ),
        "operating_hurdle_calibration": calibration,
        "capital_authority": False,
    }
    return episodes, {**report, "evidence_sha256": stable_sha256(report)}


def compile_strategy_hurdle_calibration(
    root: Path, *, bindings: tuple[Mapping[str, Any], ...] | None = None,
) -> dict[str, Any]:
    """Score the probability leaf separately from the security-return translation."""

    if bindings is None:
        bindings = tuple(
            _read_json(path)
            for path in sorted((root / "closed_book" / "strategy_alpha_bindings").glob("*.json"))
        )
    library_path = root / "institutional_learning" / "strategy_moves" / "latest.json"
    try:
        library = _read_json(library_path)
    except ValueError:
        library = {}
    outcomes = {
        (str(move.get("move_sha256") or ""), str(episode.get("contract_sha256") or "")):
        dict(episode)
        for move in library.get("moves") or () if isinstance(move, Mapping)
        for episode in move.get("outcome_episodes") or () if isinstance(episode, Mapping)
        and episode.get("status") in {"supports", "contradicts"}
    }
    rows = []
    gaps = []
    for binding in bindings:
        if (
            binding.get("schema") != STRATEGY_ALPHA_BINDING_SCHEMA
            or not _valid_hash(dict(binding), "binding_sha256")
        ):
            gaps.append(_gap("invalid_binding_for_hurdle_calibration"))
            continue
        if (
            not binding.get("operating_contract_sha256")
            or binding.get("operating_hurdle_probability") is None
            or not binding.get("strategy_procedure_sha256")
        ):
            gaps.append(_gap(
                "legacy_binding_missing_typed_hurdle_forecast",
                run_id=binding.get("run_id"),
            ))
            continue
        identity = (
            str(binding.get("move_sha256") or ""),
            str(binding.get("operating_contract_sha256") or ""),
        )
        outcome = outcomes.get(identity)
        if outcome is None:
            gaps.append(_gap(
                "operating_hurdle_outcome_pending", run_id=binding.get("run_id"),
                operating_contract_sha256=identity[1],
            ))
            continue
        probability = require_finite(
            binding.get("operating_hurdle_probability"), "operating hurdle probability",
        )
        if not 0 <= probability <= 1:
            raise ValueError("operating hurdle probability must be in [0, 1]")
        actual = 1.0 if outcome["status"] == "supports" else 0.0
        clipped = min(1 - 1e-12, max(1e-12, probability))
        rows.append({
            "run_id": binding.get("run_id"),
            "strategy_procedure_sha256": binding.get("strategy_procedure_sha256"),
            "operating_contract_sha256": identity[1],
            "forecast_probability": probability,
            "actual_hurdle_event": int(actual),
            "brier_loss": (probability - actual) ** 2,
            "half_control_brier_loss": 0.25,
            "log_loss": -(actual * math.log(clipped) + (1 - actual) * math.log(1 - clipped)),
            "outcome_episode_sha256": outcome.get("episode_sha256"),
            "outcome_available_at": outcome.get("available_at"),
            "source_refs": list(outcome.get("source_refs") or ()),
        })
    procedures = {str(row["strategy_procedure_sha256"] or "") for row in rows}
    body = {
        "schema": "jaggedthoughts-strategy-hurdle-calibration-v1",
        "settled_forecast_count": len(rows),
        "procedure_sha256s": sorted(procedures),
        "rows": rows,
        "mean_brier_loss": (
            sum(row["brier_loss"] for row in rows) / len(rows) if rows else None
        ),
        "half_control_mean_brier_loss": 0.25 if rows else None,
        "status": (
            "mixed_procedures_not_poolable" if len(procedures) > 1
            else "calibration_observed" if rows
            else "awaiting_operating_outcomes"
        ),
        "gaps": gaps,
        "promotion_authority": False,
        "capital_authority": False,
    }
    return {**body, "calibration_sha256": stable_sha256(body)}


def evaluate_strategy_alpha_tournament(
    *,
    tournament_id: str,
    owner: str,
    as_of: str,
    candidate_set_frozen_at: str,
    episodes: tuple[StrategyAlphaEpisode, ...],
    mode: str = "historical_backtest",
    transaction_cost_bps: float = 10.0,
    probe_weight: float = 0.05,
    min_inference_blocks: int = 8,
    alpha: float = 0.05,
    periods_per_year: float = 4.0,
    seed: int = 42,
) -> dict[str, Any]:
    """Test the incremental phenotype contribution against nested controls."""

    if not episodes:
        raise ValueError("strategy-alpha tournament requires episodes")
    frozen_at = canonical_timestamp(candidate_set_frozen_at, "candidate_set_frozen_at")
    if not 0 < require_finite(probe_weight, "probe_weight") <= 0.25:
        raise ValueError("probe_weight must be in (0, 0.25]")
    if len({episode.episode_id for episode in episodes}) != len(episodes):
        raise ValueError("strategy-alpha episode identities must be unique")
    if len({episode.issuer_identity for episode in episodes}) != len(episodes):
        raise ValueError("strategy-alpha tournament accepts one primary episode per issuer")
    if len({episode.cohort_family_sha256 for episode in episodes}) != 1:
        raise ValueError("strategy-alpha tournament cannot pool incompatible cohort families")
    if any(timestamp_key(frozen_at) > timestamp_key(episode.issued_at) for episode in episodes):
        raise ValueError("candidate set must freeze before every forecast issues")
    procedure_shas = {episode.strategy_procedure_sha256 for episode in episodes}
    if len(procedure_shas) != 1:
        raise ValueError("strategy-alpha tournament cannot pool different procedure identities")
    procedure_sha = next(iter(procedure_shas))

    candidate_contract = {
        "schema": STRATEGY_ALPHA_TOURNAMENT_SCHEMA,
        "frozen_at": frozen_at,
        "nested_models": _MODEL_MECHANISMS,
        "strategy_procedure_sha256": procedure_sha,
        "forecast_formula": {
            NULL_CONTROL: "0",
            MOMENTUM_CONTROL: "frozen six-month benchmark-active return",
            VALUATION_CONTROL: "valuation_expected_active_return",
            DURABILITY_CONTROL: "valuation_expected_active_return + durability_return_adjustment",
            STRATEGY_MODEL: (
                "valuation_expected_active_return + durability_return_adjustment "
                "+ phenotype_return_adjustment"
            ),
        },
        "paper_weight_rule": f"{probe_weight} when expected active return > 0; otherwise 0",
    }
    candidate_set_sha256 = stable_sha256(candidate_contract)
    models = tuple(
        WorldModelCandidate(
            model_id=model_id,
            version=procedure_sha[:16],
            model_family="nested_strategy_alpha_ablation",
            trial_family_id="strategy-alpha-nested-ablation-v1",
            mechanism_ids=mechanisms,
            linked_observable_ids=(),
            source_refs=(f"candidate-set:{candidate_set_sha256}",),
        )
        for model_id, mechanisms in _MODEL_MECHANISMS.items()
    )
    lowered_episodes = tuple(
        BacktestEpisode(
            episode_id=episode.episode_id,
            inference_block_id=episode.inference_block_id,
            entity_id=episode.entity_id,
            start_at=episode.start_at,
            end_at=episode.end_at,
            outcome_available_at=episode.outcome_available_at,
            starting_weight=0.0,
            asset_return=(
                episode.security_target_return
                if episode.security_target_return is not None else episode.asset_return
            ),
            benchmark_return=(
                0.0 if episode.security_target_return is not None else episode.benchmark_return
            ),
            cash_return=episode.cash_return,
            actual_values={
                "active_return": (
                    episode.security_target_return
                    if episode.security_target_return is not None
                    else episode.asset_return - episode.benchmark_return
                )
            },
            source_refs=episode.outcome_source_refs,
        )
        for episode in episodes
    )
    forecasts = tuple(
        WorldModelForecast(
            model_id=model_id,
            episode_id=episode.episode_id,
            trained_through=episode.trained_through,
            issued_at=episode.issued_at,
            predicted_values={"active_return": prediction},
            target_weight=probe_weight if prediction > 0 else 0.0,
            source_refs=(f"information-set:{episode.information_set_sha256}",),
        )
        for episode in episodes
        for model_id, prediction in episode.predictions().items()
    )
    evaluation = evaluate_world_model_tournament(
        tournament_id=tournament_id,
        owner=owner,
        as_of=as_of,
        mode=mode,
        baseline_model_id=VALUATION_CONTROL,
        observables=(ObservableSpec("active_return", "decimal_return", "absolute", 0.10, 1.0),),
        models=models,
        episodes=lowered_episodes,
        forecasts=forecasts,
        transaction_cost_bps=transaction_cost_bps,
        declared_trial_family_ids=("strategy-alpha-nested-ablation-v1",),
        source_refs=tuple(sorted(
            {f"candidate-set:{candidate_set_sha256}"}
            | {f"information-set:{episode.information_set_sha256}" for episode in episodes}
            | {ref for episode in episodes for ref in episode.outcome_source_refs}
        )),
        alpha=alpha,
        min_inference_blocks=min_inference_blocks,
        periods_per_year=periods_per_year,
        seed=seed,
    )
    mean_losses = {
        row["model_id"]: float(row["prediction_loss"]["mean"])
        for row in evaluation["model_metrics"]
    }
    point_edge = all(
        mean_losses[STRATEGY_MODEL] < mean_losses[control]
        for control in (
            NULL_CONTROL, MOMENTUM_CONTROL, VALUATION_CONTROL, DURABILITY_CONTROL,
        )
    )
    incremental_comparisons = []
    for control in (
        NULL_CONTROL, MOMENTUM_CONTROL, VALUATION_CONTROL, DURABILITY_CONTROL,
    ):
        comparison = next(
            row for row in evaluation["paired_comparisons"]
            if row["dimension"] == "prediction_loss"
            and {row["left_model_id"], row["right_model_id"]} == {STRATEGY_MODEL, control}
        )
        target_delta = float(comparison["observed_delta"])
        if comparison["right_model_id"] == STRATEGY_MODEL:
            target_delta *= -1
        incremental_comparisons.append({
            "control_model_id": control,
            "target_minus_control_prediction_loss": target_delta,
            "p_value": comparison["p_value"],
            "fdr": comparison["fdr"],
            "target_better_after_fdr": bool(
                target_delta < 0
                and comparison.get("fdr")
                and comparison["fdr"]["rejected_at_alpha"]
            ),
        })
    statistical_edge = all(row["target_better_after_fdr"] for row in incremental_comparisons)
    economic_comparisons = []
    for control in (
        NULL_CONTROL, MOMENTUM_CONTROL, VALUATION_CONTROL, DURABILITY_CONTROL,
    ):
        comparison = next(
            row for row in evaluation["paired_comparisons"]
            if row["dimension"] == "economic_loss"
            and {row["left_model_id"], row["right_model_id"]} == {STRATEGY_MODEL, control}
        )
        target_delta = float(comparison["observed_delta"])
        if comparison["right_model_id"] == STRATEGY_MODEL:
            target_delta *= -1
        economic_comparisons.append({
            "control_model_id": control,
            "target_minus_control_economic_loss": target_delta,
            "p_value": comparison["p_value"],
            "fdr": comparison["fdr"],
            "target_better_after_fdr": bool(
                target_delta < 0
                and comparison.get("fdr")
                and comparison["fdr"]["rejected_at_alpha"]
            ),
        })
    economic_edge = all(row["target_better_after_fdr"] for row in economic_comparisons)
    body = {
        "schema": STRATEGY_ALPHA_TOURNAMENT_SCHEMA,
        "candidate_set": {**candidate_contract, "candidate_set_sha256": candidate_set_sha256},
        "same_information_control": {
            "verified": True,
            "identity": (
                "one frozen epoch with deterministic controls and one masked "
                "operating-hurdle probability"
            ),
            "incremental_question": (
                "Does the typed strategy-choice residual improve later active-return prediction "
                "beyond null, momentum, valuation, and value-quality controls?"
            ),
        },
        "phenotype_bindings": [
            {
                "episode_id": episode.episode_id,
                "information_set_sha256": episode.information_set_sha256,
                "phenotype_sha256": episode.phenotype_sha256,
                "strategy_expectation_residual_sha256": (
                    episode.strategy_expectation_residual_sha256
                ),
                "strategy_translation_kind": episode.strategy_translation_kind,
                "strategy_causal_effect_earned": episode.strategy_causal_effect_earned,
                "strategy_procedure_sha256": episode.strategy_procedure_sha256,
                "phenotype_available_at": episode.phenotype_available_at,
                "phenotype_source_refs": list(episode.phenotype_source_refs),
            }
            for episode in episodes
        ],
        "evaluation": evaluation,
        "incremental_comparisons": incremental_comparisons,
        "economic_comparisons": economic_comparisons,
        "strategy_point_estimate_better_than_controls": point_edge,
        "strategy_better_than_controls_after_fdr": statistical_edge,
        "strategy_after_cost_better_than_controls_after_fdr": economic_edge,
        "status": (
            "insufficient_inference_blocks" if not evaluation["inference_sufficient"]
            else "point_estimate_rejected" if not point_edge
            else "inconclusive_after_fdr" if not statistical_edge
            else "no_after_cost_edge" if not economic_edge
            else "prospective_conditional_challenger" if mode == "prospective_shadow"
            else "retrospective_support_requires_prospective_settlement"
        ),
        "capital_authority": False,
        "promotion_boundary": (
            "A direct hurdle residual may advance only as a conditional paper challenger. "
            "Causal labeling additionally requires a separately transported effect. Neither "
            "status can activate a portfolio."
        ),
    }
    return {**body, "strategy_alpha_tournament_sha256": stable_sha256(body)}


__all__ = [
    "DURABILITY_CONTROL",
    "MOMENTUM_CONTROL",
    "NULL_CONTROL",
    "STRATEGY_ALPHA_BINDING_SCHEMA",
    "STRATEGY_ALPHA_EVIDENCE_SCHEMA",
    "STRATEGY_ALPHA_TOURNAMENT_SCHEMA",
    "STRATEGY_MODEL",
    "StrategyAlphaEpisode",
    "VALUATION_CONTROL",
    "compile_strategy_alpha_evidence",
    "compile_strategy_hurdle_calibration",
    "evaluate_strategy_alpha_tournament",
    "strategy_alpha_tournament_surface",
    "validate_strategy_alpha_binding_abi",
]
