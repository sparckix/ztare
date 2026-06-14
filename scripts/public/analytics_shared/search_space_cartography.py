#!/usr/bin/env python3
"""GP-218 R1 — Search-Space Cartography.

A reusable analytic for any project that runs a parameter / generator sweep:
given a JSON of per-generator (loss, signal-axis) results, report the
phase-diagram structure of the resulting plane:

  - Modes on the signal axis (clusters detected via histogram + valley)
  - Empty gaps on the signal axis (regions of size >= --gap-min with no points)
  - Basin counts on the loss-vs-signal plane (connected components after binning)
  - Pareto front (best loss per signal bin)

Origin: GP-218 RH desk audit (2026-05-05) surfaced "Search-Space Cartography"
as a reusable apparatus move that the GP-125 RH operator-search project
invented and that neither v5 nor GP-219 names. The bimodal CV gap finding
(F-GP125-BIMODAL-GAP) was its first instance: 28 generators sweep, CV
empty in (0.37, 0.54), splitting operator space into polynomial-dominated
vs arithmetic-dominated regimes with no interpolant. This script codifies
the move so any sweep JSON anywhere can be cartographed automatically —
no project needs to invent it again.

Usage:
    python scripts/public/analytics_shared/search_space_cartography.py \\
        --sweep projects/riemann_operator_search/workspace/riemann_a10_dense_20260423.json \\
        --loss-key loss \\
        --signal-key spacing_var \\
        --report-out projects/riemann_operator_search/workspace/analytics_cartography/<run>_<axis>.md

    # Auto-detect with sensible defaults (scans common keys):
    python scripts/public/analytics_shared/search_space_cartography.py --sweep <path>

Sweep JSON schemas accepted:
  - {"all_results": [...]}             (RH operator search)
  - {"results": [...]}                 (generic)
  - {"per_generator": {name: {...}}}   (dict-style)
  - flat list                          (raw sweep records)

Each record must have the loss key and signal key; other fields ignored.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
# Common signal-axis keys to auto-try when --signal-key is omitted
COMMON_SIGNAL_KEYS = (
    "spacing_var", "spacing_cv", "cv", "sff_l1",
    "score", "sigma_eff", "diversity",
)
# Common loss keys
COMMON_LOSS_KEYS = ("loss", "mse", "objective", "error", "score_loss")


@dataclass
class CartographyResult:
    n_records: int
    loss_key: str
    signal_key: str
    loss_min: float
    loss_max: float
    signal_min: float
    signal_max: float
    modes: list[dict] = field(default_factory=list)            # [{center, count, loss_at_center}]
    empty_gaps: list[dict] = field(default_factory=list)       # [{lo, hi, width}]
    pareto_front: list[dict] = field(default_factory=list)     # [{signal_bin, best_loss, generator}]
    basin_count_2d: int = 0


def load_records(path: Path) -> list[dict]:
    """Load sweep JSON in any of the accepted schemas; return flat list of records."""
    if not path.exists():
        print(f"ERROR: sweep file not found: {path}", file=sys.stderr)
        sys.exit(2)
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("all_results", "results", "records", "sweep_results"):
            if key in data and isinstance(data[key], list):
                return [r for r in data[key] if isinstance(r, dict)]
        for key in ("per_generator", "by_generator", "generators"):
            if key in data and isinstance(data[key], dict):
                out = []
                for name, rec in data[key].items():
                    if isinstance(rec, dict):
                        rec = dict(rec)
                        rec.setdefault("generator", name)
                        out.append(rec)
                return out
    print(f"ERROR: could not find sweep records in {path}; expected one of: all_results, results, per_generator", file=sys.stderr)
    sys.exit(2)


def auto_detect_keys(records: list[dict], loss_key: str | None, signal_key: str | None) -> tuple[str, str]:
    """If keys not provided, scan common candidates against record schema."""
    if not records:
        print("ERROR: no records loaded", file=sys.stderr)
        sys.exit(2)
    sample = records[0]
    if loss_key is None:
        for k in COMMON_LOSS_KEYS:
            if k in sample and isinstance(sample[k], (int, float)):
                loss_key = k
                break
        if loss_key is None:
            print(f"ERROR: could not auto-detect loss key. Available numeric keys: {[k for k, v in sample.items() if isinstance(v, (int, float))]}", file=sys.stderr)
            sys.exit(2)
    if signal_key is None:
        for k in COMMON_SIGNAL_KEYS:
            if k in sample and isinstance(sample[k], (int, float)):
                signal_key = k
                break
        if signal_key is None:
            print(f"ERROR: could not auto-detect signal key. Available numeric keys: {[k for k, v in sample.items() if isinstance(v, (int, float))]}", file=sys.stderr)
            sys.exit(2)
    return loss_key, signal_key


def detect_modes_and_gaps(values: list[float], n_bins: int, gap_min: float) -> tuple[list[dict], list[dict]]:
    """Detect modes (local maxima in histogram) and empty gaps on a 1D signal axis.

    Modes: for each bin with count > max(neighbors) AND count > floor (>=1), record
    a mode. Greedy local-max identification — sufficient for sweep N up to a few
    hundred; for larger N use a kernel-density-based method.

    Gaps: contiguous runs of bins with zero points whose total width >= gap_min.
    """
    if not values:
        return [], []
    lo, hi = min(values), max(values)
    if hi <= lo:
        return [{"center": lo, "count": len(values), "width": 0.0}], []
    bin_w = (hi - lo) / n_bins
    counts = [0] * n_bins
    bin_assignments: list[list[int]] = [[] for _ in range(n_bins)]
    for i, v in enumerate(values):
        idx = min(int((v - lo) / bin_w), n_bins - 1)
        counts[idx] += 1
        bin_assignments[idx].append(i)

    # Modes: bins where count strictly greater than both neighbors (or boundary), count >= 2
    modes = []
    for i, c in enumerate(counts):
        if c < 2:
            continue
        left = counts[i - 1] if i > 0 else -1
        right = counts[i + 1] if i + 1 < n_bins else -1
        if c >= left and c >= right and (c > left or c > right):
            center = lo + (i + 0.5) * bin_w
            modes.append({"center": round(center, 6), "count": c, "bin_index": i})

    # Empty gaps: contiguous zero-count runs with total width >= gap_min
    gaps = []
    i = 0
    while i < n_bins:
        if counts[i] == 0:
            j = i
            while j < n_bins and counts[j] == 0:
                j += 1
            gap_lo = lo + i * bin_w
            gap_hi = lo + j * bin_w
            width = gap_hi - gap_lo
            if width >= gap_min:
                gaps.append({"lo": round(gap_lo, 6), "hi": round(gap_hi, 6), "width": round(width, 6), "bins": j - i})
            i = j
        else:
            i += 1

    return modes, gaps


def compute_pareto_front(records: list[dict], loss_key: str, signal_key: str, n_bins: int = 20) -> list[dict]:
    """For each signal bin, find the record with lowest loss. Returns the Pareto curve."""
    sigs = [r[signal_key] for r in records if signal_key in r and loss_key in r]
    if not sigs:
        return []
    lo, hi = min(sigs), max(sigs)
    if hi <= lo:
        return []
    bin_w = (hi - lo) / n_bins
    best_per_bin: dict[int, dict] = {}
    for r in records:
        if signal_key not in r or loss_key not in r:
            continue
        idx = min(int((r[signal_key] - lo) / bin_w), n_bins - 1)
        if idx not in best_per_bin or r[loss_key] < best_per_bin[idx][loss_key]:
            best_per_bin[idx] = r

    pareto = []
    for idx in sorted(best_per_bin):
        r = best_per_bin[idx]
        bin_center = lo + (idx + 0.5) * bin_w
        pareto.append({
            "signal_bin_center": round(bin_center, 6),
            "best_loss": round(float(r[loss_key]), 6),
            "generator": r.get("generator") or r.get("name") or f"<bin_{idx}>",
        })
    return pareto


def estimate_basin_count_2d(records: list[dict], loss_key: str, signal_key: str, grid: int = 12) -> int:
    """Connected-component count on a 2D loss×signal binning. Approximate basin count.

    Greedy 4-connected flood fill on a grid×grid grid populated by record
    presence. This is a rough cartographic descriptor, not a rigorous mode count.
    """
    sigs = [r[signal_key] for r in records if signal_key in r and loss_key in r]
    losses = [r[loss_key] for r in records if signal_key in r and loss_key in r]
    if not sigs or not losses:
        return 0
    s_lo, s_hi = min(sigs), max(sigs)
    l_lo, l_hi = min(losses), max(losses)
    if s_hi <= s_lo or l_hi <= l_lo:
        return 0
    s_w = (s_hi - s_lo) / grid
    l_w = (l_hi - l_lo) / grid
    cells: set[tuple[int, int]] = set()
    for r in records:
        if signal_key not in r or loss_key not in r:
            continue
        si = min(int((r[signal_key] - s_lo) / s_w), grid - 1)
        li = min(int((r[loss_key] - l_lo) / l_w), grid - 1)
        cells.add((si, li))

    visited: set[tuple[int, int]] = set()
    components = 0
    for start in cells:
        if start in visited:
            continue
        components += 1
        stack = [start]
        while stack:
            c = stack.pop()
            if c in visited:
                continue
            visited.add(c)
            si, li = c
            for nbr in ((si + 1, li), (si - 1, li), (si, li + 1), (si, li - 1)):
                if nbr in cells and nbr not in visited:
                    stack.append(nbr)
    return components


def render_report(result: CartographyResult, sweep_path: Path) -> str:
    lines = []
    lines.append("# Search-Space Cartography Report\n")
    lines.append(f"_Generated by `scripts/public/analytics_shared/search_space_cartography.py` — GP-218 R1 reusable apparatus._\n")
    lines.append(f"**Source sweep:** `{sweep_path}`")
    lines.append(f"**Axes:** loss = `{result.loss_key}` | signal = `{result.signal_key}`")
    lines.append(f"**N records:** {result.n_records}")
    lines.append(f"**Loss range:** [{result.loss_min:.4f}, {result.loss_max:.4f}]")
    lines.append(f"**Signal range:** [{result.signal_min:.4f}, {result.signal_max:.4f}]\n")

    # §1 Modes
    lines.append("## Modes on signal axis\n")
    if result.modes:
        lines.append("| center | count | bin |")
        lines.append("|---|---|---|")
        for m in result.modes:
            lines.append(f"| {m['center']:.4f} | {m['count']} | {m.get('bin_index', '-')} |")
    else:
        lines.append("(no modes detected — distribution may be too uniform or N too small)")
    lines.append("")

    # §2 Empty gaps — the decision-critical cartography output
    lines.append("## Empty gaps on signal axis\n")
    lines.append("Empty gaps are the cartographic signal: regions where the parameter sweep produced ZERO points despite having neighbors on both sides. A wide gap is structural evidence that the search space has multiple regimes with no interpolant.\n")
    if result.empty_gaps:
        lines.append("| gap_lo | gap_hi | width | bins |")
        lines.append("|---|---|---|---|")
        for g in result.empty_gaps:
            lines.append(f"| {g['lo']:.4f} | {g['hi']:.4f} | {g['width']:.4f} | {g['bins']} |")
        lines.append("")
        lines.append("**Interpretation:** if any gap width is non-trivial relative to the signal range, the search space is structurally multi-modal. This is the move that surfaced the GP-125-BIMODAL-GAP finding in the RH operator-search project.")
    else:
        lines.append("(no empty gaps above threshold detected — distribution may be unimodal or sweep may be too sparse)")
    lines.append("")

    # §3 Basin count
    lines.append("## 2D basin count (loss × signal)\n")
    lines.append(f"Connected components on a 12×12 grid: **{result.basin_count_2d}**.")
    lines.append("More than 1 = the (loss, signal) plane has structurally separated basins — different generator families occupy disconnected regions. Rough cartographic descriptor; not a rigorous mode count.\n")

    # §4 Pareto front
    lines.append("## Pareto front (best loss per signal bin)\n")
    if result.pareto_front:
        lines.append("| signal_bin_center | best_loss | generator |")
        lines.append("|---|---|---|")
        for p in result.pareto_front:
            lines.append(f"| {p['signal_bin_center']:.4f} | {p['best_loss']:.6f} | `{p['generator']}` |")
        lines.append("")
        lines.append("**Reading the Pareto front:** if loss decreases as signal moves toward the target, the sweep has a generator family that approaches the target. If loss is flat or U-shaped, no generator family approaches the target across the explored signal range — suggesting a structural ceiling.")
    else:
        lines.append("(no Pareto front computable — fewer than 2 distinct signal-bin records)")
    lines.append("")

    # §5 Honest interpretation hint
    lines.append("## How to read this report\n")
    lines.append("- **Empty gaps** are the cartographic finding: a wide gap = phase boundary between regimes.")
    lines.append("- **Basin count > 1** = disconnected regions of the (loss, signal) plane = multimodality at the 2D level.")
    lines.append("- **Pareto front shape** = whether any direction in the search space approaches the target.")
    lines.append("- A unimodal sweep with no gaps and basin_count == 1 is a 'smooth ceiling' — gradient descent / parameter optimization is the bottleneck.")
    lines.append("- A bimodal sweep with a wide gap and basin_count >= 2 is a 'structural ceiling' — grammar / ansatz class is the bottleneck.")
    lines.append("")
    lines.append("Origin: this script codifies the move that produced F-GP125-BIMODAL-GAP (RH operator search, 2026-04-23). Reusable across any sweep — RH, OEIS dark sequences, NS state-pricing sweeps, future symbolic regression. See INS-083 for the audit-surfaced rationale.")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Search-Space Cartography (GP-218 R1)")
    parser.add_argument("--sweep", type=Path, required=True, help="Sweep JSON path")
    parser.add_argument("--loss-key", default=None, help="JSON field for loss/objective. Auto-detected if omitted.")
    parser.add_argument("--signal-key", default=None, help="JSON field for signal axis (e.g., spacing_var). Auto-detected if omitted.")
    parser.add_argument("--n-bins", type=int, default=20, help="Histogram bins for mode/gap detection (default: 20)")
    parser.add_argument("--gap-min", type=float, default=None,
                        help="Minimum gap width (in signal units) to report. Default: 8% of signal range.")
    parser.add_argument("--report-out", type=Path, default=None, help="Markdown report path")
    parser.add_argument("--json-out", type=Path, default=None, help="Structured JSON path")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    records = load_records(args.sweep)
    loss_key, signal_key = auto_detect_keys(records, args.loss_key, args.signal_key)

    losses = [r[loss_key] for r in records if loss_key in r and isinstance(r[loss_key], (int, float))]
    signals = [r[signal_key] for r in records if signal_key in r and isinstance(r[signal_key], (int, float))]
    if not losses or not signals:
        print(f"ERROR: no records with both '{loss_key}' and '{signal_key}'", file=sys.stderr)
        return 2

    gap_min = args.gap_min if args.gap_min is not None else 0.08 * (max(signals) - min(signals))
    modes, gaps = detect_modes_and_gaps(signals, args.n_bins, gap_min)
    pareto = compute_pareto_front(records, loss_key, signal_key, n_bins=args.n_bins)
    basin = estimate_basin_count_2d(records, loss_key, signal_key, grid=12)

    result = CartographyResult(
        n_records=len(records),
        loss_key=loss_key,
        signal_key=signal_key,
        loss_min=min(losses),
        loss_max=max(losses),
        signal_min=min(signals),
        signal_max=max(signals),
        modes=modes,
        empty_gaps=gaps,
        pareto_front=pareto,
        basin_count_2d=basin,
    )

    md = render_report(result, args.sweep)
    if args.report_out:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(md)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(asdict(result), indent=2, default=str))

    if not args.quiet:
        print(md)
        if args.report_out:
            print(f"Report: {args.report_out}")
        if args.json_out:
            print(f"JSON:   {args.json_out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
