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
