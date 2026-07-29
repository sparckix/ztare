from __future__ import annotations

from copy import deepcopy

import pytest

from ztare.leanmill.target_curriculum import (
    TARGET_STATEMENT_CHECKER_OWNER,
    build_target_conjecture_wave,
    guide_questions,
    normalize_conjecturer_output,
    preflight_target_conjecture_wave,
    target_conjecture_output_schema,
)
from ztare.leanmill.theory_ir import content_hash


def _deck() -> dict:
    card_core = {
        "card_schema": "leanmill.result_card.v1",
        "card_id": "result-card:one",
        "source_kind": "source_bound",
        "source_receipts": [{"ref": "source.md", "sha256": "a" * 64}],
        "source_sha256": "b" * 64,
        "target_identity": "Demo.seed",
        "context_sha256": "c" * 64,
        "epoch": 0,
        "lean_statement": "(P Q R : Prop) (h₁ : P → Q) (h₂ : Q → R) : P → R",
        "statement_sha256": "d" * 64,
        "hidden_proof_ref": {
            "ledger_sha256": "e" * 64,
            "line_number": 1,
            "certificate_sha256": "f" * 64,
        },
        "proof_sha256": "1" * 64,
        "recompilable_probe_sha256": "2" * 64,
        "statement_faithfulness_receipt": {
            "status": "source_bound_for_independent_review",
            "source_sha256": "b" * 64,
        },
        "kernel_receipt": {},
        "difficulty_receipt": {"status": "pending_hidden_proof_replay", "attempts": []},
        "usefulness_receipt": {"status": "pending_target_replay"},
        "golf_variants": [],
    }
    card = {**card_core, "card_sha256": content_hash(card_core)}
    deck_core = {
        "schema": "leanmill.result_card_deck.v1",
        "ledger_ref": "certs.jsonl",
        "ledger_sha256": "e" * 64,
        "objective": "Characterize the target.",
        "objective_sha256": "3" * 64,
        "objective_source_receipts": [{"ref": "source.md", "sha256": "a" * 64}],
        "context_sha256": "4" * 64,
        "epoch": 0,
        "cards": [card],
        "proof_visibility": "hidden_by_default_resolvable_only_from_frozen_ledger",
    }
    return {**deck_core, "deck_sha256": content_hash(deck_core)}


def _candidate(signature: str) -> dict:
    return {
        "title": "A target edge",
        "formal_status": "lean_candidate",
        "candidate_family": "hypothesis_minimization",
        "mathematical_statement": "A weaker hypothesis still implies the target condition.",
        "lean_signature": signature,
        "required_imports": ["Mathlib"],
        "formal_context": {
            "open_namespaces": [],
            "enclosing_namespace": "",
        },
        "dependencies": ["Demo.seed"],
        "target_edge": "Removes one candidate hypothesis from the characterization.",
        "expected_direction": "sufficient",
        "falsification_plan": "Search finite structures of orders two through five.",
        "recurrence_risk": "Could be a renamed transitivity consequence.",
        "scope_limits": "Only the stated abstract setting.",
        "capability_request": "",
    }


def test_target_conjecture_schema_is_codex_strict() -> None:
    schema = target_conjecture_output_schema(["Demo.seed"])
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    item = schema["properties"]["candidates"]["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == set(item["properties"])


def test_target_candidate_gets_host_identity_and_guide_projection() -> None:
    deck = _deck()
    output = {
        "candidates": [_candidate("(P Q : Prop) (h : P ↔ Q) : Q ↔ P")],
        "no_candidate_reason": "",
    }
    rows = normalize_conjecturer_output(deck, deck["cards"][0], output)
    assert rows[0]["candidate_id"].startswith("target-conjecture:")
    assert rows[0]["recurrence_status"] == "not_exact_card_statement"
    wave = build_target_conjecture_wave(deck, [rows])
    seen: list[str] = []

    def compile_statement(source, lean_root):
        seen.append(source)
        assert str(lean_root).endswith("ztare_proofs")
        return True

    preflight = preflight_target_conjecture_wave(
        wave,
        lean_root="/tmp/ztare_proofs",
        compile_fn=compile_statement,
    )
    questions = guide_questions(wave, preflight)
    assert questions[0]["question_id"] == rows[0]["candidate_id"]
    assert questions[0]["target_edge"] == rows[0]["target_edge"]
    assert seen == [
        "import Mathlib\n\n"
        "theorem targetConditionedStatementPreflight "
        "(P Q : Prop) (h : P ↔ Q) : Q ↔ P := by\n  sorry\n"
    ]
    assert preflight["candidate_receipts"][0]["checker_owner"] == (
        TARGET_STATEMENT_CHECKER_OWNER
    )


def test_target_candidate_rejects_proof_bytes_and_malformed_language_gap() -> None:
    deck = _deck()
    with pytest.raises(ValueError, match="proof-free"):
        normalize_conjecturer_output(
            deck,
            deck["cards"][0],
            {"candidates": [_candidate("(P : Prop) : P := by sorry")], "no_candidate_reason": ""},
        )
    gap = _candidate("")
    gap["formal_status"] = "language_gap"
    with pytest.raises(ValueError, match="name a capability"):
        normalize_conjecturer_output(
            deck,
            deck["cards"][0],
            {"candidates": [gap], "no_candidate_reason": ""},
        )


def test_wave_deduplicates_same_formal_candidate_across_cards() -> None:
    deck = _deck()
    second = deepcopy(deck["cards"][0])
    second_core = {key: value for key, value in second.items() if key != "card_sha256"}
    second_core["card_id"] = "result-card:two"
    second_core["target_identity"] = "Demo.seedTwo"
    second = {**second_core, "card_sha256": content_hash(second_core)}
    deck_core = {key: value for key, value in deck.items() if key != "deck_sha256"}
    deck_core["cards"] = [deck["cards"][0], second]
    deck = {**deck_core, "deck_sha256": content_hash(deck_core)}
    first_output = {"candidates": [_candidate("(P : Prop) : P → P")], "no_candidate_reason": ""}
    second_candidate = _candidate("(P : Prop) : P → P")
    second_candidate["dependencies"] = ["Demo.seedTwo"]
    second_output = {"candidates": [second_candidate], "no_candidate_reason": ""}
    first = normalize_conjecturer_output(deck, deck["cards"][0], first_output)
    second_rows = normalize_conjecturer_output(deck, second, second_output)

    wave = build_target_conjecture_wave(deck, [first, second_rows])

    assert wave["candidate_count"] == 1
    assert wave["candidates"][0]["also_proposed_from"] == ["result-card:two"]


def test_unbalanced_or_unelaborable_signature_is_rejected_before_guide() -> None:
    deck = _deck()
    malformed = _candidate("(P : Prop)) : P → P")
    malformed["title"] = "Malformed delimiter"
    malformed["mathematical_statement"] = "Malformed candidate."
    malformed["target_edge"] = "Malformed edge."
    unelaborable = _candidate("(n : Nat) : MissingTargetType n")
    unelaborable["title"] = "Unknown target type"
    unelaborable["mathematical_statement"] = "Unknown-name candidate."
    unelaborable["target_edge"] = "Unknown-name edge."
    rows = normalize_conjecturer_output(
        deck,
        deck["cards"][0],
        {"candidates": [malformed, unelaborable], "no_candidate_reason": ""},
    )
    wave = build_target_conjecture_wave(deck, [rows])
    compiled_sources: list[str] = []

    def lean_owner(source, _lean_root):
        compiled_sources.append(source)
        return source.count("(") == source.count(")") and "MissingTargetType" not in source

    preflight = preflight_target_conjecture_wave(
        wave,
        lean_root="/tmp/ztare_proofs",
        compile_fn=lean_owner,
    )

    assert len(compiled_sources) == 2
    assert [row["status"] for row in preflight["candidate_receipts"]] == [
        "rejected",
        "rejected",
    ]
    assert preflight["rejected_candidate_ids"] == [
        row["candidate_id"] for row in rows
    ]
    assert guide_questions(wave, preflight) == []


def test_preflight_unavailable_is_typed_and_receipt_tampering_is_rejected() -> None:
    deck = _deck()
    rows = normalize_conjecturer_output(
        deck,
        deck["cards"][0],
        {
            "candidates": [_candidate("(P : Prop) : P → P")],
            "no_candidate_reason": "",
        },
    )
    wave = build_target_conjecture_wave(deck, [rows])

    def unavailable(_source, _lean_root):
        raise RuntimeError("toolchain unavailable")

    preflight = preflight_target_conjecture_wave(
        wave,
        lean_root="/tmp/ztare_proofs",
        compile_fn=unavailable,
    )
    row = preflight["candidate_receipts"][0]
    assert row["status"] == "unavailable"
    assert row["reason_code"] == "statement_preflight_unavailable:RuntimeError"
    assert guide_questions(wave, preflight) == []

    tampered = deepcopy(preflight)
    tampered["candidate_receipts"][0]["guide_eligible"] = True
    with pytest.raises(ValueError, match="receipt digest mismatch"):
        guide_questions(wave, tampered)


def test_language_gap_reaches_guide_without_statement_compile() -> None:
    deck = _deck()
    gap = _candidate("")
    gap["formal_status"] = "language_gap"
    gap["capability_request"] = "finite_action_kernel_quotient"
    rows = normalize_conjecturer_output(
        deck,
        deck["cards"][0],
        {"candidates": [gap], "no_candidate_reason": ""},
    )
    wave = build_target_conjecture_wave(deck, [rows])

    def should_not_compile(_source, _lean_root):
        raise AssertionError("language gaps have no Lean statement")

    preflight = preflight_target_conjecture_wave(
        wave,
        lean_root="/tmp/ztare_proofs",
        compile_fn=should_not_compile,
    )
    assert preflight["candidate_receipts"][0]["status"] == "not_applicable"
    assert len(guide_questions(wave, preflight)) == 1


def test_valid_nested_and_grouped_forall_duplicates_still_use_two_slots() -> None:
    deck = _deck()
    grouped = _candidate("(P Q : Prop) : ∀ p q : P, Q")
    grouped["title"] = "Grouped binders"
    grouped["mathematical_statement"] = "Grouped universal binders."
    grouped["target_edge"] = "Grouped-binder edge."
    nested = _candidate("(P Q : Prop) : ∀ p : P, ∀ q : P, Q")
    nested["title"] = "Nested binders"
    nested["mathematical_statement"] = "Nested universal binders."
    nested["target_edge"] = "Nested-binder edge."
    rows = normalize_conjecturer_output(
        deck,
        deck["cards"][0],
        {"candidates": [grouped, nested], "no_candidate_reason": ""},
    )
    wave = build_target_conjecture_wave(deck, [rows])
    preflight = preflight_target_conjecture_wave(
        wave,
        lean_root="/tmp/ztare_proofs",
        compile_fn=lambda _source, _root: True,
    )

    assert wave["candidate_count"] == 2
    assert len(guide_questions(wave, preflight)) == 2
