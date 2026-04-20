from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.ztare.common.llm_runtime import pricing_model_name
from src.ztare.common.paths import REPO_ROOT
from src.ztare.supervisor.supervisor_state import TurnUsageTelemetry


@dataclass(frozen=True)
class ModelPricing:
    input_per_million_usd: float
    output_per_million_usd: float
    cache_creation_input_per_million_usd: float = 0.0
    cache_read_input_per_million_usd: float = 0.0


def model_pricing_path() -> Path:
    return REPO_ROOT / "supervisor" / "model_pricing.json"


def load_model_pricing(path: Path | None = None) -> dict[str, ModelPricing]:
    target = path or model_pricing_path()
    if not target.exists():
        return {}
    payload = json.loads(target.read_text())
    if payload.get("enabled") is False:
        return {}
    models = payload.get("models", {})
    return {
        str(model_name): ModelPricing(
            input_per_million_usd=float(entry["input_per_million_usd"]),
            output_per_million_usd=float(entry["output_per_million_usd"]),
            cache_creation_input_per_million_usd=float(
                entry.get("cache_creation_input_per_million_usd", 0.0)
            ),
            cache_read_input_per_million_usd=float(
                entry.get("cache_read_input_per_million_usd", 0.0)
            ),
        )
        for model_name, entry in models.items()
    }


def extract_usage_telemetry(
    *,
    stdout_text: str,
    stderr_text: str,
    sidecar_text: str | None = None,
    default_model_name: str | None = None,
    pricing_path: Path | None = None,
) -> TurnUsageTelemetry:
    usage = None
    for candidate in (sidecar_text, stdout_text, stderr_text):
        if not candidate:
            continue
        usage = _extract_usage_from_json_document(candidate)
        if usage is not None:
            break
        usage = _extract_usage_from_jsonl(candidate)
        if usage is not None:
            break
    if usage is None:
        usage = _extract_usage_from_text(
            "\n".join(part for part in (sidecar_text or "", stdout_text, stderr_text) if part)
        )

    if usage is None:
        return TurnUsageTelemetry(model_name=default_model_name, telemetry_captured=False)

    model_name = usage.get("model_name") or default_model_name
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    cache_creation_input_tokens = int(usage.get("cache_creation_input_tokens", 0))
    cache_read_input_tokens = int(usage.get("cache_read_input_tokens", 0))
    thinking_tokens = int(usage.get("thinking_tokens", 0))
    captured_cost = float(usage.get("estimated_cost_usd", 0.0))
    cost = captured_cost or estimate_cost_usd(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        thinking_tokens=thinking_tokens,
        pricing_path=pricing_path,
    )
    return TurnUsageTelemetry(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        thinking_tokens=thinking_tokens,
        estimated_cost_usd=cost,
        telemetry_captured=any(
            value > 0
            for value in (
                input_tokens,
                output_tokens,
                cache_creation_input_tokens,
                cache_read_input_tokens,
                thinking_tokens,
            )
        ),
    )


def estimate_cost_usd(
    *,
    model_name: str | None,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
    thinking_tokens: int = 0,
    pricing_path: Path | None = None,
) -> float:
    if not model_name:
        return 0.0
    pricing = load_model_pricing(pricing_path)
    canonical_model_name = pricing_model_name(model_name)
    model_pricing = pricing.get(canonical_model_name or model_name)
    if model_pricing is None:
        return 0.0

    total = 0.0
    total += (input_tokens / 1_000_000.0) * model_pricing.input_per_million_usd
    total += (output_tokens / 1_000_000.0) * model_pricing.output_per_million_usd
    total += (thinking_tokens / 1_000_000.0) * model_pricing.output_per_million_usd
    total += (
        cache_creation_input_tokens / 1_000_000.0
    ) * model_pricing.cache_creation_input_per_million_usd
    total += (
        cache_read_input_tokens / 1_000_000.0
    ) * model_pricing.cache_read_input_per_million_usd
    return round(total, 8)


def _extract_usage_from_jsonl(text: str) -> dict[str, Any] | None:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = _find_usage_fields(payload)
        if usage is not None:
            return usage
    return None


def _extract_usage_from_json_document(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if not candidate:
        return None
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return _find_usage_fields(payload)


def _find_usage_fields(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        if "usage" in payload and isinstance(payload["usage"], (dict, list)):
            nested_usage = _find_usage_fields(payload["usage"])
            if nested_usage is not None:
                if payload.get("total_cost_usd") is not None:
                    nested_usage["estimated_cost_usd"] = float(payload["total_cost_usd"])
                if nested_usage.get("model_name") is None and isinstance(payload.get("modelUsage"), dict):
                    try:
                        model_name = next(iter(payload["modelUsage"].keys()))
                    except StopIteration:
                        model_name = None
                    if model_name is not None:
                        nested_usage["model_name"] = str(model_name)
                        model_payload = payload["modelUsage"].get(model_name, {})
                        if (
                            nested_usage.get("estimated_cost_usd") in (None, 0, 0.0)
                            and isinstance(model_payload, dict)
                            and model_payload.get("costUSD") is not None
                        ):
                            nested_usage["estimated_cost_usd"] = float(model_payload["costUSD"])
                return nested_usage
        keys = set(payload.keys())
        token_keys = {
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "cached_input_tokens",
        }
        if keys & token_keys:
            cached_input_tokens = int(payload.get("cached_input_tokens", 0))
            input_details = payload.get("input_tokens_details")
            if isinstance(input_details, dict):
                cached_input_tokens = int(
                    input_details.get("cached_tokens", cached_input_tokens)
                )
            usage = {
                "input_tokens": int(payload.get("input_tokens", 0)),
                "output_tokens": int(payload.get("output_tokens", 0)),
                "cache_creation_input_tokens": int(payload.get("cache_creation_input_tokens", 0)),
                "cache_read_input_tokens": int(
                    payload.get("cache_read_input_tokens", cached_input_tokens)
                ),
            }
            model_name = payload.get("model_name") or payload.get("model")
            if model_name is not None:
                usage["model_name"] = str(model_name)
            if payload.get("total_cost_usd") is not None:
                usage["estimated_cost_usd"] = float(payload["total_cost_usd"])
            elif payload.get("costUSD") is not None:
                usage["estimated_cost_usd"] = float(payload["costUSD"])
            return usage
        for value in payload.values():
            nested = _find_usage_fields(value)
            if nested is not None:
                return nested
    if isinstance(payload, list):
        for item in payload:
            nested = _find_usage_fields(item)
            if nested is not None:
                return nested
    return None


def _extract_usage_from_text(text: str) -> dict[str, Any] | None:
    normalized = text.replace(",", "")
    input_tokens = _match_int(
        normalized,
        (
            r"input[_ ]tokens?[:=]\s*(\d+)",
            r"prompt[_ ]tokens?[:=]\s*(\d+)",
        ),
    )
    output_tokens = _match_int(
        normalized,
        (
            r"output[_ ]tokens?[:=]\s*(\d+)",
            r"completion[_ ]tokens?[:=]\s*(\d+)",
        ),
    )
    cache_creation_input_tokens = _match_int(
        normalized,
        (r"cache[_ ]creation[_ ]input[_ ]tokens?[:=]\s*(\d+)",),
    )
    cache_read_input_tokens = _match_int(
        normalized,
        (r"cache[_ ]read[_ ]input[_ ]tokens?[:=]\s*(\d+)",),
    )
    model_name = _match_str(
        normalized,
        (
            r"model(?:_name)?[:=]\s*([A-Za-z0-9_.:-]+)",
            r"using model\s+([A-Za-z0-9_.:-]+)",
        ),
    )

    if all(
        value == 0
        for value in (
            input_tokens,
            output_tokens,
            cache_creation_input_tokens,
            cache_read_input_tokens,
        )
    ):
        return None

    usage: dict[str, Any] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
    }
    if model_name is not None:
        usage["model_name"] = model_name
    return usage


def _match_int(text: str, patterns: tuple[str, ...]) -> int:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 0


def _match_str(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
