"""Validated difficulty-replay receipts for governed result-card decks."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any, Mapping

from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.lean_source import (
    has_sorry,
    replace_decl_proof,
    resolve_theorem_target,
)
from ztare.leanmill.result_cards import (
    resolve_hidden_probe,
    result_card_replay_identity,
    validate_result_card_deck,
)
from ztare.leanmill.theory_ir import content_hash


REPLAY_ATTEMPT_SCHEMA = "leanmill.result_card_replay_attempt.v1"
REPLAY_SCHEMA = "leanmill.result_card_replay.v1"


def hidden_replay_probe(deck: Mapping[str, Any], card: Mapping[str, Any]) -> str:
    """Resolve a governed probe and hide exactly the selected proof."""

    probe = resolve_hidden_probe(deck, str(card["card_id"]))
    hidden = replace_decl_proof(probe, str(card["target_identity"]), "by sorry")
    identity = resolve_theorem_target(hidden, str(card["target_identity"]))
    if identity is None:
        raise ValueError("hidden-proof replay lost the target identity")
    block = hidden[identity.decl_start:identity.decl_end]
    if not has_sorry(block):
        raise ValueError("hidden-proof replay did not remove the target proof")
    return hidden


def hidden_replay_config(
    deck: Mapping[str, Any],
    *,
    attempts_per_card: int,
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    return {
        "deck_sha256": deck["deck_sha256"],
        "attempts_per_card": attempts_per_card,
        "model": model,
        "reasoning_effort": reasoning_effort,
    }


def _hidden_probe_sha256(
    deck: Mapping[str, Any], card: Mapping[str, Any]
) -> str:
    frozen = str(card.get("hidden_replay_probe_sha256") or "")
    if frozen:
        return frozen
    return hashlib.sha256(hidden_replay_probe(deck, card).encode()).hexdigest()


def _unsigned(row: Mapping[str, Any], digest: str = "receipt_sha256") -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != digest}


def validate_hidden_replay(
    deck: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[tuple[str, int], dict[str, Any]]:
    """Validate a complete replay receipt against its exact card deck."""

    validate_result_card_deck(deck)
    core = _unsigned(receipt)
    config = receipt.get("config")
    rows = receipt.get("attempts")
    if (
        receipt.get("schema") != REPLAY_SCHEMA
        or receipt.get("receipt_sha256") != content_hash(core)
        or not isinstance(config, Mapping)
        or receipt.get("config_sha256") != content_hash(dict(config))
        or config.get("deck_sha256") != deck["deck_sha256"]
        or not isinstance(rows, list)
    ):
        raise ValueError("invalid result-card replay envelope")
    attempts_per_card = config.get("attempts_per_card")
    if type(attempts_per_card) is not int or attempts_per_card < 1:
        raise ValueError("invalid result-card replay attempt count")
    cards = {str(card["card_id"]): card for card in deck["cards"]}
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise ValueError("malformed result-card replay attempt")
        row = dict(raw)
        row_core = _unsigned(row)
        card = cards.get(str(row.get("card_id") or ""))
        attempt = row.get("attempt")
        if (
            row.get("schema") != REPLAY_ATTEMPT_SCHEMA
            or row.get("receipt_sha256") != content_hash(row_core)
            or row.get("deck_sha256") != deck["deck_sha256"]
            or card is None
            or row.get("target_identity") != card["target_identity"]
            or type(attempt) is not int
            or not 0 <= attempt < attempts_per_card
        ):
            raise ValueError("invalid result-card replay attempt binding")
        hidden_probe_sha256 = _hidden_probe_sha256(deck, card)
        identity = {
            **dict(config),
            "card_id": card["card_id"],
            "attempt": attempt,
            "hidden_probe_sha256": hidden_probe_sha256,
        }
        key = (str(card["card_id"]), attempt)
        declared_hidden = row.get("hidden_probe_sha256")
        if (
            row.get("identity_sha256") != content_hash(identity)
            or (declared_hidden is not None and declared_hidden != hidden_probe_sha256)
            or key in indexed
        ):
            raise ValueError("result-card replay attempt identity mismatch")
        indexed[key] = row
    expected = len(cards) * attempts_per_card
    if len(indexed) != expected:
        raise ValueError("result-card replay does not cover its frozen deck")
    if (
        receipt.get("kernel_closed")
        != sum(row.get("outcome") == "kernel_closed" for row in indexed.values())
        or receipt.get("provider_calls")
        != sum(int(row.get("provider_call_charge", 0)) for row in indexed.values())
    ):
        raise ValueError("result-card replay aggregate counts do not match attempts")
    return indexed


def carry_hidden_replay(
    *,
    source_deck: Mapping[str, Any],
    source_receipt: Mapping[str, Any],
    successor_deck: Mapping[str, Any],
    artifact_dir: Path,
    attempts_per_card: int,
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    """Carry difficulty evidence across an objective-only deck transition."""

    old_rows = validate_hidden_replay(source_deck, source_receipt)
    old_config = dict(source_receipt["config"])
    if old_config != hidden_replay_config(
        source_deck,
        attempts_per_card=attempts_per_card,
        model=model,
        reasoning_effort=reasoning_effort,
    ):
        raise ValueError("source replay configuration does not match successor wave")
    validate_result_card_deck(successor_deck)
    by_identity: dict[str, Mapping[str, Any]] = {}
    for card in source_deck["cards"]:
        identity = content_hash(result_card_replay_identity(card))
        if identity in by_identity:
            raise ValueError("source deck has duplicate theorem replay identities")
        by_identity[identity] = card
    if len(successor_deck["cards"]) != len(source_deck["cards"]):
        raise ValueError("successor deck changes the theorem replay population")
    config = hidden_replay_config(
        successor_deck,
        attempts_per_card=attempts_per_card,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    rows: list[dict[str, Any]] = []
    for card in successor_deck["cards"]:
        prior_card = by_identity.get(content_hash(result_card_replay_identity(card)))
        if prior_card is None:
            raise ValueError("successor card lacks a compatible theorem replay identity")
        hidden_probe_sha256 = _hidden_probe_sha256(successor_deck, card)
        for attempt in range(attempts_per_card):
            prior = old_rows[(str(prior_card["card_id"]), attempt)]
            if prior.get("outcome") == "runtime_unavailable":
                raise ValueError("runtime-unavailable replay evidence cannot be carried")
            identity = {
                **config,
                "card_id": card["card_id"],
                "attempt": attempt,
                "hidden_probe_sha256": hidden_probe_sha256,
            }
            row_core = {
                **_unsigned(prior),
                "identity_sha256": content_hash(identity),
                "deck_sha256": successor_deck["deck_sha256"],
                "card_id": card["card_id"],
                "target_identity": card["target_identity"],
                "hidden_probe_sha256": hidden_probe_sha256,
                "carried_from": {
                    "deck_sha256": source_deck["deck_sha256"],
                    "aggregate_receipt_sha256": source_receipt["receipt_sha256"],
                    "attempt_receipt_sha256": prior["receipt_sha256"],
                    "compatibility": result_card_replay_identity(card),
                },
            }
            row = {**row_core, "receipt_sha256": content_hash(row_core)}
            target_slug = re.sub(
                r"[^A-Za-z0-9_.-]+", "_", str(card["target_identity"])
            ).strip("_")[-100:]
            path = artifact_dir / "hidden_replay" / target_slug / f"attempt_{attempt}" / "attempt_receipt.json"
            write_json_atomic(path, row)
            rows.append(row)
    aggregate_core = {
        "schema": REPLAY_SCHEMA,
        "config": config,
        "config_sha256": content_hash(config),
        "attempts": rows,
        "kernel_closed": sum(row["outcome"] == "kernel_closed" for row in rows),
        "provider_calls": sum(int(row.get("provider_call_charge", 0)) for row in rows),
        "authority": "calibration_only_no_theorem_interest_credit",
        "carried_from": {
            "deck_sha256": source_deck["deck_sha256"],
            "receipt_sha256": source_receipt["receipt_sha256"],
            "compatibility_authority": "difficulty_measurement_only",
        },
    }
    aggregate = {
        **aggregate_core,
        "receipt_sha256": content_hash(aggregate_core),
    }
    validate_hidden_replay(successor_deck, aggregate)
    write_json_atomic(artifact_dir / "hidden_replay.json", aggregate)
    return aggregate


__all__ = [
    "REPLAY_ATTEMPT_SCHEMA",
    "REPLAY_SCHEMA",
    "carry_hidden_replay",
    "hidden_replay_config",
    "hidden_replay_probe",
    "validate_hidden_replay",
]
