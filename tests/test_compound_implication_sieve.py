from ztare.leanmill.compound_implication_sieve import (
    run_compound_implication_sieve,
)
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.magma_law_universe import (
    anonymous_magma_signature,
    magma_laws_through_order,
)
from ztare.leanmill.theory_ir import content_hash


def test_one_countermodel_eliminates_the_whole_matching_batch():
    signature = anonymous_magma_signature()
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in magma_laws_through_order(2)),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    result = run_compound_implication_sieve(
        context,
        sort_sizes={"S0": 4},
        max_solver_queries=4,
        timeout_ms=5_000,
    )

    effect = result["witness_effects"][0]
    assert effect["eliminated_count"] >= 2
    assert len(result["eliminated_candidate_ids"]) + len(
        result["surviving_candidate_ids"]
    ) == result["candidate_count"]
    assert effect["yield"]["compression_gain"] > 0
    assert len({row["target_formula_id"] for row in result["query_receipts"]}) == 4
    assert all(
        row["target_family_visits_before"] == 0
        for row in result["query_receipts"]
    )
    core = {key: value for key, value in result.items() if key != "receipt_sha256"}
    assert result["receipt_sha256"] == content_hash(core)
