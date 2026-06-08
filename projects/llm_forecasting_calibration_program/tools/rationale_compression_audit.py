#!/usr/bin/env python3
"""Compression-distance audit for rationale/probability decoupling.

This is a no-call test of a candidate applied lever: whether deterministic
compressed description length and normalized compression distance (NCD) of
forecast rationales add usable signal about Brier movement under an inversion
prompt. It intentionally treats compression as a proxy feature, not as a
literal Kolmogorov-complexity estimate.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import spearman_rho_with_ci


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT_JSON = WORKSPACE / "rationale_compression_audit_2026_06_03.json"
DEFAULT_OUT_MD = WORKSPACE / "rationale_compression_audit_2026_06_03.md"

BASELINE_PILOT = "v28a_full__v25_external"
INVERSION_PILOT = "v28i_full__v25_external"
MIN_FAMILY_N = 20


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


def clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def compressed_len(text: str) -> int:
    return len(zlib.compress(clean_text(text).encode("utf-8"), level=9))


def ncd(text_a: str, text_b: str) -> float:
    ca = compressed_len(text_a)
    cb = compressed_len(text_b)
    cab = compressed_len(clean_text(text_a) + "\n" + clean_text(text_b))
    denom = max(ca, cb)
    if denom <= 0:
        return 0.0
    return (cab - min(ca, cb)) / denom


def brier(p: float, y: int) -> float:
    return (p - y) ** 2


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def rounded(value: Any, ndigits: int = 6) -> Any:
    if isinstance(value, float):
        return round(value, ndigits)
    return value


def rho(xs: list[float], ys: list[float]) -> dict[str, Any]:
    if len(xs) < 4 or len(xs) != len(ys):
        return {"n": len(xs), "rho": None, "ci_lo": None, "ci_hi": None}
    r, lo, hi = spearman_rho_with_ci(xs, ys)
    return {
        "n": len(xs),
        "rho": round(r, 6) if r is not None else None,
        "ci_lo": round(lo, 6) if lo is not None else None,
        "ci_hi": round(hi, 6) if hi is not None else None,
    }


def load_rows(db: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT pc.pilot_id, pc.contract_id, pc.family, pc.p_success,
                   pc.brier, pc.parsed_json, c.y_known, c.question,
                   c.source, c.source_corpus
            FROM pilot_calls pc
            JOIN contracts c ON c.contract_id = pc.contract_id
            WHERE pc.pilot_id IN (?, ?)
              AND pc.schema_ok = 1
              AND pc.p_success IS NOT NULL
              AND pc.brier IS NOT NULL
              AND pc.family IS NOT NULL
              AND c.y_known IN (0, 1)
            """,
            (BASELINE_PILOT, INVERSION_PILOT),
        ).fetchall()
    finally:
        con.close()

    out: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        parsed = load_json(row["parsed_json"])
        rationale = clean_text(str(parsed.get("rationale_short") or ""))
        p = as_float(parsed.get("p_success"))
        if p is None:
            p = as_float(row["p_success"])
        if p is None or not rationale:
            continue
        key = (str(row["pilot_id"]), str(row["contract_id"]), str(row["family"]))
        out[key] = {
            "pilot_id": str(row["pilot_id"]),
            "contract_id": str(row["contract_id"]),
            "family": str(row["family"]),
            "p_success": p,
            "brier": float(row["brier"]),
            "computed_brier": brier(p, int(row["y_known"])),
            "y_known": int(row["y_known"]),
            "rationale": rationale,
            "compressed_len": compressed_len(rationale),
            "question": str(row["question"] or ""),
            "source": str(row["source"] or row["source_corpus"] or "unknown"),
        }
    return out


def paired_rows(rows: dict[tuple[str, str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for (_, contract_id, family), base in rows.items():
        if base["pilot_id"] != BASELINE_PILOT:
            continue
        inv = rows.get((INVERSION_PILOT, contract_id, family))
        if not inv:
            continue
        distance = ncd(base["rationale"], inv["rationale"])
        pairs.append(
            {
                "contract_id": contract_id,
                "family": family,
                "source": base["source"],
                "y_known": base["y_known"],
                "baseline_p_success": base["p_success"],
                "inversion_p_success": inv["p_success"],
                "abs_p_delta": abs(inv["p_success"] - base["p_success"]),
                "baseline_brier": base["brier"],
                "inversion_brier": inv["brier"],
                "brier_delta_inversion_minus_baseline": inv["brier"] - base["brier"],
                "baseline_compressed_len": base["compressed_len"],
                "inversion_compressed_len": inv["compressed_len"],
                "compressed_len_delta": inv["compressed_len"] - base["compressed_len"],
                "rationale_ncd": distance,
            }
        )
    return pairs


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    brier_deltas = [float(r["brier_delta_inversion_minus_baseline"]) for r in rows]
    ncds = [float(r["rationale_ncd"]) for r in rows]
    p_deltas = [float(r["abs_p_delta"]) for r in rows]
    len_deltas = [float(r["compressed_len_delta"]) for r in rows]
    median_ncd = statistics.median(ncds)
    small_p_threshold = 0.03
    high_ncd_low_p = [
        r for r in rows if float(r["rationale_ncd"]) >= median_ncd and float(r["abs_p_delta"]) <= small_p_threshold
    ]
    low_ncd_rows = [r for r in rows if float(r["rationale_ncd"]) < median_ncd]
    high_ncd_rows = [r for r in rows if float(r["rationale_ncd"]) >= median_ncd]

    def mean(key: str, subset: list[dict[str, Any]] = rows) -> float:
        return statistics.mean(float(r[key]) for r in subset)

    result = {
        "n": len(rows),
        "mean_baseline_brier": mean("baseline_brier"),
        "mean_inversion_brier": mean("inversion_brier"),
        "mean_brier_delta_inversion_minus_baseline": statistics.mean(brier_deltas),
        "median_brier_delta_inversion_minus_baseline": statistics.median(brier_deltas),
        "mean_rationale_ncd": statistics.mean(ncds),
        "median_rationale_ncd": median_ncd,
        "mean_abs_p_delta": statistics.mean(p_deltas),
        "median_abs_p_delta": statistics.median(p_deltas),
        "mean_compressed_len_delta": statistics.mean(len_deltas),
        "n_high_ncd_low_probability_movement": len(high_ncd_low_p),
        "share_high_ncd_low_probability_movement": len(high_ncd_low_p) / len(rows),
        "low_ncd_mean_brier_delta": (
            mean("brier_delta_inversion_minus_baseline", low_ncd_rows) if low_ncd_rows else None
        ),
        "high_ncd_mean_brier_delta": (
            mean("brier_delta_inversion_minus_baseline", high_ncd_rows) if high_ncd_rows else None
        ),
        "spearman_ncd_vs_abs_p_delta": rho(ncds, p_deltas),
        "spearman_ncd_vs_brier_delta": rho(ncds, brier_deltas),
        "spearman_len_delta_vs_brier_delta": rho(len_deltas, brier_deltas),
    }
    return {k: rounded(v) for k, v in result.items()}


def build_report(db: Path) -> dict[str, Any]:
    loaded = load_rows(db)
    pairs = paired_rows(loaded)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        by_family[str(row["family"])].append(row)
        by_source[str(row["source"])].append(row)

    overall = summarize(pairs)
    family = {name: summarize(rs) for name, rs in sorted(by_family.items()) if len(rs) >= 4}
    source = {name: summarize(rs) for name, rs in sorted(by_source.items()) if len(rs) >= 4}

    ncd_brier_rho = overall.get("spearman_ncd_vs_brier_delta", {}).get("rho")
    high_minus_low = None
    if overall.get("high_ncd_mean_brier_delta") is not None and overall.get("low_ncd_mean_brier_delta") is not None:
        high_minus_low = overall["high_ncd_mean_brier_delta"] - overall["low_ncd_mean_brier_delta"]
    promotable = (
        isinstance(ncd_brier_rho, float)
        and ncd_brier_rho <= -0.20
        and isinstance(high_minus_low, float)
        and high_minus_low < -0.01
        and len(pairs) >= 100
    )

    return {
        "schema": "rationale-compression-audit-v1",
        "db": str(db),
        "pilots": {
            "baseline": BASELINE_PILOT,
            "inversion": INVERSION_PILOT,
        },
        "methods": {
            "compression": "zlib level 9 over whitespace-normalized rationale_short",
            "ncd": "(C(xy) - min(C(x), C(y))) / max(C(x), C(y))",
            "brier_delta": "inversion_brier - baseline_brier; negative means inversion helped",
            "promotion_gate": "N>=100, Spearman(NCD, brier_delta)<=-0.20, and high-NCD half improves at least 0.01 Brier more than low-NCD half",
        },
        "loaded_rows": len(loaded),
        "paired_rows": len(pairs),
        "overall": overall,
        "by_family": family,
        "by_source": source,
        "policy_verdict": {
            "compression_distance_promotable": promotable,
            "high_minus_low_ncd_brier_delta": round(high_minus_low, 6) if isinstance(high_minus_low, float) else None,
            "interpretation": (
                "Compression distance is a candidate routing feature."
                if promotable
                else "Do not promote compression/NCD as a routing feature from this audit."
            ),
        },
        "example_rows_high_ncd_low_probability_movement": [
            {
                k: rounded(v)
                for k, v in row.items()
                if k
                in {
                    "contract_id",
                    "family",
                    "source",
                    "abs_p_delta",
                    "rationale_ncd",
                    "brier_delta_inversion_minus_baseline",
                }
            }
            for row in sorted(
                pairs,
                key=lambda r: (-float(r["rationale_ncd"]), float(r["abs_p_delta"])),
            )[:10]
        ],
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    overall = report["overall"]
    verdict = report["policy_verdict"]
    lines = [
        "# Rationale Compression Audit",
        "",
        f"- Baseline pilot: `{report['pilots']['baseline']}`",
        f"- Inversion pilot: `{report['pilots']['inversion']}`",
        f"- Paired rows: `{report['paired_rows']}`",
        f"- Mean baseline Brier: `{overall.get('mean_baseline_brier'):.6f}`",
        f"- Mean inversion Brier: `{overall.get('mean_inversion_brier'):.6f}`",
        f"- Mean inversion-minus-baseline Brier: `{overall.get('mean_brier_delta_inversion_minus_baseline'):.6f}`",
        f"- Mean rationale NCD: `{overall.get('mean_rationale_ncd'):.6f}`",
        f"- Mean abs probability movement: `{overall.get('mean_abs_p_delta'):.6f}`",
        f"- High-NCD/low-probability-movement share: `{overall.get('share_high_ncd_low_probability_movement'):.6f}`",
        "",
        "## Compression Signal",
        "",
        f"- Spearman NCD vs abs probability movement: `{overall['spearman_ncd_vs_abs_p_delta']}`",
        f"- Spearman NCD vs Brier delta: `{overall['spearman_ncd_vs_brier_delta']}`",
        f"- High-minus-low NCD Brier delta: `{verdict['high_minus_low_ncd_brier_delta']}`",
        f"- Promotable: `{verdict['compression_distance_promotable']}`",
        f"- Interpretation: {verdict['interpretation']}",
        "",
        "## Family Cells",
        "",
        "| family | n | mean delta | mean NCD | rho NCD vs Brier delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for family, cell in report["by_family"].items():
        rho_cell = cell["spearman_ncd_vs_brier_delta"]["rho"]
        lines.append(
            f"| `{family}` | {cell['n']} | "
            f"{cell['mean_brier_delta_inversion_minus_baseline']:.6f} | "
            f"{cell['mean_rationale_ncd']:.6f} | {rho_cell} |"
        )
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    report = build_report(args.db)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    write_markdown(report, args.out_md)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
