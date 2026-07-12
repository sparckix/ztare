import time

import pytest

from ztare.common.llm_runtime import (
    LLMRuntime,
    LLMRuntimeError,
    LLMTextResponse,
    LLMUsage,
    subscription_model_route,
    validate_subscription_model_cli,
)


class HangingRuntime(LLMRuntime):
    def _call_once(self, *args, **kwargs):  # noqa: ANN002, ANN003
        time.sleep(5)
        return object()


class _FakeChatCompletions:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):  # noqa: ANN003
        self.kwargs = kwargs
        return object()


def test_subscription_model_route_keeps_fable_on_claude() -> None:
    assert subscription_model_route("fable", requested_runtime="codex") == (
        "claude",
        "claude-fable-5",
    )
    assert subscription_model_route(
        "claude-fable-5", requested_runtime="codex"
    ) == ("claude", "claude-fable-5")
    assert subscription_model_route("gpt5.5", requested_runtime="claude") == (
        "codex",
        "gpt-5.5",
    )
    assert subscription_model_route("sol", requested_runtime="claude") == (
        "codex",
        "gpt-5.6-sol",
    )
    assert subscription_model_route("terra", requested_runtime="claude") == (
        "codex",
        "gpt-5.6-terra",
    )
    assert subscription_model_route("luna", requested_runtime="claude") == (
        "codex",
        "gpt-5.6-luna",
    )


@pytest.mark.parametrize("model", ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"])
def test_gpt56_subscription_models_require_a_compatible_codex_cli(model) -> None:
    with pytest.raises(ValueError, match="requires codex CLI"):
        validate_subscription_model_cli("codex", model, "OpenAI Codex v0.128.0")
    validate_subscription_model_cli("codex", model, "OpenAI Codex v0.144.0")


class _FakeChatClient:
    def __init__(self) -> None:
        self._completions = _FakeChatCompletions()
        self.chat = type("Chat", (), {"completions": self._completions})()

    @property
    def kwargs(self):
        return self._completions.kwargs


def test_llm_runtime_timeout_does_not_wait_for_provider_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ZTARE_DISABLE_MODEL_FALLBACK", "1")
    # Disable subscription fallback so the test stays fast (timing assertion below).
    # The subscription path would spawn a real codex CLI subprocess.
    monkeypatch.setenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", "1")
    runtime = HangingRuntime()

    started = time.monotonic()
    with pytest.raises(LLMRuntimeError):
        runtime.call_text(
            "prompt",
            model_id="gpt-4.1",
            retries=1,
            timeout_seconds=0.05,
        )
    elapsed = time.monotonic() - started

    assert elapsed < 0.5


@pytest.mark.parametrize(
    ("client_attr", "model_id"),
    [
        ("_kimi_client", "kimi-k2.6"),
        ("_grok_client", "grok-4.3"),
    ],
)
def test_chat_completion_providers_receive_call_timeout(
    client_attr: str,
    model_id: str,
) -> None:
    runtime = LLMRuntime()
    client = _FakeChatClient()
    setattr(runtime, client_attr, client)

    response = runtime._call_once(
        "return json",
        model_id,
        config={"response_format": {"type": "json_object"}},
        max_tokens=512,
        timeout_seconds=7,
    )

    assert response is not None
    assert client.kwargs["model"] == model_id
    assert client.kwargs["timeout"] == 7
    assert client.kwargs["response_format"] == {"type": "json_object"}


def test_openai_api_receives_normalized_reasoning_effort() -> None:
    runtime = LLMRuntime()
    client = _FakeChatClient()
    runtime._openai_client = client  # noqa: SLF001

    runtime._call_once(
        "reason deeply",
        "gpt-5.5",
        config={"reasoning_effort": "high"},
        max_tokens=512,
        timeout_seconds=7,
    )

    assert client.kwargs["reasoning_effort"] == "high"
    assert client.kwargs["max_completion_tokens"] == 512


def test_kimi_k26_default_text_call_disables_thinking_for_visible_output() -> None:
    runtime = LLMRuntime()
    client = _FakeChatClient()
    runtime._kimi_client = client  # noqa: SLF001

    runtime._call_once(
        "visible answer",
        "kimi-k2.6",
        config=None,
        max_tokens=512,
        timeout_seconds=7,
    )

    assert client.kwargs["temperature"] == 0.6
    assert client.kwargs["extra_body"] == {"thinking": {"type": "disabled"}}


def test_kimi_k26_explicit_thinking_config_overrides_visible_output_default() -> None:
    runtime = LLMRuntime()
    client = _FakeChatClient()
    runtime._kimi_client = client  # noqa: SLF001

    runtime._call_once(
        "reason if requested",
        "kimi-k2.6",
        config={"temperature": 1, "thinking": {"type": "enabled"}},
        max_tokens=512,
        timeout_seconds=7,
    )

    assert client.kwargs["temperature"] == 1
    assert client.kwargs["extra_body"] == {"thinking": {"type": "enabled"}}


class _StatusError(RuntimeError):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class _FallbackRuntime(LLMRuntime):
    def __init__(self, first_error: Exception) -> None:
        super().__init__()
        self.first_error = first_error
        self.calls: list[str] = []

    def model_is_configured(self, model_id: str) -> bool:
        return model_id in {"kimi-k2.6", "gpt-4.1"}

    def default_fallback_model_ids(self, model_id: str) -> tuple[str, ...]:
        return ("gpt-4.1",) if model_id == "kimi-k2.6" else ()

    def _call_once(self, _prompt: str, model_id: str, **_kwargs):  # noqa: ANN002
        self.calls.append(model_id)
        if model_id == "kimi-k2.6":
            raise self.first_error
        return object()

    def _response_to_text_result(
        self,
        response,
        requested_model_id: str,
        *,
        original_requested_model_id: str | None = None,
    ) -> LLMTextResponse:
        original = original_requested_model_id or requested_model_id
        return LLMTextResponse(
            text="OK",
            model_name=requested_model_id,
            usage=LLMUsage(model_name=requested_model_id),
            raw_response=response,
            requested_model_id=original,
            effective_model_id=requested_model_id,
            fallback_from_model_id=original if original != requested_model_id else None,
        )


def test_billing_error_continues_to_configured_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Cross-provider API fallback is OFF by default (operator directive 2026-07-10).
    # With it enabled, the old kimi→gpt-4.1 chain still works for callers that opt in.
    monkeypatch.setenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", "1")
    monkeypatch.setenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", "1")
    runtime = _FallbackRuntime(
        _StatusError("Your credit balance is too low to access this API.", 400)
    )

    result = runtime.call_text(
        "prompt",
        model_id="kimi-k2.6",
        retries=2,
        timeout_seconds=1,
    )

    assert runtime.calls == ["kimi-k2.6", "gpt-4.1"]
    assert result.text == "OK"
    assert result.effective_model_id == "gpt-4.1"
    assert result.fallback_from_model_id == "kimi-k2.6"


def test_bad_request_still_fails_closed_before_fallback() -> None:
    runtime = _FallbackRuntime(_StatusError("invalid model parameter", 400))

    with pytest.raises(LLMRuntimeError) as exc_info:
        runtime.call_text(
            "prompt",
            model_id="kimi-k2.6",
            retries=2,
            timeout_seconds=1,
        )

    assert runtime.calls == ["kimi-k2.6"]
    assert exc_info.value.model_id == "kimi-k2.6"
    assert exc_info.value.transient is False
