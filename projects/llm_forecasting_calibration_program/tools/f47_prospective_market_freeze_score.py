#!/usr/bin/env python3
"""Resolve and score the prospective F47 market-freeze packet.

This is the companion to ``f47_prospective_market_freeze_packet.py``. It is
safe to run before markets resolve: in that case it updates resolution status
where possible and emits an evidence-gap-capped ``not_ready`` verdict instead
of fabricating Brier evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ztare.experiment_stats import paired_permutation_test  # noqa: E402

from f47_cross_packet_transfer_audit import (  # noqa: E402
    DEFAULT_SOURCE_CALLS,
    DEFAULT_SOURCE_KEY,
    brier,
    confident_no,
    contract_rows as historical_contract_rows,
    load_edges as load_historical_edges,
)
from f47_translation_tournament_score import fit_logistic, sigmoid  # noqa: E402

WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_PACKET_DIR = WORKSPACE / "f47_prospective_market_freeze_packet_2026_06_04"
DEFAULT_KEY = DEFAULT_PACKET_DIR / "f47_prospective_market_freeze_answer_key.json"
DEFAULT_CALLS = DEFAULT_PACKET_DIR / "f47_prospective_market_freeze_calls.jsonl"
DEFAULT_RESOLVED_KEY = DEFAULT_PACKET_DIR / "f47_prospective_market_freeze_resolved_answer_key.json"
DEFAULT_OUT_JSON = DEFAULT_PACKET_DIR / "f47_prospective_market_freeze_score.json"
DEFAULT_OUT_MD = DEFAULT_PACKET_DIR / "f47_prospective_market_freeze_score.md"
GAMMA_BASE = "https://gamma-api.polymarket.com"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def as_probability(value: Any) -> float | None:
    out = as_float(value)
    if out is None or out < 0 or out > 1:
        return None
    return out


def parse_json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        obj = json.loads(value)
    except Exception:
        return []
    return obj if isinstance(obj, list) else []


def yes_index(outcomes: list[Any]) -> int | None:
    for i, outcome in enumerate(outcomes):
        if str(outcome).strip().lower() == "yes":
            return i
    return None


def read_json_url(url: str, *, timeout: float) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "ztare-f47-prospective-score/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def gamma_market_by_slug(slug: str, *, timeout: float) -> tuple[dict[str, Any] | None, str]:
    direct = f"{GAMMA_BASE}/markets/slug/{urllib.parse.quote(slug)}"
    try:
        obj = read_json_url(direct, timeout=timeout)
        if isinstance(obj, dict) and obj.get("id"):
            return obj, "gamma_slug_direct"
    except Exception as exc:
        direct_error = f"{type(exc).__name__}:{str(exc)[:120]}"
    params = urllib.parse.urlencode({"slug": slug, "limit": "1"})
    try:
        obj = read_json_url(f"{GAMMA_BASE}/markets?{params}", timeout=timeout)
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return obj[0], "gamma_slug_list"
    except Exception as exc:
        return None, f"gamma_fetch_failed:{direct_error};{type(exc).__name__}:{str(exc)[:120]}"
    return None, "gamma_market_not_found"


def outcome_from_market(market: dict[str, Any]) -> tuple[int | None, str]:
    if not bool(market.get("closed")) and not bool(market.get("archived")):
        return None, "open"
    outcomes = parse_json_array(market.get("outcomes"))
    idx = yes_index(outcomes)
    prices = parse_json_array(market.get("outcomePrices"))
    if idx is None or idx >= len(prices):
        return None, "closed_missing_yes_price"
    p_yes = as_probability(prices[idx])
    if p_yes is None:
        return None, "closed_invalid_yes_price"
    if p_yes >= 0.95:
        return 1, "resolved_yes_by_final_price"
    if p_yes <= 0.05:
        return 0, "resolved_no_by_final_price"
    return None, "closed_ambiguous_final_price"


def load_key(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("answer_key") or []), dict(data.get("report") or {})


def resolve_key_rows(
    rows: list[dict[str, Any]],
    *,
    live: bool,
    timeout: float,
    sleep_ms: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    market_cache: dict[str, dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    fetch_counts: Counter[str] = Counter()
    resolved_rows: list[dict[str, Any]] = []
    checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for row in rows:
        out = dict(row)
        for side in ("a", "b"):
            slug = str(row.get(f"slug_{side}") or "")
            y_key = f"y_{side}"
            status_key = f"resolution_status_{side}"
            source_key = f"resolution_source_{side}"
            if row.get(y_key) in (0, 1):
                out[status_key] = "already_resolved_in_key"
                out[source_key] = "answer_key"
                status_counts["already_resolved_in_key"] += 1
                continue
            if not live:
                out[status_key] = "not_checked_live"
                out[source_key] = "none"
                status_counts["not_checked_live"] += 1
                continue
            if slug not in market_cache:
                market, fetch_status = gamma_market_by_slug(slug, timeout=timeout)
                fetch_counts[fetch_status] += 1
                market_cache[slug] = market or {"_fetch_status": fetch_status}
                if sleep_ms:
                    time.sleep(sleep_ms / 1000)
            market = market_cache[slug]
            if "_fetch_status" in market:
                out[status_key] = str(market["_fetch_status"])
                out[source_key] = "gamma"
                status_counts[out[status_key]] += 1
                continue
            y, status = outcome_from_market(market)
            out[y_key] = y
            out[status_key] = status
            out[source_key] = "gamma"
            status_counts[status] += 1
        out["resolution_checked_at"] = checked_at
        out["resolution_status"] = (
            "resolved_pair" if out.get("y_a") in (0, 1) and out.get("y_b") in (0, 1) else "unresolved_or_partial_pair"
        )
        resolved_rows.append(out)
    return resolved_rows, {
        "live_resolution_checked": live,
        "resolution_checked_at": checked_at,
        "side_status_counts": dict(sorted(status_counts.items())),
        "fetch_counts": dict(sorted(fetch_counts.items())),
        "resolved_pairs": sum(1 for row in resolved_rows if row["resolution_status"] == "resolved_pair"),
        "total_pairs": len(resolved_rows),
    }


def family_for(row: dict[str, Any]) -> str:
    runtime = str(row.get("runtime") or "")
    model = str(row.get("model") or "")
    if runtime == "codex" and model == "gpt-5.5":
        return "codex_55"
    if runtime == "codex" and model == "gpt-5.4-mini":
        return "codex_mini"
    return runtime or str(row.get("agent_id") or "unknown")


def load_calls(calls_path: Path, key_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = {str(row["pair_id"]): row for row in key_rows}
    observations: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for line_no, row in enumerate(read_jsonl(calls_path), start=1):
        pair_id = str(row.get("pair_id") or "")
        parsed = row.get("parsed") or {}
        audit = row.get("schema_audit") or {}
        p_a = as_probability(parsed.get("p_success_a"))
        p_b = as_probability(parsed.get("p_success_b"))
        delta = as_float(parsed.get("predicted_delta"))
        if delta is None and p_a is not None and p_b is not None:
            delta = p_a - p_b
        reason = None
        if pair_id not in key:
            reason = "missing_answer_key"
        elif not audit.get("schema_ok"):
            reason = "schema_not_ok"
        elif p_a is None or p_b is None or delta is None:
            reason = "missing_probabilities"
        elif key[pair_id].get("y_a") not in (0, 1) or key[pair_id].get("y_b") not in (0, 1):
            reason = "unresolved_pair"
        if reason:
            exclusions.append({"line": line_no, "pair_id": pair_id, "agent_id": row.get("agent_id"), "reason": reason})
            continue
        answer = key[pair_id]
        observations.append(
            {
                "pair_id": pair_id,
                "source": str(answer["source"]),
                "family": family_for(row),
                "agent_id": row.get("agent_id"),
                "contract_id_a": str(answer["market_id_a"]),
                "contract_id_b": str(answer["market_id_b"]),
                "p_a": float(p_a),
                "p_b": float(p_b),
                "predicted_delta": float(delta),
                "y_a": int(answer["y_a"]),
                "y_b": int(answer["y_b"]),
                "market_p_a": float(answer["frozen_market_p_a"]),
                "market_p_b": float(answer["frozen_market_p_b"]),
                "event_family_a": answer.get("event_family_a"),
                "event_family_b": answer.get("event_family_b"),
            }
        )
    return observations, exclusions


def prospective_contract_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in edges:
        for side in ("a", "b"):
            cid = str(row[f"contract_id_{side}"])
            y = int(row[f"y_{side}"])
            emitted_p = float(row[f"p_{side}"])
            relative_score = float(row["predicted_delta"]) if side == "a" else -float(row["predicted_delta"])
            key = (str(row["family"]), cid)
            slot = grouped.setdefault(
                key,
                {
                    "family": row["family"],
                    "source": row["source"],
                    "contract_id": cid,
                    "y": y,
                    "market_ps": [],
                    "emitted_ps": [],
                    "relative_scores": [],
                    "event_families": [],
                    "degree": 0,
                },
            )
            if int(slot["y"]) != y:
                raise SystemExit(f"inconsistent y for {cid}")
            slot["market_ps"].append(float(row[f"market_p_{side}"]))
            slot["emitted_ps"].append(emitted_p)
            slot["relative_scores"].append(relative_score)
            slot["event_families"].append(row.get(f"event_family_{side}"))
            slot["degree"] += 1
    out: list[dict[str, Any]] = []
    for slot in grouped.values():
        raw = statistics.mean(slot["emitted_ps"])
        out.append(
            {
                "family": slot["family"],
                "source": slot["source"],
                "contract_id": slot["contract_id"],
                "y": int(slot["y"]),
                "degree": int(slot["degree"]),
                "raw_context_p": raw,
                "f100_family_p": confident_no(raw),
                "market_p": statistics.mean(slot["market_ps"]),
                "pairwise_score": statistics.mean(slot["relative_scores"]),
                "event_family": sorted({str(x) for x in slot["event_families"] if x})[0],
            }
        )
    return sorted(out, key=lambda row: (row["family"], row["contract_id"]))


def historical_translation_fit(source_calls: Path, source_key: Path) -> tuple[float, float, dict[str, Any]]:
    edges, exclusions = load_historical_edges("source_balanced", source_calls, source_key)
    rows = historical_contract_rows(edges)
    intercept, slope = fit_logistic([float(row["pairwise_score"]) for row in rows], [int(row["y"]) for row in rows])
    return intercept, slope, {
        "train_packet": "source_balanced",
        "train_family_rows": len(rows),
        "train_excluded_rows": len(exclusions),
        "intercept": intercept,
        "slope": slope,
    }


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else float("nan")


def compare(rows: list[dict[str, Any]], candidate: str, baseline: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    candidate_losses = [brier(float(row[candidate]), int(row["y"])) for row in rows]
    baseline_losses = [brier(float(row[baseline]), int(row["y"])) for row in rows]
    return {
        "n": len(rows),
        "candidate": candidate,
        "baseline": baseline,
        "candidate_brier": round(mean(candidate_losses), 6),
        "baseline_brier": round(mean(baseline_losses), 6),
        "delta_candidate_minus_baseline": round(mean([c - b for c, b in zip(candidate_losses, baseline_losses)]), 6),
        "paired_permutation": paired_permutation_test(candidate_losses, baseline_losses, seed=47),
    }


def summarize(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    return {
        "n": len(rows),
        "brier": round(mean([brier(float(row[policy]), int(row["y"])) for row in rows]), 6),
        "mean_p": round(mean([float(row[policy]) for row in rows]), 6),
        "yes_rate": round(mean([float(row["y"]) for row in rows]), 6),
    }


def panel_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["contract_id"])].append(row)
    out: list[dict[str, Any]] = []
    for cid, group in sorted(grouped.items()):
        ys = {int(row["y"]) for row in group}
        if len(ys) != 1:
            continue
        raw_panel = mean([float(row["raw_context_p"]) for row in group])
        market_p = mean([float(row["market_p"]) for row in group])
        translated = mean([float(row["translated_p"]) for row in group])
        out.append(
            {
                "contract_id": cid,
                "source": "polymarket",
                "event_family": sorted({str(row["event_family"]) for row in group})[0],
                "y": next(iter(ys)),
                "family_count": len({str(row["family"]) for row in group}),
                "raw_panel_p": raw_panel,
                "f100_mean_family_p": mean([float(row["f100_family_p"]) for row in group]),
                "translated_panel_p": translated,
                "market_p": market_p,
                "half_market_half_translated_p": 0.5 * market_p + 0.5 * translated,
            }
        )
    return out


def score_observations(
    observations: list[dict[str, Any]],
    *,
    source_calls: Path,
    source_key: Path,
) -> dict[str, Any]:
    intercept, slope, fit_meta = historical_translation_fit(source_calls, source_key)
    family_rows = prospective_contract_rows(observations)
    for row in family_rows:
        row["translated_p"] = sigmoid(intercept + slope * float(row["pairwise_score"]))
    panel = panel_rows(family_rows)
    comparisons = {
        "translated_vs_market": compare(panel, "translated_panel_p", "market_p"),
        "translated_vs_f100": compare(panel, "translated_panel_p", "f100_mean_family_p"),
        "translated_vs_raw": compare(panel, "translated_panel_p", "raw_panel_p"),
        "half_blend_vs_market": compare(panel, "half_market_half_translated_p", "market_p"),
    }
    market_delta = comparisons["translated_vs_market"].get("delta_candidate_minus_baseline")
    market_p_value = (comparisons["translated_vs_market"].get("paired_permutation") or {}).get("p_value")
    verdict = "f47_prospective_scored_not_promoted"
    if (
        len(panel) >= 20
        and market_delta is not None
        and market_delta <= -0.01
        and market_p_value is not None
        and market_p_value <= 0.05
    ):
        verdict = "f47_prospective_candidate_positive"
    return {
        "translation_fit": fit_meta,
        "family_rows": len(family_rows),
        "panel_rows": len(panel),
        "policy_summary": {
            key: summarize(panel, key)
            for key in ("market_p", "raw_panel_p", "f100_mean_family_p", "translated_panel_p", "half_market_half_translated_p")
        },
        "comparisons": comparisons,
        "scored_rows": panel,
        "score_verdict": verdict,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    key_rows, packet_report = load_key(args.answer_key)
    resolved_rows, resolution = resolve_key_rows(
        key_rows,
        live=not args.no_live_resolution,
        timeout=args.timeout,
        sleep_ms=args.sleep_ms,
    )
    args.resolved_key.write_text(
        json.dumps({"answer_key": resolved_rows, "packet_report": packet_report, "resolution": resolution}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    calls_exist = args.calls.exists()
    observations, exclusions = load_calls(args.calls, resolved_rows) if calls_exist else ([], [])
    unresolved_pairs = resolution["total_pairs"] - resolution["resolved_pairs"]
    report: dict[str, Any] = {
        "schema": "f47-prospective-market-freeze-score-v1",
        "date": "2026-06-04",
        "packet": "f47_prospective_market_freeze_packet",
        "answer_key": str(args.answer_key.relative_to(REPO) if args.answer_key.is_relative_to(REPO) else args.answer_key),
        "calls": str(args.calls.relative_to(REPO) if args.calls.is_relative_to(REPO) else args.calls),
        "resolved_key": str(args.resolved_key.relative_to(REPO) if args.resolved_key.is_relative_to(REPO) else args.resolved_key),
        "resolution": resolution,
        "calls_file_exists": calls_exist,
        "valid_call_observations": len(observations),
        "excluded_call_rows": len(exclusions),
        "exclusion_reasons": dict(sorted(Counter(row["reason"] for row in exclusions).items())),
        "evidence_gap_cap": None,
    }
    if unresolved_pairs:
        report["verdict"] = "not_ready_unresolved_markets"
        report["evidence_gap_cap"] = (
            "Outcomes are unresolved or partially resolved; Brier/policy claims are capped at no-evidence."
        )
        return report
    if not calls_exist:
        report["verdict"] = "not_ready_no_calls"
        report["evidence_gap_cap"] = "No model-call file exists for this frozen packet."
        return report
    if not observations:
        report["verdict"] = "not_ready_no_valid_resolved_calls"
        report["evidence_gap_cap"] = "Calls exist, but none are both schema-valid and resolved."
        return report
    report.update(score_observations(observations, source_calls=args.source_calls, source_key=args.source_key))
    report["verdict"] = report["score_verdict"]
    return report


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# F47 Prospective Market-Freeze Score",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Resolved pairs: `{report['resolution']['resolved_pairs']}` / `{report['resolution']['total_pairs']}`",
        f"- Calls file exists: `{report['calls_file_exists']}`",
        f"- Valid call observations: `{report['valid_call_observations']}`",
        f"- Excluded call rows: `{report['excluded_call_rows']}`",
        f"- Side status counts: `{report['resolution']['side_status_counts']}`",
        f"- Evidence gap cap: `{report.get('evidence_gap_cap')}`",
        "",
    ]
    if "policy_summary" in report:
        lines.extend(["## Policy Brier", "", "| policy | n | Brier | mean p | yes rate |", "|---|---:|---:|---:|---:|"])
        for key, row in report["policy_summary"].items():
            lines.append(f"| `{key}` | {row.get('n')} | {row.get('brier')} | {row.get('mean_p')} | {row.get('yes_rate')} |")
        lines.extend(["", "## Comparisons", "", "| comparison | delta candidate-minus-baseline | p |", "|---|---:|---:|"])
        for key, row in report["comparisons"].items():
            p_value = (row.get("paired_permutation") or {}).get("p_value") if isinstance(row.get("paired_permutation"), dict) else None
            lines.append(f"| `{key}` | {row.get('delta_candidate_minus_baseline')} | {p_value} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--resolved-key", type=Path, default=DEFAULT_RESOLVED_KEY)
    parser.add_argument("--source-calls", type=Path, default=DEFAULT_SOURCE_CALLS)
    parser.add_argument("--source-key", type=Path, default=DEFAULT_SOURCE_KEY)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--no-live-resolution", action="store_true")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--sleep-ms", type=int, default=50)
    args = parser.parse_args()
    report = build_report(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "resolved_pairs": report["resolution"]["resolved_pairs"],
                "total_pairs": report["resolution"]["total_pairs"],
                "calls_file_exists": report["calls_file_exists"],
                "valid_call_observations": report["valid_call_observations"],
                "evidence_gap_cap": report.get("evidence_gap_cap"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
