from src.ztare.gates.residual_core_receipt_gate import (
    run_residual_core_receipt_gate,
)


PROFILE = {
    "receipt_key": "fresh_annular_anti_laundering_receipts",
    "receipt_label": "fresh_annular_anti_laundering",
    "required_fields": [
        "not_monotone_tail",
        "not_scalar_measure",
        "same_separated_source",
        "consumed_by",
    ],
    "expected_consumers": ["C7OwnerGeometryResidualBridge"],
    "incomplete_reason": "receipt fields must contain evidence, not placeholders",
}


def test_placeholder_string_does_not_complete_required_field():
    result = run_residual_core_receipt_gate(
        {
            "fresh_annular_anti_laundering_receipts": [
                {
                    "name": "placeholder_receipt",
                    "not_monotone_tail": "missing",
                    "not_scalar_measure": "C7 non-scalar morphology theorem",
                    "same_separated_source": "same source proof",
                    "consumed_by": "C7OwnerGeometryResidualBridge",
                }
            ]
        },
        profile=PROFILE,
        expect_receipt=True,
    )

    assert result["n_complete_receipts"] == 0
    assert result["violations"][0]["type"] == (
        "fresh_annular_anti_laundering_receipt_incomplete"
    )
    assert result["violations"][0]["missing_fields"] == ["not_monotone_tail"]


def test_real_strings_and_consumer_list_complete_receipt():
    result = run_residual_core_receipt_gate(
        {
            "fresh_annular_anti_laundering_receipts": [
                {
                    "name": "paid_receipt",
                    "not_monotone_tail": "proved by theorem A",
                    "not_scalar_measure": "proved by theorem B",
                    "same_separated_source": "rfl",
                    "consumed_by": [
                        "C7OwnerGeometryResidualBridge.ofOwnerLineageAndAntiLaundering"
                    ],
                }
            ]
        },
        profile=PROFILE,
        expect_receipt=True,
    )

    assert result["violations"] == []
    assert result["n_complete_receipts"] == 1
