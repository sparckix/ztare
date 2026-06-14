#!/usr/bin/env python3
"""Recursive-gain candidate aggregator.

Reads the outputs of all the existing mining scorecards and produces a
SINGLE ranked list of "things the operator could ship now to compound."

Source scorecards consumed:
  - analytics/public/queries/audits/cross_audit_dashboard.json — primitives flagged
    decorative / dead / can_handle-narrow
  - analytics/public/queries/process/structural_analogies.json — one-shot artifacts
    that are structurally analogous to existing loops (recursion candidates)
  - analytics/public/queries/reflexive/closure_patterns.json — v5-ops with Lane A density
    or axiom-only signal that might warrant ZTARE substrate testing
  - analytics/public/queries/graphs/reference_graph.json — most-cited seams (could be
    candidates for self-skeptic ZTARE substrates) + orphan seams (no
    citations, status=open → either retire or extend)
  - analytics/public/queries/process/process_catalog.json — stalled loops (declared as
    loops but classifier says static) + un-cataloged components

Each candidate carries:
  - source: which miner surfaced it
  - mechanism: kind of recursive gain (retire / wire / loop-up /
    new-ZTARE-substrate / re-validate)
  - cost: trivial / day / week / month
  - confidence: low / medium / high (signal strength from source)
  - rationale: why this is a recursive-gain bet

Output:
  analytics/public/queries/trajectory/recursive_gain_candidates.json
  analytics/public/queries/trajectory/recursive_gain_candidates.md

Pure CPU. No LLM.

Usage:
    python scripts/public/mining/mine_recursive_gain_candidates.py
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[3]
QUERIES = REPO / "analytics" / "public" / "queries"
OUT_JSON = QUERIES / "trajectory" / "recursive_gain_candidates.json"
OUT_MD = QUERIES / "trajectory" / "recursive_gain_candidates.md"


def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== recursive-gain candidate aggregator ===")

    candidates: list[dict] = []

    # ---- Source 1: cross-audit dashboard
    cross_audit = _load(QUERIES / "audits" / "cross_audit_dashboard.json")
    if cross_audit:
        for sig in cross_audit.get("convergent_signals", []) or []:
            if sig.get("kind") != "primitive":
                continue
            severity = sig.get("severity", "")
            details = "; ".join(f.get("detail", "") for f in sig.get("flags") or [])
            # Decorative/dead primitives are retire/wire candidates
            if "decorative" in details or "dead" in details:
                mech = "retire_or_widen_can_handle"
                cost = "day"
                conf = "high" if sig.get("n_sources", 0) >= 2 else "medium"
                rationale = (
                    f"Cross-audit ({sig.get('n_sources')} independent scorecards) "
                    f"flagged {sig['id']} as {severity}. Either retire "
                    f"(low cost) or widen its can_handle predicate so it "
                    f"engages on more substrates (medium cost)."
                )
                candidates.append({
                    "source": "cross_audit",
                    "entity": sig["id"],
                    "kind": "primitive",
                    "mechanism": mech,
                    "cost": cost,
                    "confidence": conf,
                    "rationale": rationale,
                    "details": details[:300],
                })

    # ---- Source 2: structural analogies (one-shot → loop candidates)
    analogies = _load(QUERIES / "process" / "structural_analogies.json")
    if analogies:
        for pair in (analogies.get("pairs") or [])[:20]:
            score = pair.get("score", 0)
            if score < 0.20:
                continue
            mech = "wire_one_shot_as_loop"
            cost = "week"
            conf = "high" if score >= 0.30 else "medium"
            rationale = (
                f"Structural-analogy miner: {pair['one_shot']} (one-shot) "
                f"is structurally analogous to {pair['analogous_loop']} (loop). "
                f"Score {score}. Wiring the one-shot as a recursive loop "
                f"would mirror the apparatus's existing closure pattern. "
                f"GP-226 charter-critic is the canonical example of this move."
            )
            candidates.append({
                "source": "structural_analogies",
                "entity": pair["one_shot"],
                "kind": "one_shot_artifact",
                "mechanism": mech,
                "cost": cost,
                "confidence": conf,
                "rationale": rationale,
                "details": (
                    f"analogous to: {pair['analogous_loop']} | "
                    + "; ".join(pair.get("rationale", []))[:200]
                ),
            })

    # ---- Source 3: closure patterns — primitive candidates + axiom-only
    closure = _load(QUERIES / "reflexive" / "closure_patterns.json")
    if closure:
        for cand in closure.get("candidates", []) or []:
            verdict = cand.get("verdict", "")
            if verdict == "primitive_candidate":
                mech = "promote_to_cage_gate"
                cost = "week"
                conf = "high"
                rationale = (
                    f"Closure-pattern miner: v5-op '{cand['v5_op']}' surfaces "
                    f"in {cand['closure_count']} closing rows "
                    f"({cand.get('f_row_count', 0)} F-row + "
                    f"{cand.get('axiom_count', 0)} axiom) across "
                    f"{cand['n_substrate_classes']} substrate classes; no "
                    f"existing cage gate covers it. Promote to a deterministic "
                    f"primitive."
                )
            elif verdict == "axiom_only_candidate":
                mech = "ZTARE_substrate_proposal"
                cost = "month"
                conf = "low"
                rationale = (
                    f"Closure-pattern miner: v5-op '{cand['v5_op']}' has "
                    f"{cand.get('axiom_count', 0)} axiom-corpus attestations "
                    f"but ZERO F-row closure attestations across "
                    f"{cand['n_substrate_classes']} substrate classes. To "
                    f"validate it: run a NEW ZTARE substrate where this op "
                    f"is the search axis — harvest Lane A attestations or "
                    f"falsify the candidate."
                )
            else:
                continue
            candidates.append({
                "source": "closure_patterns",
                "entity": cand["v5_op"],
                "kind": "v5_op",
                "mechanism": mech,
                "cost": cost,
                "confidence": conf,
                "rationale": rationale,
                "details": cand.get("rationale", "")[:300],
            })

    # ---- Source 4: reference graph — orphan + decision-critical
    ref_graph = _load(QUERIES / "graphs" / "reference_graph.json")
    if ref_graph:
        # Top-cited seams could be candidates for self-skeptic ZTARE substrates
        top_cited = (ref_graph.get("top_cited_nodes") or [])[:5]
        for n in top_cited:
            nid = n.get("id", "")
            if not nid.startswith("research_areas/private/seams/"):
                continue
            in_deg = n.get("in_degree", 0)
            mech = "self_skeptic_ZTARE_substrate"
            cost = "month"
            conf = "medium"
            rationale = (
                f"Reference graph: this seam has in-degree {in_deg} (top-5 "
                f"decision-critical). It's a structural anchor — running a "
                f"ZTARE substrate that adversarially questions this seam "
                f"is a high-leverage recursive-gain move (the apparatus "
                f"evaluating its own assumptions)."
            )
            candidates.append({
                "source": "reference_graph_load_bearing",
                "entity": nid,
                "kind": "load_bearing_seam",
                "mechanism": mech,
                "cost": cost,
                "confidence": conf,
                "rationale": rationale,
                "details": f"in-degree {in_deg}, week {n.get('week')}",
            })

    # ---- Source 5: process catalog stalled loops
    process_catalog = _load(QUERIES / "process" / "process_catalog.json")
    if process_catalog:
        for entry in (process_catalog.get("all_records") or []):
            if not entry.get("kind_disagreement"):
                continue
            seed_kind = entry.get("seed_declared_kind") or ""
            inferred = entry.get("inferred_kind") or ""
            if seed_kind in ("loop", "periodic") and inferred in ("static", "one_shot", "occasional"):
                mech = "revive_stalled_loop"
                cost = "day"
                conf = "high"
                rationale = (
                    f"Process catalog: declared as {seed_kind!r} but the "
                    f"heuristic classifier says {inferred!r} (last write "
                    f"{entry.get('age_days', '?')}d ago). Either re-trigger "
                    f"the loop, formally retire it, or downgrade the seed "
                    f"declaration."
                )
                candidates.append({
                    "source": "process_catalog_stalled",
                    "entity": entry.get("path", ""),
                    "kind": "stalled_loop",
                    "mechanism": mech,
                    "cost": cost,
                    "confidence": conf,
                    "rationale": rationale,
                    "details": "; ".join(entry.get("notes") or [])[:200],
                })

    # ---- Sort: high-confidence first, then by mechanism cost (smaller first)
    cost_order = {"trivial": 0, "day": 1, "week": 2, "month": 3}
    conf_order = {"high": 0, "medium": 1, "low": 2}
    candidates.sort(
        key=lambda c: (
            conf_order.get(c["confidence"], 99),
            cost_order.get(c["cost"], 99),
        )
    )

    # ---- Strange-loop opportunity: re-package external R&D evidence as
    # ZTARE substrate input. Always emit one synthesis candidate.
    candidates.append({
        "source": "synthesis",
        "entity": "ZTARE-on-ZTARE-with-external-evidence",
        "kind": "meta_substrate",
        "mechanism": "strange_loop_ZTARE_substrate",
        "cost": "month",
        "confidence": "high",
        "rationale": (
            "The Research Director agents (Codex on NS, Claude on gravity, "
            "etc.) generate substrate-level findings OUTSIDE the ZTARE "
            "evaluation loop. Those findings sit in projects/*/workspace/, "
            "papers/*, and the F-row table — visible to the apparatus but "
            "never evaluated by it. A ZTARE-on-ZTARE substrate that ingests "
            "these external findings as INPUT — and asks the apparatus to "
            "evaluate / refine / extend them — closes the strange loop. "
            "See GP-134 ZTARE-on-ZTARE seam for the strange-loop proposal "
            "added 2026-05-06."
        ),
        "details": "meta-recursive bet. See GP-134.",
    })

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_candidates": len(candidates),
        "by_source": {
            s: sum(1 for c in candidates if c["source"] == s)
            for s in {c["source"] for c in candidates}
        },
        "by_mechanism": {
            m: sum(1 for c in candidates if c["mechanism"] == m)
            for m in {c["mechanism"] for c in candidates}
        },
        "candidates": candidates,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  candidates: {len(candidates)}")
    print(f"  by source: {payload['by_source']}")
    print(f"  wrote {args.out_json}")

    md = ["# Recursive-Gain Candidates\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Total:_ {len(candidates)}\n")
    md.append(
        "Aggregated across all mining surfaces (cross-audit, structural-"
        "analogy, closure-pattern, reference-graph, process-catalog). "
        "Each row is a recursive-gain bet: a concrete move the operator "
        "could promote to compound apparatus capability.\n"
    )
    md.append(
        "| Confidence | Cost | Mechanism | Entity | Source | Rationale |\n"
        "|---|---|---|---|---|---|"
    )
    for c in candidates[:50]:
        rationale = c["rationale"][:200]
        md.append(
            f"| `{c['confidence']}` | `{c['cost']}` | `{c['mechanism']}` | "
            f"`{c['entity'][:60]}` | `{c['source']}` | {rationale} |"
        )
    md.append("")
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
