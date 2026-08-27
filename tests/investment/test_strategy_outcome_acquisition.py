from ztare.common.equivariance import stable_sha256
from ztare.investment.contracts import MetricObservation, PointInTimeSnapshot
from ztare.investment.sources import SOURCE_RUN_SCHEMA
from ztare.investment.strategy_learning import STRATEGY_MOVE_LIBRARY_SCHEMA
from ztare.investment.strategy_outcome_acquisition import (
    compile_strategy_outcome_acquisition,
    compile_strategy_outcome_source_plan,
    compile_strategy_program_control_outcome_acquisition,
    compile_strategy_program_outcome_acquisition,
)


def test_outcome_acquisition_uses_frozen_periods_and_admitted_sources():
    contract = {
        "contract_sha256": "c" * 64, "metric_id": "segment_margin", "unit": "ratio",
        "direction": "increase", "minimum_effect": 0.02, "comparator": "pre_move_baseline",
        "measurement_start_at": "2025-01-01T00:00:00Z", "due_at": "2026-01-01T00:00:00Z",
        "evidence_refs": ["issuer-contract"],
        "outcome_role": "leading_operating",
        "acquisition_mode": "point_in_time_observation",
    }
    library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA,
        "moves": [{
            "entity_id": "ABC", "move_sha256": "a" * 64, "description": "Expand capacity",
            "mechanism": {"action": "expand_capacity"}, "implementation_event": {},
            "outcome_contracts": [contract], "outcome_episodes": [],
        }],
    }

    def observation(identity, value, observed, available, source="issuer_facts"):
        return MetricObservation(
            observation_id=identity, entity_id="ABC", metric_id="segment_margin",
            value=value, unit="ratio", observed_at=observed, available_at=available,
            source_ref=source,
        )

    rows = (
        observation("old", 0.08, "2024-01-01T00:00:00Z", "2024-02-01T00:00:00Z"),
        observation("baseline", 0.10, "2025-01-01T00:00:00Z", "2025-02-01T00:00:00Z"),
        observation("outcome", 0.14, "2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z"),
        observation("later", 0.30, "2026-06-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        observation("unadmitted", 0.99, "2026-01-01T00:00:00Z", "2026-01-15T00:00:00Z", "unknown"),
    )
    snapshot = PointInTimeSnapshot(
        snapshot_id="outcomes", as_of="2026-08-01T00:00:00Z", source_path="observations.csv",
        source_sha256="f" * 64, observations=rows, excluded_future_count=0,
    )
    source_run = {
        "schema": SOURCE_RUN_SCHEMA, "as_of": snapshot.as_of, "run_sha256": "b" * 64,
        "source_receipts": [{"source_id": "issuer_facts"}], "signal_receipts": [],
    }
    result = compile_strategy_outcome_acquisition(library, snapshot, source_run)
    outcome = result["eligible_outcomes"][0]["outcome"]

    assert result["due_contract_count"] == result["eligible_outcome_count"] == 1
    assert (outcome["baseline_value"], outcome["outcome_value"]) == (0.10, 0.14)
    assert outcome["source_refs"] == ["issuer_facts"]
    assert outcome["point_in_time_evidence"] == {
        "source_run_sha256": "b" * 64,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "baseline_observation_ids": ["baseline"],
        "outcome_observation_ids": ["outcome"],
    }
    assert result["capital_authority"] is False

    readout_body = {
        "metric_id": "segment_margin", "unit": "ratio", "direction": "increase",
        "minimum_effect": 0.02, "horizon_days": 365,
        "comparator": "pre_move_baseline", "measurement_start_at": "2025-01-01T00:00:00Z",
        "due_at": "2026-01-01T00:00:00Z", "supporting_option_ids": ["a", "b"],
        "basis_contract_sha256s": ["1" * 64, "2" * 64],
        "constituent_coverage_count": 2, "constituent_option_count": 3,
        "selection_rule": "all exact contract signatures shared by at least two constituent moves",
    }
    readout = {**readout_body, "readout_sha256": stable_sha256(readout_body)}
    plan_body = {
        "schema": "jaggedthoughts-strategy-program-outcome-plan-v1",
        "request_sha256": "1" * 64, "result_sha256": "2" * 64,
        "entity_id": "ABC", "status": "prospective_readouts_frozen",
        "program_id": "program", "program_expression": "combine(a,b,c)",
        "constituent_option_count": 3, "readout_count": 1, "readouts": [readout],
        "next_activation": "Acquire later.", "interpretation_boundary": "descriptive",
        "causal_program_credit_eligible": False, "portfolio_weight": 0.0,
        "capital_authority": False,
    }
    plan = {**plan_body, "plan_sha256": stable_sha256(plan_body)}
    program = compile_strategy_program_outcome_acquisition([plan], [], snapshot, source_run)
    episode = program["eligible_episodes"][0]
    assert (episode["baseline_value"], episode["outcome_value"], episode["assessment"]) == (0.10, 0.14, "supports")
    assert episode["point_in_time_evidence"]["outcome_observation_ids"] == ["outcome"]
    assert episode["causal_program_credit_eligible"] is False

    control_plan_body = {
        "schema": "jaggedthoughts-strategy-program-control-outcome-plan-v1",
        "request_sha256": "3" * 64, "result_sha256": "4" * 64,
        "entity_id": "ABC", "program_id": "control-program",
        "control_identity": "same_constituents_without_joint_evidence",
        "metric_id": "segment_margin", "unit": "ratio", "direction": "increase",
        "minimum_effect": 0.02, "horizon_days": 365,
        "comparator": "assessment_time_baseline",
        "measurement_start_at": "2025-01-01T00:00:00Z",
        "due_at": "2026-01-01T00:00:00Z", "environment_boundaries": ["software"],
        "basis_contract_sha256s": ["1" * 64, "2" * 64],
        "selection_rule": "fixed period selection",
    }
    control_plan = {
        **control_plan_body, "control_plan_sha256": stable_sha256(control_plan_body),
    }
    acquisition_card = {
        "transfer_card_sha256": "5" * 64,
        "admitted_source_controls": [{"control_readout": control_plan}],
    }
    acquisition_card = {
        **acquisition_card,
        "acquisition_card_sha256": stable_sha256(acquisition_card),
    }
    acquisition_body = {
        "schema": "jaggedthoughts-strategy-program-control-acquisition-v1",
        "cards": [acquisition_card],
    }
    acquisition = {
        **acquisition_body, "acquisition_sha256": stable_sha256(acquisition_body),
    }
    control = compile_strategy_program_control_outcome_acquisition(
        acquisition, [], snapshot, source_run,
    )["eligible_episodes"][0]
    assert (control["baseline_value"], control["outcome_value"]) == (0.10, 0.14)
    assert control["control_identity"] == "same_constituents_without_joint_evidence"
    assert control["causal_program_credit_eligible"] is False


def test_due_outcome_source_plan_selects_only_affected_company_facts():
    contract = {
        "contract_sha256": "c" * 64, "metric_id": "operating_margin_q",
        "unit": "decimal", "direction": "increase", "minimum_effect": 0.01,
        "comparator": "pre_move_baseline", "measurement_start_at": "2026-01-01T00:00:00Z",
        "due_at": "2026-04-01T00:00:00Z", "evidence_refs": ["sec"],
        "outcome_role": "leading_operating", "acquisition_mode": "point_in_time_observation",
    }
    library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA,
        "moves": [{
            "entity_id": "ABC", "move_sha256": "a" * 64, "description": "Expand",
            "outcome_contracts": [contract], "outcome_episodes": [],
        }],
    }
    manifest = {
        "schema": "jaggedthoughts-public-source-manifest-v1",
        "sources": [
            {"id": "sec_abc_companyfacts", "adapter": "sec_companyfacts", "entity_id": "ABC"},
            {"id": "sec_xyz_companyfacts", "adapter": "sec_companyfacts", "entity_id": "XYZ"},
            {"id": "yahoo_abc", "adapter": "yahoo_chart_daily", "entity_id": "ABC"},
        ],
    }
    plan = compile_strategy_outcome_source_plan(
        library, manifest, as_of="2026-04-02T00:00:00Z",
    )
    assert plan["source_ids"] == ["sec_abc_companyfacts"]
    assert plan["due_point_in_time_contract_count"] == 1
