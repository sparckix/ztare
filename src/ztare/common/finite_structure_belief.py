"""Finite model beliefs and posterior-predictive question value.

The caller owns model construction and predictive probabilities.  This module
only freezes their identity, applies categorical Bayes updates, and prices the
remaining finite question menu with the shared information-yield primitive.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .equivariance import stable_sha256
from .information_yield_pricing import posterior_predictive_information_bits


SCHEMA = "ztare.finite_structure_belief.v1"


def _text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} must be nonempty")
    return result


def _weights(values: Mapping[str, Any], model_ids: Sequence[str]) -> dict[str, float]:
    if set(values) != set(model_ids):
        raise ValueError("model weights must cover the frozen model set exactly")
    result = {model_id: float(values[model_id]) for model_id in model_ids}
    if any(not math.isfinite(value) or value < 0 for value in result.values()):
        raise ValueError("model weights must be finite and nonnegative")
    total = sum(result.values())
    if total <= 0:
        raise ValueError("model weights must have positive mass")
    return {model_id: result[model_id] / total for model_id in model_ids}


def _distribution(value: Mapping[str, Any]) -> dict[str, float]:
    result = {_text(key, "outcome id"): float(mass) for key, mass in value.items()}
    if len(result) != len(value):
        raise ValueError("predictive outcome ids collide after canonicalization")
    if not result or any(not math.isfinite(mass) or mass < 0 for mass in result.values()):
        raise ValueError("predictive distributions require finite nonnegative mass")
    total = sum(result.values())
    if total <= 0:
        raise ValueError("predictive distributions require positive mass")
    return {key: result[key] / total for key in sorted(result)}


def validate_finite_structure_belief(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = _text(body.pop("belief_sha256", ""), "finite belief hash")
    if body.get("schema") != SCHEMA or stable_sha256(body) != declared:
        raise ValueError("finite structure belief identity is invalid")
    return {**body, "belief_sha256": declared}


def compile_finite_structure_belief(
    *,
    evidence_epoch: str,
    model_ids: Sequence[str],
    question_predictives: Mapping[str, Mapping[str, Mapping[str, Any]]],
    prior_weights: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze a finite model set and its categorical question predictions."""

    models = tuple(sorted({_text(value, "model id") for value in model_ids}))
    if len(models) != len(model_ids) or not models:
        raise ValueError("finite belief requires unique model ids")
    weights = _weights(
        prior_weights or {model_id: 1.0 for model_id in models}, models,
    )
    questions = []
    question_ids: set[str] = set()
    for raw_question_id, raw_rows in question_predictives.items():
        question_id = _text(raw_question_id, "question id")
        if question_id in question_ids:
            raise ValueError("question ids collide after canonicalization")
        question_ids.add(question_id)
        if set(raw_rows) != set(models):
            raise ValueError("every question must cover the frozen model set")
        predictions = {
            model_id: _distribution(raw_rows[model_id]) for model_id in models
        }
        alphabet = sorted({key for row in predictions.values() for key in row})
        questions.append({
            "question_id": question_id,
            "outcome_alphabet": alphabet,
            "predictive_distributions": predictions,
        })
    questions.sort(key=lambda row: row["question_id"])
    if not questions:
        raise ValueError("finite belief requires at least one question")
    body = {
        "schema": SCHEMA,
        "evidence_epoch": _text(evidence_epoch, "evidence epoch"),
        "model_ids": list(models),
        "weights": weights,
        "weight_semantics": (
            "declared_prior_weights" if prior_weights is not None
            else "uniform_design_weights"
        ),
        "questions": questions,
        "observation_history": [],
        "status": "prior_frozen",
        "parent_belief_sha256": None,
    }
    return {**body, "belief_sha256": stable_sha256(body)}


def rank_finite_structure_questions(
    belief: Mapping[str, Any], *, costs: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Rank unobserved questions by posterior-predictive information per cost."""

    frozen = validate_finite_structure_belief(belief)
    if frozen.get("status") == "committee_refuted":
        raise ValueError(
            "committee-refuted belief is terminal; open a new model-set epoch"
        )
    model_ids = list(map(str, frozen["model_ids"]))
    weights = [float(frozen["weights"][model_id]) for model_id in model_ids]
    observed = {
        str(row["question_id"]) for row in frozen.get("observation_history") or ()
    }
    rows = []
    for question in frozen["questions"]:
        question_id = str(question["question_id"])
        if question_id in observed:
            continue
        cost = float((costs or {}).get(question_id, 1.0))
        if not math.isfinite(cost) or cost <= 0:
            raise ValueError("question costs must be finite and positive")
        bits = posterior_predictive_information_bits(
            [question["predictive_distributions"][model_id] for model_id in model_ids],
            weights,
        )
        rows.append({
            "question_id": question_id,
            "expected_information_bits": round(bits, 12),
            "cost_units": cost,
            "information_bits_per_cost": round(bits / cost, 12),
        })
    return sorted(
        rows,
        key=lambda row: (-row["information_bits_per_cost"], row["question_id"]),
    )


def update_finite_structure_belief(
    belief: Mapping[str, Any], *, question_id: str, observed_outcome: str,
    observed_at: str, evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Return the next belief after one later, source-bound observation."""

    frozen = validate_finite_structure_belief(belief)
    if frozen.get("status") == "committee_refuted":
        raise ValueError(
            "committee-refuted belief is terminal; open a new model-set epoch"
        )
    question_key = _text(question_id, "observed question id")
    outcome = _text(observed_outcome, "observed outcome")
    question = next(
        (row for row in frozen["questions"] if row["question_id"] == question_key), None,
    )
    if question is None or outcome not in question["outcome_alphabet"]:
        raise ValueError("observation is outside the frozen question contract")
    if question_key in {
        str(row["question_id"]) for row in frozen.get("observation_history") or ()
    }:
        raise ValueError("finite belief question is already observed")
    refs = sorted({_text(value, "evidence ref") for value in evidence_refs})
    if not refs:
        raise ValueError("finite belief update requires evidence refs")
    prior = {key: float(value) for key, value in frozen["weights"].items()}
    likelihoods = {
        model_id: float(
            question["predictive_distributions"][model_id].get(outcome, 0.0)
        )
        for model_id in frozen["model_ids"]
    }
    evidence_mass = sum(prior[key] * likelihoods[key] for key in prior)
    posterior = (
        {key: prior[key] * likelihoods[key] / evidence_mass for key in prior}
        if evidence_mass > 0 else prior
    )
    observation = {
        "question_id": question_key,
        "observed_outcome": outcome,
        "observed_at": _text(observed_at, "observed at"),
        "evidence_refs": refs,
        "predictive_evidence_mass": evidence_mass,
        "likelihoods": likelihoods,
    }
    body = {
        key: value for key, value in frozen.items() if key != "belief_sha256"
    }
    body.update({
        "weights": posterior,
        "weight_semantics": (
            "normalized_likelihood_posterior" if evidence_mass > 0
            else "prior_retained_after_committee_refutation"
        ),
        "observation_history": [*frozen.get("observation_history", ()), observation],
        "status": "updated" if evidence_mass > 0 else "committee_refuted",
        "parent_belief_sha256": frozen["belief_sha256"],
    })
    return {**body, "belief_sha256": stable_sha256(body)}


__all__ = [
    "SCHEMA", "compile_finite_structure_belief", "rank_finite_structure_questions",
    "update_finite_structure_belief", "validate_finite_structure_belief",
]
