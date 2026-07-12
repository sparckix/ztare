from __future__ import annotations

from types import SimpleNamespace

import pytest

from ztare.common.llm_runtime import LLMRuntime


def _runtime() -> LLMRuntime:
    return LLMRuntime()


def test_claude_empty_content_raises_with_model_and_stop_reason() -> None:
    response = SimpleNamespace(
        content=[SimpleNamespace(text="")],
        usage=None,
        model="claude-test-model",
        stop_reason="max_tokens",
        stop_sequence=None,
    )
    with pytest.raises(RuntimeError) as err:
        _runtime()._response_to_text_result(response, "claude-test-model")
    assert "claude-test-model" in str(err.value)
    assert "max_tokens" in str(err.value)


def test_claude_missing_content_raises() -> None:
    response = SimpleNamespace(content=[], usage=None, model="claude-test-model",
                               stop_reason=None, stop_sequence=None)
    with pytest.raises(RuntimeError):
        _runtime()._response_to_text_result(response, "claude-test-model")


def test_claude_nonempty_content_still_succeeds() -> None:
    response = SimpleNamespace(
        content=[SimpleNamespace(text="hello")],
        usage=None,
        model="claude-test-model",
    )
    out = _runtime()._response_to_text_result(response, "claude-test-model")
    assert out.text == "hello"


def test_gemini_empty_text_raises_with_model_and_finish_reason() -> None:
    response = SimpleNamespace(
        text="",
        model="gemini-test-model",
        usage_metadata=None,
        candidates=[SimpleNamespace(finish_reason="SAFETY")],
        prompt_feedback="blocked",
    )
    with pytest.raises(RuntimeError) as err:
        _runtime()._response_to_text_result(response, "gemini-test-model")
    assert "gemini-test-model" in str(err.value)
    assert "SAFETY" in str(err.value)


def test_gemini_nonempty_text_still_succeeds() -> None:
    response = SimpleNamespace(text="hello", model="gemini-test-model", usage_metadata=None)
    out = _runtime()._response_to_text_result(response, "gemini-test-model")
    assert out.text == "hello"
