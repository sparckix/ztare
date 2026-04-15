from __future__ import annotations

import concurrent.futures
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

import anthropic
from google import genai
from openai import OpenAI


MODEL_MAP = {
    "gemini": "gemini-2.5-flash",
    "gemini-pro": "gemini-3.1-pro-preview",
    "claude": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "gpt4o": "gpt-4o",
}

DIRECTOR_MODEL_MAP = {
    "gemini": "gemini-3.1-pro-preview",
    "gemini-pro": "gemini-3.1-pro-preview",
    "claude": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "gpt4o": "o1",
}

FALLBACK_MODEL_CHAINS = {
    "gemini-2.5-flash": ("claude-sonnet-4-6", "gpt-4o"),
    "gemini-3.1-pro-preview": ("claude-sonnet-4-6", "gpt-4o"),
    "claude-opus-4-6": ("claude-sonnet-4-6", "gpt-4o", "gemini-2.5-flash"),
    "claude-sonnet-4-6": ("gpt-4o", "gemini-2.5-flash"),
    "gpt-4o": ("claude-sonnet-4-6", "gemini-2.5-flash"),
    "o1": ("claude-sonnet-4-6", "gemini-2.5-flash"),
}


def resolve_model_id(model_family: str) -> str:
    if model_family not in MODEL_MAP:
        raise ValueError(f"Unsupported model family: {model_family}")
    return MODEL_MAP[model_family]


def resolve_director_model_id(model_family: str) -> str:
    if model_family not in DIRECTOR_MODEL_MAP:
        raise ValueError(f"Unsupported model family: {model_family}")
    return DIRECTOR_MODEL_MAP[model_family]


def is_claude_model(model_id: str) -> bool:
    return model_id.startswith("claude")


def is_openai_model(model_id: str) -> bool:
    return model_id.startswith("gpt") or model_id.startswith("o1") or model_id.startswith("o3") or model_id.startswith("o4")


def is_reasoning_openai_model(model_id: str) -> bool:
    return model_id.startswith("o1") or model_id.startswith("o3") or model_id.startswith("o4")


def pricing_model_name(model_name: str | None) -> str | None:
    if not model_name:
        return None
    normalized = model_name.strip()
    if normalized.startswith("models/"):
        normalized = normalized.split("/", 1)[1]
    lowered = normalized.lower()
    if lowered.startswith("claude-sonnet-4"):
        return "claude-sonnet-4-6"
    if lowered.startswith("claude-opus-4"):
        return "claude-opus-4-6"
    if lowered.startswith("gemini-2.5-flash"):
        return "gemini-2.5-flash"
    if lowered.startswith("gemini-3.1-pro-preview"):
        return "gemini-3.1-pro-preview"
    if lowered.startswith("gpt-4o"):
        return "gpt-4o"
    if lowered.startswith("o1"):
        return "o1"
    return normalized


@dataclass(frozen=True)
class LLMUsage:
    model_name: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    direct_cost_usd: float | None = None


@dataclass(frozen=True)
class LLMTextResponse:
    text: str
    model_name: str | None
    usage: LLMUsage
    raw_response: Any
    requested_model_id: str | None = None
    effective_model_id: str | None = None
    fallback_from_model_id: str | None = None


class LLMRuntimeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        model_id: str,
        transient: bool = False,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.model_id = model_id
        self.transient = transient
        self.status_code = status_code


class LLMRuntime:
    def __init__(self) -> None:
        self._gemini_client = None
        self._anthropic_client = None
        self._openai_client = None

    def gemini_client(self):
        if self._gemini_client is None and os.environ.get("GEMINI_API_KEY"):
            self._gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        return self._gemini_client

    def anthropic_client(self):
        if self._anthropic_client is None and os.environ.get("ANTHROPIC_API_KEY"):
            self._anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        return self._anthropic_client

    def openai_client(self):
        if self._openai_client is None and os.environ.get("OPENAI_API_KEY"):
            self._openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        return self._openai_client

    def require_gemini_client(self):
        client = self.gemini_client()
        if client is None:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        return client

    def model_is_configured(self, model_id: str) -> bool:
        if is_claude_model(model_id):
            return bool(os.environ.get("ANTHROPIC_API_KEY"))
        if is_openai_model(model_id):
            return bool(os.environ.get("OPENAI_API_KEY"))
        return bool(os.environ.get("GEMINI_API_KEY"))

    def default_fallback_model_ids(self, model_id: str) -> tuple[str, ...]:
        configured: list[str] = []
        seen: set[str] = {model_id}
        for candidate in FALLBACK_MODEL_CHAINS.get(model_id, ()):
            if candidate in seen:
                continue
            seen.add(candidate)
            if self.model_is_configured(candidate):
                configured.append(candidate)
        return tuple(configured)

    def _error_status_code(self, exc: Exception) -> int | None:
        status_code = getattr(exc, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if isinstance(response_status, int):
            return response_status
        return None

    def is_transient_error(self, exc: Exception) -> bool:
        status_code = self._error_status_code(exc)
        if status_code in {408, 409, 429, 500, 502, 503, 504}:
            return True
        message = str(exc).upper()
        transient_markers = [
            "UNAVAILABLE",
            "RESOURCE_EXHAUSTED",
            "RATE LIMIT",
            "TIMEOUT",
            "TIMED OUT",
            "CONNECTION RESET",
            "BROKEN PIPE",
            "REMOTEPROTOCOLERROR",
            "TEMPORARY",
            "OVERLOADED",
            "HIGH DEMAND",
            "READERROR",
        ]
        return any(marker in message for marker in transient_markers)

    def retry_delay_seconds(self, attempt: int, exc: Exception, *, base_delay: int = 20) -> int:
        if self.is_transient_error(exc):
            return min(120, base_delay * attempt)
        return min(15, 2 * attempt)

    def _call_once(self, prompt: str, model_id: str, *, config: Any = None, max_tokens: int = 16000):
        if is_claude_model(model_id):
            client = self.anthropic_client()
            if client is None:
                raise RuntimeError("ANTHROPIC_API_KEY is not set.")
            return client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

        if is_openai_model(model_id):
            client = self.openai_client()
            if client is None:
                raise RuntimeError("OPENAI_API_KEY is not set.")
            kwargs = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
            }
            if is_reasoning_openai_model(model_id):
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
            return client.chat.completions.create(**kwargs)

        client = self.gemini_client()
        if client is None:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        return client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config,
        )

    def _response_to_text_result(
        self,
        response: Any,
        requested_model_id: str,
        *,
        original_requested_model_id: str | None = None,
    ) -> LLMTextResponse:
        effective_model_id = requested_model_id
        original_model_id = original_requested_model_id or requested_model_id
        fallback_from_model_id = (
            original_model_id if original_model_id != effective_model_id else None
        )
        if is_claude_model(requested_model_id):
            usage = getattr(response, "usage", None)
            model_name = getattr(response, "model", None) or requested_model_id
            text = response.content[0].text if getattr(response, "content", None) else ""
            return LLMTextResponse(
                text=text,
                model_name=model_name,
                usage=LLMUsage(
                    model_name=model_name,
                    input_tokens=getattr(usage, "input_tokens", 0) if usage is not None else 0,
                    output_tokens=getattr(usage, "output_tokens", 0) if usage is not None else 0,
                    cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0)
                    if usage is not None
                    else 0,
                    cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0)
                    if usage is not None
                    else 0,
                ),
                raw_response=response,
                requested_model_id=original_model_id,
                effective_model_id=effective_model_id,
                fallback_from_model_id=fallback_from_model_id,
            )

        if is_openai_model(requested_model_id):
            usage = getattr(response, "usage", None)
            input_tokens = 0
            output_tokens = 0
            cache_read_input_tokens = 0
            direct_cost_usd = None
            if usage is not None:
                input_tokens = int(getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", 0)) or 0)
                output_tokens = int(
                    getattr(usage, "completion_tokens", getattr(usage, "output_tokens", 0)) or 0
                )
                prompt_details = getattr(usage, "prompt_tokens_details", None)
                input_details = getattr(usage, "input_tokens_details", None)
                cache_read_input_tokens = int(
                    getattr(prompt_details, "cached_tokens", 0)
                    or getattr(input_details, "cached_tokens", 0)
                    or 0
                )
            model_name = getattr(response, "model", None) or requested_model_id
            text = response.choices[0].message.content if getattr(response, "choices", None) else ""
            return LLMTextResponse(
                text=text or "",
                model_name=model_name,
                usage=LLMUsage(
                    model_name=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_input_tokens=cache_read_input_tokens,
                    direct_cost_usd=direct_cost_usd,
                ),
                raw_response=response,
                requested_model_id=original_model_id,
                effective_model_id=effective_model_id,
                fallback_from_model_id=fallback_from_model_id,
            )

        usage_metadata = getattr(response, "usage_metadata", None)
        model_name = getattr(response, "model", None) or requested_model_id
        return LLMTextResponse(
            text=getattr(response, "text", "") or "",
            model_name=model_name,
            usage=LLMUsage(
                model_name=model_name,
                input_tokens=getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata is not None else 0,
                output_tokens=getattr(usage_metadata, "candidates_token_count", 0)
                if usage_metadata is not None
                else 0,
                cache_read_input_tokens=getattr(usage_metadata, "cached_content_token_count", 0)
                if usage_metadata is not None
                else 0,
            ),
            raw_response=response,
            requested_model_id=original_model_id,
            effective_model_id=effective_model_id,
            fallback_from_model_id=fallback_from_model_id,
        )

    def call_text(
        self,
        prompt: str,
        *,
        model_id: str,
        fallback_model_ids: tuple[str, ...] | None = None,
        config: Any = None,
        max_tokens: int = 16000,
        retries: int = 4,
        timeout_seconds: int = 300,
        request_label: str = "request",
        progress_printer: Callable[[str], None] | None = None,
        transient_wait_seconds: int = 20,
        timeout_wait_seconds: int = 15,
    ) -> LLMTextResponse:
        candidate_model_ids = [model_id]
        if os.environ.get("ZTARE_DISABLE_MODEL_FALLBACK") == "1":
            # Hard lock: no cross-model fallback. The caller has declared that
            # an off-family silent failover would invalidate the run (e.g. a
            # pre-registered experiment where the runtime family is sealed).
            # On primary failure we raise rather than quietly switch.
            fallback_candidates: tuple[str, ...] = ()
        else:
            fallback_candidates = (
                self.default_fallback_model_ids(model_id)
                if fallback_model_ids is None
                else fallback_model_ids
            )
        for candidate in fallback_candidates:
            if candidate not in candidate_model_ids:
                candidate_model_ids.append(candidate)

        last_error: Exception | None = None
        last_attempted_model_id = model_id
        for model_index, active_model_id in enumerate(candidate_model_ids):
            if model_index > 0 and progress_printer is not None:
                progress_printer(
                    "🔁 Provider fallback engaged for "
                    f"{request_label}: {model_id} -> {active_model_id}"
                )
            for attempt in range(1, retries + 1):
                last_attempted_model_id = active_model_id
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                try:
                    if progress_printer is not None:
                        progress_printer(
                            f"📡 [DEBUG] Dispatching {request_label} to {active_model_id}... (Attempt {attempt})"
                        )
                    start_time = time.time()
                    future = executor.submit(
                        self._call_once,
                        prompt,
                        active_model_id,
                        config=config,
                        max_tokens=max_tokens,
                    )
                    response = future.result(timeout=timeout_seconds)
                    elapsed = time.time() - start_time
                    if progress_printer is not None:
                        progress_printer(f"✅ [DEBUG] Response received in {elapsed:.1f}s")
                        if active_model_id != model_id:
                            progress_printer(
                                "🧭 Effective model changed due to provider failover: "
                                f"{model_id} -> {active_model_id}"
                            )
                    return self._response_to_text_result(
                        response,
                        active_model_id,
                        original_requested_model_id=model_id,
                    )
                except concurrent.futures.TimeoutError as exc:
                    last_error = exc
                    wait_time = min(180, timeout_wait_seconds * attempt)
                    if progress_printer is not None:
                        progress_printer(
                            f"⚠️ Zombie Connection Killed. Retrying in {wait_time}s..."
                        )
                    if attempt == retries:
                        break
                    time.sleep(wait_time)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    error_str = str(exc)
                    status_code = self._error_status_code(exc)
                    if status_code in {400, 404}:
                        if progress_printer is not None:
                            progress_printer(f"❌ Configuration/Model Error: {exc}")
                        raise LLMRuntimeError(
                            error_str,
                            model_id=active_model_id,
                            transient=False,
                            status_code=status_code,
                        ) from exc
                    if self.is_transient_error(exc):
                        wait_time = self.retry_delay_seconds(
                            attempt,
                            exc,
                            base_delay=transient_wait_seconds,
                        )
                        if progress_printer is not None:
                            progress_printer(
                                f"⚠️ API Transient Issue ({error_str[:15]}...). Retrying in {wait_time}s..."
                            )
                        if attempt == retries:
                            break
                        time.sleep(wait_time)
                    else:
                        if progress_printer is not None:
                            progress_printer(f"❌ Unhandled Exception: {error_str}")
                        raise LLMRuntimeError(
                            error_str,
                            model_id=active_model_id,
                            transient=False,
                            status_code=status_code,
                        ) from exc
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

            if model_index < len(candidate_model_ids) - 1 and progress_printer is not None:
                progress_printer(
                    f"⚠️ Exhausted {active_model_id} after persistent transient failures; trying fallback provider."
                )

        raise LLMRuntimeError(
            f"Max retries exceeded across provider chain starting at {model_id}: {last_error}",
            model_id=last_attempted_model_id,
            transient=self.is_transient_error(last_error) if last_error is not None else False,
            status_code=self._error_status_code(last_error) if last_error is not None else None,
        ) from last_error
