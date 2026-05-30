import importlib.util
from pathlib import Path


HARNESS_PATH = (
    Path(__file__).resolve().parents[2]
    / "projects"
    / "ns_proofsearch_leray_convexity_trackb"
    / "gate_harness.py"
)


def _load_harness():
    spec = importlib.util.spec_from_file_location("trackb_gate_harness", HARNESS_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


VALID_SOURCE = '''
def fixed_profile_topology():
    return {
        "scope": "flat torus periodic smooth divergence-free fields",
        "topology": "fixed LP/Bony Littlewood-Paley dyadic projector profile Sobolev topology declared before payoff",
    }


def self_tax_component_prices():
    return {
        "branch": "fixed topology predeclared profile branch price charges P((u.grad)u) Leray self-tax ledger",
        "lsc": "component lower-semicontinuity LSC is required",
    }


def cross_defect_and_coherence_prices():
    return {
        "A": "A = P((u.grad)u)",
        "B": "B = P((v.grad)v)",
        "C": "C = P((u.grad)v + (v.grad)u)",
        "coherence": "charge positive parts of 2<A,B>, 2<A,C>, 2<B,C>",
        "branch_only_rejected": "branch-only LSC is not sufficient and undercharges known falsifier",
    }


def low_beat_reserve_charge():
    return {
        "beat": "high-high low-beat backscatter has a+b=q output q difference frequency",
        "symbol": "incompressible gives a.b=a.q and b.a=b.q; output frequency |q| controls multiplier",
        "reserve": "physical Sobolev enstrophy vorticity grad-vorticity reserve pays N^2 and N^4",
    }


def all_output_positive_coherence_lsc():
    return {
        "atoms": "all-output Leray output atoms are priced, not hidden source-coordinate source-L2 coordinates",
        "price": "all-output L1 / L^1 positive coherence-aware output pricing with lower-semicontinuity LSC and Fatou profile limit",
        "rejection": "source-L2 source l2 hidden source aggregate is invalid insufficient rejected and not substitute",
    }


def dynamic_event_recurrence_price():
    return {
        "events": "event edge event return event recurrence uses event weight a_e and reciprocal budget",
        "budget": "sum_e 1/a_e over events event-level multiplicity with finite Cauchy duality bounded-overlap",
        "raw": "raw recurrence price preparation lower envelope, not shell-only harmonic recurrence",
    }


def global_self_tax_budget_bridge():
    return {
        "assembly": "local-to-global glue assembly of branch cross-defect coherence reserve all-output continuum and event recurrence prices",
        "budget": "bounded summable prefix price budgets time integral ||P((u.grad)u)|| Leray self-tax integral",
    }


def continuation_price_connection():
    return {
        "identity": "production <P((u.grad)u), Delta u> controlled by Cauchy Young 4 nu",
        "criterion": "d/dt enstrophy continuation BKM regularity criterion is conditional separate not Clay scope",
    }


def smooth_escape_falsifier_or_theorem():
    return {
        "escape": "smooth periodic Sobolev sequence family profile on T^3",
        "prices": "bounded prices bounded prefix bounded reserve with payoff survives or self-tax integral survives",
        "topology": "same fixed topology declared topology theorem or falsifier",
    }


def accepted_bridge_outcome():
    return {
        "outcomes": "honest accepted theorem falsifier counterexample reduction obstruction",
        "coverage": "component LSC coherence low-beat reserve",
        "scope": "not Clay, not global regularity",
    }
'''


def test_trackb_valid_packet_passes_gate():
    harness = _load_harness()
    result = harness.evaluate_source(VALID_SOURCE)

    assert result["all_gates_pass"], result["trackb_gate"]["reasons"]
    assert result["trackb_gate"]["has_fixed_profile_topology"]
    assert result["trackb_gate"]["has_low_beat_reserve_charge"]


def test_trackb_missing_required_function_fails_before_judge():
    harness = _load_harness()
    source = VALID_SOURCE.replace(
        "def low_beat_reserve_charge():",
        "def low_beat_reserve_note():",
    )
    result = harness.evaluate_source(source)

    assert not result["all_gates_pass"]
    assert any("low_beat_reserve_charge" in reason for reason in result["trackb_gate"]["reasons"])


def test_trackb_rejected_degree_only_context_does_not_trip_banned_focus():
    harness = _load_harness()
    source = (
        VALID_SOURCE
        + '\nREJECTED = {"forbidden": "degree-only q>p scaling is rejected"}\n'
    )
    result = harness.evaluate_source(source)

    assert result["all_gates_pass"], result["trackb_gate"]["reasons"]


def test_trackb_positive_degree_only_claim_fails():
    harness = _load_harness()
    source = VALID_SOURCE.replace(
        '"scope": "not Clay, not global regularity",',
        '"scope": "degree-only q>p scaling proves Track B",',
    )
    result = harness.evaluate_source(source)

    assert not result["all_gates_pass"]
    assert "degree-only scaling" in result["trackb_gate"]["reasons"]


def test_trackb_rejected_clay_phrase_does_not_trip_overclaim():
    harness = _load_harness()
    source = "# DO NOT CLAIM NS OR CLAY PROOF. This is not a proof.\\n" + VALID_SOURCE
    result = harness.evaluate_source(source)

    assert result["all_gates_pass"], result["trackb_gate"]["reasons"]


def test_trackb_negative_scope_list_does_not_trip_clay_overclaim():
    harness = _load_harness()
    source = VALID_SOURCE.replace(
        '"scope": "not Clay, not global regularity",',
        '"not_accepted_as": ["Clay proof", "global regularity proof"],',
    )
    result = harness.evaluate_source(source)

    assert result["all_gates_pass"], result["trackb_gate"]["reasons"]


def test_trackb_iter1_low_beat_notation_passes_gate():
    harness = _load_harness()
    source = VALID_SOURCE.replace(
        '"beat": "high-high low-beat backscatter has a+b=q output q difference frequency",\n'
        '        "symbol": "incompressible gives a.b=a.q and b.a=b.q; output frequency |q| controls multiplier",',
        '"beat": "high-high low-beat backscatter has k + l = m with low output |m|",\n'
        '        "symbol": "divergence-free gives uhat_k.l = uhat_k.m and vhat_l.k = vhat_l.m; output frequency |m| controls multiplier",',
    )
    result = harness.evaluate_source(source)

    assert result["all_gates_pass"], result["trackb_gate"]["reasons"]


def test_trackb_small_semantic_marker_gap_reaches_judge_as_near_miss():
    harness = _load_harness()
    source = VALID_SOURCE.replace("not Clay, not global regularity", "scope limited")
    result = harness.evaluate_source(source)

    assert result["all_gates_pass"], result["trackb_gate"]["reasons"]
    assert result["semantic_near_miss"] is True
    assert result["content_warnings"]


def test_trackb_large_semantic_gap_still_blocks():
    harness = _load_harness()
    source = '''
def fixed_profile_topology(): return {"claim": "present"}
def self_tax_component_prices(): return {"claim": "present"}
def cross_defect_and_coherence_prices(): return {"claim": "present"}
def low_beat_reserve_charge(): return {"claim": "present"}
def global_self_tax_budget_bridge(): return {"claim": "present"}
def all_output_positive_coherence_lsc(): return {"claim": "present"}
def dynamic_event_recurrence_price(): return {"claim": "present"}
def continuation_price_connection(): return {"claim": "present"}
def smooth_escape_falsifier_or_theorem(): return {"claim": "present"}
def accepted_bridge_outcome(): return {"claim": "present"}
'''
    result = harness.evaluate_source(source)

    assert not result["all_gates_pass"]
    assert result["semantic_missing_group_count"] > 2
