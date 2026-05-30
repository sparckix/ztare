from src.ztare.gates.theorem_packet_gate import (
    FunctionContract,
    TheoremPacketGateSpec,
    canonical_contract_text,
    evaluate_theorem_packet,
    function_source,
)


def test_function_source_returns_only_module_scope_function():
    source = '''
def target():
    return "module"

def wrapper():
    def target():
        return "nested"
    return target()
'''
    text = function_source(source, "target")

    assert 'return "module"' in text
    assert "nested" not in text


def test_packet_groups_can_be_satisfied_across_declared_scope():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(
                name="observable_class",
                description="declaring observable scope.",
                own_groups=(("observable",), ("fixed",)),
                packet_groups=(("positive", "psd"), ("damping",)),
                packet_scope=("dual_kernel",),
            ),
            FunctionContract(
                name="dual_kernel",
                description="declaring dual kernel.",
                own_groups=(("certificate",),),
            ),
        ),
        banned_groups={},
    )
    source = '''
def observable_class():
    return {"scope": "fixed observable class"}

def dual_kernel():
    return {"certificate": "positive PSD certificate with damping"}
'''
    result = evaluate_theorem_packet(source, spec)

    assert result["all_gates_pass"], result["reasons"]


def test_positive_banned_phrase_fails_but_rejected_phrase_passes():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(name="theorem", description=".", own_groups=(("claim",),)),
        ),
        banned_groups={"degree-only scaling": ("degree-only", "q>p")},
    )
    rejected = '''
def theorem():
    return {"claim": "valid claim", "not_allowed": "degree-only q>p scaling is forbidden"}
'''
    positive = '''
def theorem():
    return {"claim": "degree-only q>p scaling proves the theorem"}
'''

    assert evaluate_theorem_packet(rejected, spec)["all_gates_pass"]
    result = evaluate_theorem_packet(positive, spec)
    assert not result["all_gates_pass"]
    assert "degree-only scaling" in result["reasons"]


def test_contract_text_normalizes_unicode_math_and_camel_case():
    text = "FullFixedTopologyLowHighOperatorReceipt -> LowHighBonyOperatorEstimateRealityCheck; |<Λ H, Δ_j H>| ≤ C||∇L||_∞"
    normalized = canonical_contract_text(text)

    assert "full fixed topology low high operator receipt" in normalized
    assert "low high bony operator estimate reality check" in normalized
    assert "lambda h" in normalized
    assert "delta j" in normalized
    assert "grad l" in normalized
    assert "infty" in normalized


def test_compound_theorem_packet_terms_satisfy_contract_groups():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(
                name="accepted_branch_outcome",
                description="enumerating honest accepted outcomes and scope.",
                own_groups=(
                    ("theorem", "final_theorem", "falsifier"),
                    ("branch-local", "branch_scope", "low-high", "lp/bony"),
                    ("honest", "accepted", "outcome"),
                ),
            ),
        ),
        banned_groups={},
    )
    source = '''
def accepted_branch_outcome():
    return {
        "aggregated_status": "FullFixedTopologyLowHighOperatorReceipt -> LowHighBonyOperatorEstimateRealityCheck complete.",
        "honest_outcome": "Accepted theorem packet with local estimate scope."
    }
'''

    result = evaluate_theorem_packet(source, spec)

    assert result["all_gates_pass"], result["reasons"]


def test_content_groups_can_be_soft_diagnostics():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(
                name="receipt",
                description="declaring a receipt.",
                own_groups=(("must_have_this_exact_semantic_marker",),),
            ),
        ),
        banned_groups={},
        content_groups_hard=False,
    )
    source = '''
def receipt():
    return {"claim": "structurally present but sparse"}
'''

    result = evaluate_theorem_packet(source, spec)

    assert result["all_gates_pass"]
    assert not result["reasons"]
    assert result["content_warnings"]


def test_soft_content_mode_still_blocks_missing_functions_and_baseline():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(
                name="receipt",
                description="declaring a receipt.",
                own_groups=(("marker",),),
            ),
        ),
        banned_groups={},
        content_groups_hard=False,
    )
    missing = evaluate_theorem_packet("", spec)
    baseline = evaluate_theorem_packet('def receipt():\n    return "baseline_incomplete marker"\n', spec)

    assert not missing["all_gates_pass"]
    assert "Missing top-level receipt()" in missing["reasons"][0]
    assert not baseline["all_gates_pass"]
    assert baseline["reasons"] == ["Baseline skeleton copied without completing the theorem packet."]


def test_semantic_near_miss_budget_passes_small_content_gap_with_warning():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(
                name="receipt",
                description="declaring a receipt.",
                own_groups=(("fixed",), ("exact_marker_a",), ("exact_marker_b",)),
            ),
        ),
        banned_groups={},
        semantic_near_miss_missing_group_budget=1,
    )
    source = '''
def receipt():
    return {"claim": "fixed object with exact_marker_a"}
'''

    result = evaluate_theorem_packet(source, spec)

    assert result["all_gates_pass"], result["reasons"]
    assert result["semantic_near_miss"] is True
    assert result["semantic_missing_group_count"] == 1
    assert result["content_warnings"]
    assert result["gates"][0]["near_miss"] is True


def test_semantic_near_miss_budget_blocks_large_content_gap():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(
                name="receipt",
                description="declaring a receipt.",
                own_groups=(("fixed",), ("exact_marker_a",), ("exact_marker_b",)),
            ),
        ),
        banned_groups={},
        semantic_near_miss_missing_group_budget=1,
    )
    source = '''
def receipt():
    return {"claim": "fixed object only"}
'''

    result = evaluate_theorem_packet(source, spec)

    assert not result["all_gates_pass"]
    assert result["semantic_near_miss"] is False
    assert result["semantic_missing_group_count"] == 2
    assert result["reasons"]
    assert not result["content_warnings"]


def test_semantic_near_miss_budget_still_blocks_placeholders():
    spec = TheoremPacketGateSpec(
        gate_name="HOLDOUT",
        threshold="toy",
        functions=(
            FunctionContract(
                name="receipt",
                description="declaring a receipt.",
                own_groups=(("fixed",),),
            ),
        ),
        banned_groups={},
        semantic_near_miss_missing_group_budget=3,
    )
    source = '''
def receipt():
    return {"claim": "TODO fixed"}
'''

    result = evaluate_theorem_packet(source, spec)

    assert not result["all_gates_pass"]
    assert result["semantic_missing_group_count"] == 1
    assert "placeholder/unknown content" in result["reasons"][0]
