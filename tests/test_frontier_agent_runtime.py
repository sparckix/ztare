from __future__ import annotations

from types import SimpleNamespace
import subprocess
from pathlib import Path
import json

import pytest

from ztare.leanmill.frontier_agent_runtime import (
    FrontierAgentConfig,
    SubscriptionJSONRole,
    _provider_call_charge,
    _parse_last_json_object,
    make_subscription_frontier_compiler_roles,
)
from ztare.leanmill.frontier_blueprint_compiler import render_frontier_blueprint_prompt
from ztare.leanmill.theory_ir import content_hash


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
    ],
)
def test_pre_inference_cli_rejections_do_not_consume_provider_budget(stderr):
    result = subprocess.CompletedProcess(["codex"], 1, stdout="", stderr=stderr)

    assert _provider_call_charge(result) == 0


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


@pytest.mark.parametrize(
    ("stderr", "reason"),
    [
        ("invalid_json_schema", "invalid_json_schema"),
        (
            "The 'gpt-5.6-sol' model requires a newer version of Codex.",
            "codex_cli_upgrade_required",
        ),
    ],
)
def test_retryable_transport_failure_advances_immutable_call_index(
    tmp_path, monkeypatch, stderr, reason
):
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir()
    prompt = "prompt"
    (calls_dir / "000.call.json").write_text(
        json.dumps({
            "prompt_digest": content_hash({"prompt": prompt}),
            "returncode": 1,
        }),
        encoding="utf-8",
    )
    (calls_dir / "000.stdout.txt").write_text("", encoding="utf-8")
    (calls_dir / "000.stderr.txt").write_text(stderr, encoding="utf-8")

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
