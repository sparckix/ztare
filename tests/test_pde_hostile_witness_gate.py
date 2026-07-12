from ztare.gates.pde_hostile_witness_gate import run_pde_hostile_witness_gate


def _paid_witness() -> dict:
    return {
        "label": "concentrating_spike_tail_failure",
        "witness_family": "u_lambda concentrating annular spike",
        "target_estimate_or_claim": "L1 tail <= C energy",
        "amplitude_scaling": "lambda^(3/2)",
        "support_or_localization": "annulus |x| in [lambda^-1, 2 lambda^-1]",
        "frequency_or_scale_regime": "lambda -> infinity",
        "norm_or_quantity_profile": "energy bounded, tail grows logarithmically",
        "hypotheses_preserved": "div-free and local energy class retained",
        "conclusion_stressed_or_violated": "tail bound loses uniform C",
        "failure_mechanism": "mass concentration beats unsigned tail payment",
        "parameter_limit": "lambda -> infinity",
        "claim_boundary_update": "requires annular bandlimit or owner-prefix payment",
    }


def test_hostile_witness_gate_requires_scaling_and_boundary_update() -> None:
    paid = run_pde_hostile_witness_gate(_paid_witness())
    assert paid["passed"] is True
    assert paid["classification"] == "hostile_witness_receipt_complete"

    weak = dict(_paid_witness())
    weak.pop("hypotheses_preserved")
    weak["counterexample_label_only"] = True
    weak["conclusion_not_evaluated"] = True

    rejected = run_pde_hostile_witness_gate(weak)
    assert rejected["passed"] is False
    assert rejected["missing_fields"] == ["hypotheses_preserved"]
    assert rejected["rejected_substitutes"] == [
        "counterexample_label_only",
        "conclusion_not_evaluated",
    ]
