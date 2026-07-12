from __future__ import annotations

from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order
from ztare.leanmill.theory_landscape_morphism import (
    build_landscape_fingerprint,
    propose_landscape_transport,
    test_compiled_landscape_mapping as compile_test,
)


def _context(max_order):
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(max_order)
    return build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )


def test_landscape_transport_starts_pending_and_requires_target_replay():
    source = build_landscape_fingerprint(_context(1))
    target = build_landscape_fingerprint(_context(2))
    morphism = propose_landscape_transport(source, target)
    assert all(row["status"] == "pending" for row in morphism.preservation_obligations)
    assert morphism.validate().verified is False
    mapping = {key: key for key in morphism.component_map}
    receipt = compile_test(morphism, compiled_mapping=mapping, target_test=lambda _row: True)
    assert receipt["status"] == "passed_local_target_test"
    assert receipt["axiom_authority_eligible"] is False
