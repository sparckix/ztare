from ztare.common.equivariance import stable_sha256
from ztare.investment.kernel_removal_trial import (
    ARMS,
    compile_kernel_removal_action,
    compile_kernel_removal_arms,
    compile_kernel_removal_execution_receipt,
)


def test_kernel_removal_trial_freezes_one_source_snapshot_and_four_layers() -> None:
    availability_body = {
        "schema": "jaggedthoughts-field-availability-certificate-v1",
        "as_of": "2026-08-26T00:00:00Z",
        "rows": [], "required_field_paths": [], "unverified_field_paths": [],
        "field_group_count": 0, "verified_field_group_count": 0, "complete": True,
    }
    packet_body = {
        "schema": "jaggedthoughts-closed-book-evidence-packet-v1",
        "opened_at": "2026-08-26T00:00:00Z", "end_at": "2026-11-24T00:00:00Z",
        "horizon_days": 90,
        "subject": {"kind": "paper_watch_decision", "subject_id": "watch:ACME"},
        "entity": {"entity_id": "ACME"}, "benchmark": {"entity_id": "SPY"},
        "starting_market": {}, "observable_contract": {},
        "valuation_summary": {}, "company_quality": {}, "discovery_summary": {},
        "decision_summary": {}, "evidence_archive": {},
        "research_snapshot": {"public_sources": [], "research": {}, "evidence": {}},
        "field_availability": {
            **availability_body,
            "certificate_sha256": stable_sha256(availability_body),
        },
    }
    packet = {**packet_body, "packet_sha256": stable_sha256(packet_body)}
    arms = compile_kernel_removal_arms(packet)
    assert tuple(arms) == ARMS
    assert len({row["common_source_snapshot_sha256"] for row in arms.values()}) == 1
    assert len({row["experiment_design_id"] for row in arms.values()}) == 1
    assert arms["fixed_memo_checklist"]["admitted_machinery"]["fixed_method"]["llm_owned_decomposition"]
    process_body = {
        "schema": "jaggedthoughts-forecast-process-bundle-v1",
        "runtime": "codex", "resolved_model": "gpt-test",
        "model_identity_complete": True, "provider_call_budget_per_role": 1,
        "cross_role_session_reuse": False, "output_schema_sha256": "s" * 64,
    }
    process = {**process_body, "process_bundle_sha256": stable_sha256(process_body)}
    calls = {role: {
        "packet_sha256": arms[role]["packet_sha256"],
        "artifact_ref": f"calls/{role}", "provider_call_charge": 1,
        "call_receipt": {
            "schema": "leanmill.frontier_subscription_role_call.v1",
            "role": f"jaggedthoughts_kernel_removal_{role}",
            "agent_id": f"agent:{role}", "runtime": "codex", "model": "gpt-test",
            "returncode": 0, "provider_call_charge": 1,
            "prompt_digest": stable_sha256({"prompt": role}),
            "result_digest": stable_sha256({"result": role}),
            "output_schema_digest": "s" * 64,
        },
    } for role in ARMS}
    execution = compile_kernel_removal_execution_receipt(
        arm_packets=arms, process_bundle=process, calls=calls,
    )
    action = compile_kernel_removal_action(
        packet, arm_packets=arms,
        forecast_candidate_ids={role: f"kernel_removal_{role}" for role in ARMS},
        process_bundle_sha256=process["process_bundle_sha256"],
        compiled_at="2026-08-26T00:00:01Z", execution_receipt=execution,
    )
    assert action["status"] == "sealed_four_arm_forecast"
    assert action["settlement"]["baseline_arm"] == "direct_public_packet"
