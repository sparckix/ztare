from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from ztare.common.continual_skill_memory import (
    load_continual_skill_memory,
)
from ztare.common.guarded_experiment_protocol import (
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    price_guarded_protocol,
)
from ztare.common.protocol_information_yield import (
    compile_protocol_information_yield_forecast,
    observe_protocol_information_yield,
)
from ztare.common.task_discharge import (
    TaskDischargeContract,
    TaskDischargeReceipt,
)
from ztare.common.two_stage_eligibility_ledger import (
    assemble_decision_episode_draft,
    load_decision_episode_drafts,
    record_decision_episode_draft,
    save_decision_episode_drafts,
)


def _load_arc3_play_loop():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/public/control/arc3_play_loop.py"
    spec = importlib.util.spec_from_file_location(
        "arc3_play_loop_episode_draft_test",
        path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _yield_receipts(protocol_id: str, observed_response: str):
    candidate = GuardedProtocolCandidate(
        protocol=GuardedExperimentProtocol(
            protocol_id=protocol_id,
            preparation=("prepare",),
            probe="probe",
            target_key="target",
            cost=ProtocolCost(
                preparation_execution_units=1,
                probe_execution_units=1,
                control_units=1,
            ),
            novel_context=False,
        ),
        committee=(
            ProtocolResponseHypothesis("h1", "common"),
            ProtocolResponseHypothesis("h2", "common"),
            ProtocolResponseHypothesis("h3", "rare"),
        ),
    )
    forecast = compile_protocol_information_yield_forecast(
        candidate,
        price_guarded_protocol(
            candidate,
            weights=ProtocolYieldWeights(1.0, 0.0, 0.0),
        ),
    )
    observation = observe_protocol_information_yield(
        forecast,
        observed_response=observed_response,
        observation_evidence_ref=f"live:{protocol_id}",
    )
    return forecast.to_receipt(), observation.to_receipt()


def _window(
    index: int,
    *,
    option: str,
    outcome: str,
    observed_response: str = "common",
):
    forecast, observation = _yield_receipts(
        f"protocol-{index}",
        observed_response,
    )
    return {
        "decision_namespace": "protocol-choice",
        "choice_context_sha256": f"choice-{index}",
        "continuation_context_sha256": "controller-v1",
        "chosen_option_family_sha256": option,
        "chosen_option_variant_sha256": f"{option}-variant-{index}",
        "available_option_family_sha256s": ["advance", "detour"],
        "outcome": outcome,
        "evidence_ref": f"task-adjudication:{index}",
        "information_yield_forecast": forecast,
        "information_yield_observation": observation,
    }


def test_episode_assembly_round_trips_and_rejects_yield_drift(tmp_path):
    windows = (
        _window(0, option="advance", outcome="open"),
        _window(1, option="advance", outcome="attained"),
    )
    draft = assemble_decision_episode_draft(
        windows,
        episode_ref="episode-attained",
        task_contract_sha256="external-task",
        environment_source_sha256="environment-source",
        replay_prefix_sha256="replay-prefix",
        continuation_policy_sha256="policy-v1",
        terminal_task_status="attained",
        terminal_adjudication_ref="terminal:attained",
        terminal_decision_state_sha256="terminal-state",
    )
    assert draft.windows[0].successor_decision_state_sha256 == "choice-1"
    assert draft.windows[-1].successor_decision_state_sha256 == (
        "terminal-state"
    )
    assert not draft.to_receipt()["task_credit_authorized"]

    path = tmp_path / "episodes.json"
    rows = record_decision_episode_draft((), draft)
    rows = record_decision_episode_draft(rows, draft)
    assert len(rows) == 1
    save_decision_episode_drafts(path, rows)
    restored = load_decision_episode_drafts(path)
    assert restored == (draft,)
    assert restored[0].sha256 == draft.sha256
    conflicting_draft = assemble_decision_episode_draft(
        windows,
        episode_ref="episode-attained",
        task_contract_sha256="external-task",
        environment_source_sha256="different-environment",
        replay_prefix_sha256="replay-prefix",
        continuation_policy_sha256="policy-v1",
        terminal_task_status="attained",
        terminal_adjudication_ref="terminal:attained",
        terminal_decision_state_sha256="terminal-state",
    )
    with pytest.raises(ValueError, match="conflicting draft evidence"):
        record_decision_episode_draft(restored, conflicting_draft)

    for field in ("environment_source_sha256", "replay_prefix_sha256"):
        kwargs = {
            "episode_ref": "missing-source",
            "task_contract_sha256": "external-task",
            "environment_source_sha256": "environment-source",
            "replay_prefix_sha256": "replay-prefix",
            "continuation_policy_sha256": "policy-v1",
            "terminal_task_status": "attained",
            "terminal_adjudication_ref": "terminal:attained",
            "terminal_decision_state_sha256": "terminal-state",
        }
        kwargs[field] = ""
        with pytest.raises(ValueError, match=f"{field} must be nonempty"):
            assemble_decision_episode_draft(windows, **kwargs)

    crossed = [dict(row) for row in windows]
    crossed[0] = {
        **crossed[0],
        "information_yield_observation": {
            **crossed[0]["information_yield_observation"],
            "forecast_sha256": "different-forecast",
        },
    }
    with pytest.raises(ValueError, match="crossed yield forecast identity"):
        assemble_decision_episode_draft(
            crossed,
            episode_ref="crossed",
            task_contract_sha256="external-task",
            environment_source_sha256="environment-source",
            replay_prefix_sha256="replay-prefix",
            continuation_policy_sha256="policy-v1",
            terminal_task_status="attained",
            terminal_adjudication_ref="terminal:attained",
            terminal_decision_state_sha256="terminal-state",
        )

    unavailable = [dict(row) for row in windows]
    unavailable[0] = {
        **unavailable[0],
        "information_yield_observation": {
            "schema": (
                "ztare-protocol-information-yield-observation-"
                "unavailable-v1"
            ),
            "status": "unavailable",
            "task_credit_authorized": False,
        },
    }
    with pytest.raises(ValueError, match="observation is unavailable"):
        assemble_decision_episode_draft(
            unavailable,
            episode_ref="unavailable",
            task_contract_sha256="external-task",
            environment_source_sha256="environment-source",
            replay_prefix_sha256="replay-prefix",
            continuation_policy_sha256="policy-v1",
            terminal_task_status="attained",
            terminal_adjudication_ref="terminal:attained",
            terminal_decision_state_sha256="terminal-state",
        )

    wrong_measure = [dict(row) for row in windows]
    wrong_measure[0] = {
        **wrong_measure[0],
        "information_yield_observation": {
            **wrong_measure[0]["information_yield_observation"],
            "measure_sha256": "different-measure",
        },
    }
    with pytest.raises(ValueError, match="yield measure identity"):
        assemble_decision_episode_draft(
            wrong_measure,
            episode_ref="wrong-measure",
            task_contract_sha256="external-task",
            environment_source_sha256="environment-source",
            replay_prefix_sha256="replay-prefix",
            continuation_policy_sha256="policy-v1",
            terminal_task_status="attained",
            terminal_adjudication_ref="terminal:attained",
            terminal_decision_state_sha256="terminal-state",
        )

    missing_evidence = [dict(row) for row in windows]
    missing_evidence[0] = {
        **missing_evidence[0],
        "information_yield_observation": {
            **missing_evidence[0]["information_yield_observation"],
            "observation_evidence_ref": "",
        },
    }
    with pytest.raises(ValueError, match="lacks evidence identity"):
        assemble_decision_episode_draft(
            missing_evidence,
            episode_ref="missing-evidence",
            task_contract_sha256="external-task",
            environment_source_sha256="environment-source",
            replay_prefix_sha256="replay-prefix",
            continuation_policy_sha256="policy-v1",
            terminal_task_status="attained",
            terminal_adjudication_ref="terminal:attained",
            terminal_decision_state_sha256="terminal-state",
        )


def test_play_loop_automatically_persists_unbound_episode_once(
    tmp_path,
    monkeypatch,
):
    module = _load_arc3_play_loop()
    contract = TaskDischargeContract(
        contract_id="episode-draft",
        adjudicator_id="test.episode.v1",
        lifecycle_scope="run",
        owner="test-profile",
    )
    forecast, observation = _yield_receipts(
        "selected-protocol",
        "common",
    )

    class Adapter(SimpleNamespace):
        def adjudicate_task_discharge(self, active_contract):
            return TaskDischargeReceipt(
                contract_sha256=active_contract.sha256,
                adjudicator_id=active_contract.adjudicator_id,
                status="open",
                authority="test_adapter",
                observed={"epoch": self.current_epoch},
                evidence_refs=(),
            )

    def fake_pursue_goal(_adapter, _model, max_steps, **_kw):
        return SimpleNamespace(
            status="plan_exhausted",
            steps_executed=1,
            levels_gained=0,
            saturated=False,
            observed_transitions=[],
            divergence=None,
            trace=[0],
            planning_outcome={
                "task_decision_choice": {
                    "decision_namespace": "protocol-choice",
                    "choice_context_sha256": "choice-source",
                    "continuation_context_sha256": "controller-v1",
                    "chosen_option_family_sha256": "advance",
                    "chosen_option_variant_sha256": "advance-variant",
                    "available_option_family_sha256s": [
                        "advance",
                        "detour",
                    ],
                    "information_yield_forecast": forecast,
                    "information_yield_observation": observation,
                },
            },
        )

    monkeypatch.setattr(module, "pursue_goal", fake_pursue_goal)

    def run_once():
        return module._play_round_multilife(
            Adapter(
                current_epoch=2,
                state=((0,),),
                t=0,
                action_arity=2,
            ),
            object(),
            budget=1,
            context_log=[],
            task_contract=contract,
            receipts_dir=tmp_path,
            temporal_environment_source_sha256="environment-source",
            carrier_execution_sha256="carrier-execution",
        )

    first = run_once()
    assert first.temporal_episode_draft["status"] == "recorded", (
        first.temporal_episode_draft
    )
    assert first.temporal_episode_draft["ledger_count_before"] == 0
    assert first.temporal_episode_draft["ledger_count_after"] == 1
    episodes = load_decision_episode_drafts(
        tmp_path / "temporal_decision_episode_drafts.json"
    )
    assert len(episodes) == 1
    assert episodes[0].terminal_task_status == "open"
    assert not episodes[0].to_receipt()["task_credit_authorized"]

    memory = load_continual_skill_memory(
        tmp_path / "continual_skill_memory.json"
    )
    assert len(memory.task_decision_experiences) == 1
    assert memory.temporal_decision_chains == ()

    second = run_once()
    assert second.temporal_episode_draft["status"] == "recorded"
    assert second.temporal_episode_draft["ledger_count_before"] == 1
    assert second.temporal_episode_draft["ledger_count_after"] == 1
    assert len(load_decision_episode_drafts(
        tmp_path / "temporal_decision_episode_drafts.json"
    )) == 1
