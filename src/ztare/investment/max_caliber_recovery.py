"""Sealed recovery check for one contextual maximum-caliber path tilt.

The check asks a narrow question: can a scalar exponential tilt recover a
planted issuer-conditioned path observable without promoting planted noise?
It reads the frozen company-state partitions but never writes an artifact or
grants signal/capital authority.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .learning_scheduler import LEARNING_SCHEDULE_SCHEMA
from .strategy_path_lagrangian import SCHEMA as STRATEGY_PATH_LAGRANGIAN_SCHEMA
from .strategy_state_transition_join import STRATEGY_STATE_TRANSITION_JOIN_SCHEMA


SCHEMA = "jaggedthoughts-max-caliber-recovery-v1"
MAX_CALIBER_READINESS_SCHEMA = "jaggedthoughts-max-caliber-readiness-v1"
IMPLEMENTATION_ID = "max-caliber-recovery-1.0"
REQUIRED_COLUMNS = {
    "source_epoch", "intermediate_epoch", "terminal_epoch", "entity_id",
    "source_state_id", "intermediate_state_id", "terminal_state_id",
}
_DURABILITY = {"low": -1.0, "middle": 0.0, "high": 1.0}


def _read(path: Path) -> tuple[list[dict[str, str]], str]:
    payload = path.read_bytes()
    rows = list(csv.DictReader(payload.decode("utf-8").splitlines(), delimiter="\t"))
    if not rows or not REQUIRED_COLUMNS.issubset(rows[0]):
        raise ValueError(f"invalid company-state path partition: {path}")
    return rows, hashlib.sha256(payload).hexdigest()


def _issuer_context(entity_id: str) -> float:
    """Stable [-1, 1] covariate derived from identity, never path outcomes."""
    raw = int.from_bytes(hashlib.sha256(entity_id.encode()).digest()[:8], "big")
    return 2.0 * raw / (2**64 - 1) - 1.0


def _durability(state_id: str) -> float:
    try:
        return _DURABILITY[state_id.rsplit("_", 1)[1]]
    except KeyError as error:
        raise ValueError(f"unknown durability state: {state_id}") from error


def _feature(entity_id: str, source: str, terminal: str) -> float:
    return _issuer_context(entity_id) * (_durability(terminal) - _durability(source)) / 2.0


def _directed_markov(
    rows: Sequence[Mapping[str, str]], states: Sequence[str], pseudocount: float,
) -> list[list[float]]:
    if not math.isfinite(pseudocount) or pseudocount <= 0:
        raise ValueError("pseudocount must be positive and finite")
    index = {state: offset for offset, state in enumerate(states)}
    counts = [[pseudocount for _ in states] for _ in states]
    for row in rows:
        for source, target in (
            (row["source_state_id"], row["intermediate_state_id"]),
            (row["intermediate_state_id"], row["terminal_state_id"]),
        ):
            counts[index[source]][index[target]] += 1.0
    return [[value / math.fsum(line) for value in line] for line in counts]


def _path_surface(
    row: Mapping[str, str], states: Sequence[str], transition: Sequence[Sequence[float]],
) -> tuple[list[float], list[float]]:
    index = {state: offset for offset, state in enumerate(states)}
    source = row["source_state_id"]
    base, features = [], []
    for intermediate in states:
        for terminal in states:
            base.append(
                transition[index[source]][index[intermediate]]
                * transition[index[intermediate]][index[terminal]]
            )
            features.append(_feature(row["entity_id"], source, terminal))
    return base, features


def _tilt(base: Sequence[float], features: Sequence[float], theta: float) -> list[float]:
    shift = max(theta * value for value in features)
    weights = [probability * math.exp(theta * value - shift)
               for probability, value in zip(base, features, strict=True)]
    total = math.fsum(weights)
    return [weight / total for weight in weights]


def _offset_logit(base: Sequence[float], features: Sequence[float], theta: float) -> list[float]:
    logits = [math.log(probability) + theta * value
              for probability, value in zip(base, features, strict=True)]
    shift = max(logits)
    weights = [math.exp(logit - shift) for logit in logits]
    total = math.fsum(weights)
    return [weight / total for weight in weights]


def _target(row: Mapping[str, str], states: Sequence[str]) -> int:
    index = {state: offset for offset, state in enumerate(states)}
    return index[row["intermediate_state_id"]] * len(states) + index[row["terminal_state_id"]]


def _fit_theta(
    rows: Sequence[Mapping[str, str]], targets: Sequence[int], states: Sequence[str],
    transition: Sequence[Sequence[float]],
) -> float:
    theta = 0.0
    for _ in range(30):
        gradient = variance = 0.0
        for row, target in zip(rows, targets, strict=True):
            base, features = _path_surface(row, states, transition)
            probabilities = _tilt(base, features, theta)
            expected = math.fsum(p * value for p, value in zip(probabilities, features, strict=True))
            gradient += features[target] - expected
            variance += math.fsum(
                p * (value - expected) ** 2
                for p, value in zip(probabilities, features, strict=True)
            )
        if variance <= 1e-14:
            return 0.0
        step = gradient / variance
        theta = max(-12.0, min(12.0, theta + step))
        if abs(step) <= 1e-10:
            break
    return theta


def _sample(probabilities: Sequence[float], rng: random.Random) -> int:
    draw, cumulative = rng.random(), 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if draw <= cumulative:
            return index
    return len(probabilities) - 1


def _simulate(
    rows: Sequence[Mapping[str, str]], states: Sequence[str],
    transition: Sequence[Sequence[float]], theta: float, rng: random.Random,
) -> list[int]:
    return [
        _sample(_tilt(*_path_surface(row, states, transition), theta), rng)
        for row in rows
    ]


def _scores(
    rows: Sequence[Mapping[str, str]], targets: Sequence[int], states: Sequence[str],
    transition: Sequence[Sequence[float]], theta: float,
) -> dict[str, dict[str, float]]:
    losses = {name: {"cross_entropy": [], "brier": []} for name in ("p0", "tilt")}
    for row, target in zip(rows, targets, strict=True):
        base, features = _path_surface(row, states, transition)
        for name, probabilities in (("p0", base), ("tilt", _tilt(base, features, theta))):
            losses[name]["cross_entropy"].append(-math.log(max(probabilities[target], 1e-300)))
            losses[name]["brier"].append(math.fsum(
                (probability - float(index == target)) ** 2
                for index, probability in enumerate(probabilities)
            ))
    return {
        name: {metric: math.fsum(values) / len(values) for metric, values in metrics.items()}
        for name, metrics in losses.items()
    }


def _promoted(scores: Mapping[str, Mapping[str, Mapping[str, float]]]) -> bool:
    return all(
        partition["tilt"][metric] < partition["p0"][metric]
        for partition in scores.values() for metric in ("cross_entropy", "brier")
    )


def _scenario(
    rows: Mapping[str, Sequence[Mapping[str, str]]], states: Sequence[str],
    transition: Sequence[Sequence[float]], true_theta: float, trials: int, seed: int,
) -> dict[str, object]:
    estimates, promotions, signs = [], 0, 0
    deltas = {name: {"cross_entropy": [], "brier": []} for name in ("holdout", "farther_tail")}
    for trial in range(trials):
        rng = random.Random(seed + trial)
        targets = {name: _simulate(partition, states, transition, true_theta, rng)
                   for name, partition in rows.items()}
        estimate = _fit_theta(rows["visible"], targets["visible"], states, transition)
        estimates.append(estimate)
        signs += int(true_theta != 0.0 and estimate * true_theta > 0.0)
        sealed_scores = {
            name: _scores(rows[name], targets[name], states, transition, estimate)
            for name in ("holdout", "farther_tail")
        }
        promotions += int(_promoted(sealed_scores))
        for name, scores in sealed_scores.items():
            for metric in deltas[name]:
                deltas[name][metric].append(scores["p0"][metric] - scores["tilt"][metric])
    return {
        "true_theta": true_theta,
        "trial_count": trials,
        "mean_fitted_theta": math.fsum(estimates) / trials,
        "fitted_theta_sign_recovery_rate": signs / trials if true_theta else None,
        "sealed_promotion_rate": promotions / trials,
        "mean_sealed_score_improvement": {
            name: {metric: math.fsum(values) / trials for metric, values in metrics.items()}
            for name, metrics in deltas.items()
        },
    }


def run_recovery_tournament(
    visible: str | Path, holdout: str | Path, farther_tail: str | Path, *,
    trials: int = 64, injected_theta: float = 2.0, seed: int = 260826,
    pseudocount: float = 1.0,
) -> dict[str, object]:
    """Run null and injected recovery on frozen TSV partitions; return no-authority evidence."""
    if trials < 1 or not math.isfinite(injected_theta) or injected_theta == 0.0:
        raise ValueError("trials must be positive and injected_theta finite and nonzero")
    paths = {"visible": Path(visible), "holdout": Path(holdout),
             "farther_tail": Path(farther_tail)}
    loaded = {name: _read(path) for name, path in paths.items()}
    rows = {name: value[0] for name, value in loaded.items()}
    hashes = {name: value[1] for name, value in loaded.items()}
    states = tuple(sorted({
        row[column] for partition in rows.values() for row in partition
        for column in ("source_state_id", "intermediate_state_id", "terminal_state_id")
    }))
    if len(states) < 2:
        raise ValueError("company-state recovery requires at least two states")
    transition = _directed_markov(rows["visible"], states, pseudocount)
    observed_targets = {name: [_target(row, states) for row in partition]
                        for name, partition in rows.items()}
    observed_theta = _fit_theta(rows["visible"], observed_targets["visible"], states, transition)
    observed_scores = {
        name: _scores(rows[name], observed_targets[name], states, transition, observed_theta)
        for name in ("holdout", "farther_tail")
    }
    equivalence_error = max(
        abs(left - right)
        for row in (item for partition in rows.values() for item in partition)
        for theta in (-2.0, -0.5, 0.0, 0.5, 2.0)
        for left, right in zip(
            _tilt(*_path_surface(row, states, transition), theta),
            _offset_logit(*_path_surface(row, states, transition), theta), strict=True,
        )
    )
    bundle_hash = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    null = _scenario(rows, states, transition, 0.0, trials, seed)
    injected = _scenario(rows, states, transition, injected_theta, trials, seed + 1_000_000)
    false_promotion_rate = float(null["sealed_promotion_rate"])
    injection_power = float(injected["sealed_promotion_rate"])
    sign_recovery = float(injected["fitted_theta_sign_recovery_rate"] or 0.0)
    gate = {
        "maximum_false_promotion_rate": 0.05,
        "minimum_injected_power": 0.80,
        "minimum_sign_recovery_rate": 0.80,
        "null_control_pass": false_promotion_rate <= 0.05,
        "injected_recovery_pass": injection_power >= 0.80 and sign_recovery >= 0.80,
    }
    gate["status"] = (
        "recovery_gate_passed"
        if gate["null_control_pass"] and gate["injected_recovery_pass"]
        else "recovery_gate_failed"
    )
    gate["next_activation"] = (
        "Freeze a strategy-conditioned temporal and issuer-transfer tournament."
        if gate["status"] == "recovery_gate_passed" else
        "Do not fit a strategy-conditioned path law; add independent issuers or path blocks and rerun the unchanged recovery design."
    )
    body = {
        "schema": SCHEMA,
        "design": {
            "implementation_id": IMPLEMENTATION_ID,
            "trials": trials,
            "injected_theta": injected_theta,
            "seed": seed,
            "pseudocount": pseudocount,
        },
        "partition_sha256": hashes,
        "partition_bundle_sha256": bundle_hash,
        "partition_row_counts": {name: len(value) for name, value in rows.items()},
        "state_ids": list(states),
        "baseline": "empirical_directed_two_step_markov_fit_on_visible_only",
        "issuer_context": "sha256(entity_id)_mapped_to_minus_one_plus_one; outcome_blind",
        "path_feature": "issuer_context * (terminal_durability-source_durability)/2",
        "model": "Q_theta(path|source,issuer) proportional to P0(path|source)*exp(theta*F)",
        "fit_partition": "visible",
        "sealed_score_partitions": ["holdout", "farther_tail"],
        "promotion_rule": "tilt strictly beats P0 on cross-entropy and Brier in both sealed partitions",
        "observed_diagnostic": {
            "fitted_theta": observed_theta,
            "sealed_scores": observed_scores,
            "would_promote_under_mechanical_rule": _promoted(observed_scores),
        },
        "null": {**null, "false_promotion_rate": false_promotion_rate},
        "injected": {**injected, "power": injection_power},
        "recovery_gate": gate,
        "same_feature_offset_logit": {
            "max_abs_probability_error": equivalence_error,
            "numerically_equivalent": equivalence_error <= 1e-12,
            "claim_boundary": (
                "The MaxCal form is an offset conditional logit for this feature set; "
                "it may earn compression or transfer credit, not distinct model-family credit."
            ),
        },
        "signal_authority": False,
        "capital_authority": False,
        "use_boundary": "measurement recovery only; no market signal or allocation authority",
    }
    return {**body, "result_sha256": stable_sha256(body)}


def compile_max_caliber_readiness(
    recovery: Mapping[str, Any], strategy_join: Mapping[str, Any],
    learning_schedule: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep measurement recovery and strategy-conditioning support independent."""
    if recovery.get("schema") != SCHEMA:
        raise ValueError("recovery acquisition requires a MaxCal recovery audit")
    if strategy_join.get("schema") != STRATEGY_STATE_TRANSITION_JOIN_SCHEMA:
        raise ValueError("recovery acquisition requires a strategy-state join")
    if learning_schedule.get("schema") != LEARNING_SCHEDULE_SCHEMA:
        raise ValueError("recovery acquisition requires a learning schedule")

    gate = recovery.get("recovery_gate") or {}
    fit_entities = set(map(str, strategy_join.get("fit_qualified_issuer_ids") or ()))
    exact_entities = {
        str(row.get("entity_id") or "")
        for row in strategy_join.get("event_bundles") or ()
        if isinstance(row, Mapping) and row.get("entity_id")
    }
    overlap = set(map(str, strategy_join.get("overlap_entity_ids") or ()))
    candidates = sorted((
        dict(row) for row in learning_schedule.get("actions") or ()
        if isinstance(row, Mapping)
        and row.get("kind") == "jaggedthoughts_strategy_event_refinement_research"
        and str(row.get("entity_id") or "") in overlap - exact_entities - fit_entities
    ), key=lambda row: (int(row.get("rank") or 10**9), str(row.get("work_id") or "")))
    selected = candidates[0] if candidates else None
    floor = strategy_join.get("fit_support_floor") or {}
    path_input = strategy_join.get("strategy_conditioned_path_input") or {}
    path_rows = [row for row in path_input.get("rows") or () if isinstance(row, Mapping)]
    path_missing = list(map(str, path_input.get("missing_inputs") or ()))
    independent_floor = int(floor.get("independent_issuers") or 0)
    if not independent_floor:
        independent_floor = int(
            floor.get("independent_issuers_per_exposure_class") or 0
        )
    recovery_ready = gate.get("status") == "recovery_gate_passed"
    join_ready = (
        strategy_join.get("status") == "fit_support_available" and not path_missing
    )
    body = {
        "schema": MAX_CALIBER_READINESS_SCHEMA,
        "recovery_result_sha256": recovery.get("result_sha256"),
        "strategy_join_sha256": strategy_join.get("join_sha256"),
        "learning_schedule_sha256": learning_schedule.get("schedule_sha256"),
        "measurement_recovery_lane": {
            "status": gate.get("status"),
            "partition_bundle_sha256": recovery.get("partition_bundle_sha256"),
            "selected_existing_job": None,
            "next_input_identity": (
                None if recovery_ready else "new_company_state_partition_bundle"
            ),
            "next_activation": gate.get("next_activation"),
        },
        "strategy_conditioning_lane": {
            "status": strategy_join.get("status"),
            "fit_qualified_issuer_count": len(fit_entities),
            "fit_qualified_issuer_floor": independent_floor,
            "independent_issuer_deficit": max(0, independent_floor - len(fit_entities)),
            "overlap_issuer_count": len(overlap),
            "exact_event_issuer_count": len(exact_entities),
            "path_input_sha256": path_input.get("input_sha256"),
            "exposed_two_step_path_count": sum(
                row.get("strategy_exposure") == "exposed" for row in path_rows
            ),
            "certified_unexposed_two_step_path_count": sum(
                row.get("strategy_exposure") == "unexposed" for row in path_rows
            ),
            "path_input_missing": path_missing,
            "queued_exact_event_candidate_count": len(candidates),
            "selected_existing_job": ({
                key: selected.get(key) for key in (
                    "work_id", "kind", "entity_id", "rank", "queue_priority",
                    "ordering_basis", "action_class",
                )
            } if selected else None),
        },
        "independence_contract": {
            "event_refinement_changes": "strategy_state_transition_join_only",
            "partition_refresh_changes": "measurement_recovery_only",
            "conditioned_tournament_requires": [
                "recovery_gate_passed", "strategy_fit_support_available",
            ],
        },
        "conditioned_tournament_contract": {
            "schema": STRATEGY_PATH_LAGRANGIAN_SCHEMA,
            "action": (
                "-log(P0(path|source)) - theta * "
                "certified_strategy_exposure * sustained_durability(path)"
            ),
            "statistical_identity": "same_feature_offset_conditional_multinomial_logit",
            "core_controls": [
                "directed_markov", "second_order_markov", "strategy_blind_tilt",
            ],
            "remaining_kill_controls": [
                "clustered_event_calendar_shuffle",
                "adjacent_state_representation_replay",
                "industry_shrunk_markov",
                "matched_support_phenotype_substitution",
            ],
            "implementation": "ztare.investment.strategy_path_lagrangian",
            "fit_allowed": recovery_ready and join_ready,
        },
        "status": (
            "ready_for_conditioned_tournament"
            if recovery_ready and join_ready else "collecting_independent_evidence"
        ),
        "next_activation": (
            (f"Run {selected['entity_id']} exact-event refinement at scheduler rank "
             f"#{selected['rank']} to improve only the strategy join. " if selected else "")
            + ("Acquire a new company-state partition bundle and rerun the unchanged "
               "recovery audit. " if not recovery_ready else "")
            + (f"Complete path inputs: {', '.join(path_missing)}. " if path_missing else "")
            + "Start the conditioned tournament only after both lanes pass."
        ),
        "research_authority": "independent_evidence_routing_only",
        "signal_authority": False,
        "capital_authority": False,
    }
    return {**body, "readiness_sha256": stable_sha256(body)}


def compile_workspace_recovery(
    workspace: str | Path, *, trials: int = 64, injected_theta: float = 2.0,
    seed: int = 260826, pseudocount: float = 1.0,
) -> dict[str, object]:
    """Materialize the audit once per exact partition and design identity."""
    root = Path(workspace).expanduser().resolve()
    repo = Path(__file__).resolve().parents[3]
    project = repo / "projects" / "jaggedthoughts_company_state_path_newton"
    paths = {
        "visible": project / "evidence.txt",
        "holdout": project / "evidence_holdout.txt",
        "farther_tail": project / "evidence_farther_tail.txt",
    }
    if any(not path.is_file() for path in paths.values()):
        raise FileNotFoundError("company-state path partitions are unavailable")
    hashes = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in paths.items()
    }
    design = {
        "implementation_id": IMPLEMENTATION_ID,
        "trials": trials, "injected_theta": injected_theta,
        "seed": seed, "pseudocount": pseudocount,
    }
    destination = root / "experiments" / "results" / "max-caliber-recovery.json"
    if destination.is_file():
        existing = json.loads(destination.read_text(encoding="utf-8"))
        body = dict(existing)
        declared = str(body.pop("result_sha256", ""))
        if (
            existing.get("schema") == SCHEMA
            and declared == stable_sha256(body)
            and existing.get("partition_sha256") == hashes
            and existing.get("design") == design
        ):
            return existing
    result = run_recovery_tournament(
        paths["visible"], paths["holdout"], paths["farther_tail"],
        trials=trials, injected_theta=injected_theta, seed=seed,
        pseudocount=pseudocount,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    temporary.replace(destination)
    return result


__all__ = [
    "IMPLEMENTATION_ID", "MAX_CALIBER_READINESS_SCHEMA", "SCHEMA",
    "compile_max_caliber_readiness", "compile_workspace_recovery",
    "run_recovery_tournament",
]
