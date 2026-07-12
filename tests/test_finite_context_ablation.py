from __future__ import annotations

from ztare.leanmill.finite_context_ablation import (
    audit_finite_context_single_premises,
)
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.magma_law_universe import (
    anonymous_magma_signature,
    magma_laws_through_order,
)


def test_exact_context_countermodels_certify_logical_singleton_ablation() -> None:
    laws = {row.postfix: row for row in magma_laws_through_order(3)}
    premises = (
        laws["x0 = x0 x0 x0 op0 op0"],
        laws["x0 = x0 x0 op0 x0 x0 op0 op0"],
    )
    target = laws["x0 = x0 x0 x0 op0 x0 op0 op0"]
    signature = anonymous_magma_signature()
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in (*premises, target)),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )

    receipt = audit_finite_context_single_premises(
        context,
        [row.formula_id for row in premises],
        target.formula_id,
    )

    assert receipt["status"] == "certified_single_premise_nonimplication"
    assert len(receipt["singleton_countermodels"]) == 2
    assert not receipt["unresolved_premise_formula_ids"]
    assert all(
        row["host_replay"]
        == {"base_holds": True, "premise_holds": True, "target_fails": True}
        for row in receipt["singleton_countermodels"]
    )
