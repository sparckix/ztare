from __future__ import annotations

from ztare.leanmill.magma_law_universe import (
    MagmaTerm,
    anonymous_magma_signature,
    magma_laws_exact_order,
    magma_laws_through_order,
)
from ztare.leanmill.theory_ir import validate_axioms


def test_equational_theories_order_counts_are_reproduced() -> None:
    assert [len(magma_laws_exact_order(order)) for order in range(4)] == [
        2,
        5,
        39,
        364,
    ]
    assert len(magma_laws_through_order(3)) == 410


def test_laws_are_canonical_under_side_swap_and_variable_renaming() -> None:
    rows = magma_laws_through_order(3)
    formula_ids = [row.formula_id for row in rows]
    postfix = [row.postfix for row in rows]

    assert len(formula_ids) == len(set(formula_ids))
    assert len(postfix) == len(set(postfix))
    assert all(
        row.left.postfix() <= row.right.postfix()
        or row.left.postfix().split()[0] == "x0"
        for row in rows
    )


def test_nontrivial_tautologies_are_removed_but_x_equals_x_remains() -> None:
    order_zero = magma_laws_exact_order(0)
    order_two = magma_laws_exact_order(2)

    assert any(row.left == row.right == MagmaTerm.var(0) for row in order_zero)
    assert all(row.left != row.right for row in order_two)


def test_generated_axioms_validate_against_anonymous_signature() -> None:
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(3)

    validate_axioms(signature, tuple(row.axiom for row in laws))
    assert signature.operations[0].name == "op0"
    assert laws[0].axiom.semantic_hash
