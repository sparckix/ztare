from __future__ import annotations

import pytest

from ztare.leanmill.magma_law_universe import anonymous_magma_signature
from ztare.leanmill.theory_ir import (
    OperationSymbol,
    RelationSymbol,
    SortDecl,
    TheorySignature,
)
from ztare.leanmill.typed_postfix_codec import (
    decode_postfix_equation,
    decode_postfix_formula,
    decode_postfix_term,
)


def test_postfix_codec_preserves_arbitrary_bracketing():
    signature = anonymous_magma_signature()
    left_assoc = decode_postfix_equation(
        signature,
        name="assoc_shape",
        variable_sorts={"x0": "S0", "x1": "S0", "x2": "S0"},
        lhs_tokens=("x0", "x1", "op0", "x2", "op0"),
        rhs_tokens=("x0", "x1", "x2", "op0", "op0"),
    )
    assert left_assoc.formula.formulas[0].terms[0] != left_assoc.formula.formulas[0].terms[1]


def test_postfix_codec_fails_on_underflow_unknown_or_wrong_final_stack():
    signature = anonymous_magma_signature()
    with pytest.raises(ValueError, match="underflow"):
        decode_postfix_term(
            signature, variable_sorts={"x0": "S0"}, tokens=("x0", "op0")
        )
    with pytest.raises(ValueError, match="unknown"):
        decode_postfix_term(
            signature, variable_sorts={"x0": "S0"}, tokens=("x0", "mystery")
        )
    with pytest.raises(ValueError, match="exactly one"):
        decode_postfix_term(
            signature, variable_sorts={"x0": "S0"}, tokens=("x0", "x0")
        )


def test_formula_codec_handles_relations_connectives_and_local_quantifiers():
    signature = TheorySignature(
        name="RelationalSystem",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
        relations=(RelationSymbol("edge", ("S", "S")),),
    )
    axiom = decode_postfix_formula(
        signature,
        name="successor_witness",
        variable_sorts={"x": "S", "y": "S"},
        tokens=("x", "y", "edge", "y", "step", "y", "edge", "and", "exists:y"),
    )

    assert axiom.formula.kind == "forall"
    existential = axiom.formula.formulas[0]
    assert existential.kind == "exists"
    assert existential.formulas[0].kind == "and"

    equality = decode_postfix_formula(
        signature,
        name="equality_alias",
        variable_sorts={"x": "S"},
        tokens=("x", "x", "="),
    )
    assert equality.formula.formulas[0].kind == "eq"


def test_formula_codec_rejects_term_formula_kind_confusion():
    signature = anonymous_magma_signature()
    with pytest.raises(ValueError, match="expected 2 formula"):
        decode_postfix_formula(
            signature,
            name="bad",
            variable_sorts={"x": "S0"},
            tokens=("x", "x", "and"),
        )
