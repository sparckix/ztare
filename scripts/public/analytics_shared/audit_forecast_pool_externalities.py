#!/usr/bin/env python3
"""Audit forecast-pool calibration, routing, and externalities.

This report is deliberately read-only by default. It computes what the current
forecast-pool artifacts can already support, and names where externalities still
live only in prose.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = REPO / "analytics/public/forecast_pool"
DEFAULT_GP233 = REPO / "analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md"
DEFAULT_PREDICTION_LEDGER = REPO / "analytics/public/ledgers/prediction/prediction_ledger.jsonl"
DEFAULT_FORECASTING_CHANNEL = REPO / "org/channels/forecasting_agent"
DEFAULT_DECISION_USE_LEDGER = DEFAULT_ROOT / "decision_use/decision_use_ledger.jsonl"
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


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def median(values: list[float]) -> float | None:
    return round(statistics.median(values), 4) if values else None


def mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 4) if values else None


def normalize_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9:_-]+", "", str(value or "").strip().lower())


def canonical_agent_id(value: Any) -> str | None:
    raw = str(value or "")
    if raw in CANONICAL_AGENT_IDS:
        return raw
    normalized = normalize_identifier(raw)
    return AGENT_ID_ALIASES.get(normalized)


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


def load_score_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "scores").glob("*.json")):
        score = read_json(path, {})
        if not isinstance(score, dict):
            continue
        outcome = score.get("outcome") or {}
        for row in score.get("scores") or []:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["contract_id"] = score.get("contract_id") or path.stem
            item["score_path"] = rel(path)
            item["outcome"] = outcome
            rows.append(item)
    return rows


def load_contracts(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "contracts").glob("*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            out[payload.get("contract_id") or path.stem] = payload
    return out


def load_outcomes(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "outcomes").glob("*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            out[payload.get("contract_id") or path.stem] = payload
    return out


def load_aggregates(root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "aggregates").glob("*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            out[payload.get("contract_id") or path.stem] = payload
    return out


def load_forecasts(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "forecasts").glob("*/*.json")):
        payload = read_json(path, {})
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["forecast_path"] = rel(path)
            rows.append(payload)
    return rows


def term_counts(notes: list[str], terms: list[str]) -> dict[str, int]:
    lowered = [note.lower() for note in notes]
    return {term: sum(term in note for note in lowered) for term in terms}


def calibration_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    briers = [float(row["brier"]) for row in rows if row.get("brier") is not None]
    log_scores = [float(row["log_score"]) for row in rows if row.get("log_score") is not None]
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[str(row.get("domain") or "unknown")].append(row)
    domains = []
    for domain, items in sorted(by_domain.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        db = [float(row["brier"]) for row in items if row.get("brier") is not None]
        ratios = [
            float(row["expected_cost_agent_minutes"]) / float(row["actual_cost_agent_minutes"])
            for row in items
            if row.get("expected_cost_agent_minutes") is not None
            and row.get("actual_cost_agent_minutes") is not None
            and float(row["actual_cost_agent_minutes"]) > 0
        ]
        domains.append({
            "domain": domain,
            "score_rows": len(items),
            "mean_brier": mean(db),
            "brier_skill_vs_uniform_binary": (
                None if not db else round(1.0 - (statistics.mean(db) / 0.25), 4)
            ),
            "median_expected_over_actual": median(ratios),
        })
    return {
        "score_rows": len(rows),
        "mean_brier": mean(briers),
        "mean_log_score": mean(log_scores),
        "brier_skill_vs_uniform_binary": (
            None if not briers else round(1.0 - (statistics.mean(briers) / 0.25), 4)
        ),
        "top_domains": domains[:12],
    }


def effort_block(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [
        float(row["cost_error_agent_minutes"])
        for row in rows
        if row.get("cost_error_agent_minutes") is not None
    ]
    ratios = [
        float(row["expected_cost_agent_minutes"]) / float(row["actual_cost_agent_minutes"])
        for row in rows
        if row.get("expected_cost_agent_minutes") is not None
        and row.get("actual_cost_agent_minutes") is not None
        and float(row["actual_cost_agent_minutes"]) > 0
    ]
    return {
        "median_cost_error_agent_minutes": median(errors),
        "mean_cost_error_agent_minutes": mean(errors),
        "median_expected_over_actual": median(ratios),
        "large_overestimate_rows": sum(1 for ratio in ratios if ratio >= 3.0),
        "large_underestimate_rows": sum(1 for ratio in ratios if ratio <= 0.5),
    }


def routing_block(aggregates: dict[str, dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    ev_by_hint: dict[str, list[float]] = defaultdict(list)
    for cid, agg in aggregates.items():
        hint = str(agg.get("routing_hint") or "missing")
        outcome = outcomes.get(cid)
        if not outcome or outcome.get("voided"):
            matrix[hint]["unresolved"] += 1
            continue
        success = "success" if outcome.get("success_bool") else "failure"
        matrix[hint][success] += 1
        actual = outcome.get("actual_cost_agent_minutes")
        p_success = ((agg.get("aggregate") or {}).get("p_success"))
        if actual is not None and p_success is not None:
            ev_by_hint[hint].append(float(p_success) - (float(actual) / 100.0))
    return {
        "hint_confusion": {hint: dict(counts) for hint, counts in sorted(matrix.items())},
        "approx_realized_ev_proxy_by_hint": {
            hint: mean(vals) for hint, vals in sorted(ev_by_hint.items())
        },
    }


def market_depth_block(root: Path, contracts: dict[str, dict[str, Any]], forecasts: list[dict[str, Any]]) -> dict[str, Any]:
    by_contract: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for forecast in forecasts:
        by_contract[str(forecast.get("contract_id"))].append(forecast)
    bins = Counter()
    spreads: list[float] = []
    for cid in contracts:
        items = by_contract.get(cid, [])
        count = len(items)
        if count == 0:
            bins["0"] += 1
        elif count == 1:
            bins["1"] += 1
        elif count == 2:
            bins["2"] += 1
        else:
            bins["3+"] += 1
        ps = [
            float(item["p_success"])
            for item in items
            if item.get("p_success") is not None
        ]
        if len(ps) >= 2:
            spreads.append(max(ps) - min(ps))
    update_files = list((root / "forecast_updates").glob("*/*.json"))
    return {
        "forecast_count_bins_by_contract": dict(sorted(bins.items())),
        "mean_forecasts_per_contract": (
            None if not contracts else round(len(forecasts) / len(contracts), 4)
        ),
        "contracts_with_2plus_forecasts": sum(
            1 for cid in contracts if len(by_contract.get(cid, [])) >= 2
        ),
        "median_p_success_spread_when_2plus": median(spreads),
        "mean_p_success_spread_when_2plus": mean(spreads),
        "forecast_update_files": len(update_files),
        "contracts_with_forecast_updates": len({path.parent.name for path in update_files}),
    }


def identity_hygiene_block(forecasts: list[dict[str, Any]]) -> dict[str, Any]:
    raw_counts = Counter(str(forecast.get("agent_id")) for forecast in forecasts)
    noncanonical = Counter({
        agent_id: count
        for agent_id, count in raw_counts.items()
        if agent_id not in CANONICAL_AGENT_IDS
    })
    post_binding = Counter()
    alias_view = Counter()
    ambiguous = Counter()
    for forecast in forecasts:
        raw = str(forecast.get("agent_id"))
        canonical = canonical_agent_id(raw)
        if canonical:
            alias_view[canonical] += 1
        else:
            ambiguous[raw] += 1
        forecasted_at = parse_iso(forecast.get("forecasted_at"))
        if (
            forecasted_at
            and forecasted_at >= AGENT_ID_BINDING_DATE
            and raw not in CANONICAL_AGENT_IDS
        ):
            post_binding[raw] += 1
    return {
        "unique_agent_ids": len(raw_counts),
        "top_agent_ids": raw_counts.most_common(20),
        "noncanonical_agent_id_count": len(noncanonical),
        "noncanonical_forecast_rows": sum(noncanonical.values()),
        "noncanonical_top20": noncanonical.most_common(20),
        "post_binding_noncanonical_rows": sum(post_binding.values()),
        "post_binding_noncanonical_top20": post_binding.most_common(20),
        "read_time_alias_view": dict(sorted(alias_view.items())),
        "ambiguous_alias_top20": ambiguous.most_common(20),
    }


def domain_hygiene_block(forecasts: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    forecast_domains = Counter(str(forecast.get("domain") or "unknown") for forecast in forecasts)
    score_domains = Counter(str(row.get("domain") or "unknown") for row in rows)
    family_counts = Counter(domain_family(domain) for domain in forecast_domains.elements())
    alias_families: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for domain, count in forecast_domains.items():
        family = domain_family(domain)
        if family != domain:
            alias_families[family].append((domain, count))
    return {
        "unique_forecast_domains": len(forecast_domains),
        "unique_score_domains": len(score_domains),
        "top_forecast_domains": forecast_domains.most_common(20),
        "top_score_domains": score_domains.most_common(20),
        "domain_family_counts": family_counts.most_common(20),
        "alias_family_top20": {
            family: sorted(items, key=lambda item: (-item[1], item[0]))[:12]
            for family, items in sorted(alias_families.items())
            if len(items) > 1
        },
    }


def failure_mode_quality_block(forecasts: list[dict[str, Any]]) -> dict[str, Any]:
    entropies: list[float] = []
    other_mass = 0.0
    high_entropy = 0
    with_specific_ids = 0
    with_action_change = 0
    high_entropy_without_specifics = 0
    for forecast in forecasts:
        dist = forecast.get("failure_mode_distribution") or {}
        if not isinstance(dist, dict) or not dist:
            continue
        entropy = normalized_entropy(dist)
        if entropy is None:
            continue
        entropies.append(entropy)
        try:
            other_mass += float(dist.get("other") or 0.0)
        except (TypeError, ValueError):
            pass
        has_specifics = bool(forecast.get("specific_failure_mode_ids"))
        has_action_change = bool(forecast.get("action_change_recommendation"))
        with_specific_ids += int(has_specifics)
        with_action_change += int(has_action_change)
        if entropy >= 0.9:
            high_entropy += 1
            if not (has_specifics or has_action_change):
                high_entropy_without_specifics += 1
    return {
        "forecasts_with_failure_distribution": len(entropies),
        "median_normalized_entropy": median(entropies),
        "mean_normalized_entropy": mean(entropies),
        "high_entropy_failure_distributions": high_entropy,
        "high_entropy_fraction": (
            None if not entropies else round(high_entropy / len(entropies), 4)
        ),
        "high_entropy_without_specific_ids_or_action_change": high_entropy_without_specifics,
        "forecasts_with_specific_failure_mode_ids": with_specific_ids,
        "forecasts_with_action_change_recommendation": with_action_change,
        "total_other_failure_mode_mass": round(other_mass, 4),
    }


def calibration_debt_block(
    contracts: dict[str, dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    scored_contracts = {str(row.get("contract_id")) for row in rows}
    resolved_contracts = set(outcomes)
    unscored = sorted(resolved_contracts - scored_contracts)
    unresolved = sorted(set(contracts) - resolved_contracts)
    return {
        "resolved_contracts": len(resolved_contracts),
        "scored_contracts": len(scored_contracts),
        "resolved_unscored_contracts": len(unscored),
        "resolved_unscored_contract_samples": unscored[:20],
        "unresolved_contracts": len(unresolved),
        "unresolved_contract_samples": unresolved[:20],
    }


def prediction_ledger_coverage_block(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    resolved = [
        row for row in rows
        if row.get("resolved_at")
        or row.get("actual_outcome")
        or row.get("resolution")
    ]
    brier_like = [
        row for row in rows
        if row.get("brier") is not None
        or row.get("brier_realized") is not None
        or "Brier" in str(row.get("calibration_delta_odds") or row.get("calibration_delta") or "")
    ]
    tier_counts = Counter(str(row.get("tier") or "untagged") for row in rows)
    return {
        "path": rel(path),
        "rows": len(rows),
        "resolved_rows": len(resolved),
        "brier_like_scored_rows": len(brier_like),
        "tier_counts": dict(sorted(tier_counts.items())),
        "coverage_note": (
            "PATTERN-012 rows are useful lightweight prediction evidence, "
            "but their scored coverage must be reported separately from GP-230."
        ),
    }


def transport_health_block(
    root: Path,
    channel_dir: Path,
    outcomes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    inbox = channel_dir / "inbox"
    claims = channel_dir / "claims"
    responses = channel_dir / "responses"
    messages: list[dict[str, Any]] = []
    for path in sorted(inbox.glob("*.json")) if inbox.exists() else []:
        payload = read_json(path, {})
        if isinstance(payload, dict):
            item = dict(payload)
            item["_path"] = rel(path)
            messages.append(item)
    claim_ids = {path.stem for path in claims.glob("*.json")} if claims.exists() else set()
    response_ids = {path.stem for path in responses.glob("*.json")} if responses.exists() else set()
    status_counts = Counter(str(message.get("status") or "missing") for message in messages)
    obligation_counts = Counter(str(message.get("obligation_state") or "missing") for message in messages)
    open_messages = [
        message for message in messages
        if message.get("status") != "closed"
        and message.get("obligation_state") not in {"fulfilled", "refused", "expired"}
    ]
    claimed_without_response = [
        message for message in messages
        if str(message.get("message_id")) in claim_ids
        and str(message.get("message_id")) not in response_ids
    ]
    resolved_before_consumed = []
    for message in open_messages:
        metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        contract_id = str(metadata.get("contract_id") or "")
        if contract_id and contract_id in outcomes:
            resolved_before_consumed.append({
                "message_id": message.get("message_id"),
                "contract_id": contract_id,
                "path": message.get("_path"),
            })
    aggregate_missing_after_fulfilled = []
    for message in messages:
        metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        contract_id = str(metadata.get("contract_id") or "")
        if (
            contract_id
            and message.get("obligation_state") == "fulfilled"
            and not (root / "aggregates" / f"{contract_id}.json").exists()
        ):
            aggregate_missing_after_fulfilled.append({
                "message_id": message.get("message_id"),
                "contract_id": contract_id,
                "path": message.get("_path"),
            })
    return {
        "channel_dir": rel(channel_dir),
        "inbox_messages": len(messages),
        "claim_files": len(claim_ids),
        "response_files": len(response_ids),
        "status_counts": dict(sorted(status_counts.items())),
        "obligation_state_counts": dict(sorted(obligation_counts.items())),
        "open_messages": len(open_messages),
        "claimed_without_response": len(claimed_without_response),
        "claimed_without_response_samples": [
            {"message_id": message.get("message_id"), "path": message.get("_path")}
            for message in claimed_without_response[:20]
        ],
        "open_messages_for_resolved_contracts": len(resolved_before_consumed),
        "open_messages_for_resolved_contract_samples": resolved_before_consumed[:20],
        "fulfilled_messages_missing_aggregate": len(aggregate_missing_after_fulfilled),
        "fulfilled_messages_missing_aggregate_samples": aggregate_missing_after_fulfilled[:20],
        "architecture_note": (
            "This is the pub/sub transport health surface. RD pre-tick should "
            "consume aggregate/status artifacts, not raw channel chatter."
        ),
    }


def risk_and_failure_block(forecasts: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    mode_mass = Counter()
    top_mode_hits = 0
    structured_top_hits = 0
    structured_specific_hits = 0
    structured_realized_mass: list[float] = []
    structured_scoreable = 0
    scoreable = 0
    for forecast in forecasts:
        dist = forecast.get("failure_mode_distribution") or {}
        if isinstance(dist, dict):
            for mode, p in dist.items():
                try:
                    mode_mass[str(mode)] += float(p)
                except (TypeError, ValueError):
                    pass
        cid = forecast.get("contract_id")
        outcome = outcomes.get(str(cid)) if cid else None
        if not outcome:
            continue
        realized = {str(item) for item in outcome.get("realized_failure_mode_ids") or []}
        if realized and dist:
            structured_scoreable += 1
            top_structured = max(dist.items(), key=lambda kv: float(kv[1]))[0]
            if str(top_structured) in realized:
                structured_top_hits += 1
            mass = sum(float(p) for mode, p in dist.items() if str(mode) in realized)
            structured_realized_mass.append(mass)
            specific = {str(item) for item in forecast.get("specific_failure_mode_ids") or []}
            if specific & realized:
                structured_specific_hits += 1
        error_type = str(outcome.get("error_type") or "").lower()
        note = str(outcome.get("resolution_note") or "").lower()
        if dist:
            scoreable += 1
            top = max(dist.items(), key=lambda kv: float(kv[1]))[0]
            if str(top).lower() in error_type or str(top).lower() in note:
                top_mode_hits += 1
    return {
        "forecast_failure_mode_mass_top15": mode_mass.most_common(15),
        "failure_mode_top1_text_hit_rate": (
            None if scoreable == 0 else round(top_mode_hits / scoreable, 4)
        ),
        "failure_mode_scoreable_forecasts": scoreable,
        "structured_realized_failure_mode_scoreable_forecasts": structured_scoreable,
        "structured_failure_mode_top1_hit_rate": (
            None if structured_scoreable == 0 else round(structured_top_hits / structured_scoreable, 4)
        ),
        "structured_specific_failure_mode_hit_rate": (
            None if structured_scoreable == 0 else round(structured_specific_hits / structured_scoreable, 4)
        ),
        "structured_mean_realized_failure_mode_mass": mean(structured_realized_mass),
    }


def decision_use_block(path: Path, contracts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = read_jsonl(path)
    stage_counts = Counter(str(row.get("decision_stage") or "unknown") for row in rows)
    used_for_counts = Counter(str(row.get("used_for") or "unknown") for row in rows)
    by_contract = Counter(str(row.get("contract_id") or "") for row in rows if row.get("contract_id"))
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
    missing_contract_rows = [
        row for row in rows
        if row.get("contract_id") and str(row.get("contract_id")) not in contracts
    ]
    adopted_modes = 0
    missing_aggregate = 0
    for row in rows:
        modes = row.get("failure_modes_adopted")
        if isinstance(modes, list) and modes:
            adopted_modes += 1
        if row.get("aggregate_present") is False:
            missing_aggregate += 1
    return {
        "path": rel(path),
        "exists": path.exists(),
        "rows": len(rows),
        "unique_contracts": len(by_contract),
        "stage_counts": dict(sorted(stage_counts.items())),
        "used_for_counts": dict(sorted(used_for_counts.items())),
        "decision_changed_or_rerouted_rows": len(changed),
        "rows_with_failure_modes_adopted": adopted_modes,
        "rows_with_missing_aggregate": missing_aggregate,
        "ignored_or_overridden_without_reason": len(ignored_without_reason),
        "missing_contract_reference_rows": len(missing_contract_rows),
        "recent_rows": rows[-10:],
    }


def externality_block(
    root: Path,
    contracts: dict[str, dict[str, Any]],
    forecasts: list[dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
    gp233_path: Path,
) -> dict[str, Any]:
    notes = [str(outcome.get("resolution_note") or "") for outcome in outcomes.values()]
    gp233 = gp233_path.read_text() if gp233_path.exists() else ""
    terms = [
        "preconditioner",
        "externality",
        "underpriced",
        "overestimated",
        "routing",
        "changed",
        "warning",
        "trap",
        "calibration",
        "effort",
        "forecast pool",
        "forecast-pool",
    ]
    positive_rows = [
        line for line in gp233.splitlines()
        if "forecast" in line.lower() or "gp-230" in line.lower() or "prediction" in line.lower()
    ]
    contracts_with_counterfactual = [
        cid for cid, contract in contracts.items()
        if contract.get("baseline_action") or contract.get("counterfactual_action")
    ]
    forecasts_with_specific_modes = [
        forecast for forecast in forecasts if forecast.get("specific_failure_mode_ids")
    ]
    forecasts_with_action_change = [
        forecast for forecast in forecasts if forecast.get("action_change_recommendation")
    ]
    outcomes_with_realized_modes = [
        cid for cid, outcome in outcomes.items() if outcome.get("realized_failure_mode_ids")
    ]
    outcomes_with_decision_change = [
        cid for cid, outcome in outcomes.items() if outcome.get("decision_changed_bool") is not None
    ]
    outcomes_with_changed_by_forecast = [
        cid for cid, outcome in outcomes.items() if outcome.get("changed_by_forecast_ids")
    ]
    outcomes_with_counterfactual_value = [
        cid for cid, outcome in outcomes.items() if outcome.get("counterfactual_value_bucket")
    ]
    outcomes_with_old_new_action = [
        cid for cid, outcome in outcomes.items()
        if outcome.get("old_next_action") or outcome.get("new_next_action")
    ]
    preconditioner_outcomes = [
        cid for cid, outcome in outcomes.items()
        if outcome.get("failure_mode_preconditioner_used") is True
    ]
    return {
        "outcome_resolution_note_term_counts": term_counts(notes, terms),
        "gp233_forecast_related_rows": len(positive_rows),
        "gp233_forecast_related_sample": positive_rows[-8:],
        "calibration_summary_exists": (root / "calibration_summary.json").exists(),
        "calibration_weights_exists": (root / "calibration_weights.json").exists(),
        "structured_coverage": {
            "contracts_with_counterfactual_fields": len(contracts_with_counterfactual),
            "forecasts_with_specific_failure_mode_ids": len(forecasts_with_specific_modes),
            "forecasts_with_action_change_recommendation": len(forecasts_with_action_change),
            "outcomes_with_realized_failure_mode_ids": len(outcomes_with_realized_modes),
            "outcomes_with_decision_changed_bool": len(outcomes_with_decision_change),
            "outcomes_with_failure_mode_preconditioner_used": len(preconditioner_outcomes),
            "outcomes_with_changed_by_forecast_ids": len(outcomes_with_changed_by_forecast),
            "outcomes_with_counterfactual_value_bucket": len(outcomes_with_counterfactual_value),
            "outcomes_with_old_or_new_next_action": len(outcomes_with_old_new_action),
        },
        "structured_samples": {
            "contracts_with_counterfactual_fields": contracts_with_counterfactual[-8:],
            "outcomes_with_decision_changed_bool": outcomes_with_decision_change[-8:],
            "outcomes_with_failure_mode_preconditioner_used": preconditioner_outcomes[-8:],
            "outcomes_with_changed_by_forecast_ids": outcomes_with_changed_by_forecast[-8:],
            "outcomes_with_counterfactual_value_bucket": outcomes_with_counterfactual_value[-8:],
        },
    }


def negative_externality_block(
    root: Path,
    contracts: dict[str, dict[str, Any]],
    forecasts: list[dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_contract: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for forecast in forecasts:
        by_contract[str(forecast.get("contract_id"))].append(forecast)
    hedge_rows = [
        forecast for forecast in forecasts
        if 0.45 <= float(forecast.get("p_success", 0.0)) <= 0.55
    ]
    high_entropy_modes = 0
    for forecast in forecasts:
        dist = forecast.get("failure_mode_distribution") or {}
        if not isinstance(dist, dict) or len(dist) < 3:
            continue
        entropy = -sum(float(p) * math.log(max(float(p), 1e-9)) for p in dist.values())
        if entropy >= math.log(len(dist)) * 0.9:
            high_entropy_modes += 1
    drag_flags = []
    for cid, items in by_contract.items():
        outcome = outcomes.get(cid)
        if not outcome:
            continue
        created = parse_iso((contracts.get(cid) or {}).get("created_at"))
        resolved = parse_iso(outcome.get("resolved_at"))
        if not created or not resolved:
            continue
        forecast_span = (resolved - created).total_seconds() / 60.0
        actual = outcome.get("actual_cost_agent_minutes")
        if actual is not None and forecast_span > max(15.0, float(actual) * 2.0):
            drag_flags.append({
                "contract_id": cid,
                "forecast_to_resolution_minutes": round(forecast_span, 2),
                "actual_cost_agent_minutes": float(actual),
            })
    unresolved = len(contracts) - len(outcomes)
    negative_tag_counts = Counter()
    for outcome in outcomes.values():
        for tag in outcome.get("negative_externality_tags") or []:
            negative_tag_counts[str(tag)] += 1
    return {
        "p_success_hedge_band_rows": len(hedge_rows),
        "p_success_hedge_band_fraction": round(len(hedge_rows) / len(forecasts), 4) if forecasts else None,
        "high_entropy_failure_mode_forecasts": high_entropy_modes,
        "unresolved_contracts": unresolved,
        "resolved_selection_rate": round(len(outcomes) / len(contracts), 4) if contracts else None,
        "forecast_drag_flags_top20": drag_flags[:20],
        "negative_externality_tag_counts": negative_tag_counts.most_common(20),
    }


def build_report(
    root: Path,
    gp233_path: Path,
    prediction_ledger_path: Path,
    decision_use_ledger_path: Path,
) -> dict[str, Any]:
    contracts = load_contracts(root)
    forecasts = load_forecasts(root)
    outcomes = load_outcomes(root)
    aggregates = load_aggregates(root)
    rows = load_score_rows(root)
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "root": rel(root),
        "coverage": {
            "contracts": len(contracts),
            "forecasts": len(forecasts),
            "outcomes": len(outcomes),
            "aggregates": len(aggregates),
            "score_files": len(list((root / "scores").glob("*.json"))),
            "score_rows": len(rows),
        },
        "calibration": calibration_block(rows),
        "effort": effort_block(rows),
        "routing": routing_block(aggregates, outcomes),
        "market_depth": market_depth_block(root, contracts, forecasts),
        "identity_hygiene": identity_hygiene_block(forecasts),
        "domain_hygiene": domain_hygiene_block(forecasts, rows),
        "risk_and_failure_modes": risk_and_failure_block(forecasts, outcomes),
        "failure_mode_quality": failure_mode_quality_block(forecasts),
        "positive_externalities": externality_block(root, contracts, forecasts, outcomes, gp233_path),
        "negative_externalities": negative_externality_block(root, contracts, forecasts, outcomes),
        "calibration_debt": calibration_debt_block(contracts, outcomes, rows),
        "prediction_ledger_coverage": prediction_ledger_coverage_block(prediction_ledger_path),
        "decision_use_ledger": decision_use_block(decision_use_ledger_path, contracts),
        "transport_health": transport_health_block(root, DEFAULT_FORECASTING_CHANNEL, outcomes),
        "schema_gaps": [
            "legacy outcomes lack structured decision_changed_bool / old_next_action / new_next_action",
            "legacy failure_mode_distribution rows are not scored against realized_failure_mode_ids",
            "positive externalities historically mostly live in GP-233 prose and resolution notes",
            "forecaster correlation/effective-n is not computed",
            "forecast drag and overuse are not part of routing weights",
            "legacy rows usually lack counterfactual_value_bucket",
            "live price movement is not visible when forecast_updates is empty",
            "post-binding noncanonical agent_id rows fragment calibration weights",
            "domain aliases fragment domain-specific calibration and effort priors",
            "resolved-but-unscored contracts are calibration debt",
            "raw prediction-ledger rows have different scoring coverage than GP-230 rows",
            "VPS forecaster transport needs explicit channel health before RD pre-tick treats it as reliable",
            "decision-use ledger rows must become routine for RD/membrane forecast consumption",
        ],
        "recommended_fields": {
            "contract": ["baseline_action", "counterfactual_action", "externality_hypotheses"],
            "forecast": [
                "specific_failure_mode_ids",
                "action_change_recommendation",
                "forecast_externality_tags",
            ],
            "outcome": [
                "realized_failure_mode_ids",
                "failure_mode_preconditioner_used",
                "decision_changed_bool",
                "old_next_action",
                "new_next_action",
                "externality_tags",
                "negative_externality_tags",
                "counterfactual_value_bucket",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--gp233", type=Path, default=DEFAULT_GP233)
    parser.add_argument("--prediction-ledger", type=Path, default=DEFAULT_PREDICTION_LEDGER)
    parser.add_argument("--decision-use-ledger", type=Path, default=DEFAULT_DECISION_USE_LEDGER)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report(
        args.root,
        args.gp233,
        args.prediction_ledger,
        args.decision_use_ledger,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(json.dumps({"output": rel(args.output), "coverage": report["coverage"]}, indent=2))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
