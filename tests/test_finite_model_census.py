from __future__ import annotations

from ztare.leanmill.axiom_pack_band import finite_band_pilot_design
from ztare.leanmill.finite_model_census import (
    canonicalize_magma_table,
    enumerate_magma_model_universe,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature


def test_size_two_magma_census_is_complete_and_quotiented() -> None:
    signature = anonymous_magma_signature()
    universe = enumerate_magma_model_universe(signature, carrier_sizes=(2,))

    assert universe.receipt.complete is True
    assert universe.receipt.labeled_interpretation_count == 16
    assert universe.receipt.accepted_labeled_count == 16
    assert universe.receipt.canonical_model_count == 10
    assert sum(row.labeled_orbit_count for row in universe.models) == 16


def test_canonical_table_is_invariant_under_carrier_swap() -> None:
    original = (0, 0, 0, 0)
    swapped = (1, 1, 1, 1)

    assert canonicalize_magma_table(original, 2) == canonicalize_magma_table(
        swapped, 2
    )


def test_band_diagnostic_reproduces_35_labeled_and_10_isomorphism_classes() -> None:
    design = finite_band_pilot_design()
    universe = enumerate_magma_model_universe(
        design.signature,
        carrier_sizes=(3,),
        operation_name="mul",
        base_axioms=design.base_axioms,
    )

    assert universe.receipt.labeled_interpretation_count == 19_683
    assert universe.receipt.accepted_labeled_count == 35
    assert universe.receipt.canonical_model_count == 10
    assert sum(row.labeled_orbit_count for row in universe.models) == 35
