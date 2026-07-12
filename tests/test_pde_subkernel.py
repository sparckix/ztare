from ztare.pde.subkernel import build_pde_subkernel_status


def test_pde_subkernel_status_checks_registry_runners_and_boundaries() -> None:
    status = build_pde_subkernel_status()

    assert status["schema"] == "pde-subkernel-status-v1"
    assert status["ready"] is True
    assert status["gate_count"] >= 10
    assert status["runner_import_errors"] == []
    assert "pec_l" in status["gates_by_op"]
    assert status["canonical_modules"]["work_order"] == "ztare.pde.work_order"
    assert status["canonical_modules"]["ops"] == "ztare.pde.ops"
    assert status["canonical_modules"]["currency"] == "ztare.pde.currency"
    assert status["canonical_modules"]["estimates"] == "ztare.pde.estimates"
    assert status["canonical_modules"]["receipts"] == "ztare.pde.receipts"
    assert status["canonical_modules"]["knowledge_service"] == "ztare.pde.knowledge_service"
    assert status["canonical_modules"]["completion_audit"] == "ztare.pde.completion_audit"
    assert status["architecture_requirement_status_counts"]["implemented"] >= 12
    req_ids = {
        item["requirement_id"]
        for item in status["architecture_requirements"]
    }
    assert "leanmill.failure.memory.adapter" in req_ids
    assert "pde.operator.numerics.plugins" in req_ids
    assert "leanmill_service" in status["service_boundaries"]
    assert any("receipt schemas" in item for item in status["capabilities"])
