"""Prospective checks for strategy bundles excluded by a frontier successor."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text, timestamp_key
from .strategy_options import RESULT_SCHEMA as FRONTIER_RESULT_SCHEMA


CONTRACT_SCHEMA = "jaggedthoughts-strategy-false-exclusion-contract-v1"
SETTLEMENT_SCHEMA = "jaggedthoughts-strategy-false-exclusion-settlement-v1"


def _digest(value: Any, label: str) -> str:
    digest = require_text(value, label)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _frontier(value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    frontier = dict(value)
    declared = _digest(frontier.pop("strategy_frontier_sha256", ""), "strategy frontier hash")
    if frontier.get("schema") != FRONTIER_RESULT_SCHEMA or stable_sha256(frontier) != declared:
        raise ValueError("strategy frontier identity is invalid")
    certificate = dict(frontier.get("choice_space_certificate") or {})
    certificate_hash = _digest(
        certificate.pop("choice_space_sha256", ""), "choice-space hash",
    )
    if stable_sha256(certificate) != certificate_hash:
        raise ValueError("choice-space certificate identity is invalid")
    return {**frontier, "strategy_frontier_sha256": declared}, {
        **certificate, "choice_space_sha256": certificate_hash,
    }


def _bundle(raw: Iterable[Any], vocabulary: set[str]) -> tuple[str, ...]:
    values = tuple(sorted(require_text(value, "strategy option id") for value in raw))
    if not values or len(values) != len(set(values)) or not set(values) <= vocabulary:
        raise ValueError("strategy bundle crosses or duplicates the option vocabulary")
    return values


def _feasible_bundles(certificate: Mapping[str, Any], vocabulary: set[str]) -> set[tuple[str, ...]]:
    return {
        _bundle(row.get("option_ids") or (), vocabulary)
        for row in certificate.get("feasible_bundles") or ()
        if isinstance(row, Mapping)
    }


def validate_strategy_false_exclusion_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    body = dict(value)
    declared = _digest(body.pop("contract_sha256", ""), "false-exclusion contract hash")
    if body.get("schema") != CONTRACT_SCHEMA or stable_sha256(body) != declared:
        raise ValueError("strategy false-exclusion contract identity is invalid")
    return {**body, "contract_sha256": declared}


def compile_strategy_false_exclusion_contract(
    parent: Mapping[str, Any],
    successor: Mapping[str, Any],
    *,
    accepted_predicate_sha256s: Iterable[str],
    predicate_source_ids: Iterable[str],
    evidence_cutoff: str,
    minimum_assessed_examples: int,
) -> dict[str, Any]:
    """Freeze the exact bundles removed by an additive frontier successor."""
    frozen_parent, parent_certificate = _frontier(parent)
    frozen_successor, successor_certificate = _frontier(successor)
    parent_vocabulary = set(map(str, parent_certificate.get("option_ids") or ()))
    successor_vocabulary = set(map(str, successor_certificate.get("option_ids") or ()))
    if not parent_vocabulary or parent_vocabulary != successor_vocabulary:
        raise ValueError("false-exclusion evaluation requires an unchanged option vocabulary")
    parent_bundles = _feasible_bundles(parent_certificate, parent_vocabulary)
    successor_bundles = _feasible_bundles(successor_certificate, parent_vocabulary)
    if not successor_bundles <= parent_bundles:
        raise ValueError("false-exclusion evaluation requires an additive successor")
    excluded = sorted(parent_bundles - successor_bundles)
    if not excluded:
        raise ValueError("false-exclusion evaluation requires a newly excluded bundle")
    predicate_hashes = sorted({
        _digest(value, "accepted predicate hash") for value in accepted_predicate_sha256s
    })
    predicate_sources = sorted({
        require_text(value, "predicate source id") for value in predicate_source_ids
    })
    if not predicate_hashes or not predicate_sources:
        raise ValueError("false-exclusion evaluation requires predicate hashes and sources")
    minimum = int(minimum_assessed_examples)
    if minimum < 1:
        raise ValueError("minimum assessed examples must be positive")
    body = {
        "schema": CONTRACT_SCHEMA,
        "parent_strategy_frontier_sha256": frozen_parent["strategy_frontier_sha256"],
        "successor_strategy_frontier_sha256": frozen_successor["strategy_frontier_sha256"],
        "parent_choice_space_sha256": parent_certificate["choice_space_sha256"],
        "successor_choice_space_sha256": successor_certificate["choice_space_sha256"],
        "evidence_cutoff": canonical_timestamp(evidence_cutoff, "false-exclusion evidence cutoff"),
        "accepted_predicate_sha256s": predicate_hashes,
        "predicate_source_ids": predicate_sources,
        "option_ids": sorted(parent_vocabulary),
        "excluded_bundles": [
            {"bundle_id": "|".join(bundle), "option_ids": list(bundle)}
            for bundle in excluded
        ],
        "minimum_assessed_examples": minimum,
        "research_claim_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "contract_sha256": stable_sha256(body)}


def settle_strategy_false_exclusion_contract(
    contract: Mapping[str, Any],
    admitted_world_examples: Sequence[Mapping[str, Any]],
    *,
    assessed_at: str,
) -> dict[str, Any]:
    """Assess post-cutoff admitted worlds without revising the frozen contract."""
    frozen = validate_strategy_false_exclusion_contract(contract)
    assessed = canonical_timestamp(assessed_at, "false-exclusion assessed_at")
    cutoff_key = timestamp_key(str(frozen["evidence_cutoff"]))
    if timestamp_key(assessed) <= cutoff_key:
        raise ValueError("false-exclusion assessment is not post-cutoff")
    vocabulary = set(map(str, frozen["option_ids"]))
    predicate_sources = set(map(str, frozen["predicate_source_ids"]))
    excluded = {str(row["bundle_id"]) for row in frozen["excluded_bundles"]}
    rows, seen = [], set()
    for raw in admitted_world_examples:
        example_id = require_text(raw.get("example_id"), "admitted-world example id")
        if example_id in seen:
            raise ValueError("admitted-world example ids must be unique")
        seen.add(example_id)
        bundle = _bundle(raw.get("option_ids") or (), vocabulary)
        observed = canonical_timestamp(raw.get("observed_at"), "admitted-world observed_at")
        available = canonical_timestamp(raw.get("available_at"), "admitted-world available_at")
        if timestamp_key(observed) <= cutoff_key:
            raise ValueError("admitted-world example is not post-cutoff")
        if timestamp_key(available) < timestamp_key(observed) or timestamp_key(available) > timestamp_key(assessed):
            raise ValueError("admitted-world availability is outside its assessment window")
        sources = sorted({
            require_text(value, "admitted-world source id")
            for value in raw.get("source_ids") or ()
        })
        if not sources or predicate_sources & set(sources):
            raise ValueError("admitted-world evidence is not source-independent")
        bundle_id = "|".join(bundle)
        rows.append({
            "example_id": example_id,
            "bundle_id": bundle_id,
            "option_ids": list(bundle),
            "observed_at": observed,
            "available_at": available,
            "source_ids": sources,
            "false_exclusion": bundle_id in excluded,
        })
    rows.sort(key=lambda row: row["example_id"])
    denominator = len(rows)
    numerator = sum(bool(row["false_exclusion"]) for row in rows)
    minimum = int(frozen["minimum_assessed_examples"])
    body = {
        "schema": SETTLEMENT_SCHEMA,
        "contract_sha256": frozen["contract_sha256"],
        "assessed_at": assessed,
        "status": "assessed" if denominator >= minimum else "abstained_insufficient_examples",
        "false_exclusion_numerator": numerator,
        "assessed_example_denominator": denominator,
        "false_exclusion_rate": numerator / denominator if denominator else None,
        "minimum_assessed_examples": minimum,
        "examples": rows,
        "research_claim_eligible": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "settlement_sha256": stable_sha256(body)}


__all__ = [
    "CONTRACT_SCHEMA", "SETTLEMENT_SCHEMA",
    "compile_strategy_false_exclusion_contract",
    "settle_strategy_false_exclusion_contract",
    "validate_strategy_false_exclusion_contract",
]
