#!/usr/bin/env python3
"""Closure-pattern miner — Layer 3 self-improvement substrate.

When obligations close (verified, attested, falsified-with-finding),
what structural moves succeeded? This miner walks the F-row corpus
+ verified-axioms ledger, extracts per-row v5 op tags via keyword
heuristics, and aggregates a per-(substrate-class, v5_op)
closure-rate distribution.

The output surfaces v5 op clusters that recur across substrates AND
are NOT yet captured as cage gates or grammar primitives — these are
the candidate primitives for Layer 3 of recursive self-improvement
(grammar evolution from closure pattern, vs Layer 1's constraint
injection from failure pattern).

**What this miner is and isn't:**

  IS: a heuristic aggregator over F-row prose + verified-axioms +
      champion-expression tokens. v0.1 — honest about its limits.

  IS NOT: a Lean-elaborator-level grammar synthesizer. It identifies
          candidates; operator/PM disposes whether to ship as a
          gate / primitive / grammar token.

**Outputs:**

  ``analytics/public/queries/reflexive/closure_patterns.json`` — full distribution
  ``analytics/public/queries/reflexive/closure_patterns.md`` — operator-readable summary

Pure CPU. No LLM.

Usage:
    python scripts/public/mining/mine_closure_patterns.py
    python scripts/public/mining/mine_closure_patterns.py --since 2026-04-01
"""
from __future__ import annotations

import argparse
import json
import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
F_ROWS = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
PROJECTS_DIR = REPO / "projects"
RUBRICS_DIR = REPO / "rubrics"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "reflexive" / "closure_patterns.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "reflexive" / "closure_patterns.md"


# F-row table format: columns separated by `|`
F_ROW_HEAD_RE = re.compile(r"^\|\s*E-([A-Z0-9-]+)\s*\|", re.MULTILINE)


# v5 op detection heuristics — keyword + token patterns from
# universal_research_ops.py vocabulary. Each pattern is a tuple
# (op_id, regex). Matches are accumulated per F-row.
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
    # Broadly-shared (8 of 8 subfields except logic/algtop)
    ("broad_extremal_case",
     re.compile(r"\b(extrem|worst[- ]case|best[- ]case|boundary case|edge case|corner case)\b", re.I)),
    ("broad_compression",
     re.compile(r"\b(compress|reduce[ds]? to|equivalent[ly]? to|simplif|collaps)\b", re.I)),
    ("broad_inversion",
     re.compile(r"\b(invert|reverse|dual(?:ity)?|adjoint|contrapositive)\b", re.I)),
    ("broad_falsification",
     re.compile(r"\b(falsif|counterexample|counter-example|disprov|refut)\b", re.I)),
    # Subfield-specific (4 ops)
    ("subfield_pde_estimate_craft",
     re.compile(r"\b(estimate|bound|inequalit|sobolev|holder|hölder|interpolat|integrat[ie])\b", re.I)),
    ("subfield_proof_search_pivot",
     re.compile(r"\b(pivot|reframe|change.*approach|switch.*tactic|new.*angle)\b", re.I)),
    ("subfield_residual_chasing",
     re.compile(r"\b(residual|tail|asymptot|convergen[ct]e rate)\b", re.I)),
    ("subfield_basin_hopping",
     re.compile(r"\b(basin|local minim|landscape|optimization basin)\b", re.I)),
]

# Closure-status detection from F-row prose. The F-rows are
# operator-attested narrative — heuristic but corpus-tested.
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


def derive_substrate_class(project_name: str) -> str:
    """Same heuristic as cap-kind miner."""
    for cand in (
        RUBRICS_DIR / f"{project_name}.json",
        RUBRICS_DIR / f"dynamic_{project_name}.json",
    ):
        if cand.exists():
            try:
                rubric = json.loads(cand.read_text())
                cm = rubric.get("cage_meta") or {}
                cls = cm.get("class")
                if isinstance(cls, str) and cls.strip():
                    return cls.strip()
            except Exception:  # noqa: BLE001
                pass
    n = project_name.lower()
    if n.startswith("ns_") or "ns_" in n[:5]:
        return "ns_pde"
    if n.startswith("oeis"):
        return "oeis_sequence"
    if n.startswith("gp"):
        return "gp_unspecified"
    if "consciousness" in n or "ai_" in n:
        return "qualitative_business"
    if n.startswith("paper") or "draft" in n:
        return "paper_review"
    return "uncategorized"


def parse_f_rows(text: str) -> list[dict]:
    """Parse the F-row table into per-row dicts.

    Heuristic: each row is a single line starting with `| E-`; columns
    are pipe-separated. F-rows have varying schemas across vintages
    (some have 7 columns, some 8) — we capture (id, raw_line) and
    let the downstream classifier inspect free-form prose.
    """
    rows = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(E-[A-Z0-9-]+)\s*\|", line)
        if not m:
            continue
        cols = [c.strip() for c in line.split("|")][1:-1]  # drop leading + trailing empties
        if len(cols) < 2:
            continue
        row_id = cols[0]
        # Try to extract date column if present (typically col 1 or 2)
        date_str = None
        for c in cols[:3]:
            m_date = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", c)
            if m_date:
                date_str = m_date.group(1)
                break
        # Project: extract from id like `E-GP186-NS-PHASE5CH-01` → "ns" related
        # or from a project mention in prose
        prose = " | ".join(cols[1:])
        # Look for project name in the prose
        project = None
        m_proj = re.search(r"projects/([A-Za-z0-9_-]+)/", prose)
        if m_proj:
            project = m_proj.group(1)
        rows.append({
            "id": row_id,
            "date_str": date_str,
            "raw_line": line,
            "prose": prose,
            "project": project,
        })
    return rows


def classify_closure_status(prose: str) -> str:
    """Return one of:
      - 'verified' (closed by verified axiom / theorem proven)
      - 'falsified_with_finding' (refuted, but produced a discovery)
      - 'falsified_null' (refuted, no signal)
      - 'in_progress' (default — neither verified nor falsified)
    """
    if CLOSURE_VERIFIED_RE.search(prose):
        return "verified"
    if CLOSURE_FALSIFIED_WITH_FINDING_RE.search(prose):
        return "falsified_with_finding"
    if CLOSURE_FALSIFIED_NEGATIVE_RE.search(prose):
        return "falsified_null"
    return "in_progress"


def extract_v5_ops(prose: str) -> list[str]:
    """Match all v5 op patterns; return list of unique op_ids that
    appear at least once in the prose."""
    hits = []
    for op_id, pat in V5_OP_PATTERNS:
        if pat.search(prose):
            hits.append(op_id)
    return hits


# Cage gates currently shipped — used for "primitive_candidate"
# detection (an v5-op cluster recurring in closures BUT lacking a
# corresponding gate is a candidate to ship as a new primitive).
EXISTING_CAGE_GATES = {
    "feature_coverage_adequacy": ["core_05_canonical_invariance"],
    "target_convention_homogeneity": ["core_05_canonical_invariance"],
    "cross_class_extrapolation": ["broad_extremal_case", "core_07_generalization"],
    "per_class_farther_tail": ["broad_extremal_case", "subfield_residual_chasing"],
    "symbolic_logic_cage": ["core_05_canonical_invariance"],
    "substrate_critic": ["core_05_canonical_invariance"],
    "noise_profile": ["subfield_pde_estimate_craft"],
    "analogy": ["core_06_external_framework"],
    "framer_1d": ["core_05_canonical_invariance"],
    # GP-076 + adjacent
    "predictive_divergence_sweep": ["broad_falsification"],
    "dag_steering": ["subfield_proof_search_pivot"],
    # GP-223 (proposed)
    "endpoint_type_compression_gate": ["broad_compression", "core_05_canonical_invariance"],
}


def map_op_to_existing_gates(op_id: str) -> list[str]:
    """Find which existing cage gates already cover this op."""
    return [
        gate
        for gate, ops in EXISTING_CAGE_GATES.items()
        if op_id in ops
    ]


def walk_verified_axioms() -> list[dict]:
    """Walk every projects/*/verified_axioms.json and emit one record
    per non-trivial axiom.

    Returns list of dicts with keys: project, substrate_class,
    axiom_text (string content of the axiom), source_path.

    Skips axioms that are sentinel text like "No inherited truth from
    prior runs" (the standard empty-state marker).
    """
    out = []
    for path in sorted(PROJECTS_DIR.glob("*/verified_axioms.json")):
        project_name = path.parent.name
        substrate_class = derive_substrate_class(project_name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        axioms_list = (
            data
            if isinstance(data, list)
            else (data.get("axioms", []) if isinstance(data, dict) else [])
        )
        for ax in axioms_list:
            if isinstance(ax, str):
                if "inherited truth" in ax.lower():
                    continue
                ax_text = ax
            elif isinstance(ax, dict):
                ax_text = (
                    ax.get("content")
                    or ax.get("statement")
                    or ax.get("axiom")
                    or ax.get("text")
                    or ax.get("body")
                    or ""
                )
                if not ax_text:
                    # Fallback: stringify all values
                    ax_text = " ".join(
                        str(v) for v in ax.values() if isinstance(v, str)
                    )
                if not ax_text or "inherited truth" in str(ax_text).lower():
                    continue
            else:
                continue
            out.append({
                "project": project_name,
                "substrate_class": substrate_class,
                "axiom_text": str(ax_text),
                "source_path": str(path.relative_to(REPO)),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=str, default=None,
                    help="ISO date — only F-rows on/after")
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== closure-pattern miner ===")

    if not F_ROWS.exists():
        print(f"  ERROR: F-row file not found at {F_ROWS}")
        return 1

    # ---- Lane A: F-row prose ----
    text = F_ROWS.read_text(encoding="utf-8")
    rows = parse_f_rows(text)
    print(f"  F-rows parsed: {len(rows)}")

    # ---- Lane B: verified_axioms.json corpus (ground-truth verification) ----
    verified_axioms = walk_verified_axioms()
    print(f"  verified-axioms records: {len(verified_axioms)}")

    # Optional date filter
    cutoff = args.since
    if cutoff:
        rows = [r for r in rows if (r["date_str"] or "") >= cutoff]
        print(f"  after --since {cutoff}: {len(rows)}")

    # Classify + extract ops per row
    by_status: Counter[str] = Counter()
    # closure_distribution[(substrate_class, status)][v5_op] = count
    closure_dist: dict[tuple, Counter] = defaultdict(Counter)
    # verified_op_count[v5_op] = total verified appearances (across all classes)
    verified_op_count: Counter[str] = Counter()
    falsified_finding_op_count: Counter[str] = Counter()
    in_progress_op_count: Counter[str] = Counter()
    # substrate-class totals
    class_status_totals: dict[tuple, int] = defaultdict(int)
    # Per-substrate-class verified op breakdown
    per_class_verified_ops: dict[str, Counter] = defaultdict(Counter)

    rows_classified = []
    for r in rows:
        status = classify_closure_status(r["prose"])
        ops = extract_v5_ops(r["prose"])
        substrate_class = (
            derive_substrate_class(r["project"]) if r["project"] else "uncategorized"
        )
        by_status[status] += 1
        class_status_totals[(substrate_class, status)] += 1
        for op in ops:
            closure_dist[(substrate_class, status)][op] += 1
            if status == "verified":
                verified_op_count[op] += 1
                per_class_verified_ops[substrate_class][op] += 1
            elif status == "falsified_with_finding":
                falsified_finding_op_count[op] += 1
            elif status == "in_progress":
                in_progress_op_count[op] += 1
        rows_classified.append({
            "id": r["id"],
            "date": r["date_str"],
            "project": r["project"],
            "substrate_class": substrate_class,
            "closure_status": status,
            "v5_ops": ops,
        })

    # ---- Lane B aggregation: verified-axioms-as-closure ----
    # Each non-trivial axiom counts as a verified-by-axiom-ledger
    # closure event, regardless of F-row attestation. v5 op tags come
    # first from the LLM enrichment cache (scripts/public/mining/llm_enrich_v5_op_tags.py),
    # then fall back to keyword heuristics. The keyword tagger only
    # catches ~4.2% of axioms; LLM enrichment hits ~97% so this
    # switch-on-presence boosts Layer 3 signal ~23x.
    llm_tags_path = REPO / "analytics" / "public" / "queries" / "v5_op_tags_llm.json"
    llm_tags: dict[str, list[str]] = {}
    if llm_tags_path.exists():
        try:
            llm_data = json.loads(llm_tags_path.read_text(encoding="utf-8"))
            for ax_id, entry in llm_data.items():
                if isinstance(entry, dict):
                    ops_v = entry.get("ops")
                    if isinstance(ops_v, list):
                        llm_tags[ax_id] = [
                            o for o in ops_v if isinstance(o, str)
                        ]
            print(f"  LLM v5-op enrichment loaded: {len(llm_tags)} axioms")
        except Exception:  # noqa: BLE001
            pass

    def _tag_axiom(ax: dict) -> tuple[list[str], str]:
        """Return (ops, source) where source is 'llm' or 'keyword'."""
        sha = hashlib.sha1(
            ax["axiom_text"].encode("utf-8")
        ).hexdigest()[:8]
        ax_id = f"{ax['project']}::{sha}"
        if ax_id in llm_tags:
            return llm_tags[ax_id], "llm"
        return extract_v5_ops(ax["axiom_text"]), "keyword"

    # Track counts per lane separately so the verdict logic can
    # require corroborating signal from BOTH lanes (Lane A = F-row
    # closures, Lane B = verified-axiom corpus). 2026-05-06 PM
    # finding: the LLM over-tagged 1291 uncategorized governance
    # axioms in Lane B with surface-keyword matches that don't
    # correspond to real meta-operations. Without per-lane separation
    # the verdict mixed governance noise into the primitive-candidate
    # signal. Fix: a primitive_candidate verdict now requires ≥1 Lane
    # A closure attesting the op is actually used in real research
    # closures, not just declared in axioms.
    axiom_op_count: Counter[str] = Counter()
    per_class_axiom_ops: dict[str, Counter] = defaultdict(Counter)
    n_axioms_with_ops = 0
    n_axioms_llm_tagged = 0
    # Snapshot Lane A counts BEFORE we fold Lane B in, so the verdict
    # can read "F-row only" closure counts directly.
    f_row_op_count: Counter[str] = Counter(verified_op_count)
    f_row_op_count.update(falsified_finding_op_count)
    for ax in verified_axioms:
        ops, source = _tag_axiom(ax)
        if source == "llm":
            n_axioms_llm_tagged += 1
        if ops:
            n_axioms_with_ops += 1
        for op in ops:
            axiom_op_count[op] += 1
            per_class_axiom_ops[ax["substrate_class"]][op] += 1
            # Also fold into the verified bucket — these ARE
            # verified closures, just from the ledger lane vs the
            # F-row lane.
            verified_op_count[op] += 1
            per_class_verified_ops[ax["substrate_class"]][op] += 1
    print(
        f"  verified axioms with v5-op tags: {n_axioms_with_ops}"
        f" / {len(verified_axioms)}"
        f" (LLM-tagged: {n_axioms_llm_tagged})"
    )

    # ---- Layer 3 candidate detection ----
    # An op is a "primitive candidate" if:
    #   - appears in ≥3 closing rows (Lane A + Lane B combined)
    #   - across ≥2 distinct substrate classes
    #   - AND has no existing cage gate
    #   - AND has ≥1 Lane A (F-row) attestation — guards against
    #     LLM-over-tagged governance noise dominating Lane B
    closure_op_count = verified_op_count + falsified_finding_op_count
    candidates = []
    for op, count in closure_op_count.most_common():
        n_classes = sum(
            1
            for cls, ops in per_class_verified_ops.items()
            if op in ops
        )
        existing_gates = map_op_to_existing_gates(op)
        f_row_count = f_row_op_count.get(op, 0)
        axiom_count = axiom_op_count.get(op, 0)
        if (
            count >= 3
            and n_classes >= 2
            and not existing_gates
            and f_row_count >= 1
        ):
            candidates.append({
                "v5_op": op,
                "closure_count": count,
                "verified_count": verified_op_count[op],
                "falsified_finding_count": falsified_finding_op_count[op],
                "f_row_count": f_row_count,
                "axiom_count": axiom_count,
                "n_substrate_classes": n_classes,
                "existing_gates": existing_gates,
                "verdict": "primitive_candidate",
                "rationale": (
                    f"Recurs in {count} closing rows ({f_row_count} F-row + "
                    f"{axiom_count} axiom) across {n_classes} substrate classes; "
                    "no existing cage gate covers this op — candidate for a new "
                    "gate or grammar primitive."
                ),
            })
        elif (
            count >= 3
            and n_classes >= 2
            and not existing_gates
            and f_row_count == 0
        ):
            # Axiom-corpus-only signal — likely LLM-over-tagged
            # governance prose. Surface as low-confidence candidate
            # so the operator can spot-check the underlying axioms.
            candidates.append({
                "v5_op": op,
                "closure_count": count,
                "verified_count": verified_op_count[op],
                "falsified_finding_count": falsified_finding_op_count[op],
                "f_row_count": f_row_count,
                "axiom_count": axiom_count,
                "n_substrate_classes": n_classes,
                "existing_gates": existing_gates,
                "verdict": "axiom_only_candidate",
                "rationale": (
                    f"Surfaces in {axiom_count} axioms across {n_classes} "
                    "substrate classes but ZERO F-row closure attestations. "
                    "Likely LLM-over-tagged governance prose — spot-check "
                    "before treating as a real primitive candidate."
                ),
            })
        elif count >= 5 and existing_gates:
            candidates.append({
                "v5_op": op,
                "closure_count": count,
                "verified_count": verified_op_count[op],
                "falsified_finding_count": falsified_finding_op_count[op],
                "f_row_count": f_row_count,
                "axiom_count": axiom_count,
                "n_substrate_classes": n_classes,
                "existing_gates": existing_gates,
                "verdict": "covered_decisive",
                "rationale": (
                    f"Recurs in {count} closing rows ({f_row_count} F-row + "
                    f"{axiom_count} axiom); existing gates {existing_gates} "
                    "already cover. Decisive enough to keep."
                ),
            })

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "since": args.since,
        "total_rows": len(rows),
        "verified_axioms_count": len(verified_axioms),
        "verified_axioms_with_v5_ops": n_axioms_with_ops,
        "by_status": dict(by_status),
        "verified_op_distribution": dict(verified_op_count.most_common()),
        "axiom_lane_op_distribution": dict(axiom_op_count.most_common()),
        "falsified_finding_op_distribution": dict(
            falsified_finding_op_count.most_common()
        ),
        "in_progress_op_distribution": dict(in_progress_op_count.most_common()),
        "per_class_verified_ops": {
            cls: dict(c) for cls, c in per_class_verified_ops.items()
        },
        "per_class_axiom_ops": {
            cls: dict(c) for cls, c in per_class_axiom_ops.items()
        },
        "candidates": candidates,
        "honest_caveats": [
            "v5-op detection is keyword-based — false positives expected on "
            "multi-meaning words (e.g. 'compress' may match prose about "
            "compression but not the structural move).",
            "closure_status classifier is also keyword-based; F-row prose "
            "uses varied vocabulary across vintages.",
            "EXISTING_CAGE_GATES table is hand-curated — a new gate that "
            "covers an op but isn't in this table will look like a missing "
            "primitive when it isn't.",
            "v0.1 surfaces candidates — operator/PM disposes whether to ship.",
        ],
        # rows_classified deliberately limited to top 100 for readability
        "rows_classified_sample": rows_classified[-100:],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# Closure-Pattern Distribution\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Rows analyzed:_ {len(rows)}  "
        f"_Verified:_ {by_status.get('verified', 0)}  "
        f"_Falsified+finding:_ {by_status.get('falsified_with_finding', 0)}  "
        f"_In-progress:_ {by_status.get('in_progress', 0)}\n"
    )
    md.append("## Closure status distribution\n")
    md.append("| Status | Count |\n|---|---:|")
    for s, c in by_status.most_common():
        md.append(f"| `{s}` | {c} |")
    md.append("")
    md.append("## v5-op closure rate (verified + falsified_with_finding)\n")
    md.append("| v5 op | Verified | Falsified+finding | Total closures |\n|---|---:|---:|---:|")
    for op, count in (verified_op_count + falsified_finding_op_count).most_common():
        md.append(
            f"| `{op}` | {verified_op_count[op]} | "
            f"{falsified_finding_op_count[op]} | {count} |"
        )
    md.append("")
    if candidates:
        md.append("## Primitive candidates + decision-critical-confirmed\n")
        md.append(
            "| v5 op | Verdict | Closures | Classes | Existing gates |\n"
            "|---|---|---:|---:|---|"
        )
        for c in candidates:
            gates_str = ", ".join(c["existing_gates"]) or "—"
            md.append(
                f"| `{c['v5_op']}` | `{c['verdict']}` | "
                f"{c['closure_count']} | {c['n_substrate_classes']} | "
                f"{gates_str} |"
            )
        md.append("")
        md.append("### Detailed rationale\n")
        for c in candidates:
            md.append(f"- **`{c['v5_op']}`** — {c['rationale']}")
        md.append("")
    md.append("## Honest caveats\n")
    for cv in payload["honest_caveats"]:
        md.append(f"- {cv}")
    md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
