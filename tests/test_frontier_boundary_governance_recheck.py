from __future__ import annotations

import pytest

from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import (
    build_formal_theory_context,
    save_formal_theory_context,
)
from ztare.leanmill.frontier_boundary import FrontierBoundaryResult
from ztare.leanmill.frontier_campaign_runner import (
    recheck_frontier_boundary_governance,
)
from ztare.leanmill.lean_consequence_bridge import render_lean_consequence_task
from ztare.leanmill.magma_law_universe import (
    anonymous_magma_signature,
    magma_laws_through_order,
)
from ztare.leanmill.theory_ir import content_hash


@pytest.mark.parametrize("saved_in_boundary", [True, False])
def test_boundary_proof_is_rechecked_without_an_agent_call(
    tmp_path, monkeypatch, saved_in_boundary
) -> None:
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in laws),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    attempt = tmp_path / "attempt-test"
    save_formal_theory_context(context, attempt / "formal_context.json")
    premises = (laws[1], laws[2])
    target = laws[0]
    task = render_lean_consequence_task(
        signature,
        tuple(row.axiom for row in premises),
        target.axiom,
    )
    governed_core = {
        "schema": "leanmill.governed_consequence_attempt.v1",
        "task_id": task.task_id,
        "status": "rejected_banned_axiom",
        "proof_text": "```lean\nexact True.intro\n```" if saved_in_boundary else "",
        "solver_result_digest": "saved-solver-result",
        "attribution": None,
        "work_receipt": {},
        "reason": "generic governance did not distinguish local fields",
    }
    governed = {
        **governed_core,
        "receipt_sha256": content_hash(governed_core),
    }
    boundary = FrontierBoundaryResult(
        context_hash=context.context_hash,
        query_results=(
            {
                "premise_formula_ids": [row.formula_id for row in premises],
                "target_formula_id": target.formula_id,
                "countermodel_searches": [],
                "lean": {
                    "status": "rejected_by_governance",
                    "task_id": task.task_id,
                    "governed_attempt": governed,
                },
            },
        ),
        stop_reason="campaign_finished",
    ).to_json()
    write_json_atomic(attempt / "boundary_result.json", boundary)

    required_names = {row.axiom.name for row in premises}
    from ztare.gates import v33_preflight_risk_detector as compiler

    monkeypatch.setattr(
        compiler,
        "_compile_probe",
        lambda source, *_args, **_kwargs: all(
            f"  {name} :" in source for name in required_names
        ),
    )
    lean_root = tmp_path / "lean"
    lean_root.mkdir()
    result = recheck_frontier_boundary_governance(
        attempt,
        lean_root=lean_root,
        proof_candidates=(
            None
            if saved_in_boundary
            else {target.formula_id: "```lean\nexact True.intro\n```"}
        ),
    )

    assert result["provider_calls"] == 0
    assert result["proved_attributed_count"] == 1
    assert result["query_rechecks"][0]["recheck"]["status"] == "proved_attributed"
    assert result["query_rechecks"][0]["recheck"]["proof_text"] == "exact True.intro"
    assert result["query_rechecks"][0]["proof_source"] == (
        "boundary_result" if saved_in_boundary else "explicit_recovery_candidate"
    )

    monkeypatch.setattr(
        compiler,
        "_compile_probe",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("recompiled")),
    )
    assert recheck_frontier_boundary_governance(
        attempt,
        lean_root=lean_root,
    ) == result
