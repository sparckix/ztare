"""Unit tests for BRIDGE-1 substrate-recommender validators.

Three validator-class tests per spec §10:
  (a) name-reuse detected
  (b) missing F-row/INS citation rejected
  (c) what_changes_if_succeeds boilerplate rejected (length floor)
"""

from __future__ import annotations

from ztare.research_director.substrate_recommender import (
    validate_cold,
    validate_branch,
)


GOOD_COLD_CANDIDATE = {
    "name": "ns_proofsearch_concentration_coercivity",
    "predicted_class": "formal_proof_lean",
    "confidence": "medium",
    "mining_basis": "novel; Track B branch grid",
    "rationale": (
        "Closes the concentration impact coercivity branch named in advisor_channel "
        "Turn 7. Cites F-GP186-NS-PHASE5CH-01 (the metric-degeneracy receipt) and "
        "the insights_ledger heading INS-082 (Leray gain-tax tether)."
    ),
    "charter_sketch": (
        "Target: prove that block execution under the declared Leray observable pays "
        "superlinear impact in the pricing kernel. Falsification: construct a "
        "deterministic Python audit on bounded supports that exhibits sublinear impact. "
        "Gate package: PSD certificate pass on the impact lift, plus the Lean target "
        "ns_pricing_kernel_limit_passage.lean for closure. Iteration cap: 8 iterations."
    ),
    "what_changes_if_succeeds": (
        "If concentration coercivity holds, the analytic obligation 1 of Turn 8 closes "
        "for the declared Leray ledger; the remaining Track B wall reduces to dichotomy + "
        "cross-profile recombination + price LSC, which is a 4-branch grid not 7."
    ),
}


def test_no_name_reuse():
    payload = {"candidates": [{**GOOD_COLD_CANDIDATE, "name": "gp140_ztare_discovery"}]}
    errs = validate_cold(payload, existing_names={"gp140_ztare_discovery"})
    assert any("collides with existing substrate" in e for e in errs)


def test_rationale_must_cite():
    cand = {**GOOD_COLD_CANDIDATE, "rationale": "uses inversion and compresses the asymptotic survival ledger"}
    errs = validate_cold({"candidates": [cand]}, existing_names=set())
    assert any("rationale lacks" in e for e in errs)


def test_what_changes_too_short():
    cand = {**GOOD_COLD_CANDIDATE, "what_changes_if_succeeds": "matters."}
    errs = validate_cold({"candidates": [cand]}, existing_names=set())
    assert any("what_changes_if_succeeds shorter than 100" in e for e in errs)


def test_charter_too_short():
    cand = {**GOOD_COLD_CANDIDATE, "charter_sketch": "short"}
    errs = validate_cold({"candidates": [cand]}, existing_names=set())
    assert any("charter_sketch shorter than 200" in e for e in errs)


def test_good_payload_passes():
    payload = {"candidates": [GOOD_COLD_CANDIDATE]}
    errs = validate_cold(payload, existing_names=set())
    assert errs == []


def test_branch_id_sequence_must_match():
    grid = {
        "name": "test_grid",
        "branches": [{"id": "b1", "name": "x", "obligation": "y"}, {"id": "b2", "name": "x", "obligation": "y"}],
    }
    payload = {
        "candidates": [
            {
                "branch_id": "b2",  # wrong order
                "name": "x_substrate_for_b2",
                "predicted_class": "formal_proof_lean",
                "confidence": "low",
                "rationale": "addresses branch b2 per F-GP186-NS-PHASE5CH-01",
                "falsification_criterion": "lean_target_close: obligation",
                "charter_sketch": "x" * 300,
                "what_changes_if_succeeds": "y" * 150,
            }
        ]
    }
    errs = validate_branch(payload, grid, existing_names=set())
    assert any("branch_id sequence mismatch" in e for e in errs)


def test_branch_rationale_must_cite_branch_id():
    grid = {"name": "g", "branches": [{"id": "b1", "name": "x", "obligation": "y"}]}
    payload = {
        "candidates": [
            {
                "branch_id": "b1",
                "name": "n",
                "predicted_class": "formal_proof_lean",
                "confidence": "low",
                "rationale": "no branch id and no F-row but Phase 5CT mentioned",  # F-row absent, branch_id absent
                "falsification_criterion": "lean_target_close: obligation",
                "charter_sketch": "x" * 300,
                "what_changes_if_succeeds": "y" * 150,
            }
        ]
    }
    errs = validate_branch(payload, grid, existing_names=set())
    assert any("rationale does not cite branch_id" in e for e in errs)
