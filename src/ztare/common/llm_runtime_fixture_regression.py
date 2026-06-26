from __future__ import annotations

import argparse
import json
from pathlib import Path

from ztare.common.llm_runtime import (
    LLMRuntime,
    get_model_family,
    pricing_model_name,
    resolve_director_model_id,
    resolve_model_id,
)


class _Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FallbackRuntime(LLMRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def model_is_configured(self, model_id: str) -> bool:
        return model_id in {"gemini-2.5-flash", "claude-sonnet-4-6"}

    def _call_once(
        self,
        prompt: str,
        model_id: str,
        *,
        config=None,
        max_tokens: int = 16000,
        timeout_seconds: int | None = None,
    ):
        self.calls.append(model_id)
        if model_id == "gemini-2.5-flash":
            raise RuntimeError("503 UNAVAILABLE")
        return _Obj(
            model="claude-sonnet-4-6-20260401",
            content=[_Obj(text="fallback claude text")],
            usage=_Obj(
                input_tokens=90,
                output_tokens=10,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
            ),
        )

    def is_transient_error(self, exc: Exception) -> bool:
        return "503" in str(exc)


class _TimeoutRecordingRuntime(LLMRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.seen_timeout_seconds: int | None = None

    def _call_once(
        self,
        prompt: str,
        model_id: str,
        *,
        config=None,
        max_tokens: int = 16000,
        timeout_seconds: int | None = None,
    ):
        self.seen_timeout_seconds = timeout_seconds
        return _Obj(
            model="grok-4.3",
            choices=[_Obj(message=_Obj(content="timeout checked"))],
            usage=_Obj(prompt_tokens=1, completion_tokens=1),
        )


class _SchemaConfig:
    response_mime_type = "application/json"
    response_schema = {
        "type": "OBJECT",
        "properties": {"score": {"type": "NUMBER"}},
        "required": ["score"],
    }


class _RecordingCompletions:
    def __init__(self, model_name: str = "grok-4.3") -> None:
        self.kwargs: dict[str, object] = {}
        self.model_name = model_name

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _Obj(
            model=self.model_name,
            choices=[_Obj(message=_Obj(content='{"score": 1}'))],
            usage=_Obj(prompt_tokens=1, completion_tokens=1),
        )


class _RecordingGrokRuntime(LLMRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.completions = _RecordingCompletions()

    def grok_client(self):
        return _Obj(chat=_Obj(completions=self.completions))


class _RecordingKimiRuntime(LLMRuntime):
    def __init__(self) -> None:
        super().__init__()
        self.completions = _RecordingCompletions("kimi-k2.6")

    def kimi_client(self):
        return _Obj(chat=_Obj(completions=self.completions))


def run_llm_runtime_fixture_regression() -> dict[str, object]:
    runtime = LLMRuntime()
    fallback_runtime = _FallbackRuntime()
    timeout_runtime = _TimeoutRecordingRuntime()
    recording_grok_runtime = _RecordingGrokRuntime()
    recording_kimi_runtime = _RecordingKimiRuntime()

    gemini_response = _Obj(
        text="gemini text",
        model="models/gemini-2.5-flash",
        usage_metadata=_Obj(
            prompt_token_count=111,
            candidates_token_count=22,
            cached_content_token_count=7,
        ),
    )
    openai_response = _Obj(
        model="gpt-4o-2026-04-01",
        choices=[_Obj(message=_Obj(content="openai text"))],
        usage=_Obj(
            prompt_tokens=210,
            completion_tokens=45,
            prompt_tokens_details=_Obj(cached_tokens=15),
        ),
    )
    deepseek_response = _Obj(
        model="deepseek-reasoner",
        choices=[_Obj(message=_Obj(content="deepseek text"))],
        usage=_Obj(
            prompt_tokens=410,
            completion_tokens=85,
        ),
    )
    kimi_response = _Obj(
        model="kimi-k2.6",
        choices=[_Obj(message=_Obj(content="kimi text"))],
        usage=_Obj(
            prompt_tokens=510,
            completion_tokens=95,
            prompt_tokens_details=_Obj(cached_tokens=30),
        ),
    )
    grok_response = _Obj(
        model="grok-4.3",
        choices=[_Obj(message=_Obj(content="grok text"))],
        usage=_Obj(
            prompt_tokens=610,
            completion_tokens=105,
            prompt_tokens_details=_Obj(cached_tokens=40),
        ),
    )
    claude_response = _Obj(
        model="claude-sonnet-4-6-20260401",
        content=[_Obj(text="claude text")],
        usage=_Obj(
            input_tokens=310,
            output_tokens=55,
            cache_creation_input_tokens=40,
            cache_read_input_tokens=12,
        ),
    )

    gemini_result = runtime._response_to_text_result(gemini_response, "gemini-2.5-flash")  # noqa: SLF001
    openai_result = runtime._response_to_text_result(openai_response, "gpt-4o")  # noqa: SLF001
    deepseek_result = runtime._response_to_text_result(deepseek_response, "deepseek-reasoner")  # noqa: SLF001
    kimi_result = runtime._response_to_text_result(kimi_response, "kimi-k2.6")  # noqa: SLF001
    grok_result = runtime._response_to_text_result(grok_response, "grok-4.3")  # noqa: SLF001
    claude_result = runtime._response_to_text_result(claude_response, "claude-sonnet-4-6")  # noqa: SLF001
    fallback_result = fallback_runtime.call_text(
        "fallback prompt",
        model_id="gemini-2.5-flash",
        retries=1,
        timeout_seconds=1,
        transient_wait_seconds=0,
        timeout_wait_seconds=0,
    )
    timeout_result = timeout_runtime.call_text(
        "timeout prompt",
        model_id="grok-4.3",
        retries=1,
        timeout_seconds=17,
        transient_wait_seconds=0,
        timeout_wait_seconds=0,
    )
    recording_grok_runtime._call_once(  # noqa: SLF001
        "score this",
        "grok-4.3",
        config=_SchemaConfig(),
        timeout_seconds=19,
    )
    recording_kimi_runtime._call_once(  # noqa: SLF001
        "short visible answer",
        "kimi-k2.6",
        max_tokens=8,
        timeout_seconds=19,
    )
    kimi_default_kwargs = dict(recording_kimi_runtime.completions.kwargs)
    recording_kimi_runtime._call_once(  # noqa: SLF001
        "caller controls thinking",
        "kimi-k2.6",
        config={"temperature": 1, "thinking": {"type": "enabled"}},
        max_tokens=512,
        timeout_seconds=19,
    )
    kimi_explicit_kwargs = dict(recording_kimi_runtime.completions.kwargs)

    cases = [
        {
            "case_id": "model_family_aliases_resolve_canonically",
            "passed": (
                resolve_model_id("gemini") == "gemini-3.1-pro-preview"
                and resolve_model_id("gemini-pro") == "gemini-3.1-pro-preview"
                and resolve_model_id("deepseek-reasoner") == "deepseek-reasoner"
                and resolve_model_id("kimi") == "kimi-k2.6"
                and resolve_model_id("kimi-code") == "kimi-k2.7-code"
                and resolve_model_id("grok") == "grok-4.3"
                and resolve_model_id("grok-code") == "grok-build-0.1"
                and resolve_director_model_id("gpt4o") == "o1"
                and resolve_director_model_id("deepseek") == "deepseek-chat"
                and resolve_director_model_id("kimi-code-fast") == "kimi-k2.7-code-highspeed"
                and resolve_director_model_id("xai") == "grok-4.3"
                and get_model_family("deepseek-chat") == "deepseek"
                and get_model_family("kimi-k2.6") == "kimi"
                and get_model_family("grok-4.3") == "grok"
            ),
        },
        {
            "case_id": "pricing_names_normalize_provider_variants",
            "passed": (
                pricing_model_name("models/gemini-2.5-flash") == "gemini-2.5-flash"
                and pricing_model_name("claude-sonnet-4-6-20260401") == "claude-sonnet-4-6"
                and pricing_model_name("gpt-4o-2026-04-01") == "gpt-4o"
                and pricing_model_name("deepseek-reasoner-v1") == "deepseek-reasoner"
                and pricing_model_name("kimi-k2.7-code-highspeed") == "kimi-k2.7-code-highspeed"
                and pricing_model_name("kimi-k2.6-20260620") == "kimi-k2.6"
                and pricing_model_name("grok-4.3-20260620") == "grok-4.3"
                and pricing_model_name("grok-build-0.1") == "grok-build-0.1"
            ),
        },
        {
            "case_id": "gemini_usage_is_extracted",
            "passed": (
                gemini_result.text == "gemini text"
                and gemini_result.usage.input_tokens == 111
                and gemini_result.usage.output_tokens == 22
                and gemini_result.usage.cache_read_input_tokens == 7
                and gemini_result.model_name == "models/gemini-2.5-flash"
            ),
        },
        {
            "case_id": "openai_usage_is_extracted",
            "passed": (
                openai_result.text == "openai text"
                and openai_result.usage.input_tokens == 210
                and openai_result.usage.output_tokens == 45
                and openai_result.usage.cache_read_input_tokens == 15
                and openai_result.model_name == "gpt-4o-2026-04-01"
            ),
        },
        {
            "case_id": "deepseek_usage_is_extracted_from_chat_completions_response",
            "passed": (
                deepseek_result.text == "deepseek text"
                and deepseek_result.usage.input_tokens == 410
                and deepseek_result.usage.output_tokens == 85
                and deepseek_result.model_name == "deepseek-reasoner"
            ),
        },
        {
            "case_id": "kimi_usage_is_extracted_from_chat_completions_response",
            "passed": (
                kimi_result.text == "kimi text"
                and kimi_result.usage.input_tokens == 510
                and kimi_result.usage.output_tokens == 95
                and kimi_result.usage.cache_read_input_tokens == 30
                and kimi_result.model_name == "kimi-k2.6"
            ),
        },
        {
            "case_id": "grok_usage_is_extracted_from_chat_completions_response",
            "passed": (
                grok_result.text == "grok text"
                and grok_result.usage.input_tokens == 610
                and grok_result.usage.output_tokens == 105
                and grok_result.usage.cache_read_input_tokens == 40
                and grok_result.model_name == "grok-4.3"
            ),
        },
        {
            "case_id": "claude_usage_is_extracted",
            "passed": (
                claude_result.text == "claude text"
                and claude_result.usage.input_tokens == 310
                and claude_result.usage.output_tokens == 55
                and claude_result.usage.cache_creation_input_tokens == 40
                and claude_result.usage.cache_read_input_tokens == 12
                and claude_result.model_name == "claude-sonnet-4-6-20260401"
            ),
        },
        {
            "case_id": "transient_provider_failure_falls_back_to_configured_model",
            "passed": (
                fallback_result.text == "fallback claude text"
                and fallback_result.requested_model_id == "gemini-2.5-flash"
                and fallback_result.effective_model_id == "claude-sonnet-4-6"
                and fallback_result.fallback_from_model_id == "gemini-2.5-flash"
                and fallback_runtime.calls == ["gemini-2.5-flash", "claude-sonnet-4-6"]
            ),
        },
        {
            "case_id": "transport_receives_call_timeout_budget",
            "passed": (
                timeout_result.text == "timeout checked"
                and timeout_runtime.seen_timeout_seconds == 17
            ),
        },
        {
            "case_id": "chat_completion_transport_receives_json_contract",
            "passed": (
                recording_grok_runtime.completions.kwargs.get("response_format") == {"type": "json_object"}
                and recording_grok_runtime.completions.kwargs.get("timeout") == 19
                and "RESPONSE CONTRACT:" in str(recording_grok_runtime.completions.kwargs["messages"][0]["content"])
            ),
        },
        {
            "case_id": "kimi_transport_applies_visible_output_floor",
            "passed": kimi_default_kwargs.get("max_tokens") == 256,
        },
        {
            "case_id": "kimi_k26_defaults_disable_thinking_for_visible_text",
            "passed": (
                kimi_default_kwargs.get("temperature") == 0.6
                and kimi_default_kwargs.get("extra_body") == {"thinking": {"type": "disabled"}}
            ),
        },
        {
            "case_id": "kimi_k26_explicit_thinking_config_overrides_defaults",
            "passed": (
                kimi_explicit_kwargs.get("temperature") == 1
                and kimi_explicit_kwargs.get("extra_body") == {"thinking": {"type": "enabled"}}
            ),
        },
    ]

    all_passed = all(case["passed"] for case in cases)
    return {
        "suite": "llm_runtime_fixture_regression",
        "all_passed": all_passed,
        "num_cases": len(cases),
        "num_passed": sum(1 for case in cases if case["passed"]),
        "results": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run llm runtime fixture regression.")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = run_llm_runtime_fixture_regression()
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")

    print(
        f"LLM runtime fixture regression: {summary['num_passed']}/{summary['num_cases']} passed "
        f"(all_passed={summary['all_passed']})"
    )
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status} {result['case_id']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
