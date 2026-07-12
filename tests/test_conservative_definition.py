from __future__ import annotations

import pytest

from ztare.leanmill.conservative_definition import (
    ConservativeOperationDefinition,
    build_conservative_operation_definition,
    definition_retention_receipt,
)
from ztare.leanmill.theory_ir import (
    Binder,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
)


def test_macro_expands_deterministically_into_prior_signature():
    signature = TheorySignature(
        name="BinarySystem",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("combine", ("S", "S"), "S"),),
    )
    definition = build_conservative_operation_definition(
        signature,
        name="sandwich",
        parameters=(Binder("x", "S"), Binder("y", "S")),
        result_sort="S",
        body=Term.app(
            "combine",
            Term.app("combine", Term.var("x"), Term.var("y")),
            Term.var("x"),
        ),
        source_motif_refs=("motif:xyx",),
    )
    expanded = definition.expand((Term.var("a"), Term.var("b")))
    assert expanded.to_json() == Term.app(
        "combine",
        Term.app("combine", Term.var("a"), Term.var("b")),
        Term.var("a"),
    ).to_json()
    assert definition.to_json()["conservative"] is True


def test_retention_requires_compression_or_new_separation():
    signature = TheorySignature(
        name="BinarySystem",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("combine", ("S", "S"), "S"),),
    )
    definition = build_conservative_operation_definition(
        signature,
        name="square",
        parameters=(Binder("x", "S"),),
        result_sort="S",
        body=Term.app("combine", Term.var("x"), Term.var("x")),
        source_motif_refs=("motif:xx",),
    )
    assert definition_retention_receipt(definition, motif_occurrences=1)["status"] == "rejected"
    assert definition_retention_receipt(
        definition, motif_occurrences=1, separated_consequence_class=True
    )["status"] == "retained"


def test_unbound_or_circular_looking_definition_is_rejected():
    signature = TheorySignature(
        name="BinarySystem",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("combine", ("S", "S"), "S"),),
    )
    with pytest.raises(ValueError, match="unbound"):
        build_conservative_operation_definition(
            signature,
            name="bad",
            parameters=(Binder("x", "S"),),
            result_sort="S",
            body=Term.app("combine", Term.var("x"), Term.var("y")),
            source_motif_refs=("motif:bad",),
        )


def test_signature_generic_definition_expands_without_adding_strength():
    signature = TheorySignature(
        name="UnarySystem",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    definition = build_conservative_operation_definition(
        signature,
        name="twice",
        parameters=(Binder("x", "S"),),
        result_sort="S",
        body=Term.app("step", Term.app("step", Term.var("x"))),
        source_motif_refs=("motif:double_step",),
    )

    assert isinstance(definition, ConservativeOperationDefinition)
    assert definition.expand((Term.var("y"),)).to_json() == Term.app(
        "step", Term.app("step", Term.var("y"))
    ).to_json()
    assert definition.to_json()["expansion_language"] == (
        "prior_theory_signature_only"
    )
