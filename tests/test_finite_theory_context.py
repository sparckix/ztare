from __future__ import annotations

from itertools import combinations

from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import (
    build_formal_theory_context,
    load_formal_theory_context,
    save_formal_theory_context,
)
from ztare.leanmill.magma_law_universe import (
    anonymous_magma_signature,
    magma_laws_through_order,
)


def _size_two_context():
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    universe = enumerate_magma_model_universe(signature, carrier_sizes=(2,))
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=universe,
    )
    return context, laws


def test_formal_context_profiles_typed_formulas_over_canonical_models() -> None:
    context, laws = _size_two_context()

    assert len(context.universe.models) == 10
    assert len(context.formula_profiles) == len(laws) == 7
    assert context.incidence.exact is True
    assert context.incidence.completeness_ref == context.universe.receipt.receipt_digest
    assert len(context.semantic_formula_classes()) == 5


def test_node_identity_binds_formal_context_and_extent() -> None:
    context, _laws = _size_two_context()
    nodes = context.generated_theory_nodes(max_presentation_size=2)

    assert len(nodes) == 5
    assert all(node.context_hash == context.context_hash for node in nodes)
    assert len({node.node_id for node in nodes}) == len(nodes)


def test_pair_synergy_and_independence_have_model_witnesses() -> None:
    context, _laws = _size_two_context()
    candidate = next(
        pair
        for pair in combinations(context.formula_ids, 2)
        if context.synergy_ids(pair)
        and context.independence_witness(pair, pair[0]) is not None
        and context.independence_witness(pair, pair[1]) is not None
    )

    synergy = context.synergy_ids(candidate)
    left_witness = context.independence_witness(candidate, candidate[0])
    right_witness = context.independence_witness(candidate, candidate[1])

    assert synergy
    assert left_witness is not None
    assert right_witness is not None
    assert left_witness.model_id != right_witness.model_id


def test_formula_band_changes_context_identity() -> None:
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    universe = enumerate_magma_model_universe(signature, carrier_sizes=(2,))
    full = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=universe,
    )
    reduced = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws[:-1]),
        universe=universe,
    )

    assert full.context_hash != reduced.context_hash


def test_context_snapshot_replays_materialized_truth_without_reevaluation(
    tmp_path, monkeypatch
) -> None:
    context, _laws = _size_two_context()
    path = save_formal_theory_context(context, tmp_path / "context.json")
    monkeypatch.setattr(
        "ztare.leanmill.finite_theory_context.evaluate_axiom",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("truth recomputed")),
    )
    replayed = load_formal_theory_context(path)
    assert replayed.context_hash == context.context_hash
    assert replayed.universe.model_ids == context.universe.model_ids
    assert replayed.formula_ids == context.formula_ids
