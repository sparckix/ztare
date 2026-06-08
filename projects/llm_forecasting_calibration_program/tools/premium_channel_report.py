#!/usr/bin/env python3
"""Contamination-clean premium/worry channel report for GP-245.

This report is narrower than channel_surface_report.py. It evaluates the
premium_batch1 + premium_crossfamily rows where the emitted JSON contains the
explicit scalar controls {worry, confidence, sham, p2, abserr}. The target is
absolute error, not Brier shrink deployment.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_PILOTS = ("premium_batch1", "premium_crossfamily")

FAMILY_ALIASES = {
    "codex_mini": "codex_54mini",
}


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
    try:
        x = float(value)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def maybe_scale_0_100(x: float) -> float:
    return x / 100.0 if abs(x) > 1.5 else x


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


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    return pearson(rankdata(xs), rankdata(ys))


def rounded(value: float | None, digits: int = 4) -> float | None:
    return round(value, digits) if value is not None else None


def load_rows(db: Path, pilots: tuple[str, ...]) -> list[dict[str, Any]]:
    con = sqlite3.connect(db)
    placeholders = ",".join("?" for _ in pilots)
    cur = con.cursor()
    rows: list[dict[str, Any]] = []
    for pilot_id, contract_id, family, p_success, y_known, parsed_json in cur.execute(
        f"""
        SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success,
               c.y_known, pc.parsed_json
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.pilot_id IN ({placeholders})
          AND pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
          AND c.y_known IS NOT NULL
          AND pc.parsed_json IS NOT NULL
        """,
        pilots,
    ):
        parsed = load_json(parsed_json)
        worry = as_float(parsed.get("worry"))
        confidence = as_float(parsed.get("confidence"))
        sham = as_float(parsed.get("sham"))
        p2 = as_float(parsed.get("p2"))
        abserr = as_float(parsed.get("abserr"))
        p = float(p_success)
        y = int(y_known)
        if abserr is None:
            abserr = abs(p - y)
        if worry is None:
            continue
        row = {
            "pilot_id": str(pilot_id),
            "contract_id": str(contract_id),
            "family": FAMILY_ALIASES.get(str(family), str(family)),
            "p_success": p,
            "y_known": y,
            "abserr": float(abserr),
            "worry": maybe_scale_0_100(worry),
        }
        if confidence is not None:
            row["confidence"] = maybe_scale_0_100(confidence)
        if sham is not None:
            row["sham"] = maybe_scale_0_100(sham)
        if p2 is not None:
            row["p2_disagreement"] = abs(p - float(p2))
        rows.append(row)
    con.close()
    return rows


def corr(rows: list[dict[str, Any]], channel: str, *, method: str) -> float | None:
    xs = [float(row[channel]) for row in rows if channel in row]
    ys = [float(row["abserr"]) for row in rows if channel in row]
    if method == "spearman":
        return spearman(xs, ys)
    return pearson(xs, ys)


def summarize_group(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    channels = ["worry", "confidence", "sham", "p2_disagreement"]
    values = {
        channel: {
            "n": sum(1 for row in rows if channel in row),
            "pearson_abserr": rounded(corr(rows, channel, method="pearson"), 4),
            "spearman_abserr": rounded(corr(rows, channel, method="spearman"), 4),
        }
        for channel in channels
        if any(channel in row for row in rows)
    }
    worry_r = values.get("worry", {}).get("pearson_abserr")
    confidence_r = values.get("confidence", {}).get("pearson_abserr")
    sham_r = values.get("sham", {}).get("pearson_abserr")
    beats_confidence = (
        worry_r is not None and confidence_r is not None and worry_r > confidence_r
    )
    beats_sham = worry_r is not None and sham_r is not None and worry_r > sham_r
    return {
        "label": label,
        "n": len(rows),
        "pilots": sorted({row["pilot_id"] for row in rows}),
        "channels": values,
        "worry_positive": worry_r is not None and worry_r > 0,
        "worry_beats_confidence": beats_confidence,
        "worry_beats_sham": beats_sham,
        "worry_beats_confidence_and_sham": beats_confidence and beats_sham,
        "mean_abserr": round(statistics.mean(row["abserr"] for row in rows), 4) if rows else None,
    }


def summarize(db: Path, pilots: tuple[str, ...]) -> dict[str, Any]:
    rows = load_rows(db, pilots)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[row["family"]].append(row)
    family_rows = [summarize_group(family, items) for family, items in sorted(by_family.items())]
    pooled = summarize_group("pooled", rows)
    family_positive = sum(1 for row in family_rows if row["worry_positive"])
    family_beats_controls = sum(1 for row in family_rows if row["worry_beats_confidence_and_sham"])
    return {
        "schema": "gp245-premium-channel-report-v1",
        "db": str(db),
        "pilots": list(pilots),
        "rows": len(rows),
        "family_count": len(family_rows),
        "family_rows": family_rows,
        "pooled": pooled,
        "cross_family_standard": {
            "worry_positive_families": family_positive,
            "worry_beats_confidence_and_sham_families": family_beats_controls,
            "passes_4_of_5_direction_standard": family_positive >= 4 and len(family_rows) >= 5,
            "passes_4_of_5_control_standard": family_beats_controls >= 4 and len(family_rows) >= 5,
        },
        "interpretation": {
            "target": "absolute error |p_success - y_known|, using parsed_json.abserr when present",
            "control_rule": "worry beats controls when Pearson(worry, |err|) exceeds Pearson(confidence, |err|) and Pearson(sham, |err|).",
            "claim_scope": "Cross-family replication of a worry/error direction, not a deployed uniform Brier-improvement policy.",
        },
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "premium_channel_report.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Premium Channel Report", ""]
    lines.append(f"- Rows: {result['rows']}")
    lines.append(f"- Pilots: {', '.join(result['pilots'])}")
    standard = result["cross_family_standard"]
    lines.append(
        "- Cross-family standard: "
        f"worry-positive {standard['worry_positive_families']}/{result['family_count']}; "
        f"worry beats confidence+sham {standard['worry_beats_confidence_and_sham_families']}/{result['family_count']}"
    )
    lines.append("")
    lines.append("| Family | n | n worry/conf/sham | r(worry, |err|) | r(conf, |err|) | r(sham, |err|) | beats conf+sham? |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for row in result["family_rows"]:
        ch = row["channels"]
        lines.append(
            f"| `{row['label']}` | {row['n']} | "
            f"{ch['worry']['n']}/{ch.get('confidence', {}).get('n')}/{ch.get('sham', {}).get('n')} | "
            f"{ch['worry']['pearson_abserr']} | "
            f"{ch.get('confidence', {}).get('pearson_abserr')} | "
            f"{ch.get('sham', {}).get('pearson_abserr')} | "
            f"{'yes' if row['worry_beats_confidence_and_sham'] else 'no'} |"
        )
    pooled = result["pooled"]
    ch = pooled["channels"]
    lines.append(
        f"| `pooled` | {pooled['n']} | "
        f"{ch['worry']['n']}/{ch.get('confidence', {}).get('n')}/{ch.get('sham', {}).get('n')} | "
        f"{ch['worry']['pearson_abserr']} | "
        f"{ch.get('confidence', {}).get('pearson_abserr')} | {ch.get('sham', {}).get('pearson_abserr')} | "
        f"{'yes' if pooled['worry_beats_confidence_and_sham'] else 'no'} |"
    )
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(result["interpretation"]["claim_scope"])
    lines.append("")
    lines.append(
        "This report uses absolute error rather than Brier. It should update Law 2 as "
        "an elicited-error-surface claim, while keeping the separate Brier-shrink "
        "deployment claim unpromoted until a heldout correction improves Brier."
    )
    lines.append("")
    (out_dir / "premium_channel_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilots", nargs="+", default=list(DEFAULT_PILOTS))
    parser.add_argument("--out-dir", type=Path)
    args = parser.parse_args()
    result = summarize(args.db, tuple(args.pilots))
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
