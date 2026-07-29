from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ztare.leanmill.result_cards import (
    build_result_card_deck,
    certificate_statement,
    resolve_objective_source_text,
    resolve_hidden_proof,
    validate_result_card_deck,
)
from ztare.leanmill.governed_ratification import normalized_target_signature
from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation


TARGET = "Demo.seed"


def _certificate(*, ts: str, proof: str, malformed: bool = False) -> dict:
    declaration = (
        "theorem seed (P Q R : Prop) (h₁ : P → Q) (h₂ : Q → R) : P → R := "
        + proof
    )
    if malformed:
        declaration = declaration.replace(" := ", " ")
    probe = f"""import Mathlib

namespace Demo

def marker : Nat := 1

{declaration}

end Demo
"""
    signature_hash = hashlib.sha256(
        normalized_target_signature(probe, TARGET).encode()
    ).hexdigest()
    governance = {
        "probe_match": "carried_exact_artifact" if not malformed else "reconstructed",
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
    return {
        "ts": ts,
        "target": TARGET,
        "outcome": "closed",
        "proof_text": proof,
        "recompilable_probe": probe,
        "recompilable_probe_reconstructed": malformed,
        "checker": "lean_lake",
        "matched_negative_control": {"available": True, "passed": True},
        "posed_target_signature_sha256": signature_hash,
        "closed_target_signature_sha256": signature_hash,
        "solver_validation": validation,
        "governance": governance,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_result_card_selects_governed_carried_source_and_hides_proof(tmp_path: Path) -> None:
    ledger = tmp_path / "certs.jsonl"
    old = _certificate(ts="2026-01-01T00:00:00Z", proof="by intro h; exact h₂ (h₁ h)")
    malformed = _certificate(
        ts="2027-01-01T00:00:00Z",
        proof="by intro h; exact h₂ (h₁ h)",
        malformed=True,
    )
    _write_jsonl(ledger, [old, malformed])
    source = tmp_path / "source.md"
    source.write_text("Frozen source statement.\n", encoding="utf-8")

    deck = build_result_card_deck(
        ledger_path=ledger,
        target_names=[TARGET],
        source_refs_by_target={TARGET: [source]},
        objective="Characterize exactly when the construction reconstructs.",
        objective_source_refs=[source],
    )

    validate_result_card_deck(deck)
    card = deck["cards"][0]
    assert card["target_identity"] == TARGET
    assert card["hidden_proof_ref"]["line_number"] == 1
    assert "proof_text" not in card
    assert ":=" not in card["lean_statement"]
    assert resolve_hidden_proof(deck, card["card_id"]) == old["proof_text"]
    objective_receipt = deck["objective_source_receipts"][0]
    assert objective_receipt["content"] == "Frozen source statement.\n"


def test_result_card_objective_source_bytes_survive_later_file_edit(
    tmp_path: Path,
) -> None:
    ledger = tmp_path / "certs.jsonl"
    cert = _certificate(ts="2026-01-01T00:00:00Z", proof="by intro h; exact h₂ (h₁ h)")
    _write_jsonl(ledger, [cert])
    source = tmp_path / "source.md"
    source.write_text("Frozen source statement.\n", encoding="utf-8")
    deck = build_result_card_deck(
        ledger_path=ledger,
        target_names=[TARGET],
        source_refs_by_target={TARGET: [source]},
        objective="Characterize exactly when the construction reconstructs.",
        objective_source_refs=[source],
    )
    receipt = deck["objective_source_receipts"][0]
    source.write_text("Successor source statement.\n", encoding="utf-8")

    assert resolve_objective_source_text(receipt) == "Frozen source statement.\n"


def test_legacy_result_card_source_change_fails_instead_of_changing_prompt(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.md"
    source.write_text("Frozen source statement.\n", encoding="utf-8")
    receipt = {
        "ref": str(source),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    source.write_text("Changed bytes.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source changed after deck freeze"):
        resolve_objective_source_text(receipt)


def test_result_card_qualified_statement_parser_rejects_missing_proof_boundary() -> None:
    good = _certificate(ts="2026-01-01T00:00:00Z", proof="by intro h; exact h₂ (h₁ h)")
    bad = _certificate(
        ts="2026-01-01T00:00:00Z",
        proof="by intro h; exact h₂ (h₁ h)",
        malformed=True,
    )
    assert certificate_statement(good).startswith("(P Q R : Prop)")
    assert certificate_statement(bad) == ""


@pytest.mark.parametrize(
    ("mutation",),
    [
        ("missing_governance_availability",),
        ("missing_axiom_receipt",),
        ("changed_signature_hash",),
    ],
)
def test_result_card_rejects_incomplete_or_unbound_authority(
    tmp_path: Path,
    mutation: str,
) -> None:
    cert = _certificate(
        ts="2026-01-01T00:00:00Z",
        proof="by intro h; exact h₂ (h₁ h)",
    )
    if mutation == "missing_governance_availability":
        del cert["solver_validation"]["receipts"][
            "governance_kernel_receipt"
        ]["available"]
    elif mutation == "missing_axiom_receipt":
        del cert["solver_validation"]["receipts"]["axiom_allowlist_receipt"]
    else:
        cert["closed_target_signature_sha256"] = "0" * 64
    ledger = tmp_path / "certs.jsonl"
    _write_jsonl(ledger, [cert])
    source = tmp_path / "source.md"
    source.write_text("Frozen source statement.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not card-admissible"):
        build_result_card_deck(
            ledger_path=ledger,
            target_names=[TARGET],
            source_refs_by_target={TARGET: [source]},
            objective="Characterize exactly when the construction reconstructs.",
            objective_source_refs=[source],
        )


def test_result_card_frozen_ledger_reference_fails_after_mutation(tmp_path: Path) -> None:
    ledger = tmp_path / "certs.jsonl"
    cert = _certificate(ts="2026-01-01T00:00:00Z", proof="by intro h; exact h₂ (h₁ h)")
    _write_jsonl(ledger, [cert])
    source = tmp_path / "source.md"
    source.write_text("Frozen source statement.\n", encoding="utf-8")
    deck = build_result_card_deck(
        ledger_path=ledger,
        target_names=[TARGET],
        source_refs_by_target={TARGET: [source]},
        objective="Characterize exactly when the construction reconstructs.",
        objective_source_refs=[source],
    )
    card_id = deck["cards"][0]["card_id"]
    ledger.write_text(ledger.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="ledger changed"):
        resolve_hidden_proof(deck, card_id)
