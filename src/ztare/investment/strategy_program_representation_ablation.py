"""Test whether integrated strategy structure adds path-prediction information."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from ztare.common.equivariance import stable_sha256

from .company_state_flow import COMPANY_STATE_FLOW_EVIDENCE_SCHEMA
from .strategy_learning import (
    STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA,
    STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA,
    compile_strategy_program_adoption_result,
)
from .strategy_path_lagrangian import (
    STATE_IDS,
    _loss,
    _path_prior,
    _transition,
    sustained_durability_observable,
)
from .strategy_state_transition_join import _two_step_paths


INPUT_SCHEMA = "jaggedthoughts-strategy-program-path-input-v1"
TOURNAMENT_SCHEMA = "jaggedthoughts-strategy-program-representation-ablation-v1"
ACTIVATION_SCHEMA = "jaggedthoughts-strategy-program-representation-activation-v1"
PARTITIONS = ("visible", "future_time", "unseen_issuer")
MIN_FIT_ISSUERS = 8
MIN_UNSEEN_ISSUERS = 8
MIN_PATHS_PER_ISSUER = 4
MIN_ISSUER_WIN_RATE = 0.875
MIN_INTERACTION_ISSUER_SUPPORT = 4
MIN_LOSS_IMPROVEMENT = 1e-3


def _checked_hash(row: Mapping[str, Any], schema: str, field: str) -> str:
    if row.get("schema") != schema:
        raise ValueError(f"expected {schema}")
    body = dict(row)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{schema} content hash mismatch")
    return declared


def compile_strategy_program_path_input(
    flow: Mapping[str, Any], requests: Iterable[Mapping[str, Any]],
    results: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind source-confirmed integrated programs to later company-state paths."""
    flow_sha = _checked_hash(
        flow, COMPANY_STATE_FLOW_EVIDENCE_SCHEMA, "evidence_sha256",
    )
    request_by_sha = {}
    for request in requests:
        request_sha = _checked_hash(
            request, STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA, "request_sha256",
        )
        request_by_sha[request_sha] = dict(request)

    transitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for block in flow.get("transition_blocks") or ():
        for raw in block.get("rows") or ():
            transitions[str(raw["entity_id"])].append({
                "source_epoch": str(block["source_epoch"]),
                "target_epoch": str(block["target_epoch"]),
                **dict(raw),
            })

    missing: set[str] = set()
    adoptions: list[dict[str, Any]] = []
    for raw_result in results:
        result_sha = _checked_hash(
            raw_result, STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA, "result_sha256",
        )
        request = request_by_sha.get(str(raw_result.get("request_sha256") or ""))
        if request is None:
            raise ValueError("program adoption result crossed its frozen request")
        result = compile_strategy_program_adoption_result(raw_result, request)
        if result.get("result_sha256") != result_sha:
            raise ValueError("program adoption result differs from semantic validation")
        if result.get("classification") != "exact_integrated_program_adoption":
            continue
        selected = list(result.get("selected_program_ids") or ())
        if len(selected) != 1:
            raise ValueError("exact program adoption crossed its frozen request")
        program = next((
            dict(row) for row in request.get("candidate_programs") or ()
            if row.get("program_id") == selected[0]
        ), None)
        if program is None:
            raise ValueError("selected program is absent from its frozen request")
        leaf_ids = sorted(set(map(
            str, program.get("mechanism_phenotype_sha256s") or (),
        )))
        interaction_ids = sorted(set(map(
            str, program.get("interaction_phenotype_sha256s") or (),
        )))
        if not leaf_ids or any(len(value) != 64 for value in leaf_ids):
            missing.add("typed_leaf_phenotypes")
            continue
        if program.get("active_interaction_ids") and not interaction_ids:
            missing.add("typed_interaction_phenotypes")
            continue
        option_events = list(result.get("option_events") or ())
        if not option_events:
            raise ValueError("exact program adoption requires constituent events")
        definition = {
            "program_id": str(program["program_id"]),
            "mechanism_phenotype_sha256s": leaf_ids,
            "interaction_phenotype_sha256s": interaction_ids,
        }
        adoptions.append({
            "entity_id": str(result["entity_id"]),
            "occurred_at": max(str(row["occurred_at"]) for row in option_events),
            "available_at": str(result["assessed_at"]),
            "result_sha256": result_sha,
            "program_definition": definition,
            "program_definition_sha256": stable_sha256(definition),
        })

    by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for adoption in adoptions:
        by_entity[adoption["entity_id"]].append(adoption)
    rows = []
    for entity_id, entity_adoptions in sorted(by_entity.items()):
        ordered = sorted(
            entity_adoptions,
            key=lambda row: (row["available_at"], row["result_sha256"]),
        )
        for index, adoption in enumerate(ordered):
            censor_at = ordered[index + 1]["available_at"] if index + 1 < len(ordered) else None
            observable = [
                row for row in transitions.get(entity_id, ())
                if row["source_epoch"] >= adoption["available_at"][:10]
                and (not censor_at or row["target_epoch"] < censor_at[:10])
            ]
            for path in _two_step_paths(observable):
                identity = {
                    **path,
                    "program_adoption_result_sha256": adoption["result_sha256"],
                    "program_available_at": adoption["available_at"],
                    "program_occurred_at": adoption["occurred_at"],
                    "program_definition_sha256": adoption["program_definition_sha256"],
                    **adoption["program_definition"],
                }
                rows.append({**identity, "model_row_sha256": stable_sha256(identity)})
    rows = list({row["model_row_sha256"]: row for row in rows}.values())
    counts = defaultdict(int)
    for row in rows:
        counts[str(row["entity_id"])] += 1
    eligible = sorted(
        entity for entity, count in counts.items() if count >= MIN_PATHS_PER_ISSUER
    )
    body = {
        "schema": INPUT_SCHEMA,
        "company_state_flow_evidence_sha256": flow_sha,
        "exact_program_adoption_count": len(adoptions),
        "row_count": len(rows),
        "eligible_issuer_ids": eligible,
        "eligible_issuer_count": len(eligible),
        "support_floor": {
            "fit_issuers": MIN_FIT_ISSUERS,
            "unseen_issuers": MIN_UNSEEN_ISSUERS,
            "two_step_paths_per_issuer": MIN_PATHS_PER_ISSUER,
        },
        "rows": rows,
        "missing_inputs": sorted(missing),
        "authority": "representation_ablation_input_only",
        "capital_authority": False,
    }
    return {**body, "input_sha256": stable_sha256(body)}


def _checked_row(row: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "entity_id", "source_epoch", "intermediate_epoch", "terminal_epoch",
        "source_state", "intermediate_state", "terminal_state", "program_id",
        "program_definition_sha256", "program_adoption_result_sha256",
        "program_available_at", "mechanism_phenotype_sha256s",
        "interaction_phenotype_sha256s",
        "model_row_sha256",
    }
    if missing := sorted(required - set(row)):
        raise ValueError(f"program path row misses {missing}")
    if not str(row["program_available_at"]) <= str(row["source_epoch"]):
        raise ValueError("program adoption was unavailable at path start")
    if not str(row["source_epoch"]) < str(row["intermediate_epoch"]) < str(row["terminal_epoch"]):
        raise ValueError("program path epochs must be strictly ordered")
    if any(row[field] not in STATE_IDS for field in (
        "source_state", "intermediate_state", "terminal_state",
    )):
        raise ValueError("program path uses an unsupported company state")
    for field in ("mechanism_phenotype_sha256s", "interaction_phenotype_sha256s"):
        if any(len(str(value)) != 64 for value in row[field]):
            raise ValueError("program features must be sha256 identities")
    definition = {
        "program_id": str(row["program_id"]),
        "mechanism_phenotype_sha256s": sorted(set(map(
            str, row["mechanism_phenotype_sha256s"],
        ))),
        "interaction_phenotype_sha256s": sorted(set(map(
            str, row["interaction_phenotype_sha256s"],
        ))),
    }
    if str(row["program_definition_sha256"]) != stable_sha256(definition):
        raise ValueError("program definition hash mismatch")
    identity = {key: value for key, value in row.items() if key != "model_row_sha256"}
    if str(row["model_row_sha256"]) != stable_sha256(identity):
        raise ValueError("program path row hash mismatch")
    return dict(row)


def _vocabulary(rows: Sequence[Mapping[str, Any]], structured: bool) -> tuple[str, ...]:
    features = {
        f"leaf:{value}"
        for row in rows for value in row["mechanism_phenotype_sha256s"]
    }
    if structured:
        features.update(
            f"interaction:{value}"
            for row in rows for value in row["interaction_phenotype_sha256s"]
        )
    return tuple(sorted(features))


def _context(row: Mapping[str, Any], vocabulary: Sequence[str]) -> np.ndarray:
    present = {
        *(f"leaf:{value}" for value in row["mechanism_phenotype_sha256s"]),
        *(f"interaction:{value}" for value in row["interaction_phenotype_sha256s"]),
    }
    return np.asarray([float(value in present) for value in vocabulary], dtype=float)


def _distribution(
    row: Mapping[str, Any], transition: Sequence[Sequence[float]],
    beta: np.ndarray, vocabulary: Sequence[str],
) -> np.ndarray:
    base = np.asarray(_path_prior(str(row["source_state"]), transition), dtype=float)
    context = _context(row, vocabulary)
    tilt = float(context @ beta)
    observables = np.asarray([
        sustained_durability_observable(str(row["source_state"]), middle, terminal)
        for middle in STATE_IDS for terminal in STATE_IDS
    ])
    logits = np.log(base) + tilt * observables
    weights = np.exp(logits - np.max(logits))
    return weights / np.sum(weights)


def _fit(
    rows: Sequence[Mapping[str, Any]], transition: Sequence[Sequence[float]],
    vocabulary: Sequence[str], ridge: float,
) -> np.ndarray:
    if not math.isfinite(ridge) or ridge < 0:
        raise ValueError("ridge must be nonnegative and finite")
    beta = np.zeros(len(vocabulary), dtype=float)
    state_index = {state: offset for offset, state in enumerate(STATE_IDS)}
    for _ in range(50):
        gradient = -ridge * beta
        information = ridge * np.eye(len(vocabulary))
        for row in rows:
            context = _context(row, vocabulary)
            observable = np.asarray([
                sustained_durability_observable(str(row["source_state"]), middle, terminal)
                for middle in STATE_IDS for terminal in STATE_IDS
            ])
            probabilities = _distribution(row, transition, beta, vocabulary)
            target = (
                state_index[row["intermediate_state"]] * len(STATE_IDS)
                + state_index[row["terminal_state"]]
            )
            expected = float(probabilities @ observable)
            gradient += context * (observable[target] - expected)
            variance = float(probabilities @ (observable - expected) ** 2)
            information += variance * np.outer(context, context)
        step = np.linalg.solve(information, gradient)
        beta = np.clip(beta + step, -12.0, 12.0)
        if float(np.max(np.abs(step), initial=0.0)) <= 1e-10:
            break
    return beta


def _shuffle(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issuers = sorted({str(row["entity_id"]) for row in rows})
    if len(issuers) < 2:
        return [dict(row) for row in rows]
    representative = {
        issuer: next(row for row in rows if str(row["entity_id"]) == issuer)
        for issuer in issuers
    }
    donor = {issuer: issuers[(index + 1) % len(issuers)] for index, issuer in enumerate(issuers)}
    return [{
        **dict(row),
        "mechanism_phenotype_sha256s": list(
            representative[donor[str(row["entity_id"])]]
            ["mechanism_phenotype_sha256s"]
        ),
        "interaction_phenotype_sha256s": list(
            representative[donor[str(row["entity_id"])]]
            ["interaction_phenotype_sha256s"]
        ),
    } for row in rows]


def _score(
    rows: Sequence[Mapping[str, Any]], transition: Sequence[Sequence[float]],
    bag_beta: np.ndarray, bag_vocab: Sequence[str], structured_beta: np.ndarray,
    structured_vocab: Sequence[str], shuffled_rows: Sequence[Mapping[str, Any]],
    shuffled_beta: np.ndarray,
) -> dict[str, dict[str, float]]:
    state_index = {state: offset for offset, state in enumerate(STATE_IDS)}
    losses = defaultdict(lambda: {"cross_entropy": [], "brier": []})
    for row, shuffled in zip(rows, shuffled_rows, strict=True):
        target = (
            state_index[row["intermediate_state"]] * len(STATE_IDS)
            + state_index[row["terminal_state"]]
        )
        models = {
            "directed_markov": _path_prior(str(row["source_state"]), transition),
            "bag_of_identical_leaves": _distribution(row, transition, bag_beta, bag_vocab),
            "integrated_choice_system": _distribution(
                row, transition, structured_beta, structured_vocab,
            ),
            "issuer_clustered_shuffle": _distribution(
                shuffled, transition, shuffled_beta, structured_vocab,
            ),
        }
        for model_id, probabilities in models.items():
            cross_entropy, brier = _loss(probabilities, target)
            losses[model_id]["cross_entropy"].append(cross_entropy)
            losses[model_id]["brier"].append(brier)
    return {
        model: {metric: math.fsum(values) / len(values) for metric, values in metrics.items()}
        for model, metrics in losses.items()
    }


def compile_strategy_program_representation_tournament(
    partitions: Mapping[str, Sequence[Mapping[str, Any]]], *,
    state_representation_sha256: str, pseudocount: float = 1.0, ridge: float = 1.0,
) -> dict[str, Any]:
    """Run a same-estimator structured-system versus identical-leaf ablation."""
    if set(partitions) != set(PARTITIONS):
        raise ValueError(f"program partitions must be exactly {PARTITIONS}")
    if len(state_representation_sha256) != 64:
        raise ValueError("state representation requires a sha256 identity")
    rows = {
        name: [_checked_row(row) for row in partitions[name]] for name in PARTITIONS
    }
    if any(not partition for partition in rows.values()):
        raise ValueError("program partitions cannot be empty")
    for name, partition in rows.items():
        counts = Counter(str(row["entity_id"]) for row in partition)
        required_issuers = MIN_UNSEEN_ISSUERS if name == "unseen_issuer" else MIN_FIT_ISSUERS
        if len(counts) < required_issuers or min(counts.values()) < MIN_PATHS_PER_ISSUER:
            raise ValueError(
                f"{name} requires {required_issuers} issuers with "
                f"{MIN_PATHS_PER_ISSUER} paths each"
            )
    visible_issuers = {row["entity_id"] for row in rows["visible"]}
    if visible_issuers & {row["entity_id"] for row in rows["unseen_issuer"]}:
        raise ValueError("unseen issuers overlap fit issuers")
    if {row["entity_id"] for row in rows["future_time"]} != visible_issuers:
        raise ValueError("future-time paths must cover the fit issuers")
    if not max(row["terminal_epoch"] for row in rows["visible"]) < min(
        row["source_epoch"] for row in rows["future_time"]
    ):
        raise ValueError("future-time paths must begin after visible paths end")

    bag_vocab = _vocabulary(rows["visible"], False)
    structured_vocab = _vocabulary(rows["visible"], True)
    if len(structured_vocab) == len(bag_vocab):
        raise ValueError("structured ablation requires observed interaction phenotypes")
    for partition in ("future_time", "unseen_issuer"):
        if not set(_vocabulary(rows[partition], False)) <= set(bag_vocab):
            raise ValueError("holdout introduces unseen leaf phenotypes")
        if not set(_vocabulary(rows[partition], True)) <= set(structured_vocab):
            raise ValueError("holdout introduces unseen interaction phenotypes")

    interaction_support = {
        partition: {
            interaction: len({
                str(row["entity_id"]) for row in rows[partition]
                if interaction in row["interaction_phenotype_sha256s"]
            })
            for interaction in sorted({
                str(value) for row in rows[partition]
                for value in row["interaction_phenotype_sha256s"]
            })
        }
        for partition in ("visible", "unseen_issuer")
    }
    shared_interactions = set(interaction_support["visible"]) & set(
        interaction_support["unseen_issuer"]
    )
    if not shared_interactions or any(
        interaction_support[partition][interaction] < MIN_INTERACTION_ISSUER_SUPPORT
        for partition in ("visible", "unseen_issuer")
        for interaction in shared_interactions
    ):
        raise ValueError(
            "each tested interaction requires four fit and four unseen issuers"
        )

    transition = _transition(rows["visible"], pseudocount)
    bag_beta = _fit(rows["visible"], transition, bag_vocab, ridge)
    structured_beta = _fit(rows["visible"], transition, structured_vocab, ridge)
    shuffled = {name: _shuffle(rows[name]) for name in PARTITIONS}
    shuffled_beta = _fit(shuffled["visible"], transition, structured_vocab, ridge)
    scores = {
        name: _score(
            rows[name], transition, bag_beta, bag_vocab, structured_beta,
            structured_vocab, shuffled[name], shuffled_beta,
        )
        for name in ("future_time", "unseen_issuer")
    }
    controls = (
        "directed_markov", "bag_of_identical_leaves", "issuer_clustered_shuffle",
    )
    issuer_win_rates = {}
    for name in ("future_time", "unseen_issuer"):
        issuer_scores = {}
        for issuer in sorted({str(row["entity_id"]) for row in rows[name]}):
            indices = [
                index for index, row in enumerate(rows[name])
                if str(row["entity_id"]) == issuer
            ]
            issuer_scores[issuer] = _score(
                [rows[name][index] for index in indices], transition,
                bag_beta, bag_vocab, structured_beta, structured_vocab,
                [shuffled[name][index] for index in indices], shuffled_beta,
            )
        issuer_win_rates[name] = {
            metric: {
                control: math.fsum(
                    issuer_score["integrated_choice_system"][metric]
                    < issuer_score[control][metric]
                    for issuer_score in issuer_scores.values()
                ) / len(issuer_scores)
                for control in controls
            }
            for metric in ("cross_entropy", "brier")
        }
    candidate_wins = all(
        partition[control][metric]
        - partition["integrated_choice_system"][metric] >= MIN_LOSS_IMPROVEMENT
        and issuer_win_rates[name][metric][control] >= MIN_ISSUER_WIN_RATE
        for name, partition in scores.items()
        for metric in ("cross_entropy", "brier")
        for control in controls
    )
    body = {
        "schema": TOURNAMENT_SCHEMA,
        "state_representation_sha256": state_representation_sha256,
        "estimator_identity": "ridge_conditional_logit_with_empirical_markov_offset",
        "ablation_identity": "known_interaction_transfer_vs_identical_leaf_phenotypes",
        "novel_recursive_recombination_tested": False,
        "representation_claim": (
            "tests whether previously observed interaction phenotypes transfer across "
            "later periods and unseen issuers"
        ),
        "syntactic_tree_depth_tested": False,
        "syntactic_tree_exclusion_reason": (
            "the strategy grammar uses an associative-commutative option-set quotient"
        ),
        "leaf_feature_count": len(bag_vocab),
        "interaction_feature_count": len(structured_vocab) - len(bag_vocab),
        "partition_row_counts": {name: len(value) for name, value in rows.items()},
        "fit_issuer_count": len(visible_issuers),
        "unseen_issuer_count": len({row["entity_id"] for row in rows["unseen_issuer"]}),
        "interaction_issuer_support": interaction_support,
        "scores": scores,
        "issuer_cluster_win_rates": issuer_win_rates,
        "promotion_floors": {
            "minimum_loss_improvement": MIN_LOSS_IMPROVEMENT,
            "minimum_issuer_win_rate": MIN_ISSUER_WIN_RATE,
            "minimum_interaction_issuers_per_partition": MIN_INTERACTION_ISSUER_SUPPORT,
        },
        "candidate_control_pass": candidate_wins,
        "status": "survived_representation_ablation" if candidate_wins else "recursive_credit_rejected",
        "predictive_law_authority": False,
        "causal_authority": False,
        "signal_authority": False,
        "capital_authority": False,
    }
    return {**body, "tournament_sha256": stable_sha256(body)}


def compile_strategy_program_representation_activation(
    recovery: Mapping[str, Any], path_input: Mapping[str, Any],
    prior: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Partition and run only after measurement and support gates pass."""
    input_sha = _checked_hash(path_input, INPUT_SCHEMA, "input_sha256")
    eligible = list(map(str, path_input.get("eligible_issuer_ids") or ()))
    blockers = [
        *([] if (
            recovery.get("schema") == "jaggedthoughts-max-caliber-recovery-v1"
            and (recovery.get("recovery_gate") or {}).get("status") == "recovery_gate_passed"
        ) else ["measurement_recovery_gate"]),
        *list(map(str, path_input.get("missing_inputs") or ())),
        *([] if len(eligible) >= MIN_FIT_ISSUERS + MIN_UNSEEN_ISSUERS
          else ["exact_program_adoption_path_support"]),
    ]
    base = {
        "schema": ACTIVATION_SCHEMA,
        "path_input_sha256": input_sha,
        "recovery_result_sha256": recovery.get("result_sha256"),
        "capital_authority": False,
    }
    if blockers:
        body = {**base, "status": "blocked_on_input_gates", "blockers": sorted(set(blockers)), "tournament": None}
        return {**body, "activation_sha256": stable_sha256(body)}

    prior_receipt = dict((prior or {}).get("partition_receipt") or {})
    if prior_receipt:
        unseen_issuers = set(map(str, prior_receipt.get("unseen_issuer_ids") or ()))
        fit_issuers = set(map(str, prior_receipt.get("fit_issuer_ids") or ()))
        if (
            len(unseen_issuers) != MIN_UNSEEN_ISSUERS
            or len(fit_issuers) != MIN_FIT_ISSUERS
            or not (unseen_issuers | fit_issuers) <= set(eligible)
        ):
            raise ValueError("frozen representation partition is no longer admissible")
    else:
        ordered = sorted(eligible, key=lambda entity: stable_sha256({
            "entity_id": entity, "partition": "strategy_program_representation",
        }))
        unseen_issuers = set(ordered[:MIN_UNSEEN_ISSUERS])
        fit_issuers = set(ordered[MIN_UNSEEN_ISSUERS:MIN_UNSEEN_ISSUERS + MIN_FIT_ISSUERS])
    rows = list(path_input.get("rows") or ())
    fit_rows = [row for row in rows if str(row["entity_id"]) in fit_issuers]
    selected = None
    cutoffs = (
        [str(prior_receipt["cutoff"])]
        if prior_receipt.get("cutoff") else
        sorted({str(row["source_epoch"]) for row in fit_rows})
    )
    for cutoff in cutoffs:
        visible = [row for row in fit_rows if str(row["terminal_epoch"]) < cutoff]
        future = [row for row in fit_rows if str(row["source_epoch"]) >= cutoff]
        if (
            {str(row["entity_id"]) for row in visible} == fit_issuers
            and {str(row["entity_id"]) for row in future} == fit_issuers
        ):
            selected = (cutoff, visible, future)
            break
    if selected is None:
        body = {**base, "status": "blocked_on_chronological_partition", "blockers": ["nonoverlapping_future_time_cutoff"], "tournament": None}
        return {**body, "activation_sha256": stable_sha256(body)}
    cutoff, visible, future = selected
    unseen = [row for row in rows if str(row["entity_id"]) in unseen_issuers]
    try:
        tournament = compile_strategy_program_representation_tournament(
            {"visible": visible, "future_time": future, "unseen_issuer": unseen},
            state_representation_sha256=stable_sha256({"state_ids": STATE_IDS}),
        )
    except ValueError as error:
        body = {**base, "status": "blocked_on_representation_support", "blockers": [str(error)], "tournament": None}
        return {**body, "activation_sha256": stable_sha256(body)}
    body = {
        **base,
        "status": tournament["status"],
        "blockers": [],
        "partition_receipt": {
            "cutoff": cutoff,
            "fit_issuer_ids": sorted(fit_issuers),
            "unseen_issuer_ids": sorted(unseen_issuers),
        },
        "tournament": tournament,
    }
    return {**body, "activation_sha256": stable_sha256(body)}


def compile_workspace_strategy_program_representation_activation(
    workspace: str | Path,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    summary = json.loads((
        root / "experiments/results/company-state-probability-current.json"
    ).read_text(encoding="utf-8"))
    flow = json.loads((root / str(summary["artifact_path"])).read_text(encoding="utf-8"))

    def read(directory: Path) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]

    path_input = compile_strategy_program_path_input(
        flow,
        read(root / "research_jobs/strategy_programs/requests"),
        read(root / "institutional_learning/strategy_programs/results"),
    )
    recovery = json.loads((
        root / "experiments/results/max-caliber-recovery.json"
    ).read_text(encoding="utf-8"))
    prior_path = root / "experiments/results/strategy-program-representation-ablation.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8")) if prior_path.is_file() else None
    result = compile_strategy_program_representation_activation(
        recovery, path_input, prior=prior,
    )
    input_destination = root / "experiments/results/strategy-program-path-input.json"
    input_destination.parent.mkdir(parents=True, exist_ok=True)
    input_temporary = input_destination.with_name(f".{input_destination.name}.tmp")
    input_temporary.write_text(
        json.dumps(path_input, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    input_temporary.replace(input_destination)
    destination = root / "experiments/results/strategy-program-representation-ablation.json"
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    temporary.replace(destination)
    return result


__all__ = [
    "ACTIVATION_SCHEMA", "INPUT_SCHEMA", "TOURNAMENT_SCHEMA",
    "compile_strategy_program_path_input",
    "compile_strategy_program_representation_activation",
    "compile_strategy_program_representation_tournament",
    "compile_workspace_strategy_program_representation_activation",
]
