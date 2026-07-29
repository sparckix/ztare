from __future__ import annotations

from types import SimpleNamespace
import subprocess
from pathlib import Path
import json

import pytest

from ztare.leanmill.frontier_agent_runtime import (
    FrontierAgentConfig,
    FrontierRolePreDispatchContractError,
    SubscriptionJSONRole,
    _validate_codex_strict_schema,
    _provider_call_charge,
    _parse_last_json_object,
    make_subscription_frontier_compiler_roles,
    make_subscription_theory_navigator,
)
from ztare.leanmill.frontier_blueprint_compiler import render_frontier_blueprint_prompt
from ztare.leanmill.theory_ir import content_hash


def test_successor_navigator_preserves_root_campaign_identity(monkeypatch):
    captured = {}

    def fake_run(*_args, **kwargs):
        captured.update(kwargs)
        return {"status": "fixture"}

    monkeypatch.setattr(
        "ztare.leanmill.theory_navigator.run_interactive_theory_navigator",
        fake_run,
    )

    class Role:
        def __call__(self, _prompt):
            return {}

    navigator = make_subscription_theory_navigator(
        Role(),
        attempt_id="attempt:successor",
        campaign_id="campaign:root-identity",
    )
    blueprint = SimpleNamespace(
        blueprint_id="blueprint:successor-identity",
        query_budget={"max_finalists": 1, "navigator_rounds": 1},
    )
    navigator(
        SimpleNamespace(),
        blueprint,
        SimpleNamespace(),
        budget_ledger=None,
    )

    assert captured["campaign_id"] == "campaign:root-identity"


def test_subscription_json_role_persists_and_replays_without_second_call(tmp_path, monkeypatch):
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        Path(kwargs["output_last_message_path"]).write_text(
            '{"accepted":true}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["agent"], 0, stdout='log\n{"accepted":true}', stderr=""
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=tmp_path / "calls",
        config=FrontierAgentConfig(),
    )
    assert role("prompt")["accepted"] is True
    assert (tmp_path / "calls/000.prompt.txt").read_text() == "prompt"
    replay_role = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=tmp_path / "calls",
        config=FrontierAgentConfig(),
    )
    assert replay_role("prompt")["accepted"] is True
    assert len(calls) == 1
    assert replay_role.call_count == 0
    assert replay_role.provider_call_count == 0


def test_codex_schema_preflight_rejects_provider_unsupported_keywords():
    with pytest.raises(ValueError, match="unsupported keyword 'uniqueItems'"):
        _validate_codex_strict_schema(
            {
                "type": "array",
                "items": {"type": "string"},
                "uniqueItems": True,
            }
        )


def test_subscription_json_role_replays_against_frozen_schema(tmp_path, monkeypatch):
    calls = []
    historical_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["formula_id"],
        "properties": {"formula_id": {"type": "string"}},
    }

    def fake_run(**kwargs):
        calls.append(kwargs)
        Path(kwargs["output_last_message_path"]).write_text(
            '{"formula_id":"formula:short"}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["agent"], 0, stdout="transcript", stderr=""
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    calls_dir = tmp_path / "calls"
    first = SubscriptionJSONRole(
        role="navigator",
        agent_id="navigator-a",
        repo=tmp_path,
        artifact_dir=calls_dir,
        output_schema=historical_schema,
    )
    assert first("prompt")["formula_id"] == "formula:short"

    stricter_schema = {
        **historical_schema,
        "properties": {
            "formula_id": {
                "type": "string",
                "pattern": r"^formula:[0-9a-f]{64}$",
            }
        },
    }
    replay = SubscriptionJSONRole(
        role="navigator",
        agent_id="navigator-a",
        repo=tmp_path,
        artifact_dir=calls_dir,
        output_schema=stricter_schema,
    )

    assert replay("prompt")["formula_id"] == "formula:short"
    assert len(calls) == 1
    assert replay.calls[0]["output_schema_digest"] == content_hash(historical_schema)


@pytest.mark.parametrize(
    "mutation",
    ("tampered_result", "blank_result_digest", "wrong_agent"),
)
def test_subscription_json_role_rejects_tampered_durable_success_before_dispatch(
    tmp_path, monkeypatch, mutation
):
    dispatches = []

    def fake_run(**kwargs):
        dispatches.append(kwargs)
        Path(kwargs["output_last_message_path"]).write_text(
            '{"accepted":true}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["agent"], 0, stdout="transcript", stderr=""
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    calls_dir = tmp_path / "calls"
    role = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=calls_dir,
        config=FrontierAgentConfig(),
    )
    assert role("prompt")["accepted"] is True
    call_path = calls_dir / "000.call.json"
    call = json.loads(call_path.read_text(encoding="utf-8"))
    if mutation == "tampered_result":
        (calls_dir / "000.result.json").write_text(
            '{"accepted":false}', encoding="utf-8"
        )
    elif mutation == "blank_result_digest":
        call["result_digest"] = ""
        call_path.write_text(json.dumps(call, sort_keys=True), encoding="utf-8")
    else:
        call["agent_id"] = "reviewer-c"
        call_path.write_text(json.dumps(call, sort_keys=True), encoding="utf-8")

    replay = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=calls_dir,
        config=FrontierAgentConfig(),
    )
    with pytest.raises(ValueError, match="durable frontier role"):
        replay("prompt")
    assert len(dispatches) == 1


def test_subscription_json_role_resumes_one_stable_lineage_session_across_waves(
    tmp_path, monkeypatch
):
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        Path(kwargs["output_last_message_path"]).write_text(
            '{"accepted":true}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["agent"], 0, stdout='{"accepted":true}', stderr=""
            ),
            final_session_state={
                "session_id": "session-1",
                "started_at_epoch": 1_788_000_000,
                "tick_count": len(calls),
            },
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    for wave in (1, 2):
        role = SubscriptionJSONRole(
            role="navigator",
            agent_id=f"axiompack-navigator-lineage-000.wave-{wave:03d}",
            repo=tmp_path,
            artifact_dir=tmp_path / "calls" / f"navigator.lineage-000.wave-{wave:03d}",
            config=FrontierAgentConfig(),
        )
        assert role(f"wave {wave}")["accepted"] is True

    assert calls[0]["session_state"]["is_new"] is True
    assert calls[1]["session_state"]["session_id"] == "session-1"
    assert calls[1]["session_state"]["is_new"] is False


def test_subscription_json_role_replays_frozen_prompt_identity(tmp_path, monkeypatch):
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        Path(kwargs["output_last_message_path"]).write_text(
            '{"accepted":true}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["agent"], 0, stdout='{"accepted":true}', stderr=""
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    calls_dir = tmp_path / "calls"
    first = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=calls_dir,
        config=FrontierAgentConfig(),
    )
    assert first("frozen prompt")["accepted"] is True

    replay = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=calls_dir,
        config=FrontierAgentConfig(),
    )
    assert replay.call_with_compatible_prompts("new prompt", ())["accepted"] is True
    assert len(calls) == 1
    assert replay.calls[0]["replayed"] is True


@pytest.mark.parametrize(
    "stderr",
    [
        "invalid_json_schema: unsupported keyword",
        "The 'gpt-5.6-sol' model requires a newer version of Codex.",
        "The 'fable' model is not supported with ChatGPT accounts.",
        "Selected model is at capacity. Try again later.",
        "Error: failed to initialize in-process app-server client: "
        "Operation not permitted (os error 1)",
        "invalid_request_error: invalid_value for reasoning.effort; "
        "supported values include xhigh",
    ],
)
def test_pre_inference_cli_rejections_do_not_consume_provider_budget(stderr):
    result = subprocess.CompletedProcess(["codex"], 1, stdout="", stderr=stderr)

    assert _provider_call_charge(result) == 0


def test_live_invalid_response_schema_is_a_pre_dispatch_contract_error(
    tmp_path, monkeypatch
):
    def fake_run(**_kwargs):
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["agent"],
                1,
                stdout="",
                stderr="invalid_json_schema: uniqueItems is not permitted",
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="adapter_forge",
        agent_id="adapter-forge-contract",
        repo=tmp_path,
        artifact_dir=tmp_path / "calls",
        config=FrontierAgentConfig(),
    )

    with pytest.raises(FrontierRolePreDispatchContractError):
        role("frozen prompt")

    receipt = json.loads((tmp_path / "calls/000.call.json").read_text())
    assert receipt["provider_call_charge"] == 0


def test_unknown_transport_failure_conservatively_consumes_provider_budget():
    result = subprocess.CompletedProcess(
        ["codex"], 1, stdout="", stderr="unclassified transport failure"
    )

    assert _provider_call_charge(result) == 1


def test_subscription_json_role_validates_dedicated_typed_result(tmp_path, monkeypatch):
    def fake_run(**kwargs):
        Path(kwargs["output_last_message_path"]).write_text(
            '{"decision":"finish","rationale":"Enough evidence."}',
            encoding="utf-8",
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["agent"], 0, stdout="transcript", stderr="")
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="navigator",
        agent_id="navigator-a",
        repo=tmp_path,
        artifact_dir=tmp_path / "calls",
        config=FrontierAgentConfig(),
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["decision", "rationale"],
            "properties": {
                "decision": {"type": "string"},
                "rationale": {"type": "string", "minLength": 1},
            },
        },
    )

    assert role("prompt")["decision"] == "finish"
    assert (tmp_path / "calls/000.result.json").is_file()
    assert (tmp_path / "calls/000.schema.json").is_file()
    assert role.call_count == 1
    assert role.provider_call_count == 1


def test_subscription_role_records_zero_charge_for_pre_inference_rejection(
    tmp_path, monkeypatch
):
    def fake_run(**_kwargs):
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["codex"],
                1,
                stdout="",
                stderr=(
                    "The 'fable' model is not supported when using Codex "
                    "with a ChatGPT account."
                ),
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="interpreter",
        agent_id="interpreter-a",
        repo=tmp_path,
        artifact_dir=tmp_path / "calls",
        config=FrontierAgentConfig(),
    )

    with pytest.raises(RuntimeError):
        role("prompt")
    receipt = json.loads((tmp_path / "calls/000.call.json").read_text())
    assert receipt["provider_call_charge"] == 0
    assert role.call_count == 1
    assert role.provider_call_count == 0


def test_fable_claude_role_uses_local_schema_validation(tmp_path, monkeypatch):
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["claude"], 0, stdout='{"accepted":true}', stderr=""
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="eigenquestion_reviewer",
        agent_id="fable-eigenreview",
        repo=tmp_path,
        artifact_dir=tmp_path / "fable-calls",
        config=FrontierAgentConfig(
            runtime="claude", model="claude-fable-5", reasoning_effort="low"
        ),
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["accepted"],
            "properties": {"accepted": {"type": "boolean"}},
        },
    )

    assert role("review the eigenquestion")["accepted"] is True
    assert calls[0]["runtime"] == "claude"
    assert calls[0]["output_schema"] is None
    assert calls[0]["output_last_message_path"] is None
    assert "Bash" in calls[0]["claude_disallowed_tools"]
    assert "WebSearch" in calls[0]["claude_disallowed_tools"]
    assert (tmp_path / "fable-calls/000.schema.json").is_file()


def test_frontier_role_routes_fable_alias_to_claude(tmp_path):
    from ztare.leanmill.frontier_campaign_runner import frontier_agent_role

    definition = SimpleNamespace(
        runtime={"defaults": {"runtime": "codex", "model": "fable"}},
        budget=SimpleNamespace(wall_clock_s=300),
    )
    role = frontier_agent_role(
        definition,
        role_name="eigenquestion_reviewer",
        repo=tmp_path,
        artifact_dir=tmp_path / "agent-calls",
    )

    assert role.config.runtime == "claude"
    assert role.config.model == "claude-fable-5"


def _write_failed_role_call(
    calls_dir: Path,
    *,
    prompt: str,
    stdout: str,
    stderr: str,
) -> None:
    (calls_dir / "000.prompt.txt").write_text(prompt, encoding="utf-8")
    (calls_dir / "000.stdout.txt").write_text(stdout, encoding="utf-8")
    (calls_dir / "000.stderr.txt").write_text(stderr, encoding="utf-8")
    (calls_dir / "000.call.json").write_text(
        json.dumps(
            {
                "schema": "leanmill.frontier_subscription_role_call.v1",
                "role": "reviewer",
                "agent_id": "reviewer-b",
                "runtime": "codex",
                "model": "gpt-5.4-mini",
                "prompt_digest": content_hash({"prompt": prompt}),
                "returncode": 1,
                "provider_call_charge": 0,
                "wallclock_s": 0.0,
                "stdout_digest": content_hash({"stdout": stdout}),
                "stderr_digest": content_hash({"stderr": stderr}),
                "result_digest": "",
                "output_schema_digest": "",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("stderr", "reason"),
    [
        ("invalid_json_schema", "invalid_json_schema"),
        (
            "The 'gpt-5.6-sol' model requires a newer version of Codex.",
            "codex_cli_upgrade_required",
        ),
        (
            "invalid_request_error: invalid_value for reasoning.effort; "
            "supported values include xhigh",
            "unsupported_reasoning_effort",
        ),
        (
            "Error: failed to initialize in-process app-server client: "
            "Operation not permitted (os error 1)",
            "subscription_runtime_sandbox_denied",
        ),
    ],
)
def test_retryable_transport_failure_advances_immutable_call_index(
    tmp_path, monkeypatch, stderr, reason
):
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir()
    prompt = "prompt"
    _write_failed_role_call(
        calls_dir,
        prompt=prompt,
        stdout="",
        stderr=stderr,
    )

    def fake_run(**kwargs):
        Path(kwargs["output_last_message_path"]).write_text(
            '{"accepted":true}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["agent"], 0, stdout="transcript", stderr="")
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=calls_dir,
        config=FrontierAgentConfig(),
    )

    assert role(prompt)["accepted"] is True
    assert (calls_dir / "001.call.json").is_file()
    assert role.calls[0]["retryable_transport_failure"] == reason
    assert role.call_count == 1


def test_retryable_transport_failure_is_detected_when_cli_writes_to_stdout(
    tmp_path, monkeypatch
):
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir()
    prompt = "prompt"
    _write_failed_role_call(
        calls_dir,
        prompt=prompt,
        stdout=(
            "Error: failed to initialize in-process app-server client: "
            "Operation not permitted (os error 1)"
        ),
        stderr="",
    )

    def fake_run(**kwargs):
        Path(kwargs["output_last_message_path"]).write_text(
            '{"accepted":true}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["agent"], 0, stdout="transcript", stderr="")
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=calls_dir,
        config=FrontierAgentConfig(),
    )

    assert role(prompt)["accepted"] is True
    assert (calls_dir / "001.call.json").is_file()
    assert role.calls[0]["retryable_transport_failure"] == (
        "subscription_runtime_sandbox_denied"
    )


def test_retryable_failed_prompt_can_advance_after_runtime_policy_correction(
    tmp_path, monkeypatch
):
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir()
    old_prompt = "old frozen prompt"
    _write_failed_role_call(
        calls_dir,
        prompt=old_prompt,
        stdout="",
        stderr=(
            "invalid_request_error: invalid_value for reasoning.effort; "
            "supported values include xhigh"
        ),
    )

    def fake_run(**kwargs):
        Path(kwargs["output_last_message_path"]).write_text(
            '{"accepted":true}', encoding="utf-8"
        )
        return SimpleNamespace(
            result=subprocess.CompletedProcess(
                ["agent"], 0, stdout="transcript", stderr=""
            )
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_agent_runtime.run_subscription_agent_with_recovery",
        fake_run,
    )
    role = SubscriptionJSONRole(
        role="reviewer",
        agent_id="reviewer-b",
        repo=tmp_path,
        artifact_dir=calls_dir,
        config=FrontierAgentConfig(),
    )

    assert role.call_with_compatible_prompts("corrected prompt", ())["accepted"]
    assert (calls_dir / "001.prompt.txt").read_text() == "corrected prompt"
    assert role.calls[0]["retryable_transport_failure"] == (
        "unsupported_reasoning_effort"
    )


def test_frontier_json_parser_returns_enclosing_decision_not_nested_inputs():
    response = (
        'log line\n'
        '{"decision":"request","capability_id":"list_theory_nodes@v1",'
        '"input_refs":{"offset":0,"limit":16},"rationale":"Inspect topology."}'
    )

    assert _parse_last_json_object(response) == {
        "decision": "request",
        "capability_id": "list_theory_nodes@v1",
        "input_refs": {"offset": 0, "limit": 16},
        "rationale": "Inspect topology.",
    }


def test_compiler_reviewer_callbacks_use_central_prompt_home(tmp_path):
    seen = []

    class Role:
        def __init__(self, agent_id):
            self.agent_id = agent_id
            self.call_count = 0

        def __call__(self, prompt):
            seen.append(prompt)
            return {"ok": True}

    draft, review = make_subscription_frontier_compiler_roles(
        compiler=Role("compiler-a"), reviewer=Role("reviewer-b")
    )
    draft({"schema": "brief"})
    review({"brief": {}, "draft": {}})
    assert "frontier-theory campaign draft" in seen[0]
    assert "Independently review" in seen[1]
