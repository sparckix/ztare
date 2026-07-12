from __future__ import annotations

import pytest

from ztare.common.finite_incidence_context import (
    build_context_from_adapter,
    build_incidence_context,
)


def _toy_context():
    # Objects: m0, m1, m2.  a holds on 0/1, b on 1/2, c only on 1.
    return build_incidence_context(
        object_ids=("m0", "m1", "m2"),
        attribute_truth_bits={"a": 0b011, "b": 0b110, "c": 0b010},
        exact=True,
        completeness_ref="sha256:toy-complete",
    )


def test_exact_context_computes_extent_closure_synergy_and_witnesses() -> None:
    context = _toy_context()

    assert context.extent_object_ids(("a",)) == ("m0", "m1")
    assert context.extent_object_ids(("a", "b")) == ("m1",)
    assert context.closure_ids(("a", "b")) == ("a", "b", "c")
    assert context.synergy_ids(("a", "b")) == ("c",)
    assert context.independence_object_id(("a", "b"), "a") == "m2"
    assert context.independence_object_id(("a", "b"), "b") == "m0"
    assert context.separation_object_id(("a",), ("b",)) == "m0"


def test_generated_concepts_recover_minimal_presentations() -> None:
    concepts = _toy_context().generated_concepts(max_presentation_size=2)
    singleton_extent = next(row for row in concepts if row.extent_bits == 0b010)

    assert singleton_extent.closure_bits == 0b111
    assert singleton_extent.minimal_generators == (("c",),)
    assert singleton_extent.presentation_count == 4


def test_sampled_panel_can_quotient_but_cannot_claim_closure() -> None:
    context = build_incidence_context(
        object_ids=("o0", "o1"),
        attribute_truth_bits={"same_a": 0b01, "same_b": 0b01},
        exact=False,
    )

    assert context.semantic_attribute_classes() == (("same_a", "same_b"),)
    with pytest.raises(ValueError, match="complete finite context"):
        context.closure_ids(("same_a",))


def test_object_partition_is_relative_to_the_current_observation_language() -> None:
    context = build_incidence_context(
        object_ids=("o0", "o1", "o2", "o3"),
        attribute_truth_bits={"a": 0b0011, "b": 0b0011},
        exact=True,
        completeness_ref="sha256:complete",
    )

    assert context.observational_object_classes() == (
        ("o0", "o1"),
        ("o2", "o3"),
    )
    assert context.observational_partition_summary() == {
        "class_count": 2,
        "non_singleton_class_count": 2,
        "largest_class_size": 2,
    }


def test_context_hash_binds_object_order() -> None:
    left = build_incidence_context(
        object_ids=("o0", "o1"),
        attribute_truth_bits={"a": 0b01},
        exact=True,
        completeness_ref="sha256:complete",
    )
    right = build_incidence_context(
        object_ids=("o1", "o0"),
        attribute_truth_bits={"a": 0b10},
        exact=True,
        completeness_ref="sha256:complete",
    )

    assert left.context_hash != right.context_hash


def test_adapter_build_is_shared_across_substrates() -> None:
    class Adapter:
        object_ids = ("transition:0", "transition:1")
        attribute_ids = ("program:identity", "program:flip")

        def satisfies(self, object_id: str, attribute_id: str) -> bool:
            return (object_id, attribute_id) != ("transition:1", "program:identity")

    context = build_context_from_adapter(
        Adapter(), exact=True, completeness_ref="sha256:episode-complete"
    )

    assert context.extent_object_ids(("program:identity",)) == ("transition:0",)
    assert context.closure_ids(("program:identity",)) == (
        "program:flip",
        "program:identity",
    )
