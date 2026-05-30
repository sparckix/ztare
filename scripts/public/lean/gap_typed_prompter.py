#!/usr/bin/env python3
"""Gap-typed prompter — two-stage prompt that first types the gap, then dispatches.

Borrowed from cognitive science of mathematicians (Polya, Hadamard):
working analysts type the GAP before searching for the theorem. They ask
"is this a Sobolev gap, an interpolation gap, a coercivity gap, ...?"
and then search by gap type. Our apparatus has been prompting LLMs cold;
this script structures the search.

# Two stages

  Stage 1 — gap typing: ask LLM to classify the field's likely-needed
  estimate into one of a fixed taxonomy:

    SOBOLEV         control by higher-derivative norm
    INTERPOLATION   between two function-space norms
    COERCIVITY      lower bound on a quadratic form
    COMMUTATOR      [A, B] error term bound
    PROPAGATION     bound preserved under time evolution
    LIMIT_PASSAGE   property transferred from finite to limit
    AUXILIARY       requires constructing a tailored test object
    UNKNOWN         no recognized type

  Stage 2 — gap-specific prompt: dispatch to a prompt + lemma set
  matched to the typed gap. Reuses the mathlib_lemma_scout index by
  shape tag.

# Reuse

  - `scripts/public/lean/lean_decl_index.py` (Stage 1 typed identifier filter)
  - `scripts/public/lean/mathlib_lemma_scout.py` (shape-tagged lemma retrieval)
  - `scripts/public/lean/typed_endpoint_pack.py` (downstream patch generation)

# Substrate-agnostic

  Default gap taxonomy is PDE-flavored. Override via CLI for other
  substrates (e.g. number-theory: ARITHMETIC / MULTIPLICATIVE / ZETA-LINE).

Usage:
    python scripts/public/lean/gap_typed_prompter.py \\
        --target TrackBProfileLipschitzControlObligation \\
        --field generated_quartic_survival_projection
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from src.ztare.research_director.gap_typing import (
    GAP_TYPES,
    heuristic_gap_type,
    rank_mathlib_entries,
)

GAP_CLASSIFICATION_PROMPT = """You are classifying a Lean obligation field into ONE of the following GAP TYPES — the mathematical-style classification of what kind of analytic step the field's discharge requires. This is NOT picking a patch class (transitivity / falsifier / ...); it's typing the MATHEMATICS.

# Gap taxonomy

{gap_taxonomy}

# Heuristic

  - If the field has a function-space norm + derivative count → SOBOLEV
  - If the field's signature mentions ratios of two norms → INTERPOLATION
  - If the field requires lower bound on a positive form → COERCIVITY
  - If the field involves operator products / Lie brackets → COMMUTATOR
  - If the field is "evolves and stays bounded" → PROPAGATION
  - If the field is a property of a limit object → LIMIT_PASSAGE
  - If the bound is a product / Hölder triple → HOLDER
  - If the answer requires inventing a tailored test function / weight → AUXILIARY
  - Otherwise → UNKNOWN (and describe what you see)

# Target

Target: {target}
Field: {field}
Field type: {field_type}

# Resolved type info

{type_info}

# Nearby theorems referencing this field

{nearby}

---

Return EXACTLY ONE JSON line:
{{"gap_type": "<TYPE>", "confidence": "high|medium|low", "rationale": "<1-2 sentences citing specific evidence>"}}"""


# 2026-05-06 PM: was hardcoded gemini-3-pro-preview; switched to
# LLMRuntime + pick_default_model_id_for_scripts.
from src.ztare.common.llm_runtime import (
    LLMRuntime,
    pick_default_model_id_for_scripts,
)

_RUNTIME = LLMRuntime()


def call_gemini(prompt: str, max_tokens: int = 600) -> str:
    """Provider-agnostic LLM call (legacy name preserved)."""
    model_id = pick_default_model_id_for_scripts()
    if model_id is None:
        return (
            "ERROR: no LLM provider available — set ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or GEMINI_API_KEY"
        )
    try:
        response = _RUNTIME.call_text(
            prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            request_label="gap_typed_prompter",
        )
        return response.text or "(empty)"
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


def classify_gap(target: str, field: str, dry_run: bool = False) -> dict:
    """Stage 1: ask LLM to type the gap."""
    from typed_endpoint_pack import (
        load_workmap_target, resolve_field, find_type_constructors,
        find_theorems_using_field, load_decl_index,
    )
    target_obj = load_workmap_target(target)
    if not target_obj:
        result = heuristic_gap_type("", target, field)
        result["rationale"] += " Target was not present in the workmap."
        return result
    field_info = resolve_field(target_obj, field)
    if not field_info:
        result = heuristic_gap_type("", target, field)
        result["rationale"] += " Field was not resolved inside the workmap target."
        return result
    if dry_run or not os.environ.get("GEMINI_API_KEY"):
        return heuristic_gap_type(field_info["field_type"], target, field)
    decl_index = load_decl_index()
    constructors = find_type_constructors(field_info["type_head"], decl_index)
    nearby = find_theorems_using_field(field, field_info["type_head"], top_n=6)

    type_info_block = "\n".join(
        f"- {c['kind']} {c['type_head']} ({c['file']}.lean): {len(c['fields'])} fields"
        for c in constructors) or "(no resolved constructors)"
    nearby_block = "\n".join(
        f"- {t['name']} (score={t['score']})"
        for t in nearby) or "(no nearby theorems)"
    taxonomy_block = "\n".join(
        f"  {gt}: {info['description']}"
        for gt, info in GAP_TYPES.items())

    prompt = GAP_CLASSIFICATION_PROMPT.format(
        gap_taxonomy=taxonomy_block,
        target=target, field=field,
        field_type=field_info["field_type"],
        type_info=type_info_block,
        nearby=nearby_block,
    )
    try:
        response = call_gemini(prompt)
    except Exception as exc:
        result = heuristic_gap_type(field_info["field_type"], target, field)
        result["rationale"] += (
            f" Provider classifier failed with {type(exc).__name__}; "
            "fell back to local heuristic."
        )
        result["provider_error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
        return result
    json_match = re.search(r"\{[^{}]*\"gap_type\"[^{}]*\}", response, re.DOTALL)
    if not json_match:
        return {"gap_type": "UNKNOWN", "rationale": f"LLM returned no JSON",
                "confidence": "low", "raw": response[:200]}
    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return {"gap_type": "UNKNOWN", "rationale": "JSON parse failed",
                "confidence": "low"}


def fetch_gap_specific_lemmas(gap_type: str, top_n: int = 12) -> list[dict]:
    """Stage 2 prep: pull mathlib lemmas tagged with the gap's shape tags."""
    index_path = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json"
    if not index_path.exists():
        return []
    index = json.loads(index_path.read_text())
    info = GAP_TYPES.get(gap_type, GAP_TYPES["UNKNOWN"])
    shape_groups = info.get("shape_tag_groups") or [info["shape_tags"]]
    shape_groups = [g for g in shape_groups if g]
    if not shape_groups:
        return []
    for shape_tags in shape_groups:
        matched = []
        for name, entry in index["by_name"].items():
            if all(s in entry.get("shapes", []) for s in shape_tags):
                item = dict(entry)
                item["_shape_group"] = shape_tags
                matched.append(item)
        if matched:
            return rank_mathlib_entries(matched, gap_type)[:top_n]

    # Some mathlib areas have sparse multi-tag overlap under the heuristic
    # classifier.  Fall back to "any requested tag", ranked by overlap count,
    # so the prompter still receives a small shelf of relevant primitives.
    all_shape_tags = sorted({s for group in shape_groups for s in group})
    loose = []
    for name, entry in index["by_name"].items():
        shapes = set(entry.get("shapes", []))
        overlap = sum(1 for s in all_shape_tags if s in shapes)
        if overlap:
            item = dict(entry)
            item["_shape_overlap"] = overlap
            loose.append(item)
    loose.sort(key=lambda e: (-e["_shape_overlap"], e["name"]))
    return rank_mathlib_entries(loose, gap_type)[:top_n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="use the local heuristic classifier; no LLM call")
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "lean" / "gap_typed_outputs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"=== gap-typed prompter ===")
    print(f"  target: {args.target}")
    print(f"  field:  {args.field}")
    if args.dry_run or not os.environ.get("GEMINI_API_KEY"):
        print(f"\n[stage 1] classifying gap type via local heuristic...")
    else:
        print(f"\n[stage 1] classifying gap type via Gemini...")
    classification = classify_gap(args.target, args.field, dry_run=args.dry_run)
    gap_type = classification.get("gap_type", "UNKNOWN")
    print(f"  gap_type: {gap_type}")
    print(f"  confidence: {classification.get('confidence', '?')}")
    print(f"  rationale: {classification.get('rationale', '')[:200]}")

    print(f"\n[stage 2] fetching gap-specific lemmas from mathlib scout...")
    lemmas = fetch_gap_specific_lemmas(gap_type, top_n=12)
    print(f"  found {len(lemmas)} mathlib lemmas matching gap type {gap_type}")
    for lemma in lemmas[:5]:
        print(f"    - {lemma['name']} ({lemma['file']})")

    out_path = (args.out
                / f"{args.target}_{args.field}_gap_{gap_type.lower()}.json")
    out_path.write_text(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "target": args.target, "field": args.field,
        "classification": classification,
        "gap_specific_lemmas": [{"name": l["name"], "file": l["file"],
                                  "preview": l["preview"][:200]}
                                 for l in lemmas],
    }, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
