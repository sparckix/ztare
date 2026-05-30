#!/usr/bin/env python3
"""Mine the *temporal ordering* of v5 ops applied during closure events.

Closes a Layer-3 candidate gap surfaced by tonight's session-mining agent
(``analytics/public/queries/session_mining_analysis_2026_05_08.md``):
``mine_closure_patterns.py`` aggregates *which* v5 ops co-occur with
verified closures but discards *the order* in which they appeared.
Tonight's compression-first / falsification-last pattern (and its dual,
falsification-first / compression-last on bouncing residuals) is therefore
unrecoverable from existing miners.

This miner walks the same F-row corpus as ``mine_closure_patterns`` but
extracts the **temporal sequence** of v5 op tokens within each closure
record. A "closure event" is an F-row whose prose passes
``CLOSURE_VERIFIED_RE`` *or* a verified-axiom row attached to a
non-trivial axiom statement. For each closure event we extract an ordered
list of v5 ops (one per first-occurrence position in the prose) and
aggregate frequency tables of:

  - bigram orderings (op_A → op_B)
  - first-op distribution (which ops *open* a closure narrative)
  - last-op distribution (which ops *close* a closure narrative)
  - 3-gram orderings restricted to the most-common openers / closers

Each row's outcome (verified / falsified_with_finding / falsified_null /
in_progress) is preserved so the operator can read frequencies stratified
by closure outcome.

**Honest limits:** prose ordering is a noisy proxy for *causal* ordering
of moves (an F-row author may discuss techniques in an order that differs
from how they were applied). Mitigation: aggregate over many F-rows and
flag patterns that recur across substrate classes; do not promote any
single-row sequence as a primitive.

Output:
  ``analytics/public/queries/v5_op_temporal_ordering_<DATE>.json``
  ``analytics/public/queries/v5_op_temporal_ordering_<DATE>.md``

Pure CPU. No LLM.

Usage:
    python scripts/public/mining/mine_v5_op_temporal_ordering.py
    python scripts/public/mining/mine_v5_op_temporal_ordering.py --since 2026-04-01
    python scripts/public/mining/mine_v5_op_temporal_ordering.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
F_ROWS = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
PROJECTS_DIR = REPO / "projects"

# Reuse the v5-op pattern table from mine_closure_patterns. Importing
# would couple modules — duplicating is honest acceptable cost for a
# pure aggregator.
V5_OP_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("core_01_reformulation",
     re.compile(r"\b(reformulat|recast|translate|isomorph|map[s]? to|change of basis)\b", re.I)),
    ("core_02_iterative_refinement",
     re.compile(r"\b(iterat|refine[ds]?|polish[es]?|tighten[s]?|sharpen[s]?)\b", re.I)),
    ("core_03_decomposition",
     re.compile(r"\b(decompos|split[s]?|partition|factor(?:ize|ization)|break[s]? down)\b", re.I)),
    ("core_04_local_to_global",
     re.compile(r"\b(local[- ]to[- ]global|glue|patch|sheaf|extend[s]? from|stitch|ascend[s]? from)\b", re.I)),
    ("core_05_canonical_invariance",
     re.compile(r"\b(canonical|invariant|symmetr|gauge|equivar|normaliz|standard form)\b", re.I)),
    ("core_06_external_framework",
     re.compile(r"\b(import(?:ed|ing)? (?:from|the)|borrow[s]? (?:from|the)|leverag[es]? (?:from|the)|appl[ies]+ (?:the|a) framework|under (?:the|a) framework)\b", re.I)),
    ("core_07_generalization",
     re.compile(r"\b(generaliz|abstract over|lift to|extend[s]? to|broader|family of)\b", re.I)),
    ("broad_extremal_case",
     re.compile(r"\b(extrem|worst[- ]case|best[- ]case|boundary case|edge case|corner case)\b", re.I)),
    ("broad_compression",
     re.compile(r"\b(compress|reduce[ds]? to|equivalent[ly]? to|simplif|collaps)\b", re.I)),
    ("broad_inversion",
     re.compile(r"\b(invert|reverse|dual(?:ity)?|adjoint|contrapositive)\b", re.I)),
    ("broad_falsification",
     re.compile(r"\b(falsif|counterexample|counter-example|disprov|refut)\b", re.I)),
    ("subfield_pde_estimate_craft",
     re.compile(r"\b(estimate|bound|inequalit|sobolev|holder|hölder|interpolat|integrat[ie])\b", re.I)),
    ("subfield_proof_search_pivot",
     re.compile(r"\b(pivot|reframe|change.*approach|switch.*tactic|new.*angle)\b", re.I)),
    ("subfield_residual_chasing",
     re.compile(r"\b(residual|tail|asymptot|convergen[ct]e rate)\b", re.I)),
    ("subfield_basin_hopping",
     re.compile(r"\b(basin|local minim|landscape|optimization basin)\b", re.I)),
]

CLOSURE_VERIFIED_RE = re.compile(
    r"\b(verified[_ -]?axiom|closed[ -](?:proof|obligation)|"
    r"verdict[: ]+(?:verified|closed|proven)|theorem[ -]?proven|"
    r"machine-?check|pre-?registered.*pass|hard pass)\b",
    re.I,
)
CLOSURE_FALSIFIED_WITH_FINDING_RE = re.compile(
    r"\b(falsified.*(?:finding|discovery)|counterexample.*found|"
    r"refut(?:ed|ation).*(?:produc|surfaced))\b",
    re.I,
)
CLOSURE_FALSIFIED_NEGATIVE_RE = re.compile(
    r"\b(not falsified|null result|no signal|unable to (?:falsify|disprove))\b",
    re.I,
)


def classify_closure_status(prose: str) -> str:
    if CLOSURE_VERIFIED_RE.search(prose):
        return "verified"
    if CLOSURE_FALSIFIED_WITH_FINDING_RE.search(prose):
        return "falsified_with_finding"
    if CLOSURE_FALSIFIED_NEGATIVE_RE.search(prose):
        return "falsified_null"
    return "in_progress"


def extract_v5_op_sequence(prose: str) -> list[str]:
    """Return v5 op ids in *order of first occurrence* in the prose.

    Each op contributes at most one element (its first hit). Ops that
    never appear are absent.
    """
    first_pos: dict[str, int] = {}
    for op_id, pat in V5_OP_PATTERNS:
        m = pat.search(prose)
        if m:
            first_pos[op_id] = m.start()
    return [op for op, _ in sorted(first_pos.items(), key=lambda kv: kv[1])]


def parse_f_rows(text: str, since_iso: str | None) -> list[dict]:
    rows = []
    since_dt = None
    if since_iso:
        try:
            since_dt = datetime.strptime(since_iso, "%Y-%m-%d")
        except ValueError:
            since_dt = None
    for line in text.splitlines():
        m = re.match(r"^\|\s*(E-[A-Z0-9-]+)\s*\|", line)
        if not m:
            continue
        cols = [c.strip() for c in line.split("|")][1:-1]
        if len(cols) < 2:
            continue
        row_id = cols[0]
        date_str = None
        for c in cols[:3]:
            md = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", c)
            if md:
                date_str = md.group(1)
                break
        if since_dt and date_str:
            try:
                row_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if row_dt < since_dt:
                    continue
            except ValueError:
                pass
        prose = " | ".join(cols[1:])
        rows.append({"id": row_id, "date_str": date_str, "prose": prose})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--since", default=None, help="Only include F-rows dated >= this date (YYYY-MM-DD).")
    ap.add_argument("--dry-run", action="store_true", help="Skip output writes.")
    ap.add_argument("--out-dir", type=Path, default=REPO / "analytics" / "public" / "queries")
    args = ap.parse_args()

    print("=== mine_v5_op_temporal_ordering ===")
    if not F_ROWS.exists():
        print(f"  ERROR: F-row file missing at {F_ROWS}")
        return 1
    rows = parse_f_rows(F_ROWS.read_text(encoding="utf-8"), args.since)
    print(f"  F-rows scanned: {len(rows)} (since={args.since})")

    sequences: list[dict] = []
    for r in rows:
        seq = extract_v5_op_sequence(r["prose"])
        if len(seq) < 2:
            continue  # need at least an A->B transition
        outcome = classify_closure_status(r["prose"])
        sequences.append({
            "row_id": r["id"],
            "date": r["date_str"],
            "outcome": outcome,
            "sequence": seq,
        })
    print(f"  closure events with >=2 ops: {len(sequences)}")

    bigram_counter: Counter = Counter()
    bigram_by_outcome: dict[str, Counter] = defaultdict(Counter)
    first_op_counter: Counter = Counter()
    last_op_counter: Counter = Counter()
    first_by_outcome: dict[str, Counter] = defaultdict(Counter)
    last_by_outcome: dict[str, Counter] = defaultdict(Counter)
    trigram_counter: Counter = Counter()

    for s in sequences:
        seq = s["sequence"]
        outcome = s["outcome"]
        first_op_counter[seq[0]] += 1
        last_op_counter[seq[-1]] += 1
        first_by_outcome[outcome][seq[0]] += 1
        last_by_outcome[outcome][seq[-1]] += 1
        for a, b in zip(seq, seq[1:]):
            bigram_counter[(a, b)] += 1
            bigram_by_outcome[outcome][(a, b)] += 1
        for a, b, c in zip(seq, seq[1:], seq[2:]):
            trigram_counter[(a, b, c)] += 1

    # Spotlight queries from tonight's mining catch:
    compression_first = first_op_counter.get("broad_compression", 0)
    falsification_last = last_op_counter.get("broad_falsification", 0)
    falsification_first = first_op_counter.get("broad_falsification", 0)
    compression_last = last_op_counter.get("broad_compression", 0)

    payload: dict = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "n_closure_events": len(sequences),
        "first_op_distribution": first_op_counter.most_common(20),
        "last_op_distribution": last_op_counter.most_common(20),
        "first_op_by_outcome": {o: c.most_common(10) for o, c in first_by_outcome.items()},
        "last_op_by_outcome": {o: c.most_common(10) for o, c in last_by_outcome.items()},
        "top_bigrams": [
            {"a": a, "b": b, "count": n}
            for (a, b), n in bigram_counter.most_common(40)
        ],
        "top_bigrams_by_outcome": {
            o: [{"a": a, "b": b, "count": n} for (a, b), n in c.most_common(20)]
            for o, c in bigram_by_outcome.items()
        },
        "top_trigrams": [
            {"a": a, "b": b, "c": c, "count": n}
            for (a, b, c), n in trigram_counter.most_common(20)
        ],
        "spotlight_patterns": {
            "compression_first": compression_first,
            "falsification_last": falsification_last,
            "falsification_first": falsification_first,
            "compression_last": compression_last,
        },
        "method_note": (
            "Prose-ordering proxy for v5-op temporal sequence. Honest "
            "limit: prose order != causal application order. Use "
            "aggregate frequencies (esp. cross-substrate-class recurrence) "
            "before promoting any sequence to a primitive."
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now(tz=timezone.utc).date().isoformat()
    out_json = args.out_dir / f"v5_op_temporal_ordering_{date_tag}.json"
    out_md = args.out_dir / f"v5_op_temporal_ordering_{date_tag}.md"

    if args.dry_run:
        print("  [dry-run] payload preview:")
        print(f"    n_closure_events={len(sequences)}")
        print(f"    top bigrams={payload['top_bigrams'][:5]}")
        print(f"    spotlight={payload['spotlight_patterns']}")
        return 0

    out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {out_json}")

    md = ["# v5-Op Temporal-Ordering Mining\n"]
    md.append(f"_Generated {payload['generated_utc']}_  ")
    md.append(f"_N closure events with >=2 ops:_ {len(sequences)}\n")
    md.append("## Spotlight (compression-first / falsification-last hypothesis)\n")
    md.append(
        f"- compression-first openings: **{compression_first}**\n"
        f"- falsification-last closings: **{falsification_last}**\n"
        f"- falsification-first openings: **{falsification_first}**\n"
        f"- compression-last closings: **{compression_last}**\n"
    )
    md.append("## Top bigrams (op_A -> op_B)\n")
    md.append("| Op A | Op B | Count |\n|---|---|---:|")
    for b in payload["top_bigrams"][:20]:
        md.append(f"| `{b['a']}` | `{b['b']}` | {b['count']} |")
    md.append("\n## First-op distribution\n")
    md.append("| Op | Count |\n|---|---:|")
    for op, n in payload["first_op_distribution"]:
        md.append(f"| `{op}` | {n} |")
    md.append("\n## Last-op distribution\n")
    md.append("| Op | Count |\n|---|---:|")
    for op, n in payload["last_op_distribution"]:
        md.append(f"| `{op}` | {n} |")
    out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
