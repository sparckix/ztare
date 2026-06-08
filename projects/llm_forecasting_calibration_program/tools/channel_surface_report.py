#!/usr/bin/env python3
"""DB-first channel-surface report for GP-245.

This is intentionally conservative: it uses only the master SQLite DB, extracts
known elicitation channels from parsed_json, and evaluates sign stability by
leave-one-pilot-out. The shrink test is a small diagnostic, not a deployment
claim.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"

MIN_N = 12
SHRINK_GAMMA = 0.10


def load_json(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0 + 1.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    return pearson(rankdata(xs), rankdata(ys))


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def maybe_scale_0_100(x: float) -> float:
    return x / 100.0 if abs(x) > 1.5 else x


def extract_channels(parsed: dict[str, Any]) -> dict[str, float]:
    channels: dict[str, float] = {}

    worry = as_float(parsed.get("tail_insurance_premium"))
    if worry is None:
        worry = as_float(parsed.get("worry"))
    if worry is not None:
        channels["worry"] = maybe_scale_0_100(worry)

    confidence = as_float(parsed.get("verbalized_confidence"))
    if confidence is None:
        confidence = as_float(parsed.get("confidence"))
    if confidence is not None:
        channels["confidence"] = maybe_scale_0_100(confidence)

    spread = as_float(parsed.get("spread"))
    if spread is None:
        buy = as_float(parsed.get("p_buy_yes_max"))
        sell = as_float(parsed.get("p_sell_yes_min"))
        if buy is not None and sell is not None:
            spread = sell - buy
    if spread is not None:
        channels["bid_ask_spread"] = spread

    blo = as_float(parsed.get("predicted_brier_lo"))
    bhi = as_float(parsed.get("predicted_brier_hi"))
    if blo is not None and bhi is not None:
        channels["self_brier_mid"] = (blo + bhi) / 2.0
        channels["self_brier_width"] = bhi - blo

    p_base = as_float(parsed.get("p_base_outside"))
    p_success = as_float(parsed.get("p_success"))
    if p_base is not None:
        channels["outside_view_base"] = p_base
        if p_success is not None:
            channels["outside_view_gap"] = abs(p_success - p_base)

    t_no = as_float(parsed.get("threshold_no_bad"))
    t_yes = as_float(parsed.get("threshold_yes_bad"))
    if t_no is not None and t_yes is not None:
        channels["decision_threshold_width"] = t_yes - t_no

    failure_modes = parsed.get("failure_modes")
    if isinstance(failure_modes, list):
        channels["failure_mode_count"] = float(len(failure_modes))
    elif isinstance(failure_modes, str):
        channels["failure_mode_count"] = float(len([x for x in failure_modes.split(";") if x.strip()]))

    sham = as_float(parsed.get("sham"))
    if sham is not None:
        channels["sham_scalar_control"] = maybe_scale_0_100(sham)

    p2 = as_float(parsed.get("p2"))
    if p2 is not None and p_success is not None:
        channels["resample_disagreement"] = abs(p_success - p2)

    return {k: v for k, v in channels.items() if math.isfinite(v)}


def load_rows(db: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    rows: list[dict[str, Any]] = []
    for pilot_id, contract_id, family, p_success, brier_value, y_known, parsed_json in cur.execute(
        """
        SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success, pc.brier,
               c.y_known, pc.parsed_json
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
          AND pc.brier IS NOT NULL
          AND c.y_known IS NOT NULL
          AND pc.family IS NOT NULL
        """
    ):
        parsed = load_json(parsed_json)
        channels = extract_channels(parsed)
        if not channels:
            continue
        rows.append(
            {
                "pilot_id": str(pilot_id),
                "contract_id": str(contract_id),
                "family": str(family),
                "p_success": float(p_success),
                "brier": float(brier_value),
                "y_known": int(y_known),
                "channels": channels,
            }
        )
    con.close()
    return rows


def channel_values(rows: Iterable[dict[str, Any]], channel: str) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        value = row["channels"].get(channel)
        if value is None:
            continue
        xs.append(float(value))
        ys.append(float(row["brier"]))
    return xs, ys


def zscore_params(values: list[float]) -> tuple[float, float] | None:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    sd = statistics.pstdev(values)
    if sd <= 0:
        return None
    return mean, sd


def clamp01(x: float) -> float:
    return min(1.0, max(0.0, x))


def heldout_shrink_score(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    channel: str,
    train_rho: float,
    *,
    invert_direction: bool = False,
) -> dict[str, Any] | None:
    train_values = [row["channels"][channel] for row in train_rows if channel in row["channels"]]
    params = zscore_params(train_values)
    if params is None:
        return None
    mean, sd = params
    direction = 1.0 if train_rho >= 0 else -1.0
    if invert_direction:
        direction *= -1.0
    deltas: list[float] = []
    n = 0
    for row in test_rows:
        if channel not in row["channels"]:
            continue
        p = float(row["p_success"])
        y = int(row["y_known"])
        z = (float(row["channels"][channel]) - mean) / sd
        risk = max(-2.0, min(2.0, direction * z))
        # Positive risk means the channel predicted higher error in training,
        # so shrink toward 0.5. Negative risk slightly unshrinks, bounded.
        p_adj = clamp01(p + SHRINK_GAMMA * risk * (0.5 - p))
        deltas.append(brier(p_adj, y) - brier(p, y))
        n += 1
    if n < MIN_N:
        return None
    return {
        "n": n,
        "mean_delta_brier": round(statistics.mean(deltas), 6),
        "improved": statistics.mean(deltas) < 0,
    }


def summarize(db: Path) -> dict[str, Any]:
    rows = load_rows(db)
    by_family_channel: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    channel_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for channel in row["channels"]:
            by_family_channel[(row["family"], channel)].append(row)
            channel_counts[channel] += 1

    summaries = []
    loo_results = []
    for (family, channel), items in sorted(by_family_channel.items()):
        xs, ys = channel_values(items, channel)
        rho = spearman(xs, ys)
        pilots = sorted({row["pilot_id"] for row in items})
        summary = {
            "family": family,
            "channel": channel,
            "n": len(xs),
            "pilots": len(pilots),
            "spearman_channel_brier": round(rho, 4) if rho is not None else None,
        }
        summaries.append(summary)
        if len(xs) < MIN_N * 2 or len(pilots) < 2:
            continue
        per_pilot = []
        for heldout in pilots:
            train = [row for row in items if row["pilot_id"] != heldout]
            test = [row for row in items if row["pilot_id"] == heldout]
            tx, ty = channel_values(train, channel)
            hx, hy = channel_values(test, channel)
            if len(tx) < MIN_N or len(hx) < MIN_N:
                continue
            train_rho = spearman(tx, ty)
            test_rho = spearman(hx, hy)
            if train_rho is None or test_rho is None:
                continue
            shrink = heldout_shrink_score(train, test, channel, train_rho)
            inverted = heldout_shrink_score(train, test, channel, train_rho, invert_direction=True)
            direction_control = None
            if shrink and inverted:
                edge = shrink["mean_delta_brier"] - inverted["mean_delta_brier"]
                direction_control = {
                    "inverted_mean_delta_brier": inverted["mean_delta_brier"],
                    "actual_minus_inverted_delta": round(edge, 6),
                    "actual_beats_inverted": edge < 0,
                }
            per_pilot.append(
                {
                    "heldout_pilot": heldout,
                    "train_n": len(tx),
                    "test_n": len(hx),
                    "train_rho": round(train_rho, 4),
                    "test_rho": round(test_rho, 4),
                    "sign_match": (train_rho >= 0) == (test_rho >= 0),
                    "shrink": shrink,
                    "direction_control": direction_control,
                }
            )
        if per_pilot:
            sign_matches = [r["sign_match"] for r in per_pilot]
            shrink_rows = [r["shrink"] for r in per_pilot if r["shrink"]]
            control_rows = [r["direction_control"] for r in per_pilot if r["direction_control"]]
            loo_results.append(
                {
                    "family": family,
                    "channel": channel,
                    "folds": len(per_pilot),
                    "sign_match_rate": round(sum(sign_matches) / len(sign_matches), 4),
                    "mean_test_rho": round(statistics.mean(r["test_rho"] for r in per_pilot), 4),
                    "shrink_folds": len(shrink_rows),
                    "shrink_improved_rate": round(
                        sum(1 for r in shrink_rows if r["improved"]) / len(shrink_rows), 4
                    ) if shrink_rows else None,
                    "mean_shrink_delta_brier": round(
                        statistics.mean(r["mean_delta_brier"] for r in shrink_rows), 6
                    ) if shrink_rows else None,
                    "direction_control_folds": len(control_rows),
                    "actual_beats_inverted_rate": round(
                        sum(1 for r in control_rows if r["actual_beats_inverted"]) / len(control_rows), 4
                    ) if control_rows else None,
                    "mean_actual_minus_inverted_delta": round(
                        statistics.mean(r["actual_minus_inverted_delta"] for r in control_rows), 6
                    ) if control_rows else None,
                    "fold_rows": per_pilot,
                }
            )

    ranked = sorted(
        loo_results,
        key=lambda r: (
            r["sign_match_rate"],
            r["actual_beats_inverted_rate"] if r["actual_beats_inverted_rate"] is not None else -1,
            -(r["mean_actual_minus_inverted_delta"] if r["mean_actual_minus_inverted_delta"] is not None else 999),
            r["folds"],
        ),
        reverse=True,
    )
    deployable_candidates = [
        row for row in ranked
        if row["folds"] >= 3
        and row["sign_match_rate"] >= 0.70
        and row.get("mean_shrink_delta_brier") is not None
        and row["mean_shrink_delta_brier"] < 0
        and row.get("actual_beats_inverted_rate") is not None
        and row["actual_beats_inverted_rate"] >= 0.70
        and row.get("mean_actual_minus_inverted_delta") is not None
        and row["mean_actual_minus_inverted_delta"] < 0
    ]
    return {
        "schema": "gp245-channel-surface-report-v2",
        "db": str(db),
        "rows_with_channels_and_brier": len(rows),
        "channel_counts": dict(sorted(channel_counts.items())),
        "family_channel_summary": summaries,
        "leave_one_pilot_out": ranked,
        "deployable_candidate_cells": deployable_candidates,
        "interpretation": {
            "sign_match_rate": "Fraction of heldout pilot folds where train and heldout Spearman signs match.",
            "mean_shrink_delta_brier": "Brier(adj)-Brier(raw), negative is better. Diagnostic only.",
            "actual_minus_inverted_delta": "Actual channel-direction shrink delta minus inverted-direction shrink delta; negative means the learned direction beats the wrong-direction control.",
            "guardrail": "Do not promote a policy from in-sample Spearman alone; require heldout lift and an inverted-direction control before deployment.",
        },
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "channel_surface_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Channel Surface Report", ""]
    lines.append(f"- Rows with channels and Brier: {result['rows_with_channels_and_brier']}")
    lines.append("")
    lines.append("## Channel Counts")
    lines.append("")
    for channel, n in result["channel_counts"].items():
        lines.append(f"- `{channel}`: {n}")
    lines.append("")
    lines.append("## Top Leave-One-Pilot-Out Cells")
    lines.append("")
    for row in result["leave_one_pilot_out"][:20]:
        lines.append(
            f"- `{row['family']}` / `{row['channel']}`: folds={row['folds']}, "
            f"sign_match={row['sign_match_rate']}, "
            f"mean_test_rho={row['mean_test_rho']}, "
            f"shrink_delta={row['mean_shrink_delta_brier']}, "
            f"beats_inverted={row['actual_beats_inverted_rate']}, "
            f"direction_edge={row['mean_actual_minus_inverted_delta']}"
        )
    lines.append("")
    lines.append("## Candidate Cells Passing Direction Control")
    lines.append("")
    if result["deployable_candidate_cells"]:
        for row in result["deployable_candidate_cells"]:
            lines.append(
                f"- `{row['family']}` / `{row['channel']}`: folds={row['folds']}, "
                f"sign_match={row['sign_match_rate']}, "
                f"shrink_delta={row['mean_shrink_delta_brier']}, "
                f"beats_inverted={row['actual_beats_inverted_rate']}, "
                f"direction_edge={row['mean_actual_minus_inverted_delta']}"
            )
    else:
        lines.append("- None under the current conservative filter.")
    lines.append("")
    lines.append("## Guardrail")
    lines.append("")
    lines.append(result["interpretation"]["guardrail"])
    lines.append("")
    (out_dir / "channel_surface_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    result = summarize(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
