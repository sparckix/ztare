from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ztare.common.llm_runtime import (
    LLMRuntime,
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

    def _call_once(self, prompt: str, model_id: str, *, config=None, max_tokens: int = 16000):
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


def run_llm_runtime_fixture_regression() -> dict[str, object]:
    runtime = LLMRuntime()
    fallback_runtime = _FallbackRuntime()

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
    claude_result = runtime._response_to_text_result(claude_response, "claude-sonnet-4-6")  # noqa: SLF001
    fallback_result = fallback_runtime.call_text(
        "fallback prompt",
        model_id="gemini-2.5-flash",
        retries=1,
        timeout_seconds=1,
        transient_wait_seconds=0,
        timeout_wait_seconds=0,
    )

    cases = [
        {
            "case_id": "model_family_aliases_resolve_canonically",
            "passed": (
                resolve_model_id("gemini") == "gemini-2.5-flash"
                and resolve_model_id("gemini-pro") == "gemini-3.1-pro-preview"
                and resolve_director_model_id("gpt4o") == "o1"
            ),
        },
        {
            "case_id": "pricing_names_normalize_provider_variants",
            "passed": (
                pricing_model_name("models/gemini-2.5-flash") == "gemini-2.5-flash"
                and pricing_model_name("claude-sonnet-4-6-20260401") == "claude-sonnet-4-6"
                and pricing_model_name("gpt-4o-2026-04-01") == "gpt-4o"
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
