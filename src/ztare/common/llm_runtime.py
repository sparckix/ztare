from __future__ import annotations

import concurrent.futures
import json
import os
import queue
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from ztare.common.google_genai_client import build_google_genai_client

try:
    from openai import OpenAI
except Exception:  # openai SDK not installed / import error
    OpenAI = None  # type: ignore[assignment]

# google-genai is an OPTIONAL provider (Gemini path only, used once at
# the Gemini client construction below). A top-level hard import made
# its absence poison EVERY module that transitively imports llm_runtime
# (apparatus debt: it silently killed the deterministic PDE-estimate
# preflight + anything else). Guard it so a missing optional SDK fails
# LAZILY at actual Gemini use, not at import — the standard
# optional-provider pattern. General-purpose: unblocks all transitive
# importers in any env without google-genai. Fixed 2026-05-16.
try:
    from google import genai
except Exception:  # google-genai not installed / import error
    genai = None  # type: ignore[assignment]

try:
    import anthropic
except Exception:  # anthropic SDK not installed / import error
    anthropic = None  # type: ignore[assignment]


def _bootstrap_dotenv_if_needed() -> str | None:
    """Load .env from the project root when API keys are absent from os.environ.

    Required because daemon-spawned subprocess chains (daemon → claude CLI →
    make → python) propagate scrubbed env (no ANTHROPIC_API_KEY/OPENAI_API_KEY,
    so claude CLI uses subscription instead of API key). The substrate runs
    that python then triggers DO need API access. Without this bootstrap they
    would silently fail with "no key set" at SDK construction.

    No-op if all provider keys already present in env (the local developer flow where
    keys are exported in shell). Reads .env quietly; no override of present env.
    """
    if (all(
            os.environ.get(k)
            for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY")
        )
            and (os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY"))
            and (os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY"))
            and (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))):
        # GEMINI/GOOGLE included so the embedding engine (semantic shelf / atlases) gets its key too —
        # omitting it let the gate pass while the shelf was silently dead ("no GOOGLE_API_KEY").
        return None
    try:
        from dotenv import load_dotenv  # python-dotenv (already in requirements)
    except ImportError:
        return None  # graceful: if dotenv missing, fall back to whatever os.environ has
    try:
        candidate = Path(__file__).resolve().parents[3] / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return str(candidate)
    except Exception:  # noqa: BLE001
        return None
    return None


def bootstrap_dotenv_from_repo_root() -> str | None:
    """Explicit entrypoint for repo-root dotenv resolution.

    Importing this module must not depend on the process cwd. Callers that need
    environment hydration should invoke this once from a known entrypoint.
    """
    return _bootstrap_dotenv_if_needed()


MODEL_MAP = {
    "gemini": "gemini-3.1-pro-preview",
    "gemini-lite": "gemini-3.1-flash-lite-preview",
    "gemini-pro": "gemini-3.1-pro-preview",
    "claude": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "gpt4o": "gpt-4o",
    "gpt4.1": "gpt-4.1",
    "gpt4.1-mini": "gpt-4.1-mini",
    "gpt5.5": "gpt-5.5",
    # GPT-5.6 generation (sol/terra/luna) — verified 2026-07-10 via codex CLI 0.144.0.
    # sol: most capable, high reasoning ceiling. terra: balanced. luna: fast/light.
    "sol": "gpt-5.6-sol",
    "terra": "gpt-5.6-terra",
    "luna": "gpt-5.6-luna",
    "gpt-5.6-sol": "gpt-5.6-sol",
    "gpt-5.6-terra": "gpt-5.6-terra",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gpt5.6": "gpt-5.6-sol",  # ponytail: default to sol for bare version alias
    # GP-134 reasoning-model support (2026-04-23): added o3 family for
    # reasoning-heavy substrates (e.g., gp090_01 sopfr cold-recovery)
    # where chain-of-thought depth matters more than token throughput.
    "o1": "o1",
    "o3": "o3",
    "o3-mini": "o3-mini",
    "o3-pro": "o3-pro",
    "o4-mini": "o4-mini",
    # DeepSeek family (2026-05-26): added as cross-family verification option
    # for adversarial review and committee panels per AGENTS.md §6n.3.
    # Chat Completions transport endpoint (base_url=api.deepseek.com/v1).
    # `deepseek` = V3 chat (fast, ~1-2s). `deepseek-reasoner` = R1 (slow,
    # ~30-90s, needs 8K+ output budget for internal reasoning tokens).
    "deepseek": "deepseek-chat",
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
    # Kimi / Moonshot family (Chat Completions transport).
    # `kimi` is the current general agent/reasoning model. Keep deprecated
    # `kimi-latest` / `kimi-k2-*-preview` out of the alias table.
    "kimi": "kimi-k2.6",
    "kimi-k2.6": "kimi-k2.6",
    "kimi-k2.5": "kimi-k2.5",
    "kimi-code": "kimi-k2.7-code",
    "kimi-code-fast": "kimi-k2.7-code-highspeed",
    "kimi-k2.7-code": "kimi-k2.7-code",
    "kimi-k2.7-code-highspeed": "kimi-k2.7-code-highspeed",
    "moonshot-v1-8k": "moonshot-v1-8k",
    "moonshot-v1-32k": "moonshot-v1-32k",
    "moonshot-v1-128k": "moonshot-v1-128k",
    # Grok / xAI family (Chat Completions transport).
    # `grok` follows xAI's current stable alias for the general text model.
    "grok": "grok-4.3",
    "xai": "grok-4.3",
    "grok-4.3": "grok-4.3",
    "grok-build": "grok-build-0.1",
    "grok-code": "grok-build-0.1",
    "grok-build-0.1": "grok-build-0.1",
}

# Engine-neutral effort vocabulary. Product surfaces use only these three
# values; transport adapters lower `high` to the deepest documented tier of
# the selected subscription runtime. Native spellings remain accepted by the
# low-level runtime for expert/debug callers, never in campaign contracts.
NORMALIZED_REASONING_EFFORTS = ("low", "medium", "high", "ultra")
SUBSCRIPTION_MODEL_ALIASES = {
    "fable": ("claude", "claude-fable-5"),
    "claude-fable-5": ("claude", "claude-fable-5"),
}
_SUBSCRIPTION_EFFORTS = {
    "codex": {
        "low": "low",
        "medium": "medium",
        "high": "xhigh",
        "ultra": "ultra",
        "minimal": "minimal",
        "xhigh": "xhigh",
        "max": "max",
    },
    "claude": {
        "low": "low",
        "medium": "medium",
        "high": "max",
        "ultra": "max",
        "xhigh": "xhigh",
        "max": "max",
    },
}

_SUBSCRIPTION_MODEL_EFFORTS = {
    # GPT-5.5's Responses endpoint stops at `xhigh`.  Codex CLI accepts the
    # normalized spelling `ultra` but lowers it internally to the unsupported
    # API value `max`, so pin this model before the command is launched.
    ("codex", "gpt-5.5"): {
        "high": "xhigh",
        "ultra": "xhigh",
        "xhigh": "xhigh",
    },
    # Luna exposes `max` as its deepest native tier.  Keep campaign-facing
    # `ultra` engine-neutral and lower it only after model routing.
    ("codex", "gpt-5.6-luna"): {
        "high": "high",
        "ultra": "max",
        "max": "max",
    },
}

_SUBSCRIPTION_MODEL_MINIMUM_CLI = {
    ("codex", "gpt-5.6-sol"): (0, 144, 0),
    ("codex", "gpt-5.6-terra"): (0, 144, 0),
    ("codex", "gpt-5.6-luna"): (0, 144, 0),
}


def subscription_model_route(
    model: str,
    *,
    requested_runtime: str = "",
) -> tuple[str, str]:
    """Resolve a subscription model alias and its compatible agent runtime."""

    raw = str(model or "").strip()
    lowered = raw.lower()
    alias = SUBSCRIPTION_MODEL_ALIASES.get(lowered)
    if alias is not None:
        return alias
    if lowered.startswith("claude"):
        return "claude", raw
    if lowered.startswith(("gpt", "o1", "o3", "o4", "codex", "sol", "terra", "luna")):
        return "codex", MODEL_MAP.get(lowered, raw)
    runtime = str(requested_runtime or "codex").strip().lower()
    return runtime, raw


def subscription_reasoning_effort(
    runtime: str,
    value: str,
    *,
    model: str = "",
) -> str | None:
    """Lower normalized effort to one subscription CLI's native vocabulary."""

    runtime_key = str(runtime).strip().lower()
    value_key = str(value).strip().lower()
    model_key = MODEL_MAP.get(str(model).strip().lower(), str(model).strip().lower())
    model_table = _SUBSCRIPTION_MODEL_EFFORTS.get((runtime_key, model_key))
    if model_table is not None and value_key in model_table:
        return model_table[value_key]
    table = _SUBSCRIPTION_EFFORTS.get(runtime_key)
    if table is None:
        return None
    return table.get(value_key)


def validate_subscription_model_cli(
    runtime: str,
    model: str,
    cli_version: str,
) -> None:
    """Reject a subscription route that the installed agent CLI cannot serve."""

    key = (str(runtime).strip().lower(), str(model).strip().lower())
    minimum = _SUBSCRIPTION_MODEL_MINIMUM_CLI.get(key)
    if minimum is None:
        return
    match = re.search(r"(?<![0-9])(\d+)\.(\d+)\.(\d+)(?![0-9])", str(cli_version))
    if match is None:
        raise ValueError(
            f"cannot verify {key[0]} CLI compatibility for {key[1]}: {cli_version!r}"
        )
    installed = tuple(int(value) for value in match.groups())
    if installed < minimum:
        required = ".".join(str(value) for value in minimum)
        found = ".".join(str(value) for value in installed)
        raise ValueError(
            f"{key[1]} requires {key[0]} CLI >= {required}; found {found}"
        )

DIRECTOR_MODEL_MAP = {
    "gemini": "gemini-3.1-pro-preview",
    "gemini-lite": "gemini-3.1-pro-preview",
    "gemini-pro": "gemini-3.1-pro-preview",
    "claude": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "gpt4o": "o1",
    "gpt4.1": "gpt-4.1",
    "gpt4.1-mini": "gpt-4.1-mini",
    "gpt5.5": "gpt-5.5",
    "sol": "gpt-5.6-sol",
    "terra": "gpt-5.6-terra",
    "luna": "gpt-5.6-luna",
    "gpt-5.6-sol": "gpt-5.6-sol",
    "gpt-5.6-terra": "gpt-5.6-terra",
    "gpt-5.6-luna": "gpt-5.6-luna",
    "gpt5.6": "gpt-5.6-sol",
    "o1": "o1",
    "o3": "o3",
    "o3-mini": "o3-mini",
    "o3-pro": "o3-pro",
    "o4-mini": "o4-mini",
    "deepseek": "deepseek-chat",
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
    "kimi": "kimi-k2.6",
    "kimi-k2.6": "kimi-k2.6",
    "kimi-k2.5": "kimi-k2.5",
    "kimi-code": "kimi-k2.7-code",
    "kimi-code-fast": "kimi-k2.7-code-highspeed",
    "kimi-k2.7-code": "kimi-k2.7-code",
    "kimi-k2.7-code-highspeed": "kimi-k2.7-code-highspeed",
    "moonshot-v1-8k": "moonshot-v1-8k",
    "moonshot-v1-32k": "moonshot-v1-32k",
    "moonshot-v1-128k": "moonshot-v1-128k",
    "grok": "grok-4.3",
    "xai": "grok-4.3",
    "grok-4.3": "grok-4.3",
    "grok-build": "grok-build-0.1",
    "grok-code": "grok-build-0.1",
    "grok-build-0.1": "grok-build-0.1",
}

MODEL_FAMILY_CHOICES = tuple(MODEL_MAP.keys())

# Retry budget for production mutator/judge calls.
# 2026-04-15: bumped 12 -> 25 after a gemini 503 flap.
# 2026-04-27: dropped 25 -> 3 after audit found stealth billing on OpenAI
# connection-error retries: each attempt re-sends the full prompt, OpenAI
# bills input tokens once received (before stream death), and the SDK
# does not return usage on exception. With 25 retries × 22k input tokens
# at gpt-5.5 input pricing, a single connection-storm iter costs ~$0.69
# while the apparatus reports $0. Three retries is plenty for transient
# errors and caps the worst-case at ~$0.08/iter.
PRODUCTION_CALL_RETRIES = 3

# Module-level tracker for billed-but-unreported tokens from failed
# retries (the 2026-04-27 audit fix). Each retry on a non-fatal exception
# pushes a conservative input-token estimate here, KEYED BY MODEL so a
# cross-provider fallback (gpt-5.5 retried 3× → gpt-4o retried 3×)
# attributes the right pricing to each model rather than rolling them
# all up to the last-attempted model. Callers drain in a finally-block
# and accrue per-model so apparatus telemetry stays accurate.
import threading

_FAILED_RETRY_LOCK = threading.Lock()
_FAILED_RETRY_TRACKER: dict = {
    # model_name -> {"input_tokens": int, "attempts": int}
}


def drain_failed_retry_tracker() -> dict:
    """Return-and-clear the per-model failed-retry tracker.

    Returns a flat dict for backward compatibility with the v1 caller
    (autoresearch_loop's safe_mutate), with the addition of a `per_model`
    sub-dict for proper cross-provider attribution. Top-level keys are
    summed across all models. Clears state on read.

    Returned shape:
        {
            "attempts": int,           # sum across models
            "input_tokens": int,       # sum across models
            "model_name": str | None,  # most-recent model (first if tie)
            "per_model": {model: {"input_tokens": int, "attempts": int}, ...},
        }
    """
    with _FAILED_RETRY_LOCK:
        per_model = {k: dict(v) for k, v in _FAILED_RETRY_TRACKER.items()}
        _FAILED_RETRY_TRACKER.clear()
    total_input = sum(m["input_tokens"] for m in per_model.values())
    total_attempts = sum(m["attempts"] for m in per_model.values())
    most_recent_model = next(iter(per_model.keys()), None)
    return {
        "attempts": total_attempts,
        "input_tokens": total_input,
        "model_name": most_recent_model,
        "per_model": per_model,
    }


def _record_failed_retry(prompt: str, model_name: str) -> None:
    """Record one failed retry attempt's billed-input estimate.

    Token estimate uses len(prompt)//3 (conservative — catches Claude
    and Gemini tokenizer densities; OpenAI is typically lower so this
    over-counts slightly, which is the safe direction for a stealth-bill
    estimate the user wants to see).
    """
    estimate = max(1, len(prompt) // 3)
    with _FAILED_RETRY_LOCK:
        bucket = _FAILED_RETRY_TRACKER.setdefault(
            model_name or "unknown",
            {"input_tokens": 0, "attempts": 0},
        )
        bucket["input_tokens"] += estimate
        bucket["attempts"] += 1


FALLBACK_MODEL_CHAINS = {
    "gemini-2.5-flash": ("claude-sonnet-4-6", "gpt-4o"),
    "gemini-3.1-flash-lite-preview": ("gemini-2.5-flash", "claude-sonnet-4-6"),
    "gemini-3.1-pro-preview": ("claude-sonnet-4-6", "gpt-4o"),
    "claude-opus-4-6": ("claude-sonnet-4-6", "gpt-4o", "gemini-2.5-flash"),
    "claude-sonnet-4-6": ("gpt-4o", "gemini-2.5-flash"),
    "gpt-4o": ("claude-sonnet-4-6", "gemini-2.5-flash"),
    "gpt-4.1": ("claude-sonnet-4-6", "gemini-2.5-flash"),
    "gpt-4.1-mini": ("gpt-4.1", "claude-sonnet-4-6", "gemini-2.5-flash"),
    # gpt-5.5 frontier model (2026-04-25). Cross-family fallback to
    # claude-opus-4-6 (closest-tier reasoning) then gpt-4.1, never to
    # cheaper OpenAI models within the same family request.
    "gpt-5.5": ("claude-opus-4-6", "gpt-4.1", "gemini-3.1-pro-preview"),
    "o1": ("claude-sonnet-4-6", "gemini-2.5-flash"),
    "o3": ("o3-mini", "claude-sonnet-4-6", "gpt-4.1"),
    "o3-mini": ("gpt-4.1", "claude-sonnet-4-6"),
    "o3-pro": ("o3", "claude-sonnet-4-6"),
    "o4-mini": ("o3-mini", "gpt-4.1", "claude-sonnet-4-6"),
    "kimi-k2.6": ("claude-sonnet-4-6", "gpt-4.1", "gemini-3.1-pro-preview"),
    "kimi-k2.5": ("kimi-k2.6", "claude-sonnet-4-6", "gpt-4.1"),
    "kimi-k2.7-code": ("kimi-k2.6", "claude-sonnet-4-6", "gpt-4.1"),
    "kimi-k2.7-code-highspeed": ("kimi-k2.7-code", "kimi-k2.6", "gpt-4.1"),
    "grok-4.3": ("gemini-3.1-pro-preview", "gpt-4.1", "kimi-k2.6"),
    "grok-build-0.1": ("grok-4.3", "gemini-3.1-pro-preview", "gpt-4.1"),
}

# Operator directive (2026-07-10): cross-provider API fallback is DISABLED by
# default (gpt→gemini/claude silently substituting family is wrong). The ONLY
# permitted fallback when API is dead/unreachable is the Codex SUBSCRIPTION
# runtime with the SAME requested model family. Gate re-enabled via:
#   ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK=1   (restores old behaviour)
#   ZTARE_DISABLE_SUBSCRIPTION_FALLBACK=1   (no fallback at all — fail loud)
# Only models served by the Codex subscription (OpenAI family: gpt-*/o1/o3/o4)
# qualify for subscription fallback; non-OpenAI families fail loud immediately.
# ponytail: constant, not a function — the set never changes at runtime
CODEX_SERVABLE_FAMILIES: frozenset[str] = frozenset({"openai"})


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


def is_deepseek_model(model_id: str) -> bool:
    return model_id.startswith("deepseek")


def is_kimi_model(model_id: str) -> bool:
    return model_id.startswith("kimi-") or model_id.startswith("moonshot-v1")


def _kimi_visible_text_defaults(model_id: str, config: Any) -> dict[str, Any]:
    """Provider-specific defaults for generic Kimi text calls.

    Live validation on 2026-06-23 showed `kimi-k2.6` can spend the completion
    budget in `reasoning_content` and return little/no visible
    `message.content`. Moonshot accepts a thinking-disable object, but then
    requires temperature 0.6. Apply that only when the caller has not supplied
    its own Kimi thinking/temperature policy.
    """
    def _has_explicit(key: str) -> bool:
        if isinstance(config, dict):
            return key in config and config[key] is not None
        return getattr(config, key, None) is not None

    if model_id != "kimi-k2.6" or _has_explicit("thinking") or _has_explicit("temperature"):
        return {}
    return {
        "temperature": 0.6,
        "extra_body": {"thinking": {"type": "disabled"}},
    }


def is_grok_model(model_id: str) -> bool:
    return model_id.startswith("grok-")


def is_openai_model(model_id: str) -> bool:
    return model_id.startswith("gpt") or model_id.startswith("o1") or model_id.startswith("o3") or model_id.startswith("o4")


def api_reasoning_effort(model_id: str, value: str) -> str | None:
    """Lower normalized effort for the API surface selected by ``model_id``.

    Providers without a supported fine-grained effort parameter return None;
    callers still get the requested model, without fabricated control.
    """

    requested = str(value or "").strip().lower()
    if is_claude_model(model_id):
        return {
            "low": "low", "medium": "medium", "high": "max", "max": "max",
            "ultra": "max",
        }.get(requested)
    if is_openai_model(model_id):
        return {
            "minimal": "minimal", "low": "low", "medium": "medium",
            "high": "high", "xhigh": "xhigh", "ultra": "ultra",
        }.get(requested)
    if is_grok_model(model_id):
        return {
            "low": "low", "medium": "medium", "high": "high", "ultra": "high"
        }.get(requested)
    if not (is_deepseek_model(model_id) or is_kimi_model(model_id)):
        return {
            "low": "LOW", "medium": "MEDIUM", "high": "HIGH", "ultra": "HIGH",
        }.get(requested)
    return None


def is_reasoning_openai_model(model_id: str) -> bool:
    """True for OpenAI models that use the `max_completion_tokens` API
    (reasoning family: o1/o3/o4) and the gpt-5 frontier family which
    follows the same parameter convention. Adding gpt-5.5 here closes
    the 2026-04-25 night API mismatch where gpt-5.5 calls failed with
    'Unsupported parameter: max_tokens'.
    """
    return (
        model_id.startswith("o1")
        or model_id.startswith("o3")
        or model_id.startswith("o4")
        or model_id.startswith("gpt-5")
    )


def get_model_family(model_id: str) -> str:
    """Return provider family for a canonical model ID.

    Returns one of ``"openai"``, ``"anthropic"``, ``"deepseek"``,
    ``"kimi"``, ``"grok"``, or ``"google"``.
    """
    if is_claude_model(model_id):
        return "anthropic"
    if is_deepseek_model(model_id):
        return "deepseek"
    if is_kimi_model(model_id):
        return "kimi"
    if is_grok_model(model_id):
        return "grok"
    if is_openai_model(model_id):
        return "openai"
    return "google"


# ---------------------------------------------------------------------------
# Out-of-loop script helper (2026-05-06)
# ---------------------------------------------------------------------------

# Out-of-loop scripts (negative-prompting wrapper, idea_feliz, falsifier
# prompters) historically hardcoded a single provider. Operators with
# only one set of API credentials silently broke. The function below
# picks a configured model ID based on which API key is set, so those
# scripts can call `LLMRuntime.call_text(prompt, model_id=pick_default_model_id_for_scripts())`
# without provider hardcoding. The autoresearch_loop continues to use
# its `--mutator-model` / `--judge-model` flags + MODEL_MAP — that
# path is unchanged.

# Default cheap-tier model per provider for out-of-loop scripts.
_SCRIPT_DEFAULT_PER_PROVIDER = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4.1",
    "kimi": "kimi-k2.6",
    "deepseek": "deepseek-chat",
    "grok": "grok-4.3",
    "google": "gemini-3.1-pro-preview",
}


def _provider_has_key(provider: str) -> bool:
    env_keys = {
        "anthropic": ("ANTHROPIC_API_KEY",),
        "openai": ("OPENAI_API_KEY",),
        "kimi": ("KIMI_API_KEY", "MOONSHOT_API_KEY"),
        "deepseek": ("DEEPSEEK_API_KEY",),
        "grok": ("XAI_API_KEY", "GROK_API_KEY"),
        "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    }
    return any(os.environ.get(key) for key in env_keys.get(provider, ()))


def _read_principal_model_economy() -> dict | None:
    """Walk cwd-up looking for org/preferences/principal.yaml; return its
    `model_economy` block if set. Cached for process lifetime.

    Schema: see principal.yaml example. Returned dict has keys 'tiers'
    + 'escalation_rules' + 'what_NOT_to_escalate'.
    """
    if hasattr(_read_principal_model_economy, "_cached"):
        return _read_principal_model_economy._cached  # type: ignore[attr-defined]
    try:
        import yaml
    except ImportError:
        _read_principal_model_economy._cached = None  # type: ignore[attr-defined]
        return None
    candidates = []
    cwd = Path.cwd()
    for d in [cwd] + list(cwd.parents):
        candidates.append(d / "org" / "preferences" / "principal.yaml")
    try:
        candidates.append(Path(__file__).resolve().parents[3] / "org" / "preferences" / "principal.yaml")
    except Exception:  # noqa: BLE001
        pass
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            econ = data.get("model_economy")
            if econ:
                _read_principal_model_economy._cached = econ  # type: ignore[attr-defined]
                return econ
        except Exception:  # noqa: BLE001
            continue
    _read_principal_model_economy._cached = None  # type: ignore[attr-defined]
    return None


def _read_principal_model_map() -> "dict | None":
    """The `model_map` POLICY override block from org/preferences/principal.yaml: `{alias: model_id}` merged
    OVER the code `MODEL_MAP` so a deprecated/retargeted version id (e.g. gemini-3.1-pro-preview → a successor)
    is changed in ONE policy file, not N code spots. Same cwd-up search as the model_economy reader; cached;
    absent file/block ⇒ None ⇒ the code defaults stand (byte-parity)."""
    if hasattr(_read_principal_model_map, "_cached"):
        return _read_principal_model_map._cached  # type: ignore[attr-defined]
    out = None
    try:
        import yaml
        cwd = Path.cwd()
        cands = [d / "org" / "preferences" / "principal.yaml" for d in [cwd] + list(cwd.parents)]
        try:
            cands.append(Path(__file__).resolve().parents[3] / "org" / "preferences" / "principal.yaml")
        except Exception:  # noqa: BLE001
            pass
        for path in cands:
            if not path.is_file():
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            mm = data.get("model_map")
            if isinstance(mm, dict) and mm:
                out = {str(k): str(v) for k, v in mm.items()}
                break
    except Exception:  # noqa: BLE001 — a broken policy file must never brick resolution; fall back to code defaults
        out = None
    _read_principal_model_map._cached = out  # type: ignore[attr-defined]
    return out


# Apply the policy override at import (after MODEL_MAP/DIRECTOR_MODEL_MAP are defined above): retarget any
# alias whose hardcoded version went stale, from principal.yaml — no code edit. Absent ⇒ no-op (byte-parity).
try:
    _MODEL_OVERRIDES = _read_principal_model_map() or {}
    if _MODEL_OVERRIDES:
        MODEL_MAP.update(_MODEL_OVERRIDES)
        DIRECTOR_MODEL_MAP.update(_MODEL_OVERRIDES)
except Exception:  # noqa: BLE001
    pass


def pick_model_for_tier(tier: str = "cheap", *, prefer_provider: str | None = None) -> str | None:
    """Return a model id for the requested tier (cheap | mid | pro), honoring
    `model_economy` from principal.yaml + the API key the env actually has.

    Resolution:
      1. Read model_economy.tiers[<tier>].providers from principal.yaml
      2. If `prefer_provider` is set and has API key → use that
      3. Else use principal's preferred_llm_provider (if set + key present)
      4. Else fall through the configured provider families in a stable order
      5. If no model_economy in yaml, fall back to the legacy
         pick_default_model_id_for_scripts() → cheap-tier-equivalent.

    Returns None if no provider available. Caller decides on error.
    """
    if tier not in ("cheap", "mid", "pro"):
        raise ValueError(f"unknown tier: {tier!r}; expected cheap|mid|pro")

    econ = _read_principal_model_economy()
    if not econ:
        # Fallback: no yaml policy — use the existing default for cheap;
        # for mid/pro, return None so caller knows to handle (likely uses
        # default = mid-tier model since pick_default_model_id_for_scripts
        # already returns sonnet/gpt-4.1/gemini-pro).
        if tier == "cheap":
            return pick_default_model_id_for_scripts()
        return pick_default_model_id_for_scripts()  # graceful degradation

    tier_block = (econ.get("tiers") or {}).get(tier) or {}
    providers = tier_block.get("providers") or {}

    # Try in order: explicit prefer, principal's preferred, then stable family order.
    candidate_order = []
    if prefer_provider and prefer_provider in providers:
        candidate_order.append(prefer_provider)
    principal_pref = _read_principal_preferred_provider()
    if principal_pref and principal_pref in providers and principal_pref not in candidate_order:
        candidate_order.append(principal_pref)
    for p in ("google", "openai", "anthropic", "kimi", "deepseek", "grok"):
        if p in providers and p not in candidate_order:
            candidate_order.append(p)

    for provider in candidate_order:
        if _provider_has_key(provider):
            return providers[provider]
    return None


def _read_principal_preferred_provider() -> str | None:
    """Walk cwd-up looking for org/preferences/principal.yaml; return its
    `preferences.preferred_llm_provider` if set. Returns one of
    'anthropic' | 'openai' | 'kimi' | 'deepseek' | 'grok' | 'google' | None.

    Single point of truth for provider preference. Cheap (one file read,
    cached for process lifetime). Walks up the tree the same way
    _bootstrap_dotenv_if_needed does.
    """
    if hasattr(_read_principal_preferred_provider, "_cached"):
        return _read_principal_preferred_provider._cached  # type: ignore[attr-defined]
    try:
        import yaml  # PyYAML is in requirements
    except ImportError:
        _read_principal_preferred_provider._cached = None  # type: ignore[attr-defined]
        return None
    candidates = []
    cwd = Path.cwd()
    for d in [cwd] + list(cwd.parents):
        candidates.append(d / "org" / "preferences" / "principal.yaml")
    try:
        candidates.append(Path(__file__).resolve().parents[3] / "org" / "preferences" / "principal.yaml")
    except Exception:  # noqa: BLE001
        pass
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            prefs = data.get("preferences") or {}
            provider = prefs.get("preferred_llm_provider")
            if provider in _SCRIPT_DEFAULT_PER_PROVIDER:
                _read_principal_preferred_provider._cached = provider  # type: ignore[attr-defined]
                return provider
        except Exception:  # noqa: BLE001
            continue
    _read_principal_preferred_provider._cached = None  # type: ignore[attr-defined]
    return None


def _read_principal_provider_order() -> "list[str] | None":
    """Optional `preferences.preferred_llm_provider_order` list from principal.yaml — an ORDERED
    fallback chain (e.g. ``[kimi, deepseek]`` = kimi primary, deepseek secondary). Mirrors the
    comma-separated ``LLM_DISPATCH_PREF`` env var but as durable org policy. Absent ⇒ None (the
    single-scalar `preferred_llm_provider` path stays in force; byte-parity when neither is set).
    Only known provider families are kept (silently drops typos/unsupported names).
    """
    if hasattr(_read_principal_provider_order, "_cached"):
        return _read_principal_provider_order._cached  # type: ignore[attr-defined]
    try:
        import yaml  # PyYAML is in requirements
    except ImportError:
        _read_principal_provider_order._cached = None  # type: ignore[attr-defined]
        return None
    cwd = Path.cwd()
    candidates = [d / "org" / "preferences" / "principal.yaml" for d in [cwd] + list(cwd.parents)]
    try:
        candidates.append(Path(__file__).resolve().parents[3] / "org" / "preferences" / "principal.yaml")
    except Exception:  # noqa: BLE001
        pass
    # Anchor to the FIRST principal.yaml found walking up from cwd (same authoritative file the
    # scalar reader resolves). Read its order key — None if absent. Do NOT fall through to a
    # different file just because this one lacks the key (that would silently mix two configs).
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        prefs = data.get("preferences") or {}
        raw = prefs.get("preferred_llm_provider_order")
        order = [p for p in raw if p in _SCRIPT_DEFAULT_PER_PROVIDER] if isinstance(raw, (list, tuple)) else []
        result = order or None
        _read_principal_provider_order._cached = result  # type: ignore[attr-defined]
        return result
    _read_principal_provider_order._cached = None  # type: ignore[attr-defined]
    return None


def pick_default_model_id_for_scripts(
    *,
    preference_order: tuple[str, ...] = ("anthropic", "openai", "google", "kimi", "deepseek", "grok"),
) -> str | None:
    """Return a configured model ID based on which API keys are set.

    Resolution priority (highest wins):
      1. ``LLM_DISPATCH_PREF`` env var (comma-separated, e.g. "google,openai")
      2. ``preferences.preferred_llm_provider_order`` list in principal.yaml (ordered chain)
      3. ``preferences.preferred_llm_provider`` scalar in principal.yaml
      4. ``preference_order`` argument (default: anthropic, openai, google, kimi, deepseek, grok)

    Within whichever order wins, returns the default cheap-tier model for
    the first provider whose env key is set. Returns None if none configured.
    """
    env_pref = os.environ.get("LLM_DISPATCH_PREF", "")
    if env_pref:
        # Map external names ("claude" / "gpt" / "gemini") onto canonical
        # family names used here.
        alias_map = {
            "claude": "anthropic",
            "gpt": "openai",
            "gemini": "google",
            "moonshot": "kimi",
            "xai": "grok",
        }
        order = []
        for raw in env_pref.split(","):
            name = raw.strip().lower()
            family = alias_map.get(name, name)
            if family in _SCRIPT_DEFAULT_PER_PROVIDER:
                order.append(family)
        preference_order = tuple(order) if order else preference_order
    else:
        # Honor principal.yaml preference if no env override. An explicit ORDERED list
        # (preferred_llm_provider_order) wins over the single-scalar preference; both move
        # their families to the front and keep the remaining defaults as tail fallbacks.
        principal_order = _read_principal_provider_order()
        principal_pref = _read_principal_preferred_provider()
        front = principal_order or ([principal_pref] if principal_pref else [])
        if front:
            others = [p for p in preference_order if p not in front]
            preference_order = tuple(front) + tuple(others)

    for family in preference_order:
        if family in _SCRIPT_DEFAULT_PER_PROVIDER and _provider_has_key(family):
            return _SCRIPT_DEFAULT_PER_PROVIDER[family]
    return None


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
    if lowered.startswith("gemini-3.1-flash-lite"):
        return "gemini-3.1-flash-lite-preview"
    if lowered.startswith("gemini-2.5-flash"):
        return "gemini-2.5-flash"
    if lowered.startswith("gemini-3.1-pro-preview"):
        return "gemini-3.1-pro-preview"
    if lowered.startswith("gpt-4.1-mini"):
        return "gpt-4.1-mini"
    if lowered.startswith("gpt-4.1"):
        return "gpt-4.1"
    if lowered.startswith("gpt-4o"):
        return "gpt-4o"
    # gpt-5.5 frontier family. Match before any "gpt-5" generic so dated
    # IDs like "gpt-5.5-2026-XX-YY" route to the correct pricing entry.
    if lowered.startswith("gpt-5.5"):
        return "gpt-5.5"
    if lowered.startswith("o1"):
        return "o1"
    # OpenAI reasoning models: SDK returns dated ids like "o3-2025-04-01",
    # "o3-mini-2025-01-31", "o4-mini-2026-01-15". Normalize to the canonical
    # family key in supervisor/model_pricing.json. Ordering matters — match
    # the most-specific prefix first (o3-pro before o3-mini before o3 before o4-mini).
    # Fixes "unavailable (pricing disabled or unknown model)" telemetry for
    # every o3/o4-family run. Bug report 2026-04-24 — gp140 o3/o3 run cost
    # ~$2.50 was shown as unavailable because "o3-<date>" never matched "o3".
    if lowered.startswith("o3-pro"):
        return "o3-pro"
    if lowered.startswith("o3-mini"):
        return "o3-mini"
    if lowered.startswith("o3"):
        return "o3"
    if lowered.startswith("o4-mini"):
        return "o4-mini"
    if lowered.startswith("o4"):
        return "o4"
    # DeepSeek family (2026-05-26): added per AGENTS.md §6n.3 cross-family
    # model integration. Match deepseek-reasoner before deepseek-chat so
    # reasoner IDs like "deepseek-reasoner-v1" route to the reasoner pricing
    # row (higher cost), not the chat row.
    if lowered.startswith("deepseek-reasoner"):
        return "deepseek-reasoner"
    if lowered.startswith("deepseek"):
        return "deepseek-chat"
    if lowered.startswith("kimi-k2.7-code-highspeed"):
        return "kimi-k2.7-code-highspeed"
    if lowered.startswith("kimi-k2.7-code"):
        return "kimi-k2.7-code"
    if lowered.startswith("kimi-k2.6"):
        return "kimi-k2.6"
    if lowered.startswith("kimi-k2.5"):
        return "kimi-k2.5"
    if lowered.startswith("grok-build-0.1"):
        return "grok-build-0.1"
    if lowered.startswith("grok-4.3"):
        return "grok-4.3"
    return normalized


def _response_contract_parts(config: Any) -> tuple[str | None, Any]:
    if config is None:
        return None, None
    if isinstance(config, dict):
        return config.get("response_mime_type"), config.get("response_schema")
    return (
        getattr(config, "response_mime_type", None),
        getattr(config, "response_schema", None),
    )


def _prompt_with_response_contract(prompt: str, config: Any) -> str:
    response_mime, response_schema = _response_contract_parts(config)
    if not response_mime and response_schema is None:
        return prompt
    try:
        schema_text = json.dumps(response_schema, default=str, indent=2) if response_schema is not None else ""
    except TypeError:
        schema_text = str(response_schema)
    return (
        prompt.rstrip()
        + "\n\nRESPONSE CONTRACT:\n"
        + (f"- MIME/type expectation: {response_mime}\n" if response_mime else "")
        + (
            "- Return only one JSON value matching this schema. No markdown, "
            "no prose preamble, no code fences.\n"
            f"{schema_text}\n"
            if schema_text
            else "- Return only one JSON value. No markdown, no prose preamble, no code fences.\n"
        )
    )


def _chat_completion_response_params(config: Any) -> dict[str, Any]:
    response_mime, _response_schema = _response_contract_parts(config)
    if response_mime == "application/json":
        return {"response_format": {"type": "json_object"}}
    return {}


@dataclass(frozen=True)
class LLMUsage:
    model_name: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    thinking_tokens: int = 0
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
        self._deepseek_client = None
        self._kimi_client = None
        self._grok_client = None

    def gemini_client(self):
        gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if self._gemini_client is None and gemini_api_key:
            if genai is None:
                raise RuntimeError(
                    "Gemini provider requested but google-genai is not "
                    "installed (optional dependency). Install `ztare[google]` "
                    "or use the anthropic/openai providers.")
            self._gemini_client = build_google_genai_client(
                genai.Client,
                api_key=gemini_api_key,
            )
        return self._gemini_client

    def anthropic_client(self):
        if self._anthropic_client is None and os.environ.get("ANTHROPIC_API_KEY"):
            if anthropic is None:
                raise RuntimeError(
                    "Anthropic provider requested but anthropic is not "
                    "installed (optional dependency). Install `ztare[anthropic]` "
                    "or use the google/openai providers.")
            self._anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        return self._anthropic_client

    def openai_client(self):
        if self._openai_client is None and os.environ.get("OPENAI_API_KEY"):
            if OpenAI is None:
                raise RuntimeError(
                    "OpenAI provider requested but openai is not installed "
                    "(optional dependency). Install `ztare[openai]` or use the "
                    "anthropic/google providers.")
            self._openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        return self._openai_client

    def deepseek_client(self):
        if self._deepseek_client is None and os.environ.get("DEEPSEEK_API_KEY"):
            if OpenAI is None:
                raise RuntimeError(
                    "DeepSeek provider requested but the Chat Completions "
                    "transport dependency is not installed. Install `ztare[openai]`."
                )
            self._deepseek_client = OpenAI(
                api_key=os.environ.get("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com/v1",
            )
        return self._deepseek_client

    def kimi_client(self):
        kimi_api_key = os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY")
        if self._kimi_client is None and kimi_api_key:
            if OpenAI is None:
                raise RuntimeError(
                    "Kimi provider requested but the Chat Completions "
                    "transport dependency is not installed. Install `ztare[openai]`."
                )
            self._kimi_client = OpenAI(
                api_key=kimi_api_key,
                base_url=(
                    os.environ.get("KIMI_BASE_URL")
                    or os.environ.get("MOONSHOT_BASE_URL")
                    or "https://api.moonshot.ai/v1"
                ),
            )
        return self._kimi_client

    def grok_client(self):
        grok_api_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
        if self._grok_client is None and grok_api_key:
            if OpenAI is None:
                raise RuntimeError(
                    "Grok provider requested but the Chat Completions "
                    "transport dependency is not installed. Install `ztare[openai]`."
                )
            self._grok_client = OpenAI(
                api_key=grok_api_key,
                base_url=os.environ.get("XAI_BASE_URL") or "https://api.x.ai/v1",
            )
        return self._grok_client

    def require_gemini_client(self):
        client = self.gemini_client()
        if client is None:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        return client

    def model_is_configured(self, model_id: str) -> bool:
        if is_claude_model(model_id):
            return bool(os.environ.get("ANTHROPIC_API_KEY")) and anthropic is not None
        if is_deepseek_model(model_id):
            return bool(os.environ.get("DEEPSEEK_API_KEY")) and OpenAI is not None
        if is_kimi_model(model_id):
            return bool(os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY")) and OpenAI is not None
        if is_grok_model(model_id):
            return bool(os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")) and OpenAI is not None
        if is_openai_model(model_id):
            return bool(os.environ.get("OPENAI_API_KEY")) and OpenAI is not None
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")) and genai is not None

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
        if self.is_provider_unavailable_error(exc):
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

    def is_provider_unavailable_error(self, exc: Exception) -> bool:
        message = str(exc).upper()
        unavailable_markers = (
            "CREDIT BALANCE",
            "INSUFFICIENT CREDIT",
            "INSUFFICIENT CREDITS",
            "INSUFFICIENT_QUOTA",
            "QUOTA EXCEEDED",
            "BILLING",
            "PURCHASE CREDITS",
        )
        return any(marker in message for marker in unavailable_markers)

    def retry_delay_seconds(self, attempt: int, exc: Exception, *, base_delay: int = 20) -> int:
        if self.is_transient_error(exc):
            return min(120, base_delay * attempt)
        return min(15, 2 * attempt)

    def _call_once(
        self,
        prompt: str,
        model_id: str,
        *,
        config: Any = None,
        max_tokens: int = 16000,
        timeout_seconds: int | None = None,
    ):
        provider_prompt = _prompt_with_response_contract(prompt, config)
        requested_effort = (
            str(config.get("reasoning_effort") or "")
            if isinstance(config, dict) else ""
        )
        native_effort = api_reasoning_effort(model_id, requested_effort)
        if is_claude_model(model_id):
            client = self.anthropic_client()
            if client is None:
                raise RuntimeError("ANTHROPIC_API_KEY is not set.")
            kwargs = {
                "model": model_id,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": provider_prompt}],
            }
            if timeout_seconds is not None:
                kwargs["timeout"] = timeout_seconds
            if native_effort is not None:
                output_config = dict(
                    config.get("output_config") or {}
                    if isinstance(config, dict) else {}
                )
                output_config["effort"] = native_effort
                kwargs["output_config"] = output_config
            return client.messages.create(**kwargs)

        if is_deepseek_model(model_id):
            client = self.deepseek_client()
            if client is None:
                raise RuntimeError("DEEPSEEK_API_KEY is not set.")
            kwargs = {
                "model": model_id,
                "messages": [{"role": "user", "content": provider_prompt}],
                "max_tokens": max(max_tokens, 8192) if model_id == "deepseek-reasoner" else max_tokens,
            }
            kwargs.update(_chat_completion_response_params(config))
            if isinstance(config, dict):
                for key in ("response_format", "temperature"):
                    if key in config and config[key] is not None:
                        kwargs[key] = config[key]
            if timeout_seconds is not None:
                kwargs["timeout"] = timeout_seconds
            return client.chat.completions.create(**kwargs)

        if is_openai_model(model_id):
            client = self.openai_client()
            if client is None:
                raise RuntimeError("OPENAI_API_KEY is not set.")
            kwargs = {
                "model": model_id,
                "messages": [{"role": "user", "content": provider_prompt}],
            }
            kwargs.update(_chat_completion_response_params(config))
            if is_reasoning_openai_model(model_id):
                kwargs["max_completion_tokens"] = max_tokens
            else:
                kwargs["max_tokens"] = max_tokens
            if isinstance(config, dict):
                for key in ("verbosity", "response_format", "temperature"):
                    if key in config and config[key] is not None:
                        kwargs[key] = config[key]
            if native_effort is not None:
                kwargs["reasoning_effort"] = native_effort
            if timeout_seconds is not None:
                kwargs["timeout"] = timeout_seconds
            return client.chat.completions.create(**kwargs)

        if is_kimi_model(model_id):
            client = self.kimi_client()
            if client is None:
                raise RuntimeError("KIMI_API_KEY or MOONSHOT_API_KEY is not set.")
            kwargs = {
                "model": model_id,
                "messages": [{"role": "user", "content": provider_prompt}],
                "max_tokens": max(max_tokens, 256),
            }
            kwargs.update(_kimi_visible_text_defaults(model_id, config))
            kwargs.update(_chat_completion_response_params(config))
            if isinstance(config, dict):
                for key in ("response_format", "temperature", "top_p"):
                    if key in config and config[key] is not None:
                        kwargs[key] = config[key]
                if config.get("thinking") is not None:
                    extra_body = dict(kwargs.get("extra_body") or {})
                    extra_body["thinking"] = config["thinking"]
                    kwargs["extra_body"] = extra_body
            if timeout_seconds is not None:
                kwargs["timeout"] = timeout_seconds
            return client.chat.completions.create(**kwargs)

        if is_grok_model(model_id):
            client = self.grok_client()
            if client is None:
                raise RuntimeError("XAI_API_KEY or GROK_API_KEY is not set.")
            kwargs = {
                "model": model_id,
                "messages": [{"role": "user", "content": provider_prompt}],
                "max_tokens": max_tokens,
            }
            kwargs.update(_chat_completion_response_params(config))
            if isinstance(config, dict):
                for key in ("response_format", "temperature", "top_p"):
                    if key in config and config[key] is not None:
                        kwargs[key] = config[key]
            if native_effort is not None:
                kwargs["reasoning_effort"] = native_effort
            if timeout_seconds is not None:
                kwargs["timeout"] = timeout_seconds
            return client.chat.completions.create(**kwargs)

        client = self.gemini_client()
        if client is None:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        gemini_config = config
        if isinstance(config, dict) and requested_effort:
            gemini_config = dict(config)
            gemini_config.pop("reasoning_effort", None)
            if native_effort is not None:
                thinking_config = dict(gemini_config.get("thinking_config") or {})
                thinking_config["thinking_level"] = native_effort
                gemini_config["thinking_config"] = thinking_config
        return client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=gemini_config,
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
            if not (text or "").strip():
                stop_reason = getattr(response, "stop_reason", None)
                stop_sequence = getattr(response, "stop_sequence", None)
                raise RuntimeError(
                    "Claude response contained empty message content "
                    f"(model={model_name}, stop_reason={stop_reason!r}, "
                    f"stop_sequence={stop_sequence!r})."
                )
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

        if (
            is_openai_model(requested_model_id)
            or is_deepseek_model(requested_model_id)
            or is_kimi_model(requested_model_id)
            or is_grok_model(requested_model_id)
        ):
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
            if not (text or "").strip() and getattr(response, "choices", None):
                choice = response.choices[0]
                finish_reason = getattr(choice, "finish_reason", None)
                message = getattr(choice, "message", None)
                refusal = getattr(message, "refusal", None) if message is not None else None
                annotations = getattr(message, "annotations", None) if message is not None else None
                raise RuntimeError(
                    "Chat Completions response contained empty message content "
                    f"(model={model_name}, finish_reason={finish_reason}, "
                    f"refusal={refusal!r}, annotations={annotations!r})."
                )
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
        text = getattr(response, "text", "") or ""
        if not text.strip():
            candidates = getattr(response, "candidates", None) or []
            finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
            prompt_feedback = getattr(response, "prompt_feedback", None)
            raise RuntimeError(
                "Gemini response contained empty text "
                f"(model={model_name}, finish_reason={finish_reason!r}, "
                f"prompt_feedback={prompt_feedback!r})."
            )
        return LLMTextResponse(
            text=text,
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
                thinking_tokens=(getattr(usage_metadata, "thoughts_token_count", 0) or 0)
                if usage_metadata is not None
                else 0,
            ),
            raw_response=response,
            requested_model_id=original_model_id,
            effective_model_id=effective_model_id,
            fallback_from_model_id=fallback_from_model_id,
        )

    def _call_once_with_deadline(
        self,
        prompt: str,
        model_id: str,
        *,
        config: Any,
        max_tokens: int,
        timeout_seconds: float,
    ) -> Any:
        """Run one provider call with a process-exit-safe deadline."""
        result_queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

        def _target() -> None:
            try:
                response = self._call_once(
                    prompt,
                    model_id,
                    config=config,
                    max_tokens=max_tokens,
                    timeout_seconds=timeout_seconds,
                )
            except BaseException as exc:  # noqa: BLE001
                try:
                    result_queue.put_nowait(("error", exc))
                except queue.Full:
                    pass
            else:
                try:
                    result_queue.put_nowait(("ok", response))
                except queue.Full:
                    pass

        # ThreadPoolExecutor workers are non-daemon. If an SDK ignores its own
        # timeout, future.result(timeout=...) returns control but the worker can
        # keep the process open after the loop writes run_end. A daemon worker
        # preserves the caller-visible timeout without pinning process exit.
        worker = threading.Thread(
            target=_target,
            name=f"ztare-llm-call-{model_id}",
            daemon=True,
        )
        worker.start()
        worker.join(timeout_seconds)
        if worker.is_alive():
            raise concurrent.futures.TimeoutError()
        try:
            kind, payload = result_queue.get_nowait()
        except queue.Empty as exc:
            raise RuntimeError("LLM provider worker exited without a result") from exc
        if kind == "error":
            raise payload
        return payload

    def _dispatch_via_codex_subscription(
        self,
        prompt: str,
        model_id: str,
        *,
        repo: "str | Path" = ".",
        timeout_seconds: int = 300,
    ) -> "LLMTextResponse":
        """Dispatch a plain text prompt through the Codex subscription runtime.

        Used as the ONLY permitted fallback when the primary OpenAI API is
        unreachable/dead. Returns an LLMTextResponse with transport metadata
        baked into model_name so telemetry can distinguish subscription runs.
        Raises RuntimeError on codex CLI failure (non-zero exit).
        """
        # Import here to avoid circular-import at module level (subscription_agent_runtime
        # already imports MODEL_MAP from this module; a top-level import here would cycle).
        from ztare.common.subscription_agent_runtime import (
            CODEX_SANDBOX_SEALED_COMPLETION,
            build_subscription_agent_command,
            _run_cli,  # noqa: PLC2701 — internal collab within the common package
        )
        from pathlib import Path as _Path

        command = build_subscription_agent_command(
            runtime="codex",
            prompt=prompt,
            repo=_Path(repo).resolve(),
            codex_model=model_id,
            codex_sandbox=CODEX_SANDBOX_SEALED_COMPLETION,
        )
        result = _run_cli(
            command,
            runtime="codex",
            repo=_Path(repo).resolve(),
            timeout_seconds=timeout_seconds,
            stdin_text=prompt if command and command[-1] == "-" else None,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Codex subscription fallback failed (rc={result.returncode}): "
                f"{(result.stderr or '')[:400]}"
            )
        text = (result.stdout or "").strip()
        # ponytail: subscription_fallback suffix in model_name is the attestation signal
        subscription_model_name = f"{model_id}[subscription_fallback]"
        return LLMTextResponse(
            text=text,
            model_name=subscription_model_name,
            usage=LLMUsage(model_name=subscription_model_name),
            raw_response=result,
            requested_model_id=model_id,
            effective_model_id=model_id,
            fallback_from_model_id=None,
        )

    def call_text(
        self,
        prompt: str,
        *,
        model_id: str,
        fallback_model_ids: tuple[str, ...] | None = None,
        config: Any = None,
        max_tokens: int = 16000,
        retries: int = PRODUCTION_CALL_RETRIES,
        timeout_seconds: int = 300,
        request_label: str = "request",
        progress_printer: Callable[[str], None] | None = None,
        transient_wait_seconds: int = 20,
        timeout_wait_seconds: int = 15,
        repo: "str | Path" = ".",
    ) -> LLMTextResponse:
        candidate_model_ids = [model_id]
        # Operator directive: cross-provider API fallback is OFF by default.
        # The subscription fallback (below) is the only permitted alternative.
        # ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK=1 restores the old cross-provider chain
        # (e.g. for callers that explicitly pass fallback_model_ids with a reason).
        _cross_provider_allowed = os.environ.get("ZTARE_ALLOW_CROSS_PROVIDER_FALLBACK") == "1"
        if os.environ.get("ZTARE_DISABLE_MODEL_FALLBACK") == "1" or not _cross_provider_allowed:
            # Hard lock: no cross-provider API fallback.
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
            # retries=0 must still make ONE attempt (this used to be range(1, 1) = zero attempts — a silent
            # no-call bug that fell straight through to "Max retries exceeded … None"). retries is "attempts".
            for attempt in range(1, max(int(retries), 1) + 1):
                last_attempted_model_id = active_model_id
                try:
                    if progress_printer is not None:
                        progress_printer(
                            f"📡 [DEBUG] Dispatching {request_label} to {active_model_id}... (Attempt {attempt})"
                        )
                    start_time = time.time()
                    response = self._call_once_with_deadline(
                        prompt,
                        active_model_id,
                        config=config,
                        max_tokens=max_tokens,
                        timeout_seconds=timeout_seconds,
                    )
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
                    _record_failed_retry(prompt, active_model_id)
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
                    if self.is_provider_unavailable_error(exc):
                        _record_failed_retry(prompt, active_model_id)
                        if progress_printer is not None:
                            progress_printer(
                                "⚠️ Provider unavailable for "
                                f"{request_label}: {error_str[:120]}"
                            )
                        break
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
                        _record_failed_retry(prompt, active_model_id)
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
                        _record_failed_retry(prompt, active_model_id)
                        if progress_printer is not None:
                            progress_printer(f"❌ Unhandled Exception: {error_str}")
                        # Operator directive: don't hard-raise here — let the subscription
                        # fallback below decide (it checks family + escape hatch). If the
                        # caller set ZTARE_DISABLE_SUBSCRIPTION_FALLBACK=1, the block below
                        # raises the original error anyway. Preserves last_error for context.
                        last_error = LLMRuntimeError(
                            error_str,
                            model_id=active_model_id,
                            transient=False,
                            status_code=status_code,
                        )
                        break

            if model_index < len(candidate_model_ids) - 1 and progress_printer is not None:
                progress_printer(
                    f"⚠️ Exhausted {active_model_id} after persistent transient failures; trying fallback provider."
                )

        # ── Subscription fallback (operator directive 2026-07-10) ────────────
        # Primary API chain exhausted. Before raising, try the Codex subscription
        # runtime — but ONLY for the SAME model family (no silent family substitution).
        # Gate: ZTARE_DISABLE_SUBSCRIPTION_FALLBACK=1 → fail loud immediately.
        if os.environ.get("ZTARE_DISABLE_SUBSCRIPTION_FALLBACK") != "1":
            model_family = get_model_family(model_id)
            if model_family not in CODEX_SERVABLE_FAMILIES:
                raise LLMRuntimeError(
                    f"API failure for {model_id} (family={model_family}): "
                    f"subscription fallback is only available for OpenAI-family models "
                    f"(codex subscription serves {sorted(CODEX_SERVABLE_FAMILIES)}). "
                    f"No family substitution permitted. Primary error: {last_error}",
                    model_id=last_attempted_model_id,
                    transient=False,
                ) from last_error
            if progress_printer is not None:
                progress_printer(
                    f"⚠️ API chain exhausted for {model_id}; escalating to "
                    f"Codex subscription fallback (same model, transport=subscription_fallback)."
                )
            try:
                sub_response = self._dispatch_via_codex_subscription(
                    prompt,
                    model_id,
                    repo=repo,
                    timeout_seconds=timeout_seconds,
                )
                if progress_printer is not None:
                    progress_printer(
                        f"✅ Codex subscription fallback succeeded: "
                        f"effective={sub_response.model_name}"
                    )
                return sub_response
            except Exception as sub_exc:  # noqa: BLE001
                raise LLMRuntimeError(
                    f"API chain exhausted and Codex subscription fallback also failed "
                    f"for {model_id}: sub_error={sub_exc!r}. "
                    f"Primary error: {last_error}",
                    model_id=last_attempted_model_id,
                    transient=False,
                ) from sub_exc

        raise LLMRuntimeError(
            f"Max retries exceeded across provider chain starting at {model_id}: {last_error}",
            model_id=last_attempted_model_id,
            transient=self.is_transient_error(last_error) if last_error is not None else False,
            status_code=self._error_status_code(last_error) if last_error is not None else None,
        ) from last_error
