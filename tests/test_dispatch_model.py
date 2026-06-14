from __future__ import annotations

import os
import json
import subprocess
from types import SimpleNamespace

import pytest

from src.ztare.common.dispatch_model import (
    DispatchTextResponse,
    dispatch_call_text,
    dispatch_env_for_call_site,
    dispatch_model,
    dispatch_result_receipt,
    resolve_agent_timeout_seconds,
    resolve_dispatch_capability,
)
from src.ztare.research_director.autoresearch_dispatch_canary import (
    run_dispatch_canary,
    run_dispatch_parity_benchmark,
)


def test_dispatch_model_llm_delegates_to_call_once() -> None:
    result = dispatch_model("hello", llm_call=lambda prompt: prompt.upper())

    assert result.text == "HELLO"
    assert result.capability == "llm"
    assert result.transport == "api"


def test_dispatch_model_agent_requires_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH", raising=False)

    with pytest.raises(RuntimeError):
        dispatch_model("hello", capability="agent")


def test_dispatch_model_agent_uses_subscription_runner(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    seen: dict[str, str] = {}

    def fake_runner(**kwargs):
        seen["prompt"] = kwargs["prompt"]
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    result = dispatch_model(
        "emit mutation",
        "prior failure: missing declaration",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        runner=fake_runner,
    )

    assert result.text == "typed contract"
    assert result.transport == "subscription_cli"
    assert result.worker_archetype == "fungible_agent_worker"
    assert "EXTERNALIZED BRIEFING" in seen["prompt"]
    assert "prior failure" in seen["prompt"]
    assert "emit mutation" in seen["prompt"]


def test_dispatch_result_receipt_omits_full_command_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")

    def fake_runner(**_kwargs):
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_command=["codex", "exec", "prompt text should not be stored"],
            recovery_note=None,
        )

    result = dispatch_model(
        "prompt text should not be stored",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        runner=fake_runner,
    )
    receipt = dispatch_result_receipt("mutator", result)

    assert receipt["call_site"] == "mutator"
    assert receipt["transport"] == "subscription_cli"
    assert receipt["completed"] is True
    assert receipt["command_head"] == "codex"
    assert "prompt text should not be stored" not in json.dumps(receipt)


def test_dispatch_model_stateful_agent_persists_warm_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    session_dir = tmp_path / "sessions"
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="typed contract", stderr=""),
            final_session_state={
                "schema": "leanmill-subscription-agent-session-v1",
                "runtime": "codex",
                "agent_id": "rd-director",
                "session_id": "session-123",
                "started_at_epoch": 123,
                "tick_count": 7,
                "is_new": False,
            },
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    result = dispatch_model(
        "continue the workbench thread",
        capability="agent",
        backend="codex",
        repo=tmp_path,
        stateful=True,
        fungible=False,
        continuity_key="rd-director",
        session_dir=session_dir,
        runner=fake_runner,
    )

    persisted = json.loads((session_dir / "codex_rd-director.json").read_text())
    assert result.worker_archetype == "persistent_agent_worker"
    assert seen["session_state"]["is_new"] is True
    assert persisted["session_id"] == "session-123"
    assert persisted["tick_count"] == 7
    assert persisted["last_used_at_epoch"] is not None


def test_dispatch_call_text_preserves_api_response_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_RUBRIC_REVIEW", raising=False)

    response = dispatch_call_text(
        "rubric_review",
        "prompt",
        llm_response_call=lambda prompt: DispatchTextResponse(
            text=f"api:{prompt}",
            usage={"tokens": 3},
            model_id_used="gemini-test",
        ),
    )

    assert response.text == "api:prompt"
    assert response.usage == {"tokens": 3}
    assert response.model_id_used == "gemini-test"
    assert response.dispatch_result is not None
    assert response.dispatch_result.transport == "api"


def test_dispatch_call_text_uses_scoped_agent_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_RUBRIC_REVIEW", "agent")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_RUBRIC_REVIEW_AGENT_RUNTIME", "codex")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout='{"ok": true}', stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    response = dispatch_call_text(
        "rubric_review",
        "return json",
        llm_response_call=lambda _prompt: DispatchTextResponse(text="api should not run"),
        repo=tmp_path,
        timeout_seconds=123,
        runner=fake_runner,
    )

    assert response.text == '{"ok": true}'
    assert response.model_id_used == "codex"
    assert response.dispatch_result is not None
    assert response.dispatch_result.transport == "subscription_cli"
    assert seen["agent_id"] == "autoresearch_rubric_review"
    assert seen["timeout_seconds"] == 123


def test_dispatch_call_text_uses_generic_agent_timeout_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_RUBRIC_REVIEW", "agent")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "17")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="ok", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_call_text(
        "rubric_review",
        "return text",
        llm_response_call=lambda _prompt: DispatchTextResponse(text="api should not run"),
        repo=tmp_path,
        timeout_seconds=123,
        runner=fake_runner,
    )

    assert seen["timeout_seconds"] == 17


def test_dispatch_call_text_uses_scoped_agent_timeout_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_MUTATOR", "agent")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "17")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_MUTATOR_AGENT_TIMEOUT_SECONDS", "11")
    seen: dict[str, object] = {}

    def fake_runner(**kwargs):
        seen.update(kwargs)
        return SimpleNamespace(
            result=subprocess.CompletedProcess(["codex"], 0, stdout="ok", stderr=""),
            final_command=["codex", "exec", "redacted"],
            recovery_note=None,
        )

    dispatch_call_text(
        "mutator",
        "return text",
        llm_response_call=lambda _prompt: DispatchTextResponse(text="api should not run"),
        repo=tmp_path,
        timeout_seconds=123,
        runner=fake_runner,
    )

    assert seen["timeout_seconds"] == 11


def test_resolve_agent_timeout_seconds_ignores_invalid_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZTARE_AUTORESEARCH_AGENT_TIMEOUT_SECONDS", "not-an-int")
    monkeypatch.setenv("ZTARE_AUTORESEARCH_MUTATOR_AGENT_TIMEOUT_SECONDS", "0")

    assert resolve_agent_timeout_seconds("mutator", default=123) == 123


def test_resolve_dispatch_capability_supports_call_site_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "off")
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_MUTATOR", "agent")

    assert resolve_dispatch_capability("mutator") == "agent"
    assert resolve_dispatch_capability("judge") == "llm"


def test_dispatch_env_for_call_site_matches_scoped_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH", "agent")
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_JUDGE", raising=False)
    assert dispatch_env_for_call_site("judge") == "ZTARE_AGENT_DISPATCH"

    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_JUDGE", "agent")
    assert dispatch_env_for_call_site("judge") == "ZTARE_AGENT_DISPATCH_JUDGE"


def test_dispatch_canary_exercises_subscription_path_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_MUTATOR", raising=False)

    report = run_dispatch_canary(
        call_site="mutator",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["live"] is False
    assert report["transport"] == "subscription_cli"
    assert report["worker_archetype"] == "fungible_agent_worker"
    assert report["token_seen"] is True
    assert "ZTARE_AGENT_DISPATCH_MUTATOR" not in os.environ


def test_dispatch_canary_validates_mutator_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_MUTATOR", raising=False)

    report = run_dispatch_canary(
        call_site="mutator",
        contract="mutator",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "mutator"
    assert report["contract_error"] is None
    assert report["contract_validation"]["mutation_validation"]["mismatch_code"] == "CLEAN"
    assert report["contract_validation"]["candidate_extraction"]["python_code_present"] is True


def test_dispatch_canary_validates_judge_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_JUDGE", raising=False)

    report = run_dispatch_canary(
        call_site="judge",
        contract="judge",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "judge"
    assert report["contract_error"] is None
    assert report["contract_validation"]["score"] == 42
    assert report["contract_validation"]["probability_dag_keys"] == ["edges", "nodes", "outcome"]


def test_dispatch_canary_validates_committee_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_COMMITTEE", raising=False)

    report = run_dispatch_canary(
        call_site="committee",
        contract="committee",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "committee"
    assert report["contract_error"] is None
    assert report["contract_validation"]["persona_count"] == 3
    assert report["contract_validation"]["roles"] == [
        "Boundary Auditor",
        "Mechanism Skeptic",
        "Execution Auditor",
    ]


def test_dispatch_canary_validates_inverter_contract_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_INVERTER_REVIEW", raising=False)

    report = run_dispatch_canary(
        call_site="inverter_review",
        contract="inverter",
        runtime="codex",
        live=False,
        repo=tmp_path,
    )

    assert report["ok"] is True
    assert report["contract"] == "inverter"
    assert report["contract_error"] is None
    assert report["contract_validation"]["test_count"] == 3
    assert report["contract_validation"]["categories"] == [
        "measurement_artifact",
        "confound",
        "generalization",
    ]
    assert report["contract_validation"]["auto_testable_count"] == 2


def test_dispatch_parity_benchmark_compares_api_and_subscription_contracts_without_live_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_MUTATOR", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_JUDGE", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_COMMITTEE", raising=False)
    monkeypatch.delenv("ZTARE_AGENT_DISPATCH_INVERTER_REVIEW", raising=False)

    report = run_dispatch_parity_benchmark(runtime="codex", repo=tmp_path)

    assert report["schema"] == "ztare-autoresearch-dispatch-parity-v1"
    assert report["ok"] is True
    assert report["live_subscription"] is False
    assert report["contracts"] == ["text", "mutator", "judge", "committee", "inverter"]
    assert report["summary"]["num_contracts"] == 5
    assert report["summary"]["num_parity"] == 5
    assert report["summary"]["api_all_ok"] is True
    assert report["summary"]["subscription_all_ok"] is True
    assert report["summary"]["api_mean_quality_score"] == 1.0
    assert report["summary"]["subscription_mean_quality_score"] == 1.0
    assert report["summary"]["quality_parity_count"] == 5
    assert report["summary"]["api_model_calls"] == 5
    assert report["summary"]["subscription_cli_invocations"] == 5
    assert report["summary"]["cost_basis"] == "replay_proxy"
    for row in report["rows"]:
        assert row["contract_parity"] is True
        assert row["quality_parity"] is True
        assert row["api"]["transport"] == "api"
        assert row["api"]["quality"]["quality_score"] == 1.0
        assert row["api"]["quality"]["checks_passed"] == row["api"]["quality"]["checks_total"]
        assert row["api"]["cost_proxy"]["api_model_calls"] == 1
        assert row["subscription"]["transport"] == "subscription_cli"
        assert row["subscription"]["runtime"] == "codex"
        assert row["subscription"]["quality"]["quality_score"] == 1.0
        assert (
            row["subscription"]["quality"]["checks_passed"]
            == row["subscription"]["quality"]["checks_total"]
        )
        assert row["subscription"]["cost_proxy"]["subscription_cli_invocations"] == 1
    assert "ZTARE_AGENT_DISPATCH" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_MUTATOR" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_JUDGE" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_COMMITTEE" not in os.environ
    assert "ZTARE_AGENT_DISPATCH_INVERTER_REVIEW" not in os.environ


def test_dispatch_parity_benchmark_rejects_unknown_contract(tmp_path) -> None:
    with pytest.raises(ValueError, match="unsupported canary contract"):
        run_dispatch_parity_benchmark(contracts=("text", "unknown"), repo=tmp_path)
