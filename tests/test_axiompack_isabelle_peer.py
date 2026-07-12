from __future__ import annotations

from ztare.leanmill.solver.sledgehammer import (
    execute_isabelle_theory_task,
    render_theory_implication_to_isabelle,
)
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    RelationSymbol,
    SortDecl,
    Term,
    TheorySignature,
)


def _forall_eq(name: str, left: Term, right: Term) -> AxiomFormula:
    return AxiomFormula(
        name,
        Formula.forall((Binder("x", "S"),), Formula.eq(left, right)),
    )


def test_theory_ir_renderer_quantifies_anonymous_signature_and_preserves_relation():
    signature = TheorySignature(
        "Anonymous",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("op", ("S",), "S"),),
        relations=(RelationSymbol("holds", ("S",)),),
    )
    x = Term.var("x")
    premise = _forall_eq("p", Term.app("op", Term.app("op", x)), x)
    target = AxiomFormula(
        "q",
        Formula.forall(
            (Binder("x", "S"),),
            Formula.implies(
                Formula.rel("holds", x),
                Formula.rel("holds", Term.app("op", Term.app("op", x))),
            ),
        ),
    )

    task = render_theory_implication_to_isabelle(signature, (premise,), target)

    assert "\\<forall>f0::('s0 \\<Rightarrow> 's0)" in task.statement
    assert "\\<forall>r0::('s0 \\<Rightarrow> bool)" in task.statement
    assert "\\<longrightarrow>" in task.statement
    assert task.translation_map["operations"] == {"op": "f0"}
    assert task.translation_map["relations"] == {"holds": "r0"}
    assert "Anonymous" not in task.statement


def test_theory_peer_requires_the_returned_proof_to_pass_isabelle_build():
    signature = TheorySignature(
        "Anonymous",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("op", ("S",), "S"),),
    )
    x = Term.var("x")
    premise = _forall_eq("p", Term.app("op", Term.app("op", x)), x)
    target = _forall_eq(
        "q",
        Term.app("op", Term.app("op", Term.app("op", Term.app("op", x)))),
        x,
    )
    task = render_theory_implication_to_isabelle(signature, (premise,), target)
    seen = {}

    def hammer(_theory, **kwargs):
        seen["statement"] = kwargs["statement"]
        return {"proof": "by (metis)", "used_facts": []}

    def verify(theory, **_kwargs):
        seen["theory"] = theory
        return True, "accepted"

    attempt = execute_isabelle_theory_task(
        task,
        hammer_fn=hammer,
        verify_fn=verify,
    )

    assert attempt.status == "proved"
    assert attempt.kernel_checked is True
    assert attempt.transport_calls == 2
    assert seen["statement"] == task.statement
    assert f'lemma axiompack_goal: "{task.statement}"' in seen["theory"]
    assert "by (metis)" in seen["theory"]


def test_theory_peer_never_promotes_an_unverified_or_injected_proof():
    signature = TheorySignature(
        "Anonymous",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("op", ("S",), "S"),),
    )
    x = Term.var("x")
    target = _forall_eq("q", Term.app("op", x), x)
    task = render_theory_implication_to_isabelle(signature, (), target)

    rejected = execute_isabelle_theory_task(
        task,
        hammer_fn=lambda *_args, **_kwargs: {
            "proof": "by simp\nend",
            "used_facts": [],
        },
        verify_fn=lambda *_args, **_kwargs: (True, "should not run"),
    )
    assert rejected.status == "invalid"
    assert rejected.kernel_checked is False
    assert rejected.transport_calls == 1

    failed = execute_isabelle_theory_task(
        task,
        hammer_fn=lambda *_args, **_kwargs: {
            "proof": "by (metis)",
            "used_facts": [],
        },
        verify_fn=lambda *_args, **_kwargs: (False, "type error"),
    )
    assert failed.status == "verification_failed"
    assert failed.kernel_checked is False
