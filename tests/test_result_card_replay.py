from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from ztare.leanmill.result_card_replay import (
    carry_hidden_replay,
    hidden_replay_config,
    hidden_replay_probe,
    validate_hidden_replay,
)
from ztare.leanmill.result_cards import build_result_card_deck
from ztare.leanmill.governed_ratification import normalized_target_signature
from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation
from ztare.leanmill.theory_ir import content_hash


TARGET = "Demo.seed"


def _deck(tmp_path: Path, *, epoch: int, objective_source: str) -> dict:
    proof = "by intro h; exact h"
    probe = f"""import Mathlib

namespace Demo
theorem seed (P : Prop) : P → P := {proof}
end Demo
"""
    signature_hash = hashlib.sha256(
        normalized_target_signature(probe, TARGET).encode()
    ).hexdigest()
    governance = {
        "probe_match": "carried_exact_artifact",
        "governance_kernel": {
            "available": True,
            "passed": True,
            "policy_profile": "target_ratification",
            "required_authorities": sorted(TARGET_GOVERNANCE_AUTHORITIES),
            "authority_disposition": {
                authority: "passed"
                for authority in TARGET_GOVERNANCE_AUTHORITIES
            },
            "authority_roster_sha256": (
                TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
            ),
        },
        "statement_integrity": {"ok": True},
    }
    validation = finalize_solver_validation({
        "credit_ready_at_solver_layer": True,
        "positive_axiom_receipt_required": True,
        "discriminating_mnc_required": True,
        "receipts": {
            "kernel_compile_receipt": {"available": True, "passed": True},
            "matched_negative_control_receipt": {
                "available": True,
                "passed": True,
            },
            "axiom_allowlist_receipt": {"available": True, "passed": True},
            "governance_kernel_receipt": {
                "available": True,
                "passed": True,
            },
        },
    }, governance)
    cert = {
        "ts": "2026-07-17T00:00:00Z",
        "target": TARGET,
        "outcome": "closed",
        "proof_text": proof,
        "recompilable_probe": probe,
        "checker": "lean_lake",
        "matched_negative_control": {"available": True, "passed": True},
        "posed_target_signature_sha256": signature_hash,
        "closed_target_signature_sha256": signature_hash,
        "solver_validation": validation,
        "governance": governance,
    }
    ledger = tmp_path / "certs.jsonl"
    ledger.write_text(json.dumps(cert) + "\n", encoding="utf-8")
    source = tmp_path / "source.md"
    source.write_text(objective_source, encoding="utf-8")
    return build_result_card_deck(
        ledger_path=ledger,
        target_names=[TARGET],
        source_refs_by_target={TARGET: [ledger]},
        objective="Characterize the extraction fiber.",
        objective_source_refs=[source],
        epoch=epoch,
    )


def _replay(deck: dict) -> dict:
    config = hidden_replay_config(
        deck, attempts_per_card=2, model="test-model", reasoning_effort="low"
    )
    card = deck["cards"][0]
    hidden = hidden_replay_probe(deck, card)
    rows = []
    for attempt, outcome in enumerate(("not_closed", "kernel_closed")):
        identity = {
            **config,
            "card_id": card["card_id"],
            "attempt": attempt,
            "hidden_probe_sha256": hashlib.sha256(hidden.encode()).hexdigest(),
        }
        core = {
            "schema": "leanmill.result_card_replay_attempt.v1",
            "identity_sha256": content_hash(identity),
            "deck_sha256": deck["deck_sha256"],
            "card_id": card["card_id"],
            "target_identity": TARGET,
            "attempt": attempt,
            "model": "test-model",
            "reasoning_effort": "low",
            "outcome": outcome,
            "proof_sha256": "",
            "compile_error_sha256": "",
            "attempt_summary": "fixture",
            "provider_call_charge": 1,
            "call_receipt_sha256": f"call-{attempt}",
            "infrastructure_error": "",
            "authority": "difficulty_measurement_only",
        }
        rows.append({**core, "receipt_sha256": content_hash(core)})
    core = {
        "schema": "leanmill.result_card_replay.v1",
        "config": config,
        "config_sha256": content_hash(config),
        "attempts": rows,
        "kernel_closed": 1,
        "provider_calls": 2,
        "authority": "calibration_only_no_theorem_interest_credit",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def test_replay_carries_across_objective_epoch_without_new_calls(tmp_path: Path) -> None:
    source = _deck(tmp_path, epoch=0, objective_source="old interpretation\n")
    replay = _replay(source)
    successor = _deck(tmp_path, epoch=1, objective_source="corrected interpretation\n")
    (tmp_path / "certs.jsonl").write_text("{}\n", encoding="utf-8")

    carried = carry_hidden_replay(
        source_deck=source,
        source_receipt=replay,
        successor_deck=successor,
        artifact_dir=tmp_path / "successor",
        attempts_per_card=2,
        model="test-model",
        reasoning_effort="low",
    )

    indexed = validate_hidden_replay(successor, carried)
    assert len(indexed) == 2
    assert carried["provider_calls"] == 2
    assert carried["kernel_closed"] == 1
    assert carried["carried_from"]["receipt_sha256"] == replay["receipt_sha256"]
    assert all(row["deck_sha256"] == successor["deck_sha256"] for row in indexed.values())


def test_replay_carry_rejects_changed_theorem_identity(tmp_path: Path) -> None:
    source = _deck(tmp_path, epoch=0, objective_source="old interpretation\n")
    replay = _replay(source)
    successor = _deck(tmp_path, epoch=1, objective_source="corrected interpretation\n")
    changed = deepcopy(successor)
    card_core = {
        key: value for key, value in changed["cards"][0].items() if key != "card_sha256"
    }
    card_core["statement_sha256"] = "0" * 64
    changed["cards"][0] = {**card_core, "card_sha256": content_hash(card_core)}
    deck_core = {key: value for key, value in changed.items() if key != "deck_sha256"}
    changed = {**deck_core, "deck_sha256": content_hash(deck_core)}

    with pytest.raises(ValueError, match="compatible theorem replay identity"):
        carry_hidden_replay(
            source_deck=source,
            source_receipt=replay,
            successor_deck=changed,
            artifact_dir=tmp_path / "successor",
            attempts_per_card=2,
            model="test-model",
            reasoning_effort="low",
        )
