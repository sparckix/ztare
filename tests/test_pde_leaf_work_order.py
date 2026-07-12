from ztare.pde.work_order import (
    build_pde_leaf_work_order,
    render_pde_leaf_work_order,
)


def test_pde_leaf_work_order_attaches_registry_gates_for_op() -> None:
    work_order = build_pde_leaf_work_order(
        target="annular Riesz L1 PSD trace payment",
        op_id="pec_l",
        goal="audit cancellation and projection payment",
        given={"target_currency": "projected_tracefree_variation"},
        extra_gate_ids=["G-PDE-THEOREM-APPLICABILITY"],
        formal_feedback_requested=True,
    )

    gate_ids = {gate["gate_id"] for gate in work_order["gate_requirements"]}
    assert work_order["schema"] == "pde-leaf-work-order-v1"
    assert work_order["leaf_id"].startswith("pde.leaf.pec_l.")
    assert "G-PDE-ANALYTIC-SUBSTANCE" in gate_ids
    assert "G-PDE-THEOREM-APPLICABILITY" in gate_ids
    assert "G-POSITIVE-VARIATION-BRIDGE" in gate_ids
    assert work_order["formal_feedback_requested"] is True
    assert work_order["must_return"]["verdict"].endswith("NEED_FORMALIZATION")


def test_pde_leaf_work_order_records_unknown_extra_gate_without_crashing() -> None:
    work_order = build_pde_leaf_work_order(
        target="pressure tail reserve",
        op_id="pec_h",
        extra_gate_ids=["G-UNKNOWN"],
    )

    assert any("unknown_extra_gate_ids" in note for note in work_order["notes"])
    rendered = render_pde_leaf_work_order(work_order)
    assert "PDE leaf work order" in rendered
    assert "pec_h" in rendered


def test_pde_leaf_work_order_can_focus_exact_gate_set() -> None:
    work_order = build_pde_leaf_work_order(
        target="annular Riesz PSD canary",
        op_id="pec_l",
        only_gate_ids=[
            "G-PDE-ANALYTIC-SUBSTANCE",
            "G-PDE-OPERATOR-ADMISSIBILITY",
        ],
    )

    gate_ids = [gate["gate_id"] for gate in work_order["gate_requirements"]]

    assert gate_ids == [
        "G-PDE-ANALYTIC-SUBSTANCE",
        "G-PDE-OPERATOR-ADMISSIBILITY",
    ]
    assert "G-PDE-EQUALITY-PROVENANCE" not in gate_ids
    assert any("only_gate_ids supplied" in note for note in work_order["notes"])


def test_pde_leaf_work_order_can_require_process_contract_refs() -> None:
    work_order = build_pde_leaf_work_order(
        target="active Carleson budget identity",
        op_id="pec_l",
        require_process_contract=True,
        pattern_action_contract_ref="pattern_action_contract.json",
        orchestration_contract_ref="orchestration_contract.json",
        pencil_artifact_ref="pencil.md",
    )

    refs = {
        item["artifact_key"]: item["artifact_ref"]
        for item in work_order["process_requirements"]
    }

    assert refs["pattern_action_contract"] == "pattern_action_contract.json"
    assert refs["orchestration_contract"] == "orchestration_contract.json"
    assert refs["pencil_artifact"] == "pencil.md"
    assert "orientation_artifact" in work_order["must_return"]
    rendered = render_pde_leaf_work_order(work_order)
    assert "process requirements" in rendered
    assert "pencil.md" in rendered
