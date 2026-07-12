from __future__ import annotations

from ztare.leanmill.lean_consequence_bridge import (
    check_lean_consequence_proof,
    matched_proof_attribution,
    recheck_governed_lean_consequence,
    render_lean_consequence_task,
)
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order


def test_conditional_task_contains_no_global_axiom_and_binds_inputs():
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    task = render_lean_consequence_task(
        signature, tuple(row.axiom for row in laws[1:3]), laws[0].axiom
    )
    assert "class CandidateAxiomPack" in task.source_with_hole
    assert "theorem axiompack_consequence" in task.source_with_hole
    assert "\naxiom " not in task.source_with_hole
    assert task.premise_hashes == tuple(row.axiom.semantic_hash for row in laws[1:3])


def test_kernel_statuses_and_forbidden_proof_tokens():
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    task = render_lean_consequence_task(signature, (laws[0].axiom,), laws[0].axiom)
    proved = check_lean_consequence_proof(task, "exact CandidateAxiomPack.magma_law_" + "bad", compile_fn=lambda _s: True)
    assert proved.status == "proved"
    invalid = check_lean_consequence_proof(task, "sorry", compile_fn=lambda _s: True)
    assert invalid.status == "invalid"
    unresolved = check_lean_consequence_proof(task, "trivial", compile_fn=lambda _s: None)
    assert unresolved.status == "unresolved"


def test_matched_attribution_reuses_identical_proof_bytes():
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    seen = []
    receipt = matched_proof_attribution(
        signature,
        (laws[1].axiom, laws[2].axiom),
        laws[0].axiom,
        "rfl",
        compile_fn=lambda source: seen.append(source) or True,
    )
    assert set(receipt["arms"]) == {
        "full", "empty", f"without:{laws[1].axiom.semantic_hash}",
        f"without:{laws[2].axiom.semantic_hash}",
    }
    assert len(seen) == 4


def test_saved_fenced_proof_gets_premise_aware_governance_replay():
    signature = anonymous_magma_signature()
    laws = magma_laws_through_order(1)
    premises = (laws[1].axiom, laws[2].axiom)
    task = render_lean_consequence_task(signature, premises, laws[0].axiom)
    required_names = {row.name for row in premises}

    result = recheck_governed_lean_consequence(
        task,
        "```lean\n  exact True.intro\n```",
        compile_fn=lambda source: all(name in source for name in required_names),
    )

    assert result.status == "proved_attributed"
    assert result.proof_text == "exact True.intro"
    assert result.attribution is not None
    assert result.attribution["arms"]["full"]["status"] == "proved"
    assert result.attribution["arms"]["empty"]["status"] != "proved"
