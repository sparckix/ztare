from pathlib import Path

from ztare.common import llm_runtime
from ztare.common.llm_runtime import LLMRuntime, get_model_family, resolve_model_id


def test_test_thesis_uses_runtime_provider_family_for_judge_branches() -> None:
    text = Path("src/ztare/validator/test_thesis.py").read_text(encoding="utf-8")

    assert "JUDGE_PROVIDER_FAMILY = get_model_family(JUDGE_MODEL_ID)" in text
    assert 'JUDGE_PROVIDER_FAMILY != "google"' in text
    assert 'JUDGE_PROVIDER_FAMILY == "google"' in text
    assert 'startswith(("claude", "gpt", "o1", "o3", "o4", "deepseek"))' not in text


def test_new_chat_completion_judges_are_non_google_provider_families() -> None:
    aliases = {
        "deepseek": "deepseek",
        "kimi": "kimi",
        "grok": "grok",
        "xai": "grok",
        "gpt4.1": "openai",
        "claude": "anthropic",
        "gemini": "google",
    }

    for alias, family in aliases.items():
        assert get_model_family(resolve_model_id(alias)) == family


def test_gemini_model_configuration_requires_optional_sdk(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-key")
    monkeypatch.setattr(llm_runtime, "genai", None)

    assert LLMRuntime().model_is_configured(resolve_model_id("gemini")) is False
