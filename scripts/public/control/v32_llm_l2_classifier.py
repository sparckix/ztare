#!/usr/bin/env python3
"""v32_llm_l2_classifier.py — GPT-5.5 Case 2: LLM-as-L2-classifier (NOT prover).

Deterministic L2 keyword classifier genuinely fails (0/18 even with full
statement+proof — v32_deterministic_L2_retest). Per GPT-5.5 Case 2:
use an LLM ONLY as a classifier: Lean theorem statement+proof → L2 op_id
from the 18 universal_v5_ops.

This script:
  1. Classifies the 18 v32 curated rows via gpt-4.1-mini against the
     18-op vocabulary (with each op's structural_mechanism as the rubric).
  2. Emits an operator-labeling sheet (same 18 rows + the 18-op menu)
     so the operator can supply ground-truth labels.
  3. When operator labels exist (--gold <path>), computes the GPT-5.5
     pass-gate: LLM ≥80% agreement with operator AND beats deterministic
     (which is 0/18 — so the binding test is the ≥80% vs operator).

No prover. No GNN. LLM used strictly as a classifier.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from gp235_section_4_1_intra_cluster import extract_proof_body  # type: ignore
from v32_route_c_replay_batch import extract_signature  # type: ignore

CATALOG = json.load(open(ROOT / "docs/reference/structural_language_catalog.json"))
OPS = CATALOG["universal_v5_ops"]
OP_MENU = "\n".join(
    f"  {o['op_id']}: {o['name']} — {o.get('structural_mechanism','')[:140]}"
    for o in OPS
)
VALID_OPS = {o["op_id"] for o in OPS}

PROMPT = """You are an L2 STRUCTURAL-CONTENT classifier (NOT a theorem prover).

Given a Lean 4 / Mathlib theorem (statement + proof), identify which ONE
structural-content operation from the GP-216 universal_v5 vocabulary best
describes HOW the proof restructures the problem. This is about the
mathematical MOVE, not the Lean tactics.

The 18 operations:
{op_menu}

Theorem name: {name}
Statement:
{sig}
Proof body:
{body}

Output STRICT JSON:
{{
  "op_id": "<one of the 18 op_ids exactly>",
  "confidence": "high|medium|low",
  "rationale": "<=1 sentence: which structural move and why"
}}
Output JSON now."""


def call_openai(prompt: str, model: str = "gpt-4.1-mini") -> dict:
    from openai import OpenAI
    cli = OpenAI()
    r = cli.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, temperature=0.0,
    )
    return json.loads(r.choices[0].message.content or "{}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=None, help="path to operator labels JSON {row_id: op_id}")
    ap.add_argument("--model", default="gpt-4.1-mini")
    ap.add_argument("--emit-labeling-sheet", action="store_true")
    args = ap.parse_args()

    curated = json.load(open("/tmp/v32_curated_test_rows.json"))
    rows = [r for r in curated["rows"] if r.get("resolved_path") and r.get("theorem")]

    classified = []
    for r in rows:
        thm = r["theorem"]
        sig = extract_signature(r["resolved_path"], thm) or "(sig extraction failed)"
        body = extract_proof_body(r["resolved_path"], thm) or "(body extraction failed)"
        try:
            out = call_openai(PROMPT.format(
                op_menu=OP_MENU, name=thm, sig=sig[:600], body=body[:600]
            ), model=args.model)
            op = out.get("op_id", "?")
            if op not in VALID_OPS:
                op = "INVALID_" + str(op)
            classified.append({
                "row_id": r["row_id"], "theorem": thm,
                "llm_op": op, "llm_conf": out.get("confidence", "?"),
                "llm_rationale": out.get("rationale", "")[:160],
                "sig": sig[:200],
            })
            print(f"  {thm[:38]:<38} → {op} ({out.get('confidence','?')})")
        except Exception as e:
            classified.append({"row_id": r["row_id"], "theorem": thm, "llm_op": f"ERROR:{e}"})
            print(f"  {thm[:38]:<38} → ERROR {e}")

    out_obj = {
        "model": args.model,
        "n_rows": len(rows),
        "label_space": [o["op_id"] for o in OPS],
        "classified": classified,
    }

    # Distinctness check (anti-degenerate): does the LLM produce VARIED labels?
    ops_used = [c["llm_op"] for c in classified if c.get("llm_op", "").startswith(("core","broad","spec"))]
    n_distinct = len(set(ops_used))
    out_obj["n_distinct_ops_used"] = n_distinct
    out_obj["distinctness_note"] = (
        f"{n_distinct} distinct ops across {len(ops_used)} valid classifications "
        f"(degenerate if 1; the v32 deterministic failure was 0 signal — any "
        f">=3 distinct is already strictly better than the 0/18 baseline)"
    )

    # Pass-gate vs operator gold (if provided)
    if args.gold and Path(args.gold).exists():
        gold = json.load(open(args.gold))
        agree = 0
        compared = 0
        for c in classified:
            g = gold.get(c["row_id"]) or gold.get(c["theorem"])
            if g:
                compared += 1
                if g == c.get("llm_op"):
                    agree += 1
        rate = agree / compared if compared else 0
        out_obj["pass_gate"] = {
            "operator_compared": compared,
            "agree": agree,
            "agreement_rate": round(rate, 3),
            "deterministic_baseline": "0/18 (genuinely fails)",
            "gate_threshold": 0.80,
            "verdict": "PASS_LLM_L2_CLASSIFIER" if rate >= 0.80 else "FAIL_NEEDS_BETTER_CLASSIFIER",
        }
        print(f"\nPASS-GATE: LLM agreement with operator = {agree}/{compared} = {100*rate:.0f}% "
              f"(threshold 80%; deterministic baseline 0/18) → "
              f"{out_obj['pass_gate']['verdict']}")
    else:
        # Emit the operator labeling sheet
        sheet_lines = [
            "# v32 L2 operator-labeling sheet",
            "# For each row, replace ??? with the best-fit op_id from the menu.",
            "# Menu:", OP_MENU, "",
            "# Rows (theorem + signature). Fill op_id:",
        ]
        gold_template = {}
        for c in classified:
            sheet_lines.append(f"\n## {c['row_id']} — {c['theorem']}")
            sheet_lines.append(f"   sig: {c.get('sig','')[:160]}")
            sheet_lines.append(f"   (LLM guessed: {c.get('llm_op','?')} / {c.get('llm_conf','?')})")
            sheet_lines.append(f"   operator_op_id: ???")
            gold_template[c["row_id"]] = "???"
        sheet_path = Path("/tmp/v32_L2_operator_labeling_sheet.md")
        sheet_path.write_text("\n".join(sheet_lines))
        json_template = Path("/tmp/v32_L2_operator_labels_TEMPLATE.json")
        json_template.write_text(json.dumps(gold_template, indent=2))
        print(f"\nOperator labeling sheet → {sheet_path}")
        print(f"Fill-in JSON template → {json_template}")
        print(f"Then re-run with: --gold /tmp/v32_L2_operator_labels_TEMPLATE.json")

    out_path = ROOT / "analytics/public/leanmill/results/v32_llm_l2_classifier_results.json"
    out_path.write_text(json.dumps(out_obj, indent=2, default=str))
    print(f"wrote {out_path}")
    print(f"distinctness: {out_obj['distinctness_note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
