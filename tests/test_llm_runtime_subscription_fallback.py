"""Tests for the subscription-fallback policy (operator directive 2026-07-10).

Policy:
  - Cross-provider API fallback is OFF by default (ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK=0).
  - When the primary API call fails, the fallback is the Codex subscription
    runtime with the SAME requested model family (OpenAI only).
  - Non-OpenAI families (claude/gemini/kimi/grok) fail loud — no family substitution.
  - ZTARE_DISABLE_SUBSCRIPTION_FALLBACK=1 restores fail-loud-immediately.
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ztare.common.llm_runtime import (
    CODEX_SERVABLE_FAMILIES,
    LLMRuntime,
    LLMRuntimeError,
    LLMTextResponse,
    LLMUsage,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

class _AlwaysFailsRuntime(LLMRuntime):
    """Primary API always raises (simulates dead key / network failure)."""

    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.api_calls: list[str] = []
        self._error = error

    def model_is_configured(self, model_id: str) -> bool:
        return True

    def _call_once(self, _prompt: str, model_id: str, **_kwargs):  # noqa: ANN002
        self.api_calls.append(model_id)
        raise self._error


def _fake_subscription_success(text: str = "subscription answer"):
    """Return a function that mocks _dispatch_via_codex_subscription to succeed."""
    def _mock(self, prompt, model_id, *, repo=".", timeout_seconds=300):  # noqa: ANN001
        return LLMTextResponse(
            text=text,
            model_name=f"{model_id}[subscription_fallback]",
            usage=LLMUsage(model_name=model_id),
            raw_response=None,
            requested_model_id=model_id,
            effective_model_id=model_id,
            fallback_from_model_id=None,
        )
    return _mock


def _fake_subscription_failure(exc: Exception):
    """Return a function that mocks _dispatch_via_codex_subscription to raise."""
    def _mock(self, prompt, model_id, **_kwargs):  # noqa: ANN001
        raise exc
    return _mock


# ── Test 1: primary OK → no fallback ──────────────────────────────────────────

def test_primary_ok_no_subscription_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the primary API succeeds, subscription fallback is never invoked."""
    monkeypatch.delenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", raising=False)
    monkeypatch.delenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", raising=False)

    sub_called = []

    class _SuccessRuntime(LLMRuntime):
        def model_is_configured(self, model_id: str) -> bool:  # noqa: ANN001
            return True

        def _call_once(self, _prompt, model_id, **_kw):  # noqa: ANN001
            return object()

        def _response_to_text_result(self, response, requested_model_id, **_kw):  # noqa: ANN001
            return LLMTextResponse(
                text="primary answer",
                model_name=requested_model_id,
                usage=LLMUsage(model_name=requested_model_id),
                raw_response=response,
                requested_model_id=requested_model_id,
                effective_model_id=requested_model_id,
            )

        def _dispatch_via_codex_subscription(self, *args, **kwargs):  # noqa: ANN002, ANN003
            sub_called.append(True)
            raise AssertionError("should not reach subscription fallback")

    result = _SuccessRuntime().call_text("hello", model_id="gpt-5.5", retries=1, timeout_seconds=1)
    assert result.text == "primary answer"
    assert not sub_called


# ── Test 2: primary fails → subscription fallback with same-family model ───────

def test_primary_fails_subscription_fallback_same_family(monkeypatch: pytest.MonkeyPatch) -> None:
    """When primary API fails, subscription fallback fires with the same model id."""
    monkeypatch.delenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", raising=False)
    monkeypatch.delenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", raising=False)

    runtime = _AlwaysFailsRuntime(RuntimeError("OPENAI_API_KEY is not set."))

    with patch.object(
        LLMRuntime, "_dispatch_via_codex_subscription", _fake_subscription_success("codex result")
    ):
        result = runtime.call_text("hello", model_id="gpt-5.5", retries=1, timeout_seconds=1)

    assert result.text == "codex result"
    assert result.model_name == "gpt-5.5[subscription_fallback]"
    assert result.effective_model_id == "gpt-5.5"
    assert result.requested_model_id == "gpt-5.5"
    # No family substitution — still gpt-5.5
    assert "gemini" not in (result.model_name or "")
    assert "claude" not in (result.model_name or "")
    # Transport attestation
    assert "[subscription_fallback]" in result.model_name


# ── Test 3: claude requested + API dead → loud failure (no family sub) ─────────

def test_claude_api_dead_fails_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-OpenAI family (claude) with dead API raises immediately — no sub fallback."""
    monkeypatch.delenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", raising=False)
    monkeypatch.delenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", raising=False)

    runtime = _AlwaysFailsRuntime(RuntimeError("ANTHROPIC_API_KEY is not set."))

    sub_called = []

    def _never_called(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        sub_called.append(True)
        raise AssertionError("family substitution is forbidden")

    with patch.object(LLMRuntime, "_dispatch_via_codex_subscription", _never_called):
        with pytest.raises(LLMRuntimeError) as exc_info:
            runtime.call_text("hello", model_id="claude-sonnet-4-6", retries=1, timeout_seconds=1)

    assert not sub_called
    err = str(exc_info.value)
    assert "subscription fallback is only available for OpenAI-family models" in err
    assert "claude-sonnet-4-6" in err
    assert "No family substitution" in err


# ── Test 4: ZTARE_DISABLE_SUBSCRIPTION_FALLBACK=1 → fail loud immediately ─────

def test_disable_subscription_fallback_env_fails_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    """With ZTARE_DISABLE_SUBSCRIPTION_FALLBACK=1, API failure raises without attempting codex."""
    monkeypatch.setenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", "1")
    monkeypatch.delenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", raising=False)

    runtime = _AlwaysFailsRuntime(RuntimeError("OPENAI_API_KEY is not set."))

    sub_called = []

    def _never_called(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        sub_called.append(True)

    with patch.object(LLMRuntime, "_dispatch_via_codex_subscription", _never_called):
        with pytest.raises(LLMRuntimeError):
            runtime.call_text("hello", model_id="gpt-5.5", retries=1, timeout_seconds=1)

    assert not sub_called


# ── Test 5: both API + subscription fail → loud error ─────────────────────────

def test_api_and_subscription_both_fail_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """When API and subscription both fail, raise LLMRuntimeError mentioning both."""
    monkeypatch.delenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", raising=False)
    monkeypatch.delenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", raising=False)

    runtime = _AlwaysFailsRuntime(RuntimeError("no key"))
    sub_error = RuntimeError("codex CLI timed out")

    with patch.object(
        LLMRuntime, "_dispatch_via_codex_subscription", _fake_subscription_failure(sub_error)
    ):
        with pytest.raises(LLMRuntimeError) as exc_info:
            runtime.call_text("hello", model_id="gpt-5.5", retries=1, timeout_seconds=1)

    err = str(exc_info.value)
    assert "subscription fallback also failed" in err
    assert "codex CLI timed out" in err


# ── Test 6: CODEX_SERVABLE_FAMILIES constant is sane ─────────────────────────

def test_codex_servable_families_constant() -> None:
    assert "openai" in CODEX_SERVABLE_FAMILIES
    # Non-OpenAI families must NOT be in the set
    for family in ("anthropic", "google", "kimi", "deepseek", "grok"):
        assert family not in CODEX_SERVABLE_FAMILIES


# ── Test 7: cross-provider API fallback off by default ───────────────────────

def test_cross_provider_fallback_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """By default, FALLBACK_MODEL_CHAINS cross-provider candidates are not used."""
    monkeypatch.delenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", raising=False)
    monkeypatch.setenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", "1")  # fail loud to see what models were tried

    class _TrackingRuntime(LLMRuntime):
        def __init__(self) -> None:
            super().__init__()
            self.tried: list[str] = []

        def model_is_configured(self, model_id: str) -> bool:
            return True  # say everything is configured

        def _call_once(self, _prompt, model_id, **_kw):  # noqa: ANN001
            self.tried.append(model_id)
            raise RuntimeError("primary error")

    runtime = _TrackingRuntime()
    with pytest.raises(LLMRuntimeError):
        runtime.call_text("hello", model_id="gpt-5.5", retries=1, timeout_seconds=1)

    # Only the primary model should have been tried — no cross-provider candidates
    assert runtime.tried == ["gpt-5.5"], f"unexpected cross-provider fallback: {runtime.tried}"


# ── Test 8: ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK=1 restores old chain ─────────

def test_allow_cross_provider_fallback_env_restores_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK=1 restores the FALLBACK_MODEL_CHAINS behaviour."""
    monkeypatch.setenv("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK", "1")
    monkeypatch.setenv("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK", "1")

    class _TrackingRuntime(LLMRuntime):
        def __init__(self) -> None:
            super().__init__()
            self.tried: list[str] = []

        def model_is_configured(self, model_id: str) -> bool:
            return True

        def _call_once(self, _prompt, model_id, **_kw):  # noqa: ANN001
            self.tried.append(model_id)
            raise RuntimeError("always fail")

    runtime = _TrackingRuntime()
    with pytest.raises(LLMRuntimeError):
        runtime.call_text("hello", model_id="gpt-5.5", retries=1, timeout_seconds=1)

    # With cross-provider allowed, the FALLBACK_MODEL_CHAINS candidates ARE tried
    # gpt-5.5 chain = (claude-opus-4-6, gpt-4.1, gemini-3.1-pro-preview)
    assert "claude-opus-4-6" in runtime.tried or "gpt-4.1" in runtime.tried, (
        f"expected cross-provider candidates, got: {runtime.tried}"
    )
