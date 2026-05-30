from src.ztare.gates.residual_core_receipt_gate import (
    run_residual_core_receipt_gate,
)


PROFILE = {
    "receipt_key": "core_receipts",
    "receipt_label": "example_core",
    "required_fields": ["source_fact", "required_check", "pass_fail_boundary"],
    "expected_consumers": ["ExampleConsumer.ofCoreReceipt"],
    "incomplete_reason": "core receipt requires fact/check/boundary binding",
    "wrong_consumer_reason": "receipt is bound to the wrong consumer",
    "confuser_sets": [{
        "type": "surface_anchor_laundering",
        "fields": ["surface_anchor"],
        "unless_present": ["visible_fact_binding"],
        "reason": "surface anchor alone does not pay the required check",
    }],
}


def test_residual_core_gate_flags_incomplete_generic_receipt() -> None:
    result = run_residual_core_receipt_gate(
        {"core_receipts": [{"source_fact": "visible fact"}]},
        profile=PROFILE,
    )

    assert result["passed"] is True
    assert result["n_complete_receipts"] == 0
    assert any(
        v["type"] == "example_core_receipt_incomplete"
        and "required_check" in v["missing_fields"]
        for v in result["violations"]
    )


def test_residual_core_gate_flags_profile_confuser() -> None:
    result = run_residual_core_receipt_gate(
        {"core_receipts": [{
            "source_fact": "visible fact",
            "required_check": "exact check",
            "pass_fail_boundary": "PASS iff check is paid",
            "surface_anchor": "mentions evidence path",
            "consumed_by": "ExampleConsumer.ofCoreReceipt",
        }]},
        profile=PROFILE,
    )

    assert result["passed"] is True
    assert any(
        v["type"] == "surface_anchor_laundering"
        for v in result["violations"]
    )


def test_residual_core_gate_accepts_profile_receipt() -> None:
    result = run_residual_core_receipt_gate(
        {"core_receipts": [{
            "source_fact": "visible fact",
            "required_check": "exact check",
            "pass_fail_boundary": "PASS iff exact check is paid",
            "consumed_by": "ExampleConsumer.ofCoreReceipt",
        }]},
        profile=PROFILE,
        enforce_block=True,
    )

    assert result["passed"] is True
    assert result["n_complete_receipts"] == 1
    assert result["violations"] == []


def test_residual_core_gate_blocks_wrong_consumer_when_enforced() -> None:
    result = run_residual_core_receipt_gate(
        {"core_receipts": [{
            "source_fact": "visible fact",
            "required_check": "exact check",
            "pass_fail_boundary": "PASS iff exact check is paid",
            "consumed_by": "OtherConsumer",
        }]},
        profile=PROFILE,
        enforce_block=True,
    )

    assert result["passed"] is False
    assert any(
        v["type"] == "wrong_example_core_consumer"
        for v in result["violations"]
    )
