from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any


GOOGLE_GENAI_KEY_ENV = ("GEMINI_API_KEY", "GOOGLE_API_KEY")


def _select_google_genai_key(api_key: str | None = None) -> tuple[str | None, str | None]:
    if api_key:
        for env_name in GOOGLE_GENAI_KEY_ENV:
            if os.environ.get(env_name) == api_key:
                return api_key, env_name
        return api_key, "GEMINI_API_KEY"
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"], "GEMINI_API_KEY"
    if os.environ.get("GOOGLE_API_KEY"):
        return os.environ["GOOGLE_API_KEY"], "GOOGLE_API_KEY"
    return None, None


def build_google_genai_client(
    client_factory: Callable[..., Any],
    *,
    api_key: str | None = None,
) -> Any:
    """Construct a Google GenAI client without provider-key warning chatter.

    The upstream SDK inspects both GEMINI_API_KEY and GOOGLE_API_KEY during
    construction and prints a warning to stdout when both are present, even when
    an explicit api_key is supplied. JSON-mode reports import embedding and LLM
    health paths, so that stdout warning corrupts their machine-readable output.
    Mask the non-selected key only during construction, then restore the process
    environment exactly as the caller had it.
    """
    selected_key, selected_env = _select_google_genai_key(api_key)
    if not selected_key or not selected_env:
        return client_factory(api_key=api_key)

    saved = {env_name: os.environ.get(env_name) for env_name in GOOGLE_GENAI_KEY_ENV}
    try:
        for env_name in GOOGLE_GENAI_KEY_ENV:
            if env_name == selected_env:
                os.environ[env_name] = selected_key
            else:
                os.environ.pop(env_name, None)
        return client_factory(api_key=selected_key)
    finally:
        for env_name, value in saved.items():
            if value is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = value
