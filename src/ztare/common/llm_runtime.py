from __future__ import annotations

import concurrent.futures
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

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


def _bootstrap_dotenv_if_needed() -> None:
    """Load .env from the project root when API keys are absent from os.environ.

    Required because daemon-spawned subprocess chains (daemon → claude CLI →
    make → python) propagate scrubbed env (no ANTHROPIC_API_KEY/OPENAI_API_KEY,
    so claude CLI uses subscription instead of API key). The substrate runs
    that python then triggers DO need API access. Without this bootstrap they
    would silently fail with "no key set" at SDK construction.

    No-op if all provider keys already present in env (the local developer flow where
    keys are exported in shell). Reads .env quietly; no override of present env.
    """
    if (all(os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"))
            and (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))):
        # GEMINI/GOOGLE included so the embedding engine (semantic shelf / atlases) gets its key too —
        # omitting it let the gate pass while the shelf was silently dead ("no GOOGLE_API_KEY").
        return
    try:
        from dotenv import load_dotenv  # python-dotenv (already in requirements)
    except ImportError:
        return  # graceful: if dotenv missing, fall back to whatever os.environ has
    # Walk up from CWD looking for .env (stops at filesystem root).
    cwd = Path.cwd()
    for d in [cwd] + list(cwd.parents):
        candidate = d / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)  # don't clobber explicit env
            return
    # Last resort: try the canonical project root if importable
    try:
        candidate = Path(__file__).resolve().parents[3] / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)
    except Exception:  # noqa: BLE001
        pass


_bootstrap_dotenv_if_needed()


MODEL_MAP = {
    "gemini": "gemini-2.5-flash",
    "gemini-lite": "gemini-3.1-flash-lite-preview",
    "gemini-pro": "gemini-3.1-pro-preview",
    "claude": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
    "gpt4o": "gpt-4o",
    "gpt4.1": "gpt-4.1",
    "gpt4.1-mini": "gpt-4.1-mini",
    "gpt5.5": "gpt-5.5",
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
    # OpenAI-API-compatible endpoint (base_url=api.deepseek.com/v1).
    # `deepseek` = V3 chat (fast, ~1-2s). `deepseek-reasoner` = R1 (slow,
    # ~30-90s, needs 8K+ output budget for internal reasoning tokens).
    "deepseek": "deepseek-chat",
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
}

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
    "o1": "o1",
    "o3": "o3",
    "o3-mini": "o3-mini",
    "o3-pro": "o3-pro",
    "o4-mini": "o4-mini",
}

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


def is_deepseek_model(model_id: str) -> bool:
    return model_id.startswith("deepseek")


def is_openai_model(model_id: str) -> bool:
    return model_id.startswith("gpt") or model_id.startswith("o1") or model_id.startswith("o3") or model_id.startswith("o4")


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

    Returns one of ``"openai"``, ``"anthropic"``, or ``"google"``.
    """
    if is_claude_model(model_id):
        return "anthropic"
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
    "google": "gemini-3.1-pro-preview",
}


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


def pick_model_for_tier(tier: str = "cheap", *, prefer_provider: str | None = None) -> str | None:
    """Return a model id for the requested tier (cheap | mid | pro), honoring
    `model_economy` from principal.yaml + the API key the env actually has.

    Resolution:
      1. Read model_economy.tiers[<tier>].providers from principal.yaml
      2. If `prefer_provider` is set and has API key → use that
      3. Else use principal's preferred_llm_provider (if set + key present)
      4. Else fall through providers in google/openai/anthropic order
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

    # Try in order: explicit prefer, principal's preferred, then alphabetical
    candidate_order = []
    if prefer_provider and prefer_provider in providers:
        candidate_order.append(prefer_provider)
    principal_pref = _read_principal_preferred_provider()
    if principal_pref and principal_pref in providers and principal_pref not in candidate_order:
        candidate_order.append(principal_pref)
    for p in ("google", "openai", "anthropic"):
        if p in providers and p not in candidate_order:
            candidate_order.append(p)

    env_keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GEMINI_API_KEY",
    }
    for provider in candidate_order:
        if os.environ.get(env_keys.get(provider, "")):
            return providers[provider]
    return None


def _read_principal_preferred_provider() -> str | None:
    """Walk cwd-up looking for org/preferences/principal.yaml; return its
    `preferences.preferred_llm_provider` if set. Returns one of
    'anthropic' | 'openai' | 'google' | None.

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
            if provider in ("anthropic", "openai", "google"):
                _read_principal_preferred_provider._cached = provider  # type: ignore[attr-defined]
                return provider
        except Exception:  # noqa: BLE001
            continue
    _read_principal_preferred_provider._cached = None  # type: ignore[attr-defined]
    return None


def pick_default_model_id_for_scripts(
    *,
    preference_order: tuple[str, ...] = ("anthropic", "openai", "google"),
) -> str | None:
    """Return a configured model ID based on which API keys are set.

    Resolution priority (highest wins):
      1. ``LLM_DISPATCH_PREF`` env var (comma-separated, e.g. "google,openai")
      2. ``preferences.preferred_llm_provider`` in principal.yaml
      3. ``preference_order`` argument (default: anthropic, openai, google)

    Within whichever order wins, returns the default cheap-tier model for
    the first provider whose env key is set. Returns None if none configured.
    """
    env_pref = os.environ.get("LLM_DISPATCH_PREF", "")
    if env_pref:
        # Map external names ("claude" / "gpt" / "gemini") onto canonical
        # family names used here.
        alias_map = {"claude": "anthropic", "gpt": "openai", "gemini": "google"}
        order = []
        for raw in env_pref.split(","):
            name = raw.strip().lower()
            family = alias_map.get(name, name)
            if family in _SCRIPT_DEFAULT_PER_PROVIDER:
                order.append(family)
        preference_order = tuple(order) if order else preference_order
    else:
        # Honor principal.yaml preference if no env override
        principal_pref = _read_principal_preferred_provider()
        if principal_pref:
            # Move principal's preferred provider to the front, keep others
            others = [p for p in preference_order if p != principal_pref]
            preference_order = (principal_pref,) + tuple(others)

    for family in preference_order:
        if family == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            return _SCRIPT_DEFAULT_PER_PROVIDER["anthropic"]
        if family == "openai" and os.environ.get("OPENAI_API_KEY"):
            return _SCRIPT_DEFAULT_PER_PROVIDER["openai"]
        if family == "google" and os.environ.get("GEMINI_API_KEY"):
            return _SCRIPT_DEFAULT_PER_PROVIDER["google"]
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
    return normalized


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

    def gemini_client(self):
        if self._gemini_client is None and os.environ.get("GEMINI_API_KEY"):
            if genai is None:
                raise RuntimeError(
                    "Gemini provider requested but google-genai is not "
                    "installed (optional dependency). Install google-genai "
                    "or use the anthropic/openai providers.")
            self._gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        return self._gemini_client

    def anthropic_client(self):
        if self._anthropic_client is None and os.environ.get("ANTHROPIC_API_KEY"):
            if anthropic is None:
                raise RuntimeError(
                    "Anthropic provider requested but anthropic is not "
                    "installed (optional dependency). Install anthropic "
                    "or use the google/openai providers.")
            self._anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        return self._anthropic_client

    def openai_client(self):
        if self._openai_client is None and os.environ.get("OPENAI_API_KEY"):
            if OpenAI is None:
                raise RuntimeError(
                    "OpenAI provider requested but openai is not installed "
                    "(optional dependency). Install openai or use the "
                    "anthropic/google providers.")
            self._openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        return self._openai_client

    def deepseek_client(self):
        if self._deepseek_client is None and os.environ.get("DEEPSEEK_API_KEY"):
            if OpenAI is None:
                raise RuntimeError(
                    "DeepSeek provider requested but openai is not installed "
                    "(DeepSeek uses the OpenAI-compatible SDK path)."
                )
            self._deepseek_client = OpenAI(
                api_key=os.environ.get("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com/v1",
            )
        return self._deepseek_client

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
        if is_openai_model(model_id):
            return bool(os.environ.get("OPENAI_API_KEY")) and OpenAI is not None
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

        if is_deepseek_model(model_id):
            client = self.deepseek_client()
            if client is None:
                raise RuntimeError("DEEPSEEK_API_KEY is not set.")
            kwargs = {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max(max_tokens, 8192) if model_id == "deepseek-reasoner" else max_tokens,
            }
            if isinstance(config, dict):
                for key in ("response_format", "temperature"):
                    if key in config and config[key] is not None:
                        kwargs[key] = config[key]
            return client.chat.completions.create(**kwargs)

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
            if isinstance(config, dict):
                for key in ("reasoning_effort", "verbosity", "response_format", "temperature"):
                    if key in config and config[key] is not None:
                        kwargs[key] = config[key]
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

        if is_openai_model(requested_model_id) or is_deepseek_model(requested_model_id):
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
                    "OpenAI-compatible response contained empty message content "
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
                thinking_tokens=(getattr(usage_metadata, "thoughts_token_count", 0) or 0)
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
        retries: int = PRODUCTION_CALL_RETRIES,
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
