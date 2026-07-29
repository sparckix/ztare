"""Run frozen prior-art target predicates through registered theory adapters."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, ValidationError

from ztare.common.target_predicate import (
    RetrievedExample,
    TargetPredicateAdjudication,
    TargetPredicateContract,
    TargetPredicateReceipt,
)
from ztare.leanmill.theory_adapter_registry import (
    materialize_theory_adapter_capability,
    theory_adapter_capabilities,
)
from ztare.leanmill.theory_ir import content_hash


TARGET_PREDICATE_CONSEQUENCE_CONTRACT = (
    "target_predicate_replay_outcome_totality.v1"
)
RETRIEVED_TARGET_EXAMPLES_SCHEMA = "leanmill.retrieved_target_examples.v1"
TARGET_PREDICATE_REVIEW_REPLAY_SCHEMA = (
    "leanmill.target_predicate_review_replay.v1"
)


def _bind_contract(
    value: TargetPredicateContract | Mapping[str, Any],
) -> TargetPredicateContract:
    if isinstance(value, TargetPredicateContract):
        return value
    if isinstance(value, Mapping):
        return TargetPredicateContract.from_dict(value)
    raise TypeError("target predicate contract must be typed or an object")


def _bind_example(
    value: RetrievedExample | Mapping[str, Any],
) -> RetrievedExample:
    if isinstance(value, RetrievedExample):
        return value
    if isinstance(value, Mapping):
        return RetrievedExample.from_dict(value)
    raise TypeError("retrieved example must be typed or an object")


def evaluate_target_predicate_consequence(
    contract: TargetPredicateContract | Mapping[str, Any],
    retrieved_example: RetrievedExample | Mapping[str, Any],
    *,
    receipts_dir: str | Path | None = None,
) -> TargetPredicateReceipt:
    """Evaluate one source-bound example without granting a no-prior-art verdict."""

    bound_contract = _bind_contract(contract)
    bound_example = _bind_example(retrieved_example)
    if bound_contract.adapter_id != bound_example.adapter_id:
        raise ValueError("target predicate and retrieved example require one adapter")
    Draft202012Validator.check_schema(dict(bound_contract.input_schema))
    Draft202012Validator(dict(bound_contract.input_schema)).validate(
        dict(bound_example.normalized_input)
    )
    if bound_contract.evaluator_capability not in theory_adapter_capabilities(
        bound_contract.adapter_id
    ):
        adjudication = TargetPredicateAdjudication(
            outcome="unknown",
            reason_code="evaluator_capability_unavailable",
            reason=(
                "the registered adapter does not expose the frozen target-"
                "predicate evaluator"
            ),
            witness=None,
        )
    else:
        raw = materialize_theory_adapter_capability(
            bound_contract.adapter_id,
            bound_contract.evaluator_capability,
            contract=bound_contract.to_dict(),
            retrieved_example=bound_example.to_dict(),
        )
        if isinstance(raw, TargetPredicateAdjudication):
            adjudication = raw
        elif isinstance(raw, Mapping):
            adjudication = TargetPredicateAdjudication.from_dict(raw)
        else:
            raise TypeError(
                "registered target-predicate evaluator returned no typed result"
            )
    receipt = TargetPredicateReceipt(
        contract=bound_contract,
        retrieved_example=bound_example,
        adjudication=adjudication,
    )
    if receipts_dir is not None:
        from ztare.common.schema_routes import append_consequence_event

        append_consequence_event(
            receipts_dir,
            contract_id=TARGET_PREDICATE_CONSEQUENCE_CONTRACT,
            subject_id=receipt.subject_id,
            outcome=receipt.adjudication.outcome,
            event="produced",
            evidence_refs=tuple(
                dict.fromkeys(
                    (*bound_example.evidence_refs, *adjudication.evidence_refs)
                )
            ),
            idempotent=True,
        )
    return receipt


def consume_target_predicate_consequence(
    receipt: TargetPredicateReceipt | Mapping[str, Any],
    *,
    receipts_dir: str | Path | None = None,
    replay: bool = True,
) -> dict[str, Any]:
    """Replay the exact contract/example pair, then enter prior-art state."""

    bound = (
        receipt
        if isinstance(receipt, TargetPredicateReceipt)
        else TargetPredicateReceipt.from_dict(receipt)
        if isinstance(receipt, Mapping)
        else None
    )
    if bound is None:
        raise TypeError("target-predicate receipt must be typed or an object")
    if replay:
        expected = evaluate_target_predicate_consequence(
            bound.contract,
            bound.retrieved_example,
        )
        if expected.sha256 != bound.sha256:
            raise ValueError("target-predicate adapter replay differs from stored receipt")

    from ztare.common.schema_routes import consequence_contract

    transition = consequence_contract(
        TARGET_PREDICATE_CONSEQUENCE_CONTRACT
    ).transition_for(bound.adjudication.outcome)
    result_core = {
        "schema": "leanmill.target_predicate_state_transition.v1",
        "receipt_sha256": bound.sha256,
        "contract_sha256": bound.contract.sha256,
        "example_sha256": bound.retrieved_example.sha256,
        "outcome": bound.adjudication.outcome,
        "target_state": transition.target_state,
        "authority": "post_freeze_prior_art_interpretation_only",
        "novelty_status": (
            "overlap_detected"
            if bound.adjudication.outcome == "overlap"
            else "blocked_by_unknown"
        ),
    }
    if receipts_dir is not None:
        from ztare.common.schema_routes import append_consequence_event

        append_consequence_event(
            receipts_dir,
            contract_id=TARGET_PREDICATE_CONSEQUENCE_CONTRACT,
            subject_id=bound.subject_id,
            outcome=bound.adjudication.outcome,
            event="consumed",
            evidence_refs=(f"receipt:{bound.sha256}",),
            idempotent=True,
        )
    return result_core


def _review_source_urls(review: Mapping[str, Any]) -> set[str]:
    urls = {
        str(row.get("source_url") or "")
        for field in (
            "formula_matches", "implication_prior_art", "finite_witness_matches",
        )
        for row in review.get(field) or ()
        if isinstance(row, Mapping) and str(row.get("source_url") or "").strip()
    }
    coverage = review.get("search_coverage")
    if isinstance(coverage, Mapping):
        urls.update(
            str(row.get("source_url") or "")
            for row in coverage.get("anchor_sources") or ()
            if isinstance(row, Mapping) and str(row.get("source_url") or "").strip()
        )
        urls.update(
            str(url)
            for row in coverage.get("search_legs") or ()
            if isinstance(row, Mapping)
            for url in row.get("evidence_urls") or ()
            if str(url).strip()
        )
    return urls


def replay_review_target_predicates(
    result_packet: Mapping[str, Any],
    review: Mapping[str, Any],
    examples_payload: Mapping[str, Any] | None,
    *,
    receipts_dir: str | Path | None = None,
) -> dict[str, Any] | None:
    """First-fire optional target replay from a frozen result packet.

    Campaigns without a target-predicate contract return ``None``. When a
    contract is frozen, every absence of usable examples is a typed ``unknown``
    rather than evidence that the target is absent from prior art.
    """

    frozen = result_packet.get("target_predicate_contract")
    if not isinstance(frozen, Mapping):
        if examples_payload:
            raise ValueError("retrieved target examples have no frozen predicate")
        return None
    frozen_row = dict(frozen)
    expected_contract_sha = str(frozen_row.pop("contract_sha256", ""))
    contract = TargetPredicateContract.from_dict(frozen_row)
    if contract.sha256 != expected_contract_sha:
        raise ValueError("result packet target-predicate digest mismatch")
    if contract.context_hash != str(result_packet.get("context_hash") or ""):
        raise ValueError("target-predicate contract belongs to another context")

    failures: list[dict[str, str]] = []
    receipts: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    rows: list[Any] = []
    if examples_payload is None:
        failures.append({
            "reason_code": "retrieved_examples_missing",
            "reason": "no normalized retrieved-example batch was available",
        })
    elif (
        examples_payload.get("schema") != RETRIEVED_TARGET_EXAMPLES_SCHEMA
        or examples_payload.get("contract_sha256") != contract.sha256
        or not isinstance(examples_payload.get("examples"), list)
    ):
        failures.append({
            "reason_code": "retrieved_examples_identity_invalid",
            "reason": "the retrieved-example batch does not bind the frozen contract",
        })
    else:
        rows = list(examples_payload["examples"])
        if not rows:
            failures.append({
                "reason_code": "retrieved_examples_empty",
                "reason": "the review supplied no normalized example to replay",
            })

    source_urls = _review_source_urls(review)
    for index, raw in enumerate(rows):
        try:
            if not isinstance(raw, Mapping):
                raise TypeError("retrieved example is not an object")
            example = RetrievedExample.from_dict(raw)
            if example.source_url not in source_urls:
                raise ValueError("example source is outside the executed review graph")
            receipt = evaluate_target_predicate_consequence(
                contract,
                example,
            )
            transition = consume_target_predicate_consequence(
                receipt,
            )
        except (KeyError, TypeError, ValueError, RuntimeError, ValidationError) as exc:
            failures.append({
                "reason_code": "retrieved_example_replay_invalid",
                "reason": f"example {index}: {type(exc).__name__}:{exc}",
            })
            continue
        if receipts_dir is not None:
            from ztare.common.schema_routes import append_consequence_event

            event_fields = {
                "receipts_dir": receipts_dir,
                "contract_id": TARGET_PREDICATE_CONSEQUENCE_CONTRACT,
                "subject_id": receipt.subject_id,
                "outcome": receipt.adjudication.outcome,
                "idempotent": True,
            }
            append_consequence_event(
                event="produced",
                evidence_refs=tuple(
                    dict.fromkeys(
                        (
                            *receipt.retrieved_example.evidence_refs,
                            *receipt.adjudication.evidence_refs,
                        )
                    )
                ),
                **event_fields,
            )
            append_consequence_event(
                event="consumed",
                evidence_refs=(f"receipt:{receipt.sha256}",),
                **event_fields,
            )
        receipts.append(receipt.to_dict())
        transitions.append(transition)

    outcome = (
        "overlap"
        if any(
            row.get("outcome") == "overlap"
            for row in transitions
        )
        else "unknown"
    )
    core = {
        "schema": TARGET_PREDICATE_REVIEW_REPLAY_SCHEMA,
        "packet_sha256": str(result_packet.get("packet_sha256") or ""),
        "contract_sha256": contract.sha256,
        "outcome": outcome,
        "receipt_count": len(receipts),
        "receipts": receipts,
        "transitions": transitions,
        "failures": failures,
        "claim_boundary": (
            "retrieved-example overlap or unknown only; unknown blocks an "
            "absence assessment and no outcome certifies corpus completeness"
        ),
    }
    return {**core, "replay_sha256": content_hash(core)}


__all__ = [
    "RETRIEVED_TARGET_EXAMPLES_SCHEMA",
    "TARGET_PREDICATE_CONSEQUENCE_CONTRACT",
    "TARGET_PREDICATE_REVIEW_REPLAY_SCHEMA",
    "consume_target_predicate_consequence",
    "evaluate_target_predicate_consequence",
    "replay_review_target_predicates",
]
