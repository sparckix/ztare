"""Strategy-conditioned path tilt over an empirical Markov prior.

The Lagrangian is a compact path-probability restriction, not a physics claim.
Only pre-outcome strategy exposure may tilt the prior; realized destinations are
score targets and never model inputs.
"""

from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256


SCHEMA = "jaggedthoughts-strategy-path-lagrangian-tournament-v1"
ACTIVATION_SCHEMA = "jaggedthoughts-strategy-path-lagrangian-activation-v1"
PATH_INPUT_SCHEMA = "jaggedthoughts-strategy-conditioned-path-input-v1"
STATE_IDS = (
    "low_value_low_durability", "low_value_high_durability",
    "high_value_low_durability", "high_value_high_durability",
)
_DURABILITY = {"low": -1.0, "high": 1.0}
_PARTITIONS = ("visible", "future_time", "unseen_issuer")


def _durability(state_id: str) -> float:
    for label, value in _DURABILITY.items():
        if state_id.endswith(f"_{label}_durability"):
            return value
    raise ValueError(f"unsupported company state: {state_id}")


def sustained_durability_observable(
    source_state: str, intermediate_state: str, terminal_state: str,
) -> float:
    """Return the frozen [-1, 1] sustained durable-earnings path statistic."""
    source = _durability(source_state)
    return (
        _durability(intermediate_state) - source
        + _durability(terminal_state) - source
    ) / 4.0


def _checked_row(row: Mapping[str, Any], phenotype_sha256: str) -> dict[str, Any]:
    required = {
        "entity_id", "source_epoch", "intermediate_epoch", "terminal_epoch",
        "source_state", "intermediate_state", "terminal_state",
        "strategy_exposure", "mechanism_phenotype_sha256",
    }
    missing = sorted(required - set(row))
    if missing:
        raise ValueError(f"strategy path row misses {missing}")
    exposure = str(row["strategy_exposure"])
    if exposure not in {"exposed", "unexposed"}:
        raise ValueError("strategy exposure must be certified exposed or unexposed")
    if row.get("mechanism_phenotype_sha256") != phenotype_sha256:
        raise ValueError("strategy path crosses phenotype identity")
    if not (
        str(row["source_epoch"]) < str(row["intermediate_epoch"])
        < str(row["terminal_epoch"])
    ):
        raise ValueError("strategy path epochs must be strictly ordered")
    if exposure == "exposed":
        if not str(row.get("event_available_at") or "") <= str(row["source_epoch"]):
            raise ValueError("strategy event was not public before the path source epoch")
        if len(str(row.get("implementation_event_sha256") or "")) != 64:
            raise ValueError("exposed rows require an exact implementation-event identity")
    elif len(str(row.get("monitoring_coverage_sha256") or "")) != 64:
        raise ValueError("unexposed rows require monitored no-event coverage")
    for field in ("source_state", "intermediate_state", "terminal_state"):
        if row[field] not in STATE_IDS:
            raise ValueError(f"unsupported company state: {row[field]}")
    return dict(row)


def _transition(
    rows: Sequence[Mapping[str, Any]], pseudocount: float,
) -> list[list[float]]:
    if not math.isfinite(pseudocount) or pseudocount <= 0:
        raise ValueError("pseudocount must be positive and finite")
    index = {state: offset for offset, state in enumerate(STATE_IDS)}
    counts = [[pseudocount for _ in STATE_IDS] for _ in STATE_IDS]
    for row in rows:
        for source, target in (
            (row["source_state"], row["intermediate_state"]),
            (row["intermediate_state"], row["terminal_state"]),
        ):
            counts[index[source]][index[target]] += 1.0
    return [[value / math.fsum(line) for value in line] for line in counts]


def _path_prior(
    source_state: str, transition: Sequence[Sequence[float]],
) -> list[float]:
    index = {state: offset for offset, state in enumerate(STATE_IDS)}
    source = index[source_state]
    return [
        transition[source][index[intermediate]] * transition[index[intermediate]][index[terminal]]
        for intermediate in STATE_IDS for terminal in STATE_IDS
    ]


def _features(row: Mapping[str, Any], *, strategy_blind: bool = False) -> list[float]:
    exposure = 1.0 if strategy_blind or row["strategy_exposure"] == "exposed" else 0.0
    source = str(row["source_state"])
    return [
        exposure * sustained_durability_observable(source, intermediate, terminal)
        for intermediate in STATE_IDS for terminal in STATE_IDS
    ]


def strategy_path_distribution(
    row: Mapping[str, Any], transition: Sequence[Sequence[float]], theta: float, *,
    strategy_blind: bool = False,
) -> list[float]:
    """Return P0(path|source) exp(theta*feature) / Z."""
    base, features = _path_prior(str(row["source_state"]), transition), _features(
        row, strategy_blind=strategy_blind,
    )
    shift = max(theta * value for value in features)
    weights = [
        probability * math.exp(theta * feature - shift)
        for probability, feature in zip(base, features, strict=True)
    ]
    total = math.fsum(weights)
    return [weight / total for weight in weights]


def _offset_logit_distribution(
    row: Mapping[str, Any], transition: Sequence[Sequence[float]], theta: float,
) -> list[float]:
    """Independent conditional-logit evaluation for the equivalence kill check."""
    base, features = _path_prior(str(row["source_state"]), transition), _features(row)
    logits = [
        math.log(probability) + theta * feature
        for probability, feature in zip(base, features, strict=True)
    ]
    shift = max(logits)
    weights = [math.exp(logit - shift) for logit in logits]
    total = math.fsum(weights)
    return [weight / total for weight in weights]


def _fit_theta(
    rows: Sequence[Mapping[str, Any]], transition: Sequence[Sequence[float]], *,
    ridge: float, strategy_blind: bool = False,
) -> float:
    if not math.isfinite(ridge) or ridge < 0:
        raise ValueError("ridge must be nonnegative and finite")
    index = {state: offset for offset, state in enumerate(STATE_IDS)}
    theta = 0.0
    for _ in range(50):
        gradient, curvature = -ridge * theta, ridge
        for row in rows:
            features = _features(row, strategy_blind=strategy_blind)
            probabilities = strategy_path_distribution(
                row, transition, theta, strategy_blind=strategy_blind,
            )
            target = index[row["intermediate_state"]] * len(STATE_IDS) + index[row["terminal_state"]]
            expected = math.fsum(p * value for p, value in zip(probabilities, features, strict=True))
            gradient += features[target] - expected
            curvature += math.fsum(
                p * (value - expected) ** 2
                for p, value in zip(probabilities, features, strict=True)
            )
        if curvature <= 1e-14:
            return 0.0
        step = gradient / curvature
        theta = max(-12.0, min(12.0, theta + step))
        if abs(step) <= 1e-10:
            break
    return theta


def _second_order_prior(
    rows: Sequence[Mapping[str, Any]], pseudocount: float,
) -> dict[str, list[float]]:
    counts = {
        source: [pseudocount for _ in range(len(STATE_IDS) ** 2)]
        for source in STATE_IDS
    }
    index = {state: offset for offset, state in enumerate(STATE_IDS)}
    for row in rows:
        target = index[row["intermediate_state"]] * len(STATE_IDS) + index[row["terminal_state"]]
        counts[row["source_state"]][target] += 1.0
    return {source: [value / math.fsum(line) for value in line] for source, line in counts.items()}


def _loss(probabilities: Sequence[float], target: int) -> tuple[float, float]:
    return (
        -math.log(max(probabilities[target], 1e-300)),
        math.fsum(
            (probability - float(offset == target)) ** 2
            for offset, probability in enumerate(probabilities)
        ),
    )


def _score(
    rows: Sequence[Mapping[str, Any]], transition: Sequence[Sequence[float]],
    second_order: Mapping[str, Sequence[float]], theta: float, blind_theta: float,
) -> dict[str, dict[str, float]]:
    index = {state: offset for offset, state in enumerate(STATE_IDS)}
    losses = defaultdict(lambda: {"cross_entropy": [], "brier": []})
    for row in rows:
        target = index[row["intermediate_state"]] * len(STATE_IDS) + index[row["terminal_state"]]
        models = {
            "directed_markov": _path_prior(row["source_state"], transition),
            "second_order_markov": second_order[row["source_state"]],
            "strategy_blind_tilt": strategy_path_distribution(
                row, transition, blind_theta, strategy_blind=True,
            ),
            "strategy_path_tilt": strategy_path_distribution(row, transition, theta),
        }
        for model_id, probabilities in models.items():
            cross_entropy, brier = _loss(probabilities, target)
            losses[model_id]["cross_entropy"].append(cross_entropy)
            losses[model_id]["brier"].append(brier)
    return {
        model_id: {
            metric: math.fsum(values) / len(values)
            for metric, values in metrics.items()
        }
        for model_id, metrics in losses.items()
    }


def compile_strategy_path_tournament(
    partitions: Mapping[str, Sequence[Mapping[str, Any]]], *,
    phenotype_sha256: str, state_representation_sha256: str,
    pseudocount: float = 1.0, ridge: float = 1.0,
) -> dict[str, Any]:
    """Fit on visible rows and score later-time plus unseen-issuer paths."""
    if set(partitions) != set(_PARTITIONS):
        raise ValueError(f"strategy path partitions must be exactly {_PARTITIONS}")
    if any(len(value) != 64 for value in (
        phenotype_sha256, state_representation_sha256,
    )):
        raise ValueError("strategy path identities must be sha256 digests")
    rows = {
        name: [_checked_row(row, phenotype_sha256) for row in partitions[name]]
        for name in _PARTITIONS
    }
    if any(not partition for partition in rows.values()):
        raise ValueError("strategy path partitions cannot be empty")
    visible_issuers = {row["entity_id"] for row in rows["visible"]}
    future_issuers = {row["entity_id"] for row in rows["future_time"]}
    unseen_issuers = {row["entity_id"] for row in rows["unseen_issuer"]}
    if visible_issuers & unseen_issuers:
        raise ValueError("unseen-issuer paths overlap fit issuers")
    if not future_issuers <= visible_issuers:
        raise ValueError("future-time paths must use fit issuers; issuer transfer is separate")
    if not max(str(row["terminal_epoch"]) for row in rows["visible"]) < min(
        str(row["source_epoch"]) for row in rows["future_time"]
    ):
        raise ValueError("future-time paths must start after every visible path ends")
    if not {row["strategy_exposure"] for row in rows["visible"]} == {"exposed", "unexposed"}:
        raise ValueError("visible rows require exposure overlap")

    transition = _transition(rows["visible"], pseudocount)
    second_order = _second_order_prior(rows["visible"], pseudocount)
    theta = _fit_theta(rows["visible"], transition, ridge=ridge)
    blind_theta = _fit_theta(
        rows["visible"], transition, ridge=ridge, strategy_blind=True,
    )
    scores = {
        name: _score(rows[name], transition, second_order, theta, blind_theta)
        for name in ("future_time", "unseen_issuer")
    }
    candidate_wins = all(
        partition["strategy_path_tilt"][metric]
        < min(partition[control][metric] for control in (
            "directed_markov", "second_order_markov", "strategy_blind_tilt",
        ))
        for partition in scores.values() for metric in ("cross_entropy", "brier")
    )
    offset_equivalence_error = max(
        abs(left - right)
        for row in (item for partition in rows.values() for item in partition)
        for left, right in zip(
            strategy_path_distribution(row, transition, theta),
            _offset_logit_distribution(row, transition, theta), strict=True,
        )
    )
    body = {
        "schema": SCHEMA,
        "model_identity": {
            "phenotype_sha256": phenotype_sha256,
            "state_representation_sha256": state_representation_sha256,
            "strategy_representation": "flat_mechanism_phenotype",
            "recursive_program_conditioning": False,
        },
        "partition_row_counts": {name: len(partition) for name, partition in rows.items()},
        "fit_issuer_count": len(visible_issuers),
        "unseen_issuer_count": len(unseen_issuers),
        "action": "-log(P0(path|source)) - theta * exposed_strategy_sustained_durability(path)",
        "baseline": "visible_only_empirical_directed_two_step_markov",
        "fitted_theta": theta,
        "strategy_blind_theta": blind_theta,
        "scores": scores,
        "same_feature_offset_logit": {
            "max_abs_probability_error": offset_equivalence_error,
            "numerically_equivalent": offset_equivalence_error <= 1e-12,
            "distinct_model_family_credit": False,
        },
        "candidate_control_pass": candidate_wins,
        "remaining_kill_controls": [
            "clustered_event_calendar_shuffle",
            "adjacent_state_representation_replay",
            "industry_shrunk_markov",
            "matched_support_phenotype_substitution",
        ],
        "status": "survived_initial_controls" if candidate_wins else "rejected_by_initial_controls",
        "predictive_law_authority": False,
        "causal_authority": False,
        "signal_authority": False,
        "capital_authority": False,
    }
    return {**body, "tournament_sha256": stable_sha256(body)}


def _verified_path_input(strategy_join: Mapping[str, Any]) -> dict[str, Any]:
    if strategy_join.get("schema") != "jaggedthoughts-strategy-state-transition-join-v1":
        raise ValueError("strategy-path activation requires a strategy-state join")
    join_body = dict(strategy_join)
    declared_join = str(join_body.pop("join_sha256", ""))
    if declared_join != stable_sha256(join_body):
        raise ValueError("strategy-state join content hash mismatch")
    path_input = dict(strategy_join.get("strategy_conditioned_path_input") or {})
    if path_input.get("schema") != PATH_INPUT_SCHEMA:
        raise ValueError("strategy-conditioned path input schema mismatch")
    input_body = dict(path_input)
    declared_input = str(input_body.pop("input_sha256", ""))
    if declared_input != stable_sha256(input_body):
        raise ValueError("strategy-conditioned path input hash mismatch")
    for row in path_input.get("rows") or ():
        row_body = dict(row)
        declared_row = str(row_body.pop("model_row_sha256", ""))
        if declared_row != stable_sha256(row_body):
            raise ValueError("strategy-conditioned path row hash mismatch")
    return path_input


def compile_strategy_path_activation(
    recovery: Mapping[str, Any], strategy_join: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the flat-phenotype path tournament only when its two input gates pass."""
    path_input = _verified_path_input(strategy_join)
    recovery_ready = (
        recovery.get("schema") == "jaggedthoughts-max-caliber-recovery-v1"
        and (recovery.get("recovery_gate") or {}).get("status") == "recovery_gate_passed"
    )
    support = next((
        dict(row) for row in strategy_join.get("phenotype_path_support") or ()
        if isinstance(row, Mapping) and row.get("fit_support_available")
    ), None)
    blockers = [
        *([] if recovery_ready else ["measurement_recovery_gate"]),
        *([] if support else ["exposed_and_unexposed_transfer_support"]),
        *list(map(str, path_input.get("missing_inputs") or ())),
    ]
    base = {
        "schema": ACTIVATION_SCHEMA,
        "recovery_result_sha256": recovery.get("result_sha256"),
        "strategy_join_sha256": strategy_join.get("join_sha256"),
        "path_input_sha256": path_input.get("input_sha256"),
        "model_identity": "flat_mechanism_phenotype_path_tilt",
        "recursive_program_conditioning": False,
        "signal_authority": False,
        "capital_authority": False,
    }
    if blockers:
        body = {
            **base, "status": "blocked_on_input_gates",
            "blockers": sorted(set(blockers)), "tournament": None,
        }
        return {**body, "activation_sha256": stable_sha256(body)}

    phenotype_sha = str(support["mechanism_phenotype_sha256"])
    rows = [
        dict(row) for row in path_input.get("rows") or ()
        if row.get("mechanism_phenotype_sha256") == phenotype_sha
    ]
    fit_floor = int(
        (strategy_join.get("fit_support_floor") or {}).get(
            "independent_issuers_per_exposure_class", 8,
        )
    )
    unseen_floor = int(
        (strategy_join.get("fit_support_floor") or {}).get(
            "unseen_issuers_per_exposure_class", 8,
        )
    )
    unseen_issuers: set[str] = set()
    fit_issuers: set[str] = set()
    for exposure in ("exposed", "unexposed"):
        issuers = sorted(
            {str(row["entity_id"]) for row in rows if row["strategy_exposure"] == exposure},
            key=lambda entity: stable_sha256({
                "phenotype_sha256": phenotype_sha, "entity_id": entity,
                "partition": "unseen_issuer",
            }),
        )
        unseen_issuers.update(issuers[:unseen_floor])
        fit_issuers.update(issuers[unseen_floor:unseen_floor + fit_floor])
    fit_rows = [row for row in rows if str(row["entity_id"]) in fit_issuers]
    cutoffs = sorted({str(row["source_epoch"]) for row in fit_rows})
    selected = None
    for cutoff in cutoffs:
        visible = [row for row in fit_rows if str(row["terminal_epoch"]) < cutoff]
        future = [row for row in fit_rows if str(row["source_epoch"]) >= cutoff]
        if (
            {row["entity_id"] for row in visible} == fit_issuers
            and {row["entity_id"] for row in future} == fit_issuers
        ):
            selected = (cutoff, visible, future)
            break
    if selected is None:
        body = {
            **base, "status": "blocked_on_chronological_partition",
            "blockers": ["nonoverlapping_future_time_cutoff"], "tournament": None,
        }
        return {**body, "activation_sha256": stable_sha256(body)}
    cutoff, visible, future = selected
    unseen = [row for row in rows if str(row["entity_id"]) in unseen_issuers]
    partitions = {"visible": visible, "future_time": future, "unseen_issuer": unseen}
    state_representation_sha256 = stable_sha256({"state_ids": STATE_IDS})
    tournament = compile_strategy_path_tournament(
        partitions, phenotype_sha256=phenotype_sha,
        state_representation_sha256=state_representation_sha256,
    )
    receipt = {
        "cutoff": cutoff,
        "fit_issuer_ids": sorted(fit_issuers),
        "unseen_issuer_ids": sorted(unseen_issuers),
        "partition_model_row_sha256s": {
            name: sorted(str(row["model_row_sha256"]) for row in partition)
            for name, partition in partitions.items()
        },
    }
    body = {
        **base, "status": tournament["status"], "blockers": [],
        "partition_receipt": receipt,
        "partition_receipt_sha256": stable_sha256(receipt),
        "tournament": tournament,
    }
    return {**body, "activation_sha256": stable_sha256(body)}


def compile_workspace_strategy_path_activation(workspace: str | Path) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    recovery = json.loads((
        root / "experiments/results/max-caliber-recovery.json"
    ).read_text(encoding="utf-8"))
    strategy_join = json.loads((
        root / "experiments/results/strategy-state-transition-join.json"
    ).read_text(encoding="utf-8"))
    result = compile_strategy_path_activation(recovery, strategy_join)
    destination = root / "experiments/results/strategy-path-lagrangian.json"
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return result


__all__ = [
    "ACTIVATION_SCHEMA", "PATH_INPUT_SCHEMA", "SCHEMA", "STATE_IDS",
    "compile_strategy_path_activation", "compile_strategy_path_tournament",
    "compile_workspace_strategy_path_activation",
    "strategy_path_distribution", "sustained_durability_observable",
]
