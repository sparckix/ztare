import copy
import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment import strategy_alpha_binding as binding
from ztare.investment.strategy_alpha_binding import (
    STRATEGY_ALPHA_ACTION_PROPOSAL_SCHEMA,
    STRATEGY_ALPHA_ARM_ISOLATION_SCHEMA,
    compile_strategy_alpha_arm_views,
    compile_strategy_alpha_deterministic_controls,
    compile_strategy_alpha_action_request,
    compile_strategy_alpha_issuance_action,
    compile_strategy_alpha_procedure,
)


def _write(path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _request(event: dict, *, residual_payoff: float = 0.03) -> dict:
    residual_body = {
        "schema": "jaggedthoughts-direct-strategy-expectation-residual-v1",
        "status": "compiled",
        "baseline": {"horizon_active_return": 0.04},
        "incremental_horizon_payoff": residual_payoff,
        "operating_contract_sha256": "8" * 64,
        "translation": {
            "kind": "direct_operating_hurdle_payoff",
            "causal_effect_earned": False,
        },
        "source_refs": ["filing", "event-a"],
    }
    residual = {**residual_body, "residual_sha256": stable_sha256(residual_body)}
    body = {
        "schema": "jaggedthoughts-strategy-alpha-action-request-v1",
        "created_at": "2026-08-23T00:00:00Z",
        "entity_id": "ACME", "subject_id": "equity:ACME", "horizon_days": 90,
        "nomination_sha256": "1" * 64,
        "dual_outcome_contract_sha256": "2" * 64,
        "candidate_leaf": "3" * 64,
        "phenotype_sha256": "4" * 64,
        "move_sha256": "5" * 64,
        "implementation_event_sha256": "6" * 64,
        "strategy_choice_identity_sha256": "7" * 64,
        "required_arms": ["valuation", "durability", "strategy"],
        "evidence": {
            "candidate": {
                "candidate_id": "equity:ACME", "candidate_sha256": "a" * 64,
                "entity_id": "ACME", "as_of": "2026-08-22T00:00:00Z",
                "valuation": {"summary": {
                    "price_implied_excess_return": (1.04 ** (365.25 / 90)) - 1,
                }},
                "source_refs": ["filing"],
            },
            "quality": {
                "scores": {"durable_earnings_power": 0.8},
                "source_refs": ["filing"],
            },
            "exact_move_event": event,
            "dual_outcome_contract": {"metric_id": "owner_earnings_margin"},
            "strategy_expectation_residual": residual,
        },
    }
    return {**body, "request_sha256": stable_sha256(body)}


def test_strategy_changes_cannot_reach_deterministic_controls(tmp_path) -> None:
    before = _request({"action": "acquire", "source_refs": ["event-a"]})
    after = _request({"action": "divest", "source_refs": ["event-b"]}, residual_payoff=-0.02)
    payoff_only = _request(
        {"action": "acquire", "source_refs": ["event-a"]}, residual_payoff=-0.02,
    )

    before_views, after_views = map(compile_strategy_alpha_arm_views, (before, after))
    assert before_views["valuation"] == after_views["valuation"]
    assert before_views["durability"] == after_views["durability"]
    assert before_views["strategy"] != after_views["strategy"]
    assert before_views["strategy"] == compile_strategy_alpha_arm_views(payoff_only)[
        "strategy"
    ]

    before_controls = compile_strategy_alpha_deterministic_controls(before)
    after_controls = compile_strategy_alpha_deterministic_controls(after)
    assert before_controls == after_controls
    assert before_controls["valuation"]["predicted_active_return"] == pytest.approx(0.04)
    assert before_controls["durability"]["predicted_active_return"] == pytest.approx(0.032)

    views = compile_strategy_alpha_arm_views(before)
    isolation_body = {
        "schema": STRATEGY_ALPHA_ARM_ISOLATION_SCHEMA,
        "generation_mode": "deterministic_controls_plus_masked_strategy_probability",
        "arm_view_sha256s": {
            role: view["arm_view_sha256"] for role, view in views.items()
        },
        "arm_output_sha256s": {role: role * 8 for role in views},
    }
    procedure = compile_strategy_alpha_procedure(
        runtime="codex_subscription", model="gpt-5.6-sol",
        reasoning_effort="medium", output_schema_sha256="9" * 64,
    )
    provider_result = {
        "schema": "jaggedthoughts-strategy-alpha-arm-proposal-v1",
        "role": "strategy", "arm_view_sha256": views["strategy"]["arm_view_sha256"],
        "operating_hurdle_probability": 0.6,
        "explanation": {"basis": "source-bound operating evidence"},
    }
    call_receipt = {"schema": "owned-call-v1", "status": "completed"}
    dispatch_receipt = {"schema": "owned-dispatch-v1", "status": "completed"}
    _write(tmp_path / "result.json", provider_result)
    _write(tmp_path / "call.json", call_receipt)
    _write(tmp_path / "dispatch.json", dispatch_receipt)
    provenance_body = {
        "schema": "jaggedthoughts-subscription-result-provenance-v1",
        "result_path": "result.json", "call_receipt_path": "call.json",
        "dispatch_receipt_path": "dispatch.json",
        "result_sha256": stable_sha256(provider_result),
        "call_receipt_sha256": stable_sha256(call_receipt),
        "dispatch_receipt_sha256": stable_sha256(dispatch_receipt),
        "procedure_sha256": procedure["procedure_sha256"],
        "arm_view_sha256": views["strategy"]["arm_view_sha256"],
    }
    proposal = {
        "schema": STRATEGY_ALPHA_ACTION_PROPOSAL_SCHEMA,
        **{key: before[key] for key in (
            "request_sha256", "nomination_sha256", "dual_outcome_contract_sha256",
            "candidate_leaf", "phenotype_sha256", "move_sha256",
            "implementation_event_sha256", "strategy_choice_identity_sha256",
        )},
        "arm_isolation": {
            **isolation_body, "isolation_sha256": stable_sha256(isolation_body),
        },
        "strategy_procedure": procedure,
        "strategy_provider_result": provider_result,
        "provider_result_provenance": {
            **provenance_body, "provenance_sha256": stable_sha256(provenance_body),
        },
        "arms": [
            *[{
                "role": role,
                "predicted_active_return": row["predicted_active_return"],
                "underperformance_probability": row["underperformance_probability"],
                "explanation": {"rule": row["rule"]},
            } for role, row in before_controls.items()],
            {
                "role": "strategy", "operating_hurdle_probability": 0.6,
                "explanation": {"basis": "source-bound operating evidence"},
            },
        ],
    }
    action = compile_strategy_alpha_issuance_action(
        proposal, before, available_at="2026-08-23T00:01:00Z",
    )
    predictions = {
        arm["candidate_id"].split(":")[0].removeprefix("strategy-alpha-"):
        arm["predicted_active_return"] for arm in action["arms"]
    }
    assert predictions["strategy"] == pytest.approx(0.032 + 0.6 * 0.03)
    assert action["strategy_expectation_residual"]["residual_sha256"] == (
        before["evidence"]["strategy_expectation_residual"]["residual_sha256"]
    )
    _write(
        tmp_path / "closed_book" / "strategy_alpha_action_requests"
        / f"{before['request_sha256']}.json",
        before,
    )
    assert binding._action_matches_persisted_request(tmp_path, action)
    forged_action = copy.deepcopy(action)
    forged_action["operating_hurdle_forecast"]["probability"] = 0.9
    forged_action.pop("action_sha256")
    forged_action["action_sha256"] = stable_sha256(forged_action)
    assert not binding._action_matches_persisted_request(tmp_path, forged_action)


def test_action_request_rejects_rehashed_contract_projection(
    tmp_path, monkeypatch,
) -> None:
    frozen_at = "2026-08-23T00:00:00Z"
    quality_body = {
        "entity_id": "ACME", "as_of": "2026-08-22T00:00:00Z",
        "available_at": "2026-08-22T01:00:00Z", "source_refs": ["filing"],
    }
    quality = {
        **quality_body, "quality_report_sha256": stable_sha256(quality_body),
    }
    candidate_body = {
        "candidate_id": "equity:ACME", "entity_id": "ACME",
        "screen_status": "monitor", "as_of": quality["as_of"],
        "quality_report_sha256": quality["quality_report_sha256"],
        "source_refs": ["filing"],
    }
    candidate = {
        **candidate_body, "candidate_sha256": stable_sha256(candidate_body),
    }
    run_body = {
        "schema": "jaggedthoughts-discovery-run-v1", "run_id": "run-1",
        "candidates": [candidate],
    }
    run = {**run_body, "run_sha256": stable_sha256(run_body)}
    leaf = "a" * 64
    _write(tmp_path / "discovery" / "latest.json", run)
    _write(tmp_path / "discovery" / "latest_record.json", {
        "run_id": run["run_id"], "run_sha256": run["run_sha256"],
        "candidate_leaves": {"equity:ACME": leaf},
    })
    _write(tmp_path / "quality" / "acme.json", quality)
    contract = {
        "contract_sha256": "b" * 64, "metric_id": "owner_earnings_margin",
        "unit": "decimal", "direction": "increase", "minimum_effect": 0.02,
        "comparator": "pre_move_baseline",
        "measurement_start_at": "2026-08-01T00:00:00Z",
        "due_at": "2027-08-01T00:00:00Z",
    }
    attribution = {"strategy_frontier_sha256": "c" * 64}
    event = {
        "move_sha256": "d" * 64,
        "implementation_event_sha256": "e" * 64,
        "strategy_choice_identity_sha256": "f" * 64,
        "available_at": "2026-08-20T00:00:00Z",
        "strategy_program_attribution": attribution,
        "outcome_contracts": [contract], "source_refs": ["filing"],
    }
    phenotype = "1" * 64
    monkeypatch.setattr(binding, "_exact_phenotypes", lambda *args, **kwargs: {
        phenotype: {"exact_events": [event]},
    })
    monkeypatch.setattr(
        binding, "compile_direct_strategy_expectation_residual",
        lambda *args, **kwargs: {"source_refs": ["filing"]},
    )
    dual_body = {
        "schema": "jaggedthoughts-strategy-dual-outcome-contract-v1",
        "entity_id": "ACME", "candidate_leaf": leaf,
        "candidate_sha256": candidate["candidate_sha256"],
        "move_sha256": event["move_sha256"],
        "strategy_choice_identity_sha256": event["strategy_choice_identity_sha256"],
        "mechanism_phenotype_sha256": phenotype,
        "implementation_event_sha256": event["implementation_event_sha256"],
        "implementation_available_at": event["available_at"],
        "strategy_program_attribution": attribution,
        "operating_outcome": contract,
        "security_outcome": {"horizon_days": 90}, "frozen_at": frozen_at,
    }
    dual = {
        **dual_body, "dual_outcome_contract_sha256": stable_sha256(dual_body),
    }
    nomination_body = {
        "schema": "jaggedthoughts-strategy-alpha-episode-nomination-v1",
        "entity_id": "ACME", "candidate_id": "equity:ACME",
        "candidate_leaf": leaf, "candidate_sha256": candidate["candidate_sha256"],
        "horizon_days": 90, "mechanism_phenotype_sha256s": [phenotype],
        "implementation_event_sha256s": [event["implementation_event_sha256"]],
        "dual_outcome_contract": dual, "nominated_at": frozen_at,
    }
    nomination = {
        **nomination_body, "nomination_sha256": stable_sha256(nomination_body),
    }
    assert compile_strategy_alpha_action_request(tmp_path, nomination)[
        "dual_outcome_contract_sha256"
    ] == dual["dual_outcome_contract_sha256"]

    duplicate_body = {**candidate_body, "candidate_id": "equity:ACME:duplicate"}
    duplicate = {
        **duplicate_body, "candidate_sha256": stable_sha256(duplicate_body),
    }
    ambiguous_run_body = {**run_body, "candidates": [candidate, duplicate]}
    ambiguous_run = {
        **ambiguous_run_body, "run_sha256": stable_sha256(ambiguous_run_body),
    }
    _write(tmp_path / "discovery" / "latest.json", ambiguous_run)
    _write(tmp_path / "discovery" / "latest_record.json", {
        "run_id": ambiguous_run["run_id"], "run_sha256": ambiguous_run["run_sha256"],
        "candidate_leaves": {"equity:ACME": leaf},
    })
    with pytest.raises(ValueError, match="ambiguous current candidates"):
        compile_strategy_alpha_action_request(tmp_path, nomination)
    _write(tmp_path / "discovery" / "latest.json", run)
    _write(tmp_path / "discovery" / "latest_record.json", {
        "run_id": run["run_id"], "run_sha256": run["run_sha256"],
        "candidate_leaves": {"equity:ACME": leaf},
    })

    forged = copy.deepcopy(nomination)
    forged["dual_outcome_contract"]["operating_outcome"]["minimum_effect"] = 0.99
    forged["dual_outcome_contract"].pop("dual_outcome_contract_sha256")
    forged["dual_outcome_contract"]["dual_outcome_contract_sha256"] = stable_sha256(
        forged["dual_outcome_contract"]
    )
    forged.pop("nomination_sha256")
    forged["nomination_sha256"] = stable_sha256(forged)
    with pytest.raises(ValueError, match="operating contract"):
        compile_strategy_alpha_action_request(tmp_path, forged)
