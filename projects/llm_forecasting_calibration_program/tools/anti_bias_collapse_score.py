#!/usr/bin/env python3
"""Score the GP-245 anti-bias-collapse experiment from the master DB.

No model calls. No DB writes. This consumes future `anti_bias_collapse_v1`
rows once they have been ingested into `pilot_calls` / `contracts`.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ztare.experiment_stats import bootstrap_ci, paired_permutation_test


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_OUT = REPO / "projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace"
DEFAULT_PILOT_ID = "anti_bias_collapse_v1"


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


def first(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def class_bucket(label: str | None) -> str:
    text = str(label or "").upper()
    if text.startswith("MIMIC"):
        return "MIMIC"
    if text.startswith("INHERIT"):
        return "INHERIT_CONTROL"
    if text.startswith("ESCAPE"):
        return "ESCAPE"
    return "OTHER"


def mean(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def rounded(value: float | None, digits: int = 6) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def load_calls(db: Path, pilot_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    con = sqlite3.connect(db)
    cur = con.cursor()
    rows: list[dict[str, Any]] = []
    skipped = defaultdict(int)
    for (
        call_id,
        db_pilot_id,
        contract_id,
        agent_id,
        family,
        condition,
        phase,
        p_success,
        parsed_json,
        raw_json,
        contract_raw_json,
    ) in cur.execute(
        """
        SELECT pc.call_id, pc.pilot_id, pc.contract_id, pc.agent_id, pc.family,
               pc.condition, pc.phase, pc.p_success, pc.parsed_json, pc.raw_json,
               c.raw_json
        FROM pilot_calls pc
        JOIN contracts c ON c.contract_id = pc.contract_id
        WHERE pc.pilot_id = ?
          AND pc.schema_ok = 1
          AND pc.p_success IS NOT NULL
        """,
        (pilot_id,),
    ):
        parsed = load_json(parsed_json)
        raw = load_json(raw_json)
        contract_raw = load_json(contract_raw_json)
        bias_id = first(parsed.get("bias_id"), raw.get("bias_id"), contract_raw.get("bias_id"))
        event_id = first(parsed.get("event_id"), raw.get("event_id"), contract_raw.get("event_id"))
        frame = first(parsed.get("frame"), raw.get("frame"), contract_raw.get("frame"), condition)
        prompt_arm = first(parsed.get("prompt_arm"), raw.get("prompt_arm"), contract_raw.get("prompt_arm"), phase)
        g0 = as_float(first(parsed.get("g0"), raw.get("g0"), contract_raw.get("g0")))
        bias_class = first(
            parsed.get("bias_class_preregistered"),
            raw.get("bias_class_preregistered"),
            contract_raw.get("bias_class_preregistered"),
        )
        if not bias_id:
            skipped["missing_bias_id"] += 1
            continue
        if not event_id:
            skipped["missing_event_id"] += 1
            continue
        if frame not in {"A", "B"}:
            skipped["missing_frame"] += 1
            continue
        if prompt_arm not in {"normal", "anti_bias_correction"}:
            skipped["missing_prompt_arm"] += 1
            continue
        if g0 is None:
            skipped["missing_g0"] += 1
            continue
        if not family:
            skipped["missing_family"] += 1
            continue
        rows.append(
            {
                "call_id": call_id,
                "pilot_id": db_pilot_id,
                "contract_id": contract_id,
                "agent_id": agent_id,
                "family": family,
                "bias_id": bias_id,
                "event_id": event_id,
                "frame": frame,
                "prompt_arm": prompt_arm,
                "g0": g0,
                "bias_class": bias_class,
                "class_bucket": class_bucket(bias_class),
                "p_success": float(p_success),
            }
        )
    run_row = cur.execute(
        "SELECT COUNT(*) FROM pilot_runs WHERE pilot_id = ?",
        (pilot_id,),
    ).fetchone()
    con.close()
    meta = {
        "pilot_id": pilot_id,
        "pilot_runs": int(run_row[0] or 0) if run_row else 0,
        "usable_calls": len(rows),
        "skipped": dict(skipped),
    }
    return rows, meta


def frame_gap_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (row["bias_id"], row["event_id"], row["family"], row["prompt_arm"])
        grouped[key][row["frame"]] = row
    out: list[dict[str, Any]] = []
    for (bias_id, event_id, family, prompt_arm), frames in sorted(grouped.items()):
        if "A" not in frames or "B" not in frames:
            continue
        a = frames["A"]
        b = frames["B"]
        g0 = float(a["g0"])
        frame_gap = float(a["p_success"]) - float(b["p_success"])
        excess_gap = frame_gap - g0
        out.append(
            {
                "bias_id": bias_id,
                "event_id": event_id,
                "family": family,
                "prompt_arm": prompt_arm,
                "bias_class": a["bias_class"],
                "class_bucket": a["class_bucket"],
                "g0": g0,
                "p_a": float(a["p_success"]),
                "p_b": float(b["p_success"]),
                "frame_gap": frame_gap,
                "excess_gap": excess_gap,
                "abs_excess_gap": abs(excess_gap),
            }
        )
    return out


def collapse_rows(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in gaps:
        key = (row["bias_id"], row["event_id"], row["family"])
        grouped[key][row["prompt_arm"]] = row
    out: list[dict[str, Any]] = []
    for (bias_id, event_id, family), arms in sorted(grouped.items()):
        if "normal" not in arms or "anti_bias_correction" not in arms:
            continue
        normal = arms["normal"]
        corrected = arms["anti_bias_correction"]
        collapse = float(normal["abs_excess_gap"]) - float(corrected["abs_excess_gap"])
        out.append(
            {
                "bias_id": bias_id,
                "event_id": event_id,
                "family": family,
                "bias_class": normal["bias_class"],
                "class_bucket": normal["class_bucket"],
                "normal_abs_excess": float(normal["abs_excess_gap"]),
                "corrected_abs_excess": float(corrected["abs_excess_gap"]),
                "collapse": collapse,
                "normal_frame_gap": float(normal["frame_gap"]),
                "corrected_frame_gap": float(corrected["frame_gap"]),
                "g0": float(normal["g0"]),
            }
        )
    return out


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    collapses = [float(row["collapse"]) for row in rows]
    normal_abs = [float(row["normal_abs_excess"]) for row in rows]
    corrected_abs = [float(row["corrected_abs_excess"]) for row in rows]
    point, lo, hi = bootstrap_ci(collapses, seed=42)
    perm = paired_permutation_test(corrected_abs, normal_abs, n_perm=5000, seed=42)
    return {
        "n": len(rows),
        "mean_collapse": rounded(mean(collapses)),
        "collapse_ci95": [rounded(lo), rounded(hi)],
        "mean_normal_abs_excess": rounded(mean(normal_abs)),
        "mean_corrected_abs_excess": rounded(mean(corrected_abs)),
        "paired_corrected_minus_normal": perm,
    }


def class_shuffle_control(rows: list[dict[str, Any]], *, n_perm: int = 2000, seed: int = 42) -> dict[str, Any] | None:
    mimic = [float(row["collapse"]) for row in rows if row["class_bucket"] == "MIMIC"]
    inherit = [float(row["collapse"]) for row in rows if row["class_bucket"] == "INHERIT_CONTROL"]
    if not mimic or not inherit:
        return None
    observed = statistics.mean(mimic) - statistics.mean(inherit)
    labels = [row["class_bucket"] for row in rows]
    values = [float(row["collapse"]) for row in rows]
    rng = random.Random(seed)
    extreme = 0
    valid = 0
    for _ in range(n_perm):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        m = [v for v, label in zip(values, shuffled) if label == "MIMIC"]
        h = [v for v, label in zip(values, shuffled) if label == "INHERIT_CONTROL"]
        if not m or not h:
            continue
        valid += 1
        delta = statistics.mean(m) - statistics.mean(h)
        if abs(delta) >= abs(observed):
            extreme += 1
    return {
        "observed_mimic_minus_inherit": rounded(observed),
        "n_permutations": valid,
        "p_value": rounded((extreme + 1) / (valid + 1), 4) if valid else None,
    }


def _solve_linear_system(a: list[list[float]], b: list[float]) -> list[float] | None:
    """Small Gaussian-elimination solver for tiny deterministic report regressions."""
    n = len(b)
    if not a or any(len(row) != n for row in a):
        return None
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            return None
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for row_i in range(n):
            if row_i == col:
                continue
            factor = aug[row_i][col]
            if factor:
                aug[row_i] = [v - factor * aug[col][j] for j, v in enumerate(aug[row_i])]
    return [aug[i][-1] for i in range(n)]


def _ols_beta(xs: list[list[float]], ys: list[float]) -> list[float] | None:
    if not xs or len(xs) != len(ys):
        return None
    width = len(xs[0])
    if any(len(row) != width for row in xs):
        return None
    xtx = [[0.0 for _ in range(width)] for _ in range(width)]
    xty = [0.0 for _ in range(width)]
    for row, y in zip(xs, ys):
        for i in range(width):
            xty[i] += row[i] * y
            for j in range(width):
                xtx[i][j] += row[i] * row[j]
    return _solve_linear_system(xtx, xty)


def _raw_gap_design(rows: list[dict[str, Any]], labels: list[str]) -> tuple[list[list[float]], list[float], list[str], list[str]]:
    families = sorted({str(row["family"]) for row in rows})
    raw_gaps = [float(row["normal_abs_excess"]) for row in rows]
    include_raw_gap = (max(raw_gaps) - min(raw_gaps)) > 1e-12 if raw_gaps else False
    # Drop one family dummy; intercept carries the baseline family.
    dummy_families = families[1:]
    col_names = ["intercept", "is_mimic"]
    if include_raw_gap:
        col_names.append("normal_abs_excess")
    col_names.extend([f"family:{family}" for family in dummy_families])
    xs: list[list[float]] = []
    ys: list[float] = []
    for row, label in zip(rows, labels):
        x = [1.0, 1.0 if label == "MIMIC" else 0.0]
        if include_raw_gap:
            x.append(float(row["normal_abs_excess"]))
        x.extend([1.0 if row["family"] == family else 0.0 for family in dummy_families])
        xs.append(x)
        ys.append(float(row["collapse"]))
    return xs, ys, families, col_names


def raw_gap_adjusted_control(
    rows: list[dict[str, Any]],
    *,
    n_perm: int = 2000,
    seed: int = 42,
) -> dict[str, Any] | None:
    """Estimate whether MIMIC has extra collapse after raw gap and family controls.

    The coefficient is from:

        collapse ~ 1 + is_mimic + normal_abs_excess + family fixed effects

    The permutation shuffles class labels within family, preserving the raw-gap
    distribution and family composition. This is the executable form of the
    protocol's "not explained by raw normal-arm gap size alone" guardrail.
    """
    usable = [
        row for row in rows
        if row["class_bucket"] in {"MIMIC", "INHERIT_CONTROL"}
    ]
    labels = [row["class_bucket"] for row in usable]
    if len(usable) < 8 or "MIMIC" not in labels or "INHERIT_CONTROL" not in labels:
        return None
    xs, ys, families, col_names = _raw_gap_design(usable, labels)
    beta = _ols_beta(xs, ys)
    if beta is None:
        return {
            "n": len(usable),
            "error": "singular_raw_gap_design",
            "note": "Need both MIMIC and INHERIT/control rows after family/raw-gap controls.",
        }
    observed = beta[1]

    rng = random.Random(seed)
    by_family: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(usable):
        by_family[str(row["family"])].append(idx)
    extreme = 0
    valid = 0
    for _ in range(n_perm):
        shuffled = labels[:]
        for idxs in by_family.values():
            local = [shuffled[i] for i in idxs]
            rng.shuffle(local)
            for i, label in zip(idxs, local):
                shuffled[i] = label
        perm_xs, perm_ys, _, _ = _raw_gap_design(usable, shuffled)
        perm_beta = _ols_beta(perm_xs, perm_ys)
        if perm_beta is None:
            continue
        valid += 1
        if abs(perm_beta[1]) >= abs(observed):
            extreme += 1
    raw_gap_coef = None
    if "normal_abs_excess" in col_names:
        raw_gap_coef = beta[col_names.index("normal_abs_excess")]
    return {
        "n": len(usable),
        "families": families,
        "coef_mimic_after_raw_gap_and_family": rounded(observed),
        "coef_raw_normal_abs_excess": rounded(raw_gap_coef),
        "n_permutations": valid,
        "p_value": rounded((extreme + 1) / (valid + 1), 4) if valid else None,
        "design": "collapse ~ is_mimic + normal_abs_excess + family_fixed_effects",
        "columns_used": col_names,
        "label_shuffle": "within_family",
    }


def build_report(db: Path, pilot_id: str) -> dict[str, Any]:
    calls, meta = load_calls(db, pilot_id)
    gaps = frame_gap_rows(calls)
    collapses = collapse_rows(gaps)
    class_summary: dict[str, Any] = {}
    for bucket in sorted({row["class_bucket"] for row in collapses}):
        class_summary[bucket] = summarize_group([row for row in collapses if row["class_bucket"] == bucket])
    family_summary: dict[str, Any] = {}
    for family in sorted({row["family"] for row in collapses}):
        family_rows = [row for row in collapses if row["family"] == family]
        family_summary[family] = summarize_group(family_rows)
        for bucket in sorted({row["class_bucket"] for row in family_rows}):
            family_summary[family][bucket] = summarize_group(
                [row for row in family_rows if row["class_bucket"] == bucket]
            )
    mimic_mean = (
        class_summary.get("MIMIC", {}).get("mean_collapse")
        if class_summary.get("MIMIC")
        else None
    )
    inherit_mean = (
        class_summary.get("INHERIT_CONTROL", {}).get("mean_collapse")
        if class_summary.get("INHERIT_CONTROL")
        else None
    )
    if not calls:
        verdict = "not_run"
    elif not collapses:
        verdict = "insufficient_pairs"
    elif mimic_mean is None or inherit_mean is None:
        verdict = "missing_mimic_or_control"
    elif mimic_mean <= inherit_mean:
        verdict = "kill_or_scope_mimic_collapse"
    else:
        raw_gap_control = raw_gap_adjusted_control(collapses)
        raw_gap_coef = (raw_gap_control or {}).get("coef_mimic_after_raw_gap_and_family")
        raw_gap_p = (raw_gap_control or {}).get("p_value")
        if raw_gap_coef is not None and raw_gap_coef <= 0:
            verdict = "kill_or_scope_raw_gap_explains_collapse"
        elif raw_gap_p is not None and raw_gap_p <= 0.10:
            verdict = "candidate_support_after_raw_gap_control_needs_alignment_review"
        else:
            verdict = "candidate_support_needs_alignment_and_controls"
    raw_gap_control = raw_gap_adjusted_control(collapses)
    return {
        "schema": "gp245-anti-bias-collapse-score-v1",
        "db": str(db),
        "pilot_id": pilot_id,
        "meta": meta,
        "frame_gap_pairs": len(gaps),
        "collapse_pairs": len(collapses),
        "class_summary": class_summary,
        "family_summary": family_summary,
        "class_shuffle_control": class_shuffle_control(collapses),
        "raw_gap_adjusted_control": raw_gap_control,
        "verdict": verdict,
        "promotion_guardrail": (
            "Promote only if MIMIC collapse exceeds INHERIT/control, survives label shuffle, "
            "survives raw-gap adjustment, and tracks the F107 alignment axis. "
            "A positive mean alone is not enough."
        ),
        "rows": collapses[:200],
    }


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "anti_bias_collapse_score.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Anti-Bias-Collapse Score", ""]
    lines.append(f"- Pilot: `{result['pilot_id']}`")
    lines.append(f"- Usable calls: {result['meta']['usable_calls']}")
    lines.append(f"- Frame-gap pairs: {result['frame_gap_pairs']}")
    lines.append(f"- Collapse pairs: {result['collapse_pairs']}")
    lines.append(f"- Verdict: `{result['verdict']}`")
    lines.append("")
    if result["meta"].get("skipped"):
        lines.append("## Skipped Calls")
        lines.append("")
        for key, value in result["meta"]["skipped"].items():
            lines.append(f"- `{key}`: {value}")
        lines.append("")
    lines.append("## Class Summary")
    lines.append("")
    if not result["class_summary"]:
        lines.append("- No scoreable collapse pairs yet.")
    for bucket, row in result["class_summary"].items():
        lines.append(
            f"- `{bucket}`: n={row['n']}, mean_collapse={row['mean_collapse']}, "
            f"ci95={row['collapse_ci95']}, "
            f"corrected_minus_normal={row['paired_corrected_minus_normal']}"
        )
    lines.append("")
    lines.append("## Family Summary")
    lines.append("")
    if not result["family_summary"]:
        lines.append("- No family-level scoreable rows yet.")
    for family, row in result["family_summary"].items():
        lines.append(f"- `{family}`: n={row['n']}, mean_collapse={row['mean_collapse']}")
    lines.append("")
    lines.append("## Label-Shuffle Control")
    lines.append("")
    lines.append(f"`{result['class_shuffle_control']}`")
    lines.append("")
    lines.append("## Raw-Gap Adjusted Control")
    lines.append("")
    lines.append(f"`{result['raw_gap_adjusted_control']}`")
    lines.append("")
    lines.append("## Guardrail")
    lines.append("")
    lines.append(result["promotion_guardrail"])
    lines.append("")
    (out_dir / "anti_bias_collapse_score.md").write_text("\n".join(lines), encoding="utf-8")


def _insert_call(
    cur: sqlite3.Cursor,
    *,
    pilot_id: str,
    contract_id: str,
    call_id: str,
    family: str,
    p_success: float,
    parsed: dict[str, Any],
) -> None:
    contract_raw = {
        key: parsed[key]
        for key in (
            "bias_id",
            "event_id",
            "bias_class_preregistered",
            "frame",
            "g0",
        )
    }
    cur.execute(
        "INSERT OR REPLACE INTO contracts(contract_id, raw_json) VALUES (?, ?)",
        (contract_id, json.dumps(contract_raw, sort_keys=True)),
    )
    cur.execute(
        """
        INSERT INTO pilot_calls(
          call_id, pilot_id, contract_id, agent_id, family, condition, phase,
          p_success, parsed_json, raw_json, schema_ok
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            call_id,
            pilot_id,
            contract_id,
            f"{family}_synthetic",
            family,
            parsed["frame"],
            parsed["prompt_arm"],
            p_success,
            json.dumps(parsed, sort_keys=True),
            json.dumps(parsed, sort_keys=True),
        ),
    )


def run_selftest() -> dict[str, Any]:
    """Exercise the scorer on a synthetic DB where the answer is known."""
    pilot_id = "anti_bias_collapse_v1"
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "anti_bias_selftest.db"
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("CREATE TABLE contracts(contract_id TEXT PRIMARY KEY, raw_json TEXT)")
        cur.execute("CREATE TABLE pilot_runs(pilot_id TEXT PRIMARY KEY)")
        cur.execute(
            """
            CREATE TABLE pilot_calls(
              call_id TEXT PRIMARY KEY,
              pilot_id TEXT,
              contract_id TEXT,
              agent_id TEXT,
              family TEXT,
              condition TEXT,
              phase TEXT,
              p_success REAL,
              parsed_json TEXT,
              raw_json TEXT,
              schema_ok INTEGER
            )
            """
        )
        cur.execute("INSERT INTO pilot_runs(pilot_id) VALUES (?)", (pilot_id,))
        families = ["claude", "gemini"]
        specs = [
            ("F_status_quo", "MIMIC", 0.30, 0.05),
            ("K_availability_control", "INHERIT_CONTROL", 0.30, 0.25),
        ]
        for family in families:
            for bias_id, bias_class, normal_gap, corrected_gap in specs:
                for i in range(1, 9):
                    event_id = f"{bias_id}_{i:02d}"
                    for arm, gap in (("normal", normal_gap), ("anti_bias_correction", corrected_gap)):
                        for frame, p_success in (("A", 0.5 + gap / 2), ("B", 0.5 - gap / 2)):
                            parsed = {
                                "bias_id": bias_id,
                                "event_id": event_id,
                                "bias_class_preregistered": bias_class,
                                "frame": frame,
                                "prompt_arm": arm,
                                "g0": 0.0,
                            }
                            contract_id = f"selftest_{bias_id}_{event_id}_{frame}"
                            call_id = f"{family}_{bias_id}_{event_id}_{arm}_{frame}"
                            _insert_call(
                                cur,
                                pilot_id=pilot_id,
                                contract_id=contract_id,
                                call_id=call_id,
                                family=family,
                                p_success=p_success,
                                parsed=parsed,
                            )
        con.commit()
        con.close()
        result = build_report(db, pilot_id)
    checks = {
        "usable_calls": result["meta"]["usable_calls"] == 128,
        "collapse_pairs": result["collapse_pairs"] == 32,
        "mimic_gt_inherit": (
            result["class_summary"]["MIMIC"]["mean_collapse"]
            > result["class_summary"]["INHERIT_CONTROL"]["mean_collapse"]
        ),
        "raw_gap_adjusted_positive": (
            (result["raw_gap_adjusted_control"] or {}).get("coef_mimic_after_raw_gap_and_family") or 0
        ) > 0,
        "verdict_supports_candidate": result["verdict"].startswith("candidate_support"),
    }
    return {
        "schema": "gp245-anti-bias-collapse-score-selftest-v1",
        "passed": all(checks.values()),
        "checks": checks,
        "score_summary": {
            "verdict": result["verdict"],
            "usable_calls": result["meta"]["usable_calls"],
            "collapse_pairs": result["collapse_pairs"],
            "class_summary": result["class_summary"],
            "raw_gap_adjusted_control": result["raw_gap_adjusted_control"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pilot-id", default=DEFAULT_PILOT_ID)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--selftest", action="store_true", help="Run synthetic scorer plumbing test and exit.")
    args = parser.parse_args()
    if args.selftest:
        result = run_selftest()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["passed"] else 1
    result = build_report(args.db, args.pilot_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(result, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
