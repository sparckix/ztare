#!/usr/bin/env python3
"""analyze_ablation_results.py — report on `route_c_archetype_runner.py` output.

Reads a route_c_archetype_runner JSON trace and produces:
  * per-mode closure rate (A vs B vs C vs D vs Full)
  * which rows close in which mode
  * ARCH-001..008 archetype prediction distribution
  * L3 anti-pattern flag distribution
  * closing-tactic frequency
  * cross-mode fingerprint check (rows that close in BOTH A and D — same tactic?
    paraphrase tactic? → flag for Meta-Darwin)

Usage:
  analyze_ablation_results.py --in <ablation.json> [--out <report.md>]
"""
from __future__ import annotations
import argparse, json, sys
from collections import Counter
from pathlib import Path


def fmt_pct(n: int, d: int) -> str:
    if d == 0:
        return "0/0 (—)"
    return f"{n}/{d} ({100*n//d}%)"


def analyze(trace: dict) -> str:
    rows = trace.get("rows", [])
    agg = trace.get("aggregate", {})
    n = len(rows)
    if n == 0:
        return "# Ablation report\n\nNo rows in trace.\n"

    modes = agg.get("modes", ["A", "B", "C", "D", "Full"])

    # Per-mode closure rate
    closures = {m: 0 for m in modes}
    for r in rows:
        hc = r.get("honest_count", {})
        for m in modes:
            if hc.get(f"{m}_closed"):
                closures[m] += 1

    # Per-row mode-closure breakdown
    row_table = []
    for r in rows:
        rid = r["row_id"]
        hc = r.get("honest_count", {})
        closing = {}
        # Mode A closing tactic
        if hc.get("A_closed"):
            closing["A"] = r["results"].get("A_basic_tactics_only", {}).get("closing_tactic", "?")
        # Mode D closing tactic
        if hc.get("D_closed"):
            d = r["results"].get("D_archetype_only", {})
            closing["D"] = f"{d.get('closing_tactic', '?')} (arch={d.get('L4_archetype_predicted_reviewer_spec','?')})"
        row_table.append({
            "row_id": rid,
            "A": "✓ " + closing.get("A", "") if hc.get("A_closed") else "✗",
            "B": "✓" if hc.get("B_closed") else "✗",
            "C": "✓" if hc.get("C_closed") else "✗",
            "D": "✓ " + closing.get("D", "") if hc.get("D_closed") else "✗",
            "Full": "✓" if hc.get("Full_closed") else "✗",
        })

    # ARCH archetype distribution from Mode D
    arch_dist = Counter()
    for r in rows:
        d = r.get("results", {}).get("D_archetype_only", {})
        a = d.get("L4_archetype_predicted_reviewer_spec")
        if a:
            arch_dist[a] += 1

    # L3 anti-pattern flag distribution (from Mode D)
    flag_dist = Counter()
    for r in rows:
        d = r.get("results", {}).get("D_archetype_only", {})
        for f in d.get("L3_anti_pattern_flags", []):
            flag_dist[f] += 1

    # Closing-tactic frequency (Mode A across all closed rows)
    closing_tactic_freq = Counter()
    for r in rows:
        if r.get("honest_count", {}).get("A_closed"):
            t = r["results"].get("A_basic_tactics_only", {}).get("closing_tactic")
            if t:
                closing_tactic_freq[t] += 1

    # Cross-mode fingerprint check: rows closed in BOTH A and D
    cross_closures = []
    for r in rows:
        hc = r.get("honest_count", {})
        if hc.get("A_closed") and hc.get("D_closed"):
            a_tac = r["results"].get("A_basic_tactics_only", {}).get("closing_tactic")
            d_tac = r["results"].get("D_archetype_only", {}).get("closing_tactic")
            same = "SAME" if a_tac == d_tac else "DIFF"
            cross_closures.append({
                "row_id": r["row_id"],
                "A_tactic": a_tac,
                "D_tactic": d_tac,
                "same": same,
            })

    # Build report
    out = ["# Ablation Report", ""]
    out.append(f"**Rows audited:** {n}")
    out.append(f"**Modes run:** {', '.join(modes)}")
    out.append(f"**Budget per tactic:** {agg.get('budget_s', '?')}s, workers={agg.get('workers', '?')}")
    out.append("")

    out.append("## Per-mode closure rate")
    out.append("")
    out.append("| Mode | Closures | Rate |")
    out.append("|---|---|---|")
    for m in modes:
        out.append(f"| {m} | {closures[m]} / {n} | {fmt_pct(closures[m], n)} |")
    out.append("")

    out.append("## Per-row breakdown")
    out.append("")
    out.append("| Row | A | B | C | D | Full |")
    out.append("|---|---|---|---|---|---|")
    for rt in row_table:
        out.append(f"| `{rt['row_id']}` | {rt['A']} | {rt['B']} | {rt['C']} | {rt['D']} | {rt['Full']} |")
    out.append("")

    out.append("## ARCH-001..008 archetype distribution (Mode D)")
    out.append("")
    out.append("| Archetype | Count |")
    out.append("|---|---|")
    for a, c in sorted(arch_dist.items()):
        out.append(f"| {a} | {c} |")
    out.append("")

    out.append("## L3 anti-pattern flags raised (Mode D)")
    out.append("")
    if not flag_dist:
        out.append("(none raised — every prediction's flags should be reviewed manually anyway)")
    else:
        out.append("| Flag | Count |")
        out.append("|---|---|")
        for f, c in sorted(flag_dist.items(), key=lambda kv: -kv[1]):
            out.append(f"| `{f}` | {c} |")
    out.append("")

    out.append("## Closing-tactic frequency (Mode A successes)")
    out.append("")
    if not closing_tactic_freq:
        out.append("(no Mode A closures)")
    else:
        out.append("| Tactic | Count |")
        out.append("|---|---|")
        for t, c in sorted(closing_tactic_freq.items(), key=lambda kv: -kv[1]):
            out.append(f"| `{t}` | {c} |")
    out.append("")

    out.append("## Cross-mode fingerprint check (A ∩ D closures)")
    out.append("")
    if not cross_closures:
        out.append("No rows closed in BOTH Mode A and Mode D — archetype routing didn't yield a closure that the bare basic tactics didn't already find.")
    else:
        out.append("Rows that close in both A and D — if `same=SAME`, the archetype routing reproduced the baseline closure (no signal). If `same=DIFF`, archetype routing found a distinct tactic.")
        out.append("")
        out.append("| Row | A tactic | D tactic | Same/Diff |")
        out.append("|---|---|---|---|")
        for c in cross_closures:
            out.append(f"| `{c['row_id']}` | `{c['A_tactic']}` | `{c['D_tactic']}` | **{c['same']}** |")
    out.append("")

    # Honest verdict
    out.append("## Honest verdict")
    out.append("")
    a_rate = closures.get("A", 0)
    d_rate = closures.get("D", 0)
    if d_rate > a_rate:
        out.append(f"**Mode D archetype routing closes MORE rows than Mode A baseline** ({d_rate} > {a_rate}). Archetype routing adds signal beyond bare tactic enumeration. Promote to ablation pass-gate review.")
    elif d_rate == a_rate:
        same_count = sum(1 for c in cross_closures if c["same"] == "SAME")
        if same_count == len(cross_closures) and same_count > 0:
            out.append(f"**Mode D archetype routing matches Mode A baseline closures BUT via the same tactics** (no distinct signal). The archetype classifier is preferring the same tactic the brute-force search would find. Pass-gate FAILS the 'archetype-routed Route C closes more rows OR uses fewer attempts' criterion.")
        elif d_rate == 0:
            out.append(f"**Both Mode A and Mode D close 0 rows.** Either rows are too hard for basic tactics + Mode-D's argument-free subset, or routing needs Route C / LLM wiring (Mode B / Full). Pass-gate UNDETERMINED until B / Full are wired.")
        else:
            out.append(f"**Mode A and Mode D close equal counts ({a_rate})**, but via potentially different tactics on different rows. Inspect the cross-mode table — if D finds a row A misses (and vice versa), archetype routing adds signal even at equal counts.")
    else:
        out.append(f"**Mode D archetype routing closes FEWER rows than Mode A baseline** ({d_rate} < {a_rate}). The archetype-restricted tactic set is missing closures the broader baseline catches. Investigate which tactics Mode D omits.")
    out.append("")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    trace = json.load(open(args.in_path))
    report = analyze(trace)
    if args.out:
        Path(args.out).write_text(report)
        print(f"wrote {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    sys.exit(main() or 0)
