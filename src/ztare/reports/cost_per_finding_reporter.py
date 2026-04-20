"""GP-040 Slice 2b — cost-per-finding rollup.

Reads usage_ledger/*.jsonl and emits a per-finding cost report.
Each JSONL file corresponds to one seam debate. The reporter aggregates:
  - total cost per seam debate
  - cycles to converge (or cycles before budget stop)
  - cost per cycle (mean, p50, p90)
  - convergence status (converged / stopped / in-progress)
  - cumulative cost across all debates

Usage:
  python -m src.ztare.validator.cost_per_finding_reporter
  python -m src.ztare.validator.cost_per_finding_reporter --output report.json
  python -m src.ztare.validator.cost_per_finding_reporter --ledger-dir path/to/usage_ledger
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from src.ztare.common.paths import REPO_ROOT

DEFAULT_LEDGER_DIR = (
    REPO_ROOT / "ztare_workspace" / "supervisor" / "findings_debate" / "usage_ledger"
)

SEAMS_DIR = REPO_ROOT / "research_areas" / "private" / "seams"
PUBLIC_SEAMS_DIR = REPO_ROOT / "research_areas" / "seams"

_SENTINEL_RE = re.compile(r"SENTINEL_DECISION:\s*(raise|hold)\b", re.IGNORECASE)


def _seam_name_from_ledger(ledger_path: Path) -> str:
    return ledger_path.stem


def _detect_convergence_from_seam(seam_name: str) -> str | None:
    for parent in (SEAMS_DIR, PUBLIC_SEAMS_DIR):
        seam_path = parent / f"{seam_name}.md"
        if not seam_path.exists():
            continue
        text = seam_path.read_text(encoding="utf-8")
        decisions = _SENTINEL_RE.findall(text)
        if len(decisions) >= 2 and decisions[-1].lower() == "raise" and decisions[-2].lower() == "raise":
            return "converged"
        if decisions:
            return "pending"
        return "no_debate"
    return None


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    sorted_vals = sorted(values)
    rank = (p / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


def analyse_ledger(ledger_path: Path) -> dict[str, Any]:
    records = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))

    seam_name = _seam_name_from_ledger(ledger_path)
    if not records:
        return {
            "seam": seam_name,
            "cycles": 0,
            "total_cost_usd": 0.0,
            "convergence": _detect_convergence_from_seam(seam_name),
        }

    costs = [r.get("estimated_cost_usd", 0.0) for r in records]
    total_cost = sum(costs)
    input_tokens = sum(r.get("input_tokens", 0) for r in records)
    output_tokens = sum(r.get("output_tokens", 0) for r in records)

    models_used = sorted(set(r.get("model_name", "unknown") for r in records))
    agents_used = sorted(set(r.get("agent", "unknown") for r in records))

    return {
        "seam": seam_name,
        "cycles": len(records),
        "total_cost_usd": round(total_cost, 6),
        "mean_cost_per_cycle": round(total_cost / len(records), 6),
        "p50_cost_per_cycle": round(_percentile(costs, 50) or 0, 6),
        "p90_cost_per_cycle": round(_percentile(costs, 90) or 0, 6),
        "total_input_tokens": input_tokens,
        "total_output_tokens": output_tokens,
        "models": models_used,
        "agents": agents_used,
        "convergence": _detect_convergence_from_seam(seam_name),
    }


def build_rollup(ledger_dir: Path) -> dict[str, Any]:
    ledger_files = sorted(ledger_dir.glob("*.jsonl"))
    findings = [analyse_ledger(f) for f in ledger_files]

    total_cost = sum(f["total_cost_usd"] for f in findings)
    total_cycles = sum(f["cycles"] for f in findings)
    converged = sum(1 for f in findings if f.get("convergence") == "converged")

    per_finding_costs = [f["total_cost_usd"] for f in findings if f["cycles"] > 0]

    return {
        "summary": {
            "finding_count": len(findings),
            "converged_count": converged,
            "total_cycles": total_cycles,
            "total_cost_usd": round(total_cost, 6),
            "mean_cost_per_finding": round(total_cost / len(findings), 6) if findings else 0,
            "p50_cost_per_finding": round(_percentile(per_finding_costs, 50) or 0, 6),
            "p90_cost_per_finding": round(_percentile(per_finding_costs, 90) or 0, 6),
            "mean_cycles_per_finding": round(total_cycles / len(findings), 1) if findings else 0,
        },
        "findings": findings,
    }


def print_report(rollup: dict[str, Any]) -> None:
    s = rollup["summary"]
    print("=" * 60)
    print("GP-040 Slice 2b — Cost-Per-Finding Rollup")
    print("=" * 60)
    print(f"  Findings debated     : {s['finding_count']}")
    print(f"  Converged            : {s['converged_count']}")
    print(f"  Total debate cycles  : {s['total_cycles']}")
    print(f"  Total debate cost    : ${s['total_cost_usd']:.4f}")
    print(f"  Mean cost/finding    : ${s['mean_cost_per_finding']:.4f}")
    print(f"  p50 cost/finding     : ${s['p50_cost_per_finding']:.4f}")
    print(f"  p90 cost/finding     : ${s['p90_cost_per_finding']:.4f}")
    print(f"  Mean cycles/finding  : {s['mean_cycles_per_finding']}")
    print()

    for f in rollup["findings"]:
        status = f.get("convergence", "unknown") or "unknown"
        print(f"  {f['seam']}")
        print(f"    cycles={f['cycles']}  cost=${f['total_cost_usd']:.4f}  status={status}")
        if f["cycles"] > 0:
            print(f"    mean/cycle=${f['mean_cost_per_cycle']:.4f}  "
                  f"p50/cycle=${f['p50_cost_per_cycle']:.4f}  "
                  f"p90/cycle=${f['p90_cost_per_cycle']:.4f}")
            print(f"    tokens: {f['total_input_tokens']:,} in / {f['total_output_tokens']:,} out")
            print(f"    models: {', '.join(f['models'])}  agents: {', '.join(f['agents'])}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="GP-040 Slice 2b cost-per-finding rollup")
    parser.add_argument("--ledger-dir", type=Path, default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--output", type=Path, default=None, help="Write JSON report to file")
    args = parser.parse_args()

    rollup = build_rollup(args.ledger_dir)
    print_report(rollup)

    if args.output:
        args.output.write_text(json.dumps(rollup, indent=2) + "\n")
        print(f"JSON report written to {args.output}")


if __name__ == "__main__":
    main()
