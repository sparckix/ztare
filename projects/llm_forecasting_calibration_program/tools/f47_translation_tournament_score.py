#!/usr/bin/env python3
"""Score F47 overlapping tournament calls and test ranking-to-Brier translation."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_CALLS = WORKSPACE / "pilot_f47_translation_tournament_calls_2026_06_03.jsonl"
DEFAULT_KEY = WORKSPACE / "f47_translation_tournament_packet_2026_06_03_answer_key.json"
DEFAULT_OUT_JSON = WORKSPACE / "f47_translation_tournament_score_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "f47_translation_tournament_score_2026_06_03.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_key(path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text())
    return {str(row["pair_id"]): row for row in data["answer_key"]}


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        x = float(value)
    except Exception:
        return None
    if not math.isfinite(x):
        return None
    return x


def sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def family_for(row: dict[str, Any]) -> str:
    runtime = str(row.get("runtime") or "")
    model = str(row.get("model") or "")
    if runtime == "codex" and model == "gpt-5.5":
        return "codex_55"
    if runtime == "codex" and model == "gpt-5.4-mini":
        return "codex_mini"
    return runtime or str(row.get("agent_id") or "unknown")


def brier(p: float, y: int) -> float:
    p = min(1.0, max(0.0, p))
    return (p - y) ** 2


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def fit_logistic(xs: list[float], ys: list[int]) -> tuple[float, float]:
    """Tiny deterministic logistic fit with L2 on slope only."""
    if len(set(ys)) < 2:
        base = (sum(ys) + 0.5) / (len(ys) + 1.0)
        return math.log(base / (1.0 - base)), 0.0
    mean_x = statistics.mean(xs)
    sd_x = statistics.pstdev(xs) or 1.0
    zs = [(x - mean_x) / sd_x for x in xs]
    a = math.log((sum(ys) + 0.5) / (len(ys) - sum(ys) + 0.5))
    b = 0.0
    lr = 0.05
    l2 = 0.01
    n = float(len(zs))
    for _ in range(800):
        ga = 0.0
        gb = 0.0
        for z, y in zip(zs, ys):
            p = sigmoid(a + b * z)
            ga += p - y
            gb += (p - y) * z
        ga /= n
        gb = gb / n + l2 * b
        a -= lr * ga
        b -= lr * gb
    # Convert standardized fit back to original x scale.
    return a - b * mean_x / sd_x, b / sd_x


def load_edges(calls_path: Path, key_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    key = load_key(key_path)
    observations: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for line_no, row in enumerate(read_jsonl(calls_path), start=1):
        pair_id = str(row.get("pair_id") or "")
        audit = row.get("schema_audit") or {}
        parsed = row.get("parsed") or {}
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
                    "line": line_no,
                    "pair_id": pair_id,
                    "agent_id": row.get("agent_id"),
                    "reason": reason,
                }
            )
            continue
        answer = key[pair_id]
        observations.append(
            {
                "pair_id": pair_id,
                "source": str(answer["source"]),
                "family": family_for(row),
                "agent_id": row.get("agent_id"),
                "contract_id_a": str(answer["contract_id_a"]),
                "contract_id_b": str(answer["contract_id_b"]),
                "p_a": p_a,
                "p_b": p_b,
                "predicted_delta": delta,
                "predicted_sign": sign(delta),
                "actual_delta": int(answer["actual_delta"]),
                "actual_sign": sign(float(answer["actual_delta"])),
                "y_a": int(answer["y_a"]),
                "y_b": int(answer["y_b"]),
            }
        )
    return observations, exclusions


def pairwise_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0, "error": "no rows"}
    utilities = [
        0
        if int(row["predicted_sign"]) == 0
        else (1 if int(row["predicted_sign"]) == int(row["actual_sign"]) else -1)
        for row in rows
    ]
    random = [0 for _ in rows]
    return {
        "n": len(rows),
        "accuracy": round(sum(1 for u in utilities if u == 1) / len(utilities), 6),
        "mean_utility": round(statistics.mean(utilities), 6),
        "paired_vs_random": paired_permutation_test(utilities, random, seed=47),
    }


def contract_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        family = str(row["family"])
        source = str(row["source"])
        for side in ("a", "b"):
            cid = str(row[f"contract_id_{side}"])
            y = int(row[f"y_{side}"])
            emitted_p = float(row[f"p_{side}"])
            relative_score = float(row["predicted_delta"]) if side == "a" else -float(row["predicted_delta"])
            key = (family, source, cid)
            slot = grouped.setdefault(
                key,
                {
                    "family": family,
                    "source": source,
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
                "family": slot["family"],
                "source": slot["source"],
                "contract_id": slot["contract_id"],
                "y": int(slot["y"]),
                "degree": int(slot["degree"]),
                "raw_context_p": statistics.mean(slot["emitted_ps"]),
                "pairwise_score": statistics.mean(slot["relative_scores"]),
            }
        )
    return out


def evaluate_translation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    contracts = contract_rows(rows)
    if not contracts:
        return {"n_contracts": 0, "error": "no contract rows"}
    sources = sorted({row["source"] for row in contracts})
    heldout_predictions: list[dict[str, Any]] = []
    for source in sources:
        train = [row for row in contracts if row["source"] != source]
        test = [row for row in contracts if row["source"] == source]
        if not train or not test:
            continue
        a, b = fit_logistic(
            [float(row["pairwise_score"]) for row in train],
            [int(row["y"]) for row in train],
        )
        for row in test:
            p_translated = sigmoid(a + b * float(row["pairwise_score"]))
            heldout_predictions.append(
                {
                    **row,
                    "translated_p": p_translated,
                    "heldout_source": source,
                }
            )
    if not heldout_predictions:
        return {"n_contracts": len(contracts), "error": "no heldout predictions"}

    raw_losses = [brier(float(row["raw_context_p"]), int(row["y"])) for row in heldout_predictions]
    translated_losses = [brier(float(row["translated_p"]), int(row["y"])) for row in heldout_predictions]
    prevalence = statistics.mean(int(row["y"]) for row in heldout_predictions)
    prevalence_losses = [brier(prevalence, int(row["y"])) for row in heldout_predictions]
    by_source: dict[str, Any] = {}
    for source in sources:
        subset = [row for row in heldout_predictions if row["source"] == source]
        if not subset:
            continue
        raw = [brier(float(row["raw_context_p"]), int(row["y"])) for row in subset]
        trans = [brier(float(row["translated_p"]), int(row["y"])) for row in subset]
        by_source[source] = {
            "n": len(subset),
            "raw_context_brier": round(statistics.mean(raw), 6),
            "translated_brier": round(statistics.mean(trans), 6),
            "delta_translated_minus_raw": round(statistics.mean([t - r for t, r in zip(trans, raw)]), 6),
        }
    paired = paired_permutation_test(translated_losses, raw_losses, seed=47)
    return {
        "n_contracts": len(heldout_predictions),
        "degree_counts": dict(sorted(Counter(int(row["degree"]) for row in heldout_predictions).items())),
        "source_heldout_protocol": "train logistic map pairwise_score->y on three sources, evaluate held-out source; repeat for all sources",
        "raw_context_brier": round(statistics.mean(raw_losses), 6),
        "translated_brier": round(statistics.mean(translated_losses), 6),
        "prevalence_brier": round(statistics.mean(prevalence_losses), 6),
        "delta_translated_minus_raw": round(statistics.mean([t - r for t, r in zip(translated_losses, raw_losses)]), 6),
        "paired_translated_vs_raw": paired,
        "by_source": by_source,
        "promotion_gate": {
            "requires_delta_at_most": -0.01,
            "requires_p_at_most": 0.05,
            "requires_no_source_regression": True,
        },
        "promotable": bool(
            statistics.mean([t - r for t, r in zip(translated_losses, raw_losses)]) <= -0.01
            and paired.get("p_value", 1.0) <= 0.05
            and all(row["delta_translated_minus_raw"] <= 0 for row in by_source.values())
        ),
    }


def build_report(rows: list[dict[str, Any]], exclusions: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {"all_calls": rows}
    for family in sorted({row["family"] for row in rows}):
        groups[f"family::{family}"] = [row for row in rows if row["family"] == family]
    return {
        "report": "f47_translation_tournament_score",
        "date": "2026-06-03",
        "valid_rows": len(rows),
        "excluded_rows": len(exclusions),
        "exclusion_reasons": {
            reason: sum(1 for e in exclusions if e["reason"] == reason)
            for reason in sorted({e["reason"] for e in exclusions})
        },
        "pairwise": {name: pairwise_summary(items) for name, items in groups.items()},
        "translation": {name: evaluate_translation(items) for name, items in groups.items()},
        "interpretation": (
            "Pairwise utility tests whether F47 ranking still works on the overlapping graph. "
            "Translation tests whether the relative score can be calibrated into held-out "
            "contract probabilities that beat the prompt's own emitted p_success."
        ),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# F47 translation tournament score - 2026-06-03",
        "",
        report["interpretation"],
        "",
        f"Valid rows: `{report['valid_rows']}`. Excluded rows: `{report['excluded_rows']}`.",
        "",
        "## Pairwise Utility",
        "",
        "| group | n | accuracy | utility | p vs random |",
        "|---|---:|---:|---:|---:|",
    ]
    for group, row in report["pairwise"].items():
        p = row.get("paired_vs_random", {}).get("p_value") if isinstance(row.get("paired_vs_random"), dict) else None
        lines.append(
            f"| {group} | {row.get('n')} | {row.get('accuracy')} | {row.get('mean_utility')} | {p} |"
        )
    lines.extend(["", "## Source-Heldout Translation", "", "| group | contracts | raw Brier | translated Brier | delta | p vs raw | promotable |", "|---|---:|---:|---:|---:|---:|---|"])
    for group, row in report["translation"].items():
        p = row.get("paired_translated_vs_raw", {}).get("p_value") if isinstance(row.get("paired_translated_vs_raw"), dict) else None
        lines.append(
            f"| {group} | {row.get('n_contracts')} | {row.get('raw_context_brier')} | {row.get('translated_brier')} | {row.get('delta_translated_minus_raw')} | {p} | {row.get('promotable')} |"
        )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--answer-key", type=Path, default=DEFAULT_KEY)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    rows, exclusions = load_edges(args.calls, args.answer_key)
    report = build_report(rows, exclusions)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report, args.out_md)
    print(json.dumps(report["translation"].get("all_calls", {}), indent=2, sort_keys=True))
    print(f"wrote {args.out_json}")
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
