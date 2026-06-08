#!/usr/bin/env python3
"""Cross-packet transfer audit for F47 pairwise-to-probability translation.

No model calls. No DB mutation.

The same-packet F47 translation result is promising but could be packet-local
calibration. This audit trains the logistic map from pairwise relative score to
binary outcome on one frozen F47 packet and evaluates it on the other packet.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test

from f47_translation_tournament_score import (
    brier,
    family_for,
    fit_logistic,
    sigmoid,
)


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_SOURCE_CALLS = WORKSPACE / "pilot_f47_source_balanced_consumer_calls_smoke_2026_06_03.jsonl"
DEFAULT_SOURCE_KEY = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_answer_key.json"
DEFAULT_TOURNAMENT_CALLS = WORKSPACE / "pilot_f47_translation_tournament_calls_2026_06_03.jsonl"
DEFAULT_TOURNAMENT_KEY = WORKSPACE / "f47_translation_tournament_packet_2026_06_03_answer_key.json"
DEFAULT_OUT_JSON = WORKSPACE / "f47_cross_packet_transfer_audit_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f47_cross_packet_transfer_audit_2026_06_03.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_key(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("answer_key") or []
    return {str(row["pair_id"]): row for row in rows if isinstance(row, dict)}


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out


def confident_no(p: float) -> float:
    if p < 0.10:
        return p + (0.65 - p) * 0.5
    return p


def load_edges(packet: str, calls_path: Path, key_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = load_key(key_path)
    rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for line_no, row in enumerate(read_jsonl(calls_path), start=1):
        pair_id = str(row.get("pair_id") or "")
        parsed = row.get("parsed") or {}
        audit = row.get("schema_audit") or {}
        p_a = as_float(parsed.get("p_success_a"))
        p_b = as_float(parsed.get("p_success_b"))
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
        if reason:
            exclusions.append(
                {
                    "packet": packet,
                    "line": line_no,
                    "pair_id": pair_id,
                    "agent_id": row.get("agent_id"),
                    "reason": reason,
                }
            )
            continue
        answer = key[pair_id]
        rows.append(
            {
                "packet": packet,
                "pair_id": pair_id,
                "source": str(answer["source"]),
                "family": family_for(row),
                "agent_id": row.get("agent_id"),
                "contract_id_a": str(answer["contract_id_a"]),
                "contract_id_b": str(answer["contract_id_b"]),
                "p_a": float(p_a),
                "p_b": float(p_b),
                "predicted_delta": float(delta),
                "y_a": int(answer["y_a"]),
                "y_b": int(answer["y_b"]),
            }
        )
    return rows, exclusions


def contract_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in edges:
        for side in ("a", "b"):
            cid = str(row[f"contract_id_{side}"])
            y = int(row[f"y_{side}"])
            emitted_p = float(row[f"p_{side}"])
            relative_score = float(row["predicted_delta"]) if side == "a" else -float(row["predicted_delta"])
            key = (str(row["packet"]), str(row["family"]), str(row["source"]), cid)
            slot = grouped.setdefault(
                key,
                {
                    "packet": row["packet"],
                    "family": row["family"],
                    "source": row["source"],
                    "contract_id": cid,
                    "y": y,
                    "emitted_ps": [],
                    "relative_scores": [],
                    "degree": 0,
                },
            )
            if int(slot["y"]) != y:
                raise SystemExit(f"inconsistent y for {cid}")
            slot["emitted_ps"].append(emitted_p)
            slot["relative_scores"].append(relative_score)
            slot["degree"] += 1
    out: list[dict[str, Any]] = []
    for slot in grouped.values():
        out.append(
            {
                "packet": slot["packet"],
                "family": slot["family"],
                "source": slot["source"],
                "contract_id": slot["contract_id"],
                "y": int(slot["y"]),
                "degree": int(slot["degree"]),
                "raw_context_p": statistics.mean(slot["emitted_ps"]),
                "f100_family_p": confident_no(statistics.mean(slot["emitted_ps"])),
                "pairwise_score": statistics.mean(slot["relative_scores"]),
            }
        )
    return sorted(out, key=lambda row: (row["packet"], row["family"], row["source"], row["contract_id"]))


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


def summarize_policy(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    return {
        "n": len(rows),
        "brier": round(mean([brier(float(row[policy]), int(row["y"])) for row in rows]), 6),
        "mean_p": round(mean([float(row[policy]) for row in rows]), 6),
        "yes_rate": round(mean([float(row["y"]) for row in rows]), 6),
    }


def panel_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["packet"]), str(row["contract_id"]))].append(row)
    out: list[dict[str, Any]] = []
    for (packet, contract_id), group in sorted(grouped.items()):
        ys = {int(row["y"]) for row in group}
        sources = {str(row["source"]) for row in group}
        if len(ys) != 1 or len(sources) != 1:
            continue
        out.append(
            {
                "packet": packet,
                "contract_id": contract_id,
                "source": next(iter(sources)),
                "y": next(iter(ys)),
                "family_count": len({str(row["family"]) for row in group}),
                "raw_panel_p": mean([float(row["raw_context_p"]) for row in group]),
                "f100_panel_after_mean_p": confident_no(mean([float(row["raw_context_p"]) for row in group])),
                "f100_mean_family_p": mean([float(row["f100_family_p"]) for row in group]),
                "translated_panel_p": mean([float(row["translated_p"]) for row in group]),
            }
        )
    return out


def apply_transfer(train_rows: list[dict[str, Any]], test_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not train_rows or not test_rows:
        return {"error": "empty train or test rows", "n_family_rows": 0}
    intercept, slope = fit_logistic(
        [float(row["pairwise_score"]) for row in train_rows],
        [int(row["y"]) for row in train_rows],
    )
    predictions: list[dict[str, Any]] = []
    for row in test_rows:
        item = dict(row)
        item["translated_p"] = sigmoid(intercept + slope * float(row["pairwise_score"]))
        predictions.append(item)
    panel = panel_rows(predictions)
    by_source = {}
    for source in sorted({str(row["source"]) for row in predictions}):
        subset = [row for row in predictions if str(row["source"]) == source]
        by_source[source] = {
            "translated_vs_raw": compare(subset, "translated_p", "raw_context_p"),
            "translated_vs_f100": compare(subset, "translated_p", "f100_family_p"),
        }
    panel_by_source = {}
    for source in sorted({str(row["source"]) for row in panel}):
        subset = [row for row in panel if str(row["source"]) == source]
        panel_by_source[source] = {
            "translated_vs_raw": compare(subset, "translated_panel_p", "raw_panel_p"),
            "translated_vs_f100_mean_family": compare(subset, "translated_panel_p", "f100_mean_family_p"),
        }
    family_delta = compare(predictions, "translated_p", "f100_family_p")
    panel_delta = compare(panel, "translated_panel_p", "f100_mean_family_p")
    source_safe = all(
        item["translated_vs_f100"]["delta_candidate_minus_baseline"] <= 0
        for item in by_source.values()
        if item["translated_vs_f100"].get("n", 0)
    )
    panel_source_safe = all(
        item["translated_vs_f100_mean_family"]["delta_candidate_minus_baseline"] <= 0
        for item in panel_by_source.values()
        if item["translated_vs_f100_mean_family"].get("n", 0)
    )
    return {
        "train_packet": train_rows[0]["packet"],
        "test_packet": test_rows[0]["packet"],
        "fit": {"intercept": round(intercept, 6), "slope": round(slope, 6)},
        "n_train_family_rows": len(train_rows),
        "n_test_family_rows": len(predictions),
        "n_test_panel_contracts": len(panel),
        "train_source_counts": dict(Counter(str(row["source"]) for row in train_rows)),
        "test_source_counts": dict(Counter(str(row["source"]) for row in predictions)),
        "family_policy_summary": {
            key: summarize_policy(predictions, key)
            for key in ("raw_context_p", "f100_family_p", "translated_p")
        },
        "panel_policy_summary": {
            key: summarize_policy(panel, key)
            for key in ("raw_panel_p", "f100_panel_after_mean_p", "f100_mean_family_p", "translated_panel_p")
        },
        "family_comparisons": {
            "translated_vs_raw": compare(predictions, "translated_p", "raw_context_p"),
            "translated_vs_f100": family_delta,
            "by_source": by_source,
        },
        "panel_comparisons": {
            "translated_vs_raw": compare(panel, "translated_panel_p", "raw_panel_p"),
            "translated_vs_f100_mean_family": panel_delta,
            "by_source": panel_by_source,
        },
        "promotion_gate": {
            "requires_panel_translated_beats_f100_by_at_least": -0.01,
            "requires_panel_p_at_most": 0.05,
            "requires_no_family_row_source_regression_vs_f100": True,
            "requires_no_panel_source_regression_vs_f100": True,
        },
        "promotable": bool(
            panel_delta.get("delta_candidate_minus_baseline", 1.0) <= -0.01
            and panel_delta.get("paired_permutation", {}).get("p_value", 1.0) <= 0.05
            and source_safe
            and panel_source_safe
        ),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    source_edges, source_exclusions = load_edges("source_balanced", args.source_calls, args.source_key)
    tournament_edges, tournament_exclusions = load_edges("translation_tournament", args.tournament_calls, args.tournament_key)
    source_contracts = contract_rows(source_edges)
    tournament_contracts = contract_rows(tournament_edges)
    source_to_tournament = apply_transfer(source_contracts, tournament_contracts)
    tournament_to_source = apply_transfer(tournament_contracts, source_contracts)
    verdict = "f47_cross_packet_translation_not_promoted"
    if source_to_tournament.get("promotable") and tournament_to_source.get("promotable"):
        verdict = "f47_cross_packet_translation_bidirectional_promoted"
    elif source_to_tournament.get("promotable") or tournament_to_source.get("promotable"):
        verdict = "f47_cross_packet_translation_one_direction_only"
    return {
        "schema": "f47-cross-packet-transfer-audit-v1",
        "date": "2026-06-03",
        "inputs": {
            "source_calls": str(args.source_calls.relative_to(REPO)),
            "source_key": str(args.source_key.relative_to(REPO)),
            "tournament_calls": str(args.tournament_calls.relative_to(REPO)),
            "tournament_key": str(args.tournament_key.relative_to(REPO)),
        },
        "edge_rows": {
            "source_balanced_valid": len(source_edges),
            "source_balanced_excluded": len(source_exclusions),
            "translation_tournament_valid": len(tournament_edges),
            "translation_tournament_excluded": len(tournament_exclusions),
        },
        "contract_rows": {
            "source_balanced": len(source_contracts),
            "translation_tournament": len(tournament_contracts),
        },
        "transfers": {
            "source_balanced_to_translation_tournament": source_to_tournament,
            "translation_tournament_to_source_balanced": tournament_to_source,
        },
        "verdict": verdict,
        "interpretation": (
            "Promotion requires a pairwise-to-probability translator trained on one frozen "
            "F47 packet to beat F100 on the other packet at the panel level, with no "
            "source regression. This is stricter than same-packet source-heldout fitting."
        ),
    }


def render_md(report: dict[str, Any]) -> str:
    lines = [
        "# F47 Cross-Packet Transfer Audit",
        "",
        report["interpretation"],
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Source-balanced valid/excluded edges: `{report['edge_rows']['source_balanced_valid']}` / `{report['edge_rows']['source_balanced_excluded']}`",
        f"- Translation-tournament valid/excluded edges: `{report['edge_rows']['translation_tournament_valid']}` / `{report['edge_rows']['translation_tournament_excluded']}`",
        "",
        "| direction | train rows | test family rows | test panels | panel translated | panel F100 | delta vs F100 | p vs F100 | promotable |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name, row in report["transfers"].items():
        comp = row.get("panel_comparisons", {}).get("translated_vs_f100_mean_family", {})
        p = comp.get("paired_permutation", {}).get("p_value") if isinstance(comp.get("paired_permutation"), dict) else None
        lines.append(
            "| {name} | {train} | {family_rows} | {panels} | {cand} | {base} | {delta} | {p} | {promote} |".format(
                name=name,
                train=row.get("n_train_family_rows"),
                family_rows=row.get("n_test_family_rows"),
                panels=row.get("n_test_panel_contracts"),
                cand=comp.get("candidate_brier"),
                base=comp.get("baseline_brier"),
                delta=comp.get("delta_candidate_minus_baseline"),
                p=p,
                promote=row.get("promotable"),
            )
        )
    lines.extend(["", "## Source Splits", ""])
    for name, row in report["transfers"].items():
        lines.extend([f"### {name}", "", "| source | n panels | delta translated-minus-F100 |", "|---|---:|---:|"])
        by_source = row.get("panel_comparisons", {}).get("by_source", {})
        for source, source_row in sorted(by_source.items()):
            comp = source_row.get("translated_vs_f100_mean_family", {})
            lines.append(f"| {source} | {comp.get('n')} | {comp.get('delta_candidate_minus_baseline')} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-calls", type=Path, default=DEFAULT_SOURCE_CALLS)
    parser.add_argument("--source-key", type=Path, default=DEFAULT_SOURCE_KEY)
    parser.add_argument("--tournament-calls", type=Path, default=DEFAULT_TOURNAMENT_CALLS)
    parser.add_argument("--tournament-key", type=Path, default=DEFAULT_TOURNAMENT_KEY)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    report = build_report(args)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "transfers": report["transfers"]}, indent=2, sort_keys=True))
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
