from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError

import pytest

from ztare.leanmill.formalization_admission import (
    ADMITTED,
    INADMISSIBLE_PROVIDER_DEAD,
    INVALID_ADMISSION,
    REJECTED,
    FormalizationAdmission,
    formalize_only,
)


_TASK_DIGEST = "sha256:" + "1" * 64


@pytest.fixture(autouse=True)
def _hermetic_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZTARE_LEANMILL_FAITHFULNESS_STORE", "0")
    monkeypatch.setenv("ZTARE_LEANMILL_MULTISTEP_ESCALATE", "0")
    monkeypatch.setenv("ZTARE_LEANMILL_GENERALITY_AUDIT", "0")
    monkeypatch.setenv("ZTARE_LEANMILL_AMBITION_AUDIT", "0")
    monkeypatch.setenv("ZTARE_LEANMILL_REFORMULATE", "0")
    from ztare.formal import repl_compile

    monkeypatch.setattr(repl_compile, "get_campaign_substrate", lambda: None)


def _run(source: str, *, compile_ok: bool = True):
    return formalize_only(
        "For every natural number n, n equals itself.",
        task_digest=_TASK_DIGEST,
        sandbox="/tmp/unused-lean-root",
        formalize_fn=lambda _intent: source,
        compile_fn=lambda _statement: compile_ok,
        triviality_fn=lambda _statement: False,
        backtranslate_fn=lambda _statement: "For every natural number n, n equals itself.",
        judge_fn=lambda _original, _back: True,
        structural_fn=lambda _intent, _statement: True,
        max_refines=0,
    )


def test_admission_freezes_target_at_existing_solve_boundary() -> None:
    source = "theorem admitted_target (n : Nat) : n = n := by sorry"
    admission = _run(source)

    assert admission.status == ADMITTED
    assert admission.admitted is True
    assert admission.target_name == "admitted_target"
    assert admission.source_text == source
    assert admission.target_signature
    assert admission.to_json()["admission_digest"] == admission.admission_digest
    assert admission.faithfulness_checks["compiles"] is True
    assert FormalizationAdmission.from_json(admission.to_json()) == admission

    tampered = copy.deepcopy(admission.to_json())
    tampered["source_text"] = tampered["source_text"].replace("n = n", "n = 0")
    with pytest.raises(ValueError):
        FormalizationAdmission.from_json(tampered)

    solve_input = admission.solve_input()
    assert solve_input.positional_args() == ("admitted_target", source, "")
    assert solve_input.admission_digest == admission.admission_digest

    with pytest.raises(FrozenInstanceError):
        admission.status = REJECTED  # type: ignore[misc]


def test_arm_prelude_may_change_but_frozen_target_may_not() -> None:
    source = "theorem admitted_target (n : Nat) : n = n := by sorry"
    admission = _run(source)
    arm_prelude = (
        "import Mathlib\n\n"
        "class CandidateContext : Prop where\n"
        "  marker : True"
    )

    arm_source = admission.solve_input(arm_prelude=arm_prelude).source_text
    assert arm_source.endswith(source + "\n")
    assert arm_prelude in arm_source
    assert arm_source.count("import Mathlib") == 1

    duplicated = source
    with pytest.raises(ValueError, match="retain the admitted target"):
        admission.solve_input(arm_prelude=duplicated)


def test_firewall_rejection_never_produces_solve_input() -> None:
    admission = _run(
        "theorem malformed_target (n : Nat) : n = n := by sorry",
        compile_ok=False,
    )

    assert admission.status == REJECTED
    assert admission.admitted is False
    assert admission.target_name == ""
    assert "typecheck" in admission.faithfulness_reason
    with pytest.raises(ValueError, match="cannot solve admission"):
        admission.solve_input()


def test_existing_definition_shell_gate_remains_before_admission() -> None:
    source = (
        "def Hidden : Nat := 0\n\n"
        "theorem shell_target : Hidden = 0 := by sorry"
    )
    admission = _run(source)

    assert admission.status == REJECTED
    assert admission.admitted is False
    assert admission.advisory_audits["def_shells"]
    assert "def-shell" in admission.faithfulness_reason


def test_closed_or_provider_dead_output_is_not_admitted() -> None:
    closed = _run(
        "theorem already_done (n : Nat) : n = n := by exact rfl"
    )
    assert closed.status == INVALID_ADMISSION
    assert "not a unique open declaration" in closed.faithfulness_reason

    from ztare.leanmill.solver.agentic_leaf import INADMISSIBLE_DISPATCH

    dead = formalize_only(
        "A theorem whose provider is unavailable.",
        task_digest="sha256:" + "2" * 64,
        sandbox="/tmp/unused-lean-root",
        formalize_fn=lambda _intent: INADMISSIBLE_DISPATCH,
        compile_fn=lambda _statement: True,
        triviality_fn=lambda _statement: False,
        backtranslate_fn=lambda _statement: "same",
        judge_fn=lambda _original, _back: True,
        structural_fn=lambda _intent, _statement: True,
        max_refines=0,
    )
    assert dead.status == INADMISSIBLE_PROVIDER_DEAD
    assert dead.admitted is False
