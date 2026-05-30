#!/usr/bin/env python3
"""v32_rich_corpus_l2_test.py — corrected substrate test on RICH multi-step proofs.

v32 elementary-Mathlib-one-liner corpus produced degenerate L2 labels
(deterministic 0/18 no-signal; LLM 18/18 constant core_01). Mechanism:
short Mathlib lemmas don't restructure problems, so no L2-op variation
to classify.

This re-points at structurally-RICH multi-step proofs (V30RouteCManual +
V30eRouteC: 4-term triangle composition, polar identity, log_div
decomposition, k-fold monotonicity, etc.) where L2-op variation — if the
3-catalog substrate thesis holds — should actually appear.

Decision:
  - LLM-L2 produces n_distinct >= 3 varied ops with reasonable confidence
    → substrate HAS signal on rich proofs; re-run miner on rich corpus.
  - LLM-L2 still collapses to ~1 op → substrate thesis genuinely weak
    even on rich proofs (GPT-5.5 Case 3 confirmed, not corpus artifact).

LLM strictly as classifier. No prover. No GNN.
"""
from __future__ import annotations
import json, re, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
SB = ROOT / "analytics/public/leanmill/external_benchmarks/sandboxes/v28A_carleson_baseline/carleson"
CATALOG = json.load(open(ROOT / "docs/reference/structural_language_catalog.json"))
OPS = CATALOG["universal_v5_ops"]
OP_MENU = "\n".join(f"  {o['op_id']}: {o['name']} — {o.get('structural_mechanism','')[:140]}" for o in OPS)
VALID = {o["op_id"] for o in OPS}

PROMPT = """You are an L2 STRUCTURAL-CONTENT classifier (NOT a prover).

Identify which ONE structural-content operation best describes HOW this
Lean proof RESTRUCTURES the problem (the mathematical move, not the tactics).

You MUST discriminate. Do NOT default to core_01 (Problem Reformulation)
unless you have actively ruled out core_03 (Decomposition), core_05
(Canonical Form), broad_01 (Iterative Refinement), broad_03 (Duality),
and broad_08 (Constraint Propagation). core_01 is the LAST resort, not
the first.

The 18 operations:
{op_menu}

Lean proof file `{name}`:
{body}

STRICT JSON:
{{"op_id":"<exact op_id>","confidence":"high|medium|low",
  "ruled_out":["<op_ids you considered and rejected>"],
  "rationale":"<=1 sentence"}}
Output JSON now."""


def call_openai(prompt: str, model: str = "gpt-4.1-mini") -> dict:
    from openai import OpenAI
    cli = OpenAI()
    r = cli.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, temperature=0.0,
    )
    return json.loads(r.choices[0].message.content or "{}")


def collect_rich_proofs() -> list[dict]:
    out = []
    for d in ["V30RouteCManual", "V30eRouteC"]:
        for f in sorted((SB / d).glob("*.lean")):
            txt = f.read_text()
            # Skip if it's a near-empty / sorry-only stub
            if "sorry" in txt and txt.count("\n") < 6:
                continue
            out.append({"name": f"{d}/{f.name}", "body": txt[:1800]})
    return out


def main():
    proofs = collect_rich_proofs()
    print(f"# v32 rich-corpus L2 test — {len(proofs)} multi-step proofs\n")
    classified = []
    for p in proofs:
        try:
            o = call_openai(PROMPT.format(op_menu=OP_MENU, name=p["name"], body=p["body"]))
            op = o.get("op_id", "?")
            if op not in VALID:
                op = f"INVALID:{op}"
            classified.append({
                "name": p["name"], "op": op, "conf": o.get("confidence", "?"),
                "ruled_out": o.get("ruled_out", []), "rationale": o.get("rationale", "")[:140],
            })
            print(f"  {p['name']:<32} → {op:<10} ({o.get('confidence','?')}) "
                  f"ruled_out={len(o.get('ruled_out',[]))}")
        except Exception as e:
            classified.append({"name": p["name"], "op": f"ERR:{e}"})
            print(f"  {p['name']:<32} → ERR {e}")

    valid = [c["op"] for c in classified if c["op"] in VALID]
    dist = Counter(valid)
    n_distinct = len(dist)
    hi = sum(1 for c in classified if c.get("conf") in ("high", "medium") and c["op"] in VALID)

    print(f"\n## Label distribution: {dict(dist)}")
    print(f"n_distinct ops: {n_distinct} / {len(valid)} valid classifications")
    print(f"high/medium confidence: {hi}/{len(classified)}")

    if n_distinct >= 3 and hi >= max(1, len(classified) // 2):
        verdict = "SUBSTRATE_HAS_SIGNAL_ON_RICH_PROOFS"
        rat = (f"LLM-L2 produces {n_distinct} distinct ops with {hi} hi/med-conf on "
               f"structurally-rich proofs — the v32 degeneracy WAS a corpus artifact "
               f"(elementary one-liners). Re-run miner on rich corpus.")
    elif n_distinct >= 3:
        verdict = "WEAK_SIGNAL_LOW_CONFIDENCE"
        rat = (f"{n_distinct} distinct ops but only {hi} hi/med-conf — signal present "
               f"but classifier uncertain; needs operator gold-label calibration.")
    else:
        verdict = "SUBSTRATE_THESIS_GENUINELY_WEAK"
        rat = (f"even on rich multi-step proofs LLM-L2 collapses to {n_distinct} op(s) "
               f"— GPT-5.5 Case 3 confirmed: 3-catalog L2 is explanatory vocabulary, "
               f"NOT a discriminative solver substrate. Stop mining; use catalogs for "
               f"reporting only.")
    print(f"\nVERDICT: {verdict} — {rat}")

    Path(ROOT / "analytics/public/leanmill/results/v32_rich_corpus_l2_test.json").write_text(
        json.dumps({"n_proofs": len(proofs), "distribution": dict(dist),
                    "n_distinct": n_distinct, "high_med_conf": hi,
                    "verdict": verdict, "rationale": rat,
                    "classified": classified}, indent=2, default=str))
    print("wrote analytics/public/leanmill/results/v32_rich_corpus_l2_test.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
