from __future__ import annotations

import copy
import hashlib
import json

import pytest

from ztare.leanmill.contracts.proof_gap import (
    ProofGapReceipt,
    RegisteredGapFamily,
    evaluate_axiom_pack_escalation,
    observe_admitted_proof_gap,
)
from ztare.leanmill.formalization_admission import ADMITTED, FormalizationAdmission
from ztare.leanmill.lean_source import extract_signature, strip_comments


def _sha(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _signature(source: str, name: str) -> str:
    return " ".join(strip_comments(extract_signature(source, name)).split())


def _admission(name: str, task_seed: str, conclusion: str) -> FormalizationAdmission:
    source = f"theorem {name} (n : Nat) : {conclusion} := by sorry\n"
    return FormalizationAdmission(
        task_digest=_sha(f"task:{task_seed}"),
        intent_text=f"establish {conclusion}",
        context_digest=_sha("shared-context"),
        status=ADMITTED,
        target_name=name,
        source_text=source,
        target_signature=_signature(source, name),
        faithfulness_reason="independently admitted",
        faithfulness_checks_json=json.dumps(
            {"compiles": True, "non_trivial": True, "round_trip_faithful": True},
            sort_keys=True,
            separators=(",", ":"),
        ),
        refine_trace_json="[]",
        advisory_audits_json="{}",
    )


def _family(seed: str = "shared") -> RegisteredGapFamily:
    return RegisteredGapFamily(
        family_id="priority_uncrossing",
        structure_adapter_id="leanmill.order.priority_uncrossing.v1",
        gap_kind="missing_composition_law",
        registry_digest=_sha("registry:" + seed),
        base_theory_digest=_sha("base:" + seed),
        substrate_digest=_sha("substrate:" + seed),
    )


def _result(
    admission: FormalizationAdmission,
    *,
    failure_class: dict | None = None,
    budget_killed: bool = False,
    outcome: str = "admitted_and_exact_gap",
    solved: str = "exact_gap",
    refutation: str = "",
    closure_certificate: str = "",
) -> dict:
    return {
        "lean_statement": admission.source_text,
        "faithful": True,
        "outcome": outcome,
        "solved": solved,
        "failure_class": failure_class
        or {
            "class": "math",
            "error_class": "missing_lemma",
            "reason": "common structural law absent from the registered base theory",
        },
        "budget_killed": budget_killed,
        "refutation": refutation,
        "closure_certificate": closure_certificate,
    }


def _receipt(
    admission: FormalizationAdmission,
    *,
    family: RegisteredGapFamily | None = None,
    **result_overrides,
) -> ProofGapReceipt:
    return ProofGapReceipt.from_firewall_result(
        family=family or _family(),
        admission=admission,
        result=_result(admission, **result_overrides),
    )


def _violation_types(evaluation: dict) -> set[str]:
    return {row["type"] for row in evaluation["violations"]}


def test_two_distinct_admitted_exact_math_gaps_route_only_to_quarantine() -> None:
    first = _receipt(_admission("gapA", "a", "n + 0 = n"))
    second = _receipt(_admission("gapB", "b", "0 + n = n"))

    evaluation = evaluate_axiom_pack_escalation([first, second])

    assert evaluation["eligible"] is True
    assert evaluation["status"] == "eligible_for_candidate_routing"
    assert evaluation["distinct_target_count"] == 2
    assert evaluation["routing_only"] is True
    assert evaluation["promotion_status"] == "quarantined"
    assert evaluation["proof_credit_eligible"] is False
    assert evaluation["theorem_campaign_admissible"] is False
    assert evaluation["theory_mutation_allowed"] is False
    requirements = {row["requirement"]: row for row in evaluation["required_next_gates"]}
    assert requirements["signed_unseen_task_manifest"]["satisfied"] is False
    assert requirements["typed_axiom_proposals"]["satisfied"] is False


def test_repeated_attempts_on_one_signature_do_not_count_as_repeated_gaps() -> None:
    first_admission = _admission("gapA", "a", "n + 0 = n")
    second_admission = _admission("gapA", "b", "n + 0 = n")

    evaluation = evaluate_axiom_pack_escalation(
        [_receipt(first_admission), _receipt(second_admission)]
    )

    assert evaluation["eligible"] is False
    assert evaluation["distinct_task_count"] == 2
    assert evaluation["distinct_admission_count"] == 2
    assert evaluation["distinct_target_count"] == 1
    assert "insufficient_distinct_targets" in _violation_types(evaluation)


def test_alpha_renaming_does_not_turn_one_target_into_two_gaps() -> None:
    first = _admission("gapA", "a", "n + 0 = n")
    second_source = "theorem gapB (m : Nat) : m + 0 = m := by sorry\n"
    second = FormalizationAdmission(
        task_digest=_sha("task:b"),
        intent_text="establish m + 0 = m",
        context_digest=_sha("shared-context"),
        status=ADMITTED,
        target_name="gapB",
        source_text=second_source,
        target_signature=_signature(second_source, "gapB"),
        faithfulness_reason="independently admitted",
        faithfulness_checks_json="{}",
        refine_trace_json="[]",
        advisory_audits_json="{}",
    )

    evaluation = evaluate_axiom_pack_escalation([_receipt(first), _receipt(second)])

    assert evaluation["eligible"] is False
    assert evaluation["distinct_target_count"] == 1
    assert "insufficient_distinct_targets" in _violation_types(evaluation)


def test_mixed_registered_family_base_or_substrate_is_blocked() -> None:
    evaluation = evaluate_axiom_pack_escalation(
        [
            _receipt(_admission("gapA", "a", "n + 0 = n"), family=_family("one")),
            _receipt(_admission("gapB", "b", "0 + n = n"), family=_family("two")),
        ]
    )

    assert evaluation["eligible"] is False
    assert {
        "mixed_registered_family",
        "mixed_base_theory",
        "mixed_substrate",
    }.issubset(_violation_types(evaluation))


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {
                "failure_class": {
                    "class": "apparatus",
                    "error_class": "timeout",
                    "reason": "wallclock budget exhausted",
                },
                "budget_killed": True,
            },
            {"not_mathematical_failure", "forbidden_failure_signal", "budget_killed"},
        ),
        (
            {
                "failure_class": {
                    "class": "cheat_caught",
                    "error_class": "governance_rejected",
                    "reason": "cheat blocked",
                }
            },
            {"not_mathematical_failure", "forbidden_failure_signal"},
        ),
        ({"refutation": "kernel counterexample"}, {"refutation_present"}),
        ({"closure_certificate": "certificate bytes"}, {"closure_present"}),
        ({"outcome": "admitted_and_open", "solved": "open"}, {"not_exact_gap"}),
    ],
)
def test_non_gap_budget_cheat_refutation_and_closure_evidence_are_blocked(
    overrides: dict, expected: set[str]
) -> None:
    first = _receipt(_admission("gapA", "a", "n + 0 = n"), **overrides)
    second = _receipt(_admission("gapB", "b", "0 + n = n"))

    evaluation = evaluate_axiom_pack_escalation([first, second])

    assert evaluation["eligible"] is False
    assert expected.issubset(_violation_types(evaluation))


def test_receipt_roundtrip_rejects_nested_admission_tampering() -> None:
    receipt = _receipt(_admission("gapA", "a", "n + 0 = n"))
    row = receipt.to_json()
    assert ProofGapReceipt.from_json(row).receipt_digest == receipt.receipt_digest

    tampered = copy.deepcopy(row)
    tampered["formalization_admission"]["target_signature"] = "(n : Nat) : True"
    evaluation = evaluate_axiom_pack_escalation([tampered, receipt])

    assert evaluation["eligible"] is False
    assert "malformed_receipt" in _violation_types(evaluation)


def test_receipt_rejects_attack_source_different_from_admission() -> None:
    admission = _admission("gapA", "a", "n + 0 = n")
    result = _result(admission)
    result["lean_statement"] = "theorem gapA (n : Nat) : True := by sorry\n"

    with pytest.raises(ValueError, match="attack source differs"):
        ProofGapReceipt.from_firewall_result(
            family=_family(), admission=admission, result=result
        )


def test_autoformalize_and_attackrecord_preserve_solver_gap_classification(
    tmp_path, monkeypatch
) -> None:
    from ztare.leanmill.contracts.kernel import AttackRecord
    from ztare.leanmill.solver.autoformalize import autoformalize_and_solve

    for name in (
        "ZTARE_LEANMILL_MULTISTEP_ESCALATE",
        "ZTARE_LEANMILL_REFORMULATE",
        "ZTARE_LEANMILL_FAITHFULNESS_STORE",
        "ZTARE_LEANMILL_GENERALITY_AUDIT",
        "ZTARE_LEANMILL_AMBITION_AUDIT",
    ):
        monkeypatch.setenv(name, "0")
    intent = "every natural equals itself"
    source = "theorem gapA (n : Nat) : n = n := by sorry\n"
    failure = {
        "class": "apparatus",
        "error_class": "timeout",
        "reason": "wallclock budget exhausted",
    }

    result = autoformalize_and_solve(
        intent,
        sandbox=tmp_path,
        formalize_fn=lambda _nl: source,
        compile_fn=lambda _source: True,
        triviality_fn=lambda _source: False,
        backtranslate_fn=lambda _source: intent,
        judge_fn=lambda _intent, _back: True,
        structural_fn=lambda _intent, _source: True,
        solve_fn=lambda _name, _source: {
            "results": [
                {
                    "outcome": "exact_gap",
                    "failure_class": failure,
                    "budget_killed": True,
                }
            ]
        },
        max_refines=0,
        reformulate_budget=0,
    )
    attack = AttackRecord.from_firewall_result(result, nl=intent)

    assert result["failure_class"] == failure
    assert result["budget_killed"] is True
    assert attack.failure_class == failure
    assert attack.budget_killed is True
    assert attack.solved is False


def test_observer_solves_exact_admission_and_preserves_solver_evidence() -> None:
    admission = _admission("gapA", "a", "n + 0 = n")
    calls: list[tuple[tuple, dict]] = []
    failure = {
        "class": "math",
        "error_class": "unsolved_goals",
        "reason": "kernel dead-end (unsolved_goals)",
    }
    governance = {"governance_kernel": {"passed": False}, "integrity_unverified": False}

    def solve_fn(*args, **kwargs):
        calls.append((args, kwargs))
        return {
            "results": [
                {
                    "outcome": "exact_gap",
                    "failure_class": failure,
                    "budget_killed": False,
                }
            ],
            "governance": governance,
            "closure_certificate": None,
        }

    receipt = observe_admitted_proof_gap(
        admission,
        _family(),
        solve_fn=solve_fn,
        substrate="/registered/lean-root",
        provider="codex",
        timeout_s=321,
        mode="dag_search",
        notes="use the registered structure adapter",
    )

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == admission.solve_input().positional_args()
    assert kwargs == {
        "provider": "codex",
        "timeout_s": 321,
        "mode": "dag_search",
        "substrate": "/registered/lean-root",
        "notes": "use the registered structure adapter",
    }
    assert receipt.outcome == "admitted_and_exact_gap"
    assert receipt.failure_class == failure
    assert receipt.budget_killed is False
    assert receipt.governance == governance
    assert receipt.governance_ref.startswith("sha256:")
    assert receipt.closure_certificate is None
    assert receipt.closure_certificate_ref == ""
    assert receipt.refutation is None
    assert receipt.refutation_ref == ""


def test_observer_preserves_kernel_refutation_and_evaluator_blocks_it() -> None:
    admission = _admission("gapA", "a", "n + 0 = n")

    def solve_fn(*_args, **_kwargs):
        return {
            "results": [
                {
                    "outcome": "falsified",
                    "falsifier": "counterexample n = 1",
                    "failure_class": {
                        "class": "math",
                        "error_class": "type_mismatch",
                        "reason": "kernel refutation",
                    },
                    "budget_killed": False,
                }
            ],
            "statement_false_verified": True,
            "closure_certificate": None,
        }

    receipt = observe_admitted_proof_gap(admission, _family(), solve_fn=solve_fn)
    evaluation = evaluate_axiom_pack_escalation(
        [receipt, _receipt(_admission("gapB", "b", "0 + n = n"))]
    )

    assert receipt.refutation == "counterexample n = 1"
    assert receipt.refutation_ref.startswith("sha256:")
    assert evaluation["eligible"] is False
    assert {"not_exact_gap", "forbidden_failure_signal", "refutation_present"}.issubset(
        _violation_types(evaluation)
    )
