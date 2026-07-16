from ztare.leanmill.resume_runtime_preflight import resume_runtime_preflight


def test_resume_runtime_preflight_imports_transition_closure_and_strict_schema():
    receipt = resume_runtime_preflight()

    assert receipt["status"] == "passed"
    assert receipt["provider_calls"] == 0
    assert set(receipt["callable_symbols"]) == {
        "bind_task_discharge_receipt",
        "drive_frontier_campaign",
        "execute_adapter_forge_attempt",
        "execute_frontier_boundaries",
        "make_formalization_campaign_task_executor",
    }
    assert len(receipt["navigator_output_schema_sha256"]) == 64
    assert receipt["receipt_sha256"]
