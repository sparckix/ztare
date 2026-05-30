#!/usr/bin/env python3
"""GP-134 judge-drift audit: invert-and-compress the judge discipline.

Reads a project's debate logs and latest_eval_results, and flags three
drift patterns that undermine Newton-mode forward-observable tunneling:

  1. Anchoring-to-weakest-point drift — score/rationale disagreement
     (e.g., rationale says "achieves all requirements" but score is 0).
  2. Rubric-mode attention decay — Generative Yield score trends down
     over iters even as other dimensions stay flat or improve.
  3. Tautology-penalty overuse — rationale cites "tautology" /
     "trivial restatement" on proposals that name disjoint predictions.

Decision thresholds (configurable via CLI):
  * GY variance > 40% of full range across K constant-quality proposals
    -> judge unreliable, swap judge-model.
  * Gate harness score >= 90 but debate score < 50 for > 3 iters
    -> judge systematically miscalibrated, redistribute rubric weights.

Exit code 0 if no pattern triggered, 1 if at least one fires. Intended
to be run after a loop finishes or between manual re-runs.

Usage:
  python scripts/public/audits/audit_judge_drift.py --project oeis_a000959_newton
  python scripts/public/audits/audit_judge_drift.py --project gp090_01 --verbose
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
def load_debate_logs(project_dir: Path) -> list[dict]:
    """Return debate log bodies sorted by timestamp ascending."""
    logs = []
    for p in sorted(project_dir.glob("debate_log_iter_*.md")):
        m = re.search(r"debate_log_iter_(\d+)\.md$", p.name)
        if not m:
            continue
        logs.append({"ts": int(m.group(1)), "path": p, "body": p.read_text()})
    return logs


def extract_score(body: str) -> int | None:
    m = re.search(r"\*\*Score:\*\*\s*(\d+)", body)
    if m:
        return int(m.group(1))
    m = re.search(r'"score"\s*:\s*(\d+)', body)
    if m:
        return int(m.group(1))
    return None


def extract_rationale(body: str) -> str:
    m = re.search(r"\*\*Rationale:\*\*\s*(.+?)(?:\n\n|\*\*)", body, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def extract_gy_score(body: str) -> int | None:
    """Try to locate a Generative Yield per-dimension score in the log."""
    for pat in [
        r"Generative Yield[^:]*:\s*(\d+)\s*/\s*\d+",
        r'"Generative Yield[^"]*"\s*:\s*(\d+)',
        r"generative_yield[^:]*:\s*(\d+)",
    ]:
        m = re.search(pat, body, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def load_gate_harness_score(project_dir: Path) -> int | None:
    p = project_dir / "latest_eval_results.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        for key in ("gate_harness_score", "harness_score", "gate_score"):
            if key in data:
                return int(data[key])
    except Exception:
        return None
    return None


POSITIVE_RATIONALE_MARKERS = [
    "achieves all",
    "best-in-class",
    "all rubric requirements",
    "fully satisfies",
    "exceeds",
    "strongly predicts",
    "clean recovery",
    "correct topology",
    "passes all gates",
]

TAUTOLOGY_MARKERS = [
    "tautology",
    "trivial restatement",
    "trivially",
    "restates the fitting target",
    "no genuine secondary",
    "merely restates",
]


def pattern_1_anchoring(logs: list[dict]) -> list[dict]:
    """Score low but rationale is positive — classic anchor-to-weakness."""
    hits = []
    for log in logs:
        score = extract_score(log["body"])
        rationale = extract_rationale(log["body"]).lower()
        if score is None or score > 25:
            continue
        matched = [m for m in POSITIVE_RATIONALE_MARKERS if m in rationale]
        if matched:
            hits.append({
                "iter_ts": log["ts"],
                "score": score,
                "positive_markers": matched,
                "path": str(log["path"].relative_to(REPO)),
            })
    return hits


def pattern_2_attention_decay(logs: list[dict]) -> dict:
    """GY trends down across iters — judge slipping back to Kepler."""
    trend = []
    for log in logs:
        gy = extract_gy_score(log["body"])
        if gy is not None:
            trend.append({"ts": log["ts"], "gy": gy})
    if len(trend) < 4:
        return {"triggered": False, "reason": "insufficient iters with GY score", "trend": trend}
    first_half = trend[: len(trend) // 2]
    second_half = trend[len(trend) // 2 :]
    mean_first = sum(x["gy"] for x in first_half) / len(first_half)
    mean_second = sum(x["gy"] for x in second_half) / len(second_half)
    decayed = mean_first - mean_second > 5.0
    return {
        "triggered": bool(decayed),
        "mean_first_half": round(mean_first, 2),
        "mean_second_half": round(mean_second, 2),
        "delta": round(mean_first - mean_second, 2),
        "trend": trend,
    }


def pattern_3_tautology_overuse(logs: list[dict]) -> list[dict]:
    """Rationale cites tautology but proposal had a distinct observable.

    Heuristic: tautology marker present AND rationale length > 300 chars
    (suggests a full judgment was written, not a quick dismissal on an
    actual trivial proposal). Flag for manual review rather than auto-fail.
    """
    hits = []
    for log in logs:
        rationale = extract_rationale(log["body"]).lower()
        if not rationale or len(rationale) < 300:
            continue
        matched = [m for m in TAUTOLOGY_MARKERS if m in rationale]
        if matched:
            hits.append({
                "iter_ts": log["ts"],
                "markers": matched,
                "rationale_excerpt": rationale[:400],
                "path": str(log["path"].relative_to(REPO)),
            })
    return hits


def check_gate_vs_debate(logs: list[dict], gate_score: int | None, threshold_iters: int = 3) -> dict:
    if gate_score is None or gate_score < 90:
        return {"triggered": False, "reason": f"gate_harness={gate_score} below threshold 90"}
    debates_below_50 = sum(1 for log in logs if (extract_score(log["body"]) or 0) < 50)
    return {
        "triggered": bool(debates_below_50 > threshold_iters),
        "gate_harness_score": gate_score,
        "debate_iters_below_50": debates_below_50,
        "threshold_iters": threshold_iters,
    }


def gy_variance_check(logs: list[dict], range_pct_threshold: float = 0.40) -> dict:
    gys = [extract_gy_score(l["body"]) for l in logs]
    gys = [g for g in gys if g is not None]
    if len(gys) < 5:
        return {"triggered": False, "reason": "fewer than 5 iters with GY score"}
    g_max, g_min = max(gys), min(gys)
    full_range = 25  # canonical max weight for Generative Yield
    variance_pct = (g_max - g_min) / full_range
    return {
        "triggered": variance_pct > range_pct_threshold,
        "gy_min": g_min,
        "gy_max": g_max,
        "variance_pct": round(variance_pct, 3),
        "threshold_pct": range_pct_threshold,
        "recommendation": (
            "swap JUDGE_MODEL (claude / gemini-pro) rather than mutator"
            if variance_pct > range_pct_threshold else "judge appears stable on GY"
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="project slug under projects/")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    project_dir = REPO / "projects" / args.project
    if not project_dir.exists():
        print(f"project dir not found: {project_dir}", file=sys.stderr)
        sys.exit(2)

    logs = load_debate_logs(project_dir)
    if not logs:
        print(f"no debate logs in {project_dir}")
        sys.exit(0)

    gate_score = load_gate_harness_score(project_dir)

    report = {
        "project": args.project,
        "n_iters": len(logs),
        "gate_harness_score": gate_score,
        "pattern_1_anchoring": pattern_1_anchoring(logs),
        "pattern_2_attention_decay": pattern_2_attention_decay(logs),
        "pattern_3_tautology_overuse": pattern_3_tautology_overuse(logs),
        "gate_vs_debate": check_gate_vs_debate(logs, gate_score),
        "gy_variance": gy_variance_check(logs),
    }

    triggered = []
    if report["pattern_1_anchoring"]:
        triggered.append(f"pattern-1 anchoring-drift ({len(report['pattern_1_anchoring'])} hits)")
    if report["pattern_2_attention_decay"].get("triggered"):
        d = report["pattern_2_attention_decay"]
        triggered.append(f"pattern-2 attention-decay (GY dropped {d['delta']} from {d['mean_first_half']} to {d['mean_second_half']})")
    if report["pattern_3_tautology_overuse"]:
        triggered.append(f"pattern-3 tautology-overuse ({len(report['pattern_3_tautology_overuse'])} hits)")
    if report["gate_vs_debate"].get("triggered"):
        d = report["gate_vs_debate"]
        triggered.append(f"gate-vs-debate gap (gate={d['gate_harness_score']} but {d['debate_iters_below_50']} debate iters < 50)")
    if report["gy_variance"].get("triggered"):
        d = report["gy_variance"]
        triggered.append(f"GY variance = {d['variance_pct']*100:.1f}% of full range (threshold {d['threshold_pct']*100:.0f}%) - {d['recommendation']}")

    print(f"=== Judge-drift audit: {args.project} ({len(logs)} iters) ===")
    print(f"Gate harness score: {gate_score}")
    if triggered:
        print("\nDRIFT PATTERNS TRIGGERED:")
        for t in triggered:
            print(f"  * {t}")
    else:
        print("\nNo drift patterns triggered. Judge appears stable.")

    if args.verbose or triggered:
        print("\n--- full report ---")
        print(json.dumps(report, indent=2, default=str))

    sys.exit(1 if triggered else 0)


if __name__ == "__main__":
    main()
