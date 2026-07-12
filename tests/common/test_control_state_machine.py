from __future__ import annotations

from ztare.common.control_state_machine import (
    ControlLedgerSurface,
    ControlMorphism,
    ControlStateChart,
    ControlTransition,
    control_receipt_rows,
    control_ledger_surfaces_object,
    executed_morphism_ids_from_receipts,
    receipt_objects_json_after_marker,
    render_control_state_chart_surface,
    render_control_state_surface,
)


def test_control_state_surface_distinguishes_executed_from_admissible_next() -> None:
    surface = render_control_state_surface(
        heading="WORKBENCH STATE",
        executed_morphisms=["run_strategy_required_gate"],
        carried_receipts_json='[{"type":"LEAF_WORKBENCH_RECEIPT","payload":{"capability_id":"run_strategy_required_gate"}}]',
        admissible_next=[
            ControlMorphism(
                capability_id="run_visible_json_probe",
                input_refs={
                    "artifact_refs": ["workspace/latest_patch_base_regression.json"],
                },
                claim_bindings=["separate quotient"],
            )
        ],
    )

    assert "WORKBENCH STATE" in surface
    assert '"run_strategy_required_gate"' in surface
    assert '"capability_id":"run_visible_json_probe"' in surface
    assert "LEAF_WORKBENCH_ACTION_REQUEST" in surface
    assert "LEAF_WORKBENCH_ACTION_CONTRACT" not in surface
    assert "RESULT = ..." not in surface
    assert "workspace/latest_patch_base_regression.json" in surface
    assert "kernel-retained" in surface
    assert "Ready-to-use receipt object(s)" not in surface
    assert "copy it into `control_receipts`" not in surface


def test_receipt_marker_helpers_accept_pretty_printed_receipts() -> None:
    text = """
LEAF_WORKBENCH_RECEIPT: {
  "capability_id": "run_strategy_required_gate",
  "output_summary": "status=bounded_mismatch"
}
"""

    assert executed_morphism_ids_from_receipts(text) == ["run_strategy_required_gate"]
    rendered = receipt_objects_json_after_marker(text)
    assert '"type":"LEAF_WORKBENCH_RECEIPT"' in rendered
    assert '"capability_id":"run_strategy_required_gate"' in rendered


def test_control_receipt_rows_accept_raw_json_and_rendered_markers() -> None:
    raw = '{"control_receipts":[{"type":"VISIBLE_WORKBENCH_DIAGNOSTIC","payload":{"capability_id":"score_worldmodel_candidate_delta"}}]}'
    rendered = 'LEAF_WORKBENCH_RECEIPT: {"capability_id":"run_strategy_required_gate"}'

    assert control_receipt_rows(raw) == [
        {
            "type": "VISIBLE_WORKBENCH_DIAGNOSTIC",
            "payload": {"capability_id": "score_worldmodel_candidate_delta"},
        }
    ]
    assert executed_morphism_ids_from_receipts(raw + "\n" + rendered) == [
        "score_worldmodel_candidate_delta",
        "run_strategy_required_gate",
    ]


def test_control_state_chart_renders_serializable_lifecycle() -> None:
    chart = ControlStateChart(
        schema="example-lifecycle-v1",
        transitions=(
            ControlTransition(
                state="await_declaration",
                event="commit_declaration",
                next="await_payload",
                invariant="declaration is immutable",
            ),
            ControlTransition(
                state="await_payload",
                event="payload_generated",
                next="ready",
                invariant="payload carries declaration",
            ),
        ),
    )

    assert chart.next_state("await_declaration", "commit_declaration") == "await_payload"
    assert chart.next_state("await_payload", "unknown") is None
    assert chart.admissible_events("await_payload") == ["payload_generated"]

    surface = render_control_state_chart_surface(
        chart=chart,
        state="await_payload",
        context={"committed": True},
        heading="RUNNER",
        boundary_rule="payload edits only",
    )

    assert "example-lifecycle-v1" in surface
    assert '"admissible_events":["payload_generated"]' in surface
    assert '"committed":true' in surface
    assert "payload edits only" in surface


def test_control_ledger_surfaces_are_contract_pointers_not_taxonomy() -> None:
    surfaces = control_ledger_surfaces_object(
        (
            ControlLedgerSurface(
                surface="tool_synthesis_strategy_card",
                contract="ztare.common.tool_synthesis_contract",
                authority="Strategy Office card plus tool_synthesis_gate",
            ),
        )
    )

    assert surfaces == [
        {
            "surface": "tool_synthesis_strategy_card",
            "contract": "ztare.common.tool_synthesis_contract",
            "authority": "Strategy Office card plus tool_synthesis_gate",
        }
    ]
