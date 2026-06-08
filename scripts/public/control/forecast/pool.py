#!/usr/bin/env python3
"""Sealed forecast-pool primitive for ZTARE macro/meso/micro routing.

This is intentionally simpler than an execution scheduler or LMSR.  It
implements the current conservative loop:
forecast -> aggregate -> resolve -> score -> update routing weights.

Use cases:
- macro: decision pricing, file-backed now; live LMSR deferred
- meso: sealed batch branch/strategy auctions
- micro: proper-scored action forecasts, batched and auto-resolved

Forecasting agents attest read-only pricing. Execution agents remain isolated.
Resolution is objective and artifact-backed.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import os
import json
import math
import re
import statistics
import sys
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ztare.common.subscription_agent_runtime import (  # noqa: E402
    build_subscription_agent_command,
    redact_prompt_command,
    run_subscription_agent_with_recovery as run_subscription_agent_shared,
    subscription_agent_env,
)

DEFAULT_ROOT = REPO / "analytics/public/forecast_pool"
ROOT = Path(os.environ.get("FORECAST_POOL_ROOT", DEFAULT_ROOT))
CONTRACTS = ROOT / "contracts"
FORECASTS = ROOT / "forecasts"
FORECAST_UPDATES = ROOT / "forecast_updates"
AGGREGATES = ROOT / "aggregates"
OUTCOMES = ROOT / "outcomes"
SCORES = ROOT / "scores"
STATUS = ROOT / "status"
WAKE_EVENTS = ROOT / "wake_events"
WARM_STATE = ROOT / "warm_state"
CONSUMER_STATE = ROOT / "consumer_state"
MARKET_STATE = ROOT / "market_state"
MARKET_STATE_CONTRACTS = MARKET_STATE / "contracts"
REFLEXIVE_INSIGHTS = MARKET_STATE / "reflexive_insights.json"
MAINTENANCE_PLAN = MARKET_STATE / "maintenance_plan.json"
DECISION_USE_DIR = ROOT / "decision_use"
DECISION_USE_LEDGER = DECISION_USE_DIR / "decision_use_ledger.jsonl"
SCRATCH = ROOT / "scratch"
WEIGHTS = ROOT / "calibration_weights.json"
CALIBRATION_SUMMARY = ROOT / "calibration_summary.json"
DEFAULT_PREDICTION_LEDGER = REPO / "analytics/public/ledgers/prediction/prediction_ledger.jsonl"
DEFAULT_GP233_LEDGER = REPO / "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"
DEFAULT_FORECASTING_CHANNEL = REPO / "org/channels/forecasting_agent"
CANONICAL_AGENT_IDS = {"claude", "codex", "claude_rd", "codex_rd"}
AGENT_ID_BINDING_DATE = datetime(2026, 5, 15, tzinfo=timezone.utc)
AGENT_ID_ALIASES = {
    "claude": "claude",
    "claude_forecaster": "claude",
    "claudeforecaster": "claude",
    "clauderd": "claude_rd",
    "claude_rd": "claude_rd",
    "claude:rd": "claude_rd",
    "research_director_claude_opus_4_7": "claude_rd",
    "codex": "codex",
    "codex_forecaster": "codex",
    "codexforecaster": "codex",
    "codex_rd": "codex_rd",
    "codex-rd": "codex_rd",
    "codex_rd_local": "codex_rd",
    "codex-rd-main": "codex_rd",
    "codex_rd_main": "codex_rd",
    "rd_codex": "codex_rd",
}
INDEPENDENT_FORECASTER_CANONICAL_IDS = {"claude", "codex"}

LAYERS = {"macro", "meso", "micro"}
REQUIRED_CONTRACT_FIELDS = {
    "contract_id",
    "layer",
    "task_type",
    "question",
    "objective_resolver",
    "success_threshold",
    "horizon",
    "budget_agent_minutes",
    "value_if_success",
    "cost_penalty",
    "risk_penalty",
    "information_value",
    "void_conditions",
    "execution_layer_policy",
}
REQUIRED_FORECAST_FIELDS = {
    "agent_id",
    "domain",
    "forecasted_at",
    "p_success",
    "expected_cost_agent_minutes",
    "p_regression",
    "p_dependency_issue",
    "p_needs_new_lemma",
    "failure_mode_distribution",
    "rationale_short",
    "read_only_attestation",
}
REQUIRED_OUTCOME_FIELDS = {
    "success_bool",
    "actual_cost_agent_minutes",
    "compile_status",
    "sorry_delta",
    "goal_delta",
    "error_type",
    "artifact_hash",
    "artifact_path",
    "voided",
}
CONTRACT_EXTERNALITY_FIELDS = {
    "baseline_action",
    "counterfactual_action",
    "externality_hypotheses",
}
FORECAST_EXTERNALITY_FIELDS = {
    "specific_failure_mode_ids",
    "action_change_recommendation",
    "forecast_externality_tags",
}
OUTCOME_EXTERNALITY_FIELDS = {
    "realized_failure_mode_ids",
    "failure_mode_preconditioner_used",
    "preconditioner_source",
    "preconditioner_effect",
    "decision_changed_bool",
    "old_next_action",
    "new_next_action",
    "externality_tags",
    "negative_externality_tags",
    "counterfactual_value_bucket",
    "changed_by_forecast_ids",
}


def configure_root(root: Path) -> None:
    global ROOT, CONTRACTS, FORECASTS, FORECAST_UPDATES, AGGREGATES, OUTCOMES, SCORES, STATUS, WAKE_EVENTS, WARM_STATE, CONSUMER_STATE, MARKET_STATE, MARKET_STATE_CONTRACTS, REFLEXIVE_INSIGHTS, MAINTENANCE_PLAN, DECISION_USE_DIR, DECISION_USE_LEDGER, SCRATCH, WEIGHTS, CALIBRATION_SUMMARY
    ROOT = root
    CONTRACTS = ROOT / "contracts"
    FORECASTS = ROOT / "forecasts"
    FORECAST_UPDATES = ROOT / "forecast_updates"
    AGGREGATES = ROOT / "aggregates"
    OUTCOMES = ROOT / "outcomes"
    SCORES = ROOT / "scores"
    STATUS = ROOT / "status"
    WAKE_EVENTS = ROOT / "wake_events"
    WARM_STATE = ROOT / "warm_state"
    CONSUMER_STATE = ROOT / "consumer_state"
    MARKET_STATE = ROOT / "market_state"
    MARKET_STATE_CONTRACTS = MARKET_STATE / "contracts"
    REFLEXIVE_INSIGHTS = MARKET_STATE / "reflexive_insights.json"
    MAINTENANCE_PLAN = MARKET_STATE / "maintenance_plan.json"
    DECISION_USE_DIR = ROOT / "decision_use"
    DECISION_USE_LEDGER = DECISION_USE_DIR / "decision_use_ledger.jsonl"
    SCRATCH = ROOT / "scratch"
    WEIGHTS = ROOT / "calibration_weights.json"
    CALIBRATION_SUMMARY = ROOT / "calibration_summary.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SystemExit(f"{field} must be a non-empty ISO timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as e:
        raise SystemExit(f"{field} must be an ISO timestamp: {value}") from e
    if parsed.tzinfo is None:
        raise SystemExit(f"{field} must include timezone: {value}")
    return parsed.astimezone(timezone.utc)


def parse_optional_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9:_-]+", "", str(value or "").strip().lower())


def canonical_agent_id(value: Any) -> str | None:
    raw = str(value or "")
    if raw in CANONICAL_AGENT_IDS:
        return raw
    return AGENT_ID_ALIASES.get(normalize_identifier(raw))


def domain_family(value: Any) -> str:
    raw = str(value or "unknown").strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    if "ns" in normalized and ("route1" in normalized or "navier_stokes" in normalized):
        return "ns_route1_family"
    if normalized.startswith("gp225") or normalized == "gp_225":
        return "gp225_family"
    if "lean_gnn" in normalized or "gnn_lemma" in normalized:
        return "lean_gnn_family"
    return normalized or "unknown"


def normalized_entropy(distribution: dict[str, Any]) -> float | None:
    vals: list[float] = []
    for value in distribution.values():
        try:
            p = float(value)
        except (TypeError, ValueError):
            continue
        if p > 0:
            vals.append(p)
    if not vals:
        return None
    total = sum(vals)
    if total <= 0:
        return None
    probs = [value / total for value in vals]
    if len(probs) <= 1:
        return 0.0
    entropy = -sum(p * math.log(p) for p in probs)
    return round(entropy / math.log(len(probs)), 4)


def ensure_dirs() -> None:
    for path in (
        CONTRACTS,
        FORECASTS,
        FORECAST_UPDATES,
        AGGREGATES,
        OUTCOMES,
        SCORES,
        STATUS,
        WAKE_EVENTS,
        WARM_STATE,
        CONSUMER_STATE,
        MARKET_STATE,
        MARKET_STATE_CONTRACTS,
        DECISION_USE_DIR,
        SCRATCH,
    ):
        path.mkdir(parents=True, exist_ok=True)


def slug(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in out:
        out = out.replace("__", "_")
    return out[:120]


def clamp_p(p: float) -> float:
    return min(0.98, max(0.02, p))


def logit(p: float) -> float:
    p = clamp_p(p)
    return math.log(p / (1.0 - p))


# --- F8/F10 second-moment-channel scoring helpers ----------------------------
# Added 2026-05-24 per `projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace/research_log.md`
# F8 (pilot v4 N=100): premium-vs-Brier ρ=+0.36 pooled; coverage-of-binary structurally degenerate
# F10 (pool n=590): decomposed channels (p_dep, p_lem, p_reg) predict Brier same direction
# Surface optional second-moment fields per score row; calibration_payload computes
# Spearman against Brier per (agent, domain) when ≥4 rows in cell carry the field.

OPTIONAL_SECOND_MOMENT_FORECAST_FIELDS = (
    "tail_insurance_premium",     # F8 channel (v3-v4 pilot); LEGACY — F35 demoted; per-agent sign per F36
    "tail_loss_magnitude",        # F8 sibling
    "tail_downside_worry",        # F35 signed-tail channel (v21 pilot; superior to magnitude alone)
    "tail_upside_surprise",       # F35 signed-tail channel sibling
    "verbalized_confidence",      # Tian-2023 channel (v10/v10.1 mechanism probe)
    "p_dependency_issue",         # F10 (decomposed failure-mode)
    "p_needs_new_lemma",          # F10
    "p_regression",               # F10
    "predicted_self_error_ratio", # F13 family (meta-cal)
    # --- v28 channel primitives (per_agent_prompt_policy.yaml channel_routing) ---
    "p_buy_yes_max",              # F56 bid-ask spread: highest p at which agent would buy YES
    "p_sell_yes_min",             # F56 bid-ask spread: lowest p at which agent would sell YES
    "predicted_brier_lo",         # F61 self-predicted Brier interval lower bound (b_lo)
    "predicted_brier_hi",         # F61 self-predicted Brier interval upper bound (b_hi)
)

# F36: premium-correctness coupling is agent-specific. Map agent_id → agent_family
# so downstream consumers can apply per-family sign rules without reverse-engineering
# identity from contract paths. The actual sign rule lives in
# org/calibration/per_agent_premium_sign.yaml so it can be updated without touching
# emitter code.
AGENT_FAMILY_BY_ID = {
    "claude": "claude",
    "claude_rd": "claude",
    "codex": "codex",
    "codex_rd": "codex",
    "gemini": "gemini",
    "gemini_rd": "gemini",
    "deepseek": "deepseek",
    "deepseek_rd": "deepseek",
}


# F39 / F37 deployable prompt fragments (2026-05-25). The forecast pool
# accepts the new signed-tail fields and `agent_family`; downstream emitters
# (RD self-bet, agent runners) should use these prompt fragments to populate
# them. Centralized here so the language stays consistent across emitters
# and so a future revision (v23 cross-corpus replication may sharpen the
# wording) updates ONE place.
RECOMMENDED_ELICITATION_PROMPT_FRAGMENTS = {
    "f37_signed_tail": (
        "After committing your point estimate, also emit two signed directional "
        "scalars (1-100):\n"
        "  tail_downside_worry  — suspicion the actual outcome will be MUCH "
        "WORSE than your estimate\n"
        "  tail_upside_surprise — suspicion the actual outcome will be MUCH "
        "BETTER than your estimate\n"
        "Treat each as an INDEPENDENT cognitive query — they need NOT sum to "
        "any fixed total. Both can be HIGH simultaneously (low confidence "
        "either way) or both LOW (confident point estimate). Do NOT compute "
        "one from the other."
    ),
    "f39_balance_instruction": (
        "Before committing your point estimate: if you have mentally listed "
        "failure paths (or success paths), ALSO mentally list 1-2 paths in "
        "the OPPOSITE direction. Imagining one side primes you to overweight "
        "it (availability bias). Force a balance check across both directions "
        "before fixing your estimate. This is especially important for "
        "tone-tuned models (claude family) per F36/F39; harmless for codex "
        "family per v22c at N=15/cell."
    ),
    "f56_bid_ask_spread": (
        "Quote two probabilities as a two-sided market on this contract:\n"
        "  p_buy_yes_max  — the highest probability at which you would still "
        "BUY YES (you think YES is undervalued at any p <= this)\n"
        "  p_sell_yes_min — the lowest probability at which you would still "
        "SELL YES (you think YES is overvalued at any p >= this)\n"
        "Constraints: 0 <= p_buy_yes_max <= p_success <= p_sell_yes_min <= 1. "
        "Wider spread = lower confidence. Do NOT collapse the spread to zero "
        "unless you would genuinely take either side at p_success."
    ),
    "f61_brier_interval": (
        "After committing p_success, predict the range your Brier score on "
        "this single contract will fall in:\n"
        "  predicted_brier_lo — best-case Brier (you nail it)\n"
        "  predicted_brier_hi — worst-case Brier (you are surprised)\n"
        "Brier on a binary is (p_predicted - outcome)^2; range is [0, 1]. "
        "predicted_brier_lo <= predicted_brier_hi is required. Treat this as "
        "an honest interval, not a confidence-signaling exercise — narrow "
        "intervals on contracts you actually understand, wide on those you do not."
    ),
}


def recommended_elicitation_block(*, signed_tail: bool = True, balance_instruction: bool = True) -> str:
    """Compose the recommended-elicitation prompt block for downstream emitters.

    Default ON for both per the F36→F37→F38→F39 chain. Emitters should append
    this block to their forecast-elicitation prompts so new contracts populate
    the signed-tail fields and benefit from the agent-class-asymmetric
    calibration lift documented in research_log.md.
    """
    parts = []
    if balance_instruction:
        parts.append(RECOMMENDED_ELICITATION_PROMPT_FRAGMENTS["f39_balance_instruction"])
    if signed_tail:
        parts.append(RECOMMENDED_ELICITATION_PROMPT_FRAGMENTS["f37_signed_tail"])
    return "\n\n".join(parts)


def recommended_elicitation_for_agent(agent_id: str) -> dict:
    """One-call lookup: given agent_id, return the recommended elicitation config.

    Per F41 (v22d factorial verdict):
      - claude family: balance_instruction = ON (F39 helps), signed_tail = ON (F37 neutral here but maintains response-format decomposition)
      - codex family:  balance_instruction = ON (neutral, no harm), signed_tail = ON (small effects either way)
      - unknown:       same as codex (safer default — no harm)

    Returns dict with:
      - prompt_block: the F37/F39 prompt text to append
      - signed_tail_required: True if downstream emission should be rejected without signed-tail
      - balance_instruction_required: True if prompt MUST include balance instruction
      - agent_family: derived family
      - rationale: 1-line citation of which F-row drives the recommendation
    """
    family = derive_agent_family(agent_id)
    # Per F39/F41: claude benefits from balance; signed-split helps cancel F36 tone confound.
    if family == "claude":
        rationale = ("F39 + F41 v22d: balance instruction lifts claude Brier −0.012 to −0.060; "
                     "signed-split (F37) cancels F36 tone confound. Both default ON for claude.")
        prompt = recommended_elicitation_block(signed_tail=True, balance_instruction=True)
        return {
            "agent_family": "claude", "prompt_block": prompt,
            "signed_tail_required": True, "balance_instruction_required": True,
            "rationale": rationale,
        }
    elif family == "codex":
        rationale = ("F41 v22d: balance instruction neutral (slight +0.010); signed-split neutral. "
                     "Both default ON because they're harmless and help if F36 mechanism applies cross-corpus.")
        prompt = recommended_elicitation_block(signed_tail=True, balance_instruction=True)
        return {
            "agent_family": "codex", "prompt_block": prompt,
            "signed_tail_required": False, "balance_instruction_required": False,
            "rationale": rationale,
        }
    else:
        # Unknown family — apply codex-style defaults (no harm; v23 cross-corpus can refine)
        return {
            "agent_family": None, "prompt_block": recommended_elicitation_block(),
            "signed_tail_required": False, "balance_instruction_required": False,
            "rationale": "Unknown agent family; applying codex-style defaults pending v23 cross-corpus calibration.",
        }


_COST_CALIBRATION_CACHE: dict[str, dict] = {}


def load_per_agent_cost_calibration(config_path: Path | None = None) -> dict:
    """F26 per-agent cost/effort divisor table. Mirrors load_per_agent_premium_sign."""
    if config_path is None:
        config_path = REPO / "org" / "calibration" / "per_agent_cost_calibration.yaml"
    key = str(config_path.resolve())
    cached = _COST_CALIBRATION_CACHE.get(key)
    if cached is not None:
        return cached
    if not config_path.exists():
        _COST_CALIBRATION_CACHE[key] = {"families": {}, "available": False}
        return _COST_CALIBRATION_CACHE[key]
    families: dict[str, dict] = {}
    current_family: str | None = None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("families:"):
            current_family = None
            continue
        # Family name may have alphanumerics (e.g. codex_55)
        m = re.match(r"^  ([a-z][a-z0-9_]*):\s*$", line)
        if m and not raw.startswith("    "):
            current_family = m.group(1)
            families[current_family] = {}
            continue
        if current_family and line.startswith("    "):
            kv = re.match(r"^    ([a-z][a-z0-9_]*):\s*([^\n]+?)\s*$", line)
            if kv:
                k = kv.group(1)
                v = kv.group(2).strip().strip('"')
                # Strip inline YAML comments
                if "#" in v:
                    v = v.split("#", 1)[0].strip()
                if v == "null" or v == "":
                    families[current_family][k] = None
                else:
                    try:
                        families[current_family][k] = float(v)
                    except ValueError:
                        families[current_family][k] = v
    _COST_CALIBRATION_CACHE[key] = {"families": families, "available": True}
    return _COST_CALIBRATION_CACHE[key]


def derive_agent_subfamily(agent_id: str) -> str | None:
    """Resolve agent_id to a fine-grained sub-family (claude / codex_55 / codex_mini).

    F26 cost calibration is sub-family-specific (codex_5large vs codex_5mini have
    different divisors). Broad family (codex) isn't granular enough. This helper
    does substring matching for codex_55 / codex_mini variants then falls back
    to derive_agent_family for the claude/codex broad classification.
    """
    raw = normalize_identifier(agent_id)
    if "claude" in raw:
        return "claude"
    if "codex" in raw:
        if "mini" in raw or "54mini" in raw or "5mini" in raw or "5_4_mini" in raw:
            return "codex_mini"
        if "55" in raw or "5_5" in raw or "5large" in raw:
            return "codex_55"
        return "codex"
    return derive_agent_family(agent_id)


def apply_per_agent_cost_calibration(
    raw_value: float,
    agent_id: str,
    *,
    metric: str = "effort",
    config_path: Path | None = None,
) -> tuple[float, dict]:
    """Apply F26 per-agent cost/effort divisor.

    metric ∈ {"effort", "cost"}. Returns (calibrated_value, metadata).
    Falls through (calibrated = raw) for unknown agent or missing divisor.
    Uses sub-family resolution because F26 evidence is sub-family-specific
    (codex_5large 4.12× cost; claude 4.36× effort).
    """
    subfamily = derive_agent_subfamily(agent_id)
    family = derive_agent_family(agent_id)
    config = load_per_agent_cost_calibration(config_path)
    # Try sub-family first, fall back to broad family
    rule = config.get("families", {}).get(subfamily, {}) if subfamily else {}
    if not rule and family != subfamily:
        rule = config.get("families", {}).get(family, {}) if family else {}
    key = f"{metric}_divisor"
    divisor = rule.get(key)
    if divisor is None or not isinstance(divisor, (int, float)) or divisor <= 0:
        return float(raw_value), {
            "agent_id": agent_id, "agent_family": family, "agent_subfamily": subfamily,
            "metric": metric, "divisor": None, "applied": False,
            "raw_value": float(raw_value), "calibrated_value": float(raw_value),
        }
    calibrated = float(raw_value) / float(divisor)
    return calibrated, {
        "agent_id": agent_id, "agent_family": family, "agent_subfamily": subfamily,
        "metric": metric, "divisor": float(divisor),
        "n": rule.get(f"{metric}_divisor_n"),
        "applied": True, "raw_value": float(raw_value), "calibrated_value": calibrated,
    }


def premium_as_abstention_signal(
    premium: float,
    agent_id: str,
    *,
    abstention_threshold: int = 50,
) -> dict:
    """F28: premium-as-ABSTENTION (utility lift on v10 C2 n=90, all 3 agents positive).

    F28 finding: when premium ≥ threshold, ABSTAIN rather than emit the
    point-estimate-based decision. Returns a dict with `abstain: bool` and
    F36-calibrated premium so the caller can apply the threshold uniformly.

    Default threshold is 50 (matches v10 C2 symmetric regime abst@50 +22 lift).
    Consumer code:
      sig = premium_as_abstention_signal(premium, agent_id)
      if sig['abstain']:
          # do not emit decision; route to operator or pause
      else:
          # use premium / point estimate as planned
    """
    calibrated_premium, sign_meta = apply_per_agent_premium_sign(premium, agent_id)
    abstain = calibrated_premium >= float(abstention_threshold)
    return {
        "abstain": abstain,
        "abstention_threshold": abstention_threshold,
        "raw_premium": float(premium),
        "calibrated_premium": calibrated_premium,
        "sign_metadata": sign_meta,
        "rationale": (
            "F28: premium-as-abstention (n=90, v10 C2, +22 utility lift symmetric "
            "regime, +3.89 asym_favor_no, all 3 agents positive). Calibrated "
            "premium ≥ threshold → abstain."
        ),
    }


class BestPracticeViolation(Exception):
    """Raised when a forecast emission violates a required best-practice rule.

    Per F37/F39/F41: claude-family emissions REQUIRE signed-tail fields
    (tail_downside_worry + tail_upside_surprise). Other families currently
    only warn. Emitters catch this exception and exit non-zero so RDs are
    forced to populate the right fields rather than guessing.
    """


def check_emission_best_practice(payload: dict, *, allow_bypass: bool = False) -> list[str]:
    """Check emission against F37+F39 best-practice rules.

    Returns warnings (non-blocking). RAISES BestPracticeViolation when a
    required rule is violated (currently only for claude-family without
    signed-tail per F41 evidence). Pass allow_bypass=True (via the emitter's
    --allow-missing-best-practice flag) to downgrade required→warn for
    operator-side override.
    """
    warnings: list[str] = []
    agent_id = payload.get("agent_id") or payload.get("owner") or ""
    if not agent_id:
        return warnings
    rec = recommended_elicitation_for_agent(agent_id)
    family = rec["agent_family"]
    has_signed = (payload.get("tail_downside_worry") is not None
                  and payload.get("tail_upside_surprise") is not None)
    if rec["signed_tail_required"] and not has_signed:
        msg = (
            f"REJECTED: agent_family={family} emission missing required signed-tail fields. "
            f"{rec['rationale']} "
            f"Pass --tail-downside-worry AND --tail-upside-surprise (1-100 ints) "
            f"or pass --allow-missing-best-practice to bypass."
        )
        if allow_bypass:
            warnings.append(f"[BYPASSED required-rule] {msg}")
        else:
            raise BestPracticeViolation(msg)
    elif family == "codex" and not has_signed:
        warnings.append(
            f"[F37 best-practice] codex emission lacks signed-tail. Not required for codex per F41, "
            f"but recommended for cross-pilot data parity."
        )
    return warnings


# Legacy alias preserved for any older callers; just delegates to the new check
# but suppresses the exception (returns warnings only).
def warn_if_emission_misses_best_practice(payload: dict, *, severity: str = "warn") -> list[str]:
    try:
        return check_emission_best_practice(payload, allow_bypass=True)
    except BestPracticeViolation as e:
        return [str(e)]


_PREMIUM_SIGN_CACHE: dict[str, dict] = {}


def load_per_agent_premium_sign(config_path: Path | None = None) -> dict:
    """Load per-agent premium sign rules from org/calibration/per_agent_premium_sign.yaml.

    Per F36: claude-family premium is inverted (pays more when right), codex-family
    is direction-correct (pays more when wrong). Consumers of premium signals MUST
    apply the per-family rule; uniform treatment is wrong for one family by design.

    Cached at module level — config is small, rarely changes, and re-reading on every
    forecast emission is unnecessary overhead.
    """
    if config_path is None:
        config_path = REPO / "org" / "calibration" / "per_agent_premium_sign.yaml"
    key = str(config_path.resolve())
    cached = _PREMIUM_SIGN_CACHE.get(key)
    if cached is not None:
        return cached
    if not config_path.exists():
        _PREMIUM_SIGN_CACHE[key] = {"families": {}, "available": False}
        return _PREMIUM_SIGN_CACHE[key]
    # Minimal YAML parser. Family names may include digits (codex_55). Inline
    # `# comments` stripped before value parse. Avoids adding a yaml dep.
    families: dict[str, dict] = {}
    current_family: str | None = None
    for raw in config_path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("families:"):
            current_family = None
            continue
        m = re.match(r"^  ([a-z][a-z0-9_]*):\s*$", line)
        if m and not raw.startswith("    "):
            current_family = m.group(1)
            families[current_family] = {}
            continue
        if current_family and line.startswith("    "):
            kv = re.match(r"^    ([a-z][a-z0-9_]*):\s*\"?([^\"]+)\"?\s*$", line)
            if kv:
                k = kv.group(1)
                v = kv.group(2).strip().strip('"')
                if "#" in v:
                    v = v.split("#", 1)[0].strip()
                if v.lstrip("-+").isdigit():
                    v = int(v)
                families[current_family][k] = v
    _PREMIUM_SIGN_CACHE[key] = {"families": families, "available": True}
    return _PREMIUM_SIGN_CACHE[key]


def apply_per_agent_premium_sign(
    premium: float,
    agent_id: str,
    *,
    config_path: Path | None = None,
) -> tuple[float, dict]:
    """Apply the F36 per-agent sign rule to a raw premium signal.

    Returns ``(calibrated_premium, metadata)``. The calibrated value is the
    direction-correct interpretation: high → "I'm likely wrong, hedge". The
    metadata dict carries the family, sign rule, and an `applied: bool` flag
    so callers can see whether a correction happened.

    Behaviour:
      - claude family / sign="inverted":   calibrated = -premium (or 100 − premium
                                           if magnitude is on a [1,100] scale)
      - codex family / sign="direction_correct": calibrated = premium (no change)
      - unknown family or no rule:         calibrated = premium, metadata.applied=False

    The convention assumed for premium is a [1,100] integer scale (the v22 / F37
    elicitation surface). Caller responsibility to scale-normalize if a different
    convention is in use.
    """
    family = derive_agent_family(agent_id)
    config = load_per_agent_premium_sign(config_path)
    families = config.get("families", {})
    rule = families.get(family, {}) if family else {}
    sign = rule.get("premium_sign")
    if sign == "inverted":
        # Premium is on [1, 100] integer scale per v22 / F37 elicitation; flip
        # around 100 so high becomes "less hedge" not "more hedge"
        # (post-inversion semantics matches the codex direction-correct case).
        calibrated = 100.0 - float(premium)
        applied = True
    elif sign == "direction_correct":
        calibrated = float(premium)
        applied = True
    else:
        calibrated = float(premium)
        applied = False
    return calibrated, {
        "agent_id": agent_id,
        "agent_family": family,
        "premium_sign_rule": sign,
        "applied": applied,
        "raw_premium": float(premium),
        "calibrated_premium": calibrated,
    }


def horizon_confidence_weight(horizon: str | None, reference_iso_date: str = "2026-01-01") -> float:
    """F77 horizon-confidence weight.

    Pooled across 5 families on v28a public_domain N=210, longer-horizon contracts
    have higher err² (ρ=+0.16 [+0.03, +0.29], h1_supported pooled). Mean Brier on
    April-2026-resolving contracts is 0.240; on May-2026 it is 0.385. The
    deployable interpretation is that downstream consumers should weight
    confidence in an LLM forecast DOWN as the resolution horizon grows.

    Returns a weight in (0, 1]: 1.0 for contracts resolving on (or before)
    reference_iso_date, decaying linearly to 0.5 at 180 days out, floored at 0.1.

    horizon strings observed in our corpus include "resolved-2026-04-19",
    "resolved-by-2026-04-30", or anything containing a YYYY-MM-DD substring.

    Returns 1.0 (no penalty) if the horizon cannot be parsed — consumers that
    care about audit can check whether the input was parseable before applying
    the weight downstream.
    """
    if not horizon:
        return 1.0
    import re as _re
    from datetime import datetime as _dt
    m = _re.search(r"(\d{4}-\d{2}-\d{2})", horizon)
    if not m:
        return 1.0
    try:
        resolution = _dt.fromisoformat(m.group(1))
        reference = _dt.fromisoformat(reference_iso_date)
    except ValueError:
        return 1.0
    days = (resolution - reference).days
    if days <= 0:
        return 1.0
    # Linear decay 1.0 → 0.5 over 180 days, floor at 0.1.
    w = 1.0 - 0.5 * (days / 180.0)
    return max(0.1, min(1.0, w))


def confident_no_discount(p_success: float) -> float:
    """F100 post-forecast correction for confident-NO overconfidence.

    On the public-domain N=142 cohort, every family improved under this
    adjustment when raw p_success was below 0.10. Keep this as an explicit
    calibrated view rather than silently overwriting the raw forecast. A
    2026-06-03 source-currency audit narrowed its use to live/source-valid
    rows: it improved post-cutoff rows but regressed retrospective pre-cutoff
    benchmark rows. A 2026-06-04 FRED vintage audit plus bulk repair further
    narrowed "post-cutoff" dataset use: rows scored from current revised
    labels are not source-valid calibration evidence unless label-time/vintage
    receipts pass.
    """
    p = clamp_p(float(p_success))
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def confident_no_policy_eligibility(contract: dict[str, Any]) -> dict[str, Any]:
    """Machine-readable scope gate for consuming the F100 adjusted view.

    Forecast-pool contracts are normally forward-looking decisions, so F100 is
    policy-eligible by default. Retrospective benchmark or dataset-source
    contracts can opt out by storing explicit source/label-time metadata on the
    contract. This keeps the adjusted probability visible for audit while giving
    downstream decision code a concrete eligibility bit to consume.
    """
    source_state = str(
        contract.get("source_currency_state")
        or contract.get("source_currency")
        or contract.get("cutoff_relation")
        or ""
    ).lower()
    label_state = str(
        contract.get("label_time_status")
        or contract.get("law_policy_scoreable_reason")
        or contract.get("dataset_label_time_status")
        or ""
    ).lower()
    explicit_scoreable = contract.get("law_policy_scoreable")
    if explicit_scoreable is False:
        return {
            "eligible": False,
            "reason": "contract_law_policy_scoreable_false",
        }
    if "pre_cutoff" in source_state or "pre-cutoff" in source_state:
        return {
            "eligible": False,
            "reason": "retrospective_pre_cutoff_source_visible",
        }
    if "current_label" in label_state or "without_label_time_receipt" in label_state:
        return {
            "eligible": False,
            "reason": label_state or "dataset_current_label_without_receipt",
        }
    if "changed" in label_state and "stable" not in label_state:
        return {
            "eligible": False,
            "reason": label_state,
        }
    return {
        "eligible": True,
        "reason": "forward_looking_or_source_valid_contract",
    }


def derive_agent_family(agent_id: str) -> str | None:
    """Return the agent family for an agent_id, or None if it cannot be classified.

    Family is the consumer-facing dispatch tag for F36's per-agent sign rules
    on second-moment channels. The legacy `tail_insurance_premium` is direction-
    correct (pays more when wrong) for the codex family and inverted (pays more
    when right) for the claude family at v21 N=270. New emissions should also
    populate the signed-tail pair (`tail_downside_worry`, `tail_upside_surprise`),
    which per F35 is the cleaner channel.

    Resolution order:
      1. canonical_agent_id() — exact production-pool ids (claude / codex / *_rd)
      2. substring fallback — research-pilot ids like `claude_v22`, `codex_55_v21`
         resolve to their family by lexical match. This is intentionally permissive
         so analyzers on scratch/prediction_ledger data work without requiring an
         explicit --agent-family flag on every research call.
    """
    canonical = canonical_agent_id(agent_id)
    if canonical is not None:
        family = AGENT_FAMILY_BY_ID.get(canonical)
        if family is not None:
            return family
    raw = normalize_identifier(agent_id)
    # Substring fallback handles all naming variants observed in the apparatus:
    #   raw underscore variants: claude_rd, codex_55_v22d, gemini_v24, ...
    #   colon-namespaced variants: claude:rd, codex:rd, claude:90, claude:claude_forecaster
    #   versioned variants: claude_opus_4_7, claude_handover_gp225_*, codex_5large
    # normalize_identifier() already lowercases + strips noise, so a single
    # substring check covers raw / colon-namespaced / versioned forms uniformly.
    if "claude" in raw:
        return "claude"
    if "codex" in raw:
        return "codex"
    if "gemini" in raw:
        return "gemini"
    if "deepseek" in raw:
        return "deepseek"
    return None


def _spearman_rho(xs: list[float], ys: list[float]) -> float | None:
    """Spearman rank correlation. Returns None if N<4 or degenerate."""
    n = len(xs)
    if n < 4 or n != len(ys):
        return None
    def _rank(vs: list[float]) -> list[float]:
        sorted_pairs = sorted(enumerate(vs), key=lambda p: p[1])
        ranks = [0.0] * len(vs)
        i = 0
        while i < len(sorted_pairs):
            j = i
            while j + 1 < len(sorted_pairs) and sorted_pairs[j + 1][1] == sorted_pairs[i][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[sorted_pairs[k][0]] = avg_rank
            i = j + 1
        return ranks
    rx = _rank(xs)
    ry = _rank(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((r - mx) ** 2 for r in rx) ** 0.5) * (sum((r - my) ** 2 for r in ry) ** 0.5)
    if den == 0:
        return None
    return round(num / den, 4)


def _second_moment_correlations(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """For each optional second-moment field, compute Spearman(field, brier) on the (agent,domain) items.
    Returns dict keyed by field name with {n, rho, present_in_rows}. Only includes fields present in ≥4 rows."""
    out: dict[str, dict[str, Any]] = {}
    for field in OPTIONAL_SECOND_MOMENT_FORECAST_FIELDS:
        paired: list[tuple[float, float]] = []
        for item in items:
            v = item.get(field)
            b = item.get("brier")
            if v is None or b is None:
                continue
            try:
                paired.append((float(v), float(b)))
            except (TypeError, ValueError):
                continue
        if len(paired) < 4:
            continue
        rho = _spearman_rho([p[0] for p in paired], [p[1] for p in paired])
        out[field] = {"n": len(paired), "spearman_vs_brier": rho}
    return out


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"malformed JSON in {path}: {e}") from e


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise SystemExit(f"malformed JSONL in {path}:{lineno}: {e}") from e
        if not isinstance(row, dict):
            raise SystemExit(f"JSONL row must be an object: {path}:{lineno}")
        rows.append(row)
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def append_market_event(kind: str, **fields: Any) -> None:
    """Enforced technical (operational) log for the prediction market.

    Append-only timestamped JSONL trail. Added 2026-05-16 after a stale
    malformed contract silently blocked the independent-agent warm market
    for 2 days with NO technical trace (only a static post_tick_check
    advisory). Wired into the daemon hot paths so silent multi-run
    failures and resilience-skips leave a durable, greppable timeline.
    Best-effort: logging must never break the market it observes.
    """
    try:
        path = ROOT / "market_events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": now_iso(), "kind": kind, **fields}
        with path.open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    except Exception:
        pass


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_payload_hash(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def require_fields(payload: dict[str, Any], required: set[str], label: str) -> None:
    missing = sorted(field for field in required if field not in payload)
    if missing:
        raise SystemExit(f"{label} missing required fields: {', '.join(missing)}")


def require_non_negative(value: float | int | None, field: str) -> None:
    if value is None:
        return
    if float(value) < 0:
        raise SystemExit(f"{field} must be non-negative")


def require_probability(value: float | int | None, field: str) -> None:
    if value is None:
        raise SystemExit(f"{field} is required")
    p = float(value)
    if p < 0.0 or p > 1.0:
        raise SystemExit(f"{field} must be in [0, 1]")


def require_optional_probability(value: float | int | None, field: str) -> None:
    if value is None:
        return
    require_probability(value, field)


def contract_path(contract_id: str) -> Path:
    return CONTRACTS / f"{contract_id}.json"


def forecast_dir(contract_id: str) -> Path:
    return FORECASTS / contract_id


def forecast_path(contract_id: str, agent_id: str) -> Path:
    return forecast_dir(contract_id) / f"{slug(agent_id)}.json"


def forecast_update_dir(contract_id: str, agent_id: str) -> Path:
    return FORECAST_UPDATES / contract_id / slug(agent_id)


def forecast_update_path(contract_id: str, agent_id: str, forecasted_at: str) -> Path:
    stamp = forecasted_at.replace(":", "").replace("-", "").lower()
    root = forecast_update_dir(contract_id, agent_id)
    base = root / f"{stamp}_{slug(agent_id)}.json"
    if not base.exists():
        return base
    for idx in range(2, 1000):
        candidate = root / f"{stamp}_{slug(agent_id)}_{idx}.json"
        if not candidate.exists():
            return candidate
    raise SystemExit(f"too many same-second forecast updates for {contract_id}/{agent_id}")


def independent_forecaster_rows(contract_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    root = forecast_dir(contract_id)
    paths = sorted(root.glob("*.json")) if root.exists() else []
    for path in paths:
        forecast = read_json(path, {})
        if not isinstance(forecast, dict):
            continue
        agent_id = str(forecast.get("agent_id") or path.stem)
        canonical = canonical_agent_id(agent_id)
        if canonical not in INDEPENDENT_FORECASTER_CANONICAL_IDS:
            continue
        rows.append({
            "agent_id": agent_id,
            "canonical_agent_id": canonical,
            "forecasted_at": forecast.get("forecasted_at"),
            "path": relpath(path),
        })
    return rows


def aggregate_path(contract_id: str) -> Path:
    return AGGREGATES / f"{contract_id}.json"


def outcome_path(contract_id: str) -> Path:
    return OUTCOMES / f"{contract_id}.json"


def score_path(contract_id: str) -> Path:
    return SCORES / f"{contract_id}.json"


def scratch_path(created_at: str, owner: str, question: str,
                 explicit_slug: str | None = None) -> Path:
    stamp = created_at.replace(":", "").replace("-", "").replace("+", "z")
    stamp = stamp.replace(".", "").lower().rstrip("z")
    label = slug(explicit_slug or question or "scratch_forecast")
    owner_slug = slug(owner or "unknown")
    return SCRATCH / f"{stamp}_{owner_slug}_{label}.json"


def scratch_defaults_to_prediction_mirror(owner: str) -> bool:
    """Scratch self-bets by RD-like actors should enter PATTERN-012 by
    default; sealed forecaster-role rows must stay in GP-230 forecast
    artifacts unless explicitly mirrored."""
    canonical = canonical_agent_id(owner)
    if canonical in {"claude", "codex"}:
        return False
    if canonical in {"claude_rd", "codex_rd"}:
        return True
    norm = normalize_identifier(owner)
    if "forecaster" in norm or norm in {"claude", "codex"}:
        return False
    return "rd" in norm or "scratch" in norm or "principal" in norm


def prediction_id_exists(path: Path, prediction_id: str) -> bool:
    return any(row.get("prediction_id") == prediction_id
               for row in read_jsonl(path))


def repo_path_from_user_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO / path


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")


def _same_artifact_path(left: str | Path | None, right: Path) -> bool:
    if left in (None, ""):
        return False
    left_path = repo_path_from_user_path(left)
    try:
        return left_path.resolve() == right.resolve()
    except OSError:
        return left_path == right


def find_prediction_row_for_scratch(
    rows: list[dict[str, Any]],
    *,
    prediction_id: str | None = None,
    scratch_path_value: Path | None = None,
) -> dict[str, Any] | None:
    if prediction_id:
        for row in rows:
            if row.get("prediction_id") == prediction_id:
                return row
    if scratch_path_value is not None:
        for row in rows:
            if _same_artifact_path(row.get("prediction_artifact_path"), scratch_path_value):
                return row
    return None


def status_path() -> Path:
    return STATUS / "daemon_once_latest.json"


def warm_state_path() -> Path:
    return WARM_STATE / "latest.json"


def wake_event_dir(contract_id: str) -> Path:
    return WAKE_EVENTS / contract_id


def load_contract(contract_id: str) -> dict[str, Any]:
    path = contract_path(contract_id)
    if not path.exists():
        raise SystemExit(f"missing contract: {path}")
    contract = read_json(path)
    if not isinstance(contract, dict):
        raise SystemExit(f"contract must be a JSON object: {path}")
    require_fields(contract, REQUIRED_CONTRACT_FIELDS, f"contract {contract_id}")
    return contract


def load_scratch_contract(scratch_id: str) -> tuple[dict[str, Any], Path]:
    for row in read_jsonl(SCRATCH / "scratch_ledger.jsonl"):
        if str(row.get("scratch_id") or "") != scratch_id:
            continue
        path = REPO / str(row.get("path") or "")
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            raise SystemExit(f"scratch forecast must be a JSON object: {path}")
        return payload, path
    raise SystemExit(f"missing scratch forecast: {scratch_id}")


def load_decision_contract(contract_id: str) -> tuple[dict[str, Any], Path, bool]:
    path = contract_path(contract_id)
    if path.exists():
        return load_contract(contract_id), path, False
    if contract_id.startswith("scratch_"):
        payload, scratch = load_scratch_contract(contract_id)
        return payload, scratch, True
    raise SystemExit(f"missing contract: {path}")


def load_forecasts(contract_id: str) -> list[dict[str, Any]]:
    root = forecast_dir(contract_id)
    forecasts = []
    paths = sorted(root.glob("*.json")) if root.exists() else []
    updates_root = FORECAST_UPDATES / contract_id
    if updates_root.exists():
        paths.extend(sorted(updates_root.glob("*/*.json")))
    for path in paths:
        forecast = read_json(path)
        if not isinstance(forecast, dict):
            raise SystemExit(f"forecast must be a JSON object: {path}")
        require_fields(forecast, REQUIRED_FORECAST_FIELDS, f"forecast {path}")
        forecast.setdefault("forecast_artifact_path", relpath(path))
        forecasts.append(forecast)
    return forecasts


def latest_forecasts_by_agent(forecasts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for fc in forecasts:
        agent_id = str(fc["agent_id"])
        prior = latest.get(agent_id)
        if prior is None or str(fc["forecasted_at"]) >= str(prior["forecasted_at"]):
            latest[agent_id] = fc
    return [latest[key] for key in sorted(latest)]


def load_weights() -> dict[str, Any]:
    if not WEIGHTS.exists():
        return {"default_weight": 1.0, "agents": {}, "domains": {}}
    return read_json(WEIGHTS)


def domain_weight(weights: dict[str, Any], agent_id: str, domain: str) -> float:
    agents = weights.get("agents") or {}
    entry = agents.get(agent_id) or {}
    domains = entry.get("domains") or {}
    return float(domains.get(domain, entry.get("default_weight", weights.get("default_weight", 1.0))))


def domain_effort_prior(weights: dict[str, Any], domain: str) -> float | None:
    domains = weights.get("domains") or {}
    entry = domains.get(domain) or {}
    prior = entry.get("expected_cost_agent_minutes_prior")
    return None if prior is None else float(prior)


def domain_tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.lower()) if token}


def token_jaccard(a: str, b: str) -> float:
    left = domain_tokens(a)
    right = domain_tokens(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def char_ngrams(value: str, n: int = 3) -> set[str]:
    normalized = slug(value).replace("_", "")
    if not normalized:
        return set()
    if len(normalized) <= n:
        return {normalized}
    return {normalized[i:i + n] for i in range(len(normalized) - n + 1)}


def char_ngram_jaccard(a: str, b: str) -> float:
    left = char_ngrams(a)
    right = char_ngrams(b)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def domain_similarity(a: str, b: str) -> dict[str, float]:
    token_score = token_jaccard(a, b)
    char_score = char_ngram_jaccard(a, b)
    return {
        "score": round(max(token_score, char_score), 4),
        "token_jaccard": round(token_score, 4),
        "char_trigram_jaccard": round(char_score, 4),
    }


def effort_prior_candidates(weights: dict[str, Any], requested_domain: str) -> list[dict[str, Any]]:
    domains = weights.get("domains") or {}
    candidates = []
    for domain, entry in domains.items():
        if not isinstance(entry, dict):
            continue
        prior = entry.get("expected_cost_agent_minutes_prior")
        if prior is None:
            continue
        similarity = domain_similarity(requested_domain, domain)
        candidates.append({
            "domain": domain,
            **similarity,
            "expected_cost_agent_minutes_prior": float(prior),
            "score_rows": entry.get("score_rows"),
            "sample_limited": entry.get("sample_limited"),
        })
    return sorted(candidates, key=lambda row: (-row["score"], row["domain"]))


def resolve_effort_prior(
    weights: dict[str, Any],
    requested_domain: str,
    min_similarity: float,
) -> dict[str, Any]:
    candidates = effort_prior_candidates(weights, requested_domain)
    exact_prior = domain_effort_prior(weights, requested_domain)
    if exact_prior is not None:
        return {
            "requested_domain": requested_domain,
            "selected_domain": requested_domain,
            "expected_cost_agent_minutes_prior": exact_prior,
            "match_type": "exact",
            "score": 1.0,
            "token_jaccard": 1.0,
            "char_trigram_jaccard": 1.0,
            "similarity_method": "exact_domain_or_hybrid_lexical",
            "min_similarity": min_similarity,
            "top_candidates": candidates[:5],
        }
    best = candidates[0] if candidates else None
    if best and best["score"] >= min_similarity:
        return {
            "requested_domain": requested_domain,
            "selected_domain": best["domain"],
            "expected_cost_agent_minutes_prior": best["expected_cost_agent_minutes_prior"],
            "match_type": "nearest_hybrid_lexical",
            "score": best["score"],
            "token_jaccard": best["token_jaccard"],
            "char_trigram_jaccard": best["char_trigram_jaccard"],
            "similarity_method": "exact_domain_or_hybrid_lexical",
            "min_similarity": min_similarity,
            "top_candidates": candidates[:5],
        }
    return {
        "requested_domain": requested_domain,
        "selected_domain": None,
        "expected_cost_agent_minutes_prior": None,
        "match_type": "no_acceptable_prior_domain",
        "score": best["score"] if best else None,
        "token_jaccard": best["token_jaccard"] if best else None,
        "char_trigram_jaccard": best["char_trigram_jaccard"] if best else None,
        "similarity_method": "exact_domain_or_hybrid_lexical",
        "min_similarity": min_similarity,
        "top_candidates": candidates[:5],
    }


def parse_contract_id(raw: str | None, question: str) -> str:
    contract_id = raw or slug(question + "_" + now_iso().replace(":", "").replace("-", ""))
    if not contract_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", contract_id):
        raise SystemExit("contract_id must contain only letters, numbers, hyphens, or underscores")
    return contract_id


def cmd_init_contract(args: argparse.Namespace) -> int:
    ensure_dirs()
    weights = load_weights()
    contract_id = parse_contract_id(args.contract_id, args.question)
    if args.layer not in LAYERS:
        raise SystemExit(f"layer must be one of {sorted(LAYERS)}")
    effort_prior_domain = args.effort_prior_domain or args.task_type
    require_non_negative(args.min_effort_prior_similarity, "--min-effort-prior-similarity")
    if args.min_effort_prior_similarity > 1.0:
        raise SystemExit("--min-effort-prior-similarity must be at most 1.0")
    effort_prior_evidence = resolve_effort_prior(
        weights,
        effort_prior_domain,
        args.min_effort_prior_similarity,
    )
    effort_prior = effort_prior_evidence["expected_cost_agent_minutes_prior"]
    budget_agent_minutes = args.budget_agent_minutes
    budget_source = "operator_supplied"
    if args.budget_from_effort_prior:
        if effort_prior is None:
            raise SystemExit(
                f"no effort prior for domain {effort_prior_domain!r}; "
                "run calibrate, lower --min-effort-prior-similarity, or omit --budget-from-effort-prior"
            )
        budget_agent_minutes = effort_prior
        budget_source = f"domain_effort_prior:{effort_prior_evidence['match_type']}"
    for field in (
        "value_if_success",
        "cost_penalty",
        "risk_penalty",
        "information_value",
    ):
        require_non_negative(getattr(args, field), f"--{field.replace('_', '-')}")
    require_non_negative(budget_agent_minutes, "--budget-agent-minutes")
    path = contract_path(contract_id)
    if path.exists() and not args.allow_overwrite:
        raise SystemExit(f"contract exists: {path}")
    # RC3 #27 — CONTRACT-INIT forced-consumption bind. For an NS/Track-B
    # task the surfaced item the probe consumes must be gate-validated
    # AT CREATION (before the science), stored in the contract, so a
    # close-time OR init-time-free-text paste cannot satisfy it (the
    # field is machine-validated here, not prose). Non-NS ⇒ advisory.
    _consumes_surfaced = getattr(args, "consumes_surfaced", None)
    try:
        import sys as _s
        _src = str(REPO / "src")
        if _src not in _s.path:
            _s.path.insert(0, _src)
        from ztare.validator.surfaced_consumption_gate import (
            consumed_id_is_surfaced,
        )
        _cs_ok, _cs_why = consumed_id_is_surfaced(
            _consumes_surfaced,
            f"{args.task_type} {args.question}",
        )
    except Exception as _e:
        _cs_ok, _cs_why = True, f"surfaced_consumption_gate degraded ({_e}) — advisory"
    if not _cs_ok:
        raise SystemExit(
            f"REFUSED contract-init (RC3 #27 forced-consumption): "
            f"{_cs_why}\nAn NS/Track-B contract MUST be created with "
            f"--consumes-surfaced <full live void-audit surfaced id> "
            f"(probe bound to the surfaced set at SELECTION, not "
            f"free-recalled).")
    payload = {
        "consumes_surfaced": _consumes_surfaced,
        "consumes_surfaced_validation": _cs_why,
        "contract_id": contract_id,
        "created_at": now_iso(),
        "created_by": args.created_by,
        "layer": args.layer,
        "task_type": args.task_type,
        "question": args.question,
        "objective_resolver": args.objective_resolver,
        "success_threshold": args.success_threshold,
        "horizon": args.horizon,
        "budget_agent_minutes": budget_agent_minutes,
        "budget_agent_minutes_source": budget_source,
        "effort_calibration": {
            **effort_prior_evidence,
            "source": relpath(WEIGHTS) if WEIGHTS.exists() else None,
            "agent_instruction": (
                "Use this prior as a baseline when estimating effort; override "
                "only by naming why this contract differs structurally."
            ),
        },
        "value_if_success": args.value_if_success,
        "cost_penalty": args.cost_penalty,
        "risk_penalty": args.risk_penalty,
        "information_value": args.information_value,
        "void_conditions": args.void_conditions,
        "baseline_action": args.baseline_action,
        "counterfactual_action": args.counterfactual_action,
        "externality_hypotheses": parse_json_object(
            args.externality_hypotheses_json,
            "--externality-hypotheses-json",
        ),
        "execution_layer_policy": {
            "forecasters_read_only": True,
            "builders_no_stake": True,
            "sealed_batch": True,
            "live_price_hidden_from_builders": True,
        },
        "artifact_paths": {
            "contract": relpath(path),
            "forecast_dir": relpath(forecast_dir(contract_id)),
            "aggregate": relpath(aggregate_path(contract_id)),
            "outcome": relpath(outcome_path(contract_id)),
            "score": relpath(score_path(contract_id)),
        },
    }
    write_json(path, payload)
    emitted_wake = None
    if getattr(args, "emit_warm_wake", False):
        if not getattr(args, "warm_write", True):
            raise SystemExit("--emit-warm-wake requires --warm-write")
        warm_args = argparse.Namespace(
            contract_id=contract_id,
            forecasters=getattr(
                args,
                "warm_forecasters",
                "claude:claude_forecaster:forecasting_agent,codex:codex_forecaster:forecasting_agent",
            ),
            min_forecasts=getattr(args, "warm_min_forecasts", 2),
            max_events=getattr(args, "warm_max_events", 2),
            reactivate_on_evidence=False,
            include_closed=False,
            include_calibration=getattr(args, "warm_include_calibration", True),
            include_gp233=getattr(args, "warm_include_gp233", False),
            evidence_path=getattr(args, "warm_evidence_path", []) or [],
            force=getattr(args, "warm_force", False),
            write=True,
            emit_agent_channel=getattr(args, "warm_emit_agent_channel", True),
            from_role=getattr(args, "warm_from_role", "research_director"),
            to_role="forecasting_agent",
        )
        emitted_wake = daemon_once_payload_for_contract_publish(warm_args)
    print(json.dumps({
        "contract_id": contract_id,
        "path": relpath(path),
        "warm_wake": emitted_wake,
    }, indent=2, sort_keys=True))
    refresh_market_state_best_effort(contract_id)
    return 0


def parse_failure_modes(text: str | None) -> dict[str, float]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"failure mode distribution must be JSON: {e}") from e
    if not isinstance(data, dict):
        raise SystemExit("failure mode distribution must be a JSON object")
    try:
        numeric = {str(k): float(v) for k, v in data.items()}
    except (TypeError, ValueError) as e:
        raise SystemExit(f"failure mode distribution values must be numeric: {e}") from e
    if any(v < 0 for v in numeric.values()):
        raise SystemExit("failure mode distribution values must be non-negative")
    total = sum(numeric.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in numeric.items()}


def parse_json_object(text: str | None, field: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{field} must be a JSON object: {e}") from e
    if not isinstance(data, dict):
        raise SystemExit(f"{field} must be a JSON object")
    return data


def parse_json_list(text: str | None, field: str) -> list[str]:
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"{field} must be a JSON list: {e}") from e
    if not isinstance(data, list):
        raise SystemExit(f"{field} must be a JSON list")
    return [str(item) for item in data]


def cmd_prompt_template(args: argparse.Namespace) -> int:
    """Emit the recommended elicitation prompt block + config for the given agent.

    Per F37/F39/F41 chain — RDs don't have to remember which prompt fragments
    apply to which agent family. One CLI call constructs the right prompt.

    Example:
      python3 scripts/public/control/forecast/pool.py prompt-template --agent-id claude
        -> emits balance-instruction + signed-tail fragments (F39 + F37)
      python3 scripts/public/control/forecast/pool.py prompt-template --agent-id codex_55 --format json
        -> emits full config dict
    """
    cfg = recommended_elicitation_for_agent(args.agent_id)
    if args.format == "json":
        print(json.dumps(cfg, indent=2))
    else:
        print(cfg["prompt_block"])
        print()
        print(f"# agent_family: {cfg['agent_family']}")
        print(f"# rationale: {cfg['rationale']}")
        if cfg["signed_tail_required"]:
            print(f"# REQUIRED: include tail_downside_worry + tail_upside_surprise in the emission.")
        if cfg["balance_instruction_required"]:
            print(f"# REQUIRED: include the balance instruction (already in prompt block above).")
    return 0


def cmd_add_forecast(args: argparse.Namespace) -> int:
    ensure_dirs()
    contract = load_contract(args.contract_id)
    if not args.read_only_attestation:
        raise SystemExit("--read-only-attestation is required; forecasters must attest read-only pricing")
    base_path = forecast_path(args.contract_id, args.agent_id)
    prior_forecast = read_json(base_path) if base_path.exists() else None
    if prior_forecast and not isinstance(prior_forecast, dict):
        raise SystemExit(f"forecast must be a JSON object: {base_path}")
    if prior_forecast is None and args.belief_update:
        raise SystemExit("--belief-update requires an existing base forecast for this agent")
    if prior_forecast is not None and not (args.allow_overwrite or args.belief_update):
        raise SystemExit(f"forecast exists: {base_path}; use --belief-update for a timestamped odds update")
    weights = load_weights()
    expected_cost_source = "forecaster_supplied"
    if args.expected_cost_agent_minutes is None:
        prior = domain_effort_prior(weights, args.domain)
        if prior is not None:
            args.expected_cost_agent_minutes = prior
            expected_cost_source = "domain_effort_prior"
    require_non_negative(args.expected_cost_agent_minutes, "--expected-cost-agent-minutes")
    require_optional_probability(getattr(args, "tail_insurance_premium", None), "--tail-insurance-premium")
    require_non_negative(getattr(args, "tail_loss_magnitude", None), "--tail-loss-magnitude")
    require_non_negative(getattr(args, "tail_downside_worry", None), "--tail-downside-worry")
    require_non_negative(getattr(args, "tail_upside_surprise", None), "--tail-upside-surprise")
    require_optional_probability(getattr(args, "verbalized_confidence", None), "--verbalized-confidence")
    require_non_negative(getattr(args, "predicted_self_error_ratio", None), "--predicted-self-error-ratio")
    # F56 bid-ask spread + F61 self-predicted Brier interval (channel_routing).
    require_optional_probability(getattr(args, "p_buy_yes_max", None), "--p-buy-yes-max")
    require_optional_probability(getattr(args, "p_sell_yes_min", None), "--p-sell-yes-min")
    require_optional_probability(getattr(args, "predicted_brier_lo", None), "--predicted-brier-lo")
    require_optional_probability(getattr(args, "predicted_brier_hi", None), "--predicted-brier-hi")
    if (
        getattr(args, "p_buy_yes_max", None) is not None
        and getattr(args, "p_sell_yes_min", None) is not None
        and float(args.p_buy_yes_max) > float(args.p_sell_yes_min)
    ):
        raise SystemExit(
            "--p-buy-yes-max must be <= --p-sell-yes-min "
            "(F56: buy YES low, sell YES high; spread = sell - buy)"
        )
    if (
        getattr(args, "predicted_brier_lo", None) is not None
        and getattr(args, "predicted_brier_hi", None) is not None
        and float(args.predicted_brier_lo) > float(args.predicted_brier_hi)
    ):
        raise SystemExit(
            "--predicted-brier-lo must be <= --predicted-brier-hi (F61 interval)"
        )
    # F36: derive agent_family from canonical id if not explicitly supplied. Logged
    # on every emission so downstream consumers can apply per-family rules without
    # reverse-engineering from agent_id strings.
    agent_family = getattr(args, "agent_family", None) or derive_agent_family(args.agent_id)
    forecasted_at = now_iso()
    payload = {
        "contract_id": args.contract_id,
        "forecasted_at": forecasted_at,
        "agent_id": args.agent_id,
        "domain": args.domain,
        "p_success": clamp_p(args.p_success),
        "expected_cost_agent_minutes": args.expected_cost_agent_minutes,
        "expected_cost_source": expected_cost_source,
        "p_regression": clamp_p(args.p_regression),
        "p_dependency_issue": clamp_p(args.p_dependency_issue),
        "p_needs_new_lemma": clamp_p(args.p_needs_new_lemma),
        "failure_mode_distribution": parse_failure_modes(args.failure_modes_json),
        "specific_failure_mode_ids": parse_json_list(
            args.specific_failure_mode_ids_json,
            "--specific-failure-mode-ids-json",
        ),
        "action_change_recommendation": args.action_change_recommendation,
        "forecast_externality_tags": parse_json_list(
            args.forecast_externality_tags_json,
            "--forecast-externality-tags-json",
        ),
        "rationale_short": args.rationale_short,
        "read_only_attestation": args.read_only_attestation,
        "contract_question": contract["question"],
    }
    for second_moment_field in (
        "tail_insurance_premium",
        "tail_loss_magnitude",
        "tail_downside_worry",
        "tail_upside_surprise",
        "verbalized_confidence",
        "predicted_self_error_ratio",
        "p_buy_yes_max",
        "p_sell_yes_min",
        "predicted_brier_lo",
        "predicted_brier_hi",
    ):
        second_moment_value = getattr(args, second_moment_field, None)
        if second_moment_value is not None:
            payload[second_moment_field] = float(second_moment_value)
    if (
        payload.get("p_buy_yes_max") is not None
        and payload.get("p_sell_yes_min") is not None
    ):
        payload["spread"] = round(
            float(payload["p_sell_yes_min"]) - float(payload["p_buy_yes_max"]), 6
        )
    if (
        payload.get("predicted_brier_lo") is not None
        and payload.get("predicted_brier_hi") is not None
    ):
        b_lo = float(payload["predicted_brier_lo"])
        b_hi = float(payload["predicted_brier_hi"])
        payload["b_mid"] = round((b_lo + b_hi) / 2.0, 6)
        payload["b_width"] = round(b_hi - b_lo, 6)
    if agent_family is not None:
        payload["agent_family"] = agent_family
    if args.belief_update or args.update_reason or args.evidence_fingerprint or prior_forecast:
        payload.update({
            "belief_update": bool(args.belief_update),
            "update_reason": args.update_reason,
            "evidence_fingerprint": args.evidence_fingerprint,
            "prior_forecast_artifact_path": relpath(base_path) if prior_forecast else None,
            "prior_forecasted_at": prior_forecast.get("forecasted_at") if prior_forecast else None,
            "prior_p_success": prior_forecast.get("p_success") if prior_forecast else None,
        })
    # F37/F39/F41 best-practice gate (2026-05-26 strict enforcement).
    # Reject claude-family emissions without signed-tail BEFORE write — RDs
    # must populate the right fields or pass --allow-missing-best-practice.
    try:
        warnings = check_emission_best_practice(
            payload, allow_bypass=getattr(args, "allow_missing_best_practice", False)
        )
        for w in warnings:
            print(f"[best-practice] {w}", file=sys.stderr)
    except BestPracticeViolation as e:
        print(f"[best-practice] {e}", file=sys.stderr)
        return 6  # non-zero exit; non-overlapping with existing codes
    path = (
        forecast_update_path(args.contract_id, args.agent_id, forecasted_at)
        if args.belief_update else base_path
    )
    write_json(path, payload)
    refresh_market_state_best_effort(args.contract_id)
    print(json.dumps({
        "forecast": relpath(path),
        "belief_update": bool(args.belief_update),
        "agent_id": args.agent_id,
        "forecasted_at": forecasted_at,
        "p_success": payload["p_success"],
    }, indent=2))
    return 0


def aggregate(contract_id: str) -> dict[str, Any]:
    contract = load_contract(contract_id)
    confident_no_eligibility = confident_no_policy_eligibility(contract)
    forecast_history = load_forecasts(contract_id)
    forecasts = latest_forecasts_by_agent(forecast_history)
    if not forecasts:
        raise SystemExit(f"no forecasts for {contract_id}")
    weights = load_weights()
    weighted_logits = []
    weighted_costs = []
    weighted_regressions = []
    weighted_dependency = []
    weighted_new_lemma = []
    weighted_confident_no_logits = []
    raw_panel_ps = []
    confident_no_panel_ps = []
    confident_no_adjusted_count = 0
    total_w = 0.0
    failure_modes: dict[str, float] = {}
    participants = []
    for fc in forecasts:
        agent_id = fc["agent_id"]
        domain = fc.get("domain") or contract.get("task_type") or "default"
        w = max(0.05, domain_weight(weights, agent_id, domain))
        raw_p_success = clamp_p(fc["p_success"])
        adjusted_p_success = confident_no_discount(raw_p_success)
        adjusted = abs(adjusted_p_success - raw_p_success) > 1e-12
        if adjusted:
            confident_no_adjusted_count += 1
        total_w += w
        participants.append({
            "agent_id": agent_id,
            "domain": domain,
            "weight": w,
            "p_success": raw_p_success,
            "confident_no_adjusted_p_success": adjusted_p_success,
            "confident_no_adjustment_applied": adjusted,
            "forecasted_at": fc.get("forecasted_at"),
            "belief_update": bool(fc.get("belief_update")),
            "forecast_artifact_path": fc.get("forecast_artifact_path"),
        })
        weighted_logits.append(w * logit(raw_p_success))
        weighted_confident_no_logits.append(w * logit(adjusted_p_success))
        raw_panel_ps.append(raw_p_success)
        confident_no_panel_ps.append(adjusted_p_success)
        expected_cost = fc.get("expected_cost_agent_minutes")
        if expected_cost is None:
            expected_cost = domain_effort_prior(weights, domain)
        weighted_costs.append(w * float(expected_cost or 0.0))
        weighted_regressions.append(w * float(fc.get("p_regression") or 0.0))
        weighted_dependency.append(w * float(fc.get("p_dependency_issue") or 0.0))
        weighted_new_lemma.append(w * float(fc.get("p_needs_new_lemma") or 0.0))
        for mode, p in (fc.get("failure_mode_distribution") or {}).items():
            failure_modes[mode] = failure_modes.get(mode, 0.0) + w * float(p)
    p_success = sigmoid(sum(weighted_logits) / total_w)
    raw_mean_panel_p_success = sum(raw_panel_ps) / len(raw_panel_ps)
    confident_no_p_success = sum(confident_no_panel_ps) / len(confident_no_panel_ps)
    confident_no_weighted_logit_p_success = sigmoid(sum(weighted_confident_no_logits) / total_w)
    expected_cost = sum(weighted_costs) / total_w
    p_regression = sum(weighted_regressions) / total_w
    p_dependency = sum(weighted_dependency) / total_w
    p_new_lemma = sum(weighted_new_lemma) / total_w
    norm_failure = {k: v / total_w for k, v in sorted(failure_modes.items(), key=lambda kv: -kv[1])}
    ev = (
        float(contract["value_if_success"]) * p_success
        - float(contract["cost_penalty"]) * expected_cost
        - float(contract["risk_penalty"]) * p_regression
        + float(contract["information_value"])
    )
    confident_no_ev = (
        float(contract["value_if_success"]) * confident_no_p_success
        - float(contract["cost_penalty"]) * expected_cost
        - float(contract["risk_penalty"]) * p_regression
        + float(contract["information_value"])
    )
    aggregate_summary = {
        "exists": True,
        "p_success": p_success,
        "raw_mean_panel_p_success": raw_mean_panel_p_success,
        "confident_no_adjusted_p_success": confident_no_p_success,
        "confident_no_adjusted_weighted_logit_p_success": confident_no_weighted_logit_p_success,
        "expected_cost_agent_minutes": expected_cost,
        "p_regression": p_regression,
        "p_dependency_issue": p_dependency,
        "p_needs_new_lemma": p_new_lemma,
        "expected_value": ev,
        "confident_no_adjusted_expected_value": confident_no_ev,
        "top_failure_modes": top_failure_modes(norm_failure),
    }
    allocation = allocation_recommendation(
        contract=contract,
        aggregate_summary=aggregate_summary,
        latest_forecasts=forecasts,
        lifecycle_state="aggregate_ready",
    )
    return {
        "contract_id": contract_id,
        "aggregated_at": now_iso(),
        "forecast_count": len(forecasts),
        "forecast_history_count": len(forecast_history),
        "aggregation_policy": "latest_forecast_per_agent_id",
        "aggregate": {
            "p_success": p_success,
            "raw_mean_panel_p_success": raw_mean_panel_p_success,
            "confident_no_adjusted_p_success": confident_no_p_success,
            "confident_no_adjusted_weighted_logit_p_success": confident_no_weighted_logit_p_success,
            "confident_no_adjusted_forecast_count": confident_no_adjusted_count,
            "confident_no_adjustment_policy": {
                "policy_id": "F100_confident_no_discount_v1",
                "source": "org/calibration/per_agent_prompt_policy.yaml#universal.confident_no_discount",
                "rule": "if p_raw < 0.10: p_adjusted = p_raw + (0.65 - p_raw) * 0.5",
                "aggregation": "unweighted mean panel over latest forecasts; weighted-logit adjusted view also emitted",
                "policy_eligible": confident_no_eligibility["eligible"],
                "policy_eligibility_reason": confident_no_eligibility["reason"],
                "scope": "forward-looking/source-valid calibrated post-forecast view with time-valid labels/baselines; raw aggregate preserved; do not use for retrospective pre-cutoff or current-label dataset benchmark correction",
                "latest_scope_caveat": "FRED current-label rows are excluded as calibration evidence unless an ALFRED/bulk-export confirmation reinstates repaired labels; see 2026-06-04 FRED vintage timing audit/bulk repair/rescore.",
            },
            "expected_cost_agent_minutes": expected_cost,
            "p_regression": p_regression,
            "p_dependency_issue": p_dependency,
            "p_needs_new_lemma": p_new_lemma,
            "failure_mode_distribution": norm_failure,
            "expected_value": ev,
            "confident_no_adjusted_expected_value": confident_no_ev,
        },
        "participants": participants,
        "contract_question": contract["question"],
        "routing_hint": (
            "run_or_continue" if ev > 0 and p_success >= 0.35
            else "audit_or_explore_only" if p_success >= 0.15 or float(contract["information_value"]) > 0
            else "defer_unless_exploration_budget"
        ),
        "allocation_recommendation": allocation,
    }


def cmd_aggregate(args: argparse.Namespace) -> int:
    ensure_dirs()
    payload = aggregate(args.contract_id)
    write_json(aggregate_path(args.contract_id), payload)
    refresh_market_state_best_effort(args.contract_id)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    ensure_dirs()
    load_contract(args.contract_id)
    # KERNEL ORDERING INVARIANT (mechanized 2026-05-16 after a 2x recurrence,
    # catches C-2026-05-16-136/-137): never resolve before an independent
    # warm-wake is consumed (else cross-agent forecast diversity is lost
    # because the forecaster cannot bet a resolved contract). Enforced HERE
    # at the action locus — prose in rd_tick_brief §8 was non-forcing
    # (buried-prescription). Override requires an explicit logged reason.
    independent_bets = independent_forecaster_rows(args.contract_id)
    has_independent_bet = bool(independent_bets)
    has_codex_bet = any(row["canonical_agent_id"] == "codex" for row in independent_bets)
    has_claude_bet = any(row["canonical_agent_id"] == "claude" for row in independent_bets)
    if not has_independent_bet and not getattr(args, "allow_no_independent_forecaster", False):
        print(json.dumps({
            "error": "ORDERING_BLOCK_INDEPENDENT_FORECAST_ABSENT",
            "contract_id": args.contract_id,
            "detail": ("recognized independent forecast absent — do NOT resolve "
                       "before an independent forecaster wake is consumed. "
                       "Accepted identities: claude, claude_forecaster, codex, "
                       "codex_forecaster. Run `warm-daemon-once "
                       f"--contract-id {args.contract_id} --forecasters "
                       "claude:claude_forecaster:forecasting_agent,"
                       "codex:codex_forecaster:forecasting_agent` and wait, "
                       "or pass --allow-no-independent-forecaster "
                       "--no-independent-forecaster-reason '<why>' to override "
                       "(logged)."),
        }, indent=2))
        return 2
    if (
        not has_independent_bet
        and getattr(args, "allow_no_independent_forecaster", False)
        and not getattr(args, "no_independent_forecaster_reason", None)
    ):
        print(json.dumps({
            "error": "ORDERING_OVERRIDE_NEEDS_REASON",
            "detail": (
                "--allow-no-independent-forecaster requires "
                "--no-independent-forecaster-reason '<why>'."
            ),
        }, indent=2))
        return 2
    require_non_negative(args.actual_cost_agent_minutes, "--actual-cost-agent-minutes")
    payload = {
        "contract_id": args.contract_id,
        "resolved_at": now_iso(),
        "success_bool": args.success_bool,
        "actual_cost_agent_minutes": args.actual_cost_agent_minutes,
        "compile_status": args.compile_status,
        "sorry_delta": args.sorry_delta,
        "goal_delta": args.goal_delta,
        "error_type": args.error_type,
        "artifact_hash": args.artifact_hash,
        "artifact_path": args.artifact_path,
        "resolution_note": args.resolution_note,
        "realized_failure_mode_ids": parse_json_list(
            args.realized_failure_mode_ids_json,
            "--realized-failure-mode-ids-json",
        ),
        "failure_mode_preconditioner_used": args.failure_mode_preconditioner_used,
        "preconditioner_source": args.preconditioner_source,
        "preconditioner_effect": args.preconditioner_effect,
        "decision_changed_bool": args.decision_changed_bool,
        "old_next_action": args.old_next_action,
        "new_next_action": args.new_next_action,
        "externality_tags": parse_json_list(args.externality_tags_json, "--externality-tags-json"),
        "negative_externality_tags": parse_json_list(
            args.negative_externality_tags_json,
            "--negative-externality-tags-json",
        ),
        "counterfactual_value_bucket": args.counterfactual_value_bucket,
        "changed_by_forecast_ids": parse_json_list(
            args.changed_by_forecast_ids_json,
            "--changed-by-forecast-ids-json",
        ),
        "voided": args.voided,
        "codex_bet_present": has_codex_bet,
        "claude_bet_present": has_claude_bet,
        "independent_forecaster_bet_present": has_independent_bet,
        "independent_forecaster_bets": independent_bets,
        "ordering_override_no_codex": (
            getattr(args, "no_independent_forecaster_reason", None)
            if not has_independent_bet else None),
        "ordering_override_no_independent_forecaster": (
            getattr(args, "no_independent_forecaster_reason", None)
            if not has_independent_bet else None),
    }
    write_json(outcome_path(args.contract_id), payload)
    append_market_event(
        "contract_resolved",
        contract_id=args.contract_id, success=args.success_bool)
    refresh_market_state_best_effort(args.contract_id)
    print(json.dumps({"outcome": relpath(outcome_path(args.contract_id)), "success": args.success_bool}, indent=2))
    return 0


def log_score(p: float, success: bool) -> float:
    p = clamp_p(p)
    return math.log(p if success else 1.0 - p)


def brier_score(p: float, success: bool) -> float:
    y = 1.0 if success else 0.0
    return (p - y) ** 2


def signed_calibration_bias(role_prefix: str = "research_director",
                            last_n: int = 30, min_n: int = 10) -> dict[str, Any]:
    """DIAGNOSTIC-ONLY signed forecast-calibration bias on the role's OWN
    work. bias_i = p_predicted_i - y_i (y=1 success, 0 fail) over the most
    recent non-voided resolved contracts where a forecast agent_id starts
    with role_prefix. mean<0 => systematically under-predicts own success
    = recurring-pessimism signal (AP-014 family, operator-flagged >=4x);
    mean>0 => optimism. Read directly from outcomes/+forecasts/ (robust;
    does NOT require cmd_score). SLOW TREND MONITOR, n-gated, advisory —
    NEVER an auto-override (surfacing the number induces no directive;
    the human/Meta-Darwin still judges, else it becomes optimism-gaming).
    """
    pairs: list[tuple[str, float, int]] = []  # (resolved_at, p, y)
    if not OUTCOMES.exists():
        return {"status": "no_outcomes", "n": 0}
    for of in OUTCOMES.glob("*.json"):
        try:
            o = json.loads(of.read_text(errors="ignore"))
        except Exception:
            continue
        if o.get("voided") or o.get("success_bool") is None:
            continue
        cid = of.stem
        fdir = FORECASTS / cid
        if not fdir.exists():
            continue
        p_val = None
        for ff in fdir.glob("*.json"):
            if not ff.stem.startswith(role_prefix):
                continue
            try:
                fc = json.loads(ff.read_text(errors="ignore"))
                if fc.get("p_success") is not None:
                    p_val = float(fc["p_success"])
            except Exception:
                pass
        if p_val is None:
            continue
        pairs.append((str(o.get("resolved_at") or ""), p_val,
                      1 if bool(o["success_bool"]) else 0))
    pairs.sort(key=lambda t: t[0])
    window = pairs[-last_n:]
    n = len(window)
    if n < min_n:
        return {"status": "insufficient_n", "n": n, "min_n": min_n,
                "note": f"need >={min_n} resolved own-work contracts for a "
                        "stable signed-bias trend (currently noisy)."}
    bias = sum(p - y for _, p, y in window) / n
    if bias <= -0.15:
        interp = ("RECURRING-PESSIMISM SIGNAL: own-work success "
                  "systematically under-predicted (AP-014 family). "
                  "Diagnostic only — not an override; Meta-Darwin/operator judges.")
    elif bias >= 0.15:
        interp = ("OPTIMISM SIGNAL: own-work success systematically "
                  "over-predicted. Diagnostic only — not an override.")
    else:
        interp = "CALIBRATED (|signed bias| < 0.15). No directional flag."
    return {"status": "ok", "n": n, "window_last_n": last_n,
            "mean_signed_bias": round(bias, 4),
            "convention": "bias = p_predicted - outcome; <0 pessimism, >0 optimism",
            "interpretation": interp, "diagnostic_only": True}


def failure_mode_externality_score(forecast: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
    realized = {str(item) for item in outcome.get("realized_failure_mode_ids") or []}
    dist = forecast.get("failure_mode_distribution") or {}
    specific = {str(item) for item in forecast.get("specific_failure_mode_ids") or []}
    if not realized:
        return {
            "realized_failure_mode_ids_available": False,
            "failure_mode_top1_hit": None,
            "failure_mode_realized_mass": None,
            "specific_failure_mode_id_hit": None,
        }
    top = None
    if isinstance(dist, dict) and dist:
        top = max(dist.items(), key=lambda kv: float(kv[1]))[0]
    realized_mass = 0.0
    if isinstance(dist, dict):
        for mode, p in dist.items():
            if str(mode) in realized:
                realized_mass += float(p)
    return {
        "realized_failure_mode_ids_available": True,
        "failure_mode_top1_hit": None if top is None else str(top) in realized,
        "failure_mode_realized_mass": round(realized_mass, 6),
        "specific_failure_mode_id_hit": None if not specific else bool(specific & realized),
    }


def cmd_score(args: argparse.Namespace) -> int:
    ensure_dirs()
    contract = load_contract(args.contract_id)
    outcome = read_json(outcome_path(args.contract_id))
    if not outcome:
        raise SystemExit(f"missing outcome: {outcome_path(args.contract_id)}")
    if not isinstance(outcome, dict):
        raise SystemExit(f"outcome must be a JSON object: {outcome_path(args.contract_id)}")
    require_fields(outcome, REQUIRED_OUTCOME_FIELDS, f"outcome {args.contract_id}")
    if outcome.get("voided"):
        raise SystemExit(f"contract is voided; refusing to score: {args.contract_id}")
    forecast_history = load_forecasts(args.contract_id)
    forecasts = latest_forecasts_by_agent(forecast_history)
    if not forecasts:
        raise SystemExit(f"no forecasts for {args.contract_id}")
    success = bool(outcome["success_bool"])
    contract_created_at = parse_iso_timestamp(contract["created_at"], "contract.created_at")
    resolved_at = parse_iso_timestamp(outcome["resolved_at"], "outcome.resolved_at")
    rows = []
    for fc in forecasts:
        forecasted_at = parse_iso_timestamp(fc["forecasted_at"], f"forecast {fc['agent_id']} forecasted_at")
        if forecasted_at > resolved_at:
            raise SystemExit(
                "refusing to score late forecast: "
                f"{fc['agent_id']} forecasted_at={fc['forecasted_at']} resolved_at={outcome['resolved_at']}"
            )
        p = float(fc["p_success"])
        actual_cost = outcome.get("actual_cost_agent_minutes")
        expected_cost = fc.get("expected_cost_agent_minutes")
        row = {
            "agent_id": fc["agent_id"],
            "domain": fc.get("domain"),
            "p_success": p,
            "success_bool": success,
            "brier": brier_score(p, success),
            "log_score": log_score(p, success),
            "expected_cost_agent_minutes": expected_cost,
            "actual_cost_agent_minutes": actual_cost,
            "cost_error_agent_minutes": (
                None if actual_cost is None or expected_cost is None
                else float(expected_cost) - float(actual_cost)
            ),
            "externality_audit": failure_mode_externality_score(fc, outcome),
            "temporal_audit": {
                "contract_created_at": contract["created_at"],
                "forecasted_at": fc["forecasted_at"],
                "resolved_at": outcome["resolved_at"],
                "forecast_after_contract": forecasted_at >= contract_created_at,
                "forecast_before_resolution": forecasted_at <= resolved_at,
            },
        }
        # F8/F10: pass through optional second-moment fields when present on the forecast.
        # Surfaces them on the score row so calibration_payload can compute Brier-vs-channel Spearman.
        for _smf in OPTIONAL_SECOND_MOMENT_FORECAST_FIELDS:
            _val = fc.get(_smf)
            if _val is not None:
                row[_smf] = _val
        rows.append(row)
    payload = {
        "contract_id": args.contract_id,
        "scored_at": now_iso(),
        "outcome": outcome,
        "scores": rows,
        "score_policy": "latest_forecast_per_agent_id",
        "forecast_history_count": len(forecast_history),
        "mean_brier": sum(r["brier"] for r in rows) / len(rows),
        "mean_log_score": sum(r["log_score"] for r in rows) / len(rows),
        "externality_audit": {
            "contract_fields": {
                key: contract.get(key)
                for key in sorted(CONTRACT_EXTERNALITY_FIELDS)
                if contract.get(key) not in (None, "", [], {})
            },
            "outcome_fields": {
                key: outcome.get(key)
                for key in sorted(OUTCOME_EXTERNALITY_FIELDS)
                if outcome.get(key) not in (None, "", [], {})
            },
            "forecast_rows_with_specific_failure_mode_ids": sum(
                1 for fc in forecasts if fc.get("specific_failure_mode_ids")
            ),
            "forecast_rows_with_action_change_recommendation": sum(
                1 for fc in forecasts if fc.get("action_change_recommendation")
            ),
            "forecast_rows_with_externality_tags": sum(
                1 for fc in forecasts if fc.get("forecast_externality_tags")
            ),
        },
    }
    write_json(score_path(args.contract_id), payload)
    refresh_market_state_best_effort(args.contract_id)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_scratch_forecast(args: argparse.Namespace) -> int:
    """Write an explicitly uncertified RD forecast stamp.

    This is intentionally outside contracts/forecasts/outcomes/scores and does
    not refresh market_state. It is for quick RD calibration notes when the
    certified forecast lifecycle would add more ceremony than information.
    """
    ensure_dirs()
    if not args.ack_uncertified:
        raise SystemExit(
            "scratch-forecast requires --ack-uncertified; this stamp is not "
            "a GP-230 contract, does not enter calibration, and cannot satisfy "
            "membrane gates."
        )
    require_probability(args.p_success, "--p-success")
    require_non_negative(args.expected_cost_agent_minutes,
                         "--expected-cost-agent-minutes")
    require_probability(args.tail_insurance_premium, "--tail-insurance-premium")
    require_non_negative(args.tail_loss_magnitude, "--tail-loss-magnitude")
    require_non_negative(args.tail_downside_worry, "--tail-downside-worry")
    require_non_negative(args.tail_upside_surprise, "--tail-upside-surprise")
    require_optional_probability(args.verbalized_confidence, "--verbalized-confidence")
    require_non_negative(args.predicted_self_error_ratio, "--predicted-self-error-ratio")
    # F56 bid-ask spread + F61 self-predicted Brier interval (channel_routing).
    require_optional_probability(getattr(args, "p_buy_yes_max", None), "--p-buy-yes-max")
    require_optional_probability(getattr(args, "p_sell_yes_min", None), "--p-sell-yes-min")
    require_optional_probability(getattr(args, "predicted_brier_lo", None), "--predicted-brier-lo")
    require_optional_probability(getattr(args, "predicted_brier_hi", None), "--predicted-brier-hi")
    if (
        getattr(args, "p_buy_yes_max", None) is not None
        and getattr(args, "p_sell_yes_min", None) is not None
        and float(args.p_buy_yes_max) > float(args.p_sell_yes_min)
    ):
        raise SystemExit(
            "--p-buy-yes-max must be <= --p-sell-yes-min "
            "(F56: buy YES low, sell YES high; spread = sell - buy)"
        )
    if (
        getattr(args, "predicted_brier_lo", None) is not None
        and getattr(args, "predicted_brier_hi", None) is not None
        and float(args.predicted_brier_lo) > float(args.predicted_brier_hi)
    ):
        raise SystemExit(
            "--predicted-brier-lo must be <= --predicted-brier-hi (F61 interval)"
        )
    # F36: derive agent_family from owner (e.g. "claude:RD" -> "claude") if not
    # explicitly supplied. Logged on every scratch row so analyzers can apply
    # per-family sign rules to tail_insurance_premium.
    agent_family = getattr(args, "agent_family", None) or derive_agent_family(args.owner)
    created_at = now_iso()
    failure_modes = parse_failure_modes(args.failure_modes_json)
    context = parse_json_object(args.context_json, "--context-json")
    payload: dict[str, Any] = {
        "mode": "artisanal_uncertified",
        "certified": False,
        "excluded_from_calibration": True,
        "can_satisfy_membrane": False,
        "created_at": created_at,
        "owner": args.owner,
        "domain": args.domain,
        "task_type": args.task_type,
        "question": args.question,
        "p_success": float(args.p_success),
        "expected_cost_agent_minutes": args.expected_cost_agent_minutes,
        "tail_insurance_premium": float(args.tail_insurance_premium),
        "tail_loss_magnitude": float(args.tail_loss_magnitude),
        "tail_downside_worry": (
            None if args.tail_downside_worry is None else float(args.tail_downside_worry)
        ),
        "tail_upside_surprise": (
            None if args.tail_upside_surprise is None else float(args.tail_upside_surprise)
        ),
        "agent_family": agent_family,
        "verbalized_confidence": (
            None if args.verbalized_confidence is None else float(args.verbalized_confidence)
        ),
        "predicted_self_error_ratio": (
            None if args.predicted_self_error_ratio is None
            else float(args.predicted_self_error_ratio)
        ),
        "p_buy_yes_max": (
            None if getattr(args, "p_buy_yes_max", None) is None
            else float(args.p_buy_yes_max)
        ),
        "p_sell_yes_min": (
            None if getattr(args, "p_sell_yes_min", None) is None
            else float(args.p_sell_yes_min)
        ),
        "spread": (
            None
            if getattr(args, "p_buy_yes_max", None) is None
            or getattr(args, "p_sell_yes_min", None) is None
            else round(float(args.p_sell_yes_min) - float(args.p_buy_yes_max), 6)
        ),
        "predicted_brier_lo": (
            None if getattr(args, "predicted_brier_lo", None) is None
            else float(args.predicted_brier_lo)
        ),
        "predicted_brier_hi": (
            None if getattr(args, "predicted_brier_hi", None) is None
            else float(args.predicted_brier_hi)
        ),
        "b_mid": (
            None
            if getattr(args, "predicted_brier_lo", None) is None
            or getattr(args, "predicted_brier_hi", None) is None
            else round((float(args.predicted_brier_lo) + float(args.predicted_brier_hi)) / 2.0, 6)
        ),
        "b_width": (
            None
            if getattr(args, "predicted_brier_lo", None) is None
            or getattr(args, "predicted_brier_hi", None) is None
            else round(float(args.predicted_brier_hi) - float(args.predicted_brier_lo), 6)
        ),
        "failure_mode_distribution": failure_modes,
        "rationale_short": args.rationale_short,
        "context": context,
        "resolution_predicate": args.resolution_predicate,
        "notes": args.notes,
        "semantics": {
            "official_market_state": False,
            "writes_contract": False,
            "writes_forecast": False,
            "writes_outcome": False,
            "writes_score": False,
            "usable_for_pretick_orientation": True,
            "usable_for_membrane_close": False,
        },
    }
    payload["scratch_id"] = "scratch_" + stable_payload_hash(payload)[:16]
    # F37/F39/F41 best-practice gate (2026-05-26 strict). scratch-forecast uses
    # --owner as identity, not --agent-id; build synthetic payload for the check.
    try:
        warnings = check_emission_best_practice(
            {"agent_id": args.owner, **payload},
            allow_bypass=getattr(args, "allow_missing_best_practice", False),
        )
        for w in warnings:
            print(f"[best-practice] {w}", file=sys.stderr)
    except BestPracticeViolation as e:
        print(f"[best-practice] {e}", file=sys.stderr)
        return 6
    path = scratch_path(created_at, args.owner, args.question, args.slug)
    write_json(path, payload)
    append_jsonl(SCRATCH / "scratch_ledger.jsonl", {
        "scratch_id": payload["scratch_id"],
        "created_at": created_at,
        "owner": args.owner,
        "domain": args.domain,
        "task_type": args.task_type,
        "p_success": float(args.p_success),
        "tail_insurance_premium": float(args.tail_insurance_premium),
        "tail_loss_magnitude": float(args.tail_loss_magnitude),
        "path": relpath(path),
        "certified": False,
        "excluded_from_calibration": True,
        "can_satisfy_membrane": False,
    })
    prediction_row_path = None
    prediction_id = None
    mirror_prediction = (
        args.also_prediction_ledger
        or (
            not args.no_prediction_ledger
            and scratch_defaults_to_prediction_mirror(args.owner)
        )
    )
    if mirror_prediction:
        prediction_id = args.prediction_id or (
            "PL-SCRATCH-" + stable_payload_hash({
                "scratch_id": payload["scratch_id"],
                "question": args.question,
                "created_at": created_at,
            })[:12]
        )
        if prediction_id_exists(args.prediction_ledger, prediction_id):
            raise SystemExit(
                f"prediction_id already exists in {args.prediction_ledger}: "
                f"{prediction_id}"
            )
        prediction_row = {
            "prediction_id": prediction_id,
            "predicted_at": created_at,
            "predictor": args.owner,
            "substrate": args.domain,
            "tier": 1 if args.task_type == "meso_contract" else 2,
            "question": args.question,
            "p_success": float(args.p_success),
            "effort_estimate_agent_minutes": args.expected_cost_agent_minutes,
            "cost_estimate_usd": 0.0,
            "tail_insurance_premium": float(args.tail_insurance_premium),
            "tail_loss_magnitude": float(args.tail_loss_magnitude),
            "tail_downside_worry": (
                None if args.tail_downside_worry is None else float(args.tail_downside_worry)
            ),
            "tail_upside_surprise": (
                None if args.tail_upside_surprise is None else float(args.tail_upside_surprise)
            ),
            "agent_family": agent_family,
            "verbalized_confidence": (
                None if args.verbalized_confidence is None else float(args.verbalized_confidence)
            ),
            "predicted_self_error_ratio": (
                None if args.predicted_self_error_ratio is None
                else float(args.predicted_self_error_ratio)
            ),
            "failure_mode_distribution": failure_modes,
            "pre_registered_thresholds": args.resolution_predicate,
            "prediction_artifact_path": relpath(path),
            "linked_scratch_id": payload["scratch_id"],
            "forecast_pool_semantics": {
                "source": "forecast_pool scratch-forecast",
                "certified": False,
                "excluded_from_calibration": True,
                "can_satisfy_membrane": False,
                "not_a_gp230_contract": True,
            },
            "rationale_short": args.rationale_short,
            "resolved_at": None,
            "actual_outcome": None,
            "actual_outcome_bucket": None,
        }
        append_jsonl(args.prediction_ledger, prediction_row)
        prediction_row_path = relpath(args.prediction_ledger)
    if prediction_id or prediction_row_path:
        payload["prediction_id"] = prediction_id
        payload["prediction_ledger_mirror"] = prediction_row_path
        write_json(path, payload)
    print(json.dumps({
        "scratch_id": payload["scratch_id"],
        "path": relpath(path),
        "certified": False,
        "excluded_from_calibration": True,
        "can_satisfy_membrane": False,
        "prediction_ledger_mirror": prediction_row_path,
        "prediction_id": prediction_id,
    }, indent=2, sort_keys=True))
    return 0


def cmd_scratch_resolve(args: argparse.Namespace) -> int:
    """Resolve an uncertified scratch forecast and its local prediction row.

    This deliberately stays outside contracts/outcomes/scores. It closes the
    PATTERN-012-style scratch/self-bet loop by updating the local scratch
    artifact and the local prediction ledger mirror when one exists.
    """
    ensure_dirs()
    if not args.prediction_id and not args.scratch_path:
        raise SystemExit("scratch-resolve requires --prediction-id or --scratch-path")
    resolved_at = args.resolved_at or now_iso()
    parse_iso_timestamp(resolved_at, "--resolved-at")
    rows = read_jsonl(args.prediction_ledger)

    scratch_path_value: Path | None = None
    matched_row = find_prediction_row_for_scratch(rows, prediction_id=args.prediction_id)
    if args.scratch_path:
        scratch_path_value = repo_path_from_user_path(args.scratch_path)
    elif matched_row and matched_row.get("prediction_artifact_path"):
        scratch_path_value = repo_path_from_user_path(matched_row["prediction_artifact_path"])
    if scratch_path_value is None:
        raise SystemExit(
            f"could not locate scratch artifact for prediction_id={args.prediction_id!r}"
        )

    payload = read_json(scratch_path_value)
    if not isinstance(payload, dict):
        raise SystemExit(f"scratch artifact must be a JSON object: {scratch_path_value}")
    if payload.get("certified") is True or payload.get("can_satisfy_membrane") is True:
        raise SystemExit("scratch-resolve only handles uncertified scratch artifacts")

    prediction_id = args.prediction_id or payload.get("prediction_id")
    if not matched_row:
        matched_row = find_prediction_row_for_scratch(
            rows,
            prediction_id=prediction_id,
            scratch_path_value=scratch_path_value,
        )
    if not prediction_id and matched_row:
        prediction_id = matched_row.get("prediction_id")

    already_resolved = bool(payload.get("resolved_at"))
    if matched_row and matched_row.get("resolved_at"):
        already_resolved = True
    if already_resolved and not args.allow_reresolve:
        raise SystemExit(
            "scratch forecast already has a resolution; pass --allow-reresolve to overwrite"
        )

    resolution_artifact_path = None
    if args.resolution_artifact:
        resolution_artifact_path = relpath(repo_path_from_user_path(args.resolution_artifact))

    resolution = {
        "resolved_at": resolved_at,
        "actual_outcome": args.actual_outcome,
        "actual_outcome_bucket": args.actual_outcome_bucket,
        "resolution_summary": args.resolution_summary,
        "resolution_artifact_path": resolution_artifact_path,
        "resolution_source": "forecast_pool scratch-resolve",
    }
    payload.update(resolution)
    payload["resolution"] = dict(resolution)
    payload["prediction_id"] = prediction_id
    payload["prediction_ledger_mirror"] = relpath(args.prediction_ledger)
    write_json(scratch_path_value, payload)

    updated_prediction_rows = 0
    if rows:
        for row in rows:
            row_matches = False
            if prediction_id and row.get("prediction_id") == prediction_id:
                row_matches = True
            elif _same_artifact_path(row.get("prediction_artifact_path"), scratch_path_value):
                row_matches = True
            if not row_matches:
                continue
            row.update({
                "resolved_at": resolved_at,
                "actual_outcome": args.actual_outcome,
                "actual_outcome_bucket": args.actual_outcome_bucket,
                "resolution_summary": args.resolution_summary,
                "resolution_artifact_path": resolution_artifact_path,
                "resolution_source": "forecast_pool scratch-resolve",
            })
            updated_prediction_rows += 1
        if updated_prediction_rows:
            write_jsonl(args.prediction_ledger, rows)

    resolution_row = {
        "resolved_at": resolved_at,
        "scratch_id": payload.get("scratch_id"),
        "prediction_id": prediction_id,
        "path": relpath(scratch_path_value),
        "prediction_ledger": relpath(args.prediction_ledger),
        "actual_outcome": args.actual_outcome,
        "actual_outcome_bucket": args.actual_outcome_bucket,
        "resolution_artifact_path": resolution_artifact_path,
        "resolution_summary": args.resolution_summary,
        "updated_prediction_rows": updated_prediction_rows,
        "certified": False,
        "excluded_from_calibration": True,
        "can_satisfy_membrane": False,
    }
    append_jsonl(SCRATCH / "scratch_resolution_ledger.jsonl", resolution_row)
    print(json.dumps(resolution_row, indent=2, sort_keys=True))
    return 0


def collect_score_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(SCORES.glob("*.json")):
        score = read_json(path)
        if not isinstance(score, dict):
            continue
        contract_id = score.get("contract_id") or path.stem
        for row in score.get("scores", []):
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["contract_id"] = contract_id
            item["score_path"] = relpath(path)
            rows.append(item)
    return rows


def bounded_weight_from_brier(mean_brier: float, n: int) -> float:
    raw = 0.25 / max(0.05, mean_brier)
    raw = min(2.0, max(0.25, raw))
    shrink = n / (n + 5.0)
    return round((1.0 - shrink) + shrink * raw, 4)


def effort_prior_from_actuals(actuals: list[float]) -> float | None:
    usable = [float(v) for v in actuals if v and float(v) > 0]
    if len(usable) < 2:
        return None
    # Conservative shrinkage above observed median: use the market to learn
    # directionally, without letting tiny samples set razor-thin budgets.
    return round(max(1.0, statistics.median(usable) * 1.75), 2)


def calibration_payload(min_domain_n: int = 2) -> dict[str, Any]:
    rows = collect_score_rows()
    agent_domain: dict[tuple[str, str], list[dict[str, Any]]] = {}
    domain_rows: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        agent_id = str(row.get("agent_id") or "unknown")
        domain = str(row.get("domain") or "general")
        agent_domain.setdefault((agent_id, domain), []).append(row)
        domain_rows.setdefault(domain, []).append(row)

    agents: dict[str, Any] = {}
    for (agent_id, domain), items in sorted(agent_domain.items()):
        briers = [float(item.get("brier") or 0.0) for item in items]
        cost_errors = [
            float(item["cost_error_agent_minutes"])
            for item in items
            if item.get("cost_error_agent_minutes") is not None
        ]
        actuals = [
            float(item["actual_cost_agent_minutes"])
            for item in items
            if item.get("actual_cost_agent_minutes") is not None
        ]
        expected = [
            float(item["expected_cost_agent_minutes"])
            for item in items
            if item.get("expected_cost_agent_minutes") is not None
        ]
        entry = agents.setdefault(agent_id, {"default_weight": 1.0, "domains": {}, "evidence": {}})
        entry["domains"][domain] = bounded_weight_from_brier(sum(briers) / len(briers), len(items)) if briers else 1.0
        # F8/F10: compute Spearman(field, brier) per (agent, domain) for any optional
        # second-moment field present in ≥4 rows. Empty dict when no channels qualify.
        second_moment = _second_moment_correlations(items)
        entry["evidence"][domain] = {
            "score_rows": len(items),
            "mean_brier": round(sum(briers) / len(briers), 4) if briers else None,
            "mean_cost_error_agent_minutes": round(sum(cost_errors) / len(cost_errors), 4) if cost_errors else None,
            "median_actual_cost_agent_minutes": round(statistics.median(actuals), 4) if actuals else None,
            "median_expected_cost_agent_minutes": round(statistics.median(expected), 4) if expected else None,
            "sample_limited": len(items) < 3,
            "second_moment_channels": second_moment,  # F8/F10 — empty {} unless rows carry premium/decomposed/etc.
        }

    domains: dict[str, Any] = {}
    for domain, items in sorted(domain_rows.items()):
        actuals = [
            float(item["actual_cost_agent_minutes"])
            for item in items
            if item.get("actual_cost_agent_minutes") is not None
        ]
        expected = [
            float(item["expected_cost_agent_minutes"])
            for item in items
            if item.get("expected_cost_agent_minutes") is not None
        ]
        ratios = [
            round(float(item["expected_cost_agent_minutes"]) / float(item["actual_cost_agent_minutes"]), 4)
            for item in items
            if item.get("expected_cost_agent_minutes") is not None
            and item.get("actual_cost_agent_minutes") is not None
            and float(item["actual_cost_agent_minutes"]) > 0
        ]
        domains[domain] = {
            "score_rows": len(items),
            "expected_cost_agent_minutes_prior": effort_prior_from_actuals(actuals)
            if len(items) >= min_domain_n
            else None,
            "median_actual_cost_agent_minutes": round(statistics.median(actuals), 4) if actuals else None,
            "median_expected_cost_agent_minutes": round(statistics.median(expected), 4) if expected else None,
            "expected_over_actual_ratios": ratios,
            "median_expected_over_actual": round(statistics.median(ratios), 4) if ratios else None,
            "sample_limited": len(items) < 3,
        }

    return {
        "generated_at": now_iso(),
        "mode": "explicit_calibration_from_score_artifacts",
        "score_rows": len(rows),
        "default_weight": 1.0,
        "agents": agents,
        "domains": domains,
        "own_work_signed_bias": signed_calibration_bias(),
        "semantics": {
            "hidden_auto_mutation_during_score": False,
            "requires_explicit_calibrate_write": True,
            "weights_are_domain_specific": True,
            "effort_priors_are_advisory_not_vetoes": True,
            "small_sample_shrinkage": True,
        },
    }


def cmd_calibrate(args: argparse.Namespace) -> int:
    ensure_dirs()
    payload = calibration_payload(args.min_domain_n)
    if args.write:
        write_json(CALIBRATION_SUMMARY, payload)
        payload["summary_artifact_path"] = relpath(CALIBRATION_SUMMARY)
    if args.write_weights:
        write_json(WEIGHTS, payload)
        payload["weights_artifact_path"] = relpath(WEIGHTS)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_externalities(args: argparse.Namespace) -> int:
    """Automated positive/negative-externality rollup over all scores.

    Added 2026-05-16. The per-score `externality_audit` + contract
    `externality_hypotheses` + outcome externality tags were captured
    but NEVER rolled up (the only artifact was a stale 2-day-old manual
    JSON, no generator). This harvests that stranded signal into a
    fresh reproducible artifact so the market's positive externalities
    (calibration, failure-mode hit-rate, externality realisation) feed
    back instead of sitting inert across hundreds of score files.
    """
    ensure_dirs()
    by_agent: dict[str, dict[str, Any]] = {}
    pos_tags: dict[str, int] = {}
    neg_tags: dict[str, int] = {}
    contracts_with_hypotheses = 0
    scored = 0
    scored_contract_ids: set[str] = set()
    score_rows = 0
    for sp in sorted(SCORES.glob("*.json")):
        sc = read_json(sp)
        if not isinstance(sc, dict):
            continue
        scored += 1
        contract_id = str(sc.get("contract_id") or sp.stem)
        scored_contract_ids.add(contract_id)
        outcome = sc.get("outcome") or {}
        for t in outcome.get("externality_tags") or []:
            pos_tags[str(t)] = pos_tags.get(str(t), 0) + 1
        for t in outcome.get("negative_externality_tags") or []:
            neg_tags[str(t)] = neg_tags.get(str(t), 0) + 1
        cpath = contract_path(contract_id)
        if cpath.exists():
            c = read_json(cpath)
            if isinstance(c, dict) and c.get("externality_hypotheses"):
                contracts_with_hypotheses += 1
        for row in sc.get("scores") or []:
            score_rows += 1
            a = str(row.get("agent_id"))
            agg = by_agent.setdefault(a, {
                "n": 0, "brier_sum": 0.0, "log_sum": 0.0,
                "fm_top1_hits": 0, "fm_evaluable": 0, "realized_mass_sum": 0.0})
            agg["n"] += 1
            if row.get("brier") is not None:
                agg["brier_sum"] += float(row["brier"])
            if row.get("log_score") is not None:
                agg["log_sum"] += float(row["log_score"])
            ea = row.get("externality_audit") or {}
            if ea.get("realized_failure_mode_ids_available"):
                agg["fm_evaluable"] += 1
                if ea.get("failure_mode_top1_hit") is True:
                    agg["fm_top1_hits"] += 1
                if ea.get("failure_mode_realized_mass") is not None:
                    agg["realized_mass_sum"] += float(ea["failure_mode_realized_mass"])
    agents = {}
    for a, g in by_agent.items():
        n = max(g["n"], 1)
        fe = max(g["fm_evaluable"], 1)
        agents[a] = {
            "n_scored": g["n"],
            "mean_brier": round(g["brier_sum"] / n, 6),
            "mean_log_score": round(g["log_sum"] / n, 6),
            "failure_mode_top1_hit_rate": round(g["fm_top1_hits"] / fe, 4),
            "failure_mode_evaluable": g["fm_evaluable"],
            "mean_realized_failure_mass": round(g["realized_mass_sum"] / fe, 6),
        }

    contracts: dict[str, dict[str, Any]] = {}
    for path in sorted(CONTRACTS.glob("*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            contracts[str(payload.get("contract_id") or path.stem)] = payload

    forecasts: list[dict[str, Any]] = []
    for path in sorted(FORECASTS.glob("*/*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            row = dict(payload)
            row["forecast_path"] = relpath(path)
            forecasts.append(row)

    outcomes: dict[str, dict[str, Any]] = {}
    for path in sorted(OUTCOMES.glob("*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            outcomes[str(payload.get("contract_id") or path.stem)] = payload

    forecasts_by_contract: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for forecast in forecasts:
        forecasts_by_contract[str(forecast.get("contract_id"))].append(forecast)

    forecast_count_bins = Counter()
    p_success_spreads: list[float] = []
    for cid in contracts:
        contract_forecasts = forecasts_by_contract.get(cid, [])
        count = len(contract_forecasts)
        if count == 0:
            forecast_count_bins["0"] += 1
        elif count == 1:
            forecast_count_bins["1"] += 1
        elif count == 2:
            forecast_count_bins["2"] += 1
        else:
            forecast_count_bins["3+"] += 1
        ps = [
            float(forecast["p_success"])
            for forecast in contract_forecasts
            if forecast.get("p_success") is not None
        ]
        if len(ps) >= 2:
            p_success_spreads.append(max(ps) - min(ps))
    update_files = list(FORECAST_UPDATES.glob("**/*.json"))

    raw_agent_counts = Counter(str(forecast.get("agent_id")) for forecast in forecasts)
    noncanonical_agent_counts = Counter({
        agent_id: count
        for agent_id, count in raw_agent_counts.items()
        if agent_id not in CANONICAL_AGENT_IDS
    })
    post_binding_noncanonical = Counter()
    alias_view = Counter()
    ambiguous_alias = Counter()
    for forecast in forecasts:
        raw_agent = str(forecast.get("agent_id"))
        canonical = canonical_agent_id(raw_agent)
        if canonical:
            alias_view[canonical] += 1
        else:
            ambiguous_alias[raw_agent] += 1
        forecasted_at = parse_optional_iso(forecast.get("forecasted_at"))
        if (
            forecasted_at
            and forecasted_at >= AGENT_ID_BINDING_DATE
            and raw_agent not in CANONICAL_AGENT_IDS
        ):
            post_binding_noncanonical[raw_agent] += 1

    domain_counts = Counter(str(forecast.get("domain") or "unknown") for forecast in forecasts)
    domain_family_counts = Counter(domain_family(domain) for domain in domain_counts.elements())
    alias_families: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for domain, count in domain_counts.items():
        family = domain_family(domain)
        if family != domain:
            alias_families[family].append((domain, count))

    entropies: list[float] = []
    high_entropy = 0
    high_entropy_without_specifics = 0
    forecasts_with_specifics = 0
    forecasts_with_action_change = 0
    for forecast in forecasts:
        dist = forecast.get("failure_mode_distribution") or {}
        if not isinstance(dist, dict) or not dist:
            continue
        entropy = normalized_entropy(dist)
        if entropy is None:
            continue
        entropies.append(entropy)
        has_specifics = bool(forecast.get("specific_failure_mode_ids"))
        has_action_change = bool(forecast.get("action_change_recommendation"))
        forecasts_with_specifics += int(has_specifics)
        forecasts_with_action_change += int(has_action_change)
        if entropy >= 0.9:
            high_entropy += 1
            if not (has_specifics or has_action_change):
                high_entropy_without_specifics += 1

    resolved_contract_ids = set(outcomes)
    unscored_resolved = sorted(resolved_contract_ids - scored_contract_ids)
    unresolved_contracts = sorted(set(contracts) - resolved_contract_ids)
    prediction_rows = read_jsonl(getattr(args, "prediction_ledger", DEFAULT_PREDICTION_LEDGER))
    resolved_prediction_rows = [
        row for row in prediction_rows
        if row.get("resolved_at")
        or row.get("actual_outcome")
        or row.get("resolution")
    ]
    brier_prediction_rows = [
        row for row in prediction_rows
        if row.get("brier") is not None
        or row.get("brier_realized") is not None
        or "Brier" in str(row.get("calibration_delta_odds") or row.get("calibration_delta") or "")
    ]
    role_id = "forecasting_agent"
    channel_dir = channel_role_dir(role_id)
    inbox_dir = channel_inbox_dir(role_id)
    claims_dir = channel_claims_dir(role_id)
    responses_dir = channel_responses_dir(role_id)
    channel_messages: list[dict[str, Any]] = []
    for path in sorted(inbox_dir.glob("*.json")) if inbox_dir.exists() else []:
        message = read_json(path, {})
        if isinstance(message, dict):
            item = dict(message)
            item["_path"] = relpath(path)
            channel_messages.append(item)
    claim_ids = {path.stem for path in claims_dir.glob("*.json")} if claims_dir.exists() else set()
    response_ids = {path.stem for path in responses_dir.glob("*.json")} if responses_dir.exists() else set()
    message_status_counts = Counter(str(message.get("status") or "missing") for message in channel_messages)
    obligation_counts = Counter(str(message.get("obligation_state") or "missing") for message in channel_messages)
    open_messages = [
        message for message in channel_messages
        if message.get("status") != "closed"
        and message.get("obligation_state") not in {"fulfilled", "refused", "expired"}
    ]
    claimed_without_response = [
        message for message in channel_messages
        if str(message.get("message_id")) in claim_ids
        and str(message.get("message_id")) not in response_ids
    ]
    open_resolved_messages = []
    for message in open_messages:
        metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        contract_id = str(metadata.get("contract_id") or "")
        if contract_id and contract_id in outcomes:
            open_resolved_messages.append({
                "message_id": message.get("message_id"),
                "contract_id": contract_id,
                "path": message.get("_path"),
            })
    payload = {
        "generated_at": now_iso(),
        "mode": "externalities_rollup",
        "scored_contracts": scored,
        "score_rows": score_rows,
        "contracts_with_externality_hypotheses": contracts_with_hypotheses,
        "agents": agents,
        "positive_externality_tags": dict(sorted(pos_tags.items(), key=lambda kv: -kv[1])),
        "negative_externality_tags": dict(sorted(neg_tags.items(), key=lambda kv: -kv[1])),
        "market_depth": {
            "contracts": len(contracts),
            "forecasts": len(forecasts),
            "forecast_count_bins_by_contract": dict(sorted(forecast_count_bins.items())),
            "mean_forecasts_per_contract": (
                None if not contracts else round(len(forecasts) / len(contracts), 4)
            ),
            "contracts_with_2plus_forecasts": sum(
                1 for cid in contracts if len(forecasts_by_contract.get(cid, [])) >= 2
            ),
            "median_p_success_spread_when_2plus": (
                None if not p_success_spreads else round(statistics.median(p_success_spreads), 4)
            ),
            "mean_p_success_spread_when_2plus": (
                None if not p_success_spreads else round(statistics.mean(p_success_spreads), 4)
            ),
            "forecast_update_files": len(update_files),
            "contracts_with_forecast_updates": len({
                path.relative_to(FORECAST_UPDATES).parts[0]
                for path in update_files
                if len(path.relative_to(FORECAST_UPDATES).parts) >= 3
            }),
        },
        "identity_hygiene": {
            "unique_agent_ids": len(raw_agent_counts),
            "top_agent_ids": raw_agent_counts.most_common(20),
            "noncanonical_agent_id_count": len(noncanonical_agent_counts),
            "noncanonical_forecast_rows": sum(noncanonical_agent_counts.values()),
            "noncanonical_top20": noncanonical_agent_counts.most_common(20),
            "post_binding_noncanonical_rows": sum(post_binding_noncanonical.values()),
            "post_binding_noncanonical_top20": post_binding_noncanonical.most_common(20),
            "read_time_alias_view": dict(sorted(alias_view.items())),
            "ambiguous_alias_top20": ambiguous_alias.most_common(20),
        },
        "domain_hygiene": {
            "unique_forecast_domains": len(domain_counts),
            "top_forecast_domains": domain_counts.most_common(20),
            "domain_family_counts": domain_family_counts.most_common(20),
            "alias_family_top20": {
                family: sorted(items, key=lambda item: (-item[1], item[0]))[:12]
                for family, items in sorted(alias_families.items())
                if len(items) > 1
            },
        },
        "failure_mode_quality": {
            "forecasts_with_failure_distribution": len(entropies),
            "median_normalized_entropy": (
                None if not entropies else round(statistics.median(entropies), 4)
            ),
            "mean_normalized_entropy": (
                None if not entropies else round(statistics.mean(entropies), 4)
            ),
            "high_entropy_failure_distributions": high_entropy,
            "high_entropy_fraction": (
                None if not entropies else round(high_entropy / len(entropies), 4)
            ),
            "high_entropy_without_specific_ids_or_action_change": high_entropy_without_specifics,
            "forecasts_with_specific_failure_mode_ids": forecasts_with_specifics,
            "forecasts_with_action_change_recommendation": forecasts_with_action_change,
        },
        "causal_externality_capture": {
            "contracts_with_counterfactual_fields": sum(
                1 for contract in contracts.values()
                if contract.get("baseline_action") or contract.get("counterfactual_action")
            ),
            "outcomes_with_realized_failure_mode_ids": sum(
                1 for outcome in outcomes.values() if outcome.get("realized_failure_mode_ids")
            ),
            "outcomes_with_failure_mode_preconditioner_used": sum(
                1 for outcome in outcomes.values()
                if outcome.get("failure_mode_preconditioner_used") is True
            ),
            "outcomes_with_decision_changed_bool": sum(
                1 for outcome in outcomes.values() if outcome.get("decision_changed_bool") is not None
            ),
            "outcomes_with_changed_by_forecast_ids": sum(
                1 for outcome in outcomes.values() if outcome.get("changed_by_forecast_ids")
            ),
            "outcomes_with_counterfactual_value_bucket": sum(
                1 for outcome in outcomes.values() if outcome.get("counterfactual_value_bucket")
            ),
            "outcomes_with_old_or_new_next_action": sum(
                1 for outcome in outcomes.values()
                if outcome.get("old_next_action") or outcome.get("new_next_action")
            ),
        },
        "calibration_debt": {
            "resolved_contracts": len(resolved_contract_ids),
            "scored_contracts": len(scored_contract_ids),
            "resolved_unscored_contracts": len(unscored_resolved),
            "resolved_unscored_contract_samples": unscored_resolved[:20],
            "unresolved_contracts": len(unresolved_contracts),
            "unresolved_contract_samples": unresolved_contracts[:20],
        },
        "prediction_ledger_coverage": {
            "path": relpath(getattr(args, "prediction_ledger", DEFAULT_PREDICTION_LEDGER)),
            "rows": len(prediction_rows),
            "resolved_rows": len(resolved_prediction_rows),
            "brier_like_scored_rows": len(brier_prediction_rows),
            "coverage_note": (
                "PATTERN-012 rows are useful lightweight prediction evidence, "
                "but their scored coverage must be reported separately from GP-230."
            ),
        },
        "transport_health": {
            "channel_dir": relpath(channel_dir),
            "inbox_messages": len(channel_messages),
            "claim_files": len(claim_ids),
            "response_files": len(response_ids),
            "status_counts": dict(sorted(message_status_counts.items())),
            "obligation_state_counts": dict(sorted(obligation_counts.items())),
            "open_messages": len(open_messages),
            "claimed_without_response": len(claimed_without_response),
            "claimed_without_response_samples": [
                {"message_id": message.get("message_id"), "path": message.get("_path")}
                for message in claimed_without_response[:20]
            ],
            "open_messages_for_resolved_contracts": len(open_resolved_messages),
            "open_messages_for_resolved_contract_samples": open_resolved_messages[:20],
            "architecture_note": (
                "This is the pub/sub transport health surface. RD pre-tick should "
                "consume aggregate/status artifacts, not raw channel chatter."
            ),
        },
    }
    if args.write:
        out = ROOT / "externalities_rollup.json"
        write_json(out, payload)
        payload["artifact_path"] = relpath(out)
        append_market_event(
            "externalities_rollup",
            scored_contracts=scored, agents=len(agents))
    print(json.dumps(payload, indent=2))
    return 0


def calibration_status() -> dict[str, Any]:
    score_paths = sorted(SCORES.glob("*.json"))
    latest_score_mtime = max((path.stat().st_mtime for path in score_paths), default=None)
    summary_mtime = CALIBRATION_SUMMARY.stat().st_mtime if CALIBRATION_SUMMARY.exists() else None
    summary = read_json(CALIBRATION_SUMMARY, {}) if CALIBRATION_SUMMARY.exists() else {}
    domains = summary.get("domains") if isinstance(summary, dict) else {}
    domain_brief = []
    if isinstance(domains, dict):
        for domain, entry in sorted(domains.items()):
            if not isinstance(entry, dict):
                continue
            ratio = entry.get("median_expected_over_actual")
            prior = entry.get("expected_cost_agent_minutes_prior")
            overestimated = bool(ratio is not None and float(ratio) >= 3.0)
            domain_brief.append({
                "domain": domain,
                "score_rows": entry.get("score_rows"),
                "expected_cost_agent_minutes_prior": prior,
                "median_expected_over_actual": ratio,
                "sample_limited": entry.get("sample_limited"),
                "effort_overestimated": overestimated,
            })
    return {
        "summary_path": relpath(CALIBRATION_SUMMARY),
        "weights_path": relpath(WEIGHTS),
        "summary_exists": CALIBRATION_SUMMARY.exists(),
        "weights_exists": WEIGHTS.exists(),
        "score_count": len(score_paths),
        "stale": bool(latest_score_mtime and (summary_mtime is None or summary_mtime < latest_score_mtime)),
        "score_rows_in_summary": summary.get("score_rows") if isinstance(summary, dict) else None,
        "domain_effort_priors": domain_brief,
        "rd_consumption_rule": (
            "use GP-230 for replay/Lean batches, GNN/GPU/training gates, public claims, "
            "or branch choices with real opportunity cost; use raw PL plus GP-233 for cheap saved audits"
        ),
    }


def status_rows(contract_ids: list[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in contract_ids:
        if cid.startswith("scratch_") and not contract_path(cid).exists():
            try:
                scratch, scratch_artifact_path = load_scratch_contract(cid)
            except SystemExit as exc:
                append_market_event(
                    "malformed_scratch_skipped",
                    contract_id=cid, error=str(exc))
                rows.append({
                    "contract_id": cid,
                    "malformed": True,
                    "next_action": "malformed_scratch_skipped",
                    "error": str(exc),
                    "artifact_paths": {"contract": relpath(SCRATCH / "scratch_ledger.jsonl")},
                    "question": "",
                })
                continue
            decision_rows = decision_use_rows(cid)
            rows.append({
                "contract_id": cid,
                "scratch_contract": True,
                "next_action": "scratch_only_not_gp230",
                "question": scratch.get("question"),
                "owner": scratch.get("owner"),
                "p_success": scratch.get("p_success"),
                "excluded_from_calibration": bool(scratch.get("excluded_from_calibration")),
                "can_satisfy_membrane": bool(scratch.get("can_satisfy_membrane")),
                "decision_use": {
                    "row_count": len(decision_rows),
                    "latest": decision_rows[-1] if decision_rows else None,
                },
                "artifact_paths": {"contract": relpath(scratch_artifact_path)},
            })
            continue
        # Resilience (2026-05-16): a single malformed/stale contract must
        # NOT abort the whole scan / market re-derive / warm-consumer path.
        # Skip-and-flag it (visibly tracked, never silently dropped) and
        # keep processing valid work. Mirrors cmd_warm_daemon_once.
        try:
            contract = load_contract(cid)
        except SystemExit as exc:
            append_market_event(
                "malformed_contract_skipped",
                contract_id=cid, error=str(exc))
            rows.append({
                "contract_id": cid,
                "malformed": True,
                "next_action": "malformed_skipped",
                "error": str(exc),
                "artifact_paths": {"contract": relpath(contract_path(cid))},
                "question": "",
            })
            continue
        forecast_error = None
        try:
            forecast_history = load_forecasts(cid)
            forecasts = latest_forecasts_by_agent(forecast_history)
        except SystemExit as exc:
            forecast_history = []
            forecasts = []
            forecast_error = str(exc)
            append_market_event(
                "malformed_forecast_skipped",
                contract_id=cid, error=forecast_error)
        outcome = read_json(outcome_path(cid))
        aggregate_payload = read_json(aggregate_path(cid))
        score_payload = read_json(score_path(cid))
        if forecast_error:
            next_action = "malformed_forecast_skipped"
        elif outcome and outcome.get("voided"):
            next_action = "voided_no_score"
        elif outcome and not forecasts:
            next_action = "resolved_without_forecasts"
        elif not forecasts:
            next_action = "await_forecasts"
        elif not aggregate_payload:
            next_action = "aggregate_when_rd_releases"
        elif not outcome:
            next_action = "await_objective_outcome"
        elif not score_payload:
            next_action = "score"
        else:
            next_action = "closed"
        rows.append({
            "contract_id": cid,
            "layer": contract.get("layer"),
            "task_type": contract.get("task_type"),
            "forecast_count": len(forecasts),
            "forecast_history_count": len(forecast_history),
            "forecast_error": forecast_error,
            "has_aggregate": bool(aggregate_payload),
            "resolved": bool(outcome),
            "has_score": bool(score_payload),
            "next_action": next_action,
            "artifact_paths": {
                "contract": relpath(contract_path(cid)),
                "forecast_dir": relpath(forecast_dir(cid)),
                "aggregate": relpath(aggregate_path(cid)),
                "outcome": relpath(outcome_path(cid)),
                "score": relpath(score_path(cid)),
            },
            "question": (contract.get("question") or "")[:120],
        })
    return rows


def scan_prediction_ledger(path: Path, limit: int) -> dict[str, Any]:
    rows = read_jsonl(path)
    resolutions = {row.get("resolves") for row in rows if row.get("resolves")}
    predictions = [
        row for row in rows
        if row.get("prediction_id") and not row.get("resolves")
    ]
    unresolved = [
        row for row in predictions
        if not row.get("resolved_at") and row.get("prediction_id") not in resolutions
    ]
    recent = unresolved[-limit:] if limit > 0 else []
    return {
        "path": relpath(path),
        "exists": path.exists(),
        "total_prediction_rows": len(predictions),
        "unresolved_count": len(unresolved),
        "recent_unresolved": [
            {
                "prediction_id": row.get("prediction_id"),
                "predicted_at": row.get("predicted_at"),
                "tier": row.get("tier"),
                "substrate": row.get("substrate"),
                "question": (row.get("question") or "")[:160],
                "prediction_artifact_path": row.get("prediction_artifact_path"),
            }
            for row in recent
        ],
    }


def top_failure_modes(distribution: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode, value in distribution.items():
        try:
            p = float(value)
        except (TypeError, ValueError):
            continue
        rows.append({"mode": str(mode), "p": p})
    return sorted(rows, key=lambda row: (-row["p"], row["mode"]))[:limit]


def allocation_recommendation(
    *,
    contract: dict[str, Any],
    aggregate_summary: dict[str, Any],
    latest_forecasts: list[dict[str, Any]],
    lifecycle_state: str,
) -> dict[str, Any]:
    """Convert sealed prices into a small RD allocation action.

    This is intentionally a routing hint, not an executor. The RD still owns
    the scientific decision, but should not have to re-derive the market read.
    """
    if lifecycle_state in {"malformed", "malformed_forecast"}:
        return {
            "action": "ask_another_independent_agent",
            "reason": "market artifacts malformed; repair or replace pricing input first",
            "voi_proxy": None,
        }
    if lifecycle_state == "forecast_requested":
        return {
            "action": "ask_another_independent_agent",
            "reason": "no usable forecast aggregate yet",
            "voi_proxy": None,
        }
    p_success = aggregate_summary.get("p_success")
    expected_value = aggregate_summary.get("expected_value")
    expected_cost = aggregate_summary.get("expected_cost_agent_minutes")
    information_value = float(contract.get("information_value") or 0.0)
    latest_ps: list[float] = []
    for forecast in latest_forecasts:
        try:
            latest_ps.append(float(forecast.get("p_success")))
        except (TypeError, ValueError):
            continue
    spread = max(latest_ps) - min(latest_ps) if len(latest_ps) >= 2 else 0.0
    try:
        p = float(p_success)
    except (TypeError, ValueError):
        return {
            "action": "ask_another_independent_agent",
            "reason": "aggregate lacks p_success",
            "voi_proxy": None,
        }
    try:
        ev = float(expected_value)
    except (TypeError, ValueError):
        ev = None
    uncertainty = p * (1.0 - p)
    voi_proxy = round(information_value + uncertainty + spread, 4)
    top_modes = aggregate_summary.get("top_failure_modes") or []
    top_mode_mass = float(top_modes[0]["p"]) if top_modes else 0.0
    if len(latest_ps) < 2:
        return {
            "action": "ask_another_independent_agent",
            "reason": "fewer than two independent usable forecasts",
            "voi_proxy": voi_proxy,
            "p_success": p,
            "forecast_spread": spread,
        }
    if spread >= 0.25:
        return {
            "action": "ask_another_independent_agent",
            "reason": "large cross-forecaster disagreement",
            "voi_proxy": voi_proxy,
            "p_success": p,
            "forecast_spread": round(spread, 4),
        }
    if ev is not None and ev > 0 and p >= 0.65:
        return {
            "action": "run_now",
            "reason": "positive expected value and high success probability",
            "voi_proxy": voi_proxy,
            "p_success": p,
            "expected_value": ev,
            "forecast_spread": round(spread, 4),
        }
    if 0.35 <= p < 0.65 and (top_mode_mass >= 0.25 or voi_proxy >= 0.45):
        return {
            "action": "split_contract",
            "reason": "uncertainty is concentrated enough to price a smaller branch",
            "voi_proxy": voi_proxy,
            "p_success": p,
            "top_failure_mode": top_modes[0] if top_modes else None,
            "forecast_spread": round(spread, 4),
        }
    if ev is not None and ev < 0 and p < 0.2 and information_value <= 0:
        return {
            "action": "kill_branch",
            "reason": "low probability, negative expected value, and no declared information value",
            "voi_proxy": voi_proxy,
            "p_success": p,
            "expected_value": ev,
        }
    if ev is not None and ev < 0:
        return {
            "action": "defer",
            "reason": "negative expected value; keep as later option unless new evidence arrives",
            "voi_proxy": voi_proxy,
            "p_success": p,
            "expected_value": ev,
            "expected_cost_agent_minutes": expected_cost,
        }
    return {
        "action": "defer",
        "reason": "market is not decisive enough to run now; wait for sharper evidence or smaller split",
        "voi_proxy": voi_proxy,
        "p_success": p,
        "expected_value": ev,
        "forecast_spread": round(spread, 4),
    }


def lifecycle_state_from_status(row: dict[str, Any]) -> dict[str, Any]:
    next_action = str(row.get("next_action") or "unknown")
    mapping = {
        "malformed_skipped": ("malformed", ["repair_contract_json"]),
        "malformed_forecast_skipped": ("malformed_forecast", ["repair_forecast_json"]),
        "resolved_without_forecasts": ("resolved_without_forecasts", ["forecast_backfill_or_void_no_score"]),
        "await_forecasts": ("forecast_requested", ["forecast_fulfilled_or_expired"]),
        "aggregate_when_rd_releases": ("forecast_fulfilled", ["aggregate_ready"]),
        "await_objective_outcome": ("aggregate_ready", ["pre_tick_consumed", "resolved"]),
        "voided_no_score": ("voided", []),
        "score": ("resolved_unscored", ["resolved_scored"]),
        "closed": ("resolved_scored", []),
    }
    state, missing = mapping.get(next_action, ("unknown", []))
    return {
        "state": state,
        "next_action": next_action,
        "missing_obligations": missing,
        "closed": state in {"resolved_scored", "voided"},
        "blocks_post_tick_close": state in {"resolved_unscored", "resolved_without_forecasts"},
    }


def decision_use_rows(contract_id: str | None = None) -> list[dict[str, Any]]:
    rows = read_jsonl(DECISION_USE_LEDGER)
    if contract_id is None:
        return rows
    return [row for row in rows if str(row.get("contract_id") or "") == contract_id]


def compact_aggregate_summary(aggregate_payload: Any) -> dict[str, Any]:
    if not isinstance(aggregate_payload, dict) or not aggregate_payload:
        return {"exists": False}
    aggregate = aggregate_payload.get("aggregate")
    if not isinstance(aggregate, dict):
        aggregate = {}
    return {
        "exists": True,
        "aggregated_at": aggregate_payload.get("aggregated_at"),
        "forecast_count": aggregate_payload.get("forecast_count"),
        "forecast_history_count": aggregate_payload.get("forecast_history_count"),
        "participants": aggregate_payload.get("participants") or [],
        "routing_hint": aggregate_payload.get("routing_hint"),
        "allocation_recommendation": aggregate_payload.get("allocation_recommendation"),
        "p_success": aggregate.get("p_success"),
        "expected_cost_agent_minutes": aggregate.get("expected_cost_agent_minutes"),
        "p_regression": aggregate.get("p_regression"),
        "p_dependency_issue": aggregate.get("p_dependency_issue"),
        "p_needs_new_lemma": aggregate.get("p_needs_new_lemma"),
        "expected_value": aggregate.get("expected_value"),
        "top_failure_modes": top_failure_modes(
            aggregate.get("failure_mode_distribution") or {}
        ),
    }


def independence_group(agent_id: Any) -> str:
    raw = str(agent_id or "unknown").strip() or "unknown"
    canonical = canonical_agent_id(raw)
    if canonical in {"codex", "codex_rd"}:
        return "independent_agent_family:codex"
    if canonical in {"claude", "claude_rd"}:
        return "independent_agent_family:claude"
    return f"legacy_or_named_agent:{canonical or raw}"


def effective_independence_for_forecasts(forecasts: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    raw_ids = []
    for row in forecasts:
        raw = str(row.get("agent_id") or "unknown")
        raw_ids.append(raw)
        groups[independence_group(raw)].append(raw)
    return {
        "latest_forecast_count": len(forecasts),
        "raw_agent_ids": raw_ids,
        "independence_groups": [
            {"group": group, "raw_agent_ids": sorted(set(ids))}
            for group, ids in sorted(groups.items())
        ],
        "effective_n": len(groups),
        "meets_two_independent_agents": len(groups) >= 2,
        "note": (
            "Effective-N is a conservative read-time lower bound. Multiple "
            "aliases in one provider/runtime family count as one independent "
            "agent family for routing."
        ),
    }


def contract_read_model(contract_id: str, status_row: dict[str, Any] | None = None) -> dict[str, Any]:
    if status_row is None:
        status_row = status_rows([contract_id])[0]
    lifecycle = lifecycle_state_from_status(status_row)
    if status_row.get("malformed"):
        return {
            "contract_id": contract_id,
            "generated_at": now_iso(),
            "malformed": True,
            "lifecycle": lifecycle,
            "artifact_paths": status_row.get("artifact_paths") or {},
            "error": status_row.get("error"),
        }
    contract = load_contract(contract_id)
    aggregate_payload = read_json(aggregate_path(contract_id), {})
    outcome_payload = read_json(outcome_path(contract_id), {})
    score_payload = read_json(score_path(contract_id), {})
    try:
        forecast_history = load_forecasts(contract_id)
        latest = latest_forecasts_by_agent(forecast_history)
    except SystemExit as exc:
        forecast_history = []
        latest = []
        lifecycle.setdefault("warnings", []).append(str(exc))
    decision_rows = decision_use_rows(contract_id)
    aggregate_summary = compact_aggregate_summary(aggregate_payload)
    latest_decision_use = decision_rows[-1] if decision_rows else None
    allocation = aggregate_summary.get("allocation_recommendation")
    if not isinstance(allocation, dict):
        allocation = allocation_recommendation(
            contract=contract,
            aggregate_summary=aggregate_summary,
            latest_forecasts=latest,
            lifecycle_state=lifecycle["state"],
        )
    independence = effective_independence_for_forecasts(latest)
    return {
        "contract_id": contract_id,
        "generated_at": now_iso(),
        "contract": {
            "created_at": contract.get("created_at"),
            "created_by": contract.get("created_by"),
            "layer": contract.get("layer"),
            "task_type": contract.get("task_type"),
            "question": contract.get("question"),
            "horizon": contract.get("horizon"),
            "objective_resolver": contract.get("objective_resolver"),
            "success_threshold": contract.get("success_threshold"),
            "budget_agent_minutes": contract.get("budget_agent_minutes"),
            "consumes_surfaced": contract.get("consumes_surfaced"),
        },
        "lifecycle": lifecycle,
        "forecasts": {
            "latest_count": len(latest),
            "history_count": len(forecast_history),
            "latest": [
                {
                    "agent_id": row.get("agent_id"),
                    "canonical_agent_id": canonical_agent_id(row.get("agent_id")),
                    "forecasted_at": row.get("forecasted_at"),
                    "domain": row.get("domain"),
                    "p_success": row.get("p_success"),
                    "expected_cost_agent_minutes": row.get("expected_cost_agent_minutes"),
                    "rationale_short": row.get("rationale_short"),
                    "specific_failure_mode_ids": row.get("specific_failure_mode_ids") or [],
                    "action_change_recommendation": row.get("action_change_recommendation"),
                    "artifact_path": row.get("forecast_artifact_path"),
                }
                for row in latest
            ],
        },
        "aggregate": aggregate_summary,
        "outcome": {
            "exists": isinstance(outcome_payload, dict) and bool(outcome_payload),
            "resolved_at": outcome_payload.get("resolved_at") if isinstance(outcome_payload, dict) else None,
            "success_bool": outcome_payload.get("success_bool") if isinstance(outcome_payload, dict) else None,
            "voided": outcome_payload.get("voided") if isinstance(outcome_payload, dict) else None,
            "actual_cost_agent_minutes": outcome_payload.get("actual_cost_agent_minutes") if isinstance(outcome_payload, dict) else None,
            "decision_changed_bool": outcome_payload.get("decision_changed_bool") if isinstance(outcome_payload, dict) else None,
            "changed_by_forecast_ids": outcome_payload.get("changed_by_forecast_ids") if isinstance(outcome_payload, dict) else [],
        },
        "score": {
            "exists": isinstance(score_payload, dict) and bool(score_payload),
            "scored_at": score_payload.get("scored_at") if isinstance(score_payload, dict) else None,
            "mean_brier": score_payload.get("mean_brier") if isinstance(score_payload, dict) else None,
            "score_rows": len(score_payload.get("scores") or []) if isinstance(score_payload, dict) else 0,
        },
        "decision_use": {
            "ledger_path": relpath(DECISION_USE_LEDGER),
            "row_count": len(decision_rows),
            "latest": latest_decision_use,
        },
        "effective_independence": independence,
        "rd_fast_read": {
            "next_action": lifecycle["next_action"],
            "routing_hint": aggregate_summary.get("routing_hint"),
            "allocation_recommendation": allocation,
            "p_success": aggregate_summary.get("p_success"),
            "expected_cost_agent_minutes": aggregate_summary.get("expected_cost_agent_minutes"),
            "top_failure_modes": aggregate_summary.get("top_failure_modes") or [],
            "effective_n": independence["effective_n"],
            "meets_two_independent_agents": independence["meets_two_independent_agents"],
            "latest_decision_use": latest_decision_use,
        },
        "artifact_paths": {
            "contract": relpath(contract_path(contract_id)),
            "aggregate": relpath(aggregate_path(contract_id)),
            "outcome": relpath(outcome_path(contract_id)),
            "score": relpath(score_path(contract_id)),
            "market_state": relpath(MARKET_STATE_CONTRACTS / f"{contract_id}.json"),
        },
    }


def transport_health(channel_dir: Path = DEFAULT_FORECASTING_CHANNEL) -> dict[str, Any]:
    inbox = channel_dir / "inbox"
    claims = channel_dir / "claims"
    responses = channel_dir / "responses"
    messages: list[dict[str, Any]] = []
    for path in sorted(inbox.glob("*.json")) if inbox.exists() else []:
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        messages.append({
            "message_id": str(payload.get("message_id") or path.stem),
            "contract_id": str(metadata.get("contract_id") or payload.get("contract_id") or ""),
            "status": str(payload.get("status") or "missing"),
            "obligation_state": str(payload.get("obligation_state") or "missing"),
            "path": relpath(path),
        })
    claim_ids = {path.stem for path in claims.glob("*.json")} if claims.exists() else set()
    response_ids = {path.stem for path in responses.glob("*.json")} if responses.exists() else set()
    resolved_ids = {path.stem for path in OUTCOMES.glob("*.json")}
    aggregate_ids = {path.stem for path in AGGREGATES.glob("*.json")}
    open_messages = [
        message for message in messages
        if message["status"] != "closed"
        and message["obligation_state"] not in {"fulfilled", "refused", "expired"}
    ]
    claimed_without_response = [
        message for message in messages
        if message["message_id"] in claim_ids
        and message["message_id"] not in response_ids
    ]
    open_resolved = [
        message for message in open_messages
        if message["contract_id"] and message["contract_id"] in resolved_ids
    ]
    fulfilled_missing_aggregate = [
        message for message in messages
        if message["contract_id"]
        and message["contract_id"] not in aggregate_ids
        and message["obligation_state"] == "fulfilled"
    ]
    return {
        "channel_dir": relpath(channel_dir),
        "inbox_messages": len(messages),
        "claim_files": len(claim_ids),
        "response_files": len(response_ids),
        "status_counts": dict(sorted(Counter(m["status"] for m in messages).items())),
        "obligation_state_counts": dict(sorted(Counter(m["obligation_state"] for m in messages).items())),
        "open_messages": len(open_messages),
        "claimed_without_response": len(claimed_without_response),
        "open_for_resolved_contracts": len(open_resolved),
        "fulfilled_messages_missing_aggregate": len(fulfilled_missing_aggregate),
        "open_for_resolved_contract_samples": open_resolved[:10],
        "fulfilled_missing_aggregate_samples": fulfilled_missing_aggregate[:10],
    }


def calibration_by_agent_model() -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_ids: dict[str, set[str]] = defaultdict(set)
    for row in collect_score_rows():
        raw = str(row.get("agent_id") or "unknown")
        canonical = canonical_agent_id(raw) or raw
        grouped[canonical].append(row)
        raw_ids[canonical].add(raw)
    agents: dict[str, Any] = {}
    for agent_id, rows in sorted(grouped.items()):
        briers = [float(row["brier"]) for row in rows if row.get("brier") is not None]
        cost_errors = [
            abs(float(row["cost_error_agent_minutes"]))
            for row in rows
            if row.get("cost_error_agent_minutes") is not None
        ]
        high_confidence_misses = []
        for row in rows:
            try:
                p = float(row.get("p_success"))
            except (TypeError, ValueError):
                continue
            success = bool(row.get("success_bool"))
            if (p >= 0.75 and not success) or (p <= 0.25 and success):
                high_confidence_misses.append({
                    "contract_id": row.get("contract_id"),
                    "p_success": p,
                    "success_bool": success,
                    "score_path": row.get("score_path"),
                })
        agents[agent_id] = {
            "raw_agent_ids": sorted(raw_ids[agent_id]),
            "score_rows": len(rows),
            "mean_brier": None if not briers else round(statistics.mean(briers), 4),
            "mean_abs_effort_error_agent_minutes": (
                None if not cost_errors else round(statistics.mean(cost_errors), 2)
            ),
            "high_confidence_miss_count": len(high_confidence_misses),
            "high_confidence_miss_samples": high_confidence_misses[:10],
        }
    return {
        "generated_at": now_iso(),
        "score_file_count": len(list(SCORES.glob("*.json"))),
        "agents": agents,
    }


def bucket_label(index: int, buckets: int = 5) -> str:
    lo = index / buckets
    hi = (index + 1) / buckets
    return f"{lo:.1f}-{hi:.1f}"


def probability_reliability(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        try:
            p = float(row.get("p_success"))
        except (TypeError, ValueError):
            continue
        idx = min(4, max(0, int(p * 5)))
        buckets[idx].append(row)
    out = []
    for idx in range(5):
        items = buckets.get(idx, [])
        if not items:
            out.append({"bucket": bucket_label(idx), "n": 0})
            continue
        preds = [float(item.get("p_success")) for item in items]
        ys = [1.0 if item.get("success_bool") else 0.0 for item in items]
        out.append({
            "bucket": bucket_label(idx),
            "n": len(items),
            "mean_predicted_p_success": round(statistics.mean(preds), 4),
            "empirical_success_rate": round(statistics.mean(ys), 4),
            "calibration_gap": round(statistics.mean(preds) - statistics.mean(ys), 4),
            "mean_brier": round(statistics.mean(float(item.get("brier") or 0.0) for item in items), 4),
        })
    return out


def effort_reliability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = []
    for row in rows:
        expected = row.get("expected_cost_agent_minutes")
        actual = row.get("actual_cost_agent_minutes")
        if expected is None or actual is None:
            continue
        try:
            expected_f = float(expected)
            actual_f = float(actual)
        except (TypeError, ValueError):
            continue
        if actual_f < 0:
            continue
        usable.append((expected_f, actual_f, row))
    if not usable:
        return {"rows": 0}
    errors = [expected - actual for expected, actual, _ in usable]
    abs_errors = [abs(value) for value in errors]
    ratios = [
        expected / actual
        for expected, actual, _ in usable
        if actual > 0
    ]
    return {
        "rows": len(usable),
        "mean_error_agent_minutes": round(statistics.mean(errors), 2),
        "median_abs_error_agent_minutes": round(statistics.median(abs_errors), 2),
        "median_expected_over_actual": (
            None if not ratios else round(statistics.median(ratios), 4)
        ),
        "large_overestimate_rows": sum(
            1 for expected, actual, _ in usable if actual > 0 and expected >= 2.0 * actual
        ),
        "large_underestimate_rows": sum(
            1 for expected, actual, _ in usable if actual > 0 and expected <= 0.5 * actual
        ),
    }


def failure_mode_reliability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scoreable = [
        row for row in rows
        if isinstance(row.get("externality_audit"), dict)
        and row["externality_audit"].get("realized_failure_mode_ids_available") is True
    ]
    top_hits = [
        row for row in scoreable
        if row["externality_audit"].get("failure_mode_top1_hit") is True
    ]
    specific_scoreable = [
        row for row in scoreable
        if row["externality_audit"].get("specific_failure_mode_id_hit") is not None
    ]
    specific_hits = [
        row for row in specific_scoreable
        if row["externality_audit"].get("specific_failure_mode_id_hit") is True
    ]
    masses = [
        float(row["externality_audit"].get("failure_mode_realized_mass"))
        for row in scoreable
        if row["externality_audit"].get("failure_mode_realized_mass") is not None
    ]
    return {
        "scoreable_rows": len(scoreable),
        "top1_precision": None if not scoreable else round(len(top_hits) / len(scoreable), 4),
        "specific_id_precision": (
            None if not specific_scoreable else round(len(specific_hits) / len(specific_scoreable), 4)
        ),
        "mean_realized_failure_mode_mass": None if not masses else round(statistics.mean(masses), 4),
        "recall_proxy_note": (
            "Exact recall requires outcome-level realized-mode cardinality per row; "
            "mean_realized_failure_mode_mass is the current probability-mass recall proxy."
        ),
    }


def sorted_by_forecast_time(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> str:
        temporal = row.get("temporal_audit") if isinstance(row.get("temporal_audit"), dict) else {}
        return str(temporal.get("forecasted_at") or "")
    return sorted(rows, key=key)


def drift_block(rows: list[dict[str, Any]], key_field: str, min_n: int = 8, window: int = 5) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get(key_field) or "unknown")
        groups[key].append(row)
    out: dict[str, Any] = {}
    for key, items in sorted(groups.items()):
        ordered = sorted_by_forecast_time(items)
        if len(ordered) < min_n:
            continue
        recent = ordered[-window:]
        prior = ordered[:-window]
        if not prior:
            continue
        recent_brier = statistics.mean(float(row.get("brier") or 0.0) for row in recent)
        prior_brier = statistics.mean(float(row.get("brier") or 0.0) for row in prior)
        recent_bias = statistics.mean(
            float(row.get("p_success") or 0.0) - (1.0 if row.get("success_bool") else 0.0)
            for row in recent
        )
        prior_bias = statistics.mean(
            float(row.get("p_success") or 0.0) - (1.0 if row.get("success_bool") else 0.0)
            for row in prior
        )
        out[key] = {
            "rows": len(ordered),
            "recent_window": len(recent),
            "prior_rows": len(prior),
            "recent_mean_brier": round(recent_brier, 4),
            "prior_mean_brier": round(prior_brier, 4),
            "brier_delta_recent_minus_prior": round(recent_brier - prior_brier, 4),
            "recent_signed_bias": round(recent_bias, 4),
            "prior_signed_bias": round(prior_bias, 4),
            "signed_bias_delta_recent_minus_prior": round(recent_bias - prior_bias, 4),
        }
    return out


def high_confidence_misses(rows: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    incidents = []
    for row in rows:
        try:
            p = float(row.get("p_success"))
        except (TypeError, ValueError):
            continue
        success = bool(row.get("success_bool"))
        if not ((p >= 0.75 and not success) or (p <= 0.25 and success)):
            continue
        incidents.append({
            "contract_id": row.get("contract_id"),
            "agent_id": row.get("agent_id"),
            "domain": row.get("domain"),
            "p_success": p,
            "success_bool": success,
            "brier": row.get("brier"),
            "score_path": row.get("score_path"),
        })
    return sorted(incidents, key=lambda item: float(item.get("brier") or 0.0), reverse=True)[:limit]


def reliability_model() -> dict[str, Any]:
    rows = collect_score_rows()
    by_domain_rows = []
    domains: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        domains[str(row.get("domain") or "unknown")].append(row)
    for domain, items in sorted(domains.items()):
        if len(items) < 5:
            continue
        by_domain_rows.append({
            "domain": domain,
            "rows": len(items),
            "probability_reliability": probability_reliability(items),
            "effort_reliability": effort_reliability(items),
        })
    return {
        "generated_at": now_iso(),
        "score_rows": len(rows),
        "probability_reliability": probability_reliability(rows),
        "effort_reliability": effort_reliability(rows),
        "failure_mode_reliability": failure_mode_reliability(rows),
        "per_agent_drift": drift_block(rows, "agent_id"),
        "per_domain_drift": drift_block(rows, "domain"),
        "high_confidence_miss_incidents": high_confidence_misses(rows),
        "domain_reliability": by_domain_rows,
    }


def decision_use_summary() -> dict[str, Any]:
    rows = decision_use_rows()
    stage_counts = Counter(str(row.get("decision_stage") or "unknown") for row in rows)
    used_for_counts = Counter(str(row.get("used_for") or "unknown") for row in rows)
    changed = [
        row for row in rows
        if row.get("decision_changed_bool") is True
        or str(row.get("used_for") or "") in {"split", "defer", "kill", "ask_more"}
    ]
    ignored_without_reason = [
        row for row in rows
        if str(row.get("used_for") or "") in {"ignore", "override"}
        and not str(row.get("ignored_forecast_reason") or "").strip()
    ]
    return {
        "ledger_path": relpath(DECISION_USE_LEDGER),
        "rows": len(rows),
        "stage_counts": dict(sorted(stage_counts.items())),
        "used_for_counts": dict(sorted(used_for_counts.items())),
        "decision_changed_rows": len(changed),
        "ignored_without_reason": len(ignored_without_reason),
        "recent": rows[-10:],
    }


def score_externality_summary() -> dict[str, Any]:
    scored_contracts = 0
    preconditioner_used = 0
    decision_changed_present = 0
    changed_by_forecast_present = 0
    counterfactual_value_present = 0
    samples: list[dict[str, Any]] = []
    for path in sorted(SCORES.glob("*.json")):
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        scored_contracts += 1
        audit = payload.get("externality_audit")
        if not isinstance(audit, dict):
            continue
        fields = audit.get("outcome_fields")
        if not isinstance(fields, dict):
            continue
        cid = str(payload.get("contract_id") or path.stem)
        if fields.get("failure_mode_preconditioner_used") is True:
            preconditioner_used += 1
            if len(samples) < 10:
                samples.append({
                    "contract_id": cid,
                    "preconditioner_effect": fields.get("preconditioner_effect"),
                    "changed_by_forecast_ids": fields.get("changed_by_forecast_ids") or [],
                    "score_path": relpath(path),
                })
        if "decision_changed_bool" in fields:
            decision_changed_present += 1
        if fields.get("changed_by_forecast_ids"):
            changed_by_forecast_present += 1
        if fields.get("counterfactual_value_bucket"):
            counterfactual_value_present += 1
    return {
        "scored_contracts": scored_contracts,
        "failure_mode_preconditioner_used": preconditioner_used,
        "decision_changed_bool_present": decision_changed_present,
        "changed_by_forecast_ids_present": changed_by_forecast_present,
        "counterfactual_value_bucket_present": counterfactual_value_present,
        "preconditioner_samples": samples,
    }


def independence_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    contracts_with_forecasts = 0
    thin_contracts = []
    effective_counts: Counter[int] = Counter()
    for row in rows:
        cid = str(row.get("contract_id") or "")
        if not cid or row.get("malformed"):
            continue
        try:
            latest = latest_forecasts_by_agent(load_forecasts(cid))
        except SystemExit:
            continue
        if not latest:
            continue
        contracts_with_forecasts += 1
        eff = effective_independence_for_forecasts(latest)
        effective_counts[int(eff["effective_n"])] += 1
        if not eff["meets_two_independent_agents"] and len(thin_contracts) < 20:
            thin_contracts.append({
                "contract_id": cid,
                "latest_forecast_count": eff["latest_forecast_count"],
                "effective_n": eff["effective_n"],
                "independence_groups": eff["independence_groups"],
            })
    return {
        "contracts_with_forecasts": contracts_with_forecasts,
        "effective_n_bins": {
            str(key): effective_counts[key] for key in sorted(effective_counts)
        },
        "thin_independence_contracts_sample": thin_contracts,
        "thin_independence_contract_count": sum(
            count for key, count in effective_counts.items() if key < 2
        ),
    }


def forecast_update_health(rows: list[dict[str, Any]]) -> dict[str, Any]:
    update_files = sorted(FORECAST_UPDATES.glob("**/*.json"))
    open_with_prior_forecast = [
        str(row.get("contract_id"))
        for row in rows
        if row.get("forecast_count")
        and lifecycle_state_from_status(row)["state"] in {
            "forecast_fulfilled",
            "aggregate_ready",
        }
    ]
    return {
        "forecast_update_files": len(update_files),
        "open_contracts_with_prior_forecast": len(open_with_prior_forecast),
        "open_contracts_with_prior_forecast_samples": open_with_prior_forecast[:20],
        "note": (
            "Belief updates should be evidence-driven. A zero update count is "
            "acceptable only when no material evidence arrived before resolution."
        ),
    }


def maintenance_plan_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    score_debt = []
    aggregate_debt = []
    void_or_backfill = []
    for row in rows:
        cid = str(row.get("contract_id") or "")
        if not cid or row.get("malformed"):
            continue
        state = lifecycle_state_from_status(row)["state"]
        if state == "resolved_unscored":
            score_debt.append({
                "contract_id": cid,
                "command": f"forecast_pool.py score --contract-id {cid}",
            })
        elif state == "forecast_fulfilled":
            aggregate_debt.append({
                "contract_id": cid,
                "command": f"forecast_pool.py aggregate --contract-id {cid}",
            })
        elif state == "resolved_without_forecasts":
            void_or_backfill.append({
                "contract_id": cid,
                "note": (
                    "Resolved without usable pre-resolution forecasts; void, "
                    "document ordering override, or backfill under policy."
                ),
            })
    decision_summary = decision_use_summary()
    return {
        "generated_at": now_iso(),
        "purpose": "Generated maintenance queue for forecast-market hygiene.",
        "score_debt": score_debt[:50],
        "aggregate_debt": aggregate_debt[:50],
        "resolved_without_forecasts": void_or_backfill[:50],
        "decision_use": decision_summary,
        "counts": {
            "score_debt": len(score_debt),
            "aggregate_debt": len(aggregate_debt),
            "resolved_without_forecasts": len(void_or_backfill),
            "decision_use_rows": decision_summary.get("rows"),
        },
    }


def reflexive_insight_model(
    rows: list[dict[str, Any]],
    reliability_payload: dict[str, Any],
) -> dict[str, Any]:
    """Generate market-owned reflexive nudges from scored artifacts.

    This is intentionally a read model. It reduces RD meta-work by turning
    calibration, externality, debt, and transport traces into a small set of
    suggested research-allocation actions.
    """
    insights: list[dict[str, Any]] = []

    def add(
        insight_id: str,
        kind: str,
        severity: str,
        title: str,
        evidence: dict[str, Any],
        suggested_action: str,
    ) -> None:
        insights.append({
            "id": insight_id,
            "kind": kind,
            "severity": severity,
            "title": title,
            "evidence": evidence,
            "suggested_action": suggested_action,
        })

    aggregate_count = sum(1 for row in rows if row.get("has_aggregate"))
    unresolved_score_debt = [
        row["contract_id"] for row in rows
        if lifecycle_state_from_status(row)["state"] == "resolved_unscored"
    ]
    resolved_without_forecasts = [
        row["contract_id"] for row in rows
        if lifecycle_state_from_status(row)["state"] == "resolved_without_forecasts"
    ]
    decision_summary = decision_use_summary()
    externality = score_externality_summary()
    transport = transport_health()
    independence = independence_summary(rows)
    update_health = forecast_update_health(rows)
    effort = reliability_payload.get("effort_reliability")
    if not isinstance(effort, dict):
        effort = {}
    failure_mode = reliability_payload.get("failure_mode_reliability")
    if not isinstance(failure_mode, dict):
        failure_mode = {}
    high_confidence = reliability_payload.get("high_confidence_miss_incidents")
    if not isinstance(high_confidence, list):
        high_confidence = []

    if externality["failure_mode_preconditioner_used"]:
        add(
            "positive_externality_failure_mode_preconditioning",
            "positive_externality",
            "info",
            "Forecasts have already preconditioned execution against named traps.",
            {
                "preconditioner_used_contracts": externality["failure_mode_preconditioner_used"],
                "samples": externality["preconditioner_samples"],
            },
            "Keep requiring forecasts to name specific failure modes and action-change recommendations.",
        )

    if aggregate_count and int(decision_summary.get("rows") or 0) < aggregate_count:
        add(
            "decision_use_capture_gap",
            "reflexive_capture_gap",
            "high" if int(decision_summary.get("rows") or 0) == 0 else "medium",
            "Aggregates exist without matching decision-use coverage.",
            {
                "aggregate_contracts": aggregate_count,
                "decision_use_rows": decision_summary.get("rows"),
                "decision_changed_rows": decision_summary.get("decision_changed_rows"),
            },
            "Let RD tooling consume rd_fast_read and write decision-use rows automatically when a forecast routes, confirms, delays, or is overridden.",
        )

    median_effort_ratio = effort.get("median_expected_over_actual")
    if isinstance(median_effort_ratio, (int, float)) and median_effort_ratio >= 1.5:
        add(
            "effort_prior_overestimate",
            "calibration",
            "medium",
            "Forecasts are overestimating agent effort.",
            {
                "median_expected_over_actual": median_effort_ratio,
                "large_overestimate_rows": effort.get("large_overestimate_rows"),
                "rows": effort.get("rows"),
            },
            "Use domain effort priors from calibration before assigning agent-minute budgets.",
        )

    if failure_mode.get("scoreable_rows"):
        add(
            "failure_mode_signal_quality",
            "externality_quality",
            "info",
            "Failure-mode forecasts are now scoreable against realized traps.",
            {
                "scoreable_rows": failure_mode.get("scoreable_rows"),
                "top1_precision": failure_mode.get("top1_precision"),
                "specific_id_precision": failure_mode.get("specific_id_precision"),
                "mean_realized_failure_mode_mass": failure_mode.get("mean_realized_failure_mode_mass"),
            },
            "Prefer forecasts with specific_failure_mode_ids over diffuse risk lists.",
        )

    if high_confidence:
        add(
            "high_confidence_miss_review",
            "calibration_incident",
            "medium",
            "High-confidence misses exist and should update weights or prompts.",
            {
                "count": len(high_confidence),
                "samples": high_confidence[:10],
            },
            "Review these rows before trusting high-confidence forecasts in the same domain or agent family.",
        )

    if independence["thin_independence_contract_count"]:
        add(
            "thin_effective_independence",
            "market_depth",
            "medium",
            "Some forecasted contracts have fewer than two independent agent families.",
            {
                "contracts_with_forecasts": independence["contracts_with_forecasts"],
                "effective_n_bins": independence["effective_n_bins"],
                "thin_contract_count": independence["thin_independence_contract_count"],
                "samples": independence["thin_independence_contracts_sample"],
            },
            "Treat thin contracts as single-view forecasts unless another independent agent family prices them.",
        )

    if update_health["open_contracts_with_prior_forecast"] and update_health["forecast_update_files"] == 0:
        add(
            "forecast_update_absence",
            "market_dynamics",
            "medium",
            "No belief-update artifacts exist for open contracts with prior forecasts.",
            update_health,
            "When material evidence arrives before resolution, wake forecasters for a no-update or belief-update response.",
        )

    if unresolved_score_debt:
        add(
            "resolved_score_debt",
            "hygiene",
            "high",
            "Some resolved forecast contracts are not yet scored.",
            {
                "count": len(unresolved_score_debt),
                "samples": unresolved_score_debt[:20],
            },
            "Score or explicitly void these contracts before treating calibration weights as current.",
        )

    if resolved_without_forecasts:
        add(
            "resolved_without_forecasts",
            "hygiene",
            "medium",
            "Some contracts resolved without usable pre-resolution forecasts.",
            {
                "count": len(resolved_without_forecasts),
                "samples": resolved_without_forecasts[:20],
            },
            "Void, document the ordering override, or backfill under policy; do not treat these as normal market evidence.",
        )

    if transport.get("open_for_resolved_contracts") or transport.get("fulfilled_messages_missing_aggregate"):
        add(
            "transport_debt",
            "infrastructure",
            "medium",
            "Forecasting transport has stale or unaggregated messages.",
            {
                "open_for_resolved_contracts": transport.get("open_for_resolved_contracts"),
                "fulfilled_messages_missing_aggregate": transport.get("fulfilled_messages_missing_aggregate"),
            },
            "Run warm-daemon/aggregate maintenance before relying on channel state as market state.",
        )

    return {
        "generated_at": now_iso(),
        "producer": "forecast_pool.materialize-state",
        "purpose": (
            "Mechanized reflexive insight read model. RDs consume these nudges; "
            "they do not need to author separate meta-analysis to discover them."
        ),
        "counts": {
            "contracts": len(rows),
            "aggregate_contracts": aggregate_count,
            "decision_use_rows": decision_summary.get("rows"),
            "score_rows": reliability_payload.get("score_rows"),
            "thin_independence_contracts": independence["thin_independence_contract_count"],
            "forecast_update_files": update_health["forecast_update_files"],
        },
        "effective_independence": independence,
        "forecast_update_health": update_health,
        "insight_count": len(insights),
        "insights": insights,
    }


def global_health_model(rows: list[dict[str, Any]]) -> dict[str, Any]:
    action_counts = Counter(str(row.get("next_action") or "unknown") for row in rows)
    lifecycle_counts = Counter(
        lifecycle_state_from_status(row)["state"] for row in rows
    )
    resolved_unscored = [
        row["contract_id"] for row in rows
        if lifecycle_state_from_status(row)["state"] in {
            "resolved_unscored",
            "resolved_without_forecasts",
        }
    ]
    aggregate_missing = [
        row["contract_id"] for row in rows
        if row.get("next_action") == "aggregate_when_rd_releases"
    ]
    awaiting_forecasts = [
        row["contract_id"] for row in rows
        if row.get("next_action") == "await_forecasts"
    ]
    return {
        "generated_at": now_iso(),
        "forecast_pool_root": relpath(ROOT),
        "contract_count": len(rows),
        "action_counts": dict(sorted(action_counts.items())),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "resolved_without_score": {
            "count": len(resolved_unscored),
            "samples": resolved_unscored[:20],
        },
        "aggregate_missing": {
            "count": len(aggregate_missing),
            "samples": aggregate_missing[:20],
        },
        "awaiting_forecasts": {
            "count": len(awaiting_forecasts),
            "samples": awaiting_forecasts[:20],
        },
        "transport": transport_health(),
        "decision_use": decision_use_summary(),
        "calibration": calibration_status(),
        "reliability": {
            "path": relpath(MARKET_STATE / "reliability.json"),
            "summary": "probability buckets, effort reliability, failure-mode precision, drift, high-confidence misses",
        },
        "reflexive_insights": {
            "path": relpath(REFLEXIVE_INSIGHTS),
            "summary": "market-generated positive externalities, calibration incidents, decision-use gaps, and maintenance nudges",
        },
        "maintenance_plan": {
            "path": relpath(MAINTENANCE_PLAN),
            "summary": "generated score, aggregate, void/backfill, and decision-use hygiene queue",
        },
        "rd_fast_path": {
            "consume": relpath(MARKET_STATE / "global_health.json"),
            "record_decision_use": (
                "forecast_pool.py record-decision-use --contract-id <cid> "
                "--tick-id <tick> --owner <rd> --decision-stage pretick "
                "--used-for <run|split|defer|kill|ask_more|ignore|override>"
            ),
            "refresh": "forecast_pool.py materialize-state",
        },
    }


def materialize_market_state(contract_id: str | None = None) -> dict[str, Any]:
    ensure_dirs()
    all_ids = sorted(path.stem for path in CONTRACTS.glob("*.json"))
    if contract_id:
        if not contract_path(contract_id).exists():
            raise SystemExit(f"missing contract: {contract_path(contract_id)}")
        target_ids = [contract_id]
    else:
        target_ids = all_ids
    all_rows = status_rows(all_ids)
    rows_by_id = {str(row.get("contract_id")): row for row in all_rows}
    written_contracts = []
    for cid in target_ids:
        model = contract_read_model(cid, rows_by_id.get(cid))
        out = MARKET_STATE_CONTRACTS / f"{cid}.json"
        write_json(out, model)
        written_contracts.append(relpath(out))
    global_payload = global_health_model(all_rows)
    calibration_payload_by_agent = calibration_by_agent_model()
    reliability_payload = reliability_model()
    reflexive_payload = reflexive_insight_model(all_rows, reliability_payload)
    maintenance_payload = maintenance_plan_model(all_rows)
    global_path = MARKET_STATE / "global_health.json"
    calibration_path = MARKET_STATE / "calibration_by_agent.json"
    reliability_path = MARKET_STATE / "reliability.json"
    write_json(global_path, global_payload)
    write_json(calibration_path, calibration_payload_by_agent)
    write_json(reliability_path, reliability_payload)
    write_json(REFLEXIVE_INSIGHTS, reflexive_payload)
    write_json(MAINTENANCE_PLAN, maintenance_payload)
    append_market_event(
        "market_state_materialized",
        contract_id=contract_id,
        contracts_written=len(written_contracts),
    )
    return {
        "generated_at": now_iso(),
        "contract_id": contract_id,
        "contracts_written": written_contracts,
        "global_health": relpath(global_path),
        "calibration_by_agent": relpath(calibration_path),
        "reliability": relpath(reliability_path),
        "reflexive_insights": relpath(REFLEXIVE_INSIGHTS),
        "maintenance_plan": relpath(MAINTENANCE_PLAN),
    }


def refresh_market_state_best_effort(contract_id: str | None = None) -> None:
    try:
        materialize_market_state(contract_id)
    except Exception as exc:
        append_market_event(
            "market_state_refresh_failed",
            contract_id=contract_id,
            error=repr(exc),
        )


def cmd_materialize_state(args: argparse.Namespace) -> int:
    payload = materialize_market_state(args.contract_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_record_decision_use(args: argparse.Namespace) -> int:
    ensure_dirs()
    contract, contract_artifact_path, is_scratch_contract = load_decision_contract(args.contract_id)
    if getattr(args, "dedupe", False):
        for row in decision_use_rows(args.contract_id):
            if (
                str(row.get("tick_id") or "") == str(args.tick_id)
                and str(row.get("owner") or "") == str(args.owner)
                and str(row.get("decision_stage") or "") == str(args.decision_stage)
            ):
                print(json.dumps({
                    "deduped": True,
                    "existing": row,
                }, indent=2, sort_keys=True))
                return 0
    aggregate_payload = read_json(aggregate_path(args.contract_id), {})
    if not aggregate_payload and not args.allow_missing_aggregate and not is_scratch_contract:
        raise SystemExit(
            "record-decision-use requires an aggregate/status artifact; "
            "run `forecast_pool.py aggregate --contract-id "
            f"{args.contract_id}` or pass --allow-missing-aggregate with an "
            "explicit --ignored-forecast-reason."
        )
    if args.used_for in {"ignore", "override"} and not args.ignored_forecast_reason:
        raise SystemExit("--used-for ignore/override requires --ignored-forecast-reason")
    if args.allow_missing_aggregate and not args.ignored_forecast_reason and not is_scratch_contract:
        raise SystemExit("--allow-missing-aggregate requires --ignored-forecast-reason")
    aggregate_summary = compact_aggregate_summary(aggregate_payload)
    if is_scratch_contract and not aggregate_payload:
        aggregate_summary = {
            "exists": False,
            "scratch_contract": True,
            "excluded_from_calibration": bool(contract.get("excluded_from_calibration")),
        }
    record = {
        "decision_use_id": f"du_{uuid.uuid4().hex[:12]}",
        "recorded_at": now_iso(),
        "contract_id": args.contract_id,
        "tick_id": args.tick_id,
        "owner": args.owner,
        "decision_stage": args.decision_stage,
        "used_for": args.used_for,
        "decision_changed_bool": args.decision_changed_bool,
        "forecast_delta": args.forecast_delta,
        "old_action": args.old_action,
        "new_action": args.new_action,
        "failure_modes_adopted": parse_json_list(
            args.failure_modes_adopted_json,
            "--failure-modes-adopted-json",
        ),
        "ignored_forecast_reason": args.ignored_forecast_reason,
        "notes": args.notes,
        "aggregate_present": bool(aggregate_payload),
        "aggregate_summary": aggregate_summary,
        "contract_question": contract.get("question"),
        "artifact_paths": {
            "contract": relpath(contract_artifact_path),
            "aggregate": relpath(aggregate_path(args.contract_id)),
            "decision_use_ledger": relpath(DECISION_USE_LEDGER),
        },
    }
    append_jsonl(DECISION_USE_LEDGER, record)
    append_market_event(
        "decision_use_recorded",
        contract_id=args.contract_id,
        tick_id=args.tick_id,
        owner=args.owner,
        used_for=args.used_for,
        decision_changed=args.decision_changed_bool,
    )
    if not is_scratch_contract:
        refresh_market_state_best_effort(args.contract_id)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


def daemon_once_payload(args: argparse.Namespace) -> dict[str, Any]:
    contract_ids = sorted(path.stem for path in CONTRACTS.glob("*.json"))
    if args.contract_id:
        if not contract_path(args.contract_id).exists():
            raise SystemExit(f"missing contract: {contract_path(args.contract_id)}")
        contract_ids = [args.contract_id]
    rows = status_rows(contract_ids)
    action_counts: dict[str, int] = {}
    for row in rows:
        action = row["next_action"]
        action_counts[action] = action_counts.get(action, 0) + 1
    append_market_event(
        "daemon_once_scan",
        contract_count=len(rows),
        malformed_skipped=action_counts.get("malformed_skipped", 0),
        closed=action_counts.get("closed", 0),
        await_forecasts=action_counts.get("await_forecasts", 0))
    return {
        "generated_at": now_iso(),
        "mode": "daemon_once_status_scan",
        "forecast_pool_root": relpath(ROOT),
        "contract_count": len(rows),
        "action_counts": action_counts,
        "contracts": rows,
        "calibration": calibration_status(),
        "prediction_ledger": scan_prediction_ledger(args.prediction_ledger, args.ledger_limit),
        "semantics": {
            "dispatches_agents": False,
            "resolves_contracts": False,
            "scores_contracts": False,
            "writes_status_artifact": bool(args.write),
        },
    }


def parse_warm_forecasters(text: str) -> list[dict[str, str]]:
    """Parse runtime:agent_id[:role_id] entries.

    `runtime` is a dispatch hint only.  This command never launches the runtime.
    """
    out: list[dict[str, str]] = []
    for raw in text.split(","):
        item = raw.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) not in {2, 3}:
            raise SystemExit(
                "--forecasters entries must be runtime:agent_id or runtime:agent_id:role_id"
            )
        runtime, agent_id = parts[0].strip(), parts[1].strip()
        role_id = parts[2].strip() if len(parts) == 3 else "forecasting_agent"
        if runtime not in {"claude", "codex"}:
            raise SystemExit("warm forecaster runtime must be claude or codex")
        if not agent_id:
            raise SystemExit("warm forecaster agent_id cannot be empty")
        out.append({"runtime": runtime, "agent_id": agent_id, "role_id": role_id})
    if not out:
        raise SystemExit("--forecasters produced no forecaster entries")
    return out


def evidence_fingerprint(paths: list[Path]) -> dict[str, Any]:
    entries = []
    for path in paths:
        exists = path.exists()
        entries.append({
            "path": relpath(path),
            "exists": exists,
            "sha256": file_sha256(path) if exists and path.is_file() else None,
            "mtime_ns": path.stat().st_mtime_ns if exists else None,
        })
    return {
        "entries": entries,
        "fingerprint": stable_payload_hash(entries),
    }


def warm_prompt(
    *,
    contract: dict[str, Any],
    forecaster: dict[str, str],
    reason: str,
    evidence: dict[str, Any],
    prior_forecast: dict[str, Any] | None,
) -> str:
    prior = "none"
    if prior_forecast:
        prior = (
            f"p_success={prior_forecast.get('p_success')}, "
            f"expected_cost_agent_minutes={prior_forecast.get('expected_cost_agent_minutes')}, "
            f"forecasted_at={prior_forecast.get('forecasted_at')}"
        )
    evidence_lines = "\n".join(
        f"- {entry['path']} sha256={entry['sha256']}"
        for entry in evidence["entries"]
        if entry.get("exists")
    )
    if reason == "resolved_contract_calibration_reflection":
        required_output = (
            "1. This contract is already resolved. Do not add a new forecast row and do not add a belief update.\n"
            "2. Read the outcome, score, calibration summary, and GP-233 evidence when supplied.\n"
            "3. Emit a concise calibration reflection or `NO_UPDATE` response naming any effort/probability/externality lesson.\n"
            "4. Do not resolve, score, execute the contract, or mutate calibration artifacts."
        )
    else:
        required_output = (
            "1. If no prior forecast exists, add a sealed forecast with read-only attestation.\n"
            f"2. If a prior forecast exists, write a timestamped odds update with `--belief-update --update-reason <reason> --evidence-fingerprint {evidence['fingerprint']}` only when the evidence changed your probability or failure-mode distribution materially; otherwise say no update.\n"
            "3. Keep probability calibration, effort estimate, and failure-mode/externality notes separate.\n"
            "4. Do not resolve, score, or execute the contract."
        )
    return f"""You are a read-only GP-230 warm forecaster.

Runtime hint: {forecaster['runtime']}
Agent id: {forecaster['agent_id']}
Role id: {forecaster['role_id']}
Wake reason: {reason}

Subscription-safety rule: do not poll, wait, or keep a session alive. Inspect the referenced artifacts, emit one forecast or odds-update command, then exit.

Contract id: {contract['contract_id']}
Layer: {contract['layer']}
Task type: {contract['task_type']}
Question: {contract['question']}
Objective resolver: {contract['objective_resolver']}
Success threshold: {contract['success_threshold']}
Horizon: {contract['horizon']}

Prior forecast from this agent: {prior}

Evidence fingerprint: {evidence['fingerprint']}
Evidence files:
{evidence_lines}

DAG/void discipline:
- If an evidence file is a probability DAG, use it to decompose the forecast into premises, dependencies, and weakest nodes.
- Also name what the DAG does not represent: missing observables, unpriced residuals, hidden coupling, stale evidence, or a missing negative case.
- Do not treat DAG existence as evidence that the top-level probability is earned.

Required output:
{required_output}
"""


def warm_event_payload(
    *,
    contract: dict[str, Any],
    forecaster: dict[str, str],
    reason: str,
    evidence_paths: list[Path],
    prior_forecast: dict[str, Any] | None,
) -> dict[str, Any]:
    evidence = evidence_fingerprint(evidence_paths)
    payload = {
        "schema_version": 1,
        "specversion": "ztare.forecast_pool.wake.v1",
        "created_at": now_iso(),
        "id": None,
        "source": "scripts/public/control/forecast/pool.py",
        "type": "gp230.warm_forecaster.wake",
        "subject": contract["contract_id"],
        "kind": "gp230.warm_forecaster.wake",
        "contract_id": contract["contract_id"],
        "forecaster": forecaster,
        "reason": reason,
        "launches_agent": False,
        "subscription_safe": True,
        "reactivation_policy": {
            "wake_only_on_contract_or_evidence_delta": True,
            "no_idle_polling_inside_agent": True,
            "agent_must_exit_after_one_forecast_or_no_update": True,
            "outcome_write_access": False,
        },
        "a2a": {
            "message_kind": "request",
            "from_role": "research_director",
            "to_role": forecaster["role_id"],
            "obligation_state_hint": "pending",
            "artifact_dependency_hint": "contract_plus_evidence_fingerprint",
            "authority_note": (
                "This wake event creates a read-only forecasting obligation. "
                "It grants no authority to execute, resolve, score, or mutate contracts."
            ),
        },
        "dag_guidance": {
            "use_probability_dag_if_supplied": True,
            "inspect_voids_not_only_nodes": True,
            "dag_paths": [
                relpath(path)
                for path in evidence_paths
                if "dag" in path.name.lower() or "probability" in path.name.lower()
            ],
        },
        "prior_forecast_path": (
            relpath(forecast_path(contract["contract_id"], forecaster["agent_id"]))
            if prior_forecast else None
        ),
        "evidence": evidence,
        "prompt": warm_prompt(
            contract=contract,
            forecaster=forecaster,
            reason=reason,
            evidence=evidence,
            prior_forecast=prior_forecast,
        ),
    }
    payload["wake_key"] = stable_payload_hash({
        "contract_id": contract["contract_id"],
        "agent_id": forecaster["agent_id"],
        "reason": reason,
        "evidence": evidence["fingerprint"],
    })
    payload["id"] = f"wake_{payload['wake_key'][:24]}"
    return payload


def emit_warm_agent_message(
    *,
    event: dict[str, Any],
    event_path: Path,
    from_role: str,
    to_role: str,
) -> dict[str, Any]:
    sender_impl = "ztare_local"
    try:
        cf_src = REPO.parent / "cognitive-firm" / "src"
        if cf_src.exists() and str(cf_src) not in sys.path:
            sys.path.insert(0, str(cf_src))
        from cognitive_firm.orchestration import agent_channels as cf_channels
        from cognitive_firm.orchestration import transition_log as cf_transition_log

        cf_channels.CHANNELS_DIR = REPO / "org" / "channels"
        cf_channels.ROLES_DIR = REPO / "org" / "roles"
        cf_transition_log.TRANSITIONS_LOG = REPO / "ztare_workspace" / "transitions.jsonl"
        send_agent_message = cf_channels.send_agent_message
        sender_impl = "cognitive_firm"
    except Exception:
        try:
            from src.ztare.orchestration.agent_channels import send_agent_message
        except Exception as exc:  # pragma: no cover - environment/config failure.
            raise SystemExit(f"could not import agent channel sender: {exc}") from exc

    message = send_agent_message(
        from_role=from_role,
        to_role=to_role,
        kind="request",
        subject=f"GP-230 warm forecast wake: {event['contract_id']}",
        body=event["prompt"],
        expects_response=True,
        causality_id=event["wake_key"],
        references=[
            relpath(contract_path(event["contract_id"])),
            relpath(event_path),
        ],
        artifacts=[relpath(event_path)],
        metadata={
            "schema_version": 1,
            "forecast_pool_wake_key": event["wake_key"],
            "contract_id": event["contract_id"],
            "agent_id": event["forecaster"]["agent_id"],
            "runtime": event["forecaster"]["runtime"],
            "role_id": event["forecaster"]["role_id"],
            "reason": event["reason"],
            "subscription_safe": True,
            "launches_agent": False,
            "evidence_fingerprint": event["evidence"]["fingerprint"],
        },
    )
    return {
        "message_id": message.message_id,
        "to_role": message.to_role,
        "from_role": message.from_role,
        "wake_key": event["wake_key"],
        "contract_id": event["contract_id"],
        "agent_id": event["forecaster"]["agent_id"],
        "sender_impl": sender_impl,
    }


def channel_role_dir(role_id: str) -> Path:
    return REPO / "org" / "channels" / slug(role_id)


def channel_inbox_dir(role_id: str) -> Path:
    return channel_role_dir(role_id) / "inbox"


def channel_claims_dir(role_id: str) -> Path:
    return channel_role_dir(role_id) / "claims"


def channel_responses_dir(role_id: str) -> Path:
    return channel_role_dir(role_id) / "responses"


def consumer_status_path() -> Path:
    return CONSUMER_STATE / "latest.json"


def consumer_prompt_dir() -> Path:
    return CONSUMER_STATE / "prompts"


def consumer_output_dir() -> Path:
    return CONSUMER_STATE / "outputs"


def consumer_runtime_session_dir() -> Path:
    return CONSUMER_STATE / "runtime_sessions"


def consumer_runtime_session_path(agent_id: str, runtime: str) -> Path:
    return consumer_runtime_session_dir() / f"{slug(runtime)}_{slug(agent_id)}.json"


def get_or_create_runtime_session(
    *,
    agent_id: str,
    runtime: str,
    max_ticks: int,
    max_age_hours: float,
) -> dict[str, Any]:
    path = consumer_runtime_session_path(agent_id, runtime)
    state = read_json(path, {})
    now = datetime.now(timezone.utc)
    if not isinstance(state, dict):
        state = {}
    started_raw = state.get("started_at")
    stale = True
    if state.get("session_id") and started_raw:
        try:
            started = parse_iso_timestamp(str(started_raw), "runtime_session.started_at")
            age_h = (now - started).total_seconds() / 3600.0
            stale = int(state.get("tick_count") or 0) >= max_ticks or age_h >= max_age_hours
        except SystemExit:
            stale = True
    if stale:
        state = {
            "schema_version": 1,
            "runtime": runtime,
            "agent_id": agent_id,
            "session_id": str(uuid.uuid4()),
            "started_at": now_iso(),
            "last_tick_at": None,
            "tick_count": 0,
            "is_new": True,
            "continuity_policy": "resume_if_supported_else_artifact_memory",
        }
    else:
        state["is_new"] = False
    write_json(path, state)
    state["session_state_path"] = relpath(path)
    return state


def note_runtime_session_tick(
    *,
    agent_id: str,
    runtime: str,
    session_state: dict[str, Any],
) -> None:
    path = consumer_runtime_session_path(agent_id, runtime)
    current = read_json(path, {})
    if not isinstance(current, dict):
        current = {}
    current.update({
        "runtime": runtime,
        "agent_id": agent_id,
        "session_id": session_state.get("session_id"),
        "started_at": session_state.get("started_at"),
        "last_tick_at": now_iso(),
        "tick_count": int(current.get("tick_count") or session_state.get("tick_count") or 0) + 1,
        "is_new": False,
        "continuity_policy": "resume_if_supported_else_artifact_memory",
    })
    write_json(path, current)


def invalidate_runtime_session(
    *,
    agent_id: str,
    runtime: str,
    reason: str,
) -> None:
    path = consumer_runtime_session_path(agent_id, runtime)
    current = read_json(path, {})
    if not isinstance(current, dict):
        current = {}
    current.update({
        "runtime": runtime,
        "agent_id": agent_id,
        "invalidated_at": now_iso(),
        "invalidated_reason": reason,
        "session_id": None,
        "is_new": True,
    })
    write_json(path, current)


def load_channel_message(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def channel_message_path(role_id: str, message_id: str) -> Path:
    return channel_inbox_dir(role_id) / f"{message_id}.json"


def channel_sent_mirror_path(message: dict[str, Any]) -> Path:
    return (
        REPO
        / "org"
        / "channels"
        / slug(str(message.get("from_role") or "unknown"))
        / "sent"
        / f"{message.get('message_id')}.json"
    )


def write_channel_message(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)
    mirror = channel_sent_mirror_path(payload)
    if mirror.exists():
        write_json(mirror, payload)


def update_channel_message_lifecycle(
    *,
    role_id: str,
    message_id: str,
    actor: str,
    status: str | None = None,
    obligation_state: str | None = None,
    note: str,
) -> dict[str, Any]:
    path = channel_message_path(role_id, message_id)
    message = read_json(path)
    if not isinstance(message, dict):
        raise SystemExit(f"missing or malformed channel message: {path}")
    metadata = message.setdefault("metadata", {})
    if status is not None:
        message["status"] = status
        metadata["last_status_actor"] = actor
        metadata["last_status_note"] = note
        metadata["last_status_utc"] = now_iso()
    if obligation_state is not None:
        message["obligation_state"] = obligation_state
        metadata["last_obligation_actor"] = actor
        metadata["last_obligation_note"] = note
        metadata["last_obligation_utc"] = now_iso()
    write_channel_message(path, message)
    return message


def open_forecast_messages(
    *,
    role_id: str,
    runtime: str | None,
    agent_id: str | None,
    contract_id: str | None,
    limit: int,
    include_claimed: bool = False,
) -> list[dict[str, Any]]:
    inbox = channel_inbox_dir(role_id)
    if not inbox.exists():
        return []
    messages: list[dict[str, Any]] = []
    for path in sorted(inbox.glob("*.json"), key=lambda p: p.stat().st_mtime):
        msg = load_channel_message(path)
        if not msg:
            continue
        metadata = msg.get("metadata") if isinstance(msg.get("metadata"), dict) else {}
        if metadata.get("contract_id") is None or metadata.get("forecast_pool_wake_key") is None:
            continue
        if msg.get("status") == "closed" or msg.get("obligation_state") in {"fulfilled", "refused", "expired"}:
            continue
        if runtime and metadata.get("runtime") != runtime:
            continue
        if agent_id and metadata.get("agent_id") != agent_id:
            continue
        if contract_id and metadata.get("contract_id") != contract_id:
            continue
        claim_path = channel_claims_dir(role_id) / f"{msg.get('message_id')}.json"
        if claim_path.exists() and not include_claimed:
            continue
        msg["_path"] = path
        messages.append(msg)
        if len(messages) >= limit:
            break
    return messages


def atomic_claim_message(
    *,
    role_id: str,
    message: dict[str, Any],
    consumer_id: str,
    mode: str,
) -> dict[str, Any]:
    message_id = str(message["message_id"])
    metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
    claim = {
        "schema_version": 1,
        "claimed_at": now_iso(),
        "consumer_id": consumer_id,
        "mode": mode,
        "role_id": role_id,
        "message_id": message_id,
        "contract_id": metadata.get("contract_id"),
        "agent_id": metadata.get("agent_id"),
        "runtime": metadata.get("runtime"),
        "wake_key": metadata.get("forecast_pool_wake_key"),
        "subscription_safe": mode != "live" or metadata.get("runtime") in {"claude", "codex"},
    }
    path = channel_claims_dir(role_id) / f"{message_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise SystemExit(f"message already claimed: {relpath(path)}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(claim, indent=2, sort_keys=True) + "\n")
    claim["claim_path"] = relpath(path)
    return claim


def forecast_count_for_agent(contract_id: str, agent_id: str) -> int:
    return sum(1 for row in load_forecasts(contract_id) if row.get("agent_id") == agent_id)


def render_forecaster_prompt(
    *,
    message: dict[str, Any],
    role_id: str,
    runtime: str,
    agent_id: str,
) -> str:
    metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
    contract_id = str(metadata.get("contract_id") or "")
    evidence_fingerprint = str(metadata.get("evidence_fingerprint") or "")
    wake_key = str(metadata.get("forecast_pool_wake_key") or "")
    references = message.get("references") if isinstance(message.get("references"), list) else []
    artifacts = message.get("artifacts") if isinstance(message.get("artifacts"), list) else []
    prior = latest_forecast_by_agent(contract_id, agent_id)
    prior_line = (
        f"Prior latest forecast: p_success={prior.get('p_success')} at {prior.get('forecasted_at')} "
        f"path={prior.get('forecast_artifact_path')}"
        if prior else "Prior latest forecast: none"
    )
    return f"""You are running as the GP-230 forecasting agent `{agent_id}` on runtime `{runtime}`.

Role and mandate:
- Read `AGENTS.md` controlling rules.
- Read `org/roles/{role_id}.yaml`.
- Read `org/mandates/forecasting_agent_mandate.md`.
- You may inspect project files, evidence ledgers, specs, seams, GP-233, and referenced artifacts to price the contract.
- You must not execute the forecasted work, resolve contracts, score outcomes, or mutate source/proof/experiment files.

Wake obligation:
- contract_id: {contract_id}
- wake_key: {wake_key}
- evidence_fingerprint: {evidence_fingerprint}
- reason: {metadata.get('reason')}
- message_id: {message.get('message_id')}
- {prior_line}

Referenced artifacts:
{chr(10).join(f"- {item}" for item in [*references, *artifacts]) or "- none"}

Task:
1. Read the contract and the referenced evidence artifacts.
2. If the wake reason is `resolved_contract_calibration_reflection`, do not add a forecast or belief update; write a concise calibration reflection or `NO_UPDATE`.
3. If the contract is open and no prior forecast exists for `{agent_id}`, add one forecast using:
   ./venv/bin/python scripts/public/control/forecast/pool.py add-forecast --contract-id {contract_id} --agent-id {agent_id} ...
4. If the contract is open and a prior forecast exists, add a timestamped update only when evidence materially changes odds, effort, dependency risk, or failure-mode distribution:
   ./venv/bin/python scripts/public/control/forecast/pool.py add-forecast --contract-id {contract_id} --agent-id {agent_id} --belief-update --update-reason "{metadata.get('reason')}" --evidence-fingerprint {evidence_fingerprint} ...
5. If there is no material update, state `NO_UPDATE` with the reason.
6. Exit after the single forecast/no-update response. Do not poll or launch agents.

Original wake prompt:
{message.get('body') or ''}
"""


def latest_forecast_by_agent(contract_id: str, agent_id: str) -> dict[str, Any] | None:
    forecasts = [row for row in load_forecasts(contract_id) if row.get("agent_id") == agent_id]
    latest = latest_forecasts_by_agent(forecasts)
    return latest[0] if latest else None


def build_subscription_runtime_command(
    *,
    runtime: str,
    prompt: str,
    session_state: dict[str, Any] | None = None,
) -> list[str]:
    return build_subscription_agent_command(
        runtime=runtime,
        prompt=prompt,
        repo=REPO,
        session_state=session_state,
        codex_model_env="ZTARE_CODEX_FORECAST_MODEL",
        default_codex_model="gpt-5.4-mini",
    )


def subscription_runtime_env(runtime: str) -> dict[str, str]:
    return subscription_agent_env(runtime)


def run_subscription_runtime_with_recovery(
    *,
    runtime: str,
    prompt: str,
    agent_id: str,
    session_state: dict[str, Any] | None,
    timeout_seconds: int,
) -> tuple[Any, dict[str, Any] | None, list[str], list[str], str | None]:
    run = run_subscription_agent_shared(
        runtime=runtime,
        prompt=prompt,
        agent_id=agent_id,
        repo=REPO,
        session_state=session_state,
        timeout_seconds=timeout_seconds,
        invalidate_session=lambda reason: invalidate_runtime_session(
            agent_id=agent_id,
            runtime=runtime,
            reason=reason,
        ),
        create_replacement_session=lambda: get_or_create_runtime_session(
            agent_id=agent_id,
            runtime=runtime,
            max_ticks=10**9,
            max_age_hours=10**9,
        ),
        codex_model_env="ZTARE_CODEX_FORECAST_MODEL",
        default_codex_model="gpt-5.4-mini",
    )
    return run.result, run.final_session_state, run.initial_command, run.final_command, run.recovery_note


def write_consumer_response(
    *,
    role_id: str,
    message: dict[str, Any],
    claim: dict[str, Any] | None,
    payload: dict[str, Any],
) -> Path:
    response_path = channel_responses_dir(role_id) / f"{message.get('message_id')}.json"
    payload = {
        **payload,
        "schema_version": 1,
        "message_id": message.get("message_id"),
        "claim_path": claim.get("claim_path") if claim else None,
        "written_at": now_iso(),
    }
    write_json(response_path, payload)
    return response_path


def cmd_warm_consumer_once(args: argparse.Namespace) -> int:
    ensure_dirs()
    messages = open_forecast_messages(
        role_id=args.role_id,
        runtime=args.runtime,
        agent_id=args.agent_id,
        contract_id=args.contract_id,
        limit=args.max_messages,
        include_claimed=args.include_claimed,
    )
    if not messages:
        payload = {
            "mode": "warm_consumer_once",
            "consumer_mode": args.mode,
            "checked_at": now_iso(),
            "role_id": args.role_id,
            "runtime": args.runtime,
            "agent_id": args.agent_id,
            "contract_id": args.contract_id,
            "messages_found": 0,
            "launches_agent": False,
        }
        write_json(consumer_status_path(), payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    processed: list[dict[str, Any]] = []
    for message in messages:
        metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        runtime = args.runtime or str(metadata.get("runtime") or "")
        agent_id = args.agent_id or str(metadata.get("agent_id") or "")
        contract_id = str(metadata.get("contract_id") or "")
        if not runtime or not agent_id or not contract_id:
            processed.append({
                "message_id": message.get("message_id"),
                "status": "skipped",
                "reason": "missing runtime/agent_id/contract_id metadata",
            })
            continue
        if outcome_path(contract_id).exists() and metadata.get("reason") != "resolved_contract_calibration_reflection":
            actor = args.consumer_id or f"{runtime}_{agent_id}"
            update_channel_message_lifecycle(
                role_id=args.role_id,
                message_id=str(message["message_id"]),
                actor=actor,
                status="closed",
                obligation_state="expired",
                note="stale open-forecast wake expired because contract is already resolved",
            )
            response_path = write_consumer_response(
                role_id=args.role_id,
                message=message,
                claim=None,
                payload={
                    "mode": args.mode,
                    "contract_id": contract_id,
                    "agent_id": agent_id,
                    "runtime": runtime,
                    "launches_agent": False,
                    "expired_without_launch": True,
                    "reason": "contract_resolved_before_forecaster_consumed_open_wake",
                },
            )
            processed.append({
                "message_id": message.get("message_id"),
                "status": "expired_stale_resolved_contract_wake",
                "response_path": relpath(response_path),
                "launches_agent": False,
            })
            continue
        if (
            args.mode == "live"
            and runtime == "claude"
            and os.environ.get("ZTARE_ENABLE_CLAUDE_FORECASTER", "").lower()
            not in {"1", "true", "yes"}
        ):
            consumer_id = args.consumer_id or f"{runtime}_{agent_id}"
            claim = atomic_claim_message(
                role_id=args.role_id,
                message=message,
                consumer_id=consumer_id,
                mode=args.mode,
            )
            update_channel_message_lifecycle(
                role_id=args.role_id,
                message_id=str(message["message_id"]),
                actor=consumer_id,
                status="closed",
                obligation_state="refused",
                note="claude forecast runtime disabled until subscription auth mode is verified",
            )
            response_path = write_consumer_response(
                role_id=args.role_id,
                message=message,
                claim=claim,
                payload={
                    "mode": args.mode,
                    "contract_id": contract_id,
                    "agent_id": agent_id,
                    "runtime": runtime,
                    "launches_agent": False,
                    "blocked_runtime": True,
                    "reason": "claude_forecaster_disabled_until_subscription_auth_verified",
                },
            )
            processed.append({
                "message_id": message.get("message_id"),
                "status": "blocked_runtime",
                "claim_path": claim["claim_path"],
                "response_path": relpath(response_path),
                "launches_agent": False,
            })
            continue
        prompt = render_forecaster_prompt(
            message=message,
            role_id=args.role_id,
            runtime=runtime,
            agent_id=agent_id,
        )
        prompt_path = consumer_prompt_dir() / f"{message.get('message_id')}_{runtime}_{slug(agent_id)}.md"
        write_json(prompt_path.with_suffix(".json"), {
            "message_id": message.get("message_id"),
            "contract_id": contract_id,
            "agent_id": agent_id,
            "runtime": runtime,
            "prompt_path": relpath(prompt_path),
            "rendered_at": now_iso(),
            "mode": args.mode,
        })
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")

        before_count = forecast_count_for_agent(contract_id, agent_id)
        session_state = (
            get_or_create_runtime_session(
                agent_id=agent_id,
                runtime=runtime,
                max_ticks=args.resume_max_ticks,
                max_age_hours=args.resume_max_age_hours,
            )
            if args.use_resume and runtime == "claude" else None
        )
        command_preview = build_subscription_runtime_command(
            runtime=runtime,
            prompt=prompt,
            session_state=session_state,
        )
        prompt_ref = f"@{relpath(prompt_path)}"
        command_redacted = redact_prompt_command(command_preview, prompt_ref)
        if args.mode == "preview":
            response_path = write_consumer_response(
                role_id=args.role_id,
                message=message,
                claim=None,
                payload={
                    "mode": "preview",
                    "contract_id": contract_id,
                    "agent_id": agent_id,
                    "runtime": runtime,
                    "prompt_path": relpath(prompt_path),
                    "command_preview": command_redacted,
                    "session_state": session_state,
                    "launches_agent": False,
                    "claimed": False,
                },
            )
            processed.append({
                "message_id": message.get("message_id"),
                "status": "previewed",
                "response_path": relpath(response_path),
                "prompt_path": relpath(prompt_path),
                "command_preview": command_redacted,
            })
            continue

        consumer_id = args.consumer_id or f"{runtime}_{agent_id}"
        claim = atomic_claim_message(
            role_id=args.role_id,
            message=message,
            consumer_id=consumer_id,
            mode=args.mode,
        )
        update_channel_message_lifecycle(
            role_id=args.role_id,
            message_id=str(message["message_id"]),
            actor=consumer_id,
            status="acknowledged",
            obligation_state="accepted",
            note=f"forecast consumer claimed in {args.mode} mode",
        )
        update_channel_message_lifecycle(
            role_id=args.role_id,
            message_id=str(message["message_id"]),
            actor=consumer_id,
            obligation_state="in_progress",
            note=f"forecast consumer started in {args.mode} mode",
        )

        if args.mode == "stub":
            after_count = forecast_count_for_agent(contract_id, agent_id)
            response_path = write_consumer_response(
                role_id=args.role_id,
                message=message,
                claim=claim,
                payload={
                    "mode": "stub",
                    "contract_id": contract_id,
                    "agent_id": agent_id,
                    "runtime": runtime,
                    "prompt_path": relpath(prompt_path),
                    "command_preview": command_redacted,
                    "session_state": session_state,
                    "launches_agent": False,
                    "forecast_count_before": before_count,
                    "forecast_count_after": after_count,
                    "stub_result": "lifecycle_ok_no_subscription_runtime_started",
                },
            )
            update_channel_message_lifecycle(
                role_id=args.role_id,
                message_id=str(message["message_id"]),
                actor=consumer_id,
                status="closed",
                obligation_state="fulfilled",
                note="stub consumer lifecycle test completed; no LLM launched",
            )
            processed.append({
                "message_id": message.get("message_id"),
                "status": "stub_fulfilled",
                "claim_path": claim["claim_path"],
                "response_path": relpath(response_path),
                "prompt_path": relpath(prompt_path),
                "launches_agent": False,
            })
            continue

        if args.mode != "live":
            raise SystemExit(f"unsupported consumer mode: {args.mode}")
        if args.no_live_runtime:
            raise SystemExit("live mode blocked by --no-live-runtime")

        output_path = consumer_output_dir() / f"{message.get('message_id')}_{runtime}_{slug(agent_id)}.txt"
        started_at = now_iso()
        result, final_session_state, attempted_command, final_command, recovery_note = run_subscription_runtime_with_recovery(
            runtime=runtime,
            prompt=prompt,
            agent_id=agent_id,
            session_state=session_state,
            timeout_seconds=args.timeout_seconds,
        )
        if final_session_state is not session_state:
            session_state = final_session_state
        final_command_redacted = redact_prompt_command(final_command, prompt_ref)
        output_text = (
            f"returncode={result.returncode}\n"
            f"started_at={started_at}\n"
            f"finished_at={now_iso()}\n\n"
            f"recovery_note={recovery_note or ''}\n"
            f"attempted_command={' '.join(redact_prompt_command(attempted_command, prompt_ref))}\n"
            f"final_command={' '.join(final_command_redacted)}\n\n"
            f"--- stdout ---\n{result.stdout}\n\n--- stderr ---\n{result.stderr}\n"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
        after_count = forecast_count_for_agent(contract_id, agent_id)
        output_combined = f"{result.stdout}\n{result.stderr}".lower()
        has_no_update = "no_update" in output_combined or "no update" in output_combined
        fulfilled = result.returncode == 0 and (
            not args.require_forecast_or_no_update
            or after_count > before_count
            or has_no_update
        )
        response_path = write_consumer_response(
            role_id=args.role_id,
            message=message,
            claim=claim,
            payload={
                "mode": "live",
                "contract_id": contract_id,
                "agent_id": agent_id,
                "runtime": runtime,
                "prompt_path": relpath(prompt_path),
                "command_preview": final_command_redacted,
                "initial_command_preview": command_redacted,
                "recovery_note": recovery_note,
                "session_state": session_state,
                "launches_agent": True,
                "returncode": result.returncode,
                "output_path": relpath(output_path),
                "forecast_count_before": before_count,
                "forecast_count_after": after_count,
                "detected_no_update": has_no_update,
                "fulfilled": fulfilled,
            },
        )
        if fulfilled:
            if args.use_resume and session_state:
                note_runtime_session_tick(
                    agent_id=agent_id,
                    runtime=runtime,
                    session_state=session_state,
                )
            update_channel_message_lifecycle(
                role_id=args.role_id,
                message_id=str(message["message_id"]),
                actor=consumer_id,
                status="closed",
                obligation_state="fulfilled",
                note="live forecast consumer completed forecast or explicit no-update",
            )
            status = "live_fulfilled"
        else:
            update_channel_message_lifecycle(
                role_id=args.role_id,
                message_id=str(message["message_id"]),
                actor=consumer_id,
                status="acknowledged",
                obligation_state="blocked_input",
                note="live forecast consumer did not produce forecast/no-update marker",
            )
            status = "blocked_input"
        processed.append({
            "message_id": message.get("message_id"),
            "status": status,
            "claim_path": claim["claim_path"],
            "response_path": relpath(response_path),
            "prompt_path": relpath(prompt_path),
            "output_path": relpath(output_path),
            "launches_agent": True,
            "returncode": result.returncode,
        })

    payload = {
        "mode": "warm_consumer_once",
        "consumer_mode": args.mode,
        "checked_at": now_iso(),
        "role_id": args.role_id,
        "runtime": args.runtime,
        "agent_id": args.agent_id,
        "contract_id": args.contract_id,
        "messages_found": len(messages),
        "messages_processed": len(processed),
        "launches_agent": args.mode == "live",
        "processed": processed,
    }
    write_json(consumer_status_path(), payload)
    refresh_market_state_best_effort(args.contract_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_warm_consumer_loop(args: argparse.Namespace) -> int:
    iterations = 0
    while args.max_iterations is None or iterations < args.max_iterations:
        iterations += 1
        print(json.dumps({
            "mode": "warm_consumer_loop_tick",
            "consumer_mode": args.mode,
            "iteration": iterations,
            "max_iterations": args.max_iterations,
            "interval_seconds": args.interval_seconds,
            "started_at": now_iso(),
            "launches_agent": args.mode == "live",
        }, indent=2, sort_keys=True))
        cmd_warm_consumer_once(args)
        if args.max_iterations is not None and iterations >= args.max_iterations:
            break
        time.sleep(args.interval_seconds)
    print(json.dumps({
        "mode": "warm_consumer_loop_exit",
        "consumer_mode": args.mode,
        "iterations": iterations,
        "exited_at": now_iso(),
        "launches_agent": args.mode == "live",
    }, indent=2, sort_keys=True))
    return 0


def cmd_warm_daemon_once(args: argparse.Namespace) -> int:
    ensure_dirs()
    forecasters = parse_warm_forecasters(args.forecasters)
    contract_ids = sorted(path.stem for path in CONTRACTS.glob("*.json"))
    if args.contract_id:
        if not contract_path(args.contract_id).exists():
            raise SystemExit(f"missing contract: {contract_path(args.contract_id)}")
        contract_ids = [args.contract_id]
    state = read_json(warm_state_path(), {})
    if not isinstance(state, dict):
        state = {}
    seen = state.get("seen_wake_keys") or {}
    if not isinstance(seen, dict):
        seen = {}
    events: list[dict[str, Any]] = []
    skipped_malformed = []
    for cid in contract_ids:
        try:
            contract = load_contract(cid)
        except SystemExit as exc:
            skipped_malformed.append({"contract_id": cid, "error": str(exc)})
            continue
        outcome = read_json(outcome_path(cid))
        if outcome and not args.include_closed:
            continue
        try:
            forecasts = {
                forecast.get("agent_id"): forecast
                for forecast in latest_forecasts_by_agent(load_forecasts(cid))
                if isinstance(forecast, dict)
            }
        except SystemExit as exc:
            append_market_event(
                "warm_daemon_skipped_malformed_forecast",
                contract_id=cid, error=str(exc))
            skipped_malformed.append({
                "contract_id": cid,
                "error": f"forecast: {exc}",
            })
            continue
        evidence_paths = [contract_path(cid), aggregate_path(cid), outcome_path(cid), score_path(cid)]
        if args.include_calibration:
            evidence_paths.extend([CALIBRATION_SUMMARY, WEIGHTS])
        if args.include_gp233:
            evidence_paths.append(DEFAULT_GP233_LEDGER)
        evidence_paths.extend(args.evidence_path or [])
        for forecaster in forecasters:
            prior = forecasts.get(forecaster["agent_id"])
            reason = None
            if outcome and args.include_closed:
                reason = "resolved_contract_calibration_reflection"
            elif prior is None and len(forecasts) < args.min_forecasts:
                reason = "new_contract_needs_forecast"
            elif prior is not None and args.reactivate_on_evidence:
                reason = "evidence_changed_update_odds"
            if not reason:
                continue
            event = warm_event_payload(
                contract=contract,
                forecaster=forecaster,
                reason=reason,
                evidence_paths=evidence_paths,
                prior_forecast=prior,
            )
            if event["wake_key"] in seen and not args.force:
                continue
            events.append(event)
            if len(events) >= args.max_events:
                break
        if len(events) >= args.max_events:
            break
    written = []
    channel_messages = []
    if args.write:
        for event in events:
            event_id = f"{now_iso().replace(':', '').replace('-', '')}_{event['forecaster']['agent_id']}_{event['wake_key'][:12]}"
            path = wake_event_dir(event["contract_id"]) / f"{slug(event_id)}.json"
            write_json(path, event)
            written.append(relpath(path))
            if args.emit_agent_channel:
                channel_messages.append(emit_warm_agent_message(
                    event=event,
                    event_path=path,
                    from_role=args.from_role,
                    to_role=event["forecaster"].get("role_id") or args.to_role,
                ))
            seen[event["wake_key"]] = {
                "written_at": event["created_at"],
                "path": relpath(path),
                "contract_id": event["contract_id"],
                "agent_id": event["forecaster"]["agent_id"],
                "reason": event["reason"],
                "evidence_fingerprint": event["evidence"]["fingerprint"],
                "channel_message_id": (
                    channel_messages[-1]["message_id"]
                    if args.emit_agent_channel and channel_messages else None
                ),
            }
        state_payload = {
            "updated_at": now_iso(),
            "seen_wake_keys": seen,
            "policy": {
                "launches_agents": False,
                "writes_prompt_ready_wake_events": True,
                "optionally_emits_a2a_agent_messages": bool(args.emit_agent_channel),
                "subscription_safe": True,
            },
        }
        write_json(warm_state_path(), state_payload)
    payload = {
        "generated_at": now_iso(),
        "mode": "warm_forecaster_daemon_once",
        "contract_count_scanned": len(contract_ids),
        "forecasters": forecasters,
        "events_ready": len(events),
        "events_written": written,
        "channel_messages": channel_messages,
        "skipped_malformed_contracts": skipped_malformed[:20],
        "semantics": {
            "dispatches_agents": False,
            "polls_llm_sessions": False,
            "resolves_contracts": False,
            "scores_contracts": False,
            "safe_for_subscription_runtimes": True,
        },
        "events": events,
    }
    refresh_market_state_best_effort(args.contract_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def daemon_once_payload_for_contract_publish(args: argparse.Namespace) -> dict[str, Any]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_warm_daemon_once(args)
    text = buf.getvalue().strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {
            "mode": "warm_contract_publish_hook",
            "parsed": False,
            "raw_output_tail": text[-2000:],
        }
    return {
        "mode": "warm_contract_publish_hook",
        "parsed": True,
        "events_ready": payload.get("events_ready"),
        "events_written": payload.get("events_written"),
        "channel_messages": payload.get("channel_messages"),
        "semantics": payload.get("semantics"),
    }


def cmd_warm_daemon_loop(args: argparse.Namespace) -> int:
    iterations = 0
    while args.max_iterations is None or iterations < args.max_iterations:
        iterations += 1
        print(json.dumps({
            "mode": "warm_forecaster_daemon_loop_tick",
            "iteration": iterations,
            "max_iterations": args.max_iterations,
            "interval_seconds": args.interval_seconds,
            "started_at": now_iso(),
            "launches_agents": False,
        }, indent=2, sort_keys=True))
        cmd_warm_daemon_once(args)
        if args.max_iterations is not None and iterations >= args.max_iterations:
            break
        time.sleep(args.interval_seconds)
    print(json.dumps({
        "mode": "warm_forecaster_daemon_loop_exit",
        "iterations": iterations,
        "exited_at": now_iso(),
        "launches_agents": False,
    }, indent=2, sort_keys=True))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    ensure_dirs()
    contract_ids = sorted(path.stem for path in CONTRACTS.glob("*.json"))
    if args.contract_id:
        if args.contract_id.startswith("scratch_") and not contract_path(args.contract_id).exists():
            scratch, scratch_artifact_path = load_scratch_contract(args.contract_id)
            decision_rows = decision_use_rows(args.contract_id)
            rows = [{
                "contract_id": args.contract_id,
                "scratch_contract": True,
                "next_action": "scratch_only_not_gp230",
                "question": scratch.get("question"),
                "owner": scratch.get("owner"),
                "p_success": scratch.get("p_success"),
                "excluded_from_calibration": bool(scratch.get("excluded_from_calibration")),
                "can_satisfy_membrane": bool(scratch.get("can_satisfy_membrane")),
                "decision_use": {
                    "row_count": len(decision_rows),
                    "latest": decision_rows[-1] if decision_rows else None,
                },
                "artifact_paths": {"contract": relpath(scratch_artifact_path)},
            }]
            print(json.dumps({"contracts": rows, "calibration": calibration_status()}, indent=2))
            return 0
        if not contract_path(args.contract_id).exists():
            raise SystemExit(f"missing contract: {contract_path(args.contract_id)}")
        contract_ids = [args.contract_id]
    rows = status_rows(contract_ids)
    print(json.dumps({"contracts": rows, "calibration": calibration_status()}, indent=2))
    return 0


def cmd_daemon_once(args: argparse.Namespace) -> int:
    ensure_dirs()
    payload = daemon_once_payload(args)
    if args.write:
        write_json(status_path(), payload)
        payload["artifact_path"] = relpath(status_path())
    print(json.dumps(payload, indent=2))
    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="forecast_pool_smoke_") as tmp:
        smoke_root = Path(tmp) / "forecast_pool"
        prediction_ledger = Path(tmp) / "prediction_ledger.jsonl"
        prediction_ledger.write_text(
            json.dumps({
                "prediction_id": "PL-SMOKE-OPEN",
                "predicted_at": "2026-05-12T00:00:00Z",
                "predictor": "smoke",
                "substrate": "forecast_pool_smoke",
                "tier": 1,
                "question": "Will daemon-once see this unresolved row?",
                "resolved_at": None,
            }) + "\n" +
            json.dumps({
                "prediction_id": "PL-SMOKE-CLOSED",
                "predicted_at": "2026-05-12T00:01:00Z",
                "predictor": "smoke",
                "substrate": "forecast_pool_smoke",
                "tier": 1,
                "question": "Resolved row.",
                "resolved_at": "2026-05-12T00:02:00Z",
            }) + "\n"
        )
        configure_root(smoke_root)
        cid = "smoke_patch_compile"

        cmd_init_contract(argparse.Namespace(
            contract_id=cid,
            created_by="smoke",
            layer="micro",
            task_type="patch_compile",
            question="Will the smoke patch compile?",
            objective_resolver="local_smoke_resolver",
            success_threshold="compile_status == pass",
            horizon="immediate",
            budget_agent_minutes=10.0,
            effort_prior_domain=None,
            min_effort_prior_similarity=0.35,
            budget_from_effort_prior=False,
            value_if_success=1.0,
            cost_penalty=0.01,
            risk_penalty=1.0,
            information_value=0.1,
            void_conditions="smoke infra failure",
            baseline_action="skip smoke patch",
            counterfactual_action="run smoke patch",
            externality_hypotheses_json='{"preconditioner": "syntax risk named before execution"}',
            allow_overwrite=False,
        ))
        cmd_add_forecast(argparse.Namespace(
            contract_id=cid,
            agent_id="smoke_agent_high",
            domain="smoke",
            p_success=1.5,
            expected_cost_agent_minutes=8.0,
            p_regression=0.01,
            p_dependency_issue=0.04,
            p_needs_new_lemma=0.0,
            failure_modes_json='{"syntax": 2, "test": 1}',
            specific_failure_mode_ids_json='["syntax"]',
            action_change_recommendation="keep smoke patch minimal",
            forecast_externality_tags_json='["preconditioner"]',
            rationale_short="Smoke high-confidence forecast.",
            read_only_attestation=True,
            allow_overwrite=False,
            belief_update=False,
            update_reason=None,
            evidence_fingerprint=None,
        ))
        cmd_add_forecast(argparse.Namespace(
            contract_id=cid,
            agent_id="smoke_agent_low",
            domain="smoke",
            p_success=-0.2,
            expected_cost_agent_minutes=12.0,
            p_regression=0.10,
            p_dependency_issue=0.20,
            p_needs_new_lemma=0.0,
            failure_modes_json='{"dependency": 1}',
            specific_failure_mode_ids_json='["dependency"]',
            action_change_recommendation=None,
            forecast_externality_tags_json='[]',
            rationale_short="Smoke low-confidence forecast.",
            read_only_attestation=True,
            allow_overwrite=False,
            belief_update=False,
            update_reason=None,
            evidence_fingerprint=None,
        ))
        cmd_add_forecast(argparse.Namespace(
            contract_id=cid,
            agent_id="smoke_agent_low",
            domain="smoke",
            p_success=0.65,
            expected_cost_agent_minutes=9.0,
            p_regression=0.08,
            p_dependency_issue=0.12,
            p_needs_new_lemma=0.0,
            failure_modes_json='{"dependency": 0.5, "syntax": 0.5}',
            specific_failure_mode_ids_json='["syntax"]',
            action_change_recommendation="odds update after smoke evidence fingerprint changed",
            forecast_externality_tags_json='["belief_update"]',
            rationale_short="Smoke belief update forecast.",
            read_only_attestation=True,
            allow_overwrite=False,
            belief_update=True,
            update_reason="evidence_changed_update_odds",
            evidence_fingerprint="smoke-evidence-fingerprint-v2",
        ))
        aggregate_payload = aggregate(cid)
        write_json(aggregate_path(cid), aggregate_payload)
        cmd_record_decision_use(argparse.Namespace(
            contract_id=cid,
            tick_id="smoke_tick",
            owner="smoke_rd",
            decision_stage="pretick",
            used_for="run",
            decision_changed_bool=True,
            forecast_delta="aggregate moved action from skip to run",
            old_action="skip smoke patch",
            new_action="run smoke patch",
            failure_modes_adopted_json='["syntax"]',
            ignored_forecast_reason=None,
            notes="smoke decision-use row",
            allow_missing_aggregate=False,
        ))
        cmd_resolve(argparse.Namespace(
            contract_id=cid,
            success_bool=True,
            actual_cost_agent_minutes=9.0,
            compile_status="pass",
            sorry_delta=0,
            goal_delta=1,
            error_type=None,
            artifact_hash="smoke-artifact-hash",
            artifact_path=str(smoke_root / "artifact.txt"),
            resolution_note="local smoke resolution",
            realized_failure_mode_ids_json='["syntax"]',
            failure_mode_preconditioner_used=True,
            preconditioner_source="smoke_agent_high",
            preconditioner_effect="kept smoke patch minimal",
            decision_changed_bool=True,
            old_next_action="skip smoke patch",
            new_next_action="run smoke patch",
            externality_tags_json='["preconditioner"]',
            negative_externality_tags_json='[]',
            counterfactual_value_bucket="low",
            changed_by_forecast_ids_json='["smoke_agent_high"]',
            voided=False,
            allow_no_independent_forecaster=True,
            no_independent_forecaster_reason=(
                "smoke test uses synthetic non-provider forecaster ids"
            ),
        ))
        cmd_score(argparse.Namespace(contract_id=cid))
        cmd_calibrate(argparse.Namespace(min_domain_n=1, write=True, write_weights=True))
        cmd_scratch_forecast(argparse.Namespace(
            owner="codex:RD",
            domain="scratch_smoke",
            task_type="micro_contract",
            question="Will scratch smoke status remain readable?",
            p_success=0.5,
            expected_cost_agent_minutes=1.0,
            tail_insurance_premium=0.5,
            tail_loss_magnitude=1.0,
            tail_downside_worry=0.0,
            tail_upside_surprise=0.0,
            verbalized_confidence=None,
            predicted_self_error_ratio=None,
            failure_modes_json='{"scratch_schema_regression": 1.0}',
            rationale_short="Scratch status smoke.",
            resolution_predicate="TRUE iff scratch artifact can be read by status.",
            context_json='{}',
            notes="smoke scratch row",
            slug="scratch_status_smoke",
            also_prediction_ledger=False,
            no_prediction_ledger=True,
            prediction_id=None,
            prediction_ledger=prediction_ledger,
            ack_uncertified=True,
        ))
        scratch_rows = read_jsonl(SCRATCH / "scratch_ledger.jsonl")
        scratch_id = str(scratch_rows[-1].get("scratch_id") or "")
        scratch_status = status_rows([scratch_id])[0]
        cmd_record_decision_use(argparse.Namespace(
            contract_id=scratch_id,
            tick_id="smoke_scratch_tick",
            owner="smoke_rd",
            decision_stage="manual",
            used_for="split",
            decision_changed_bool=True,
            forecast_delta=None,
            old_action="ignore scratch",
            new_action="read scratch status",
            failure_modes_adopted_json='["scratch_schema_regression"]',
            ignored_forecast_reason=None,
            notes="scratch decision-use smoke row",
            allow_missing_aggregate=True,
            dedupe=False,
        ))
        scratch_decisions = decision_use_rows(scratch_id)
        scratch_status_after_decision = status_rows([scratch_id])[0]
        status_row = status_rows([cid])[0]
        status_payload = {
            "contract": contract_path(cid).exists(),
            "forecast_count": status_row["forecast_count"],
            "forecast_history_count": status_row["forecast_history_count"],
            "aggregate": status_row["has_aggregate"],
            "outcome": status_row["resolved"],
            "score": status_row["has_score"],
            "calibration_summary": CALIBRATION_SUMMARY.exists(),
            "calibration_weights": WEIGHTS.exists(),
        }
        daemon_payload = daemon_once_payload(argparse.Namespace(
            contract_id=None,
            prediction_ledger=prediction_ledger,
            ledger_limit=5,
            write=True,
        ))
        write_json(status_path(), daemon_payload)
        if not status_path().exists():
            raise SystemExit("smoke failed: daemon_once_status_artifact")
        if daemon_payload["prediction_ledger"]["unresolved_count"] != 1:
            raise SystemExit("smoke failed: prediction_ledger_unresolved_count")
        if daemon_payload["action_counts"].get("closed") != 1:
            raise SystemExit("smoke failed: daemon_once_contract_action")
        failures = [name for name, ok in status_payload.items() if name not in {"forecast_count", "forecast_history_count"} and not ok]
        if status_row["forecast_count"] != 2:
            failures.append("forecast_count")
        if status_row["forecast_history_count"] != 3:
            failures.append("forecast_history_count")
        forecast_history = load_forecasts(cid)
        active_forecasts = latest_forecasts_by_agent(forecast_history)
        clipped = sorted(fc["p_success"] for fc in active_forecasts)
        history_clipped = sorted(fc["p_success"] for fc in forecast_history)
        if clipped != [0.65, 0.98] or history_clipped != [0.02, 0.65, 0.98]:
            failures.append("probability_clipping")
        score_payload = read_json(score_path(cid), {})
        if not (score_payload.get("externality_audit") or {}).get("outcome_fields"):
            failures.append("externality_audit_fields")
        if score_payload.get("forecast_history_count") != 3:
            failures.append("score_history_count")
        if not scratch_status.get("scratch_contract"):
            failures.append("scratch_status_read_model")
        if scratch_status.get("next_action") != "scratch_only_not_gp230":
            failures.append("scratch_next_action")
        if scratch_status.get("p_success") != 0.5:
            failures.append("scratch_p_success")
        if len(scratch_decisions) != 1:
            failures.append("scratch_decision_use_row")
        if ((scratch_status_after_decision.get("decision_use") or {}).get("row_count")) != 1:
            failures.append("scratch_decision_use_status")
        state_payload = materialize_market_state(cid)
        contract_state = read_json(MARKET_STATE_CONTRACTS / f"{cid}.json", {})
        global_state = read_json(MARKET_STATE / "global_health.json", {})
        reflexive_state = read_json(REFLEXIVE_INSIGHTS, {})
        maintenance_state = read_json(MAINTENANCE_PLAN, {})
        if not state_payload.get("contracts_written"):
            failures.append("market_state_written")
        if (contract_state.get("decision_use") or {}).get("row_count") != 1:
            failures.append("decision_use_read_model")
        if (contract_state.get("effective_independence") or {}).get("effective_n") != 2:
            failures.append("effective_independence_read_model")
        if (contract_state.get("lifecycle") or {}).get("state") != "resolved_scored":
            failures.append("market_state_lifecycle")
        if (global_state.get("decision_use") or {}).get("rows") != 2:
            failures.append("global_decision_use_summary")
        if (reflexive_state.get("counts") or {}).get("forecast_update_files") != 1:
            failures.append("reflexive_forecast_update_health")
        if not reflexive_state.get("insight_count"):
            failures.append("reflexive_insight_model")
        if (maintenance_state.get("counts") or {}).get("decision_use_rows") != 2:
            failures.append("maintenance_plan")
        if failures:
            raise SystemExit(f"smoke failed: {', '.join(failures)}")
        print(json.dumps({
            "smoke": "pass",
            "root": str(smoke_root),
            "artifacts": status_payload,
            "daemon_once": {
                "status_artifact": str(status_path()),
                "unresolved_prediction_rows": daemon_payload["prediction_ledger"]["unresolved_count"],
                "action_counts": daemon_payload["action_counts"],
            },
            "status": status_row,
            "clipped_p_success": clipped,
            "history_p_success": history_clipped,
        }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init-contract")
    p.add_argument("--contract-id")
    p.add_argument("--created-by", default="codex:RD")
    p.add_argument("--layer", required=True, choices=sorted(LAYERS))
    p.add_argument("--task-type", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--objective-resolver", required=True)
    p.add_argument("--success-threshold", required=True)
    p.add_argument("--horizon", required=True)
    p.add_argument("--budget-agent-minutes", type=float, default=60.0)
    p.add_argument("--effort-prior-domain", default=None)
    p.add_argument("--min-effort-prior-similarity", type=float, default=0.35)
    p.add_argument("--budget-from-effort-prior", action="store_true")
    p.add_argument("--value-if-success", type=float, default=1.0)
    p.add_argument("--cost-penalty", type=float, default=0.01)
    p.add_argument("--risk-penalty", type=float, default=1.0)
    p.add_argument("--information-value", type=float, default=0.0)
    p.add_argument("--void-conditions", default="infra failure, resolver unavailable, or contract artifact missing")
    p.add_argument("--baseline-action", default=None)
    p.add_argument("--counterfactual-action", default=None)
    p.add_argument("--externality-hypotheses-json", default="{}")
    p.add_argument("--allow-overwrite", action="store_true")
    p.add_argument(
        "--emit-warm-wake",
        action="store_true",
        help="After writing the contract, immediately publish warm forecaster wake/A2A messages.",
    )
    p.add_argument(
        "--warm-forecasters",
        default="claude:claude_forecaster:forecasting_agent,codex:codex_forecaster:forecasting_agent",
    )
    p.add_argument("--warm-min-forecasts", type=int, default=2)
    p.add_argument("--warm-max-events", type=int, default=2)
    p.add_argument("--warm-include-calibration", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--warm-include-gp233", action="store_true")
    p.add_argument("--warm-evidence-path", type=Path, action="append", default=[])
    p.add_argument("--warm-force", action="store_true")
    p.add_argument("--warm-write", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--warm-emit-agent-channel", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--warm-from-role", default="research_director")
    p.add_argument("--consumes-surfaced", default=None,
                   help="RC3 #27: the FULL live void-audit surfaced id "
                        "this tick's probe consumes. Validated AT "
                        "contract-init for NS/Track-B tasks (probe bound "
                        "to the surfaced set at selection, not "
                        "free-recalled); stored in the contract.")
    p.set_defaults(func=cmd_init_contract)

    p = sub.add_parser("add-forecast")
    p.add_argument("--contract-id", required=True)
    p.add_argument("--agent-id", required=True)
    p.add_argument("--domain", default="general")
    p.add_argument("--p-success", type=float, required=True)
    p.add_argument("--expected-cost-agent-minutes", type=float, default=None)
    p.add_argument("--p-regression", type=float, default=0.05)
    p.add_argument("--p-dependency-issue", type=float, default=0.05)
    p.add_argument("--p-needs-new-lemma", type=float, default=0.05)
    p.add_argument("--tail-insurance-premium", type=float, default=None,
                   help="F8 legacy probability-like magnitude in [0,1]. Per F36 sign is per-agent-family; "
                        "prefer --tail-downside-worry + --tail-upside-surprise.")
    p.add_argument("--tail-loss-magnitude", type=float, default=None)
    p.add_argument("--tail-downside-worry", type=float, default=None,
                   help="F35 signed-tail channel (1-100): suspicion that actual outcome will "
                        "be MUCH WORSE than p_success. Use alongside --tail-upside-surprise.")
    p.add_argument("--tail-upside-surprise", type=float, default=None,
                   help="F35 signed-tail channel (1-100): suspicion that actual outcome will "
                        "be MUCH BETTER than p_success. Use alongside --tail-downside-worry.")
    p.add_argument("--agent-family", default=None,
                   help="F36 per-agent dispatch tag (claude/codex). Defaults to derive_agent_family(agent_id).")
    p.add_argument("--allow-missing-best-practice", action="store_true",
                   help="Bypass the F37/F39/F41 best-practice gate (rejects claude emissions without "
                        "signed-tail by default). Use only when operator explicitly knows the bypass is justified.")
    p.add_argument("--verbalized-confidence", type=float, default=None)
    p.add_argument("--predicted-self-error-ratio", type=float, default=None)
    # F56 bid-ask spread channel (codex_mini + deepseek specialist; rho=+0.69/+0.61 N=15).
    p.add_argument("--p-buy-yes-max", type=float, default=None,
                   help="F56 bid-ask: highest p at which the forecaster would buy YES. "
                        "Pair with --p-sell-yes-min; spread = p_sell - p_buy is the channel.")
    p.add_argument("--p-sell-yes-min", type=float, default=None,
                   help="F56 bid-ask: lowest p at which the forecaster would sell YES. "
                        "Must satisfy p_buy_yes_max <= p_sell_yes_min.")
    # F61 self-predicted Brier interval channel (b_mid/b_width per channel_routing).
    p.add_argument("--predicted-brier-lo", type=float, default=None,
                   help="F61 self-predicted Brier interval lower bound (0..1). "
                        "Pair with --predicted-brier-hi; b_mid + b_width are derived.")
    p.add_argument("--predicted-brier-hi", type=float, default=None,
                   help="F61 self-predicted Brier interval upper bound (0..1). "
                        "Must satisfy predicted_brier_lo <= predicted_brier_hi.")
    p.add_argument("--failure-modes-json", default="{}")
    p.add_argument("--specific-failure-mode-ids-json", default="[]")
    p.add_argument("--action-change-recommendation", default=None)
    p.add_argument("--forecast-externality-tags-json", default="[]")
    p.add_argument("--rationale-short", required=True)
    p.add_argument("--read-only-attestation", action="store_true")
    p.add_argument("--allow-overwrite", action="store_true")
    p.add_argument("--belief-update", action="store_true")
    p.add_argument("--update-reason", default=None)
    p.add_argument("--evidence-fingerprint", default=None)
    p.set_defaults(func=cmd_add_forecast)

    p = sub.add_parser("aggregate")
    p.add_argument("--contract-id", required=True)
    p.set_defaults(func=cmd_aggregate)

    p = sub.add_parser("resolve")
    p.add_argument("--contract-id", required=True)
    p.add_argument("--success-bool", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--actual-cost-agent-minutes", type=float, default=None)
    p.add_argument("--compile-status", default=None)
    p.add_argument("--sorry-delta", type=int, default=None)
    p.add_argument("--goal-delta", type=int, default=None)
    p.add_argument("--error-type", default=None)
    p.add_argument("--artifact-hash", default=None)
    p.add_argument("--artifact-path", default=None)
    p.add_argument("--resolution-note", default="")
    p.add_argument("--realized-failure-mode-ids-json", default="[]")
    p.add_argument("--failure-mode-preconditioner-used", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--preconditioner-source", default=None)
    p.add_argument("--preconditioner-effect", default=None)
    p.add_argument("--decision-changed-bool", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--old-next-action", default=None)
    p.add_argument("--new-next-action", default=None)
    p.add_argument("--externality-tags-json", default="[]")
    p.add_argument("--negative-externality-tags-json", default="[]")
    p.add_argument("--counterfactual-value-bucket", default=None)
    p.add_argument("--changed-by-forecast-ids-json", default="[]")
    p.add_argument("--voided", action="store_true")
    p.add_argument(
        "--allow-no-independent-forecaster",
        "--allow-no-codex",
        dest="allow_no_independent_forecaster",
        action="store_true",
        help=(
            "Override the ORDERING guard (resolve without a recognized "
            "independent forecaster bet). Requires "
            "--no-independent-forecaster-reason; logged to outcome. "
            "--allow-no-codex is a backward-compatible alias."
        ),
    )
    p.add_argument(
        "--no-independent-forecaster-reason",
        "--no-codex-reason",
        dest="no_independent_forecaster_reason",
        default=None,
        help=(
            "Required justification when --allow-no-independent-forecaster "
            "is used. --no-codex-reason is a backward-compatible alias."
        ),
    )
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("score")
    p.add_argument("--contract-id", required=True)
    p.set_defaults(func=cmd_score)

    p = sub.add_parser(
        "prompt-template",
        help="Emit the recommended elicitation prompt block for the given agent_id "
             "(F37 signed-tail + F39 balance instruction, agent-family-tuned per F41). "
             "RDs call this to construct the right prompt without remembering which "
             "fragments are required for which agent family.",
    )
    p.add_argument("--agent-id", required=True,
                   help="Agent identifier (e.g. claude, codex, claude_rd, codex_55, codex_54mini).")
    p.add_argument("--format", choices=("text", "json"), default="text",
                   help="text = just the prompt block; json = full config dict.")
    p.set_defaults(func=cmd_prompt_template)

    p = sub.add_parser("scratch-forecast")
    p.add_argument("--owner", default="codex:RD")
    p.add_argument("--domain", default="general")
    p.add_argument("--task-type", default="artisanal")
    p.add_argument("--question", required=True)
    p.add_argument("--p-success", type=float, required=True)
    p.add_argument("--expected-cost-agent-minutes", type=float, default=None)
    p.add_argument("--tail-insurance-premium", type=float, required=True,
                   help="F8 legacy probability-like magnitude in [0,1]. Per F36 sign is per-agent-family; "
                        "prefer the signed-tail pair below.")
    p.add_argument("--tail-loss-magnitude", type=float, required=True)
    p.add_argument("--tail-downside-worry", type=float, default=None,
                   help="F35 signed-tail (1-100): suspicion outcome will be MUCH WORSE than p_success. "
                        "Recommended alongside --tail-upside-surprise; superior to magnitude alone.")
    p.add_argument("--tail-upside-surprise", type=float, default=None,
                   help="F35 signed-tail (1-100): suspicion outcome will be MUCH BETTER than p_success.")
    p.add_argument("--agent-family", default=None,
                   help="F36 per-agent dispatch tag (claude/codex). Defaults to "
                        "derive_agent_family(owner) — substring-falls-back so e.g. owner='claude:RD' "
                        "resolves to family='claude'.")
    p.add_argument("--allow-missing-best-practice", action="store_true",
                   help="Bypass the F37/F39/F41 best-practice gate (rejects claude scratch without "
                        "signed-tail by default). Use only with explicit operator justification.")
    p.add_argument("--verbalized-confidence", type=float, default=None)
    p.add_argument("--predicted-self-error-ratio", type=float, default=None)
    # F56 bid-ask spread channel (codex_mini + deepseek specialist; rho=+0.69/+0.61 N=15).
    p.add_argument("--p-buy-yes-max", type=float, default=None,
                   help="F56 bid-ask: highest p at which the forecaster would buy YES. "
                        "Pair with --p-sell-yes-min; spread = p_sell - p_buy is the channel.")
    p.add_argument("--p-sell-yes-min", type=float, default=None,
                   help="F56 bid-ask: lowest p at which the forecaster would sell YES. "
                        "Must satisfy p_buy_yes_max <= p_sell_yes_min.")
    # F61 self-predicted Brier interval channel (b_mid/b_width per channel_routing).
    p.add_argument("--predicted-brier-lo", type=float, default=None,
                   help="F61 self-predicted Brier interval lower bound (0..1). "
                        "Pair with --predicted-brier-hi; b_mid + b_width are derived.")
    p.add_argument("--predicted-brier-hi", type=float, default=None,
                   help="F61 self-predicted Brier interval upper bound (0..1). "
                        "Must satisfy predicted_brier_lo <= predicted_brier_hi.")
    p.add_argument("--failure-modes-json", default="{}")
    p.add_argument("--rationale-short", required=True)
    p.add_argument("--resolution-predicate", default=None)
    p.add_argument("--context-json", default="{}")
    p.add_argument("--notes", default=None)
    p.add_argument("--slug", default=None)
    p.add_argument("--also-prediction-ledger", action="store_true",
                   help=("Force an explicit PATTERN-012 mirror row. RD-like "
                         "scratch owners mirror by default; forecaster-role "
                         "owners do not. The scratch forecast remains "
                         "uncertified and excluded from GP-230 calibration."))
    p.add_argument("--no-prediction-ledger", action="store_true",
                   help="Disable the default PATTERN-012 mirror for RD-like scratch owners.")
    p.add_argument("--prediction-id", default=None,
                   help="Optional prediction_id for --also-prediction-ledger.")
    p.add_argument("--prediction-ledger", type=Path,
                   default=DEFAULT_PREDICTION_LEDGER)
    p.add_argument("--ack-uncertified", action="store_true")
    p.set_defaults(func=cmd_scratch_forecast)

    p = sub.add_parser("scratch-resolve")
    p.add_argument("--prediction-id", default=None,
                   help="Prediction ledger id to resolve, for mirrored scratch forecasts.")
    p.add_argument("--scratch-path", type=Path, default=None,
                   help="Scratch forecast artifact path; may be absolute or repo-relative.")
    p.add_argument("--actual-outcome", required=True)
    p.add_argument("--actual-outcome-bucket", required=True)
    p.add_argument("--resolution-summary", required=True)
    p.add_argument("--resolution-artifact", default=None)
    p.add_argument("--resolved-at", default=None,
                   help="Optional ISO timestamp; defaults to now.")
    p.add_argument("--prediction-ledger", type=Path,
                   default=DEFAULT_PREDICTION_LEDGER)
    p.add_argument("--allow-reresolve", action="store_true")
    p.set_defaults(func=cmd_scratch_resolve)

    p = sub.add_parser("calibrate")
    p.add_argument("--min-domain-n", type=int, default=2)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-weights", action="store_true")
    p.set_defaults(func=cmd_calibrate)

    p = sub.add_parser("status")
    p.add_argument("--contract-id")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("externalities")
    p.add_argument("--write", action="store_true")
    p.add_argument("--prediction-ledger", type=Path, default=DEFAULT_PREDICTION_LEDGER)
    p.set_defaults(func=cmd_externalities)

    p = sub.add_parser("daemon-once")
    p.add_argument("--contract-id")
    p.add_argument("--prediction-ledger", type=Path, default=DEFAULT_PREDICTION_LEDGER)
    p.add_argument("--ledger-limit", type=int, default=5)
    p.add_argument("--write", action="store_true")
    p.set_defaults(func=cmd_daemon_once)

    p = sub.add_parser("materialize-state")
    p.add_argument("--contract-id")
    p.set_defaults(func=cmd_materialize_state)

    p = sub.add_parser("record-decision-use")
    p.add_argument("--contract-id", required=True)
    p.add_argument("--tick-id", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument(
        "--decision-stage",
        choices=["pretick", "membrane", "posttick", "manual"],
        default="pretick",
    )
    p.add_argument(
        "--used-for",
        choices=["run", "split", "defer", "kill", "ask_more", "ignore", "override"],
        required=True,
    )
    p.add_argument("--decision-changed-bool", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--forecast-delta", default=None)
    p.add_argument("--old-action", default=None)
    p.add_argument("--new-action", default=None)
    p.add_argument("--failure-modes-adopted-json", default="[]")
    p.add_argument("--ignored-forecast-reason", default=None)
    p.add_argument("--notes", default=None)
    p.add_argument("--allow-missing-aggregate", action="store_true")
    p.add_argument("--dedupe", action="store_true")
    p.set_defaults(func=cmd_record_decision_use)

    p = sub.add_parser("warm-daemon-once")
    p.add_argument("--contract-id")
    p.add_argument(
        "--forecasters",
        default="claude:claude_forecaster:forecasting_agent,codex:codex_forecaster:forecasting_agent",
        help="Comma-separated runtime:agent_id[:role_id] entries. Runtime is claude or codex.",
    )
    p.add_argument("--min-forecasts", type=int, default=2)
    p.add_argument("--max-events", type=int, default=20)
    p.add_argument("--reactivate-on-evidence", action="store_true")
    p.add_argument("--include-closed", action="store_true")
    p.add_argument("--include-calibration", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--include-gp233", action="store_true")
    p.add_argument("--evidence-path", type=Path, action="append", default=[])
    p.add_argument("--force", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument(
        "--emit-agent-channel",
        action="store_true",
        help="Also write a role-inbox A2A request pointing at each wake event.",
    )
    p.add_argument("--from-role", default="research_director")
    p.add_argument("--to-role", default="forecasting_agent")
    p.set_defaults(func=cmd_warm_daemon_once)

    p = sub.add_parser("warm-daemon-loop")
    p.add_argument("--contract-id")
    p.add_argument(
        "--forecasters",
        default="claude:claude_forecaster:forecasting_agent,codex:codex_forecaster:forecasting_agent",
        help="Comma-separated runtime:agent_id[:role_id] entries. Runtime is claude or codex.",
    )
    p.add_argument("--min-forecasts", type=int, default=2)
    p.add_argument("--max-events", type=int, default=20)
    p.add_argument("--reactivate-on-evidence", action="store_true")
    p.add_argument("--include-closed", action="store_true")
    p.add_argument("--include-calibration", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--include-gp233", action="store_true")
    p.add_argument("--evidence-path", type=Path, action="append", default=[])
    p.add_argument("--force", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument(
        "--emit-agent-channel",
        action="store_true",
        help="Also write a role-inbox A2A request pointing at each wake event.",
    )
    p.add_argument("--from-role", default="research_director")
    p.add_argument("--to-role", default="forecasting_agent")
    p.add_argument("--interval-seconds", type=float, default=300.0)
    p.add_argument("--max-iterations", type=int, default=None)
    p.set_defaults(func=cmd_warm_daemon_loop)

    p = sub.add_parser("warm-consumer-once")
    p.add_argument("--role-id", default="forecasting_agent")
    p.add_argument("--runtime", choices=["claude", "codex"], default=None)
    p.add_argument("--agent-id", default=None)
    p.add_argument("--contract-id", default=None)
    p.add_argument("--max-messages", type=int, default=1)
    p.add_argument("--include-claimed", action="store_true")
    p.add_argument(
        "--mode",
        choices=["preview", "stub", "live"],
        default="live",
        help="live runs the subscription CLI once (default); preview is an explicit dry run; stub claims/closes without launching.",
    )
    p.add_argument("--consumer-id", default=None)
    p.add_argument("--timeout-seconds", type=int, default=900)
    p.add_argument("--no-live-runtime", action="store_true")
    p.add_argument("--require-forecast-or-no-update", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--use-resume", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--resume-max-ticks", type=int, default=100)
    p.add_argument("--resume-max-age-hours", type=float, default=24.0)
    p.set_defaults(func=cmd_warm_consumer_once)

    p = sub.add_parser("warm-consumer-loop")
    p.add_argument("--role-id", default="forecasting_agent")
    p.add_argument("--runtime", choices=["claude", "codex"], default=None)
    p.add_argument("--agent-id", default=None)
    p.add_argument("--contract-id", default=None)
    p.add_argument("--max-messages", type=int, default=1)
    p.add_argument("--include-claimed", action="store_true")
    p.add_argument(
        "--mode",
        choices=["preview", "stub", "live"],
        default="live",
        help="live runs the subscription CLI once (default); preview is an explicit dry run; stub claims/closes without launching.",
    )
    p.add_argument("--consumer-id", default=None)
    p.add_argument("--timeout-seconds", type=int, default=900)
    p.add_argument("--no-live-runtime", action="store_true")
    p.add_argument("--require-forecast-or-no-update", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--use-resume", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--resume-max-ticks", type=int, default=100)
    p.add_argument("--resume-max-age-hours", type=float, default=24.0)
    p.add_argument("--interval-seconds", type=float, default=300.0)
    p.add_argument("--max-iterations", type=int, default=None)
    p.set_defaults(func=cmd_warm_consumer_loop)

    p = sub.add_parser("smoke")
    p.set_defaults(func=cmd_smoke)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "success_bool", True) is None and args.cmd == "resolve" \
            and not getattr(args, "voided", False):
        raise SystemExit("resolve requires --success-bool or --no-success-bool "
                         "(exempt only when --voided: a void makes NO success "
                         "claim by definition — forcing true/false on a "
                         "void-unrun would be fabrication; downstream no-score "
                         "paths already key on `voided or success_bool is None`)")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
