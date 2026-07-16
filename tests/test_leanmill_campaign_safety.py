from __future__ import annotations


def test_semantic_reference_cannot_supply_hard_identity_inputs() -> None:
    from ztare.leanmill.solver.autoformalize import _reference_gate_inputs

    assert _reference_gate_inputs({
        "exact": False,
        "fingerprint": {"n_explicit_binders": 9},
        "statement": "theorem unrelated : False := by sorry",
    }) == (None, "")
    assert _reference_gate_inputs({
        "exact": True,
        "fingerprint": {"n_explicit_binders": 2},
        "statement": "theorem same (n : Nat) : n = n := by sorry",
    }) == ({"n_explicit_binders": 2}, "theorem same (n : Nat) : n = n := by sorry")


def test_budget_stop_defers_untouched_notes_without_retries(monkeypatch, tmp_path) -> None:
    from ztare.leanmill.solver.autoformalize_notes import autoformalize_from_notes

    for name in (
        "ZTARE_LEANMILL_NOTES_RETRY",
        "ZTARE_LEANMILL_FALSIFY_ESCALATION",
        "ZTARE_LEANMILL_SELF_CORRECT_DEFS",
    ):
        monkeypatch.setenv(name, "0")
    calls: list[str] = []

    def attack(nl, **_kwargs):
        calls.append(nl)
        return {
            "nl": nl,
            "lean_statement": "",
            "faithful": None,
            "outcome": "budget_exhausted",
            "faithfulness_reason": "BUDGET_EXHAUSTED",
            "solved": False,
        }

    result = autoformalize_from_notes(
        "## Target\nG.\n## Lemmas\n- A.\n- B.\n- C.\n",
        lean_root=tmp_path,
        attack_fn=attack,
        on_progress=lambda _msg: None,
    )
    assert calls == ["A."]
    assert result["execution_stop"] == "budget_exhausted"
    assert result["wall_deferred"] == ["B.", "C.", "G."]
    assert result["target"]["deferred"] == "execution_stop"
    assert "execution_stop=budget_exhausted" in result["summary"]


def test_typed_formal_work_item_bypasses_natural_language_admission(monkeypatch, tmp_path) -> None:
    import ztare.leanmill.solver.autoformalize_notes as notes

    for name in (
        "ZTARE_LEANMILL_NOTES_RETRY",
        "ZTARE_LEANMILL_FALSIFY_ESCALATION",
        "ZTARE_LEANMILL_SELF_CORRECT_DEFS",
    ):
        monkeypatch.setenv(name, "0")
    statement = "theorem posed (n : Nat) : n = n := by sorry"
    item = notes.FormalSourceWorkItem(
        target_name="posed",
        source_text="import Mathlib\n" + statement + "\n",
        target_block=statement,
    )
    routed: list[str] = []

    def direct(work_item, **_kwargs):
        routed.append(work_item.target_name)
        return {
            "nl": statement,
            "lean_statement": statement,
            "faithful": True,
            "outcome": "admitted_and_closed",
            "solved": True,
        }

    monkeypatch.setattr(notes, "_attack_formal_source", direct)

    def prose_attack(*_args, **_kwargs):
        raise AssertionError("typed Lean source entered the natural-language lane")

    result = notes.autoformalize_from_notes(
        "## Lemmas\n- " + statement + "\n",
        lean_root=tmp_path,
        attack_fn=prose_attack,
        formal_work_items={notes._formal_work_item_key(statement): item},
        on_progress=lambda _msg: None,
    )
    assert routed == ["posed"]
    assert result["lemmas"][0]["solved"] is True


def test_typed_formal_budget_stop_is_not_an_empty_formalization(tmp_path) -> None:
    from ztare.leanmill.exploration_budget import BudgetExceeded
    from ztare.leanmill.solver.autoformalize_notes import (
        FormalSourceWorkItem,
        _attack_formal_source,
    )

    item = FormalSourceWorkItem(
        target_name="posed",
        source_text="theorem posed : True := by sorry\n",
        target_block="theorem posed : True := by sorry",
    )

    def exhausted(*_args, **_kwargs):
        raise BudgetExceeded("hard_cap_reached:provider_calls")

    result = _attack_formal_source(
        item,
        lean_root=tmp_path,
        timeout_s=1,
        solve_fn=exhausted,
    )
    assert result["outcome"] == "budget_exhausted"
    assert result["budget_killed"] is True
    assert "BUDGET_EXHAUSTED" in result["faithfulness_reason"]


def test_roundtrip_budget_stop_is_not_an_unfaithful_verdict() -> None:
    from ztare.leanmill.exploration_budget import BudgetExceeded
    from ztare.leanmill.solver.autoformalize import faithfulness_gate

    def exhausted(_statement):
        raise BudgetExceeded("hard_cap_reached:provider_calls")

    verdict = faithfulness_gate(
        "A nontrivial claim.",
        "theorem posed (P : Prop) (h : P) : P := by sorry",
        compile_fn=lambda _statement: True,
        triviality_fn=lambda _statement: False,
        backtranslate_fn=exhausted,
        judge_fn=lambda _original, _rendered: True,
    )
    assert verdict.accepted is False
    assert verdict.reason == "BUDGET_EXHAUSTED"
    assert verdict.checks["budget_exhausted"] is True


def test_p1_blueprint_admission_rejects_mode_conflict() -> None:
    from pathlib import Path
    from ztare.leanmill.campaign_manifest import (
        formalize_campaign_admission,
        load_campaign_manifest,
    )

    repo = Path(__file__).resolve().parents[1]
    old = load_campaign_manifest(repo / "projects/leanmill_experiments/p1_rungA_blueprint.md")
    canonical = load_campaign_manifest(repo / "projects/leanmill_experiments/p1_rungA_campaign.md")
    assert formalize_campaign_admission(old)["status"] == "rejected"
    assert formalize_campaign_admission(canonical)["status"] == "admissible"
